// Định dạng VN tập trung + escapeHtml
const nf0 = new Intl.NumberFormat('vi-VN', { maximumFractionDigits: 0 });
const nf1 = new Intl.NumberFormat('vi-VN', { maximumFractionDigits: 1 });

export function escapeHtml(v) {
    if (v === null || v === undefined) return '';
    return String(v).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}
export const esc = escapeHtml;

export function formatNumber(v, digits = 0) {
    if (v === null || v === undefined || v === '') return '';
    const n = Number(v);
    if (Number.isNaN(n)) return escapeHtml(v);
    return digits ? nf1.format(n) : nf0.format(Math.round(n));
}
export function formatCurrency(v) {
    if (v === null || v === undefined || v === '') return '—';
    return formatNumber(v) + ' ₫';
}
export function formatVNDShort(v) {
    const n = Number(v) || 0;
    const a = Math.abs(n);
    if (a >= 1e9) return nf1.format(n / 1e9) + ' tỷ';
    if (a >= 1e6) return nf1.format(n / 1e6) + ' tr';
    if (a >= 1e3) return nf0.format(n / 1e3) + ' k';
    return nf0.format(n);
}
export function formatDate(v) {
    if (!v) return '';
    const s = String(v).slice(0, 10);
    const m = s.match(/^(\d{4})-(\d{2})-(\d{2})$/);
    if (!m) return escapeHtml(v);
    return `${m[3]}/${m[2]}/${m[1]}`;
}
export function formatDateTime(v) {
    if (!v) return '';
    const s = String(v);
    return formatDate(s.slice(0, 10)) + (s.length > 10 ? ' ' + s.slice(11, 16) : '');
}
export function toISODate(d) {
    const dt = d instanceof Date ? d : new Date(d);
    const z = (n) => String(n).padStart(2, '0');
    return `${dt.getFullYear()}-${z(dt.getMonth() + 1)}-${z(dt.getDate())}`;
}
export function daysUntil(dateStr) {
    if (!dateStr) return null;
    const d = new Date(String(dateStr).slice(0, 10) + 'T00:00:00');
    const t = new Date(); t.setHours(0, 0, 0, 0);
    return Math.round((d - t) / 86400000);
}
export function thangLabel(t, n) { return `T${t}/${n}`; }
export function initials(name) {
    return String(name || '').trim().split(/\s+/).slice(-2).map((p) => p[0] || '').join('').toUpperCase();
}
