import { escapeHtml } from '../lib/format.js';

let onClose = null;
export function showModal({ title = '', body = '', footer = '', wide = false, closable = true } = {}) {
    const mount = document.getElementById('ns-modal-mount');
    if (!mount) return null;
    mount.innerHTML = `<div class="ns-modal-content${wide ? ' ns-modal-wide' : ''}">
        <div class="ns-modal-head"><div class="ns-modal-title">${escapeHtml(title)}</div>
        ${closable ? '<button class="ns-icon-btn" data-ns-close aria-label="Đóng">✕</button>' : ''}</div>
        <div class="ns-modal-body">${body}</div>
        ${footer ? `<div class="ns-modal-foot">${footer}</div>` : ''}</div>`;
    mount.classList.add('ns-show');
    document.body.style.overflow = 'hidden';
    const content = mount.querySelector('.ns-modal-content');
    mount.onclick = (e) => { if (closable && (e.target === mount || e.target.closest('[data-ns-close]'))) closeModal(); };
    return content;
}
export function closeModal() {
    const mount = document.getElementById('ns-modal-mount');
    if (!mount) return;
    mount.classList.remove('ns-show'); mount.innerHTML = ''; mount.onclick = null;
    document.body.style.overflow = '';
    if (onClose) { const fn = onClose; onClose = null; try { fn(); } catch (e) { console.error(e); } }
}
export function setModalCloseHandler(fn) { onClose = fn; }
export function confirmModal(title, text, { okLabel = 'Đồng ý', danger = false } = {}) {
    return new Promise((resolve) => {
        const c = showModal({
            title, body: `<p>${escapeHtml(text)}</p>`,
            footer: `<button class="ns-btn ns-btn-ghost" data-ns-close>Huỷ</button><button class="ns-btn ${danger ? 'ns-btn-danger' : 'ns-btn-primary'}" data-ok>${escapeHtml(okLabel)}</button>`,
        });
        setModalCloseHandler(() => resolve(false));
        c.querySelector('[data-ok]').onclick = () => { onClose = null; closeModal(); resolve(true); };
    });
}
