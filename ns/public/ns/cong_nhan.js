// Trang /phieuluong — công nhân tự xem phiếu lương của CHÍNH MÌNH (ns.api.cong_nhan).
//
// Quyền kiểm ở server mọi lần gọi: nhân viên suy từ phiên đăng nhập, trình duyệt không gửi mã nhân viên (trừ HR
// xem thay qua ?nv=, server kiểm quyền HR). Phiếu vẽ bằng đúng component của màn nhân sự (components/phieu_luong.js)
// → công nhân và phòng nhân sự nhìn cùng một con số.
//
// Chọn tháng: ‹ › hoặc danh sách; tháng đang xem ghi lên địa chỉ (#2026-10) để tải lại / gửi link vẫn đúng tháng.
import { call } from './lib/api.js';
import { escapeHtml as esc } from './lib/format.js';
import { phieuLuongHtml } from './components/phieu_luong.js';

const BUILD = 'ns-cn1'; // PHẢI khớp SHELL_BUILD trong www/phieuluong.py
const CTX = window.NS_CONTEXT || {};
window.NS_CN = { build: BUILD };
console.log(`[NS] cong_nhan build=${BUILD}`);

const view = document.getElementById('cn-view');
const st = { thang: [], i: 0, cache: new Map(), info: null };
const khoa = (x) => `${x.nam}-${String(x.thang).padStart(2, '0')}`;
const thamSo = (a = {}) => (CTX.xemThay ? { ...a, employee: CTX.employee } : a);

function toast(msg) {
    const m = document.getElementById('ns-toast-mount');
    if (!m) return;
    const t = document.createElement('div');
    t.className = 'ns-toast ns-error';
    t.textContent = msg;
    m.appendChild(t);
    setTimeout(() => t.remove(), 4000);
}

// ── menu tài khoản: đổi mật khẩu / đăng xuất ──
function moMenu() {
    let m = document.getElementById('ns-acct-menu');
    if (m) { m.remove(); return; }
    m = document.createElement('div');
    m.id = 'ns-acct-menu';
    m.className = 'ns-acct-menu';
    m.innerHTML = `<div class="ns-acct-name">${esc(CTX.full_name || CTX.user)}</div>
        <div class="ns-acct-sub">${esc(CTX.user)}</div>
        <a class="ns-acct-link" href="/update-password">🔑 Đổi mật khẩu</a>
        ${CTX.laHr ? '<a class="ns-acct-link" href="/ns">Về trang Nhân sự</a>' : ''}
        <button class="ns-acct-logout" id="cn-logout">Đăng xuất</button>`;
    document.body.appendChild(m);
    m.querySelector('#cn-logout').onclick = dangXuat;
    setTimeout(() => document.addEventListener('click', (e) => {
        if (!m.contains(e.target) && e.target.id !== 'cn-menu-btn') m.remove();
    }, { once: true }), 0);
}
async function dangXuat() {
    try {
        const res = await fetch('/api/method/logout', {
            method: 'POST', credentials: 'same-origin',
            headers: { 'X-Frappe-CSRF-Token': CTX.csrfToken || '', Accept: 'application/json' },
        });
        if (!res.ok && res.status !== 401) throw new Error(`HTTP ${res.status}`);
    } catch (e) {
        toast('Chưa đăng xuất được — kiểm tra mạng rồi thử lại.');
        return;
    }
    window.location.href = '/login?redirect-to=%2Fphieuluong';
}
const nutMenu = document.getElementById('cn-menu-btn');
if (nutMenu) nutMenu.onclick = moMenu;

// ── khung trang ──
function veKhung() {
    const x = st.thang[st.i];
    view.innerHTML = `
        ${CTX.xemThay ? `<div class="ns-risk-bar ns-info-bar"><span>Phòng nhân sự đang <b>xem như công nhân</b>: ${esc(CTX.employeeName)} · ${esc(CTX.employee)}</span></div>` : ''}
        <div class="ns-cn-chao"><div class="ns-cn-ten">${esc(CTX.employeeName || '')}</div>
            <div class="ns-cn-phu">${esc(CTX.employee || '')}${CTX.department ? ` · ${esc(CTX.department)}` : ''}</div></div>
        <div class="ns-cn-thang">
            <button class="ns-icon-btn ns-cn-lui" id="cn-lui" aria-label="Tháng trước" ${st.i >= st.thang.length - 1 ? 'disabled' : ''}>‹</button>
            <select class="ns-input ns-cn-chon" id="cn-chon" aria-label="Chọn tháng">${st.thang.map((t, i) => `<option value="${i}" ${i === st.i ? 'selected' : ''}>Tháng ${t.thang}/${t.nam}${t.tam_tinh ? ' · tạm tính' : ''}</option>`).join('')}</select>
            <button class="ns-icon-btn ns-cn-toi" id="cn-toi" aria-label="Tháng sau" ${st.i <= 0 ? 'disabled' : ''}>›</button>
        </div>
        <div id="cn-phieu" class="ns-card ns-cn-phieu" aria-live="polite"><div class="ns-skeleton" style="height:220px"></div></div>
        <div class="ns-cn-chan">Thắc mắc về lương: liên hệ phòng nhân sự. Phiếu chỉ hiện sau khi phòng lương duyệt.</div>`;
    view.querySelector('#cn-lui').onclick = () => chon(st.i + 1);
    view.querySelector('#cn-toi').onclick = () => chon(st.i - 1);
    view.querySelector('#cn-chon').onchange = (e) => chon(Number(e.target.value));
    taiPhieu(x);
}

function chon(i) {
    if (i < 0 || i >= st.thang.length || i === st.i) return;
    st.i = i;
    history.replaceState(null, '', `${location.pathname}${location.search}#${khoa(st.thang[i])}`);
    veKhung();
}

async function taiPhieu(x) {
    const k = khoa(x);
    const o = view.querySelector('#cn-phieu');
    let d = st.cache.get(k);
    if (!d) {
        try {
            d = await call('ns.api.cong_nhan.phieu', thamSo({ thang: x.thang, nam: x.nam }));
        } catch (e) {
            if (khoa(st.thang[st.i]) === k) o.innerHTML = `<div class="ns-risk-bar">${esc(e.message)}</div>`;
            return;
        }
        st.cache.set(k, d);
    }
    if (khoa(st.thang[st.i]) !== k) return; // đã chuyển tháng khác trong lúc chờ
    o.innerHTML = d.phieu.length
        ? d.phieu.map((p) => phieuLuongHtml(p, { congNhan: true })).join('')
        : '<div class="ns-empty"><div class="ns-empty-icon">🧾</div><div class="ns-empty-title">Tháng này chưa có phiếu</div></div>';
}

async function batDau() {
    if (!view || !CTX.coNhanVien) return;
    let d;
    try {
        d = await call('ns.api.cong_nhan.cac_thang', thamSo());
    } catch (e) {
        view.innerHTML = `<div class="ns-risk-bar">${esc(e.message)}</div>`;
        return;
    }
    st.info = d;
    st.thang = d.thang || [];
    if (!st.thang.length) {
        view.innerHTML = `<div class="ns-empty" style="padding-top:2.5rem"><div class="ns-empty-icon">🧾</div>
            <div class="ns-empty-title">Chưa có phiếu lương nào</div>
            <div>Phiếu lương hiện ở đây sau khi phòng lương duyệt.</div></div>`;
        return;
    }
    const h = location.hash.replace('#', '');
    const i = st.thang.findIndex((x) => khoa(x) === h);
    st.i = i >= 0 ? i : 0;
    veKhung();
}

batDau();
