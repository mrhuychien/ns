"""§4.3 — Timeline 1 người: NS Su Kien + tháng lương (đọc thẳng SalaryDay / SX Phieu Luong)."""
import frappe
from frappe.utils import cint, flt, fmt_money

from ns.api import guard
from ns.api.phieu import chon_phieu, phieu_khoan, phieu_nhat


def _so(v):
    return fmt_money(flt(v), precision=0)


def _salary_product(employee):
    """§3.5 bước 5: SalaryProduct (app lam-luong cũ) nếu còn và map được."""
    if not frappe.db.exists("DocType", "SalaryProduct") or not frappe.db.table_exists("SalaryProduct"):
        return []
    try:
        meta = frappe.get_meta("SalaryProduct")
    except Exception:
        return []
    fn = {f.fieldname for f in meta.fields}
    f_emp = "employee" if "employee" in fn else None
    f_month = next((c for c in ("month", "thang") if c in fn), None)
    f_year = next((c for c in ("year", "nam") if c in fn), None)
    f_tong = next((c for c in ("luongthucnhan", "luong_thuc_nhan", "tongtien", "tong_tien", "thucnhan") if c in fn), None)
    if not (f_emp and f_month and f_year and f_tong):
        return []  # mapping không rõ → bỏ qua, không đoán
    rows = frappe.get_all(
        "SalaryProduct", filters={f_emp: employee, "docstatus": ("<", 2)},
        fields=["name", f_month, f_year, f_tong, "docstatus"], limit_page_length=0, ignore_permissions=True,
    )
    out = []
    for r in rows:
        m, y = cint(r.get(f_month)), cint(r.get(f_year))
        if not m or not y:
            continue
        out.append({
            "ngay": f"{y:04d}-{m:02d}-01", "loai": "Lương khoán (cũ)", "tieu_de": f"T{m}/{y}",
            "noi_dung": f"thực nhận {_so(r.get(f_tong))}", "gia_tri_cu": None, "gia_tri_moi": None,
            "tep": None, "nguon": "Tự động", "ref_doctype": "SalaryProduct", "ref_name": r.name,
            "trang_thai": "Đã duyệt" if cint(r.docstatus) == 1 else "Nháp",
        })
    return out


@frappe.whitelist()
def get(employee):
    """List sort ngay desc."""
    guard()
    out = []
    for r in frappe.get_all(
        "NS Su Kien", filters={"employee": employee},
        fields=["name", "ngay", "loai", "tieu_de", "noi_dung", "gia_tri_cu", "gia_tri_moi", "tep", "nguon"],
        order_by="ngay desc, creation desc", limit_page_length=0,
    ):
        out.append({
            "ngay": r.ngay, "loai": r.loai, "tieu_de": r.tieu_de or r.loai, "noi_dung": r.noi_dung,
            "gia_tri_cu": r.gia_tri_cu, "gia_tri_moi": r.gia_tri_moi, "tep": r.tep, "nguon": r.nguon,
            "ref_doctype": "NS Su Kien", "ref_name": r.name, "trang_thai": None,
        })
    # SalaryDay — group (year, month): ưu tiên docstatus=1, không có thì nháp mới nhất
    nhom = {}
    for r in phieu_nhat(employees=[employee]):
        nhom.setdefault((cint(r.year), cint(r.month)), []).append(r)
    for (y, m), rows in nhom.items():
        if not m or not y:
            continue
        r, _trung = chon_phieu(rows)
        tt = (r.get("status") or "") + (" (Nháp)" if cint(r.docstatus) == 0 else "")
        out.append({
            "ngay": f"{y:04d}-{m:02d}-01", "loai": "Lương công nhật", "tieu_de": f"T{m}/{y}",
            "noi_dung": f"{flt(r.get('congngay'))} công · làm thêm {flt(r.get('lamthem'))} · thực nhận {_so(r.get('luongthucnhan'))}",
            "gia_tri_cu": None, "gia_tri_moi": None, "tep": None, "nguon": "Tự động",
            "ref_doctype": "SalaryDay", "ref_name": r.name, "trang_thai": tt.strip() or ("Nháp" if cint(r.docstatus) == 0 else "Đã duyệt"),
            "thang": m, "nam": y,
        })
    nhom = {}
    for r in phieu_khoan(employees=[employee]):
        nhom.setdefault((cint(r.nam), cint(r.thang)), []).append(r)
    for (y, m), rows in nhom.items():
        if not m or not y:
            continue
        r, _trung = chon_phieu(rows)
        out.append({
            "ngay": f"{y:04d}-{m:02d}-01", "loai": "Lương khoán", "tieu_de": f"T{m}/{y}",
            "noi_dung": f"{flt(r.get('ngay_cong'))} công · lương SP {_so(r.get('luong_san_pham'))} · thực nhận {_so(r.get('luong_thuc_nhan'))}",
            "gia_tri_cu": None, "gia_tri_moi": None, "tep": None, "nguon": "Tự động",
            "ref_doctype": "SX Phieu Luong", "ref_name": r.name,
            "trang_thai": (r.get("trang_thai") or ("Nháp" if cint(r.docstatus) == 0 else "Đã duyệt")) + (" (Nháp)" if cint(r.docstatus) == 0 and r.get("trang_thai") else ""),
            "thang": m, "nam": y,
        })
    out.extend(_salary_product(employee))
    out.sort(key=lambda x: str(x["ngay"] or ""), reverse=True)
    return out
