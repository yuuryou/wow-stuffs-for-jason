"""wow stuffs for Jason - video CMS."""

# CONTENT PIPELINE RULE:
# All game terms (map names, item names, NPC names, boss names, achievement names,
# reward names) MUST be cross-referenced with wowhead.com before being stored.
# NEVER machine-translate game terms. Each term must have both:
#   - English name (from wowhead)
#   - Traditional Chinese name (from wowhead 繁體中文 locale)
# Use wowhead_linker.py to fetch correct names for both languages.

import os
import sys
import json
from flask import Flask, render_template, request, jsonify, redirect, url_for, send_from_directory, make_response

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import (
    init_db, get_all_videos, get_videos, get_videos_paginated, get_video, add_video, update_video, delete_video,
    get_all_maps, get_all_rewards, get_videos_by_reward_type, get_stats, search_videos,
    get_rewards_by_category
)
from utils.douyin_parser import parse_douyin_url
from utils.wowhead_linker import search_wowhead, classify_reward, generate_wowhead_links

app = Flask(__name__)
app.config['SECRET_KEY'] = 'wow-douyin-hub-jason-2024'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['JSON_AS_ASCII'] = False
app.config['JSONIFY_MIMETYPE'] = 'application/json; charset=utf-8'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


@app.after_request
def add_charset_header(response):
    """Ensure all responses use UTF-8 encoding."""
    content_type = response.headers.get('Content-Type', '')
    if content_type and 'charset' not in content_type:
        # Only add charset to text/* and application/json responses
        if any(content_type.startswith(prefix) for prefix in
               ('text/', 'application/json', 'application/javascript')):
            response.headers['Content-Type'] = f'{content_type}; charset=utf-8'
    elif response.is_json:
        response.headers['Content-Type'] = 'application/json; charset=utf-8'
    return response


# ─── Language Helpers ────────────────────────────────────────────────────────

def get_lang():
    """Get current language from cookie. Defaults to 'zh'."""
    lang = request.cookies.get('lang', 'zh')
    return lang if lang in ('en', 'zh') else 'zh'


@app.template_filter('zfill')
def zfill_filter(value, width):
    """Pad a numeric string with leading zeros (Python str.zfill)."""
    return str(value).zfill(int(width))


@app.context_processor
def inject_lang():
    return {'lang': get_lang()}


# ─── Page Routes ────────────────────────────────────────────────────────────

@app.route('/')
def index():
    lang = get_lang()
    stats = get_stats()
    recent = get_videos(lang=lang, sort_by='created_at', order='DESC')[:6]
    maps_list = get_all_maps()
    return render_template('index.html', stats=stats, recent=recent, maps=maps_list, lang=lang)


@app.route('/videos')
def videos_page():
    lang = get_lang()
    sort_by = request.args.get('sort', 'created_at')
    order = request.args.get('order', 'DESC')
    map_filter = request.args.get('map', '')
    search = request.args.get('q', '')
    page = request.args.get('page', 1, type=int)

    if search:
        all_videos = search_videos(search)
        total = len(all_videos)
        per_page = 20
        total_pages = max(1, (total + per_page - 1) // per_page)
        page = max(1, min(page, total_pages))
        start = (page - 1) * per_page
        end = start + per_page
        videos = all_videos[start:end]
    else:
        videos, total, total_pages, page = get_videos_paginated(
            lang=lang, sort_by=sort_by, order=order,
            map_filter=map_filter or None, page=page, per_page=20
        )

    maps_list = get_all_maps()
    return render_template('videos.html', videos=videos, maps=maps_list,
                          current_sort=sort_by, current_order=order,
                          current_map=map_filter, search_query=search,
                          page=page, total_pages=total_pages, lang=lang)


@app.route('/videos/<int:video_id>')
def video_detail(video_id):
    lang = get_lang()
    video = get_video(video_id)
    if not video:
        return redirect(url_for('videos_page'))
    # Map language-specific fields
    if lang == 'en':
        video['title'] = video.get('title_en') or video.get('title', '')
        video['description'] = video.get('description_en') or video.get('description', '')
        video['map_name'] = video.get('map_name_en') or video.get('map_name', '')
    else:
        video['title'] = video.get('title_zh') or video.get('title', '')
        video['description'] = video.get('description_zh') or video.get('description', '')
        video['map_name'] = video.get('map_name_zh') or video.get('map_name', '')

    # Load per-video guide content from guides/video_{id}.html
    guide_html = None
    guide_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'guides', f'video_{video_id}.html')
    if os.path.isfile(guide_path):
        with open(guide_path, 'r', encoding='utf-8') as f:
            guide_content = f.read()
        # Render guide content as a Jinja2 template with lang context
        from jinja2 import Template
        guide_html = Template(guide_content).render(lang=lang)

    return render_template('video_detail.html', video=video, lang=lang, guide_html=guide_html)


@app.route('/maps')
def maps_page():
    lang = get_lang()
    maps_list = get_all_maps()
    return render_template('by_map.html', maps=maps_list, lang=lang)


@app.route('/maps/<path:map_name>')
def map_videos(map_name):
    lang = get_lang()
    videos = get_videos(lang=lang, map_filter=map_name)
    return render_template('map_detail.html', map_name=map_name, videos=videos, lang=lang)


@app.route('/rewards')
def rewards_page():
    lang = get_lang()
    categories = get_rewards_by_category()
    return render_template('by_rewards.html', categories=categories, lang=lang)


@app.route('/rewards/item/<category>/<path:name>')
def reward_item_videos(category, name):
    """Show videos containing a specific reward item."""
    lang = get_lang()
    from urllib.parse import unquote
    name = unquote(name)
    # Find videos that contain this reward
    all_videos = get_all_videos(sort_by='created_at', order='DESC')
    matched = []
    for v in all_videos:
        for r in v.get('rewards', []):
            if r.get('name', '') == name:
                matched.append(v)
                break
    # Look up time-limited status from reward_cache
    from database import get_db
    conn = get_db()
    row = conn.execute(
        'SELECT is_time_limited, time_limited_note FROM reward_cache WHERE name = ? AND category = ?',
        (name, category)
    ).fetchone()
    conn.close()
    is_time_limited = bool(row['is_time_limited']) if row else False
    time_limited_note = row['time_limited_note'] if row else ''
    return render_template('reward_item_detail.html',
                         category=category, reward_name=name,
                         videos=matched, lang=lang,
                         is_time_limited=is_time_limited,
                         time_limited_note=time_limited_note)


@app.route('/rewards/<reward_type>')
def reward_videos(reward_type):
    lang = get_lang()
    videos = get_videos_by_reward_type(reward_type)
    return render_template('reward_detail.html', reward_type=reward_type, videos=videos, lang=lang)


@app.route('/edit/<int:video_id>')
def edit_page(video_id):
    lang = get_lang()
    video = get_video(video_id)
    if not video:
        return redirect(url_for('videos_page'))
    maps_list = get_all_maps()
    return render_template('edit_video.html', video=video, maps=maps_list, lang=lang)


@app.route('/guides')
def guides_page():
    return render_template('guides.html', lang=get_lang())


@app.route('/guides/star-river-transmog')
def guide_star_river():
    return render_template('guide_star_river.html', lang=get_lang())


@app.route('/guides/void-twisted-whelpling')
def guide_void_twisted_whelpling():
    return render_template('guide_void_twisted_whelpling.html', lang=get_lang())


@app.route('/guides/primordial-anima-essence')
def guide_primordial_anima_essence():
    return render_template('guide_primordial_anima_essence.html', lang=get_lang())


@app.route('/guides/placid-deep-cat')
def guide_placid_deep_cat():
    return render_template('guide_placid_deep_cat.html', lang=get_lang())


@app.route('/guides/wheelchair-cat-baal')
def guide_wheelchair_cat_baal():
    return render_template('guide_wheelchair_cat_baal.html', lang=get_lang())


@app.route('/search')
def search_redirect():
    q = request.args.get('q', '')
    return redirect(url_for('videos_page', q=q))


# ─── Language Toggle Route ──────────────────────────────────────────────────

@app.route('/set-lang/<lang>')
def set_lang(lang):
    if lang not in ('en', 'zh'):
        lang = 'zh'
    resp = make_response(redirect(request.referrer or url_for('index')))
    resp.set_cookie('lang', lang, max_age=365*24*60*60, path='/', httponly=True)
    return resp


# ─── API Routes ─────────────────────────────────────────────────────────────

@app.route('/api/videos', methods=['GET'])
def api_get_videos():
    lang = request.args.get('lang', get_lang())
    sort_by = request.args.get('sort', 'created_at')
    order = request.args.get('order', 'DESC')
    map_filter = request.args.get('map', '')
    search = request.args.get('q', '')

    if search:
        videos = search_videos(search)
    else:
        videos = get_videos(lang=lang, sort_by=sort_by, order=order, map_filter=map_filter or None)
    return jsonify(videos)


@app.route('/api/videos', methods=['POST'])
def api_add_video():
    data = request.get_json(force=True, silent=True)
    if not data:
        data = request.form.to_dict()

    douyin_url = data.get('douyin_url', '').strip()
    if not douyin_url:
        err_msg = '請提供抖音連結' if get_lang() == 'zh' else 'Douyin URL is required'
        return jsonify({'error': err_msg}), 400

    # Auto-parse Douyin metadata if fields are empty
    if not data.get('title') and not data.get('title_zh') and not data.get('title_en'):
        parsed = parse_douyin_url(douyin_url)
        data['title'] = parsed.get('title', '')
        data['description'] = parsed.get('description', '')
        data['author'] = parsed.get('author', '')
        data['thumbnail_url'] = parsed.get('thumbnail_url', '')
        # Also store as zh by default
        if data['title']:
            data.setdefault('title_zh', data['title'])
        if data['description']:
            data.setdefault('description_zh', data['description'])

    # Process rewards and classify + search wowhead
    rewards_raw = data.get('rewards', [])
    if isinstance(rewards_raw, str):
        try:
            rewards_raw = json.loads(rewards_raw)
        except json.JSONDecodeError:
            rewards_raw = [{'name': n.strip()} for n in rewards_raw.split(',') if n.strip()]

    for r in rewards_raw:
        if 'type' not in r or not r['type']:
            r['type'] = classify_reward(r.get('name', ''))

    data['rewards'] = rewards_raw

    # Auto-generate wowhead links for rewards
    if rewards_raw and not data.get('wowhead_links'):
        names = [r['name'] for r in rewards_raw]
        links = generate_wowhead_links(names)
        data['wowhead_links'] = links

    # Parse time_spent_minutes from label if not provided
    if not data.get('time_spent_minutes') and data.get('time_spent_label'):
        import re
        hours_match = re.search(r'(\d+)\s*(小時|h|hr|hrs)', data['time_spent_label'])
        mins_match = re.search(r'(\d+)\s*(分鐘|分|m|min|mins)', data['time_spent_label'])
        total = 0
        if hours_match:
            total += int(hours_match.group(1)) * 60
        if mins_match:
            total += int(mins_match.group(1))
        if total > 0:
            data['time_spent_minutes'] = total
        elif data['time_spent_label'].isdigit():
            data['time_spent_minutes'] = int(data['time_spent_label'])

    try:
        vid = add_video(data)
        msg = '影片已新增' if get_lang() == 'zh' else 'Video added successfully'
        return jsonify({'id': vid, 'message': msg}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/videos/<int:video_id>', methods=['GET'])
def api_get_video(video_id):
    video = get_video(video_id)
    if not video:
        err_msg = '找不到影片' if get_lang() == 'zh' else 'Video not found'
        return jsonify({'error': err_msg}), 404
    return jsonify(video)


@app.route('/api/videos/<int:video_id>', methods=['PUT'])
def api_update_video(video_id):
    data = request.get_json(force=True, silent=True)
    if not data:
        data = request.form.to_dict()

    if 'rewards' in data and isinstance(data['rewards'], str):
        try:
            data['rewards'] = json.loads(data['rewards'])
        except json.JSONDecodeError:
            pass

    # Parse time_spent_minutes from label if present
    if data.get('time_spent_label') is not None and not data.get('time_spent_minutes'):
        import re as re_mod
        hours_match = re_mod.search(r'(\d+)\s*(小時|h|hr|hrs)', data['time_spent_label'])
        mins_match = re_mod.search(r'(\d+)\s*(分鐘|分|m|min|mins)', data['time_spent_label'])
        total = 0
        if hours_match:
            total += int(hours_match.group(1)) * 60
        if mins_match:
            total += int(mins_match.group(1))
        if total > 0:
            data['time_spent_minutes'] = total
        elif data['time_spent_label'].isdigit():
            data['time_spent_minutes'] = int(data['time_spent_label'])

    update_video(video_id, data)
    msg = '影片已更新' if get_lang() == 'zh' else 'Video updated successfully'
    return jsonify({'message': msg})


@app.route('/api/videos/<int:video_id>', methods=['DELETE'])
def api_delete_video(video_id):
    delete_video(video_id)
    msg = '影片已刪除' if get_lang() == 'zh' else 'Video deleted successfully'
    return jsonify({'message': msg})


@app.route('/api/maps')
def api_get_maps():
    return jsonify(get_all_maps())


@app.route('/api/rewards')
def api_get_rewards():
    return jsonify(get_all_rewards())


@app.route('/api/stats')
def api_get_stats():
    return jsonify(get_stats())


@app.route('/api/wowhead/search')
def api_wowhead_search():
    q = request.args.get('q', '')
    itype = request.args.get('type', '')
    if not q:
        return jsonify([])
    results = search_wowhead(q, item_type=itype or None)
    return jsonify(results)


@app.route('/api/parse-douyin', methods=['POST'])
def api_parse_douyin():
    data = request.get_json(force=True, silent=True)
    if not data:
        data = request.form.to_dict()
    url = data.get('url', '')
    if not url:
        err_msg = '請提供網址' if get_lang() == 'zh' else 'URL required'
        return jsonify({'error': err_msg}), 400
    result = parse_douyin_url(url)
    return jsonify(result)


# ─── Static Files ──────────────────────────────────────────────────────────

@app.route('/static/<path:filename>')
def static_files(filename):
    resp = send_from_directory(os.path.join(BASE_DIR, 'static'), filename)
    ext = os.path.splitext(filename)[1].lower()
    # Cache static assets aggressively: 7 days for media, 1 day for CSS/JS
    if ext in ('.mp4', '.webm', '.jpg', '.jpeg', '.png', '.webp', '.gif', '.svg', '.ico', '.woff2'):
        resp.cache_control.max_age = 604800  # 7 days
        resp.cache_control.public = True
    elif ext in ('.css', '.js'):
        resp.cache_control.max_age = 86400   # 1 day
        resp.cache_control.public = True
    return resp


# ─── Error Handlers ─────────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(e):
    return render_template('404.html', lang=get_lang()), 404


@app.errorhandler(500)
def server_error(e):
    return render_template('500.html', lang=get_lang()), 500


# ─── Main ───────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    init_db()
    print("wow stuffs for Jason")
    print("   運行於 http://localhost:5050")
    app.run(host='0.0.0.0', port=5050, debug=True)
