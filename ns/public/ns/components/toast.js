import { escapeHtml } from '../lib/format.js';

export function showToast(msg, type = 'info', ms = 3500) {
    const mount = document.getElementById('ns-toast-mount');
    if (!mount) { console.log('[toast]', type, msg); return; }
    const t = document.createElement('div');
    t.className = `ns-toast ns-${type}`;
    t.innerHTML = escapeHtml(msg).replace(/\n/g, '<br>');
    mount.appendChild(t);
    setTimeout(() => { t.style.animation = 'nsToastOut .25s ease forwards'; setTimeout(() => t.remove(), 260); }, ms);
}
export function showLoading(text = 'Đang xử lý…') {
    const m = document.getElementById('ns-loading-mount');
    if (!m) return;
    const tx = m.querySelector('.ns-loading-text'); if (tx) tx.textContent = text;
    m.hidden = false;
}
export function hideLoading() { const m = document.getElementById('ns-loading-mount'); if (m) m.hidden = true; }
export async function withLoading(fn, text) {
    showLoading(text);
    try { return await fn(); } finally { hideLoading(); }
}
