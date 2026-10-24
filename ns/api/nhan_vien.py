"""§4.1 — Danh sách NLĐ, hồ sơ 1 người, lưu, tạo mới."""
import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, today

from ns.api import canh_bao, common, guard
from ns.api.bo_sung import pct, tinh_thieu, _meta_cot

TAB = {
    "bhxh": {"status": "Active", "ns_dong_bhxh": 1},
    "khong_bhxh": {"status": "Active", "ns_dong_bhxh": 0},
    "tam_nghi": {"status": ("in", ["Inactive", "Suspended"])},
    "da_nghi": {"status": "Left"},
}


def _filters_tab(tab, department, q):
    if tab not in TAB:
        frappe.throw(_("Tab không hợp lệ: {0}").format(tab))
    f = dict(TAB[tab])
    if "ns_dong_bhxh" in f and not common.meta_emp().has_field("ns_dong_bhxh"):
        frappe.throw(_("Chưa có field ns_dong_bhxh — chạy bench migrate."))
    return common.loc_bo_phan(f, department)


def _dong(e, gt, ctx, cols):
    thieu, n_ap, n_du, _g = tinh_thieu(e, gt, cols, ctx["hom_nay"])
    return {
        "name": e.name,
        "employee_name": e.employee_name,
        "department": e.department,
        "loai_luong": common.loai_luong(e.department),
        "status": e.status,
        "date_of_joining": e.date_of_joining,
        "tham_nien_nam": common.tham_nien_nam(e.date_of_joining),
        common.F_BAO_HIEM: flt(e.get(common.F_BAO_HIEM)),
        "bao_hiem": flt(e.get(common.F_BAO_HIEM)),
        "ns_dong_bhxh": cint(e.get("ns_dong_bhxh")),
        common.F_LUONG_CB: flt(e.get(common.F_LUONG_CB)),
        "luong_cb": flt(e.get(common.F_LUONG_CB)),
        "cell_number": e.cell_number,
        "image": e.get("image"),
        "pct_du": pct(n_du, n_ap),
        "canh_bao": canh_bao.tinh(e, gt, ctx),
    }


@frappe.whitelist()
def danh_sach(tab="bhxh", department=None, q=None):
    """Danh sách theo tab (bhxh / khong_bhxh / tam_nghi / da_nghi) + đếm từng tab."""
    guard()
    or_filters = common.dieu_kien_tim(q)
    filters = _filters_tab(tab, department, q)
    emps = frappe.get_all(
        "Employee", filters=filters, or_filters=or_filters,
        fields=common.fields_co("Employee", common.FIELD_DANH_SACH),
        order_by="employee_name asc", limit_page_length=0,
    )
    gt = common.lay_giay_to([e.name for e in emps])
    ctx = canh_bao.ngu_canh()
    cols = _meta_cot()
    dong = [_dong(e, gt.get(e.name, []), ctx, cols) for e in emps]
    tong_so = {}
    for t in TAB:
        tong_so[t] = frappe.db.count("Employee", filters=_filters_tab(t, department, None)) if not or_filters else len(
            frappe.get_all("Employee", filters=_filters_tab(t, department, None), or_filters=or_filters, pluck="name", limit_page_length=0)
        )
    return {"tab": tab, "dong": dong, "tong_so": tong_so}


@frappe.whitelist()
def chi_tiet(name):
    """Hồ sơ 1 người: field whitelist + ns_giay_to + canh_bao + loai_luong + thieu."""
    guard()
    doc = frappe.get_doc("Employee", name)
    meta = common.meta_emp()
    out = {}
    for f in common.WHITELIST_SUA + common.FIELD_DOC_THEM:
        if f == "ns_giay_to":
            continue
        if f == "name" or meta.has_field(f):
            out[f] = doc.get(f)
    out["name"] = doc.name
    gt = [r.as_dict() for r in (doc.get("ns_giay_to") or [])] if meta.has_field("ns_giay_to") else []
    for r in gt:
        for k in ("doctype", "parent", "parenttype", "parentfield", "owner", "modified_by", "creation", "modified", "docstatus"):
            r.pop(k, None)
    out["ns_giay_to"] = gt
    emp = frappe._dict(out)
    ctx = canh_bao.ngu_canh()
    out["canh_bao"] = canh_bao.tinh(emp, gt, ctx)
    out["loai_luong"] = common.loai_luong(doc.department)
    out["tham_nien_nam"] = common.tham_nien_nam(doc.date_of_joining)
    cols = _meta_cot()
    thieu, n_ap, n_du, g = tinh_thieu(emp, gt, cols, ctx["hom_nay"])
    out["thieu"] = thieu
    out["pct_du"] = pct(n_du, n_ap)
    out["thieu_label"] = {**{c["field"]: c["label"] for c in cols}}
    out["tuy_chon"] = common.tuy_chon()
    out["field_co"] = [f for f in common.WHITELIST_SUA if meta.has_field(f)]
    return out


@frappe.whitelist()
def luu(name, data=None):
    """Lưu hồ sơ: chỉ key whitelist; ns_giay_to thay cả bảng; validate §4.1."""
    guard()
    data = common.parse_data(data)
    doc = frappe.get_doc("Employee", name)
    common.ap_dung_data(doc, data)
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return chi_tiet(name)


@frappe.whitelist()
def tao(data=None):
    """Tạo Employee mới: first_name = họ tên đầy đủ (cách RVHG đang dùng)."""
    guard()
    data = common.parse_data(data)
    ho_ten = (data.get("first_name") or data.get("employee_name") or "").strip()
    if not ho_ten:
        frappe.throw(_("Thiếu họ tên."))
    for f, label in (("gender", "giới tính"), ("date_of_birth", "ngày sinh"), ("date_of_joining", "ngày vào làm")):
        if not data.get(f):
            frappe.throw(_("Thiếu {0}.").format(label))
    doc = frappe.new_doc("Employee")
    doc.naming_series = "HR-EMP-"
    doc.first_name = ho_ten
    doc.status = "Active"
    doc.company = data.get("company") or common.company_mac_dinh()
    cho_phep = {"gender", "date_of_birth", "date_of_joining", "department", "custom_cccd", "cell_number",
                "designation", "custom_zalo", "attendance_device_id"}
    payload = {k: v for k, v in data.items() if k in cho_phep and v not in (None, "")}
    common.ap_dung_data(doc, payload)
    if getdate(doc.date_of_joining) > getdate(today()):
        frappe.throw(_("Ngày vào làm không được sau hôm nay."))
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    return {"name": doc.name, "employee_name": doc.employee_name}
