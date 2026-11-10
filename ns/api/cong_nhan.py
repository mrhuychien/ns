"""Công nhân tự xem phiếu lương của CHÍNH MÌNH — trang /phieuluong.

Ai xem được gì — kiểm ở server, trong mọi method:
  · Đã đăng nhập (không phải Guest), tài khoản đang bật.
  · Tài khoản đang gắn với một hồ sơ nhân viên qua Employee.ns_tai_khoan (HR gắn ở /ns → Tài khoản). Nhân viên
    LUÔN suy từ phiên đăng nhập — không nhận mã nhân viên từ trình duyệt, nên không đoán mã để đọc lương người khác.
  · Ngoại lệ duy nhất: người có quyền HR của app (ns.api.guard) truyền `employee` để XEM NHƯ CÔNG NHÂN (công nhân
    hỏi "sao tôi không thấy phiếu tháng 9" → HR mở đúng màn công nhân đang nhìn).
Thấy phiếu nào:
  · Mặc định CHỈ phiếu ĐÃ DUYỆT (docstatus = 1) — số cuối cùng, không đổi nữa.
  · site_config `ns_cong_nhan_xem_nhap = 1` → thấy thêm phiếu NHÁP, ghi rõ "tạm tính". Riêng SalaryDay nháp chỉ
    hiện khi P1 đã bật (`ns_tinh_lai_salaryday = 1`): trước P1, số trên phiếu nháp chỉ đúng sau khi kế toán mở Desk
    và Save (SPEC §7) — cho công nhân xem số cũ là tạo thắc mắc giả.
Không ghi gì. Đọc SalaryDay / SX Phieu Luong bỏ qua quyền DocType SAU KHI đã khoá phạm vi về đúng một nhân viên
(gotcha #9) — role NS Cong Nhan không có quyền DocType nào.
"""
import frappe
from frappe import _
from frappe.utils import cint, flt

from ns.api import co_quyen
from ns.api.phieu import chon_phieu, phieu_khoan, phieu_nhat
from ns.api.phieu_luong import DT_KHOAN, DT_NHAT, lay_doc, xem_doc

F_TK = "ns_tai_khoan"


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


def _xem_nhap(loai):
    if not cint(frappe.conf.get("ns_cong_nhan_xem_nhap")):
        return False
    if loai == "nhat":
        return bool(cint(frappe.conf.get("ns_tinh_lai_salaryday")))
    return True


def _hien(rows, loai):
    """Phiếu công nhân được thấy: đã duyệt; nháp chỉ khi bật (xem docstring)."""
    ok = {1, 0} if _xem_nhap(loai) else {1}
    return [r for r in rows if cint(r.docstatus) in ok]


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
            "xem_thay": xem_thay, "xem_nhap": _xem_nhap("khoan")}


@frappe.whitelist()
def cac_thang(employee=None):
    """Các tháng có phiếu xem được, mới nhất trước: [{thang, nam, thuc_nhan, so_phieu, tam_tinh}]."""
    emp, xem_thay = pham_vi(employee)
    nhom = {}
    for loai, rows, ft, fn, f_tien in (
            ("nhat", phieu_nhat(employees=[emp]), "month", "year", "luongthucnhan"),
            ("khoan", phieu_khoan(employees=[emp]), "thang", "nam", "luong_thuc_nhan")):
        for k, ds in _theo_thang(_hien(rows, loai), ft, fn).items():
            p, _trung = chon_phieu(ds)
            g = nhom.setdefault(k, {"nam": k[0], "thang": k[1], "thuc_nhan": 0.0, "so_phieu": 0, "tam_tinh": False})
            g["thuc_nhan"] += flt(p.get(f_tien))
            g["so_phieu"] += 1
            g["tam_tinh"] = g["tam_tinh"] or cint(p.docstatus) == 0
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
        p, _trung = chon_phieu(_hien(rows, loai))
        if p:
            xem = xem_doc(lay_doc(dt, p.name))
            if xem.get("employee") != emp:          # phòng thủ: bộ lọc employee đã làm việc này
                continue
            out.append(xem)
    return {**_thong_tin(emp, xem_thay), "thang": thang, "nam": nam, "phieu": out}
