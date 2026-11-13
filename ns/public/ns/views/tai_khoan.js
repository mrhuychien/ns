// #/tai-khoan — Tài khoản xem lương của công nhân: ai đã có, ai chưa, tạo (từng người / hàng loạt), cấp lại mật khẩu,
// khoá, gỡ, in thẻ. Quyền thật ở server: xem = HR User trở lên; sửa = HR Manager (CTX.isManager chỉ để ẩn nút).
import { ns } from '../lib/api.js';
import { skeleton, emptyState } from '../lib/dom.js';
import { escapeHtml as esc, formatNumber } from '../lib/format.js';
import { replaceQuery } from '../lib/router.js';
import { paged } from '../components/table.js';
import { tkHtml, tkNutHtml, ganNutTaiKhoan, taoHangLoat, coQuyenSua } from '../components/tai_khoan.js';

const CTX = window.NS_CONTEXT || {};
const LOC = [['', 'Tất cả'], ['chua', 'Chưa có tài khoản'], ['co', 'Đã có'], ['khoa', 'Đã khoá'], ['nghi', 'Đã nghỉ còn tài khoản']];
const TT = { Active: 'Đang làm', Inactive: 'Tạm nghỉ', Suspended: 'Tạm đình chỉ', Left: 'Đã nghỉ' };
const bpLabel = (d) => (d === '__none__' ? 'Chưa có bộ phận' : d || 'Mọi bộ phận');
const khongDau = (s) => String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/đ/g, 'd').replace(/Đ/g, 'D').toLowerCase();

export async function render({ container, query = {}, setHeader }) {
    setHeader('Tài khoản xem lương');
    const st = { loc: query.loc || '', bp: query.bp || '', q: query.q || '', data: null, chon: new Set() };
    container.innerHTML = `
        <div id="tk-bao"></div>
        <div id="tk-kpi"></div>
        <div class="ns-filters">
            <div class="ns-search"><input id="tk-q" placeholder="Tìm tên, mã NV, số điện thoại…" value="${esc(st.q)}"></div>
            <select class="ns-input" id="tk-bp"><option value="">Mọi bộ phận</option>${(CTX.departments || []).map((d) => `<option value="${esc(d)}" ${st.bp === d ? 'selected' : ''}>${esc(bpLabel(d))}</option>`).join('')}</select>
        </div>
        <div class="ns-chips ns-mb-3" id="tk-loc">${LOC.map(([k, l]) => `<button class="ns-chip ${st.loc === k ? 'ns-active' : ''}" data-loc="${k}">${l}</button>`).join('')}</div>
        <div class="ns-actions ns-mb-3" id="tk-hang-loat"></div>
        <div id="tk-body">${skeleton(60, 5)}</div>`;
    const body = container.querySelector('#tk-body');
    const sync = () => replaceQuery({ loc: st.loc, bp: st.bp, q: st.q });
    let hen = null;
    container.querySelector('#tk-q').oninput = (e) => { clearTimeout(hen); hen = setTimeout(() => { st.q = e.target.value.trim(); sync(); ve(); }, 250); };
    container.querySelector('#tk-bp').onchange = (e) => { st.bp = e.target.value; sync(); ve(); };
    container.querySelectorAll('[data-loc]').forEach((b) => {
        b.onclick = () => { st.loc = b.dataset.loc; container.querySelectorAll('[data-loc]').forEach((x) => x.classList.toggle('ns-active', x === b)); sync(); ve(); };
    });

    async function tai() {
        try { st.data = await ns.taiKhoan.danhSach(); } catch (e) { body.innerHTML = `<div class="ns-risk-bar">${esc(e.message)}</div>`; return; }
        st.chon.clear();
        ve();
    }
    function locDong() {
        const d = st.data; if (!d) return [];
        const q = khongDau(st.q);
        return d.dong.filter((r) => {
            if (st.bp === '__none__' ? r.department : st.bp && r.department !== st.bp) return false;
            if (st.loc === 'chua' && (r.tai_khoan || r.status !== 'Active')) return false;
            if (st.loc === 'co' && !r.tai_khoan) return false;
            if (st.loc === 'khoa' && !(r.tai_khoan && !r.tai_khoan.bat)) return false;
            if (st.loc === 'nghi' && !(r.status !== 'Active' && r.tai_khoan)) return false;
            if (q && !khongDau(`${r.employee_name} ${r.employee} ${r.cell_number || ''} ${(r.tai_khoan || {}).sdt || ''}`).includes(q)) return false;
            return true;
        });
    }
    function ve() {
        const d = st.data; if (!d) return;
        const t = d.tong_hop;
        container.querySelector('#tk-bao').innerHTML = `
            ${d.co_field ? '' : '<div class="ns-risk-bar"><span><strong>Chưa migrate:</strong> Employee chưa có field ns_tai_khoan — chạy <code>bench --site … migrate</code>.</span></div>'}
            ${d.dang_nhap_sdt ? '' : '<div class="ns-risk-bar"><span><strong>Site chưa cho đăng nhập bằng số điện thoại.</strong> System Settings → bật <b>Allow Login using Mobile Number</b> (hoặc <b>… User Name</b>) — chưa bật thì công nhân không đăng nhập được.</span></div>'}
            <div class="ns-risk-bar ns-info-bar"><span>Công nhân mở <b>${esc(d.url)}</b>, đăng nhập bằng số điện thoại + mật khẩu, chỉ thấy phiếu lương của chính mình — ${d.cong_nhan_xem_nhap ? 'cả phiếu <b>tạm tính</b> (chưa duyệt, ghi rõ “Tạm tính”)' : 'chỉ phiếu <b>đã duyệt</b>'}.</span></div>`;
        container.querySelector('#tk-kpi').innerHTML = `<div class="ns-kpi-grid ns-mb-3">
            <div class="ns-kpi-card"><div class="ns-kpi-label">Đang làm</div><div class="ns-kpi-value">${t.so_nv}</div></div>
            <div class="ns-kpi-card"><div class="ns-kpi-label">Có tài khoản</div><div class="ns-kpi-value success">${t.co_tk}</div><div class="ns-kpi-sub">${t.so_nv ? formatNumber((t.co_tk / t.so_nv) * 100) : 0}%</div></div>
            <div class="ns-kpi-card"><div class="ns-kpi-label">Chưa có</div><div class="ns-kpi-value ${t.chua_tk ? 'warning' : ''}">${t.chua_tk}</div></div>
            <div class="ns-kpi-card"><div class="ns-kpi-label">Đã nghỉ còn dùng</div><div class="ns-kpi-value ${t.nghi_con_tk ? 'danger' : ''}">${t.nghi_con_tk}</div><div class="ns-kpi-sub">${t.bi_khoa} tài khoản đã khoá</div></div></div>`;
        const rows = locDong();
        const coTheTao = rows.filter((r) => !r.tai_khoan && r.status === 'Active');
        const hl = container.querySelector('#tk-hang-loat');
        hl.innerHTML = coQuyenSua() && d.co_field && coTheTao.length ? `
            <label class="ns-flex ns-items-center ns-gap-2 ns-text-sm"><input type="checkbox" id="tk-chon-het"> Chọn cả ${coTheTao.length} người chưa có tài khoản</label>
            <button class="ns-btn ns-btn-sm ns-btn-primary" id="tk-tao-chon" disabled>Tạo tài khoản cho người đã chọn</button>` : '';
        if (!rows.length) { body.innerHTML = emptyState('🔑', 'Không có ai khớp bộ lọc'); return; }
        const tim = (emp) => d.dong.find((r) => r.employee === emp);
        const renderSlice = (slice) => `<div class="ns-tk-list">${slice.map((r) => `
            <div class="ns-tk-row" data-emp="${esc(r.employee)}">
                ${coQuyenSua() && d.co_field && !r.tai_khoan && r.status === 'Active' ? `<input type="checkbox" data-chon="${esc(r.employee)}" ${st.chon.has(r.employee) ? 'checked' : ''} aria-label="Chọn ${esc(r.employee_name)}">` : ''}
                <div class="ns-tk-who"><a class="ns-tk-name" href="#/nv/${encodeURIComponent(r.employee)}?tab=luong">${esc(r.employee_name)}</a>
                    <div class="ns-tk-meta">${esc(r.employee)} · ${esc(r.department || 'Chưa có bộ phận')}${r.status !== 'Active' ? ` · <span class="ns-badge ns-badge-danger">${esc(TT[r.status] || r.status)}</span>` : ''}
                    · SĐT hồ sơ: ${r.cell_number ? esc(r.cell_number) : '<span class="ns-badge ns-badge-warning">chưa có</span>'}</div></div>
                <div class="ns-tk-acc">${tkHtml(r.tai_khoan)}</div>
                <div class="ns-actions">${d.co_field ? tkNutHtml(r) : ''}
                    ${r.tai_khoan ? `<a class="ns-btn ns-btn-sm ns-btn-ghost" href="/phieuluong?nv=${encodeURIComponent(r.employee)}" target="_blank" title="Xem đúng màn công nhân đang thấy">👁 Xem như công nhân</a>` : ''}</div>
            </div>`).join('')}</div>`;
        const onDraw = (el) => {
            ganNutTaiKhoan(el, tim, tai);
            el.querySelectorAll('[data-chon]').forEach((c) => { c.onchange = () => { if (c.checked) st.chon.add(c.dataset.chon); else st.chon.delete(c.dataset.chon); capNhatNut(); }; });
        };
        body.innerHTML = paged({ rows, pageSize: 30, render: renderSlice, onDraw });
        const het = hl.querySelector('#tk-chon-het');
        const nutTao = hl.querySelector('#tk-tao-chon');
        function capNhatNut() {
            if (!nutTao) return;
            const n = coTheTao.filter((r) => st.chon.has(r.employee)).length;
            nutTao.disabled = !n;
            nutTao.textContent = n ? `Tạo tài khoản cho ${n} người đã chọn` : 'Tạo tài khoản cho người đã chọn';
            if (het) het.checked = n === coTheTao.length;
        }
        if (het) het.onchange = () => { coTheTao.forEach((r) => (het.checked ? st.chon.add(r.employee) : st.chon.delete(r.employee))); body.querySelectorAll('[data-chon]').forEach((c) => { c.checked = st.chon.has(c.dataset.chon); }); capNhatNut(); };
        if (nutTao) nutTao.onclick = () => taoHangLoat(coTheTao.filter((r) => st.chon.has(r.employee)), tai);
        capNhatNut();
    }
    sync();
    await tai();
    return () => {};
}
