"""doc_events Employee (§3.1 đồng bộ cờ BHXH, §3.4 sự kiện tự động).

Hook trên DocType CHUẨN chạy cho mọi lần lưu của mọi app → chỉ tính toán,
KHÔNG throw (bọc try/except + log_error). Bỏ qua toàn bộ khi frappe.flags.ns_backfill.
"""
import frappe
from frappe.utils import flt, fmt_money, getdate, now_datetime, today

from ns.api import common

SLUG = {
    "Vào làm": "vao-lam", "Điều chuyển bộ phận": "dieu-chuyen", "Thay đổi lương": "doi-luong",
    "Ký HĐLĐ": "ky-hdld", "Bắt đầu đóng BHXH": "bat-dau-bhxh", "Ngừng đóng BHXH": "ngung-bhxh",
    "Tạm nghỉ": "tam-nghi", "Đi làm lại": "di-lam-lai", "Nghỉ việc": "nghi-viec",
}


def _bo_qua():
    return bool(frappe.flags.ns_backfill or frappe.flags.in_install or frappe.flags.in_migrate or frappe.flags.in_patch)


def validate(doc, method=None):
    """custom_bảo_hiểm > 0 → ép ns_dong_bhxh = 1 (cho phép 1 mà bảo hiểm = 0)."""
    if _bo_qua():
        return
    try:
        if not doc.meta.has_field("ns_dong_bhxh"):
            return
        if flt(doc.get(common.F_BAO_HIEM)) > 0 and not doc.get("ns_dong_bhxh"):
            doc.ns_dong_bhxh = 1
    except Exception:
        frappe.log_error(frappe.get_traceback(), "ns.events.employee.validate")


def ghi_su_kien(employee, loai, ngay, khoa, tieu_de=None, noi_dung=None, gia_tri_cu=None, gia_tri_moi=None):
    """Insert NS Su Kien nguồn Tự động, idempotent theo khoa_tu_dong. Trả name hoặc None."""
    if not frappe.db.table_exists("NS Su Kien"):
        return None
    if frappe.db.exists("NS Su Kien", {"khoa_tu_dong": khoa}):
        return None
    sk = frappe.get_doc({
        "doctype": "NS Su Kien",
        "employee": employee,
        "ngay": ngay or today(),
        "loai": loai,
        "tieu_de": tieu_de or loai,
        "noi_dung": noi_dung,
        "gia_tri_cu": None if gia_tri_cu is None else str(gia_tri_cu),
        "gia_tri_moi": None if gia_tri_moi is None else str(gia_tri_moi),
        "nguon": "Tự động",
        "khoa_tu_dong": khoa,
    })
    sk.flags.ignore_permissions = True
    sk.insert(ignore_permissions=True)
    return sk.name


def _khoa(loai, name):
    return f"{SLUG.get(loai, frappe.scrub(loai))}:{name}:{now_datetime().isoformat()}"


def after_insert(doc, method=None):
    if _bo_qua():
        return
    try:
        ghi_su_kien(doc.name, "Vào làm", doc.get("date_of_joining") or today(), f"vao-lam:{doc.name}",
                    noi_dung=f"Bộ phận: {doc.get('department') or '—'}")
    except Exception:
        frappe.log_error(frappe.get_traceback(), "ns.events.employee.after_insert")


def _tien(v):
    return fmt_money(flt(v), precision=0)


def on_update(doc, method=None):
    if _bo_qua():
        return
    try:
        truoc = doc.get_doc_before_save()
        if not truoc:
            return
        name = doc.name
        if (truoc.get("department") or None) != (doc.get("department") or None):
            ghi_su_kien(name, "Điều chuyển bộ phận", today(), _khoa("Điều chuyển bộ phận", name),
                        gia_tri_cu=truoc.get("department") or "—", gia_tri_moi=doc.get("department") or "—")
        if flt(truoc.get(common.F_LUONG_CB)) != flt(doc.get(common.F_LUONG_CB)):
            ghi_su_kien(name, "Thay đổi lương", today(), _khoa("Thay đổi lương", name),
                        gia_tri_cu=_tien(truoc.get(common.F_LUONG_CB)), gia_tri_moi=_tien(doc.get(common.F_LUONG_CB)))
        if doc.meta.has_field("vn_contract_type") and (truoc.get("vn_contract_type") or None) != (doc.get("vn_contract_type") or None):
            ghi_su_kien(name, "Ký HĐLĐ", today(), _khoa("Ký HĐLĐ", name),
                        gia_tri_cu=truoc.get("vn_contract_type") or "—", gia_tri_moi=doc.get("vn_contract_type") or "—")
        if doc.meta.has_field("ns_dong_bhxh"):
            cu, moi = int(bool(truoc.get("ns_dong_bhxh"))), int(bool(doc.get("ns_dong_bhxh")))
            if cu == 0 and moi == 1:
                ghi_su_kien(name, "Bắt đầu đóng BHXH", doc.get("ns_bhxh_tu_ngay") or today(),
                            _khoa("Bắt đầu đóng BHXH", name),
                            noi_dung=f"Mức trừ: {_tien(doc.get(common.F_BAO_HIEM))}")
            elif cu == 1 and moi == 0:
                ghi_su_kien(name, "Ngừng đóng BHXH", doc.get("ns_bhxh_den_ngay") or today(),
                            _khoa("Ngừng đóng BHXH", name),
                            noi_dung=doc.get("ns_ly_do_khong_bhxh"))
        st_cu, st_moi = truoc.get("status"), doc.get("status")
        if st_cu != st_moi:
            if st_moi in ("Inactive", "Suspended"):
                ghi_su_kien(name, "Tạm nghỉ", today(), _khoa("Tạm nghỉ", name), gia_tri_cu=st_cu, gia_tri_moi=st_moi)
            elif st_cu == "Inactive" and st_moi == "Active":
                ghi_su_kien(name, "Đi làm lại", today(), _khoa("Đi làm lại", name), gia_tri_cu=st_cu, gia_tri_moi=st_moi)
            elif st_moi == "Left":
                ghi_su_kien(name, "Nghỉ việc", doc.get("relieving_date") or today(), _khoa("Nghỉ việc", name),
                            noi_dung=doc.get("reason_for_leaving"), gia_tri_cu=st_cu, gia_tri_moi=st_moi)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "ns.events.employee.on_update")
