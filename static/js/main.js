/**
 * WoW Douyin Hub — WoW Theme
 * Client-side interactivity + SPA navigation (background video never reloads)
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
        videoUpdated: '影片已成功更新！',
        updateError: '錯誤：',
        unknownError: '未知錯誤',
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
        videoUpdated: 'Video updated successfully!',
        updateError: 'Error: ',
        unknownError: 'Unknown error',
    }
};

function _(key) {
    return (T[LANG] && T[LANG][key]) || (T['zh'][key]) || key;
}

document.addEventListener('DOMContentLoaded', () => {
    initThemeToggle();
    initSortSelects();
    initRewardInputs();
    initDeleteButtons();
    initWowheadSearch();
    initLangToggle();
    initGlassRefraction();
    observeGlassEnter();
    initNavIndicator();
    initEditVideoForm();
    initGlobalLinkInterceptor();
    initBackToTop();
    createSpinner();
});

/* ═══════════════════════════════════════════════════════════════════════
   SPA Navigation Engine
   ═══════════════════════════════════════════════════════════════════════ */

function navigateTo(url, pushState = true) {
    if (url === window.location.pathname + window.location.search) return;

    // Show loading spinner
    showSpinner();

    fetch(url)
        .then(resp => {
            if (!resp.ok) throw new Error('HTTP ' + resp.status);
            return resp.text();
        })
        .then(html => {
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');
            const newContent = doc.querySelector('#app-content');
            const newTitle = doc.querySelector('title')?.textContent;

            if (!newContent) {
                // Fallback: full page reload if response has no #app-content
                window.location.href = url;
                return;
            }

            document.getElementById('app-content').innerHTML = newContent.innerHTML;

            if (newTitle) document.title = newTitle;

            // Update lang if it changed
            const newLang = doc.documentElement.dataset.lang;
            if (newLang && newLang !== document.documentElement.dataset.lang) {
                document.documentElement.dataset.lang = newLang;
                // Re-parse T object with new lang (LANG is re-read on next access)
                // Note: LANG const can't be changed, but page scripts that use _() will work
            }

            if (pushState) {
                history.pushState({ url }, '', url);
            }

            // Update bottom nav active state based on new URL
            updateNavActive(url);

            // Re-initialize page-specific scripts
            reinitPageScripts();

            hideSpinner();

            window.scrollTo({ top: 0, behavior: 'instant' });
        })
        .catch(() => {
            hideSpinner();
            // On error, fallback to full navigation
            window.location.href = url;
        });
}

function initGlobalLinkInterceptor() {
    document.addEventListener('click', (e) => {
        const link = e.target.closest('a');
        if (!link) return;

        const href = link.getAttribute('href');
        if (!href) return;

        // Skip external links, anchors, javascript, data-no-spa
        if (href.startsWith('http://') || href.startsWith('https://')) return;
        if (href.startsWith('#') || href.startsWith('javascript:')) return;
        if (link.getAttribute('data-no-spa') !== null) return;
        if (link.getAttribute('target') === '_blank') return;

        // Already handled by bottom nav (preventDefault already called there)
        if (link.closest('.bottom-nav')) return;

        // Skip if default was already prevented by another handler
        if (e.defaultPrevented) return;

        e.preventDefault();
        navigateTo(href);
    });
}

function updateNavActive(url) {
    // Normalize URL: resolve relative paths to absolute pathname
    let absUrl;
    try {
        absUrl = new URL(url, window.location.href).pathname;
    } catch (e) {
        absUrl = url;
    }

    const navLinks = document.querySelectorAll('.bottom-nav a');
    navLinks.forEach(link => {
        const href = link.getAttribute('href');
        // Resolve relative href to absolute pathname for comparison
        let absHref;
        try {
            absHref = new URL(href, window.location.href).pathname;
        } catch (e) {
            absHref = href;
        }

        if (absHref === '/') {
            link.classList.toggle('active', absUrl === '/');
        } else {
            link.classList.toggle('active', absUrl === absHref || absUrl.startsWith(absHref + '/'));
        }
    });

    // Reposition indicator
    const nav = document.querySelector('.bottom-nav');
    const indicator = nav?.querySelector('.nav-indicator');
    if (!nav || !indicator) return;

    const activeLink = nav.querySelector('a.active');
    if (!activeLink) return;

    const navRect = nav.getBoundingClientRect();
    const linkRect = activeLink.getBoundingClientRect();
    const x = linkRect.left - navRect.left;

    indicator.classList.remove('ready');
    indicator.style.transition = 'none';
    indicator.style.width = linkRect.width + 'px';
    indicator.style.transform = `translate3d(${x}px, 0, 0)`;
    void indicator.offsetWidth;
    indicator.style.transition = '';
    requestAnimationFrame(() => indicator.classList.add('ready'));
}


/* ═══════════════════════════════════════════════════════════════════════
   Page Scripts Reinitialization Hub
   Called after every SPA content swap
   ═══════════════════════════════════════════════════════════════════════ */

function reinitPageScripts() {
    initSortSelects();
    initRewardInputs();
    initDeleteButtons();
    initWowheadSearch();
    observeGlassEnter();
    initEditVideoForm();
    initPaginationLinks();
}


/* ═══════════════════════════════════════════════════════════════════════
   Sort / Filter Auto-submit
   ═══════════════════════════════════════════════════════════════════════ */

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

    navigateTo(`/videos?${params.toString()}`);
}


/* ═══════════════════════════════════════════════════════════════════════
   Reward Inputs
   ═══════════════════════════════════════════════════════════════════════ */

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
        <span class="reward-type-badge">${escapeHtml(type)}</span>
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
        const typeBadge = chip.querySelector('.reward-type-badge');
        const type = typeBadge ? typeBadge.textContent : 'item';
        const textNodes = Array.from(chip.childNodes).filter(n => n.nodeType === 3);
        const name = textNodes.map(n => n.textContent.trim()).join('').replace(/×$/, '').trim();
        if (name) rewards.push({ name, type });
    });

    const hiddenInput = document.getElementById('rewards-data');
    if (hiddenInput) {
        hiddenInput.value = JSON.stringify(rewards);
    }
}


/* ═══════════════════════════════════════════════════════════════════════
   Delete Confirmation
   ═══════════════════════════════════════════════════════════════════════ */

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
                    setTimeout(() => navigateTo('/videos'), 800);
                } else {
                    showToast(_('deleteFail'), 'error');
                }
            } catch(err) {
                showToast(_('deleteFailMsg') + err.message, 'error');
            }
        });
    });
}


/* ═══════════════════════════════════════════════════════════════════════
   wowhead Search
   ═══════════════════════════════════════════════════════════════════════ */

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
                    resultsDiv.innerHTML = '';
                    results.slice(0, 5).forEach(r => {
                        const item = document.createElement('button');
                        item.type = 'button';
                        item.className = 'wowhead-link';
                        item.style.cursor = 'pointer';
                        item.title = _('clickAdd');
                        item.textContent = `[${r.type}] ${r.name}`;
                        item.addEventListener('click', () => {
                            const rewardNameInput = document.getElementById('reward-name-input');
                            const rewardTypeInput = document.getElementById('reward-type-input');
                            if (rewardNameInput) rewardNameInput.value = r.name || '';
                            if (rewardTypeInput) rewardTypeInput.value = r.type || 'item';
                            addRewardRow();
                        });
                        resultsDiv.appendChild(item);
                    });
                }
            }
        } catch(err) {
            if (resultsDiv) resultsDiv.innerHTML = '<p class="text-muted">' + _('searchFail') + '</p>';
        } finally {
            searchBtn.disabled = false;
        }
    });
}


/* ═══════════════════════════════════════════════════════════════════════
   Edit Video Form
   (extracted from edit_video.html inline <script>)
   ═══════════════════════════════════════════════════════════════════════ */

function initEditVideoForm() {
    const form = document.getElementById('edit-video-form');
    if (!form) return;

    form.addEventListener('submit', async function(e) {
        e.preventDefault();

        const chips = document.querySelectorAll('#reward-chips .reward-chip');
        const rewards = [];
        chips.forEach(chip => {
            const typeBadge = chip.querySelector('.reward-type-badge');
            const type = typeBadge ? typeBadge.textContent : 'item';
            const textNodes = Array.from(chip.childNodes).filter(n => n.nodeType === 3);
            const name = textNodes.map(n => n.textContent.trim()).join('').replace(/×$/, '').trim();
            if (name) rewards.push({ name, type });
        });

        const videoIdInput = document.querySelector('[name="video_id"]');
        const videoId = videoIdInput ? videoIdInput.value : null;
        if (!videoId) {
            showToast(_('updateError') + _('unknownError'), 'error');
            return;
        }

        const formData = new FormData(this);
        const data = Object.fromEntries(formData.entries());
        data.rewards = rewards;

        try {
            const resp = await fetch('/api/videos/' + videoId, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            const result = await resp.json();

            if (resp.ok) {
                showToast(_('videoUpdated'), 'success');
                setTimeout(() => navigateTo('/videos/' + videoId), 500);
            } else {
                showToast(_('updateError') + (result.error || _('unknownError')), 'error');
            }
        } catch(err) {
            showToast(_('updateError') + err.message, 'error');
        }
    });
}


/* ═══════════════════════════════════════════════════════════════════════
   Utilities
   ═══════════════════════════════════════════════════════════════════════ */

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

function initLangToggle() {
    const toggle = document.querySelector('.lang-toggle');
    if (!toggle) return;
    toggle.addEventListener('click', () => {
        toggle.style.transform = 'scale(0.96)';
        setTimeout(() => {
            toggle.style.transform = '';
        }, 120);
    });
}


/* ═══════════════════════════════════════════════════════════════════════
   Liquid Glass Displacement Map Generation (Level 3)
   ═══════════════════════════════════════════════════════════════════════ */

function generateDisplacementMap(size) {
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

            const squircle = Math.pow(normalizedDist, 4) * 0.85;
            const falloff = normalizedDist < 0.9 ? squircle : squircle * (1 - (normalizedDist - 0.9) / 0.1);

            const angle = Math.atan2(dy, dx);
            const refract = falloff * 70;
            const rx = Math.cos(angle) * refract;
            const ry = Math.sin(angle) * refract;

            data[idx] = Math.round(128 + rx);
            data[idx + 1] = Math.round(128 + ry);
            data[idx + 2] = Math.round(falloff * 60);
            data[idx + 3] = 255;
        }
    }
    ctx.putImageData(imageData, 0, 0);
    return canvas.toDataURL('image/png');
}

function initGlassRefraction() {
    const isChromium = !!(window.chrome && navigator.userAgentData &&
        navigator.userAgentData.brands?.some(b => b.brand.includes('Chromium')));

    if (!isChromium) return;

    const mapDataUrl = generateDisplacementMap(512);

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

    const filter = document.getElementById('liquid-glass-refract');
    if (!filter) return;
    const maps = filter.querySelectorAll('feDisplacementMap');
    if (maps[0]) maps[0].setAttribute('scale', '8');
    if (maps[1]) maps[1].setAttribute('scale', '8');

    document.querySelectorAll('.glass-panel, .glass-card, .glass-nav, .glass-btn, .glass-input').forEach(el => {
        el.classList.add('glass-refract');
    });
}


/* ═══════════════════════════════════════════════════════════════════════
   Glass Enter Animation Observer
   ═══════════════════════════════════════════════════════════════════════ */

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


/* ═══════════════════════════════════════════════════════════════════════
   Nav Indicator (sliding active tab highlight + SPA navigation)
   ═══════════════════════════════════════════════════════════════════════ */

function initNavIndicator() {
    const nav = document.querySelector('.bottom-nav');
    const indicator = nav?.querySelector('.nav-indicator');
    if (!nav || !indicator) return;

    const links = Array.from(nav.querySelectorAll('a'));

    function positionIndicator(target, animate = true) {
        const navRect = nav.getBoundingClientRect();
        const linkRect = target.getBoundingClientRect();
        const x = linkRect.left - navRect.left;

        if (!animate) {
            indicator.classList.remove('ready');
            indicator.style.transition = 'none';
        }

        indicator.style.width = linkRect.width + 'px';
        indicator.style.transform = `translate3d(${x}px, 0, 0)`;

        if (!animate) {
            void indicator.offsetWidth;
            indicator.style.transition = '';
            requestAnimationFrame(() => indicator.classList.add('ready'));
        }
    }

    const activeLink = nav.querySelector('a.active') || links[0];
    if (activeLink) {
        positionIndicator(activeLink, false);
    }

    let resizeTimer;
    window.addEventListener('resize', () => {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(() => {
            const current = nav.querySelector('a.active') || links[0];
            if (current) positionIndicator(current, false);
        }, 100);
    });

    links.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation(); // prevent global interceptor from double-firing

            const href = link.getAttribute('href');
            if (!href || href === window.location.pathname + window.location.search) return;

            links.forEach(item => item.classList.toggle('active', item === link));
            positionIndicator(link, true);

            const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
            const delay = prefersReducedMotion ? 80 : 520;

            setTimeout(() => {
                navigateTo(href);
            }, delay);
        });
    });
}

window.addEventListener('popstate', (event) => {
    const url = window.location.pathname + window.location.search;
    // Fetch and replace content without pushing state again
    showSpinner();
    fetch(url)
        .then(resp => {
            if (!resp.ok) throw new Error('HTTP ' + resp.status);
            return resp.text();
        })
        .then(html => {
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');
            const newContent = doc.querySelector('#app-content');
            const newTitle = doc.querySelector('title')?.textContent;

            if (newContent) {
                document.getElementById('app-content').innerHTML = newContent.innerHTML;
            }
            if (newTitle) document.title = newTitle;

            const newLang = doc.documentElement.dataset.lang;
            if (newLang && newLang !== document.documentElement.dataset.lang) {
                document.documentElement.dataset.lang = newLang;
            }

            updateNavActive(url);
            reinitPageScripts();
            hideSpinner();
            window.scrollTo({ top: 0, behavior: 'instant' });
        })
        .catch(() => {
            hideSpinner();
            window.location.href = url;
        });
});


/* ═══════════════════════════════════════════════════════════════════════
   Theme Toggle (dark / light / auto)
   ═══════════════════════════════════════════════════════════════════════ */

function initThemeToggle() {
    const btn = document.getElementById('theme-toggle');
    if (!btn) return;

    // Read persisted theme or default to 'auto'
    let theme = localStorage.getItem('lg-theme') || 'auto';
    applyTheme(theme);
    updateThemeIcon(theme);

    btn.addEventListener('click', () => {
        // Cycle: auto → dark → light → auto
        if (theme === 'auto') theme = 'dark';
        else if (theme === 'dark') theme = 'light';
        else theme = 'auto';

        localStorage.setItem('lg-theme', theme);
        applyTheme(theme);
        updateThemeIcon(theme);
    });
}

function applyTheme(theme) {
    if (theme === 'auto') {
        document.documentElement.removeAttribute('data-theme');
    } else {
        document.documentElement.setAttribute('data-theme', theme);
    }
}

function updateThemeIcon(theme) {
    const btn = document.getElementById('theme-toggle');
    if (!btn) return;
    if (theme === 'auto') btn.textContent = '◐';
    else if (theme === 'dark') btn.textContent = '☾';
    else btn.textContent = '☼';
    btn.title = theme === 'auto'
        ? (LANG === 'zh' ? '跟隨系統' : 'Auto')
        : theme === 'dark'
            ? (LANG === 'zh' ? '深色模式' : 'Dark Mode')
            : (LANG === 'zh' ? '淺色模式' : 'Light Mode');
}


/* ═══════════════════════════════════════════════════════════════════════
   SPA Loading Spinner
   ═══════════════════════════════════════════════════════════════════════ */

function createSpinner() {
    if (document.getElementById('spa-spinner')) return;

    const overlay = document.createElement('div');
    overlay.id = 'spa-spinner';
    overlay.className = 'spa-spinner-overlay';
    overlay.innerHTML = '<div class="spa-spinner-ring"></div>';
    document.body.appendChild(overlay);
}

function showSpinner() {
    const spinner = document.getElementById('spa-spinner');
    if (!spinner) { createSpinner(); }
    // Small delay to avoid flash on instant navigations
    const el = document.getElementById('spa-spinner');
    if (el) {
        clearTimeout(el._showTimer);
        el._showTimer = setTimeout(() => {
            el.classList.add('active');
        }, 150);
    }
}

function hideSpinner() {
    const el = document.getElementById('spa-spinner');
    if (el) {
        clearTimeout(el._showTimer);
        el.classList.remove('active');
    }
}


/* ═══════════════════════════════════════════════════════════════════════
   Back to Top Button
   ═══════════════════════════════════════════════════════════════════════ */

function initBackToTop() {
    // Remove any existing button (from previous SPA navigation)
    const existing = document.getElementById('back-to-top');
    if (existing) return; // Don't re-create; scroll handler persists

    const btn = document.createElement('button');
    btn.id = 'back-to-top';
    btn.className = 'back-to-top';
    btn.innerHTML = '&#9650;';
    btn.title = LANG === 'zh' ? '回到頂部' : 'Back to Top';
    btn.setAttribute('aria-label', LANG === 'zh' ? '回到頂部' : 'Back to Top');
    document.body.appendChild(btn);

    btn.addEventListener('click', () => {
        const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        window.scrollTo({
            top: 0,
            behavior: prefersReducedMotion ? 'instant' : 'smooth'
        });
    });

    // Scroll handler (throttled)
    let ticking = false;
    window.addEventListener('scroll', () => {
        if (ticking) return;
        ticking = true;
        requestAnimationFrame(() => {
            const el = document.getElementById('back-to-top');
            if (el) {
                el.classList.toggle('visible', window.scrollY > 500);
            }
            ticking = false;
        });
    }, { passive: true });
}


/* ═══════════════════════════════════════════════════════════════════════
   Pagination Links — build URL from filter bar state
   ═══════════════════════════════════════════════════════════════════════ */

function initPaginationLinks() {
    document.querySelectorAll('.pagination-btn[data-page]').forEach(btn => {
        btn.addEventListener('click', e => {
            e.preventDefault();
            const page = btn.getAttribute('data-page');
            const sort = document.getElementById('sort-select')?.value || 'created_at';
            const order = document.getElementById('order-select')?.value || 'DESC';
            const map = document.getElementById('map-filter')?.value || '';
            const q = document.getElementById('video-search')?.value || '';

            const params = new URLSearchParams();
            params.set('page', page);
            params.set('sort', sort);
            params.set('order', order);
            if (map) params.set('map', map);
            if (q) params.set('q', q);

            navigateTo(`/videos?${params.toString()}`);
        });
    });
}

/* ─── Waypoint Copy ──────────────────────────────────────────────────── */
function copyWay(btn) {
    const text = btn.getAttribute('data-way');
    const lang = document.documentElement.getAttribute('data-lang');
    const doneText = lang === 'en' ? '✓ Copied!' : '✓ 已複製';
    navigator.clipboard.writeText(text).then(() => {
        btn.classList.add('copied');
        btn.textContent = doneText;
        setTimeout(() => {
            btn.classList.remove('copied');
            btn.textContent = text;
        }, 1500);
    }).catch(() => {
        const ta = document.createElement('textarea');
        ta.value = text;
        ta.style.position = 'fixed';
        ta.style.opacity = '0';
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
        btn.classList.add('copied');
        btn.textContent = doneText;
        setTimeout(() => {
            btn.classList.remove('copied');
            btn.textContent = text;
        }, 1500);
    });
}
