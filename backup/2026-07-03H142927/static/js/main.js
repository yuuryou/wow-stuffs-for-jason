/**
 * WoW Douyin Hub - WoW Theme
 * Client-side interactivity
 */

const LANG = document.documentElement.dataset.lang || 'zh';

const T = {
    zh: {
        confirmDelete: '確定要刪除這個影片？此操作無法撤銷。',
        deleted: '影片已刪除',
        deleteFail: '刪除失敗',
        deleteFailMsg: '刪除失敗: ',
        parsing: '解析中...',
        parse: '解析',
        parseOk: 'Douyin 資訊已自動填入',
        parseFail: '解析失敗，請手動填寫',
        noResults: '未找到結果',
        searchFail: '搜尋失敗',
        clickAdd: '點擊新增',
        videoSaved: '影片已儲存',
        saveFail: '儲存失敗',
    },
    en: {
        confirmDelete: 'Are you sure you want to delete this video? This cannot be undone.',
        deleted: 'Video deleted',
        deleteFail: 'Delete failed',
        deleteFailMsg: 'Delete failed: ',
        parsing: 'Parsing...',
        parse: 'Parse',
        parseOk: 'Douyin info auto-filled',
        parseFail: 'Parse failed, please fill manually',
        noResults: 'No results found',
        searchFail: 'Search failed',
        clickAdd: 'Click to add',
        videoSaved: 'Video saved successfully',
        saveFail: 'Save failed',
    }
};

function _(key) {
    return (T[LANG] && T[LANG][key]) || (T['zh'][key]) || key;
}

document.addEventListener('DOMContentLoaded', () => {
    initSortSelects();
    initRewardInputs();
    initDeleteButtons();
    initWowheadSearch();
    initLangToggle();
    initGlassRefraction();
    observeGlassEnter();
    initNavIndicator();
});

/* ── Sort / Filter Auto-submit ────────────────────────────────────────── */
function initSortSelects() {
    const sortSelect = document.getElementById('sort-select');
    const orderSelect = document.getElementById('order-select');
    const mapSelect = document.getElementById('map-filter');

    if (sortSelect) {
        sortSelect.addEventListener('change', applyFilters);
    }
    if (orderSelect) {
        orderSelect.addEventListener('change', applyFilters);
    }
    if (mapSelect) {
        mapSelect.addEventListener('change', applyFilters);
    }
}

function applyFilters() {
    const sort = document.getElementById('sort-select')?.value || 'created_at';
    const order = document.getElementById('order-select')?.value || 'DESC';
    const map = document.getElementById('map-filter')?.value || '';

    const params = new URLSearchParams();
    params.set('sort', sort);
    params.set('order', order);
    if (map) params.set('map', map);

    window.location.href = `/videos?${params.toString()}`;
}

/* ── Reward Inputs ────────────────────────────────────────────────────── */
function initRewardInputs() {
    const addBtn = document.getElementById('add-reward-btn');
    if (!addBtn) return;

    addBtn.addEventListener('click', addRewardRow);

    // Load existing rewards from hidden input
    const existing = document.getElementById('rewards-data');
    if (existing && existing.value) {
        try {
            const rewards = JSON.parse(existing.value);
            rewards.forEach(r => addRewardChip(r.name, r.type));
        } catch(e) {}
    }
}

function addRewardRow() {
    const nameInput = document.getElementById('reward-name-input');
    const typeSelect = document.getElementById('reward-type-input');
    if (!nameInput || !nameInput.value.trim()) return;

    const name = nameInput.value.trim();
    const type = typeSelect?.value || 'item';

    addRewardChip(name, type);
    nameInput.value = '';
}

function addRewardChip(name, type) {
    const list = document.getElementById('reward-chips');
    if (!list) return;

    const chip = document.createElement('span');
    chip.className = 'reward-chip';
    chip.innerHTML = `
        <span class="reward-type-badge">${type}</span>
        ${escapeHtml(name)}
        <button type="button" onclick="this.parentElement.remove(); syncRewards();">&times;</button>
    `;
    list.appendChild(chip);
    syncRewards();
}

function syncRewards() {
    const chips = document.querySelectorAll('#reward-chips .reward-chip');
    const rewards = [];
    chips.forEach(chip => {
        const type = chip.querySelector('.reward-type-badge')?.textContent || 'item';
        const name = chip.childNodes[1]?.textContent?.trim() || '';
        rewards.push({ name, type });
    });

    const hiddenInput = document.getElementById('rewards-data');
    if (hiddenInput) {
        hiddenInput.value = JSON.stringify(rewards);
    }
}

/* ── Delete Confirmation ──────────────────────────────────────────────── */
function initDeleteButtons() {
    document.querySelectorAll('.btn-danger[data-delete-id]').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            e.preventDefault();
            const id = btn.dataset.deleteId;
            if (!confirm(_('confirmDelete'))) return;

            try {
                const resp = await fetch(`/api/videos/${id}`, { method: 'DELETE' });
                if (resp.ok) {
                    showToast(_('deleted'), 'success');
                    setTimeout(() => window.location.href = '/videos', 800);
                } else {
                    showToast(_('deleteFail'), 'error');
                }
            } catch(err) {
                showToast(_('deleteFailMsg') + err.message, 'error');
            }
        });
    });
}

/* ── wowhead Search ───────────────────────────────────────────────────── */
function initWowheadSearch() {
    const searchBtn = document.getElementById('wowhead-search-btn');
    const searchInput = document.getElementById('wowhead-search-input');
    if (!searchBtn || !searchInput) return;

    searchBtn.addEventListener('click', async () => {
        const q = searchInput.value.trim();
        if (!q) return;

        searchBtn.disabled = true;
        const resultsDiv = document.getElementById('wowhead-results');
        if (resultsDiv) resultsDiv.innerHTML = '<span class="loading-spinner"></span>';

        try {
            const resp = await fetch(`/api/wowhead/search?q=${encodeURIComponent(q)}`);
            const results = await resp.json();

            if (resultsDiv) {
                if (results.length === 0) {
                    resultsDiv.innerHTML = '<p class="text-muted">' + _('noResults') + '</p>';
                } else {
                    resultsDiv.innerHTML = results.slice(0, 5).map(r => `
                        <div class="wowhead-link" style="cursor:pointer"
                             onclick="document.getElementById('reward-name-input').value='${escapeHtml(r.name)}';document.getElementById('reward-type-input').value='${r.type}';addRewardRow();"
                             title="' + _('clickAdd') + '">
                            [${r.type}] ${escapeHtml(r.name)}
                        </div>
                    `).join('');
                }
            }
        } catch(err) {
            if (resultsDiv) resultsDiv.innerHTML = '<p class="text-muted">' + _('searchFail') + '</p>';
        } finally {
            searchBtn.disabled = false;
        }
    });
}

/* ── Utilities ────────────────────────────────────────────────────────── */
function showToast(message, type = '') {
    const existing = document.querySelector('.toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(10px)';
        toast.style.transition = '0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 2500);
}

function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

/* ── Liquid Glass Displacement Map Generation (Level 3) ─────────────── */
function generateDisplacementMap(size) {
    /* Generate a squircle-based displacement map.
       The map is a 512x512 PNG where R channel = X displacement,
       G channel = Y displacement, B = 0, A = 255.
       Center is neutral gray (128,128) - no displacement.
       Edges refract inward toward the center. */
    const canvas = document.createElement('canvas');
    canvas.width = size;
    canvas.height = size;
    const ctx = canvas.getContext('2d');
    const imageData = ctx.createImageData(size, size);
    const data = imageData.data;
    const cx = size / 2;
    const cy = size / 2;
    const maxRadius = size * 0.55;

    for (let y = 0; y < size; y++) {
        for (let x = 0; x < size; x++) {
            const idx = (y * size + x) * 4;
            const dx = x - cx;
            const dy = y - cy;
            const dist = Math.sqrt(dx * dx + dy * dy);
            const normalizedDist = Math.min(dist / maxRadius, 1);

            /* Squircle falloff for smoother glass-like refraction */
            const squircle = Math.pow(normalizedDist, 4) * 0.85;
            const falloff = normalizedDist < 0.9 ? squircle : squircle * (1 - (normalizedDist - 0.9) / 0.1);

            const angle = Math.atan2(dy, dx);
            /* Refract inward toward center */
            const refract = falloff * 70; /* Max 70px displacement */
            const rx = Math.cos(angle) * refract;
            const ry = Math.sin(angle) * refract;

            /* R channel: X displacement mapped 0..255; neutral=128 */
            data[idx] = Math.round(128 + rx);
            /* G channel: Y displacement mapped 0..255; neutral=128 */
            data[idx + 1] = Math.round(128 + ry);
            /* B channel: subtle edge highlight */
            data[idx + 2] = Math.round(falloff * 60);
            /* Alpha */
            data[idx + 3] = 255;
        }
    }
    ctx.putImageData(imageData, 0, 0);
    return canvas.toDataURL('image/png');
}

function initGlassRefraction() {
    /* Only activate SVG refraction on Chromium (Blink) browsers.
       Firefox/Safari either don't support feImage with data: URI
       or handle feDisplacementMap differently. They gracefully
       fall back to the @supports not rule in CSS. */
    const isChromium = !!(window.chrome && navigator.userAgentData &&
        navigator.userAgentData.brands?.some(b => b.brand.includes('Chromium')));

    if (!isChromium) return;

    const mapDataUrl = generateDisplacementMap(512);

    /* Inject the displacement map image into the SVG filter */
    const svg = document.querySelector('svg[aria-hidden="true"]');
    if (!svg) return;
    const defs = svg.querySelector('defs');
    if (!defs) return;

    const image = document.createElementNS('http://www.w3.org/2000/svg', 'image');
    image.setAttribute('id', 'lg-displacement');
    image.setAttribute('href', mapDataUrl);
    image.setAttribute('width', '512');
    image.setAttribute('height', '512');
    defs.appendChild(image);

    /* Activate displacement scales */
    const filter = document.getElementById('liquid-glass-refract');
    if (!filter) return;
    const maps = filter.querySelectorAll('feDisplacementMap');
    if (maps[0]) maps[0].setAttribute('scale', '8');
    if (maps[1]) maps[1].setAttribute('scale', '8');

    /* Add glass-refract class to eligible elements */
    document.querySelectorAll('.glass-panel, .glass-card, .glass-nav, .glass-btn, .glass-input').forEach(el => {
        el.classList.add('glass-refract');
    });
}

/* ── Glass Enter Animation Observer ──────────────────────────────────── */
function observeGlassEnter() {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('glass-enter-done');
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.1, rootMargin: '0px 0px -30px 0px' });

    document.querySelectorAll('.glass-panel, .glass-card, .video-card, .detail-meta-item, .item-entry').forEach(el => {
        el.classList.add('glass-enter');
        observer.observe(el);
    });
}

/* ── Nav Indicator (sliding active tab highlight) ────────────────────── */
function initNavIndicator() {
    const nav = document.querySelector('.bottom-nav');
    const indicator = nav?.querySelector('.nav-indicator');
    if (!nav || !indicator) return;

    const links = nav.querySelectorAll('a');

    function positionIndicator(target) {
        const navRect = nav.getBoundingClientRect();
        const linkRect = target.getBoundingClientRect();
        indicator.style.left = (linkRect.left - navRect.left) + 'px';
        indicator.style.width = linkRect.width + 'px';
    }

    // Position on initial active tab
    const activeLink = nav.querySelector('a.active') || links[0];
    if (activeLink) {
        // Double rAF: frame 1 = layout settle + set position (still invisible),
        //             frame 2 = reveal + enable transitions
        requestAnimationFrame(() => {
            positionIndicator(activeLink);
            requestAnimationFrame(() => {
                indicator.classList.add('ready');
            });
        });
    }

    // Reposition on window resize
    let resizeTimer;
    window.addEventListener('resize', () => {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(() => {
            const current = nav.querySelector('a.active') || links[0];
            if (current) positionIndicator(current);
        }, 100);
    });

    // Reposition on tab click, animate, then navigate
    links.forEach(link => {
        link.addEventListener('click', (e) => {
            // Already on this page — no navigation needed, just reposition
            if (link.classList.contains('active')) {
                positionIndicator(link);
                return;
            }

            const href = link.getAttribute('href');
            if (!href) return;

            e.preventDefault();
            positionIndicator(link);

            // Wait for CSS transition to finish before navigating;
            // shorter delay when prefers-reduced-motion is active
            const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
            const delay = prefersReducedMotion ? 80 : 520;

            setTimeout(() => {
                window.location.href = href;
            }, delay);
        });
    });
}
