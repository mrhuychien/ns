// Tài khoản XEM LƯƠNG của công nhân — các bước dùng chung cho màn #/tai-khoan và ô tài khoản ở hồ sơ.
// Quyền thật ở server (ns.api.tai_khoan: tạo / cấp lại / khoá / gỡ chỉ HR Manager). Mật khẩu chỉ hiện MỘT lần.
import { ns } from '../lib/api.js';
import { escapeHtml as esc, formatDateTime } from '../lib/format.js';
import { showToast, withLoading } from './toast.js';
import { showModal, closeModal, confirmModal } from './modal.js';
import { moTrangInTheDangNhap } from '../lib/inthe.js';

const CTX = window.NS_CONTEXT || {};
export const coQuyenSua = () => !!CTX.isManager;

/** Nhãn trạng thái tài khoản (cột / ô trong hồ sơ). */
export function tkHtml(tk) {
    if (!tk) return '<span class="ns-badge ns-badge-muted">Chưa có tài khoản</span>';
    if (!tk.co_that) return `<span class="ns-badge ns-badge-danger">Tài khoản ${esc(tk.user)} không còn</span>`;
    return `<span class="ns-badge ${tk.bat ? 'ns-badge-success' : 'ns-badge-danger'}">${tk.bat ? 'Đang dùng' : 'Đã khoá'}</span>
        <b>${esc(tk.sdt || tk.user)}</b>${tk.rieng ? '' : ' <span class="ns-badge ns-badge-primary" title="Tài khoản có thêm chức năng khác (app sx / Desk) — mật khẩu quản ở nơi cấp">dùng chung</span>'}
        <div class="ns-sub">${tk.lan_cuoi ? `đăng nhập lần cuối ${esc(formatDateTime(tk.lan_cuoi))}` : 'chưa đăng nhập lần nào'}</div>`;
}

/** Nút thao tác cho một nhân viên (data-tk-* để màn gọi bắt sự kiện). */
export function tkNutHtml(nv) {
    if (!coQuyenSua()) return '';
    const tk = nv.tai_khoan;
    const e = esc(nv.employee);
    if (!tk) return `<button class="ns-btn ns-btn-sm ns-btn-primary" data-tk-tao="${e}">＋ Tạo tài khoản</button>`;
    const nut = [];
    if (tk.rieng && tk.co_that) {
        nut.push(`<button class="ns-btn ns-btn-sm" data-tk-caplai="${e}">Cấp lại mật khẩu</button>`);
        nut.push(tk.bat ? `<button class="ns-btn ns-btn-sm" data-tk-khoa="${e}">Khoá</button>`
            : `<button class="ns-btn ns-btn-sm" data-tk-mo="${e}">Mở khoá</button>`);
    }
    nut.push(`<button class="ns-btn ns-btn-sm ns-btn-ghost" data-tk-go="${e}" title="Gỡ tài khoản khỏi hồ sơ này">Gỡ</button>`);
    return nut.join('');
}

/** Gắn sự kiện cho mọi nút data-tk-* trong root. timNv(employee) → dòng nhân viên; xong(): tải lại. */
export function ganNutTaiKhoan(root, timNv, xong) {
    root.querySelectorAll('[data-tk-tao]').forEach((b) => { b.onclick = () => taoTaiKhoan(timNv(b.dataset.tkTao), xong); });
    root.querySelectorAll('[data-tk-caplai]').forEach((b) => { b.onclick = () => capLai(timNv(b.dataset.tkCaplai), xong); });
    root.querySelectorAll('[data-tk-khoa]').forEach((b) => { b.onclick = () => khoaMo(timNv(b.dataset.tkKhoa), true, xong); });
    root.querySelectorAll('[data-tk-mo]').forEach((b) => { b.onclick = () => khoaMo(timNv(b.dataset.tkMo), false, xong); });
    root.querySelectorAll('[data-tk-go]').forEach((b) => { b.onclick = () => goTk(timNv(b.dataset.tkGo), xong); });
}

/** Kết quả cấp / cấp lại: mật khẩu hiện MỘT lần + nút in thẻ. ds = [{ten, employee, sdt, mat_khau, url, lien_ket}] */
export function ketQua(ds, { tieuDe = 'Đã cấp tài khoản', loi = [] } = {}) {
    const coMk = ds.some((x) => x.mat_khau);
    const c = showModal({
        title: tieuDe, wide: ds.length > 1,
        body: `${coMk ? '<div class="ns-risk-bar ns-warn-bar"><span>Mật khẩu chỉ hiện <b>MỘT LẦN</b> (hệ thống lưu dạng băm). In thẻ ngay, hoặc chép lại trước khi đóng.</span></div>' : ''}
            ${ds.length ? `<div class="ns-tk-list">${ds.map((x) => `<div class="ns-tk-row">
                <div class="ns-tk-who"><div class="ns-tk-name">${esc(x.ten)}</div><div class="ns-tk-meta">${esc(x.employee)} · đăng nhập: <b>${esc(x.sdt)}</b></div></div>
                <div>${x.mat_khau ? `<div class="ns-sub">Mật khẩu</div><div class="ns-tk-mk">${esc(x.mat_khau)}</div>`
        : `<div class="ns-sub">${x.dung_chung ? 'Gắn vào tài khoản dùng chung' : 'Gắn vào tài khoản sẵn có'} — đăng nhập bằng mật khẩu đang dùng</div>`}</div></div>`).join('')}</div>` : ''}
            ${loi.length ? `<div class="ns-section-title ns-mt-3">Chưa làm được (${loi.length})</div><div class="ns-risk-bar" style="display:block">${loi.map((x) => `<div><b>${esc(x.ten)}</b>: ${esc(x.msg)}</div>`).join('')}</div>` : ''}
            ${ds.length ? `<div class="ns-text-sm ns-text-muted ns-mt-2">Công nhân mở <b>${esc(ds[0].url)}</b> (hoặc quét QR trên thẻ), đăng nhập bằng số điện thoại + mật khẩu.</div>` : ''}`,
        footer: `${ds.length ? '<button class="ns-btn ns-btn-primary" id="tk-in">🖨️ In thẻ</button>' : ''}<button class="ns-btn" data-ns-close>Đóng</button>`,
    });
    const nutIn = c && c.querySelector('#tk-in');
    if (nutIn) {
        nutIn.onclick = () => {
            if (!moTrangInTheDangNhap(ds)) showToast('Trình duyệt chặn cửa sổ in — cho phép pop-up rồi bấm lại.', 'warning', 6000);
        };
    }
    return c;
}

function hoiSdt(nv) {
    return new Promise((resolve) => {
        const c = showModal({
            title: 'Tạo tài khoản xem lương',
            body: `<p><b>${esc(nv.employee_name)}</b> · ${esc(nv.employee)}</p>
                <div class="ns-field ns-mt-2"><label>Số điện thoại (tên đăng nhập) *</label>
                <input class="ns-input" id="tk-sdt" inputmode="tel" autocomplete="off" value="${esc(nv.cell_number || '')}" placeholder="0912345678"></div>
                <div class="ns-text-sm ns-text-muted ns-mt-2">Hệ thống tự đặt mật khẩu, hiện một lần để in thẻ. Công nhân chỉ xem được phiếu lương <b>đã duyệt</b> của chính mình.</div>`,
            footer: '<button class="ns-btn ns-btn-ghost" data-ns-close>Huỷ</button><button class="ns-btn ns-btn-primary" id="tk-ok">Tạo tài khoản</button>',
        });
        let xong = false;
        const ip = c.querySelector('#tk-sdt');
        const ok = () => { xong = true; const v = ip.value.trim(); closeModal(); resolve(v); };
        c.querySelector('#tk-ok').onclick = ok;
        ip.onkeydown = (e) => { if (e.key === 'Enter') ok(); };
        setTimeout(() => ip.focus(), 50);
        // đóng bằng ✕ / Huỷ / bấm nền
        const mount = document.getElementById('ns-modal-mount');
        const cu = mount.onclick;
        mount.onclick = (e) => { if (!xong && (e.target === mount || e.target.closest('[data-ns-close]'))) resolve(null); if (cu) cu(e); };
    });
}

export async function taoTaiKhoan(nv, xong) {
    if (!nv) return;
    const sdt = await hoiSdt(nv);
    if (sdt === null) return;
    try {
        let r = await withLoading(() => ns.taiKhoan.tao(nv.employee, sdt), 'Đang tạo…');
        if (r.can_xac_nhan) {
            const dongY = await confirmModal('Số này đã có tài khoản',
                `Số ${r.sdt} đã có tài khoản "${r.ten_tai_khoan}"${r.dung_chung ? ' (đang dùng cho chức năng khác: app sx / Desk)' : ''}${r.bat ? '' : ' — đang khoá'}. `
                + `Gắn tài khoản đó vào hồ sơ ${r.ten}? Chủ tài khoản sẽ xem được phiếu lương của hồ sơ này — chỉ đồng ý khi đúng là cùng một người.`,
                { okLabel: 'Đúng người — gắn' });
            if (!dongY) return;
            r = await withLoading(() => ns.taiKhoan.tao(nv.employee, sdt, 1), 'Đang gắn…');
        }
        ketQua([r], { tieuDe: r.lien_ket ? 'Đã gắn tài khoản' : 'Đã cấp tài khoản' });
        if (xong) xong();
    } catch (e) { showToast(e.message, 'error', 6000); }
}

export async function capLai(nv, xong) {
    if (!nv) return;
    if (!await confirmModal('Cấp lại mật khẩu', `Đặt mật khẩu MỚI cho ${nv.employee_name}? Mật khẩu cũ hết dùng được và mọi máy đang đăng nhập bị đăng xuất.`, { okLabel: 'Cấp lại' })) return;
    try {
        const r = await withLoading(() => ns.taiKhoan.capLai(nv.employee), 'Đang cấp lại…');
        ketQua([r], { tieuDe: 'Đã cấp lại mật khẩu' });
        if (xong) xong();
    } catch (e) { showToast(e.message, 'error', 6000); }
}

export async function khoaMo(nv, khoa, xong) {
    if (!nv) return;
    if (khoa && !await confirmModal('Khoá tài khoản', `Khoá tài khoản của ${nv.employee_name}? Người đó bị đăng xuất và không đăng nhập được nữa cho tới khi mở lại.`, { okLabel: 'Khoá', danger: true })) return;
    try {
        await withLoading(() => ns.taiKhoan.khoa(nv.employee, khoa ? 1 : 0));
        showToast(khoa ? 'Đã khoá tài khoản' : 'Đã mở khoá', 'success');
        if (xong) xong();
    } catch (e) { showToast(e.message, 'error', 6000); }
}

export async function goTk(nv, xong) {
    if (!nv) return;
    const tk = nv.tai_khoan || {};
    if (!await confirmModal('Gỡ tài khoản', `Gỡ tài khoản ${tk.sdt || tk.user || ''} khỏi hồ sơ ${nv.employee_name}? Người đó hết xem được phiếu lương ngay.${tk.rieng ? ' Tài khoản riêng này sẽ bị khoá.' : ' Tài khoản dùng chung giữ nguyên cho chức năng khác.'}`, { okLabel: 'Gỡ', danger: true })) return;
    try {
        await withLoading(() => ns.taiKhoan.go(nv.employee));
        showToast('Đã gỡ tài khoản', 'success');
        if (xong) xong();
    } catch (e) { showToast(e.message, 'error', 6000); }
}

/** Tạo hàng loạt (chỉ người CHƯA có tài khoản và SĐT chưa thuộc tài khoản nào — trùng thì để làm riêng từng người). */
export async function taoHangLoat(dsNv, xong) {
    const ds = dsNv.filter((x) => !x.tai_khoan);
    if (!ds.length) { showToast('Không có ai cần tạo', 'warning'); return; }
    if (!await confirmModal('Tạo tài khoản hàng loạt', `Tạo tài khoản cho ${ds.length} người theo số điện thoại trên hồ sơ? Người chưa có / sai số điện thoại, hoặc số đã có tài khoản, sẽ được liệt kê để làm riêng.`, { okLabel: `Tạo ${ds.length} tài khoản` })) return;
    const ok = []; const loi = [];
    await withLoading(async () => {
        for (const nv of ds) {
            try {
                const r = await ns.taiKhoan.tao(nv.employee, nv.cell_number || '');
                if (r.can_xac_nhan) loi.push({ ten: nv.employee_name, msg: `số ${r.sdt} đã có tài khoản "${r.ten_tai_khoan}" — bấm Tạo tài khoản ở dòng này để xác nhận gắn` });
                else ok.push(r);
            } catch (e) { loi.push({ ten: nv.employee_name, msg: e.message }); }
        }
    }, `Đang tạo ${ds.length} tài khoản…`);
    ketQua(ok, { tieuDe: `Đã cấp ${ok.length}/${ds.length} tài khoản`, loi });
    if (xong) xong();
}
