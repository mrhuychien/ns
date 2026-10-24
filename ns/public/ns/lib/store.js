// Store nhỏ: cache theo key + sự kiện
const cache = new Map();
const listeners = new Map();
export const store = {
    get: (k) => cache.get(k),
    set(k, v) { cache.set(k, v); (listeners.get(k) || []).forEach((fn) => fn(v)); },
    del: (k) => cache.delete(k),
    clear: () => cache.clear(),
    on(k, fn) { listeners.set(k, [...(listeners.get(k) || []), fn]); return () => this.off(k, fn); },
    off(k, fn) { listeners.set(k, (listeners.get(k) || []).filter((f) => f !== fn)); },
};
export function pref(key, def) {
    try { const v = localStorage.getItem('ns_' + key); return v == null ? def : JSON.parse(v); } catch { return def; }
}
export function setPref(key, v) { try { localStorage.setItem('ns_' + key, JSON.stringify(v)); } catch { /* */ } }
