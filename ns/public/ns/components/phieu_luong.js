// Phiếu lương — dựng HTML từ view model của ns.api.phieu_luong. Port thẻ Phiếu lương của app sx (D110) + từng
// ngày (D234): đúng thứ tự phiếu giấy — các khoản → tổng thu nhập → trừ → thực nhận; sản phẩm trong tháng gộp theo
// mã; TỪNG NGÀY làm những gì (số lượng, đơn giá, thành tiền, cộng ngày); lỗi phạt.
//
// Dùng chung ba chỗ: tab Công & lương của hồ sơ, bảng lương tháng (nút Xem), trang công nhân /phieuluong.
// Mọi số lấy NGUYÊN từ server — component không tự nhân / cộng lại tiền (hai nơi tính là hai con số).
// Chỉ HTML thuần (không gắn sự kiện, không nút Desk): nút In / Mở ERPNext do màn của phòng nhân sự tự thêm.
import { escapeHtml as esc, formatNumber } from '../lib/format.js';

const so = (n) => formatNumber(Math.round(n || 0));
const dong = (n) => `${so(n)} đ`;
const ngayThang = (iso) => (iso ? `${String(iso).slice(8, 10)}/${String(iso).slice(5, 7)}` : '');

/** Nhãn trạng thái. Trang công nhân gọi phiếu nháp là "Tạm tính" — số còn đổi được. */
export function nhanTrangThai(p, { congNhan = false } = {}) {
    if (p.docstatus === 2) return '<span class="ns-badge ns-badge-danger">Đã huỷ</span>';
    if (p.docstatus === 1) return '<span class="ns-badge ns-badge-success">Đã duyệt</span>';
    return `<span class="ns-badge ns-badge-warning">${congNhan ? 'Tạm tính' : 'Nháp'}</span>`;
}

function hang(trai, phai, { phu = '', lop = '' } = {}) {
    return `<div class="ns-pl-row ${lop}"><div class="ns-pl-row-ten">${trai}${phu ? `<div class="ns-pl-phu">${phu}</div>` : ''}</div>
        <div class="ns-pl-row-so">${phai}</div></div>`;
}

/** Một ngày công khoán (D234): đầu ngày (ngày · thứ · chấm ăn), mỗi sản phẩm một dòng (làm theo giờ: số giờ × đơn
 * giá / giờ), rồi CỘNG NGÀY = thu nhập ngày của phiếu. Có hệ số (Chủ nhật / 1-1) hay tiền ăn thì ghi phép tính:
 * lương SP × hệ số + tiền ăn. */
export function veNgayKhoan(x) {
    const an = [x.an_ca ? 'ăn ca' : '', x.an_dem ? 'ăn đêm' : ''].filter(Boolean).join(' · ');
    const phepTinh = x.he_so > 1 || x.tien_an ? [
        x.luong_sp ? `lương SP ${so(x.luong_sp)}${x.he_so > 1 ? ` × ${formatNumber(x.he_so, 2)}` : ''}` : '',
        x.tien_an ? `tiền ăn ${so(x.tien_an)}` : '',
    ].filter(Boolean).join(' + ') : '';
    return `<tbody>
        <tr class="ns-pl-ngay-dau"><td colspan="4"><b>${esc(ngayThang(x.ngay))}${x.thu ? ` · ${esc(x.thu)}` : ''}</b>${
    an ? ` <span class="ns-pl-phu">· ${esc(an)}</span>` : ''}</td></tr>
        ${(x.sp || []).map((r) => `<tr>
            <td>${esc(r.ten || '')}${r.cach_lam ? ` <span class="ns-pl-phu">· ${esc(r.cach_lam)}</span>` : ''}</td>
            <td>${r.theo_gio ? `${formatNumber(r.so_luong, 2)}&nbsp;giờ` : formatNumber(r.so_luong)}</td>
            <td>${r.don_gia ? formatNumber(r.don_gia) : '<span class="ns-pl-canh">⚠ chưa có giá</span>'}</td>
            <td>${so(r.thanh_tien)}</td></tr>`).join('')}
        <tr class="ns-pl-ngay-cong"><td colspan="3">Cộng ngày${phepTinh ? ` <span class="ns-pl-phu">(${esc(phepTinh)})</span>` : ''}</td>
            <td><b>${so(x.thu_nhap)}</b></td></tr>
    </tbody>`;
}

/** Bảng chấm công một tháng công nhật: ngày · công · thêm giờ (số gốc của bảng chấm công; tiền tính ở phiếu). */
function bangChamCong(ngay) {
    return `<table class="ns-pl-ngay ns-pl-cc"><thead><tr><th>Ngày</th><th>Công</th><th>Thêm giờ</th></tr></thead><tbody>
        ${ngay.map((x) => `<tr class="${x.thu === 'Chủ nhật' ? 'ns-pl-cn' : ''}${!x.cong && !x.them_gio ? ' ns-pl-trong' : ''}">
            <td><b>${esc(ngayThang(x.ngay))}</b>${x.thu ? ` <span class="ns-pl-phu">· ${esc(x.thu)}</span>` : ''}</td>
            <td>${x.cong ? formatNumber(x.cong, 2) : '–'}</td>
            <td>${x.them_gio ? `${formatNumber(x.them_gio, 2)}&nbsp;giờ` : '–'}</td></tr>`).join('')}
    </tbody></table>`;
}

/**
 * HTML một phiếu lương.
 * @param p view model (ns.api.phieu_luong.xem_doc)
 * @param opts.congNhan  trang công nhân: nháp gọi là "Tạm tính" + dòng nhắc
 * @param opts.xemThay   phòng nhân sự đang xem như công nhân: phiếu tạm tính công nhân CHƯA thấy (p.cong_nhan_thay
 *                       === false) được ghi rõ — HR thấy cả phiếu tạm tính, công nhân chỉ thấy phiếu đã duyệt
 * @param opts.hienTen   ghi tên người trên đầu phiếu (modal của bảng lương)
 */
export function phieuLuongHtml(p, { congNhan = false, hienTen = false, xemThay = false } = {}) {
    const khoan = p.loai === 'khoan';
    const congChu = p.ngay_san_xuat ? `${formatNumber(p.ngay_cong, 2)}/${formatNumber(p.ngay_san_xuat, 2)}` : formatNumber(p.ngay_cong, 2);
    const tong = [
        `<div class="ns-pl-tong-chinh"><span class="ns-pl-nhan">Thực nhận</span><b>${esc(dong(p.thuc_nhan))}</b></div>`,
        `<div><span class="ns-pl-nhan">Ngày công${p.ngay_san_xuat ? ' / ngày SX' : ''}</span><b>${esc(congChu)}</b></div>`,
        !khoan && p.lam_them ? `<div><span class="ns-pl-nhan">Làm thêm</span><b>${formatNumber(p.lam_them, 2)} công</b></div>` : '',
        !khoan && p.luong_co_ban ? `<div><span class="ns-pl-nhan">Lương cơ bản</span><b>${esc(dong(p.luong_co_ban))}</b></div>` : '',
    ].join('');

    const cacKhoan = [
        ...(p.cong || []).map((x) => hang(esc(x.ten), esc(dong(x.tien)))),
        hang('Tổng thu nhập', esc(dong(p.tong_tien)), { lop: 'ns-pl-row-tong' }),
        ...(p.tru || []).map((x) => hang(esc(x.ten), `− ${esc(dong(x.tien))}`, { lop: 'ns-pl-row-tru' })),
        ...((p.tru || []).length ? [hang('Thực nhận', esc(dong(p.thuc_nhan)), { lop: 'ns-pl-row-tong ns-pl-row-thuc' })] : []),
        ...(!khoan && p.chuyen_khoan ? [hang('Trong đó chuyển khoản', esc(dong(p.chuyen_khoan)), { lop: 'ns-pl-row-phu' })] : []),
    ].join('');

    // D225: dòng "Làm theo giờ" — số lượng là số GIỜ
    const sanPham = (p.san_pham || []).map((x) => hang(
        `${esc(x.ten)}${x.cach_lam ? ` <span class="ns-pl-phu">· ${esc(x.cach_lam)}</span>` : ''}`,
        esc(dong(x.thanh_tien)),
        { phu: `${x.theo_gio ? `${formatNumber(x.so_luong, 2)} giờ` : formatNumber(x.so_luong)} × ${
            x.don_gia ? `${formatNumber(x.don_gia)} đ` : '<span class="ns-pl-canh">⚠ chưa có giá</span>'}` },
    )).join('');

    const phat = (p.phat || []).map((x) => hang(esc(x.ly_do || '—'), `− ${esc(dong(x.tien))}`, {
        lop: 'ns-pl-row-tru',
        phu: x.so_luong ? `${formatNumber(x.so_luong, 2)} × ${formatNumber(x.gia_tien)} đ` : '',
    })).join('');

    const ngay = p.ngay || [];
    const tungNgay = !ngay.length ? '' : khoan
        ? `<div class="ns-pl-muc">Từng ngày (đồng)</div>
           <table class="ns-pl-ngay"><thead><tr><th>Sản phẩm</th><th>SL</th><th>Đơn giá</th><th>Thành tiền</th></tr></thead>
           ${ngay.map(veNgayKhoan).join('')}</table>`
        : `<div class="ns-pl-muc">Chấm công từng ngày</div>${bangChamCong(ngay)}`;

    return `<section class="ns-pl" data-pl="${esc(p.name)}">
        <div class="ns-pl-dau">
            <div><div class="ns-pl-loai">${esc(p.loai_ten || (khoan ? 'Lương công khoán' : 'Lương công nhật'))} · T${esc(p.thang)}/${esc(p.nam)}</div>
                ${hienTen ? `<div class="ns-pl-phu">${esc(p.ten || '')} · ${esc(p.employee || '')}</div>` : ''}</div>
            <div class="ns-pl-nhan-tt">${nhanTrangThai(p, { congNhan })}${!khoan && p.trang_thai ? ` <span class="ns-badge ns-badge-muted">${esc(p.trang_thai)}</span>` : ''}</div>
        </div>
        ${congNhan && p.docstatus === 0 ? `<div class="ns-risk-bar ns-warn-bar ns-pl-bao"><span>Phiếu chưa duyệt — số đang <b>tạm tính</b>, còn có thể thay đổi.${
    xemThay && p.cong_nhan_thay === false ? ' Công nhân <b>chưa thấy</b> phiếu này — chỉ hiện với công nhân sau khi duyệt.' : ''}</span></div>` : ''}
        ${p.chua_gia ? `<div class="ns-risk-bar ns-warn-bar ns-pl-bao"><span>⚠ ${p.chua_gia} dòng sản phẩm chưa có đơn giá (đang tính 0 đồng)${congNhan ? ' — phòng lương đang cập nhật.' : ' — chưa duyệt được.'}</span></div>` : ''}
        <div class="ns-pl-tong">${tong}</div>
        <div class="ns-pl-muc">Các khoản</div><div class="ns-pl-list">${cacKhoan}</div>
        ${sanPham ? `<div class="ns-pl-muc">Sản phẩm trong tháng</div><div class="ns-pl-list">${sanPham}</div>` : ''}
        ${tungNgay}
        ${phat ? `<div class="ns-pl-muc">Lỗi phạt</div><div class="ns-pl-list">${phat}</div>` : ''}
        ${p.ghi_chu ? `<div class="ns-pl-muc">Ghi chú</div><div class="ns-pl-ghichu">${esc(p.ghi_chu)}</div>` : ''}
    </section>`;
}
