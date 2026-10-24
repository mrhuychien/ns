"""Hằng số, whitelist field và helper dùng chung cho API ns.

Lưu ý: fieldname có dấu (custom_bảo_hiểm…) lấy NGUYÊN từ dump; dùng qua
doc.get()/frappe.get_all(fields=[...]) được, SQL thô bắt buộc backtick.
Chuỗi ở đây giữ dạng NFC — khớp với fieldname trong DB.
"""
import json
import re
import unicodedata

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, today

BO_PHAN_KHOAN = "Công khoán - HGC"
BO_PHAN_BINH_DUONG = "Bình Dương - HGC"
KHONG_BO_PHAN = "__none__"

# Field có dấu tái dùng (KHÔNG tạo trùng)
F_BAO_HIEM = "custom_bảo_hiểm"
F_LUONG_CB = "custom_lương_cơ_bản"
F_HO_TRO = "custom_hỗ_trợ"
F_LUONG_TK = "custom_lương_tài_khoản"
F_AN_CA_TOI = "custom_ăn_ca_tối_tại_công_ty"
F_NAM_GIA_NHAP = "custom_năm_gia_nhập"

# §4.1.1 — field Employee được sửa từ app
WHITELIST_SUA = [
    "first_name", "gender", "date_of_birth", "image", "custom_cccd", "cell_number",
    "custom_zalo", "personal_email", "current_address", "permanent_address",
    "person_to_be_contacted", "emergency_phone_number", "relation", "department",
    "designation", "date_of_joining", "vn_contract_type", "contract_end_date",
    "attendance_device_id", "status", "relieving_date", "reason_for_leaving",
    F_LUONG_CB, F_HO_TRO, F_BAO_HIEM, F_LUONG_TK, F_AN_CA_TOI,
    "ns_dong_bhxh", "ns_so_so_bhxh", "ns_bhxh_tu_ngay", "ns_bhxh_den_ngay",
    "ns_ly_do_khong_bhxh", "vn_insurance_salary", "vn_tax_code",
    "vn_number_of_dependents", "health_insurance_no", "bank_name", "bank_ac_no",
    "custom_bankowner", "salary_mode", "ns_giay_to",
]

# Field chỉ đọc trả về kèm chi_tiet
FIELD_DOC_THEM = [
    "name", "employee_name", "company", "status", F_NAM_GIA_NHAP, "creation", "modified",
    "user_id",
]

# Field của dòng giấy tờ được ghi từ app
GIAY_TO_FIELDS = ["loai", "so", "ngay_cap", "noi_cap", "ngay_het_han", "tep", "ghi_chu"]

# Field dùng cho danh sách (§4.1 danh_sach + cảnh báo §6)
FIELD_DANH_SACH = [
    "name", "employee_name", "department", "status", "date_of_joining", "date_of_birth",
    "cell_number", "custom_cccd", "attendance_device_id", "bank_ac_no", "contract_end_date",
    "ns_dong_bhxh", "ns_ly_do_khong_bhxh", F_BAO_HIEM, F_LUONG_CB, F_LUONG_TK, "image",
    "gender", "custom_zalo", "permanent_address", "vn_contract_type", "ns_so_so_bhxh",
    "vn_insurance_salary", "ns_bhxh_tu_ngay", "vn_tax_code", "vn_number_of_dependents",
    "bank_name", "custom_bankowner",
]


def nfc(s):
    return unicodedata.normalize("NFC", s) if isinstance(s, str) else s


def meta_emp():
    return frappe.get_meta("Employee")


def fields_co(doctype, fields):
    """Chỉ xin những field meta đang có (gotcha #19) — tránh Unknown column khi
    site chưa migrate đủ. Field thiếu → caller nhận None qua .get()."""
    meta = frappe.get_meta(doctype)
    return [f for f in fields if f == "name" or meta.has_field(f)]


def loai_luong(department):
    return "Khoán" if nfc(department or "") == nfc(BO_PHAN_KHOAN) else "Nhật"


def la_khoan(department):
    return loai_luong(department) == "Khoán"


def tham_nien_nam(date_of_joining, den_ngay=None):
    if not date_of_joining:
        return None
    try:
        d0 = getdate(date_of_joining)
        d1 = getdate(den_ngay or today())
    except Exception:
        return None
    return round((d1 - d0).days / 365.25, 1)


def parse_data(data):
    if data is None:
        return {}
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except ValueError:
            frappe.throw(_("Dữ liệu gửi lên không phải JSON hợp lệ."))
    if not isinstance(data, dict):
        frappe.throw(_("Dữ liệu gửi lên phải là object."))
    return data


def parse_list(v):
    if v is None or v == "":
        return []
    if isinstance(v, str):
        try:
            v = json.loads(v)
        except ValueError:
            return [x.strip() for x in v.split(",") if x.strip()]
    return list(v) if isinstance(v, (list, tuple)) else [v]


def company_mac_dinh():
    c = frappe.defaults.get_global_default("company") or frappe.db.get_single_value(
        "Global Defaults", "default_company"
    )
    if not c:
        c = frappe.db.get_value("Company", {}, "name")
    return c


def lay_nhan_vien(filters=None, fields=None, order_by="employee_name asc"):
    fields = fields_co("Employee", fields or FIELD_DANH_SACH)
    return frappe.get_all("Employee", filters=filters or {}, fields=fields, order_by=order_by, limit_page_length=0)


def lay_giay_to(employees):
    """Trả {employee: [rows NS Giay To]} — 1 query cho cả danh sách."""
    out = {e: [] for e in employees}
    if not employees or not frappe.db.table_exists("NS Giay To"):
        return out
    rows = frappe.get_all(
        "NS Giay To",
        filters={"parenttype": "Employee", "parent": ("in", list(employees))},
        fields=["name", "parent", "loai", "so", "ngay_cap", "noi_cap", "ngay_het_han", "tep", "ghi_chu", "idx"],
        order_by="parent asc, idx asc",
        limit_page_length=0,
    )
    for r in rows:
        out.setdefault(r.parent, []).append(r)
    return out


def loc_bo_phan(filters, department):
    """Áp lọc bộ phận: None = mọi; '__none__' = chưa có bộ phận; tên = đúng bộ phận."""
    if not department:
        return filters
    if department == KHONG_BO_PHAN:
        filters["department"] = ("is", "not set")
    else:
        filters["department"] = department
    return filters


def dieu_kien_tim(q):
    """or_filters like trên employee_name, custom_cccd, attendance_device_id, name."""
    q = (q or "").strip()
    if not q:
        return None
    like = f"%{q}%"
    cols = fields_co("Employee", ["employee_name", "custom_cccd", "attendance_device_id", "name"])
    return [[c, "like", like] for c in cols]


# ─── validate dữ liệu Employee ghi từ app (§4.1 luu / §4.7 luu_o) ───

CCCD_RE = re.compile(r"^\d{12}$")


def validate_gia_tri(field, value, doc=None):
    """Trả value đã chuẩn hoá hoặc throw ValidationError (thông điệp tiếng Việt)."""
    if field == "custom_cccd" and value:
        v = re.sub(r"\D", "", str(value))
        if not CCCD_RE.match(v):
            frappe.throw(_("CCCD phải đúng 12 chữ số."))
        return v
    if field == "date_of_joining" and value:
        if getdate(value) > getdate(today()):
            frappe.throw(_("Ngày vào làm không được sau hôm nay."))
    if field == "status" and value == "Left":
        rd = (doc or {}).get("relieving_date") if doc else None
        if not rd:
            frappe.throw(_("Trạng thái Đã nghỉ (Left) bắt buộc có ngày nghỉ việc."))
    if field in ("cell_number", "custom_zalo", "emergency_phone_number") and value:
        return re.sub(r"[^\d+]", "", str(value))
    if field == "vn_number_of_dependents" and value not in (None, ""):
        return cint(value)
    if field in (F_BAO_HIEM, F_LUONG_CB, F_HO_TRO, F_LUONG_TK, "vn_insurance_salary") and value not in (None, ""):
        if isinstance(value, str):
            value = re.sub(r"[.,\s]", "", value)
        return flt(value)
    return value


def ap_dung_data(doc, data):
    """Ghi các key whitelist từ data vào doc Employee (ns_giay_to thay cả bảng).
    Validate theo §4.1. Không save."""
    data = {k: v for k, v in data.items() if k in WHITELIST_SUA}
    meta = meta_emp()
    # Validate status=Left cần relieving_date (lấy từ data hoặc doc hiện tại)
    merged = dict(doc.as_dict())
    merged.update({k: v for k, v in data.items() if k != "ns_giay_to"})
    for k, v in data.items():
        if k == "ns_giay_to":
            continue
        if not meta.has_field(k):
            frappe.throw(_("Field {0} chưa có trên Employee — chạy bench migrate.").format(k))
        data[k] = validate_gia_tri(k, v, merged)
    if "status" not in data and merged.get("status") == "Left" and "relieving_date" in data and not data["relieving_date"]:
        frappe.throw(_("Nhân viên đã nghỉ bắt buộc có ngày nghỉ việc."))
    for k, v in data.items():
        if k == "ns_giay_to":
            if not meta.has_field("ns_giay_to"):
                frappe.throw(_("Field ns_giay_to chưa có trên Employee — chạy bench migrate."))
            doc.set("ns_giay_to", [])
            for row in parse_list(v):
                if not isinstance(row, dict):
                    continue
                r = {f: row.get(f) for f in GIAY_TO_FIELDS if row.get(f) not in (None, "")}
                if not r.get("loai"):
                    frappe.throw(_("Dòng giấy tờ thiếu Loại."))
                doc.append("ns_giay_to", r)
            continue
        doc.set(k, v if v != "" else None)
    return doc


def tuy_chon():
    """Danh sách lựa chọn cho các Select/Link hay dùng trên form (client dựng editor)."""
    meta = meta_emp()
    out = {}

    def opts(fn):
        f = meta.get_field(fn)
        if not f or not f.options:
            return []
        return [o for o in str(f.options).split("\n") if o != ""]

    for fn in ("vn_contract_type", "ns_ly_do_khong_bhxh", "salary_mode", "status", "reason_for_leaving"):
        if meta.has_field(fn):
            f = meta.get_field(fn)
            if f.fieldtype == "Select":
                out[fn] = opts(fn)
    try:
        out["gender"] = frappe.get_all("Gender", pluck="name", order_by="name asc")
    except Exception:
        out["gender"] = []
    try:
        out["department"] = danh_sach_bo_phan()
    except Exception:
        out["department"] = []
    try:
        out["designation"] = frappe.get_all("Designation", pluck="name", order_by="name asc", limit_page_length=0)
    except Exception:
        out["designation"] = []
    try:
        out["bank_name"] = frappe.get_all("Bank", pluck="name", order_by="name asc", limit_page_length=0)
    except Exception:
        out["bank_name"] = []
    return out


def danh_sach_bo_phan():
    """Bộ phận đang có nhân viên (distinct), sort tên."""
    rows = frappe.get_all(
        "Employee", fields=["department"], filters={"department": ("is", "set")},
        group_by="department", order_by="department asc", limit_page_length=0,
    )
    return [r.department for r in rows if r.department]


def thang_truoc(thang, nam, lui=1):
    """(thang, nam) lùi `lui` tháng."""
    t, n = cint(thang), cint(nam)
    for _i in range(lui):
        t -= 1
        if t <= 0:
            t = 12
            n -= 1
    return t, n
