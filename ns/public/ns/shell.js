// Shell SPA /ns — hash router, header, bottom-nav, view code-split
import { route, setNotFound, start, navigate, parseHash } from './lib/router.js';
import { escapeHtml } from './lib/format.js';
import { showToast } from './components/toast.js';
import { closeModal } from './components/modal.js';

const BUILD = 'ns-r1'; // PHẢI khớp SHELL_BUILD trong www/ns.py
const CTX = window.NS_CONTEXT || {};
console.log(`[NS] shell build=${BUILD}`);
window.NS_APP = { build: BUILD, ctx: CTX, navigate };

const withV = (p) => `${p}?v=${encodeURIComponent(CTX.assetVersion || Date.now())}`;
const VIEW_MODULES = {
    danh_sach: () => import(withV('./views/danh_sach.js')),
    ho_so: () => import(withV('./views/ho_so.js')),
    bo_sung: () => import(withV('./views/bo_sung.js')),
    luong: () => import(withV('./views/luong.js')),
    viec: () => import(withV('./views/viec.js')),
};

const NAV = [
    { key: 'danh_sach', href: '#/', icon: '👥', label: 'Nhân sự', match: (p) => p === '/' || p.startsWith('/nv') },
    { key: 'bo_sung', href: '#/bo-sung', icon: '📝', label: 'Bổ sung', match: (p) => p.startsWith('/bo-sung') },
    { key: 'luong', href: '#/luong', icon: '💰', label: 'Lương', match: (p) => p.startsWith('/luong') },
    { key: 'viec', href: '#/viec', icon: '✅', label: 'Việc', match: (p) => p.startsWith('/viec') },
    { key: 'chamcong', href: '/chamcong2', icon: '🕒', label: 'Chấm công', match: () => false, external: true },
];

const viewEl = () => document.getElementById('ns-view');
let current = null; // { key, cleanup }

function renderHeader(title, { back = false, actions = '' } = {}) {
    const h = document.getElementById('ns-header');
    if (!h) return;
    h.innerHTML = `
        ${back ? '<button class="ns-icon-btn" id="ns-back" aria-label="Quay lại">←</button>' : '<span class="ns-logo">NS</span>'}
        <div class="ns-header-title">${escapeHtml(title)}</div>
        <div class="ns-header-actions">${actions}
            <nav class="ns-desktop-nav">${NAV.map((n) => `<a href="${n.href}" data-nav="${n.key}">${n.icon} ${n.label}</a>`).join('')}</nav>
            <button class="ns-icon-btn" id="ns-refresh" aria-label="Làm mới" title="Làm mới">↻</button>
            <button class="ns-icon-btn" id="ns-acct" aria-label="Tài khoản" title="${escapeHtml(CTX.full_name || CTX.user || '')}">👤</button>
        </div>`;
    const b = h.querySelector('#ns-back'); if (b) b.onclick = () => (history.length > 1 ? history.back() : navigate('/'));
    h.querySelector('#ns-refresh').onclick = () => dispatchCurrent(true);
    h.querySelector('#ns-acct').onclick = toggleAcct;
    markActive();
}
function renderNav() {
    const n = document.getElementById('ns-nav');
    if (!n) return;
    n.innerHTML = NAV.map((x) => `<a class="ns-nav-item" href="${x.href}" data-nav="${x.key}"><span class="ns-nav-icon">${x.icon}</span><span>${x.label}</span></a>`).join('');
    markActive();
}
function markActive() {
    const { path } = parseHash();
    document.querySelectorAll('[data-nav]').forEach((a) => {
        const n = NAV.find((x) => x.key === a.dataset.nav);
        a.classList.toggle('ns-active', !!(n && n.match(path)));
    });
}
function toggleAcct() {
    let m = document.getElementById('ns-acct-menu');
    if (m) { m.remove(); return; }
    m = document.createElement('div'); m.id = 'ns-acct-menu'; m.className = 'ns-acct-menu';
    m.innerHTML = `<div class="ns-acct-name">${escapeHtml(CTX.full_name || CTX.user)}</div>
        <div class="ns-acct-sub">${escapeHtml(CTX.user)}${CTX.isManager ? ' · HR Manager' : ''}</div>
        <a class="ns-acct-link" href="/app/employee">Mở ERPNext (Desk)</a>
        <a class="ns-acct-link" href="/chamcong2">Chấm công</a>
        <button class="ns-acct-logout" id="ns-logout">Đăng xuất</button>`;
    document.body.appendChild(m);
    m.querySelector('#ns-logout').onclick = () => { location.href = '/?cmd=web_logout'; };
    setTimeout(() => document.addEventListener('click', (e) => { if (!m.contains(e.target) && e.target.id !== 'ns-acct') m.remove(); }, { once: true }), 0);
}

let lastCtx = null;
async function show(key, ctx) {
    lastCtx = { key, ctx };
    closeModal();
    const container = viewEl();
    if (current && current.cleanup) try { current.cleanup(); } catch (e) { console.error(e); }
    container.innerHTML = '<div class="ns-skeleton" style="height:200px"></div>';
    container.scrollTop = 0; window.scrollTo(0, 0);
    try {
        const mod = await VIEW_MODULES[key]();
        const cleanup = await mod.render({ container, ...ctx, setHeader: renderHeader });
        current = { key, cleanup: typeof cleanup === 'function' ? cleanup : null };
    } catch (e) {
        console.error(e);
        container.innerHTML = `<div class="ns-card ns-risk-bar"><strong>Lỗi tải màn hình:</strong> ${escapeHtml(e.message || e)}</div>`;
        showToast(e.message || 'Lỗi tải màn hình', 'error');
    }
    markActive();
}
function dispatchCurrent(force) { if (lastCtx) show(lastCtx.key, { ...lastCtx.ctx, force: !!force }); }

route('/', ({ query }) => show('danh_sach', { query }));
route('/nv/:name', ({ params, query }) => show('ho_so', { params, query }));
route('/bo-sung', ({ query }) => show('bo_sung', { query }));
route('/luong', ({ query }) => show('luong', { query }));
route('/viec', ({ query }) => show('viec', { query }));
route('/chamcong', () => { window.location.href = '/chamcong2'; });
setNotFound(() => navigate('/', true));

renderNav();
window.addEventListener('hashchange', markActive);

// Trang mặc định: #/viec nếu có việc đỏ (hết hạn), còn không #/
(async function boot() {
    if (!location.hash || location.hash === '#' || location.hash === '#/') {
        try {
            const { ns } = await import('./lib/api.js');
            const v = await ns.viec();
            if (v && v.co_do) { history.replaceState(null, '', '#/viec'); }
        } catch (e) { console.warn('[NS] viec boot', e); }
    }
    start();
})();
