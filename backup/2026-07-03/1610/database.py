import sqlite3
import json
import os
from datetime import datetime

DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
DB_PATH = os.path.join(DB_DIR, 'wow_hub.db')


def get_db():
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_db()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            douyin_url TEXT NOT NULL UNIQUE,
            title TEXT DEFAULT '',
            description TEXT DEFAULT '',
            author TEXT DEFAULT '',
            map_name TEXT DEFAULT '',
            title_en TEXT DEFAULT '',
            title_zh TEXT DEFAULT '',
            description_en TEXT DEFAULT '',
            description_zh TEXT DEFAULT '',
            map_name_en TEXT DEFAULT '',
            map_name_zh TEXT DEFAULT '',
            time_spent_minutes INTEGER DEFAULT 0,
            time_spent_label TEXT DEFAULT '',
            rewards_json TEXT DEFAULT '[]',
            wowhead_links_json TEXT DEFAULT '[]',
            thumbnail_url TEXT DEFAULT '',
            thumbnail_local TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            updated_at TEXT DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS reward_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT DEFAULT 'other',
            wowhead_icon_url TEXT DEFAULT '',
            wowhead_id INTEGER DEFAULT 0,
            lookup_count INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            UNIQUE(name, category)
        );

        CREATE INDEX IF NOT EXISTS idx_videos_map ON videos(map_name);
        CREATE INDEX IF NOT EXISTS idx_videos_created ON videos(created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_reward_cache_category ON reward_cache(category);
    ''')
    conn.commit()
    conn.close()


def video_from_row(row):
    if row is None:
        return None
    v = dict(row)
    v['rewards'] = json.loads(v.get('rewards_json', '[]'))
    v['wowhead_links'] = json.loads(v.get('wowhead_links_json', '[]'))
    return v


def get_videos(lang='zh', sort_by='created_at', order='DESC', map_filter=None):
    """Return videos with language-appropriate fields mapped to neutral keys.

    Args:
        lang: 'en' or 'zh' (Traditional Chinese, default)
        sort_by, order, map_filter: same as get_all_videos

    Returns videos where title/description/map_name are taken from
    _en or _zh columns, falling back gracefully for legacy data.
    """
    rows = get_all_videos_raw(sort_by=sort_by, order=order, map_filter=map_filter)
    result = []
    for r in rows:
        v = video_from_row(r)
        if lang == 'en':
            v['title'] = v.get('title_en') or v.get('title', '')
            v['description'] = v.get('description_en') or v.get('description', '')
            v['map_name'] = v.get('map_name_en') or v.get('map_name', '')
        else:
            v['title'] = v.get('title_zh') or v.get('title', '')
            v['description'] = v.get('description_zh') or v.get('description', '')
            v['map_name'] = v.get('map_name_zh') or v.get('map_name', '')
        result.append(v)
    return result


def get_videos_paginated(lang='zh', sort_by='created_at', order='DESC',
                         map_filter=None, page=1, per_page=20):
    """Return paginated videos with total count.

    Returns:
        (videos, total_count, total_pages, page)
    """
    rows = get_all_videos_raw(sort_by=sort_by, order=order, map_filter=map_filter)
    total = len(rows)

    # Apply pagination slice
    start = (page - 1) * per_page
    end = start + per_page
    rows = rows[start:end]

    result = []
    for r in rows:
        v = video_from_row(r)
        if lang == 'en':
            v['title'] = v.get('title_en') or v.get('title', '')
            v['description'] = v.get('description_en') or v.get('description', '')
            v['map_name'] = v.get('map_name_en') or v.get('map_name', '')
        else:
            v['title'] = v.get('title_zh') or v.get('title', '')
            v['description'] = v.get('description_zh') or v.get('description', '')
            v['map_name'] = v.get('map_name_zh') or v.get('map_name', '')
        result.append(v)

    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))
    return result, total, total_pages, page


def get_all_videos_raw(sort_by='created_at', order='DESC', map_filter=None):
    """Raw fetch without language mapping. Used internally by get_videos()."""
    conn = get_db()
    valid_sorts = {'created_at', 'title', 'time_spent_minutes', 'map_name'}
    if sort_by not in valid_sorts:
        sort_by = 'created_at'
    order = 'DESC' if order.upper() == 'DESC' else 'ASC'

    query = 'SELECT * FROM videos'
    params = []
    if map_filter:
        query += ' WHERE map_name = ? OR map_name_en = ? OR map_name_zh = ?'
        params.extend([map_filter, map_filter, map_filter])
    query += f' ORDER BY {sort_by} {order}'

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [video_from_row(r) for r in rows]


def get_all_videos(sort_by='created_at', order='DESC', map_filter=None):
    return get_all_videos_raw(sort_by=sort_by, order=order, map_filter=map_filter)


def get_video(video_id):
    conn = get_db()
    row = conn.execute('SELECT * FROM videos WHERE id = ?', (video_id,)).fetchone()
    conn.close()
    return video_from_row(row)


def add_video(data):
    conn = get_db()
    conn.execute('''
        INSERT INTO videos (douyin_url, title, description, author, map_name,
                           title_en, title_zh, description_en, description_zh,
                           map_name_en, map_name_zh,
                           time_spent_minutes, time_spent_label, rewards_json,
                           wowhead_links_json, thumbnail_url, thumbnail_local)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data['douyin_url'],
        data.get('title', ''),
        data.get('description', ''),
        data.get('author', ''),
        data.get('map_name', ''),
        data.get('title_en', ''),
        data.get('title_zh', data.get('title', '')),
        data.get('description_en', ''),
        data.get('description_zh', data.get('description', '')),
        data.get('map_name_en', ''),
        data.get('map_name_zh', data.get('map_name', '')),
        data.get('time_spent_minutes', 0),
        data.get('time_spent_label', ''),
        json.dumps(data.get('rewards', []), ensure_ascii=False),
        json.dumps(data.get('wowhead_links', []), ensure_ascii=False),
        data.get('thumbnail_url', ''),
        data.get('thumbnail_local', '')
    ))
    conn.commit()
    vid = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
    conn.close()
    return vid


def update_video(video_id, data):
    conn = get_db()
    fields = []
    values = []
    for key in ['title', 'description', 'author', 'map_name',
                'title_en', 'title_zh', 'description_en', 'description_zh',
                'map_name_en', 'map_name_zh',
                'time_spent_minutes', 'time_spent_label',
                'thumbnail_url', 'thumbnail_local', 'douyin_url']:
        if key in data:
            fields.append(f'{key} = ?')
            values.append(data[key])
    if 'rewards' in data:
        fields.append('rewards_json = ?')
        values.append(json.dumps(data['rewards'], ensure_ascii=False))
    if 'wowhead_links' in data:
        fields.append('wowhead_links_json = ?')
        values.append(json.dumps(data['wowhead_links'], ensure_ascii=False))

    fields.append("updated_at = datetime('now', 'localtime')")
    values.append(video_id)
    conn.execute(f'UPDATE videos SET {", ".join(fields)} WHERE id = ?', values)
    conn.commit()
    conn.close()


def delete_video(video_id):
    conn = get_db()
    conn.execute('DELETE FROM videos WHERE id = ?', (video_id,))
    conn.commit()
    conn.close()


def get_all_maps():
    conn = get_db()
    rows = conn.execute(
        'SELECT map_name, COUNT(*) as count FROM videos WHERE map_name != "" GROUP BY map_name ORDER BY count DESC'
    ).fetchall()
    conn.close()
    return [{'name': r['map_name'], 'count': r['count']} for r in rows]


def get_all_rewards():
    conn = get_db()
    rows = conn.execute('SELECT rewards_json FROM videos WHERE rewards_json != "[]"').fetchall()
    conn.close()
    reward_map = {}
    for r in rows:
        rewards = json.loads(r['rewards_json'])
        for item in rewards:
            name = item.get('name', '')
            rtype = item.get('type', 'other')
            if name:
                key = f"{rtype}:{name}"
                if key not in reward_map:
                    reward_map[key] = {'name': name, 'type': rtype, 'count': 0}
                reward_map[key]['count'] += 1
    return sorted(reward_map.values(), key=lambda x: x['count'], reverse=True)


def get_videos_by_reward_type(rtype):
    conn = get_db()
    rows = conn.execute('SELECT * FROM videos WHERE rewards_json != "[]"').fetchall()
    conn.close()
    result = []
    for r in rows:
        rewards = json.loads(r['rewards_json'])
        if any(item.get('type') == rtype for item in rewards):
            result.append(video_from_row(r))
    return result


def get_stats():
    conn = get_db()
    total = conn.execute('SELECT COUNT(*) FROM videos').fetchone()[0]
    maps_count = conn.execute(
        'SELECT COUNT(DISTINCT map_name) FROM videos WHERE map_name != ""'
    ).fetchone()[0]
    total_time = conn.execute(
        'SELECT SUM(time_spent_minutes) FROM videos'
    ).fetchone()[0] or 0

    # Map coverage: videos that have an associated map
    videos_with_map = conn.execute(
        'SELECT COUNT(*) FROM videos WHERE map_name != "" OR map_name_en != "" OR map_name_zh != ""'
    ).fetchone()[0]
    map_coverage = round(videos_with_map / total * 100, 1) if total > 0 else 0

    # Total rewards (distinct rewards across all videos)
    import json as _json
    rows = conn.execute(
        "SELECT rewards_json FROM videos WHERE rewards_json != '[]' AND rewards_json IS NOT NULL"
    ).fetchall()
    rewards_set = set()
    for r in rows:
        try:
            items = _json.loads(r['rewards_json'])
            for item in items:
                name = item.get('name', '').strip()
                if name:
                    rewards_set.add(name)
        except Exception:
            pass

    conn.close()
    return {
        'total_videos': total,
        'total_maps': maps_count,
        'total_time_minutes': total_time,
        'total_time_label': f"{total_time // 60}小時{total_time % 60}分" if total_time >= 60 else f"{total_time}分鐘",
        'map_coverage': map_coverage,
        'total_rewards': len(rewards_set),
    }


def search_videos(keyword):
    conn = get_db()
    q = f'%{keyword}%'
    rows = conn.execute(
        '''SELECT * FROM videos
           WHERE title LIKE ? OR description LIKE ? OR map_name LIKE ?
              OR rewards_json LIKE ?
           ORDER BY created_at DESC''',
        (q, q, q, q)
    ).fetchall()
    conn.close()
    return [video_from_row(r) for r in rows]


# ─── Reward Cache ──────────────────────────────────────────────────────────

def get_reward_cache(name, category):
    """Get cached reward entry."""
    conn = get_db()
    row = conn.execute(
        'SELECT * FROM reward_cache WHERE name = ? AND category = ?',
        (name, category)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def upsert_reward_cache(name, category, wowhead_icon_url='', wowhead_id=0):
    """Insert or update reward cache entry."""
    conn = get_db()
    existing = conn.execute(
        'SELECT id, lookup_count FROM reward_cache WHERE name = ? AND category = ?',
        (name, category)
    ).fetchone()
    if existing:
        conn.execute(
            '''UPDATE reward_cache
               SET wowhead_icon_url = COALESCE(NULLIF(?, ''), wowhead_icon_url),
                   wowhead_id = CASE WHEN ? > 0 THEN ? ELSE wowhead_id END,
                   lookup_count = lookup_count + 1
               WHERE id = ?''',
            (wowhead_icon_url, wowhead_id, wowhead_id, existing['id'])
        )
    else:
        conn.execute(
            '''INSERT INTO reward_cache (name, category, wowhead_icon_url, wowhead_id)
               VALUES (?, ?, ?, ?)''',
            (name, category, wowhead_icon_url, wowhead_id)
        )
    conn.commit()
    conn.close()


def get_rewards_by_category():
    """Get all rewards grouped by category, with cached icons."""
    from utils.wowhead_image import classify_reward_to_category, get_wowhead_icon_url

    # First, collect all unique rewards from videos and classify them
    conn = get_db()
    rows = conn.execute(
        "SELECT id, rewards_json FROM videos WHERE rewards_json != '[]'"
    ).fetchall()
    conn.close()

    reward_lookup = {}  # key: (category, name)
    for r in rows:
        video_id = r['id']
        rewards = json.loads(r['rewards_json'])
        for item in rewards:
            name = item.get('name', '')
            rtype = item.get('type', 'other')
            if not name:
                continue
            category = classify_reward_to_category(name, rtype)
            key = (category, name)
            if key not in reward_lookup:
                reward_lookup[key] = {
                    'name': name,
                    'category': category,
                    'original_type': rtype,
                    'count': 0,
                    'video_ids': [],
                    'wowhead_icon_url': '',
                }
            reward_lookup[key]['count'] += 1
            if video_id not in reward_lookup[key]['video_ids']:
                reward_lookup[key]['video_ids'].append(video_id)

    # Load cached icons
    conn = get_db()
    cached = conn.execute('SELECT name, category, wowhead_icon_url FROM reward_cache').fetchall()
    conn.close()
    cache_map = {(r['category'], r['name']): r['wowhead_icon_url'] for r in cached}

    # Assign icons from cache or generate fallback URLs (use large icons for better quality)
    LARGE_ICON_BASE = "https://wow.zamimg.com/images/wow/icons/large"
    from utils.wowhead_image import FALLBACK_ICONS
    for key, val in reward_lookup.items():
        if key in cache_map and cache_map[key]:
            val['wowhead_icon_url'] = cache_map[key].replace('/medium/', '/large/')
        else:
            cat = val['category']
            fallback = FALLBACK_ICONS.get(cat, 'inv_misc_questionmark')
            val['wowhead_icon_url'] = f"{LARGE_ICON_BASE}/{fallback}.jpg"

    # Group by category
    categories = {}
    for key, val in reward_lookup.items():
        cat = val['category']
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(val)

    # Sort each category's rewards by count desc
    for cat in categories:
        categories[cat].sort(key=lambda x: x['count'], reverse=True)

    return categories
