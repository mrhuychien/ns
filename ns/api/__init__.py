"""API của app ns — mọi method whitelisted gọi guard() ở dòng đầu.

Quy ước (SPEC §4): user phải có 1 trong HR User / HR Manager / System Manager.
Guest hoặc user chỉ có role Employee → PermissionError. Sau guard, đọc SalaryDay /
SX Phieu Luong bằng frappe.get_all (bỏ qua quyền DocType vì SX Phieu Luong chỉ mở cho
SX Quan Ly); ghi Employee / NS Su Kien qua get_doc().save(ignore_permissions=True)
để hook chạy.
"""
import frappe
from frappe import _

ROLE_DUOC_PHEP = {"HR User", "HR Manager", "System Manager"}
ROLE_QUAN_LY = {"HR Manager", "System Manager"}


def roles_cua(user=None):
    user = user or frappe.session.user
    if not user or user == "Guest":
        return set()
    return set(frappe.get_roles(user))


def co_quyen(user=None):
    """True nếu user được vào /ns (không throw)."""
    return bool(roles_cua(user) & ROLE_DUOC_PHEP)


def la_quan_ly(user=None):
    return bool(roles_cua(user) & ROLE_QUAN_LY)


def guard():
    """Chặn Guest / user không có role HR. Gọi ở dòng đầu mọi whitelisted method."""
    if not co_quyen():
        frappe.throw(_("Bạn không có quyền dùng chức năng nhân sự."), frappe.PermissionError)


def guard_quan_ly():
    guard()
    if not la_quan_ly():
        frappe.throw(_("Chỉ HR Manager mới được thực hiện thao tác này."), frappe.PermissionError)
