// #/luong?t=&n=&loai= — Bảng lương tháng (chỉ đọc)
import { ns } from '../lib/api.js';
import { html, raw, skeleton, emptyState } from '../lib/dom.js';
import { escapeHtml, formatNumber } from '../lib/format.js';
import { replaceQuery } from '../lib/router.js';
import { showToast, withLoading } from '../components/toast.js';
import { paged } from '../components/table.js';

const CTX = window.NS_CONTEXT || {};
const SO = new Set(['ngaysanxuat', 'congngay', 'lamthem', 'luongngaycong', 'luonglamthem', 'anca', 'chuyencan', 'hotrongaycong', 'hotro', 'thuongkhac', 'thuongthamnien', 'tongtien', 'baohiem', 'tienphat', 'tongkhautru', 'luongthucnhan', 'luongck',
    'ngay_san_xuat', 'ngay_cong', 'luong_san_pham', 'tien_an', 'chuyen_can', 'ho_tro_ngay_cong', 'ho_tro', 'thuong_tham_nien', 'tong_tien', 'bao_hiem', 'tien_phat', 'tong_khau_tru', 'luong_thuc_nhan']);
const LE = new Set(['congngay', 'lamthem', 'ngay_cong', 'ngaysanxuat', 'ngay_san_xuat']);
const bpLabel = (d) => (d === '__none__' ? 'Chưa có bộ phận' : d || 'Tất cả');

export async function render({ container, query = {}, setHeader }) {
    const now = new Date();
    const st = { t: Number(query.t) || now.getMonth() + 1, n: Number(query.n) || now.getFullYear(), loai: query.loai === 'khoan' ? 'khoan' : 'nhat', bp: query.bp || '', tt: query.tt || '', data: null };
    setHeader('Bảng lương tháng');
    container.innerHTML = html`
        <div class="ns-filters">
            <label class="ns-field"><span class="ns-field-label">Tháng</span><input class="ns-input" type="month" id="l-month" value="${st.n}-${String(st.t).padStart(2, '0')}"></label>
            <div class="ns-tabs" style="margin:0;flex:1"><button class="ns-tab ${st.loai === 'nhat' ? 'ns-active' : ''}" data-loai="nhat">Công nhật</button><button class="ns-tab ${st.loai === 'khoan' ? 'ns-active' : ''}" data-loai="khoan">Công khoán</button></div>
        </div>
        <div class="ns-filters">
            <select class="ns-input" id="l-bp"><option value="">Mọi bộ phận</option>${raw((CTX.departments || []).map((d) => `<option value="${escapeHtml(d)}" ${st.bp === d ? 'selected' : ''}>${escapeHtml(bpLabel(d))}</option>`).join(''))}</select>
            <select class="ns-input" id="l-tt"><option value="">Mọi trạng thái</option><option value="duyet" ${st.tt === 'duyet' ? 'selected' : ''}>Đã duyệt</option><option value="nhap" ${st.tt === 'nhap' ? 'selected' : ''}>Nháp</option><option value="thieu" ${st.tt === 'thieu' ? 'selected' : ''}>Thiếu phiếu</option><option value="trung" ${st.tt === 'trung' ? 'selected' : ''}>Trùng</option></select>
            <div class="ns-actions"><button class="ns-btn ns-btn-sm" id="l-xlsx">⬇️ Xuất Excel</button><button class="ns-btn ns-btn-sm" id="l-ck" ${st.loai === 'nhat' ? '' : 'hidden'}>🏦 Danh sách chuyển khoản</button></div>
        </div>
        <div id="l-kpi"></div>
        <div id="l-body">${raw(skeleton(300))}</div>
        <div class="ns-text-sm ns-text-muted ns-mt-2">v1 chỉ đọc. Sửa công → <a href="/chamcong2">Chấm công</a>; sửa phiếu → mở trong ERPNext. Đỏ = thiếu phiếu, cam = trùng nháp, xám = nháp.</div>`;

    const body = container.querySelector('#l-body'); const kpi = container.querySelector('#l-kpi');
    function sync() { replaceQuery({ t: st.t, n: st.n, loai: st.loai, bp: st.bp, tt: st.tt }); }
    container.querySelector('#l-month').onchange = (e) => { const [n, t] = e.target.value.split('-'); st.t = Number(t); st.n = Number(n); sync(); load(); };
    container.querySelectorAll('[data-loai]').forEach((b) => { b.onclick = () => { st.loai = b.dataset.loai; container.querySelectorAll('[data-loai]').forEach((x) => x.classList.toggle('ns-active', x === b)); container.querySelector('#l-ck').hidden = st.loai !== 'nhat'; sync(); load(); }; });
    container.querySelector('#l-bp').onchange = (e) => { st.bp = e.target.value; sync(); load(); };
    container.querySelector('#l-tt').onchange = (e) => { st.tt = e.target.value; sync(); draw(); };
    container.querySelector('#l-xlsx').onclick = async () => { try { await withLoading(() => ns.luong.xuatExcel({ thang: st.t, nam: st.n, loai: st.loai, department: st.bp || null }), 'Đang xuất…'); } catch (e) { showToast(e.message, 'error'); } };
    container.querySelector('#l-ck').onclick = async () => { try { await withLoading(() => ns.luong.chuyenKhoan({ thang: st.t, nam: st.n }), 'Đang xuất…'); } catch (e) { showToast(e.message, 'error'); } };

    async function load() {
        body.innerHTML = skeleton(300); kpi.innerHTML = '';
        try { st.data = await ns.luong.bang({ thang: st.t, nam: st.n, loai: st.loai, department: st.bp || null }); draw(); }
        catch (e) { body.innerHTML = `<div class="ns-risk-bar">${escapeHtml(e.message)}</div>`; }
    }
    function draw() {
        const d = st.data; if (!d) return;
        const thucNhan = st.loai === 'nhat' ? 'luongthucnhan' : 'luong_thuc_nhan';
        kpi.innerHTML = `<div class="ns-kpi-grid ns-mb-3">
            <div class="ns-kpi-card"><div class="ns-kpi-label">Tổng thực nhận</div><div class="ns-kpi-value success">${formatNumber(d.tong[thucNhan])}</div><div class="ns-kpi-sub">T${d.thang}/${d.nam} · ${d.dong.length} người</div></div>
            <div class="ns-kpi-card"><div class="ns-kpi-label">Đã duyệt</div><div class="ns-kpi-value">${d.so_duyet}</div></div>
            <div class="ns-kpi-card"><div class="ns-kpi-label">Nháp</div><div class="ns-kpi-value ${d.so_nhap ? 'warning' : ''}">${d.so_nhap}</div></div>
            <div class="ns-kpi-card"><div class="ns-kpi-label">Thiếu phiếu</div><div class="ns-kpi-value ${d.so_thieu_phieu ? 'danger' : ''}">${d.so_thieu_phieu}</div></div></div>
            ${d.co_nguon ? '' : `<div class="ns-risk-bar">Site chưa có bảng ${st.loai === 'nhat' ? 'SalaryDay' : 'SX Phieu Luong'} — không đọc được phiếu.</div>`}`;
        let rows = d.dong;
        if (st.tt === 'duyet') rows = rows.filter((r) => r.docstatus === 1);
        if (st.tt === 'nhap') rows = rows.filter((r) => r.docstatus === 0);
        if (st.tt === 'thieu') rows = rows.filter((r) => r.thieu_phieu);
        if (st.tt === 'trung') rows = rows.filter((r) => r.trung);
        if (!rows.length) { body.innerHTML = emptyState('🧾', 'Không có dòng nào'); return; }
        const cot = d.cot; const lb = d.label;
        const tong = {}; cot.forEach((c) => { if (SO.has(c)) tong[c] = rows.reduce((s, r) => s + (Number(r[c]) || 0), 0); });
        const renderSlice = (slice, start) => `<div class="ns-table-wrap"><table class="ns-table"><thead><tr><th>#</th><th class="ns-sticky">Nhân viên</th><th>Bộ phận</th><th>Phiếu</th>${cot.map((c) => `<th class="${SO.has(c) ? 'ns-num' : ''}">${escapeHtml(lb[c] || c)}</th>`).join('')}<th></th></tr></thead><tbody>
            ${slice.map((r, i) => `<tr class="${r.thieu_phieu ? 'ns-row-do' : r.trung ? 'ns-row-cam' : r.docstatus === 0 ? 'ns-row-xam' : ''}">
                <td class="ns-text-muted">${start + i + 1}</td><td class="ns-sticky"><a href="#/nv/${escapeHtml(r.employee)}?tab=luong&t=${d.thang}&n=${d.nam}" style="font-weight:700">${escapeHtml(r.employee_name)}</a><div class="ns-sub">${escapeHtml(r.employee)}</div></td>
                <td>${escapeHtml(r.department || '—')}</td>
                <td>${r.thieu_phieu ? '<span class="ns-badge ns-badge-danger">Thiếu phiếu</span>' : `<span class="ns-badge ${r.docstatus === 1 ? 'ns-badge-success' : 'ns-badge-warning'}">${r.docstatus === 1 ? 'Đã duyệt' : 'Nháp'}</span>${r.trung ? ` <span class="ns-badge ns-badge-danger" title="${r.so_phieu} phiếu">Trùng</span>` : ''}`}</td>
                ${cot.map((c) => `<td class="${SO.has(c) ? 'ns-num' : ''}">${r[c] == null ? '' : SO.has(c) ? formatNumber(r[c], LE.has(c) ? 1 : 0) : escapeHtml(r[c])}</td>`).join('')}
                <td class="ns-actions">${r.name ? `<a class="ns-btn ns-btn-sm" href="/app/${st.loai === 'nhat' ? 'salaryday' : 'sx-phieu-luong'}/${encodeURIComponent(r.name)}" target="_blank">Mở phiếu</a>${st.loai === 'nhat' ? `<a class="ns-btn ns-btn-sm" href="/printview?doctype=SalaryDay&name=${encodeURIComponent(r.name)}&format=${encodeURIComponent('Phiếu lương công nhật')}" target="_blank">In</a>` : ''}` : ''}</td></tr>`).join('')}</tbody>
            <tfoot><tr><td></td><td class="ns-sticky">TỔNG (${rows.length})</td><td></td><td></td>${cot.map((c) => `<td class="${SO.has(c) ? 'ns-num' : ''}">${SO.has(c) ? formatNumber(tong[c], LE.has(c) ? 1 : 0) : ''}</td>`).join('')}<td></td></tr></tfoot></table></div>`;
        body.innerHTML = paged({ rows, pageSize: 50, render: renderSlice });
    }
    sync(); load();
    return () => {};
}
