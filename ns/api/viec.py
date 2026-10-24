"""§4.6 — Việc cần làm: gom cảnh báo §6 theo nhóm."""
import frappe

from ns.api import canh_bao, common, guard


@frappe.whitelist()
def tong_hop():
    """Các nhóm {ma, ten, muc, so_luong, dong[]} — chỉ NV chưa Left (trừ nhóm liên quan)."""
    guard()
    emps = common.lay_nhan_vien({"status": ("!=", "Left")})
    gt = common.lay_giay_to([e.name for e in emps])
    ctx = canh_bao.ngu_canh()
    nhom = {ma: {"ma": ma, "ten": canh_bao.TEN[ma], "muc": None, "so_luong": 0, "dong": []} for ma in canh_bao.THU_TU}
    for e in emps:
        for c in canh_bao.tinh(e, gt.get(e.name, []), ctx):
            g = nhom[c["ma"]]
            g["so_luong"] += 1
            g["dong"].append({
                "name": e.name, "employee_name": e.employee_name, "department": e.department,
                "muc": c["muc"], "chi_tiet": c.get("chi_tiet"),
            })
            if g["muc"] is None or {"do": 0, "vang": 1, "xanh": 2}[c["muc"]] < {"do": 0, "vang": 1, "xanh": 2}[g["muc"]]:
                g["muc"] = c["muc"]
    out = [g for g in nhom.values() if g["so_luong"]]
    co_do = any(g["muc"] == "do" for g in out)
    return {"nhom": out, "co_do": co_do, "so_do": sum(1 for g in out for d in g["dong"] if d["muc"] == "do")}
