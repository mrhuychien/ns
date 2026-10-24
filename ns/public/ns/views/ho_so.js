// #/nv/:name — Hồ sơ: Thông tin · Giấy tờ · Lịch sử · Công & lương
import { ns, upload } from '../lib/api.js';
import { html, raw, skeleton, emptyState } from '../lib/dom.js';
import { escapeHtml, formatNumber, formatDate, daysUntil, initials } from '../lib/format.js';
import { replaceQuery } from '../lib/router.js';
import { showToast, withLoading } from '../components/toast.js';
import { showModal, closeModal, confirmModal } from '../components/modal.js';
import { inputFor, readValue, displayValue } from '../components/field.js';
import { canhBaoList } from '../components/canh_bao.js';

const CTX = window.NS_CONTEXT || {};
const F = {
    LCB: 'custom_lương_cơ_bản', HT: 'custom_hỗ_trợ', BH: 'custom_bảo_hiểm', LTK: 'custom_lương_tài_khoản', ACT: 'custom_ăn_ca_tối_tại_công_ty',
};
const GROUPS = [
    { ten: 'Cá nhân', fields: [
        ['first_name', 'Họ tên', 'Data'], ['gender', 'Giới tính', 'Link:gender'], ['date_of_birth', 'Ngày sinh', 'Date'], ['custom_cccd', 'CCCD', 'Data'],
        ['cell_number', 'SĐT', 'Data'], ['custom_zalo', 'Zalo', 'Data'], ['personal_email', 'Email', 'Data'],
        ['current_address', 'Địa chỉ hiện tại', 'Small Text'], ['permanent_address', 'Thường trú', 'Small Text'],
        ['person_to_be_contacted', 'Liên hệ khẩn cấp', 'Data'], ['emergency_phone_number', 'SĐT khẩn cấp', 'Data'], ['relation', 'Quan hệ', 'Data'],
    ] },
    { ten: 'Công việc', fields: [
        ['department', 'Bộ phận', 'Link:department'], ['designation', 'Chức danh', 'Link:designation'], ['date_of_joining', 'Ngày vào làm', 'Date'],
        ['vn_contract_type', 'Loại HĐ', 'Select:vn_contract_type'], ['contract_end_date', 'Ngày hết hạn HĐ', 'Date'], ['attendance_device_id', 'Mã máy chấm công', 'Data'],
        ['status', 'Trạng thái', 'Select:status'], ['relieving_date', 'Ngày nghỉ việc', 'Date', 'left'], ['reason_for_leaving', 'Lý do nghỉ', 'Data', 'left'],
    ] },
    { ten: 'Lương & BHXH', fields: [
        [F.LCB, 'Lương cơ bản', 'Currency'], [F.HT, 'Hỗ trợ', 'Currency'], [F.BH, 'Bảo hiểm (mức trừ/tháng)', 'Currency'], [F.LTK, 'Lương tài khoản (CK)', 'Currency'],
        [F.ACT, 'Ăn ca tối tại công ty', 'Check'], ['ns_dong_bhxh', 'Đóng BHXH', 'Check'], ['ns_so_so_bhxh', 'Số sổ BHXH', 'Data'],
        ['vn_insurance_salary', 'Mức lương đóng BH', 'Currency'], ['ns_bhxh_tu_ngay', 'Đóng BHXH từ', 'Date'], ['ns_bhxh_den_ngay', 'Ngừng đóng từ', 'Date'],
        ['ns_ly_do_khong_bhxh', 'Lý do không đóng BHXH', 'Select:ns_ly_do_khong_bhxh', 'khongbhxh'], ['vn_tax_code', 'Mã số thuế', 'Data'],
        ['vn_number_of_dependents', 'Số người phụ thuộc', 'Int'], ['health_insurance_no', 'Mã thẻ BHYT', 'Data'],
    ] },
    { ten: 'Ngân hàng', fields: [
        ['bank_name', 'Ngân hàng', 'Link:bank_name'], ['bank_ac_no', 'Số tài khoản', 'Data'], ['custom_bankowner', 'Chủ tài khoản', 'Data'], ['salary_mode', 'Hình thức trả', 'Select:salary_mode'],
    ] },
];
const LOAI_GT = ['CCCD', 'Hợp đồng lao động', 'Phụ lục HĐLĐ', 'Giấy khám sức khỏe', 'Xác nhận kiến thức ATTP', 'Sổ BHXH', 'Bằng cấp / chứng chỉ', 'Khác'];
const LOAI_SK = ['Vào làm', 'Ký HĐLĐ', 'Phụ lục HĐLĐ', 'Thay đổi lương', 'Điều chuyển bộ phận', 'Bắt đầu đóng BHXH', 'Ngừng đóng BHXH', 'Khen thưởng', 'Kỷ luật', 'Khám sức khỏe', 'Tập huấn ATTP', 'Tạm nghỉ', 'Đi làm lại', 'Nghỉ việc', 'Khác'];
const TABS = [['thongtin', 'Thông tin'], ['giayto', 'Giấy tờ'], ['lichsu', 'Lịch sử'], ['luong', 'Công & lương']];

export async function render({ container, params, query = {}, setHeader }) {
    const name = params.name;
    const st = { tab: query.tab || 'thongtin', t: Number(query.t) || null, n: Number(query.n) || null, data: null, giayTo: [], dirtyGt: false };
    setHeader('Hồ sơ', { back: true });
    container.innerHTML = skeleton(120, 3);
    try { st.data = await ns.nhanVien.chiTiet(name); } catch (e) { container.innerHTML = `<div class="ns-risk-bar">${escapeHtml(e.message)}</div>`; return; }
    st.giayTo = (st.data.ns_giay_to || []).map((r) => ({ ...r }));
    setHeader(st.data.employee_name || name, { back: true, actions: `<a class="ns-btn ns-btn-sm ns-hide-mobile" href="/app/employee/${encodeURIComponent(name)}" target="_blank">Mở ERPNext</a>` });

    container.innerHTML = html`
        <div class="ns-view-banner">
            <div class="ns-flex ns-items-center ns-gap-3">
                <div class="ns-avatar" style="width:52px;height:52px;font-size:1.1rem">${st.data.image ? raw(`<img src="${escapeHtml(st.data.image)}" alt="">`) : initials(st.data.employee_name)}</div>
                <div><div class="ns-view-banner-title">${st.data.employee_name}</div>
                <div class="ns-view-banner-subtitle">${st.data.name} · ${st.data.department || 'Chưa có bộ phận'} · ${st.data.loai_luong} · ${st.data.tham_nien_nam != null ? st.data.tham_nien_nam + ' năm' : ''}</div></div>
            </div>
            <div class="ns-view-banner-badge">${trangThai(st.data.status)}</div>
        </div>
        <div id="hs-canhbao"></div>
        <div class="ns-tabs" id="hs-tabs"></div>
        <div id="hs-body"></div>`;
    const body = container.querySelector('#hs-body');

    function drawBanner() {
        const d = st.data;
        const thieu = (d.thieu || []).filter((f) => !f.startsWith('gt_'));
        const gtThieu = (d.thieu || []).filter((f) => f.startsWith('gt_'));
        const lbl = (f) => d.thieu_label?.[f] || f;
        const gtLbl = { gt_cccd: 'giấy CCCD', gt_hdld: 'HĐLĐ còn hạn', gt_ksk: 'khám SK còn hạn', gt_attp: 'ATTP còn hạn' };
        container.querySelector('#hs-canhbao').innerHTML = `
            ${d.canh_bao?.length ? `<div class="ns-card ns-mb-3">${canhBaoList(d.canh_bao)}</div>` : ''}
            ${(thieu.length || gtThieu.length) ? `<div class="ns-risk-bar ns-warn-bar"><strong>Hồ sơ ${d.pct_du}% · còn thiếu:</strong>
                ${thieu.map((f) => `<a href="#" class="ns-chip ns-chip-warn" data-focus="${escapeHtml(f)}">${escapeHtml(lbl(f))}</a>`).join('')}
                ${gtThieu.map((f) => `<a href="#" class="ns-chip ns-chip-warn" data-gt-tab>${escapeHtml(gtLbl[f] || f)}</a>`).join('')}</div>` : ''}`;
        container.querySelectorAll('[data-focus]').forEach((a) => { a.onclick = (e) => { e.preventDefault(); goTab('thongtin'); setTimeout(() => { const i = body.querySelector(`[data-field="${a.dataset.focus}"]`); if (i) { i.scrollIntoView({ block: 'center' }); i.focus(); } }, 50); }; });
        container.querySelectorAll('[data-gt-tab]').forEach((a) => { a.onclick = (e) => { e.preventDefault(); goTab('giayto'); }; });
    }
    function drawTabs() {
        container.querySelector('#hs-tabs').innerHTML = TABS.map(([k, l]) => html`<button class="ns-tab ${st.tab === k ? 'ns-active' : ''}" data-tab="${k}">${l}${k === 'giayto' ? raw(` <span class="ns-count">${st.giayTo.length}</span>`) : ''}</button>`).join('');
        container.querySelectorAll('#hs-tabs [data-tab]').forEach((b) => { b.onclick = () => goTab(b.dataset.tab); });
    }
    function goTab(tab) { st.tab = tab; replaceQuery({ tab, t: st.t, n: st.n }); drawTabs(); drawBody(); }
    async function reload() {
        st.data = await ns.nhanVien.chiTiet(name);
        st.giayTo = (st.data.ns_giay_to || []).map((r) => ({ ...r })); st.dirtyGt = false;
        drawBanner(); drawTabs();
    }
    function drawBody() {
        if (st.tab === 'thongtin') return drawThongTin();
        if (st.tab === 'giayto') return drawGiayTo();
        if (st.tab === 'lichsu') return drawLichSu();
        return drawLuong();
    }

    // ───── Thông tin ─────
    function drawThongTin() {
        const d = st.data; const co = new Set(d.field_co || []); const tc = d.tuy_chon || {};
        body.innerHTML = `<form id="hs-form">${GROUPS.map((g) => `<div class="ns-card"><div class="ns-section-title">${g.ten}</div><div class="ns-form-grid">
            ${g.fields.filter(([f]) => co.has(f)).map(([f, label, type, cond]) => {
                const [ft, optKey] = type.split(':');
                const opts = optKey ? (tc[optKey] || []) : null;
                const hide = (cond === 'left' && d.status !== 'Left') || (cond === 'khongbhxh' && Number(d.ns_dong_bhxh));
                const wide = ft === 'Small Text';
                return `<div class="ns-field ${wide ? 'ns-span-2' : ''}" data-cond="${cond || ''}" ${hide ? 'hidden' : ''}><label>${escapeHtml(label)}${(d.thieu || []).includes(f) ? ' <span class="ns-badge ns-badge-warning">thiếu</span>' : ''}</label>
                    ${inputFor({ field: f, fieldtype: ft === 'Link' && opts && opts.length <= 60 ? 'Select' : ft, options: opts, value: d[f] })}<div class="ns-field-err" data-err="${escapeHtml(f)}"></div></div>`;
            }).join('')}</div></div>`).join('')}
            <div class="ns-card"><div class="ns-section-title">Ảnh</div><div class="ns-flex ns-items-center ns-gap-3">
                <div class="ns-avatar" style="width:64px;height:64px" id="hs-img">${d.image ? `<img src="${escapeHtml(d.image)}" alt="">` : escapeHtml(initials(d.employee_name))}</div>
                <label class="ns-btn ns-btn-sm">Tải ảnh<input type="file" accept="image/*" hidden id="hs-img-file"></label>
                <input type="hidden" data-field="image" name="image" value="${escapeHtml(d.image || '')}"></div></div>
            <div class="ns-actions ns-mt-3" style="position:sticky;bottom:calc(var(--ns-bottom-h) + .5rem);z-index:5"><button type="submit" class="ns-btn ns-btn-primary">💾 Lưu hồ sơ</button><button type="button" class="ns-btn" id="hs-cancel">Huỷ</button></div></form>`;
        const form = body.querySelector('#hs-form');
        const statusEl = form.querySelector('[data-field="status"]');
        if (statusEl) statusEl.addEventListener('change', () => form.querySelectorAll('[data-cond="left"]').forEach((x) => { x.hidden = statusEl.value !== 'Left'; }));
        const bhEl = form.querySelector('[data-field="ns_dong_bhxh"]');
        if (bhEl) bhEl.addEventListener('change', () => form.querySelectorAll('[data-cond="khongbhxh"]').forEach((x) => { x.hidden = bhEl.checked; }));
        form.querySelector('#hs-cancel').onclick = () => drawThongTin();
        form.querySelector('#hs-img-file').onchange = async (e) => {
            const f = e.target.files[0]; if (!f) return;
            try { const r = await withLoading(() => upload(f, { doctype: 'Employee', docname: name, isPrivate: 0 }), 'Đang tải ảnh…');
                form.querySelector('[data-field="image"]').value = r.file_url; form.querySelector('#hs-img').innerHTML = `<img src="${escapeHtml(r.file_url)}" alt="">`; showToast('Đã tải ảnh — nhấn Lưu để ghi', 'success'); } catch (err) { showToast(err.message, 'error'); }
        };
        form.onsubmit = async (e) => {
            e.preventDefault();
            form.querySelectorAll('.ns-field-err').forEach((x) => { x.textContent = ''; }); form.querySelectorAll('.ns-invalid').forEach((x) => x.classList.remove('ns-invalid'));
            const data = {};
            form.querySelectorAll('[data-field]').forEach((i) => { data[i.dataset.field] = readValue(i); });
            // validate client nhanh
            let bad = false;
            if (data.custom_cccd && !/^\d{12}$/.test(String(data.custom_cccd).replace(/\D/g, ''))) { mark('custom_cccd', 'CCCD phải đúng 12 chữ số'); bad = true; }
            if (data.date_of_joining && data.date_of_joining > CTX.today) { mark('date_of_joining', 'Không được sau hôm nay'); bad = true; }
            if (data.status === 'Left' && !data.relieving_date) { mark('relieving_date', 'Bắt buộc khi Đã nghỉ'); bad = true; }
            if (bad) return;
            try {
                st.data = await withLoading(() => ns.nhanVien.luu(name, data), 'Đang lưu…');
                st.giayTo = (st.data.ns_giay_to || []).map((r) => ({ ...r }));
                showToast('Đã lưu hồ sơ', 'success'); drawBanner(); drawTabs(); drawThongTin();
                setHeader(st.data.employee_name, { back: true, actions: `<a class="ns-btn ns-btn-sm ns-hide-mobile" href="/app/employee/${encodeURIComponent(name)}" target="_blank">Mở ERPNext</a>` });
            } catch (err) {
                const msg = err.message || 'Lỗi lưu';
                const f = guessField(msg); if (f) mark(f, msg);
                showToast(msg, 'error');
            }
            function mark(f, m) { const i = form.querySelector(`[data-field="${f}"]`); if (i) { i.classList.add('ns-invalid'); i.closest('.ns-field')?.removeAttribute('hidden'); i.scrollIntoView({ block: 'center' }); } const e2 = form.querySelector(`[data-err="${f}"]`); if (e2) e2.textContent = m; }
        };
    }
    function guessField(msg) {
        const m = msg.toLowerCase();
        if (m.includes('cccd')) return 'custom_cccd'; if (m.includes('vào làm')) return 'date_of_joining'; if (m.includes('nghỉ việc')) return 'relieving_date';
        return null;
    }

    // ───── Giấy tờ ─────
    function hanBadge(r) {
        const d = daysUntil(r.ngay_het_han);
        if (d === null) return '<span class="ns-badge ns-badge-muted">—</span>';
        if (d < 0) return `<span class="ns-badge ns-badge-danger">Hết hạn ${-d} ngày</span>`;
        if (d <= 30) return `<span class="ns-badge ns-badge-warning">Còn ${d} ngày</span>`;
        return `<span class="ns-badge ns-badge-success">${formatDate(r.ngay_het_han)}</span>`;
    }
    function drawGiayTo() {
        body.innerHTML = `<div class="ns-card"><div class="ns-section-title"><span>Giấy tờ (${st.giayTo.length})</span>
            <div class="ns-actions"><button class="ns-btn ns-btn-sm" id="gt-add">+ Thêm</button><button class="ns-btn ns-btn-primary ns-btn-sm" id="gt-save" ${st.dirtyGt ? '' : 'disabled'}>💾 Lưu</button></div></div>
            ${st.giayTo.length ? `<div class="ns-table-wrap"><table class="ns-table"><thead><tr><th>Loại</th><th>Số</th><th>Ngày cấp</th><th>Nơi cấp</th><th>Hết hạn</th><th>Tệp</th><th>Ghi chú</th><th></th></tr></thead><tbody>
            ${st.giayTo.map((r, i) => html`<tr><td><b>${r.loai}</b></td><td>${r.so || ''}</td><td>${formatDate(r.ngay_cap)}</td><td>${r.noi_cap || ''}</td><td>${raw(hanBadge(r))}</td>
                <td>${r.tep ? raw(`<a href="${escapeHtml(r.tep)}" target="_blank">📎 Xem</a>`) : ''}</td><td>${r.ghi_chu || ''}</td>
                <td class="ns-actions"><button class="ns-btn ns-btn-sm" data-edit="${i}">Sửa</button><button class="ns-btn ns-btn-sm ns-btn-danger" data-del="${i}">Xoá</button></td></tr>`).join('')}</tbody></table></div>` : emptyState('🗂️', 'Chưa có giấy tờ', 'Thêm CCCD, HĐLĐ, giấy khám sức khỏe, ATTP…')}
            ${st.dirtyGt ? '<div class="ns-risk-bar ns-warn-bar ns-mt-3">Có thay đổi chưa lưu — nhấn <b>Lưu</b>.</div>' : ''}</div>`;
        body.querySelector('#gt-add').onclick = () => openGt(null);
        body.querySelectorAll('[data-edit]').forEach((b) => { b.onclick = () => openGt(Number(b.dataset.edit)); });
        body.querySelectorAll('[data-del]').forEach((b) => { b.onclick = async () => { if (await confirmModal('Xoá giấy tờ', `Xoá dòng "${st.giayTo[b.dataset.del].loai}"?`, { danger: true, okLabel: 'Xoá' })) { st.giayTo.splice(Number(b.dataset.del), 1); st.dirtyGt = true; drawGiayTo(); } }; });
        body.querySelector('#gt-save').onclick = async () => {
            try { st.data = await withLoading(() => ns.nhanVien.luu(name, { ns_giay_to: st.giayTo }), 'Đang lưu…');
                st.giayTo = (st.data.ns_giay_to || []).map((r) => ({ ...r })); st.dirtyGt = false; showToast('Đã lưu giấy tờ', 'success'); drawBanner(); drawTabs(); drawGiayTo(); } catch (e) { showToast(e.message, 'error'); }
        };
    }
    function openGt(idx) {
        const r = idx === null ? { loai: 'CCCD' } : { ...st.giayTo[idx] };
        const c = showModal({ title: idx === null ? 'Thêm giấy tờ' : 'Sửa giấy tờ', body: `<div class="ns-form-grid">
            <div class="ns-field"><label>Loại *</label>${inputFor({ field: 'loai', fieldtype: 'Select', options: LOAI_GT, value: r.loai })}</div>
            <div class="ns-field"><label>Số</label>${inputFor({ field: 'so', value: r.so })}</div>
            <div class="ns-field"><label>Ngày cấp</label>${inputFor({ field: 'ngay_cap', fieldtype: 'Date', value: r.ngay_cap })}</div>
            <div class="ns-field"><label>Nơi cấp</label>${inputFor({ field: 'noi_cap', value: r.noi_cap })}</div>
            <div class="ns-field"><label>Hết hạn</label>${inputFor({ field: 'ngay_het_han', fieldtype: 'Date', value: r.ngay_het_han })}</div>
            <div class="ns-field"><label>Ghi chú</label>${inputFor({ field: 'ghi_chu', value: r.ghi_chu })}</div>
            <div class="ns-field ns-span-2"><label>Tệp</label><div class="ns-flex ns-items-center ns-gap-2"><label class="ns-btn ns-btn-sm">📎 Chọn tệp<input type="file" hidden id="gt-file"></label><span id="gt-file-name" class="ns-text-sm">${r.tep ? `<a href="${escapeHtml(r.tep)}" target="_blank">${escapeHtml(r.tep.split('/').pop())}</a>` : 'Chưa có'}</span><input type="hidden" data-field="tep" value="${escapeHtml(r.tep || '')}"></div></div>
        </div>`, footer: '<button class="ns-btn ns-btn-ghost" data-ns-close>Huỷ</button><button class="ns-btn ns-btn-primary" id="gt-ok">Xong</button>' });
        c.querySelector('#gt-file').onchange = async (e) => {
            const f = e.target.files[0]; if (!f) return;
            try { const u = await withLoading(() => upload(f, { doctype: 'Employee', docname: name, isPrivate: 1 }), 'Đang tải tệp…');
                c.querySelector('[data-field="tep"]').value = u.file_url; c.querySelector('#gt-file-name').innerHTML = `<a href="${escapeHtml(u.file_url)}" target="_blank">${escapeHtml(f.name)}</a>`; } catch (err) { showToast(err.message, 'error'); }
        };
        c.querySelector('#gt-ok').onclick = () => {
            const row = {}; c.querySelectorAll('[data-field]').forEach((i) => { row[i.dataset.field] = readValue(i); });
            if (!row.loai) { showToast('Chọn loại giấy tờ', 'warning'); return; }
            if (idx === null) st.giayTo.push(row); else st.giayTo[idx] = { ...st.giayTo[idx], ...row };
            st.dirtyGt = true; closeModal(); drawGiayTo();
        };
    }

    // ───── Lịch sử ─────
    async function drawLichSu() {
        body.innerHTML = `<div class="ns-card"><div class="ns-section-title"><span>Lịch sử</span><button class="ns-btn ns-btn-sm" id="sk-add">+ Thêm sự kiện</button></div><div id="sk-list">${skeleton(50, 4)}</div></div>`;
        body.querySelector('#sk-add').onclick = () => openSuKien();
        let list;
        try { list = await ns.lichSu(name); } catch (e) { body.querySelector('#sk-list').innerHTML = `<div class="ns-risk-bar">${escapeHtml(e.message)}</div>`; return; }
        const el = body.querySelector('#sk-list');
        if (!list.length) { el.innerHTML = emptyState('🕰️', 'Chưa có sự kiện'); return; }
        el.innerHTML = `<div class="ns-timeline">${list.map((x) => {
            const luong = x.ref_doctype === 'SalaryDay' || x.ref_doctype === 'SX Phieu Luong' || x.ref_doctype === 'SalaryProduct';
            return html`<div class="ns-tl-item ${luong ? 'ns-tl-luong' : x.nguon === 'Tự động' ? 'ns-tl-auto' : ''}" ${luong && x.thang ? raw(`data-luong="${x.thang}-${x.nam}"`) : ''} ${luong ? raw('style="cursor:pointer"') : ''}>
                <div class="ns-tl-date">${formatDate(x.ngay)}${x.nguon === 'Tự động' ? raw(' <span class="ns-badge ns-badge-muted">tự động</span>') : ''}${x.trang_thai ? raw(` <span class="ns-badge ${/nháp/i.test(x.trang_thai) ? 'ns-badge-warning' : 'ns-badge-success'}">${escapeHtml(x.trang_thai)}</span>`) : ''}</div>
                <div class="ns-tl-title">${x.loai}${x.tieu_de && x.tieu_de !== x.loai ? ' · ' + x.tieu_de : ''}</div>
                ${x.gia_tri_cu || x.gia_tri_moi ? raw(`<div class="ns-tl-body">${escapeHtml(x.gia_tri_cu || '—')} → <b>${escapeHtml(x.gia_tri_moi || '—')}</b></div>`) : ''}
                ${x.noi_dung ? raw(`<div class="ns-tl-body">${escapeHtml(x.noi_dung)}</div>`) : ''}
                ${x.tep ? raw(`<div class="ns-tl-body"><a href="${escapeHtml(x.tep)}" target="_blank">📎 Tệp</a></div>`) : ''}
                ${x.ref_doctype === 'NS Su Kien' ? raw(`<div class="ns-actions ns-mt-1"><button class="ns-btn ns-btn-sm" data-sk-edit="${escapeHtml(x.ref_name)}" data-nd="${escapeHtml(x.noi_dung || '')}" data-td="${escapeHtml(x.tieu_de || '')}" data-nguon="${escapeHtml(x.nguon)}">Sửa nội dung</button>${x.nguon === 'Tay' && CTX.isManager ? `<button class="ns-btn ns-btn-sm ns-btn-danger" data-sk-del="${escapeHtml(x.ref_name)}">Xoá</button>` : ''}</div>`) : ''}
            </div>`; }).join('')}</div>`;
        el.querySelectorAll('[data-luong]').forEach((d) => { d.onclick = () => { const [t, n] = d.dataset.luong.split('-'); st.t = Number(t); st.n = Number(n); goTab('luong'); }; });
        el.querySelectorAll('[data-sk-edit]').forEach((b) => { b.onclick = () => openSuaSk(b.dataset.skEdit, b.dataset.nd, b.dataset.td, b.dataset.nguon); });
        el.querySelectorAll('[data-sk-del]').forEach((b) => { b.onclick = async () => { if (await confirmModal('Xoá sự kiện', 'Xoá sự kiện này?', { danger: true, okLabel: 'Xoá' })) { try { await ns.suKien.xoa(b.dataset.skDel); showToast('Đã xoá', 'success'); drawLichSu(); } catch (e) { showToast(e.message, 'error'); } } }; });
    }
    function openSuKien() {
        const c = showModal({ title: 'Thêm sự kiện', body: `<div class="ns-form-grid">
            <div class="ns-field"><label>Ngày *</label>${inputFor({ field: 'ngay', fieldtype: 'Date', value: CTX.today })}</div>
            <div class="ns-field"><label>Loại *</label>${inputFor({ field: 'loai', fieldtype: 'Select', options: LOAI_SK, value: 'Khác' })}</div>
            <div class="ns-field ns-span-2"><label>Tiêu đề</label>${inputFor({ field: 'tieu_de' })}</div>
            <div class="ns-field ns-span-2"><label>Nội dung</label>${inputFor({ field: 'noi_dung', fieldtype: 'Small Text' })}</div>
            <div class="ns-field ns-span-2"><label>Tệp</label><div class="ns-flex ns-items-center ns-gap-2"><label class="ns-btn ns-btn-sm">📎 Chọn tệp<input type="file" hidden id="sk-file"></label><span id="sk-file-name" class="ns-text-sm">Chưa có</span><input type="hidden" data-field="tep" value=""></div></div></div>`,
            footer: '<button class="ns-btn ns-btn-ghost" data-ns-close>Huỷ</button><button class="ns-btn ns-btn-primary" id="sk-ok">Thêm</button>' });
        c.querySelector('#sk-file').onchange = async (e) => { const f = e.target.files[0]; if (!f) return; try { const u = await withLoading(() => upload(f, { doctype: 'Employee', docname: name }), 'Đang tải…'); c.querySelector('[data-field="tep"]').value = u.file_url; c.querySelector('#sk-file-name').textContent = f.name; } catch (err) { showToast(err.message, 'error'); } };
        c.querySelector('#sk-ok').onclick = async () => {
            const a = { employee: name }; c.querySelectorAll('[data-field]').forEach((i) => { a[i.dataset.field] = readValue(i); });
            if (!a.ngay || !a.loai) { showToast('Thiếu ngày hoặc loại', 'warning'); return; }
            try { await withLoading(() => ns.suKien.them(a)); closeModal(); showToast('Đã thêm sự kiện', 'success'); drawLichSu(); } catch (e) { showToast(e.message, 'error'); }
        };
    }
    function openSuaSk(skName, nd, td, nguon) {
        const c = showModal({ title: 'Sửa nội dung sự kiện', body: `<div class="ns-form-grid">${nguon === 'Tay' ? `<div class="ns-field ns-span-2"><label>Tiêu đề</label>${inputFor({ field: 'tieu_de', value: td })}</div>` : '<div class="ns-span-2 ns-text-sm ns-text-muted">Sự kiện tự động: chỉ bổ sung nội dung.</div>'}
            <div class="ns-field ns-span-2"><label>Nội dung</label>${inputFor({ field: 'noi_dung', fieldtype: 'Small Text', value: nd })}</div></div>`,
            footer: '<button class="ns-btn ns-btn-ghost" data-ns-close>Huỷ</button><button class="ns-btn ns-btn-primary" id="sk-ok">Lưu</button>' });
        c.querySelector('#sk-ok').onclick = async () => {
            const ndv = readValue(c.querySelector('[data-field="noi_dung"]')); const tdEl = c.querySelector('[data-field="tieu_de"]');
            try { await ns.suKien.suaNoiDung(skName, ndv, tdEl ? readValue(tdEl) : undefined); closeModal(); showToast('Đã lưu', 'success'); drawLichSu(); } catch (e) { showToast(e.message, 'error'); }
        };
    }

    // ───── Công & lương ─────
    async function drawLuong() {
        const now = new Date();
        if (!st.t) { st.t = now.getMonth() + 1; st.n = now.getFullYear(); }
        const mv = `${st.n}-${String(st.t).padStart(2, '0')}`;
        body.innerHTML = `<div class="ns-card"><div class="ns-filters"><label class="ns-field"><span class="ns-field-label">Tháng</span><input class="ns-input" type="month" id="cl-month" value="${mv}"></label><span class="ns-text-sm ns-text-muted">Chỉ đọc · sửa công → <a href="/chamcong2">Chấm công</a>, sửa phiếu → ERPNext</span></div><div id="cl-body">${skeleton(80, 3)}</div></div>`;
        body.querySelector('#cl-month').onchange = (e) => { const [n, t] = e.target.value.split('-'); st.t = Number(t); st.n = Number(n); replaceQuery({ tab: 'luong', t: st.t, n: st.n }); drawLuong(); };
        replaceQuery({ tab: 'luong', t: st.t, n: st.n });
        const el = body.querySelector('#cl-body');
        let d;
        try { d = await ns.congLuong(name, st.t, st.n); } catch (e) { el.innerHTML = `<div class="ns-risk-bar">${escapeHtml(e.message)}</div>`; return; }
        if (!d.phieu.length) { el.innerHTML = emptyState('🧾', `Chưa có phiếu tháng ${st.t}/${st.n}`); return; }
        el.innerHTML = d.phieu.map(phieuHtml).join('');
    }
    function phieuHtml(p) {
        const h = p.header || {};
        const nhat = p.loai === 'Nhật';
        const kpi = nhat ? [['Ngày SX', h.ngaysanxuat, 0], ['Công', h.congngay, 1], ['Làm thêm', h.lamthem, 1], ['Lương công', h.luongngaycong], ['Lương làm thêm', h.luonglamthem], ['Ăn ca', h.anca], ['Chuyên cần', h.chuyencan], ['Hỗ trợ ngày công', h.hotrongaycong], ['Hỗ trợ', h.hotro], ['Thưởng khác', h.thuongkhac], ['Thưởng thâm niên', h.thuongthamnien], ['Tổng tiền', h.tongtien], ['Bảo hiểm', h.baohiem], ['Tiền phạt', h.tienphat], ['Tổng khấu trừ', h.tongkhautru], ['THỰC NHẬN', h.luongthucnhan], ['Chuyển khoản', h.luongck]]
            : [['Ngày SX', h.ngay_san_xuat, 0], ['Công', h.ngay_cong, 1], ['Lương SP', h.luong_san_pham], ['Tiền ăn', h.tien_an], ['Chuyên cần', h.chuyen_can], ['Hỗ trợ ngày công', h.ho_tro_ngay_cong], ['Hỗ trợ', h.ho_tro], ['Thưởng thâm niên', h.thuong_tham_nien], ['Tổng tiền', h.tong_tien], ['Bảo hiểm', h.bao_hiem], ['Tiền phạt', h.tien_phat], ['Tổng khấu trừ', h.tong_khau_tru], ['THỰC NHẬN', h.luong_thuc_nhan]];
        const tt = nhat ? (h.status || '') : (h.trang_thai || '');
        return html`<div class="ns-section">
            <div class="ns-flex ns-items-center ns-justify-between ns-flex-wrap ns-gap-2 ns-mb-2">
                <div><b>${p.loai === 'Nhật' ? 'Lương công nhật' : 'Lương công khoán'}</b> · <span class="ns-sub">${p.name}</span>
                    <span class="ns-badge ${p.docstatus === 1 ? 'ns-badge-success' : 'ns-badge-warning'}">${p.docstatus === 1 ? 'Đã duyệt' : 'Nháp'}${tt ? ' · ' + tt : ''}</span>
                    ${p.trung ? raw('<span class="ns-badge ns-badge-danger">Trùng phiếu nháp</span>') : ''}</div>
                <div class="ns-actions">${nhat ? raw(`<a class="ns-btn ns-btn-sm" href="${escapeHtml(p.in_url)}" target="_blank">🖨️ In</a>`) : ''}<a class="ns-btn ns-btn-sm" href="${p.desk_url}" target="_blank">Mở trong ERPNext</a></div></div>
            <div class="ns-kpi-grid">${raw(kpi.map(([l, v, dg]) => `<div class="ns-kpi-card"><div class="ns-kpi-label">${escapeHtml(l)}</div><div class="ns-kpi-value ${l === 'THỰC NHẬN' ? 'success' : ''}" style="font-size:1.05rem">${dg === undefined ? formatNumber(v) : formatNumber(v, dg)}</div></div>`).join(''))}</div>
            ${p.dong?.length ? raw(`<div class="ns-section-title ns-mt-3">Bảng ngày (${p.dong.length})</div><div class="ns-table-wrap"><table class="ns-table"><thead><tr>${nhat ? '<th>Ngày</th><th class="ns-num">Công</th><th class="ns-num">Thêm giờ</th>' : '<th>Ngày</th><th>Thứ</th><th>Ăn ca</th><th>Ăn đêm</th><th class="ns-num">Tiền ăn</th><th class="ns-num">Lương SP</th><th class="ns-num">Hệ số</th><th class="ns-num">Thu nhập ngày</th>'}</tr></thead><tbody>
                ${p.dong.map((r) => nhat ? `<tr><td>${formatDate(r.ngay)}</td><td class="ns-num">${formatNumber(r.cong, 1)}</td><td class="ns-num">${formatNumber(r.them_gio, 1)}</td></tr>`
                    : `<tr><td>${formatDate(r.ngay)}</td><td>${escapeHtml(r.thu || '')}</td><td>${r.an_ca ? '✓' : ''}</td><td>${r.an_dem ? '✓' : ''}</td><td class="ns-num">${formatNumber(r.tien_an)}</td><td class="ns-num">${formatNumber(r.luong_sp)}</td><td class="ns-num">${formatNumber(r.he_so, 1)}</td><td class="ns-num">${formatNumber(r.thu_nhap_ngay)}</td></tr>`).join('')}</tbody></table></div>`) : ''}
            ${p.phat?.length ? raw(`<div class="ns-section-title ns-mt-3">Phạt (${p.phat.length})</div><div class="ns-table-wrap"><table class="ns-table"><thead><tr><th>Nội dung</th><th class="ns-num">SL</th><th class="ns-num">Giá</th><th class="ns-num">Thành tiền</th></tr></thead><tbody>${p.phat.map((r) => `<tr><td>${escapeHtml(r.noi_dung)}</td><td class="ns-num">${formatNumber(r.so_luong, 1)}</td><td class="ns-num">${formatNumber(r.gia_tien)}</td><td class="ns-num">${formatNumber(r.thanh_tien)}</td></tr>`).join('')}</tbody></table></div>`) : ''}
        </div>`;
    }

    drawBanner(); drawTabs(); drawBody();
    return () => {};
}
function trangThai(s) { return { Active: 'Đang làm', Inactive: 'Tạm nghỉ', Suspended: 'Tạm đình chỉ', Left: 'Đã nghỉ' }[s] || s || ''; }
