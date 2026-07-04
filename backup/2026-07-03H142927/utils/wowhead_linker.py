# CONTENT PIPELINE RULE:
# All game terms (map names, item names, NPC names, boss names, achievement names,
# reward names) MUST be cross-referenced with wowhead.com before being stored.
# NEVER machine-translate game terms. Each term must have both:
#   - English name (from wowhead)
#   - Traditional Chinese name (from wowhead 繁體中文 locale)
# Use wowhead_linker.py to fetch correct names for both languages.
"""wowhead.com integration - search items and generate links."""

import requests
import re
from urllib.parse import quote

WOWHEAD_SEARCH = "https://www.wowhead.com/search"
WOWHEAD_ITEM = "https://www.wowhead.com/item={id}"
WOWHEAD_QUEST = "https://www.wowhead.com/quest={id}"
WOWHEAD_NPC = "https://www.wowhead.com/npc={id}"
WOWHEAD_SPELL = "https://www.wowhead.com/spell={id}"
WOWHEAD_ZONE = "https://www.wowhead.com/zone={id}"

TYPE_URLS = {
    'mount': 'https://www.wowhead.com/mounts',
    'item': 'https://www.wowhead.com/items',
    'quest': 'https://www.wowhead.com/quests',
    'spell': 'https://www.wowhead.com/spells',
    'npc': 'https://www.wowhead.com/npcs',
    'zone': 'https://www.wowhead.com/zones',
    'achievement': 'https://www.wowhead.com/achievements',
}


def search_wowhead(query, item_type=None):
    """Search wowhead for an item/quest/npc and return possible matches."""
    try:
        params = {'q': query}
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        resp = requests.get(WOWHEAD_SEARCH, params=params, headers=headers, timeout=10)
        if resp.status_code != 200:
            return []

        resp.encoding = resp.apparent_encoding or 'utf-8'

        results = []
        # Extract from search results page
        pattern = r'data-id="(\d+)"[^>]*data-type="(\w+)"[^>]*>(.*?)</a>'
        matches = re.findall(pattern, resp.text, re.DOTALL)

        for m in matches[:10]:
            wid, wtype, raw_name = m
            name = re.sub(r'<[^>]+>', '', raw_name).strip()
            if item_type and wtype != item_type:
                continue
            results.append({
                'id': wid,
                'type': wtype,
                'name': name,
                'url': get_wowhead_url(wid, wtype)
            })
        return results
    except Exception:
        return []


def get_wowhead_url(wid, wtype='item'):
    url_map = {
        'item': WOWHEAD_ITEM,
        'quest': WOWHEAD_QUEST,
        'npc': WOWHEAD_NPC,
        'spell': WOWHEAD_SPELL,
        'zone': WOWHEAD_ZONE,
    }
    template = url_map.get(wtype, WOWHEAD_ITEM)
    return template.format(id=wid)


def generate_wowhead_links(item_names):
    """Given a list of item name strings, search wowhead and return links."""
    links = []
    for name in item_names:
        results = search_wowhead(name)
        if results:
            links.append(results[0])
        else:
            links.append({
                'name': name,
                'url': f'https://www.wowhead.com/search?q={quote(name)}',
                'type': 'unknown'
            })
    return links


def classify_reward(name):
    """Classify a reward name as mount/item/achievement based on keywords."""
    name_lower = name.lower()
    mount_keywords = ['reins', 'mount', 'drake', 'proto', 'serpent', 'charger',
                      'steed', 'wyrm', 'talon', 'phoenix', 'hawkstrider',
                      '坐騎', '韁繩', '龍', '馬', '鳥', '獸', '虎', '狼', '豹']
    achievement_keywords = ['achievement', 'title', 'lord', 'lady',
                            'feat of strength', 'glory of the',
                            '成就', '頭銜', '偉業']

    for kw in mount_keywords:
        if kw in name_lower:
            return 'mount'
    for kw in achievement_keywords:
        if kw in name_lower:
            return 'achievement'
    return 'item'
