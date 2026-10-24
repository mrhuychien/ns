// #/bo-sung?bp= — Bổ sung thông tin còn thiếu: tiến độ, lưới NV × field, Excel
import { ns, upload } from '../lib/api.js';
import { html, raw, skeleton, emptyState, debounce } from '../lib/dom.js';
import { escapeHtml } from '../lib/format.js';
import { replaceQuery } from '../lib/router.js';
import { showToast, withLoading } from '../components/toast.js';
import { showModal, closeModal } from '../components/modal.js';
import { inputFor, readValue, displayValue } from '../components/field.js';

const CTX = window.NS_CONTEXT || {};
const bpLabel = (d) => (d === '__none__' ? 'Chưa có bộ phận' : d || 'Tất cả');

export async function render({ container, query = {}, setHeader }) {
    const st = { bp: query.bp || '', chiThieu: query.all !== '1', q: '', col: query.col || '', tq: null, luoi: null };
    setHeader('Bổ sung hồ sơ');
    container.innerHTML = html`
        <div class="ns-card" id="bs-progress">${raw(skeleton(60))}</div>
        <div class="ns-filters ns-mt-3">
            <div class="ns-chips" id="bs-bp"></div>
        </div>
        <div class="ns-filters">
            <label class="ns-flex ns-items-center ns-gap-2 ns-text-sm"><span class="ns-switch"><input type="checkbox" id="bs-chithieu" ${st.chiThieu ? 'checked' : ''}><span></span></span> Chỉ người còn thiếu</label>
            <div class="ns-search"><input type="search" id="bs-q" placeholder="Tìm tên"></div>
            <div class="ns-actions"><button class="ns-btn ns-btn-sm" id="bs-mau">⬇️ Tải mẫu Excel</button><label class="ns-btn ns-btn-sm ns-btn-primary">⬆️ Nhập file<input type="file" accept=".xlsx" hidden id="bs-file"></label></div>
        </div>
        <div id="bs-grid">${raw(skeleton(300))}</div>
        <div class="ns-text-sm ns-text-muted ns-mt-2">Ô vàng = thiếu · ô gạch chéo = không áp dụng · click ô để sửa, Enter/blur lưu ngay, Tab sang ô thiếu kế tiếp · Giấy tờ chỉ đếm, bấm để mở hồ sơ.</div>`;

    const progEl = container.querySelector('#bs-progress');
    const gridEl = container.querySelector('#bs-grid');
    function sync() { replaceQuery({ bp: st.bp, all: st.chiThieu ? '' : '1', col: st.col }); }

    function drawBp() {
        const el = container.querySelector('#bs-bp');
        el.innerHTML = [html`<button class="ns-chip ${!st.bp ? 'ns-active' : ''}" data-bp="">Tất cả</button>`].concat((CTX.departments || []).map((d) => html`<button class="ns-chip ${st.bp === d ? 'ns-active' : ''}" data-bp="${d}">${bpLabel(d)}</button>`)).join('');
        el.querySelectorAll('[data-bp]').forEach((b) => { b.onclick = () => { st.bp = b.dataset.bp; drawBp(); sync(); loadAll(); }; });
    }
    async function loadAll() {
        progEl.innerHTML = skeleton(60); gridEl.innerHTML = skeleton(300);
        try {
            const [tq, luoi] = await Promise.all([ns.boSung.tongQuan(st.bp || null), ns.boSung.luoi(st.bp || null, st.chiThieu)]);
            st.tq = tq; st.luoi = luoi;
            drawProgress(); drawGrid();
        } catch (e) { gridEl.innerHTML = `<div class="ns-risk-bar">${escapeHtml(e.message)}</div>`; }
    }
    function drawProgress() {
        const t = st.tq.tong_hop;
        const p = t.so_nv ? Math.round(100 * t.so_du / t.so_nv) : 100;
        progEl.innerHTML = html`<div class="ns-flex ns-justify-between ns-items-center ns-flex-wrap ns-gap-2">
            <div><div class="ns-label">Hồ sơ đủ</div><div class="ns-kpi-value">${t.so_du}/${t.so_nv} <span class="ns-text-sm ns-text-muted">(${p}%) · trung bình ${t.trung_binh_pct}%</span></div></div>
            <div class="ns-text-sm ns-text-muted">${bpLabel(st.bp)}</div></div>
            <div class="ns-progress ns-mt-2"><span style="width:${p}%"></span></div>
            <div class="ns-chips ns-mt-3" id="bs-cols">${raw(t.thieu_theo_field.map((x) => html`<button class="ns-chip ns-chip-warn ${st.col === x.field ? 'ns-active' : ''}" data-col="${x.field}">${x.label} <b>${x.so_luong}</b></button>`).join(''))}${t.thieu_theo_field.length ? '' : raw('<span class="ns-badge ns-badge-success">Không còn thiếu gì 🎉</span>')}</div>`;
        progEl.querySelectorAll('[data-col]').forEach((b) => { b.onclick = () => { st.col = st.col === b.dataset.col ? '' : b.dataset.col; sync(); drawProgress(); drawGrid(); }; });
    }

    // ───── lưới ─────
    function drawGrid() {
        const L = st.luoi;
        let cols = L.cot;
        const gts = L.giay_to;
        if (st.col && !st.col.startsWith('gt_')) cols = cols.filter((c) => c.field === st.col);
        const gtShow = st.col ? gts.filter((g) => g.ma === st.col) : gts;
        let rows = L.dong;
        if (st.q) { const q = st.q.toLowerCase(); rows = rows.filter((r) => (r.employee_name || '').toLowerCase().includes(q) || r.name.toLowerCase().includes(q)); }
        if (st.col) rows = rows.filter((r) => r.thieu.includes(st.col));
        if (!rows.length) { gridEl.innerHTML = emptyState('✅', 'Không có ai cần bổ sung', st.col ? 'theo cột đang lọc' : ''); return; }
        const groups = [];
        cols.forEach((c) => { const g = groups[groups.length - 1]; if (g && g.nhom === c.nhom) g.n++; else groups.push({ nhom: c.nhom, n: 1 }); });
        if (gtShow.length) groups.push({ nhom: 'Giấy tờ', n: gtShow.length });
        gridEl.innerHTML = `<div class="ns-text-sm ns-text-muted ns-mb-2">${rows.length} người</div><div class="ns-grid-wrap"><table class="ns-grid"><thead>
            <tr><th class="ns-grid-name" rowspan="2">Nhân viên</th>${groups.map((g) => `<th class="ns-grid-group" colspan="${g.n}">${escapeHtml(g.nhom)}</th>`).join('')}</tr>
            <tr>${cols.map((c) => `<th class="ns-grid-sub">${escapeHtml(c.label)}</th>`).join('')}${gtShow.map((g) => `<th class="ns-grid-sub">${escapeHtml(g.label.replace('Giấy tờ: ', ''))}</th>`).join('')}</tr></thead><tbody>
            ${rows.map((r) => `<tr data-nv="${escapeHtml(r.name)}"><td class="ns-grid-name"><a href="#/nv/${escapeHtml(r.name)}" style="font-weight:700">${escapeHtml(r.employee_name)}</a><div class="ns-sub">${escapeHtml(r.department || '—')} · <span data-pct>${r.pct_du}%</span></div></td>
                ${cols.map((c) => cellHtml(r, c)).join('')}
                ${gtShow.map((g) => `<td class="ns-gt ${r.giay_to[g.ma] ? '' : 'ns-thieu'}"><a class="ns-cell" href="#/nv/${escapeHtml(r.name)}?tab=giayto" title="${escapeHtml(g.label)}">${r.giay_to[g.ma] ? '✓' : '—'}</a></td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
        gridEl.querySelectorAll('td[data-field]').forEach((td) => { td.onclick = () => startEdit(td); });
    }
    function cellHtml(r, c) {
        const o = r.o[c.field] || {};
        const cls = !o.ap_dung ? 'ns-na' : o.thieu ? 'ns-thieu' : '';
        return `<td class="${cls}" data-field="${escapeHtml(c.field)}" data-ft="${escapeHtml(c.fieldtype)}" ${o.ap_dung ? '' : 'data-na="1"'}><span class="ns-cell" title="${escapeHtml(c.label)}">${o.ap_dung ? escapeHtml(displayValue(c.fieldtype, o.gia_tri)) : ''}</span></td>`;
    }
    function startEdit(td) {
        if (td.dataset.na || td.classList.contains('ns-editing')) return;
        const tr = td.closest('tr'); const emp = tr.dataset.nv; const field = td.dataset.field;
        const col = st.luoi.cot.find((c) => c.field === field);
        const row = st.luoi.dong.find((d) => d.name === emp);
        const cur = row.o[field].gia_tri;
        td.classList.add('ns-editing');
        const cell = td.querySelector('.ns-cell');
        cell.innerHTML = inputFor({ field, fieldtype: col.fieldtype, options: col.options, value: cur });
        const input = cell.querySelector('[data-field]');
        input.focus(); if (input.select) try { input.select(); } catch (e) { /* */ }
        let done = false;
        const finish = async (save, next) => {
            if (done) return; done = true;
            const v = readValue(input);
            if (!save || String(v ?? '') === String(cur ?? '')) { restore(td, col, cur, row); if (next) tabNext(tr, td); return; }
            try {
                const r = await ns.boSung.luuO(emp, field, v);
                Object.assign(row, { o: r.o, thieu: r.thieu, pct_du: r.pct_du, giay_to: r.giay_to });
                restore(td, col, r.o[field].gia_tri, row); td.classList.remove('ns-thieu'); td.classList.add('ns-ok-moi');
                tr.querySelector('[data-pct]').textContent = r.pct_du + '%';
                // cập nhật các ô khác của hàng (áp dụng/thiếu có thể đổi — vd bật BHXH)
                tr.querySelectorAll('td[data-field]').forEach((x) => { if (x !== td) { const c2 = st.luoi.cot.find((c) => c.field === x.dataset.field); const o = r.o[c2.field]; x.className = !o.ap_dung ? 'ns-na' : o.thieu ? 'ns-thieu' : (x.classList.contains('ns-ok-moi') ? 'ns-ok-moi' : ''); if (o.ap_dung) x.removeAttribute('data-na'); else x.dataset.na = '1'; x.querySelector('.ns-cell').textContent = o.ap_dung ? displayValue(c2.fieldtype, o.gia_tri) : ''; } });
                refreshProgress(field, row);
                if (next) tabNext(tr, td);
            } catch (e) {
                done = false; td.classList.add('ns-loi'); td.title = e.message; showToast(e.message, 'error');
                input.classList.add('ns-invalid'); input.focus();
            }
        };
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') { e.preventDefault(); finish(true, false); }
            else if (e.key === 'Escape') { finish(false, false); }
            else if (e.key === 'Tab') { e.preventDefault(); finish(true, true); }
        });
        input.addEventListener('blur', () => setTimeout(() => finish(true, false), 120));
        if (input.type === 'checkbox' || input.tagName === 'SELECT') input.addEventListener('change', () => finish(true, false));
    }
    function restore(td, col, v, row) { td.classList.remove('ns-editing', 'ns-loi'); td.removeAttribute('title'); td.querySelector('.ns-cell').textContent = displayValue(col.fieldtype, v); td.onclick = () => startEdit(td); }
    function tabNext(tr, td) {
        const cells = Array.from(tr.querySelectorAll('td[data-field]'));
        const i = cells.indexOf(td);
        const nxt = cells.slice(i + 1).find((x) => x.classList.contains('ns-thieu')) || cells.slice(i + 1).find((x) => !x.dataset.na);
        if (nxt) startEdit(nxt);
    }
    async function refreshProgress() {
        try { st.tq = await ns.boSung.tongQuan(st.bp || null); drawProgress(); } catch (e) { /* im lặng */ }
    }

    // ───── Excel ─────
    container.querySelector('#bs-mau').onclick = async () => { try { await withLoading(() => ns.boSung.mauExcel(st.bp || null), 'Đang tạo file…'); } catch (e) { showToast(e.message, 'error'); } };
    container.querySelector('#bs-file').onchange = async (e) => {
        const f = e.target.files[0]; e.target.value = ''; if (!f) return;
        try {
            const up = await withLoading(() => upload(f, { doctype: null, docname: null, isPrivate: 1 }), 'Đang tải file…');
            const xem = await withLoading(() => ns.boSung.xemTruoc(up.file_url), 'Đang đọc file…');
            openDiff(up.file_url, xem);
        } catch (err) { showToast(err.message, 'error'); }
    };
    function openDiff(fileUrl, xem) {
        const rows = xem.dong;
        const body = rows.length ? `<div class="ns-text-sm ns-mb-2">${xem.so_nv_thay_doi} nhân viên có thay đổi · ${xem.so_dong_loi} dòng lỗi (đỏ, sẽ bỏ qua). Ô trống trong Excel không xoá dữ liệu cũ.</div>
            <div class="ns-table-wrap" style="max-height:60vh;overflow:auto"><table class="ns-table"><thead><tr><th><input type="checkbox" id="df-all" checked></th><th>Nhân viên</th><th>Thay đổi (cũ → mới)</th></tr></thead><tbody>
            ${rows.map((r) => { const loi = r.loi || r.thay_doi.some((t) => t.loi); return `<tr class="${loi ? 'ns-row-do' : ''}"><td>${loi ? '' : `<input type="checkbox" data-pick="${escapeHtml(r.employee)}" checked>`}</td>
                <td><b>${escapeHtml(r.employee_name || r.employee)}</b><div class="ns-sub">${escapeHtml(r.employee)}</div>${r.loi ? `<div class="ns-field-err">${escapeHtml(r.loi)}</div>` : ''}</td>
                <td style="white-space:normal">${r.thay_doi.map((t) => `<div class="${t.loi ? 'ns-field-err' : ''}"><b>${escapeHtml(t.label)}</b>: ${escapeHtml(fmt(t.cu))} → <b>${escapeHtml(fmt(t.moi))}</b>${t.loi ? ` — ${escapeHtml(t.loi)}` : ''}</div>`).join('')}</td></tr>`; }).join('')}</tbody></table></div>`
            : emptyState('🟰', 'Không có thay đổi nào', 'File giống dữ liệu hiện có hoặc không khớp Mã NV.');
        const c = showModal({ title: 'Xem trước nhập Excel', wide: true, body, footer: `<button class="ns-btn ns-btn-ghost" data-ns-close>Đóng</button>${rows.length ? '<button class="ns-btn ns-btn-primary" id="df-apply">✅ Áp dụng</button>' : ''}` });
        const all = c.querySelector('#df-all'); if (all) all.onchange = () => c.querySelectorAll('[data-pick]').forEach((x) => { x.checked = all.checked; });
        const ap = c.querySelector('#df-apply');
        if (ap) ap.onclick = async () => {
            const picks = Array.from(c.querySelectorAll('[data-pick]:checked')).map((x) => x.dataset.pick);
            if (!picks.length) { showToast('Chưa chọn nhân viên nào', 'warning'); return; }
            try {
                const r = await withLoading(() => ns.boSung.apDung(fileUrl, picks), 'Đang áp dụng…');
                closeModal();
                showToast(`Đã cập nhật ${r.thanh_cong} nhân viên${r.loi.length ? `, ${r.loi.length} lỗi` : ''}`, r.loi.length ? 'warning' : 'success', 5000);
                if (r.loi.length) showModal({ title: 'Lỗi khi áp dụng', body: `<ul>${r.loi.map((l) => `<li><b>${escapeHtml(l.employee)}</b>: ${escapeHtml(l.msg)}</li>`).join('')}</ul>`, footer: '<button class="ns-btn" data-ns-close>Đóng</button>' });
                loadAll();
            } catch (e) { showToast(e.message, 'error'); }
        };
    }
    function fmt(v) { return v === null || v === undefined || v === '' ? '—' : String(v); }

    container.querySelector('#bs-chithieu').onchange = (e) => { st.chiThieu = e.target.checked; sync(); loadAll(); };
    container.querySelector('#bs-q').addEventListener('input', debounce((e) => { st.q = e.target.value.trim(); drawGrid(); }, 200));
    drawBp(); sync(); loadAll();
    return () => {};
}
