"""§4.5 — Bảng lương tháng (chỉ đọc), xuất Excel, danh sách chuyển khoản."""
import frappe
from frappe import _
from frappe.utils import cint, flt, today

from ns.api import common, guard
from ns.api.phieu import (COT_KHOAN, COT_KHOAN_SO, COT_NHAT, COT_NHAT_SO, chon_phieu, gom_theo_nv,
                          phieu_khoan, phieu_nhat)

LABEL_NHAT = {
    "ngaysanxuat": "Ngày SX", "congngay": "Công", "lamthem": "Làm thêm", "luongngaycong": "Lương công",
    "luonglamthem": "Lương làm thêm", "anca": "Ăn ca", "chuyencan": "Chuyên cần", "hotrongaycong": "Hỗ trợ ngày công",
    "hotro": "Hỗ trợ", "thuongkhac": "Thưởng khác", "thuongthamnien": "Thưởng thâm niên", "tongtien": "Tổng tiền",
    "baohiem": "Bảo hiểm", "tienphat": "Tiền phạt", "tongkhautru": "Tổng khấu trừ", "luongthucnhan": "Thực nhận",
    "luongck": "Chuyển khoản", "status": "Trạng thái",
}
LABEL_KHOAN = {
    "ngay_san_xuat": "Ngày SX", "ngay_cong": "Công", "luong_san_pham": "Lương SP", "tien_an": "Tiền ăn",
    "chuyen_can": "Chuyên cần", "ho_tro_ngay_cong": "Hỗ trợ ngày công", "ho_tro": "Hỗ trợ",
    "thuong_tham_nien": "Thưởng thâm niên", "tong_tien": "Tổng tiền", "bao_hiem": "Bảo hiểm", "tien_phat": "Tiền phạt",
    "tong_khau_tru": "Tổng khấu trừ", "luong_thuc_nhan": "Thực nhận", "trang_thai": "Trạng thái",
}


def _tap_nhan_vien(loai, department, thang, nam):
    """Active thuộc phạm vi ∪ nhân viên có phiếu tháng đó."""
    if loai == "nhat":
        filters = {"status": "Active", "department": ("!=", common.BO_PHAN_KHOAN)}
        rows = phieu_nhat(thang, nam)
    else:
        filters = {"status": "Active", "department": common.BO_PHAN_KHOAN}
        rows = phieu_khoan(thang, nam)
    if department:
        if department == common.KHONG_BO_PHAN:
            filters["department"] = ("is", "not set")
        else:
            filters["department"] = department
    if loai == "nhat" and not department:
        # "department != X" bỏ sót NULL trong SQL → gom 2 lượt
        emps = common.lay_nhan_vien({"status": "Active", "department": ("is", "not set")})
        emps += common.lay_nhan_vien({"status": "Active", "department": ("!=", common.BO_PHAN_KHOAN)})
    else:
        emps = common.lay_nhan_vien(filters)
    by = {e.name: e for e in emps}
    theo_nv = gom_theo_nv(rows)
    them = [n for n in theo_nv if n not in by]
    if them:
        for e in common.lay_nhan_vien({"name": ("in", them)}):
            if department and department != common.KHONG_BO_PHAN and e.department != department:
                continue
            if department == common.KHONG_BO_PHAN and e.department:
                continue
            by[e.name] = e
    return by, theo_nv


def _bang(thang, nam, loai, department=None):
    thang, nam = cint(thang), cint(nam)
    if loai not in ("nhat", "khoan"):
        frappe.throw(_("loai phải là nhat hoặc khoan."))
    cot = COT_NHAT if loai == "nhat" else COT_KHOAN
    cot_so = COT_NHAT_SO if loai == "nhat" else COT_KHOAN_SO
    by, theo_nv = _tap_nhan_vien(loai, department, thang, nam)
    dong, tong = [], {c: 0.0 for c in cot_so}
    so_thieu, so_nhap, so_duyet = 0, 0, 0
    for name in sorted(by, key=lambda n: (by[n].employee_name or "")):
        e = by[name]
        p, trung = chon_phieu(theo_nv.get(name, []))
        d = {
            "employee": e.name, "employee_name": e.employee_name, "department": e.department,
            "loai_luong": common.loai_luong(e.department), "thieu_phieu": p is None, "trung": trung,
            "name": p.name if p else None, "docstatus": cint(p.docstatus) if p else None,
            "so_phieu": len(theo_nv.get(name, [])),
        }
        for c in cot:
            d[c] = p.get(c) if p else None
        if p:
            for c in cot_so:
                tong[c] += flt(p.get(c))
            if cint(p.docstatus) == 1:
                so_duyet += 1
            else:
                so_nhap += 1
        else:
            so_thieu += 1
        dong.append(d)
    return {
        "thang": thang, "nam": nam, "loai": loai, "cot": cot, "label": LABEL_NHAT if loai == "nhat" else LABEL_KHOAN,
        "dong": dong, "tong": tong, "so_thieu_phieu": so_thieu, "so_nhap": so_nhap, "so_duyet": so_duyet,
        "co_nguon": (frappe.db.table_exists("SalaryDay") if loai == "nhat" else frappe.db.table_exists("SX Phieu Luong")),
    }


@frappe.whitelist()
def bang(thang, nam, loai="nhat", department=None):
    """Bảng lương tháng, loai ∈ {nhat, khoan}."""
    guard()
    return _bang(thang, nam, loai, department)


def _tra_xlsx(filename, rows, sheet):
    from frappe.utils.xlsxutils import make_xlsx

    xlsx = make_xlsx(rows, sheet)
    frappe.response["filename"] = filename
    frappe.response["filecontent"] = xlsx.getvalue()
    frappe.response["type"] = "download"


@frappe.whitelist()
def xuat_excel(thang, nam, loai="nhat", department=None):
    """Xuất bảng lương .xlsx, header tiếng Việt, dòng tổng."""
    guard()
    b = _bang(thang, nam, loai, department)
    cot = b["cot"]
    label = b["label"]
    header = ["STT", "Mã NV", "Họ tên", "Bộ phận", "Phiếu", "Ghi chú"] + [label.get(c, c) for c in cot]
    rows = [header]
    for i, d in enumerate(b["dong"], start=1):
        ghi_chu = "Thiếu phiếu" if d["thieu_phieu"] else ("Trùng nháp" if d["trung"] else ("Nháp" if d["docstatus"] == 0 else ""))
        rows.append([i, d["employee"], d["employee_name"], d["department"], d["name"] or "", ghi_chu]
                    + [d.get(c) if d.get(c) is not None else "" for c in cot])
    rows.append(["", "", "TỔNG", "", "", ""] + [b["tong"].get(c, "") if c in b["tong"] else "" for c in cot])
    _tra_xlsx(f"bang_luong_{loai}_T{cint(thang)}_{cint(nam)}.xlsx", rows, "Bang luong")


@frappe.whitelist()
def chuyen_khoan(thang, nam):
    """Danh sách chuyển khoản từ SalaryDay submitted của tháng, luongck > 0."""
    guard()
    thang, nam = cint(thang), cint(nam)
    rows = [r for r in phieu_nhat(thang, nam) if cint(r.docstatus) == 1 and flt(r.get("luongck")) > 0]
    names = {r.employee for r in rows}
    ten = {e.name: e for e in common.lay_nhan_vien({"name": ("in", list(names))}, ["name", "employee_name", "bank_ac_no", "bank_name", "custom_bankowner"])} if names else {}
    data = [["STT", "Mã NV", "Chủ tài khoản", "Số TK", "Ngân hàng", "Số tiền", "Nội dung"]]
    tong = 0.0
    for i, r in enumerate(sorted(rows, key=lambda x: (ten.get(x.employee, {}).get("employee_name") or "")), start=1):
        e = ten.get(r.employee, frappe._dict())
        so_tien = flt(r.get("luongck"))
        tong += so_tien
        data.append([
            i, r.employee,
            r.get("chutaikhoan") or e.get("custom_bankowner") or e.get("employee_name") or "",
            r.get("taikhoan") or e.get("bank_ac_no") or "",
            r.get("nganhang") or e.get("bank_name") or "",
            so_tien, f"Luong T{thang}/{nam} {e.get('employee_name') or r.employee}",
        ])
    data.append(["", "", "TỔNG", "", "", tong, ""])
    _tra_xlsx(f"chuyen_khoan_T{thang}_{nam}.xlsx", data, "Chuyen khoan")
