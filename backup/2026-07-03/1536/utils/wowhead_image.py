"""Wowhead image URL utilities.

Wowhead provides item/achievement icons via:
- https://wow.zamimg.com/images/wow/icons/large/{icon_name}.jpg (large)
- https://wow.zamimg.com/images/wow/icons/medium/{icon_name}.jpg (medium)
- https://wow.zamimg.com/modelviewer/live/webthumbs/npc/{display_id}/{display_id}.jpg (NPC/mount)

We also support generating Wowhead tooltip links with icons via the static render:
- https://wow.zamimg.com/images/wow/icons/medium/{icon}.jpg

For automatic lookup, we use wowhead search to find item/spell IDs,
then derive icon URLs from known icon patterns or scrape the tooltip page.
"""

import json
import os
import sqlite3
import re
import urllib.request
import urllib.parse
import urllib.error
import time

WOWHEAD_SEARCH_URL = "https://www.wowhead.com/search"
WOWHEAD_ICON_BASE = "https://wow.zamimg.com/images/wow/icons/medium"
WOWHEAD_ITEM_URL = "https://www.wowhead.com/item/{id}"
WOWHEAD_SPELL_URL = "https://www.wowhead.com/spell/{id}"
WOWHEAD_ACHIEVEMENT_URL = "https://www.wowhead.com/achievement/{id}"

# Known category → search type mapping
CATEGORY_TYPE_MAP = {
    'mount': 'spell',      # mounts are spells on wowhead
    'toy': 'item',
    'transmog': 'item',
    'pet': 'item',
    'gear': 'item',
    'weapon': 'item',
    'achievement': 'achievement',
    'other': 'item',
}

# Common icon name patterns for known items (fallback when search fails)
FALLBACK_ICONS = {
    'mount': 'ability_mount_ridinghorse',
    'toy': 'inv_misc_toy_01',
    'transmog': 'inv_chest_cloth_43',
    'pet': 'inv_pet_baby',
    'achievement': 'achievement_bg_winwsg',
    'gear': 'inv_helmet_120',
    'weapon': 'inv_sword_1h_short',
    'other': 'inv_misc_questionmark',
}


def _wowhead_search(name, search_type='item'):
    """Search wowhead for an item/spell/achievement and return the first result.

    Uses the Wowhead JSON search endpoint:
    https://www.wowhead.com/search?q=QUERY&json
    """
    params = urllib.parse.urlencode({'q': name, 'json': ''})
    url = f"{WOWHEAD_SEARCH_URL}?{params}"
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
    })
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode('utf-8', errors='replace')
    except Exception:
        return None

    # Wowhead returns a JSON array: [query_string, {items: [{...}]}]
    # The JSON sometimes uses unquoted keys (JS-style), try to handle both
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Fallback: extract icon with regex
        icon_match = re.search(r'"icon"\s*:\s*"([^"]+)"', raw)
        if icon_match:
            return {'wowhead_id': 0, 'icon': icon_match.group(1), 'search_type': search_type}
        return None

    if isinstance(data, list) and len(data) >= 2:
        result_obj = data[1]
        items = result_obj.get('items', [])
        if items:
            first = items[0]
            return {
                'wowhead_id': first.get('id', 0),
                'icon': first.get('icon'),
                'search_type': search_type,
            }

    return None


def get_wowhead_icon_url(name, category='other'):
    """Get a wowhead icon URL for a reward item.

    Returns a medium icon URL string, or None if not found.
    Result is cached locally to avoid repeated lookups.
    """
    cache = _load_icon_cache()
    cache_key = f"{category}:{name.lower()}"
    if cache_key in cache:
        cached = cache[cache_key]
        if cached:
            return cached

    # Try to search wowhead
    search_type = CATEGORY_TYPE_MAP.get(category, 'item')
    result = _wowhead_search(name, search_type)

    if result and result.get('icon'):
        icon_url = f"{WOWHEAD_ICON_BASE}/{result['icon']}.jpg"
        cache[cache_key] = icon_url
        _save_icon_cache(cache)
        return icon_url

    # Use fallback icon based on category
    fallback = FALLBACK_ICONS.get(category, 'inv_misc_questionmark')
    icon_url = f"{WOWHEAD_ICON_BASE}/{fallback}.jpg"
    cache[cache_key] = icon_url
    _save_icon_cache(cache)
    return icon_url


# ─── Local cache (file-based) ────────────────────────────────────────────

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
CACHE_FILE = os.path.join(CACHE_DIR, 'wowhead_icon_cache.json')


def _load_icon_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_icon_cache(cache):
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


# ─── Category definitions ────────────────────────────────────────────────

CATEGORY_EMOJI = {
    'toy': '🧸',
    'mount': '🐎',
    'transmog': '👗',
    'pet': '🐾',
    'achievement': '🏆',
    'gear': '🛡️',
    'weapon': '⚔️',
    'other': '🎁',
}

CATEGORY_LABELS_ZH = {
    'toy': '玩具',
    'mount': '坐騎',
    'transmog': '幻化',
    'pet': '寵物',
    'achievement': '成就',
    'gear': '裝備',
    'weapon': '武器',
    'other': '其他',
}

CATEGORY_LABELS_EN = {
    'toy': 'Toys',
    'mount': 'Mounts',
    'transmog': 'Transmog',
    'pet': 'Pets',
    'achievement': 'Achievements',
    'gear': 'Gear',
    'weapon': 'Weapons',
    'other': 'Other',
}


def classify_reward_to_category(reward_name, reward_type):
    """Map reward name/type to a UI category."""
    name_lower = reward_name.lower() if reward_name else ''

    # Mounts
    if reward_type == 'mount':
        return 'mount'
    if 'mount' in name_lower or 'reins' in name_lower or 'steed' in name_lower:
        return 'mount'

    # Achievements
    if reward_type == 'achievement':
        return 'achievement'

    # Pets
    if reward_type == 'pet' or 'pet' in name_lower or 'companion' in name_lower:
        return 'pet'

    # Toys
    toy_keywords = ['toy', 'ball', 'kite', 'whistle', 'prism', 'totem',
                    'reflector', 'transformer', 'costume', 'disguise',
                    '火把', '镜子', '盒子', '玩具', '风车', '气球',
                    '笛子', '哨子', '玩偶', '娃娃', '风筝']
    if any(kw in name_lower for kw in toy_keywords):
        return 'toy'

    # Transmog (appearance items)
    mog_keywords = ['cloak', 'robe', 'tunic', 'vest', 'leggings', 'bracers',
                    'shoulders', 'helm', 'boots', 'gloves', 'belt', 'tabard',
                    'shirt', 'gown', 'mantle', 'cowl', 'hood', 'cap',
                    '披风', '斗篷', '长袍', '外套', '护腿', '护腕',
                    '肩甲', '头盔', '靴子', '手套', '腰带', '衬衣']
    if any(kw in name_lower for kw in mog_keywords):
        return 'transmog'

    # Weapons
    weapon_keywords = ['sword', 'axe', 'mace', 'dagger', 'staff', 'bow',
                       'gun', 'wand', 'polearm', 'shield', 'fist',
                       'blade', 'hammer', 'spear', 'crossbow', 'glaive',
                       '剑', '斧', '锤', '匕首', '法杖', '弓',
                       '枪', '魔杖', '长柄', '盾', '拳套', '刀']
    if any(kw in name_lower for kw in weapon_keywords):
        return 'weapon'

    # Gear (armor/equipment not covered by transmog/weapon)
    gear_keywords = ['ring', 'necklace', 'trinket', 'amulet', 'charm',
                     '戒指', '项链', '饰品', '护符']
    if any(kw in name_lower for kw in gear_keywords):
        return 'gear'

    return 'other'


def get_category_label(category, lang='en'):
    """Get display label for a category."""
    if lang == 'zh':
        return CATEGORY_LABELS_ZH.get(category, category.capitalize())
    return CATEGORY_LABELS_EN.get(category, category.capitalize())


def get_category_emoji(category):
    """Get emoji icon for a category."""
    return CATEGORY_EMOJI.get(category, '🎁')
