"""Douyin video link parser - extracts metadata from Douyin share links."""

import re
import requests
import json


def parse_douyin_url(url):
    """Parse a Douyin share URL and extract basic metadata if possible."""
    result = {
        'url': url,
        'title': '',
        'description': '',
        'author': '',
        'thumbnail_url': '',
        'video_id': ''
    }

    # Extract video ID from various Douyin URL formats
    patterns = [
        r'video/(\d+)',
        r'modal_id=(\d+)',
        r'/(\d{15,})/',
        r'note/(\d+)',
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            result['video_id'] = match.group(1)
            break

    # Try to fetch page metadata
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) '
                          'AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 '
                          'Mobile/15E148 Safari/604.1'
        }
        resp = requests.get(url, headers=headers, timeout=15, allow_redirects=True)

        if resp.status_code == 200:
            # Ensure proper UTF-8 decoding of response content
            resp.encoding = resp.apparent_encoding or 'utf-8'
            html = resp.text

            # Try to find JSON-LD or og tags
            title_match = re.search(r'<title>([^<]+)</title>', html)
            if title_match:
                result['title'] = title_match.group(1).strip()

            og_title = re.search(r'<meta[^>]+property="og:title"[^>]+content="([^"]+)"', html)
            if og_title:
                result['title'] = og_title.group(1)

            og_desc = re.search(r'<meta[^>]+property="og:description"[^>]+content="([^"]+)"', html)
            if og_desc:
                result['description'] = og_desc.group(1)

            og_image = re.search(r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"', html)
            if og_image:
                result['thumbnail_url'] = og_image.group(1)

            # Try embedded JSON data - use balanced brace extractor
            json_pattern = r'window\._ROUTER_DATA\s*=\s*'
            json_match = re.search(json_pattern, html)
            if json_match:
                start = json_match.end()
                depth = 0
                end = start
                in_string = False
                escape = False
                for i, ch in enumerate(html[start:], start):
                    if escape:
                        escape = False
                        continue
                    if ch == '\\':
                        escape = True
                        continue
                    if ch == '"' and not escape:
                        in_string = not in_string
                        continue
                    if in_string:
                        continue
                    if ch == '{':
                        depth += 1
                    elif ch == '}':
                        depth -= 1
                        if depth == 0:
                            end = i + 1
                            break
                if end > start:
                    try:
                        data = json.loads(html[start:end])
                        loader = data.get('loaderData', {})
                        for key in loader:
                            video_data = loader[key].get('videoData', {})
                            if video_data:
                                result['title'] = video_data.get('desc', result['title'])
                                author_info = video_data.get('author', {})
                                result['author'] = author_info.get('nickname', '')
                                cover = video_data.get('cover', {})
                                result['thumbnail_url'] = cover.get('url_list', [''])[0] or result['thumbnail_url']
                                break
                    except (json.JSONDecodeError, KeyError, TypeError):
                        pass

    except Exception:
        pass

    return result
