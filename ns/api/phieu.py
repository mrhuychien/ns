"""Đọc mềm phiếu lương: SalaryDay (custom DocType trong DB, module Projects) và
SX Phieu Luong (app sx). App ns KHÔNG đổi schema, chỉ đọc. Mọi truy vấn kiểm
table_exists / has_column trước (gotcha #22) để site thiếu app sx không vỡ."""
import frappe
from frappe.utils import cint, flt

DT_NHAT = "SalaryDay"
DT_KHOAN = "SX Phieu Luong"

# §4.5 cột nhật (từ SalaryDay) + field phụ cần cho logic
COT_NHAT = [
    "ngaysanxuat", "congngay", "lamthem", "luongngaycong", "luonglamthem", "anca", "chuyencan",
    "hotrongaycong", "hotro", "thuongkhac", "thuongthamnien", "tongtien", "baohiem", "tienphat",
    "tongkhautru", "luongthucnhan", "luongck", "status",
]
COT_NHAT_SO = [
    "ngaysanxuat", "congngay", "lamthem", "luongngaycong", "luonglamthem", "anca", "chuyencan",
    "hotrongaycong", "hotro", "thuongkhac", "thuongthamnien", "tongtien", "baohiem", "tienphat",
    "tongkhautru", "luongthucnhan", "luongck",
]
PHU_NHAT = ["employee", "month", "year", "ngay", "department", "chutaikhoan", "taikhoan", "nganhang",
            "luongcoban", "ancatoi", "tinhthuongthamnien", "docstatus", "modified", "creation"]

# §4.5 cột khoán (từ SX Phieu Luong)
COT_KHOAN = [
    "ngay_san_xuat", "ngay_cong", "luong_san_pham", "tien_an", "chuyen_can", "ho_tro_ngay_cong",
    "ho_tro", "thuong_tham_nien", "tong_tien", "bao_hiem", "tien_phat", "tong_khau_tru",
    "luong_thuc_nhan", "trang_thai",
]
COT_KHOAN_SO = [
    "ngay_san_xuat", "ngay_cong", "luong_san_pham", "tien_an", "chuyen_can", "ho_tro_ngay_cong",
    "ho_tro", "thuong_tham_nien", "tong_tien", "bao_hiem", "tien_phat", "tong_khau_tru",
    "luong_thuc_nhan",
]
PHU_KHOAN = ["employee", "nam", "thang", "docstatus", "modified", "creation"]


def co_nhat():
    return frappe.db.table_exists(DT_NHAT)


def co_khoan():
    return frappe.db.table_exists(DT_KHOAN)


def _cot(doctype, cols):
    """Chỉ lấy cột đang có trong bảng; cột thiếu caller đọc .get() → None."""
    have = []
    for c in cols:
        if c in ("name", "docstatus", "modified", "creation") or frappe.db.has_column(doctype, c):
            have.append(c)
    return have


def _query(doctype, cols, filters, order_by):
    return frappe.get_all(
        doctype, filters=filters, fields=["name"] + _cot(doctype, cols),
        order_by=order_by, limit_page_length=0, ignore_permissions=True,
    )


def phieu_nhat(thang=None, nam=None, employees=None, docstatus_lt=2, names=None):
    """Danh sách SalaryDay docstatus<2 (hoặc theo filter)."""
    if not co_nhat():
        return []
    filters = {"docstatus": ("<", docstatus_lt)}
    if thang:
        filters["month"] = cint(thang)
    if nam:
        filters["year"] = cint(nam)
    if employees is not None:
        if not employees:
            return []
        filters["employee"] = ("in", list(employees))
    if names:
        filters["name"] = ("in", list(names))
    return _query(DT_NHAT, COT_NHAT + PHU_NHAT, filters, "docstatus desc, modified desc")


def phieu_khoan(thang=None, nam=None, employees=None, docstatus_lt=2, names=None):
    if not co_khoan():
        return []
    filters = {"docstatus": ("<", docstatus_lt)}
    if thang:
        filters["thang"] = cint(thang)
    if nam:
        filters["nam"] = cint(nam)
    if employees is not None:
        if not employees:
            return []
        filters["employee"] = ("in", list(employees))
    if names:
        filters["name"] = ("in", list(names))
    return _query(DT_KHOAN, COT_KHOAN + PHU_KHOAN, filters, "docstatus desc, modified desc")


def chon_phieu(rows):
    """Ưu tiên docstatus=1; không có thì nháp mới sửa nhất. trung=True nếu >1 nháp.
    rows đã sort docstatus desc, modified desc."""
    if not rows:
        return None, False
    nhap = [r for r in rows if cint(r.docstatus) == 0]
    da_duyet = [r for r in rows if cint(r.docstatus) == 1]
    chon = da_duyet[0] if da_duyet else nhap[0]
    return chon, len(nhap) > 1


def gom_theo_nv(rows):
    out = {}
    for r in rows:
        out.setdefault(r.employee, []).append(r)
    return out


def thong_ke_thang(thang, nam):
    """{employee: {"nhat": [...], "khoan": [...]}} cho 1 tháng — dùng cho cảnh báo."""
    out = {}
    for r in phieu_nhat(thang, nam):
        out.setdefault(r.employee, {"nhat": [], "khoan": []})["nhat"].append(r)
    for r in phieu_khoan(thang, nam):
        out.setdefault(r.employee, {"nhat": [], "khoan": []})["khoan"].append(r)
    return out


def doc_bang_con(doc):
    """Trả mọi bảng con của doc dưới dạng {fieldname: [dict,...]} (không cần biết tên child DocType)."""
    out = {}
    for tf in doc.meta.get_table_fields():
        rows = []
        for r in doc.get(tf.fieldname) or []:
            d = r.as_dict()
            for k in ("doctype", "parent", "parenttype", "parentfield", "owner", "modified_by", "creation", "modified", "docstatus"):
                d.pop(k, None)
            rows.append(d)
        out[tf.fieldname] = rows
    return out


def so(v):
    return flt(v)
