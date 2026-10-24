import { escapeHtml } from '../lib/format.js';

const ICON = {
    hd_het_han: '📄', kham_sk_het_han: '🩺', attp_het_han: '🍽️', thieu_cccd: '🪪', thieu_bo_phan: '🏷️',
    thieu_ma_may: '🖐️', thieu_luong_cb: '💵', thieu_tk: '🏦', bhxh_rui_ro: '🛡️', bhxh_chua_muc: '🛡️',
    sinh_nhat: '🎂', luong_thieu_phieu: '🧾', luong_con_nhap: '📝', luong_trung: '⚠️',
};
export function icon(ma) { return ICON[ma] || '•'; }
export function badgeMuc(muc) { return muc === 'do' ? 'danger' : muc === 'vang' ? 'warning' : 'success'; }
export function canhBaoIcons(list, max = 4) {
    if (!list || !list.length) return '<span class="ns-text-muted">—</span>';
    const sh = list.slice(0, max);
    return `<span class="ns-cb-icons">${sh.map((c) => `<span class="ns-cb ns-cb-${c.muc}" title="${escapeHtml(c.ten)}${c.chi_tiet ? ' — ' + escapeHtml(c.chi_tiet) : ''}">${icon(c.ma)}</span>`).join('')}${list.length > max ? `<span class="ns-cb ns-cb-more">+${list.length - max}</span>` : ''}</span>`;
}
export function canhBaoList(list) {
    if (!list || !list.length) return '';
    return `<div class="ns-cb-list">${list.map((c) => `<span class="ns-badge ns-badge-${badgeMuc(c.muc)}">${icon(c.ma)} ${escapeHtml(c.ten)}${c.chi_tiet ? ` · ${escapeHtml(c.chi_tiet)}` : ''}</span>`).join('')}</div>`;
}
