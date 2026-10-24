// Hash router: '#/nv/:name?tab=x' → { path, params, query }
const routes = [];
let notFound = null;

export function route(pattern, handler) {
    const keys = [];
    const re = new RegExp('^' + pattern.replace(/\//g, '\\/').replace(/:(\w+)/g, (_, k) => { keys.push(k); return '([^\\/]+)'; }) + '\\/?$');
    routes.push({ re, keys, handler, pattern });
}
export function setNotFound(fn) { notFound = fn; }

export function parseHash(hash = location.hash) {
    let h = hash.replace(/^#/, '') || '/';
    if (!h.startsWith('/')) h = '/' + h;
    const [path, qs = ''] = h.split('?');
    const query = {};
    new URLSearchParams(qs).forEach((v, k) => { query[k] = v; });
    return { path, query };
}

export function navigate(path, replace = false) {
    const target = '#' + (path.startsWith('/') ? path : '/' + path);
    if (replace) history.replaceState(null, '', target); else location.hash = target.slice(1);
    if (replace) dispatch();
}
export function replaceQuery(query) {
    const { path } = parseHash();
    const qs = new URLSearchParams(Object.entries(query).filter(([, v]) => v !== '' && v != null)).toString();
    history.replaceState(null, '', '#' + path + (qs ? '?' + qs : ''));
}

export function dispatch() {
    const { path, query } = parseHash();
    for (const r of routes) {
        const m = path.match(r.re);
        if (m) {
            const params = {};
            r.keys.forEach((k, i) => { params[k] = decodeURIComponent(m[i + 1]); });
            return r.handler({ path, params, query });
        }
    }
    // Self-heal: route lạ có thể do shell cũ → reload 1 lần (cờ theo path)
    const flag = 'ns_reload:' + path;
    if (!sessionStorage.getItem(flag)) { sessionStorage.setItem(flag, '1'); location.reload(); return; }
    sessionStorage.removeItem(flag);
    if (notFound) notFound({ path, query }); else navigate('/', true);
}
export function start() { window.addEventListener('hashchange', dispatch); dispatch(); }
