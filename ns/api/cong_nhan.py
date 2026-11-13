"""Công nhân tự xem phiếu lương của CHÍNH MÌNH — trang /phieuluong.

Ai xem được gì — kiểm ở server, trong mọi method:
  · Đã đăng nhập (không phải Guest), tài khoản đang bật.
  · Tài khoản đang gắn với một hồ sơ nhân viên qua Employee.ns_tai_khoan (HR gắn ở /ns → Tài khoản). Nhân viên
    LUÔN suy từ phiên đăng nhập — không nhận mã nhân viên từ trình duyệt, nên không đoán mã để đọc lương người khác.
  · Ngoại lệ duy nhất: người có quyền HR của app (ns.api.guard) truyền `employee` để XEM NHƯ CÔNG NHÂN (công nhân
    hỏi "sao tôi không thấy phiếu tháng 9" → HR mở đúng màn công nhân đang nhìn).
Thấy phiếu nào:
  · Công nhân: phiếu ĐÃ DUYỆT và phiếu TẠM TÍNH (nháp, docstatus 0) — cả công khoán lẫn công nhật; phiếu nháp ghi rõ
    "Tạm tính", số còn đổi được (yêu cầu 13/11/2026: công nhân thấy phiếu tạm tính). Tắt — chỉ phiếu đã duyệt:
    `bench --site <site> set-config ns_cong_nhan_xem_nhap 0`.
  · Công nhật (SalaryDay) nháp khi P1 CHƯA bật (`ns_tinh_lai_salaryday` ≠ 1): tiền trên phiếu chỉ được tính lại khi kế
    toán lưu phiếu trên Desk (Client Script — SPEC §7), còn bảng chấm công thì /chamcong2 ghi ngay → phiếu kèm
    `tien_cho_cap_nhat` để màn hình nói rõ "có thể chưa gồm ngày công mới chấm". KHÔNG tự tính lại ở đây: phòng nhân
    sự ở /ns thấy đúng số trên phiếu — hai nơi tính là hai con số.
  · Phòng nhân sự xem thay (quét thẻ / nút 👁): thấy cả phiếu tạm tính; mỗi phiếu kèm `cong_nhan_thay` (đã tắt cho công
    nhân xem nháp thì màn hình ghi "công nhân chưa thấy").
  · Phiếu đã huỷ không bao giờ.
Không ghi gì. Đọc SalaryDay / SX Phieu Luong bỏ qua quyền DocType SAU KHI đã khoá phạm vi về đúng một nhân viên
(gotcha #9) — role NS Cong Nhan không có quyền DocType nào.
"""
from urllib.parse import quote

import frappe
from frappe import _
from frappe.utils import cint, flt

from ns.api import co_quyen
from ns.salaryday import bat_hook as p1_dang_bat
from ns.api.phieu import chon_phieu, phieu_khoan, phieu_nhat
from ns.api.phieu_luong import DT_KHOAN, DT_NHAT, lay_doc, xem_doc

F_TK = "ns_tai_khoan"
TRANG = "/phieuluong"


def dia_chi_the(the=None):
    """Địa chỉ trang công nhân kèm mã chủ thẻ (?the=) — nằm trong QR của thẻ đăng nhập, và là chỗ quay về sau khi đăng
    nhập. Không có mã → địa chỉ trơn (thẻ in trước đây)."""
    return TRANG + (f"?the={quote(the, safe='')}" if the else "")


def nhan_vien_cua(user):
    """Mã nhân viên gắn với tài khoản, hoặc None (chưa gắn / site chưa migrate field)."""
    if not user or user == "Guest" or not frappe.get_meta("Employee").has_field(F_TK):
        return None
    ds = frappe.get_all("Employee", filters={F_TK: user}, pluck="name", limit=2)
    return ds[0] if len(ds) == 1 else None      # unique index → không thể >1; vẫn phòng thủ


def pham_vi(employee=None):
    """(mã nhân viên được xem, xem_thay). Throw PermissionError nếu không đủ quyền."""
    user = frappe.session.user
    if not user or user == "Guest":
        frappe.throw(_("Hãy đăng nhập để xem phiếu lương."), frappe.PermissionError)
    if employee:
        if not co_quyen(user):
            frappe.throw(_("Chỉ phòng nhân sự mới xem thay được."), frappe.PermissionError)
        if not frappe.db.exists("Employee", employee):
            frappe.throw(_("Không có nhân viên {0}.").format(employee), frappe.DoesNotExistError)
        return employee, True
    if not cint(frappe.db.get_value("User", user, "enabled")):
        frappe.throw(_("Tài khoản đang bị khoá."), frappe.PermissionError)
    emp = nhan_vien_cua(user)
    if not emp:
        frappe.throw(_("Tài khoản này chưa gắn với hồ sơ nhân viên nào — liên hệ phòng nhân sự."),
                     frappe.PermissionError)
    return emp, False


def xem_nhap():
    """Công nhân có thấy phiếu TẠM TÍNH (nháp) không — MẶC ĐỊNH CÓ; site_config ns_cong_nhan_xem_nhap = 0 để tắt."""
    return bool(cint(frappe.conf.get("ns_cong_nhan_xem_nhap", 1)))


def _hien(rows, xem_thay=False):
    """Phiếu được thấy: đã duyệt + tạm tính (công nhân: trừ khi đã tắt; phòng nhân sự xem thay: luôn).
    Phiếu đã huỷ không bao giờ."""
    ok = {1, 0} if (xem_thay or xem_nhap()) else {1}
    return [r for r in rows if cint(r.docstatus) in ok]


def cong_nhan_thay(docstatus):
    """Công nhân (tự đăng nhập) có thấy phiếu này không — để màn xem thay của phòng nhân sự ghi rõ."""
    return cint(docstatus) == 1 or xem_nhap()


def tien_cho_cap_nhat(loai, docstatus):
    """Phiếu công nhật nháp khi P1 chưa bật: tiền chỉ tính lại khi kế toán lưu phiếu trên Desk — có thể chưa theo kịp
    bảng chấm công (xem docstring đầu tệp)."""
    return loai == "nhat" and cint(docstatus) == 0 and not p1_dang_bat()


def _theo_thang(rows, f_thang, f_nam):
    out = {}
    for r in rows:
        t, n = cint(r.get(f_thang)), cint(r.get(f_nam))
        if 1 <= t <= 12 and n:
            out.setdefault((n, t), []).append(r)
    return out


def _thong_tin(emp, xem_thay):
    e = frappe.db.get_value("Employee", emp, ["name", "employee_name", "department"], as_dict=True) or {}
    return {"employee": emp, "employee_name": e.get("employee_name") or emp, "department": e.get("department"),
            "xem_thay": xem_thay, "xem_nhap": xem_nhap()}


@frappe.whitelist()
def cac_thang(employee=None):
    """Các tháng có phiếu xem được, mới nhất trước: [{thang, nam, thuc_nhan, so_phieu, tam_tinh, cong_nhan_thay}].
    `cong_nhan_thay` = công nhân tự đăng nhập thấy tháng này (có ít nhất một phiếu họ được thấy)."""
    emp, xem_thay = pham_vi(employee)
    nhom = {}
    for loai, rows, ft, fn, f_tien in (
            ("nhat", phieu_nhat(employees=[emp]), "month", "year", "luongthucnhan"),
            ("khoan", phieu_khoan(employees=[emp]), "thang", "nam", "luong_thuc_nhan")):
        for k, ds in _theo_thang(_hien(rows, xem_thay), ft, fn).items():
            p, _trung = chon_phieu(ds)
            g = nhom.setdefault(k, {"nam": k[0], "thang": k[1], "thuc_nhan": 0.0, "so_phieu": 0, "tam_tinh": False,
                                    "cong_nhan_thay": False})
            g["thuc_nhan"] += flt(p.get(f_tien))
            g["so_phieu"] += 1
            g["tam_tinh"] = g["tam_tinh"] or cint(p.docstatus) == 0
            g["cong_nhan_thay"] = g["cong_nhan_thay"] or cong_nhan_thay(p.docstatus)
    return {**_thong_tin(emp, xem_thay), "thang": [nhom[k] for k in sorted(nhom, reverse=True)]}


@frappe.whitelist()
def phieu(thang, nam, employee=None):
    """Phiếu lương của một tháng (công nhật và / hoặc công khoán) — view model dựng chung với màn nhân sự."""
    emp, xem_thay = pham_vi(employee)
    thang, nam = cint(thang), cint(nam)
    if not (1 <= thang <= 12 and 2000 <= nam <= 2100):
        frappe.throw(_("Tháng không hợp lệ."))
    out = []
    for loai, dt, rows in (("nhat", DT_NHAT, phieu_nhat(thang, nam, [emp])),
                           ("khoan", DT_KHOAN, phieu_khoan(thang, nam, [emp]))):
        p, _trung = chon_phieu(_hien(rows, xem_thay))
        if p:
            xem = xem_doc(lay_doc(dt, p.name))
            if xem.get("employee") != emp:          # phòng thủ: bộ lọc employee đã làm việc này
                continue
            xem["cong_nhan_thay"] = cong_nhan_thay(xem.get("docstatus"))
            xem["tien_cho_cap_nhat"] = tien_cho_cap_nhat(loai, xem.get("docstatus"))
            out.append(xem)
    return {**_thong_tin(emp, xem_thay), "thang": thang, "nam": nam, "phieu": out}
