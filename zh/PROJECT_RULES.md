# Wow Stuffs for Jason — 專案規則

> 所有改動必須遵守本文件。新增功能 / 內容時，若相關規則已在此定義，一律以本文為準。

---

## 1. 獎勵圖片規則

- **來源**：所有獎勵物品的圖片必須從 **Wowhead** 取得實際物品圖示，禁止使用通用問號 fallback。
- **搜尋方式**：使用 Wowhead JSON API 端點：
  ```
  https://www.wowhead.com/search?q={物品名稱}&json
  ```
  傳回格式為 `[query_string, {items: [{icon: "xxx", id: 123, ...}]}]`，從 `items[0].icon` 提取圖示名稱。
- **圖片 URL**：
  ```
  https://wow.zamimg.com/images/wow/icons/large/{icon_name}.jpg
  ```
- **快取**：所有查到的圖示必須存入 `reward_cache` 表，避免每次重複搜尋。
- **快取鍵順序**：`cache_map` 的 key 必須是 `(category, name)`，不可顛倒為 `(name, category)`，否則永遠匹配不上。

### 新獎勵入庫流程

1. 影片新增後，若含 `rewards_json`，掃描其中的獎勵名稱與類型
2. 對每個新獎勵，呼叫 `_wowhead_search(name)` 搜尋 Wowhead
3. 搜尋不到時，嘗試去掉逗號後的部分（如 "X, Y" → "X"）再搜一次
4. 仍找不到時，嘗試用相近關鍵詞搜尋，記錄結果
5. 將 `(name, category, wowhead_icon_url)` 寫入 `reward_cache`（`INSERT OR REPLACE`）
6. 若完全無法取得圖示，才使用類別 fallback 圖示（`utils/wowhead_image.py` 中的 `FALLBACK_ICONS`）

---

## 2. 中文化規則

- 所有模板中的 UI 文字必須使用 `{% if lang == 'zh' %}中文{% else %}English{% endif %}` 條件分支覆蓋
- 重點檢查對象：導航欄、按鈕、標籤、空狀態提示、計數單位、頁面標題
- 浮動導航欄必須完全雙語，不遺漏任何標籤

---

## 3. 備份規則

- 任何程式碼 / 模板 / CSS / 資料庫結構修改前，必須先建立備份
- 備份路徑：`backup/YYYY-MM-DD/HHMM/`
- 備份內容：`templates/`、`static/css/`、`utils/`、`data/`、`app.py`、`database.py`

---

## 4. 座標格式規則

- WOW 攻略頁面中的 `/way` 座標必須以可點擊複製按鈕呈現
- CSS class：`.way-copy`，屬性：`data-way`
- 點擊後透過 `navigator.clipboard` 複製並顯示 `✓ Copied!` 回饋

---

## 5. 圖片引用規則

- 從 Wowhead 借用的圖片，使用其 CDN URL（`wow.zamimg.com`），不本地儲存
- 圖片載入使用 `loading="lazy"` 並提供 `onerror` fallback

---

## 6. 獎勵類別定義

| 類別鍵 | 中文 | English |
|--------|------|---------|
| toy | 玩具 | Toys |
| mount | 坐騎 | Mounts |
| transmog | 幻化 | Transmog |
| pet | 寵物 | Pets |
| achievement | 成就 | Achievements |
| gear | 裝備 | Gear |
| weapon | 武器 | Weapons |
| other | 其他 | Other |
