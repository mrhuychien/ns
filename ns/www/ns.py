"""Context bridge cho SPA /ns (§4.8)."""
import re

import frappe
from frappe.utils import now, today

from ns.api import co_quyen, common, la_quan_ly

no_cache = 1
sitemap = 0

# PHẢI khớp BUILD trong public/ns/shell.js (Luật vàng #2 — chống shell cũ)
SHELL_BUILD = "ns-r1"


def _asset_version():
    return re.sub(r"[^0-9A-Za-z.\-T]", "-", now().replace(" ", "T").replace(":", "-"))


def get_context(context):
    user = frappe.session.user
    if not user or user == "Guest":
        frappe.local.flags.redirect_location = "/login?redirect-to=/ns"
        raise frappe.Redirect
    context.no_cache = 1
    context.show_sidebar = 0
    context.no_breadcrumbs = 1
    context.title = "Nhân sự RVHG"
    context.shell_build = SHELL_BUILD
    context.asset_version = _asset_version()
    context.co_quyen = co_quyen(user)
    deps, deps_all = [], []
    if context.co_quyen:
        try:
            deps = common.danh_sach_bo_phan()
            deps_all = frappe.get_all("Department", filters={"is_group": 0}, pluck="name", order_by="name asc", limit_page_length=0)
        except Exception:
            frappe.log_error(frappe.get_traceback(), "ns.www.ns.departments")
    context.ns_context = {
        "user": user,
        "full_name": frappe.db.get_value("User", user, "full_name") or user,
        "isManager": la_quan_ly(user),
        "assetVersion": context.asset_version,
        "csrfToken": frappe.sessions.get_csrf_token(),
        "departments": deps + [common.KHONG_BO_PHAN],
        "departmentsAll": sorted(set(deps_all) | set(deps)),
        "today": today(),
        "shellBuild": SHELL_BUILD,
        "boPhanKhoan": common.BO_PHAN_KHOAN,
        "coQuyen": context.co_quyen,
    }
    return context
