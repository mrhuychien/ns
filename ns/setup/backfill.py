"""§3.5 — Backfill một lần: bench --site site1.local execute ns.setup.backfill.run

Idempotent (bỏ qua khoá đã có), đặt frappe.flags.ns_backfill = True để hook
Employee không sinh thêm sự kiện, in bảng đếm cuối cùng."""
import frappe
from frappe.utils import flt, getdate, today

from ns.api import common
from ns.events.employee import ghi_su_kien


def run(dry_run=False):
    dry_run = str(dry_run).lower() in ("1", "true", "yes")
    frappe.flags.ns_backfill = True
    meta = frappe.get_meta("Employee")
    if not meta.has_field("ns_dong_bhxh"):
        print("THIẾU field ns_dong_bhxh — chạy `bench --site <site> migrate` trước.")
        return
    dem = {"dong_bhxh_set": 0, "vao_lam": 0, "nghi_viec": 0, "nghi_viec_khong_ngay": 0, "bat_dau_bhxh": 0, "salaryproduct": None}
    emps = frappe.get_all(
        "Employee",
        fields=common.fields_co("Employee", ["name", "employee_name", "status", "date_of_joining", "relieving_date",
                                             "reason_for_leaving", "modified", "ns_dong_bhxh", common.F_BAO_HIEM]),
        limit_page_length=0,
    )
    # 1) ns_dong_bhxh = 1 cho custom_bảo_hiểm > 0 (db_set, không chạy hook)
    for e in emps:
        if flt(e.get(common.F_BAO_HIEM)) > 0 and not e.get("ns_dong_bhxh"):
            dem["dong_bhxh_set"] += 1
            e["ns_dong_bhxh"] = 1
            if not dry_run:
                frappe.db.set_value("Employee", e.name, "ns_dong_bhxh", 1, update_modified=False)
    # 2) Vào làm
    for e in emps:
        if e.get("date_of_joining"):
            khoa = f"vao-lam:{e.name}"
            if frappe.db.exists("NS Su Kien", {"khoa_tu_dong": khoa}):
                continue
            dem["vao_lam"] += 1
            if not dry_run:
                ghi_su_kien(e.name, "Vào làm", e.date_of_joining, khoa)
    # 3) Nghỉ việc
    for e in emps:
        if e.get("status") != "Left":
            continue
        khoa = f"nghi-viec:{e.name}:backfill"
        if frappe.db.exists("NS Su Kien", {"khoa_tu_dong": khoa}):
            continue
        dem["nghi_viec"] += 1
        if e.get("relieving_date"):
            ngay, noi_dung = e.relieving_date, e.get("reason_for_leaving")
        else:
            dem["nghi_viec_khong_ngay"] += 1
            ngay = getdate(e.modified)
            noi_dung = "Backfill: không có ngày nghỉ việc, lấy ngày sửa hồ sơ gần nhất"
        if not dry_run:
            ghi_su_kien(e.name, "Nghỉ việc", ngay, khoa, noi_dung=noi_dung)
    # 4) Bắt đầu đóng BHXH — không bịa ngày
    for e in emps:
        if not e.get("ns_dong_bhxh"):
            continue
        khoa = f"bat-dau-bhxh:{e.name}:backfill"
        if frappe.db.exists("NS Su Kien", {"khoa_tu_dong": khoa}):
            continue
        dem["bat_dau_bhxh"] += 1
        if not dry_run:
            ghi_su_kien(
                e.name, "Bắt đầu đóng BHXH", today(), khoa,
                noi_dung=f"Ghi nhận khi khởi tạo app ns — ngày bắt đầu đóng thực tế chưa rõ, mức trừ {flt(e.get(common.F_BAO_HIEM)):,.0f}",
            )
    # 5) SalaryProduct
    if frappe.db.exists("DocType", "SalaryProduct"):
        try:
            m = frappe.get_meta("SalaryProduct")
            fn = {f.fieldname for f in m.fields}
            ok = "employee" in fn and any(c in fn for c in ("month", "thang")) and any(c in fn for c in ("year", "nam")) \
                and any(c in fn for c in ("luongthucnhan", "luong_thuc_nhan", "tongtien", "tong_tien", "thucnhan"))
            dem["salaryproduct"] = "MAP ĐƯỢC → timeline hiện 'Lương khoán (cũ)'" if ok else \
                "CÒN DocType nhưng mapping không rõ (thiếu employee/tháng/năm/tổng) → bỏ qua, không đoán"
        except Exception as ex:  # noqa
            dem["salaryproduct"] = f"lỗi đọc meta: {ex}"
    else:
        dem["salaryproduct"] = "không có DocType"
    if not dry_run:
        frappe.db.commit()
    frappe.flags.ns_backfill = False
    print("\n=== ns backfill" + (" (DRY RUN)" if dry_run else "") + " ===")
    for k, v in dem.items():
        print(f"{k:28s}: {v}")
    return dem
