// In THẺ ĐĂNG NHẬP XEM LƯƠNG cho công nhân — dựng HTML ngay trên máy rồi mở tab in (cách của app sx, D63/D81).
//
// Một thẻ: tên + mã NV, QR mở thẳng trang /phieuluong, số điện thoại (tên đăng nhập) và mật khẩu.
// QR CHỈ chứa địa chỉ trang (không chứa mật khẩu / mã đăng nhập): rơi thẻ ra ngoài thì người nhặt vẫn phải có mật
// khẩu — nhưng mật khẩu in ngay bên dưới, nên vẫn giữ thẻ như giữ chìa khoá; mất thẻ → HR bấm "Cấp lại".
// QR vẽ bằng vendor/qrcode.js (MIT) ra SVG: in nét, không cần bật "đồ hoạ nền" (sx D186).
import qrcode from '../vendor/qrcode.js';

const VIEN = 4; // vùng trắng quanh mã — chuẩn QR đòi tối thiểu 4 ô

export function veQR(text, oPx) {
    const qr = qrcode(0, 'M'); // mức sửa lỗi M: chịu ~15% bẩn / xước
    qr.addData(String(text));
    qr.make();
    const n = qr.getModuleCount();
    const m = n + VIEN * 2;
    let d = '';
    for (let y = 0; y < n; y++) {
        for (let x = 0; x < n; x++) {
            if (qr.isDark(y, x)) d += `M${x + VIEN} ${y + VIEN}h1v1h-1z`;
        }
    }
    return `<svg class="qr" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${m} ${m}" width="${m * oPx}" height="${m * oPx}" `
        + `shape-rendering="crispEdges"><rect width="${m}" height="${m}" fill="#fff"/><path d="${d}" fill="#000"/></svg>`;
}

const esc = (s) => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
const gonUrl = (u) => String(u || '').replace(/^https?:\/\//, '');

/** HTML trang in (tách ra để test được không cần mở cửa sổ). ds = [{ten, employee, sdt, mat_khau, url}] */
export function htmlTheDangNhap(ds) {
    const the = ds.map((e) => `
    <div class="the">
      <div class="dau">XEM PHIẾU LƯƠNG</div>
      <div class="ten">${esc(e.ten)}</div>
      <div class="ma">${esc(e.employee || '')}</div>
      ${veQR(e.url, 3)}
      <div class="url">${esc(gonUrl(e.url))}</div>
      <div class="o">
        <div class="nhan">Tên đăng nhập (số điện thoại)</div>
        <div class="gt">${esc(e.sdt)}</div>
        <div class="nhan">Mật khẩu</div>
        <div class="gt mk">${e.mat_khau ? esc(e.mat_khau) : '<span class="cu">(mật khẩu đang dùng)</span>'}</div>
      </div>
      <ol class="hd"><li>Quét mã bằng camera điện thoại</li><li>Nhập số điện thoại và mật khẩu ở trên</li><li>Chọn tháng để xem</li></ol>
      <div class="chan">Giữ tờ này như giữ chìa khoá. Đổi mật khẩu: bấm 👤 trên trang phiếu lương.</div>
    </div>`).join('');
    return `<!doctype html><html lang="vi"><head><meta charset="utf-8"><title>Thẻ đăng nhập xem lương</title><style>
 body { font-family: Arial, sans-serif; margin: 8mm; }
 .luoi { display: flex; flex-wrap: wrap; gap: 5mm; }
 .huongdan { margin-bottom: 5mm; font-size: 10pt; color: #444; }
 @media print { .huongdan { display: none } }
 .the { width: 64mm; border: 1px solid #999; border-radius: 3mm; padding: 4mm; text-align: center; page-break-inside: avoid; }
 .dau { font-size: 8pt; letter-spacing: 1px; color: #555; font-weight: 700; }
 .ten { font-size: 13pt; font-weight: 700; margin-top: 1mm; }
 .ma { font-size: 8.5pt; color: #555; margin-bottom: 1.5mm; }
 .qr { display: block; margin: 0 auto; }
 .url { font-family: monospace; font-size: 8pt; color: #333; margin: 1mm 0 2mm; word-break: break-all; }
 .o { border-top: 1px dashed #bbb; padding-top: 2mm; text-align: left; }
 .nhan { font-size: 7.5pt; color: #666; text-transform: uppercase; letter-spacing: .4px; }
 .gt { font-family: monospace; font-size: 13pt; font-weight: 700; margin-bottom: 1.5mm; letter-spacing: 1px; word-break: break-all; }
 .gt.mk { font-size: 15pt; } .gt .cu { font-family: Arial, sans-serif; font-size: 9pt; font-weight: 400; letter-spacing: 0; }
 .hd { text-align: left; font-size: 8pt; color: #333; margin: 1.5mm 0 0; padding-left: 4.5mm; }
 .chan { margin-top: 2mm; font-size: 7.5pt; color: #888; }
</style></head><body>
<div class="huongdan">${ds.length} thẻ. Cắt rời từng thẻ, đưa TẬN TAY người lao động — trên thẻ có mật khẩu, đừng để lại trên
 bàn. In ở 100% (không "fit to page"), quét thử MỘT thẻ trước khi phát.</div>
<div class="luoi">${the}</div>
</body></html>`;
}

/** Mở trang in trong tab mới (Blob — giữ nguyên màn đang làm). Trả false nếu trình duyệt chặn pop-up. */
export function moTrangInTheDangNhap(ds) {
    const url = URL.createObjectURL(new Blob([htmlTheDangNhap(ds)], { type: 'text/html' }));
    const w = window.open(url, '_blank');
    setTimeout(() => URL.revokeObjectURL(url), 60000);
    return !!w;
}
