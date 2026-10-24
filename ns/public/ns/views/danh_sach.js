// #/ — Danh sách NLĐ: 4 tab, lọc bộ phận, tìm, + Thêm người
import { ns } from '../lib/api.js';
import { html, raw, skeleton, emptyState, debounce } from '../lib/dom.js';
import { escapeHtml, formatNumber, formatDate, initials } from '../lib/format.js';
import { replaceQuery } from '../lib/router.js';
import { pref, setPref } from '../lib/store.js';
import { showToast, withLoading } from '../components/toast.js';
import { showModal, closeModal } from '../components/modal.js';
import { paged } from '../components/table.js';
import { inputFor, readValue } from '../components/field.js';
import { canhBaoIcons } from '../components/canh_bao.js';

const CTX = window.NS_CONTEXT || {};
const TABS = [
    { key: 'bhxh', label: 'Đóng BHXH' }, { key: 'khong_bhxh', label: 'Không đóng BHXH' },
    { key: 'tam_nghi', label: 'Tạm nghỉ' }, { key: 'da_nghi', label: 'Đã nghỉ' },
];
const bpLabel = (d) => (d === '__none__' ? 'Chưa có bộ phận' : d || '—');

export async function render({ container, query = {}, setHeader }) {
    const state = { tab: query.tab || pref('ds_tab', 'bhxh'), bp: query.bp || '', q: query.q || '', data: null };
    setHeader('Nhân sự RVHG', { actions: '<button class="ns-btn ns-btn-primary ns-btn-sm" id="ns-add-emp">+ Thêm người</button>' });
    document.getElementById('ns-add-emp').onclick = () => openTao();

    container.innerHTML = html`
        <div class="ns-tabs" id="ds-tabs"></div>
        <div class="ns-filters">
            <div class="ns-search"><input id="ds-q" type="search" placeholder="Tìm tên / CCCD / mã máy / mã NV" value="${state.q}"></div>
        </div>
        <div class="ns-chips ns-mb-3" id="ds-bp"></div>
        <div id="ds-body">${raw(skeleton(60, 6))}</div>`;

    const tabsEl = container.querySelector('#ds-tabs');
    const bpEl = container.querySelector('#ds-bp');
    const body = container.querySelector('#ds-body');

    function drawTabs(tong = {}) {
        tabsEl.innerHTML = TABS.map((t) => html`<button class="ns-tab ${t.key === state.tab ? 'ns-active' : ''}" data-tab="${t.key}">${t.label} <span class="ns-count">${tong[t.key] ?? '…'}</span></button>`).join('');
        tabsEl.querySelectorAll('[data-tab]').forEach((b) => { b.onclick = () => { state.tab = b.dataset.tab; setPref('ds_tab', state.tab); sync(); load(); }; });
    }
    function drawBp() {
        const deps = CTX.departments || [];
        bpEl.innerHTML = [html`<button class="ns-chip ${!state.bp ? 'ns-active' : ''}" data-bp="">Tất cả</button>`]
            .concat(deps.map((d) => html`<button class="ns-chip ${state.bp === d ? 'ns-active' : ''}" data-bp="${d}">${bpLabel(d)}</button>`)).join('');
        bpEl.querySelectorAll('[data-bp]').forEach((b) => { b.onclick = () => { state.bp = b.dataset.bp; drawBp(); sync(); load(); }; });
    }
    function sync() { replaceQuery({ tab: state.tab, bp: state.bp, q: state.q }); }

    async function load() {
        body.innerHTML = skeleton(60, 6);
        try {
            const data = await ns.nhanVien.danhSach({ tab: state.tab, department: state.bp || null, q: state.q || null });
            state.data = data;
            drawTabs(data.tong_so);
            drawRows(data.dong);
        } catch (e) { body.innerHTML = `<div class="ns-risk-bar">${escapeHtml(e.message)}</div>`; }
    }

    function rowTable(rows, start) {
        return `<div class="ns-table-wrap"><table class="ns-table"><thead><tr>
            <th>#</th><th>Mã</th><th>Họ tên</th><th>Bộ phận</th><th>Loại</th><th>Ngày vào</th><th class="ns-num">Thâm niên</th>
            <th class="ns-num">BHXH</th><th class="ns-num">Lương CB</th><th>SĐT</th><th class="ns-num">Hồ sơ</th><th>Cảnh báo</th></tr></thead><tbody>
            ${rows.map((r, i) => html`<tr class="ns-clickable" data-nv="${r.name}">
                <td class="ns-text-muted">${start + i + 1}</td><td><span class="ns-sub">${r.name}</span></td>
                <td><b>${r.employee_name}</b></td><td>${bpLabel(r.department)}</td>
                <td><span class="ns-badge ${r.loai_luong === 'Khoán' ? 'ns-badge-primary' : 'ns-badge-muted'}">${r.loai_luong}</span></td>
                <td>${formatDate(r.date_of_joining)}</td><td class="ns-num">${r.tham_nien_nam == null ? '—' : r.tham_nien_nam + ' năm'}</td>
                <td class="ns-num">${r.bao_hiem > 0 ? formatNumber(r.bao_hiem) : (r.ns_dong_bhxh ? raw('<span class="ns-badge ns-badge-warning">chưa mức</span>') : '—')}</td>
                <td class="ns-num">${r.luong_cb > 0 ? formatNumber(r.luong_cb) : '—'}</td><td>${r.cell_number || '—'}</td>
                <td class="ns-num">${raw(pctBadge(r.pct_du))}</td><td>${raw(canhBaoIcons(r.canh_bao))}</td></tr>`).join('')}
            </tbody></table></div>`;
    }
    function rowCards(rows) {
        return `<div class="ns-emp-list">${rows.map((r) => html`<a class="ns-emp-card" href="#/nv/${r.name}">
            <div class="ns-avatar">${r.image ? raw(`<img src="${escapeHtml(r.image)}" alt="">`) : initials(r.employee_name)}</div>
            <div><div class="ns-emp-name">${r.employee_name}</div>
                <div class="ns-emp-meta"><span>${bpLabel(r.department)}</span><span>· ${r.loai_luong}</span>${r.cell_number ? raw(`<span>· ${escapeHtml(r.cell_number)}</span>`) : ''}</div>
                <div class="ns-emp-meta">${raw(canhBaoIcons(r.canh_bao, 5))}</div></div>
            <div class="ns-emp-right"><span>${r.bao_hiem > 0 ? 'BH ' + formatNumber(r.bao_hiem) : (r.ns_dong_bhxh ? 'BH chưa mức' : 'Không BHXH')}</span>
                <span>${r.luong_cb > 0 ? 'CB ' + formatNumber(r.luong_cb) : ''}</span>${raw(pctBadge(r.pct_du))}</div></a>`).join('')}</div>`;
    }
    function drawRows(rows) {
        if (!rows.length) { body.innerHTML = emptyState('📭', 'Không có ai trong danh sách này', state.q ? 'Thử từ khoá khác' : ''); return; }
        body.innerHTML = `<div class="ns-text-sm ns-text-muted ns-mb-2">${rows.length} người</div>
            <div class="ns-emp-table">${paged({ rows, pageSize: 25, render: rowTable, onDraw: (el) => el.querySelectorAll('[data-nv]').forEach((tr) => { tr.onclick = () => { location.hash = '#/nv/' + tr.dataset.nv; }; }) })}</div>
            ${paged({ rows, pageSize: 25, render: rowCards })}`;
        // paged() trả 2 bản (table/cards) — CSS ẩn 1 theo breakpoint; wrapper thứ 2 cần class để ẩn trên desktop
        const wraps = body.querySelectorAll('.ns-paged'); if (wraps[1]) wraps[1].classList.add('ns-emp-list-wrap');
    }
    container.querySelector('#ds-q').addEventListener('input', debounce((e) => { state.q = e.target.value.trim(); sync(); load(); }, 300));

    drawTabs(); drawBp(); sync(); load();
    return () => {};
}
function pctBadge(p) {
    if (p == null) return '';
    const cls = p >= 100 ? 'success' : p >= 70 ? 'warning' : 'danger';
    return `<span class="ns-badge ns-badge-${cls}" title="Hồ sơ đủ ${p}%">${p}%</span>`;
}

function openTao() {
    const tc = CTX;
    const deps = tc.departmentsAll || [];
    const body = `<div class="ns-form-grid">
        <div class="ns-field ns-span-2"><label>Họ tên đầy đủ *</label>${inputFor({ field: 'first_name', placeholder: 'Nguyễn Văn A' })}</div>
        <div class="ns-field"><label>Giới tính *</label>${inputFor({ field: 'gender', fieldtype: 'Select', options: ['Male', 'Female', 'Other'] })}</div>
        <div class="ns-field"><label>Ngày sinh *</label>${inputFor({ field: 'date_of_birth', fieldtype: 'Date' })}</div>
        <div class="ns-field"><label>Ngày vào làm *</label>${inputFor({ field: 'date_of_joining', fieldtype: 'Date', value: tc.today })}</div>
        <div class="ns-field"><label>Bộ phận</label>${inputFor({ field: 'department', fieldtype: 'Select', options: deps })}</div>
        <div class="ns-field"><label>CCCD</label>${inputFor({ field: 'custom_cccd', placeholder: '12 chữ số' })}</div>
        <div class="ns-field"><label>SĐT</label>${inputFor({ field: 'cell_number' })}</div>
    </div><div class="ns-text-sm ns-text-muted ns-mt-2">Giới tính lưu theo giá trị ERPNext (Male = Nam, Female = Nữ).</div>`;
    const c = showModal({ title: 'Thêm người lao động', body, footer: '<button class="ns-btn ns-btn-ghost" data-ns-close>Huỷ</button><button class="ns-btn ns-btn-primary" id="tao-ok">Tạo & mở hồ sơ</button>' });
    c.querySelector('#tao-ok').onclick = async () => {
        const data = {};
        c.querySelectorAll('[data-field]').forEach((i) => { const v = readValue(i); if (v !== null && v !== '') data[i.dataset.field] = v; });
        try {
            const r = await withLoading(() => ns.nhanVien.tao(data), 'Đang tạo…');
            closeModal(); showToast(`Đã tạo ${r.employee_name} (${r.name})`, 'success');
            location.hash = '#/nv/' + r.name;
        } catch (e) { showToast(e.message, 'error'); }
    };
}
