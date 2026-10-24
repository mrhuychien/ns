// html`` template literal: giá trị ${} được escape, trừ khi bọc raw()
import { escapeHtml } from './format.js';

class Raw { constructor(s) { this.s = s; } toString() { return this.s; } }
export function raw(s) { return new Raw(s == null ? '' : String(s)); }
export function html(strings, ...vals) {
    let out = '';
    strings.forEach((s, i) => {
        out += s;
        if (i < vals.length) {
            const v = vals[i];
            if (v instanceof Raw) out += v.s;
            else if (Array.isArray(v)) out += v.map((x) => (x instanceof Raw ? x.s : escapeHtml(x))).join('');
            else if (v === null || v === undefined || v === false) out += '';
            else out += escapeHtml(v);
        }
    });
    return out;
}
export function el(sel, root = document) { return root.querySelector(sel); }
export function els(sel, root = document) { return Array.from(root.querySelectorAll(sel)); }
export function on(root, event, selector, handler) {
    root.addEventListener(event, (e) => {
        const t = e.target.closest(selector);
        if (t && root.contains(t)) handler(e, t);
    });
}
export function debounce(fn, ms = 250) {
    let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); };
}
export function skeleton(h = 120, n = 1) {
    return Array.from({ length: n }, () => `<div class="ns-skeleton" style="height:${h}px;margin-bottom:.75rem"></div>`).join('');
}
export function emptyState(icon, title, sub = '') {
    return `<div class="ns-empty"><div class="ns-empty-icon">${icon}</div><div class="ns-empty-title">${escapeHtml(title)}</div>${sub ? `<div>${escapeHtml(sub)}</div>` : ''}</div>`;
}
