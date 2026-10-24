"""§4.2 — Sự kiện tay trên timeline."""
import frappe
from frappe import _

from ns.api import guard, guard_quan_ly


@frappe.whitelist()
def them(employee, ngay, loai, tieu_de=None, noi_dung=None, tep=None):
    """Thêm sự kiện nguồn Tay."""
    guard()
    if not frappe.db.exists("Employee", employee):
        frappe.throw(_("Nhân viên không tồn tại."))
    doc = frappe.get_doc({
        "doctype": "NS Su Kien",
        "employee": employee,
        "ngay": ngay,
        "loai": loai,
        "tieu_de": tieu_de or loai,
        "noi_dung": noi_dung,
        "tep": tep,
        "nguon": "Tay",
    })
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    return doc.as_dict()


@frappe.whitelist()
def sua_noi_dung(name, noi_dung=None, tieu_de=None):
    """Sửa nội dung (mọi nguồn — với Tự động chỉ được bổ sung noi_dung)."""
    guard()
    doc = frappe.get_doc("NS Su Kien", name)
    doc.noi_dung = noi_dung
    if tieu_de is not None and doc.nguon == "Tay":
        doc.tieu_de = tieu_de
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return doc.as_dict()


@frappe.whitelist()
def xoa(name):
    """Xoá sự kiện — chỉ nguồn Tay, chỉ HR Manager / System Manager."""
    guard_quan_ly()
    doc = frappe.get_doc("NS Su Kien", name)
    if doc.nguon != "Tay":
        frappe.throw(_("Không xoá được sự kiện tự động."))
    doc.delete(ignore_permissions=True)
    frappe.db.commit()
    return {"ok": True}
