"""Trang /phieuluong — công nhân tự xem phiếu lương của chính mình.

Guest → /login?redirect-to=/phieuluong (thẻ đăng nhập in QR trỏ thẳng tới đây). Đăng nhập rồi:
  · tài khoản gắn hồ sơ (Employee.ns_tai_khoan) → xem phiếu của hồ sơ đó;
  · người có quyền HR + ?nv=<mã NV> → XEM NHƯ CÔNG NHÂN (đúng màn công nhân đang nhìn);
  · còn lại → thông báo "chưa gắn hồ sơ", không lộ gì.
Đây chỉ là khung + context; số liệu lấy qua ns.api.cong_nhan (kiểm quyền lại ở mọi lần gọi).
"""
import re

import frappe
from frappe.utils import now, today

from ns.api import co_quyen
from ns.api.cong_nhan import nhan_vien_cua

no_cache = 1
sitemap = 0

# PHẢI khớp BUILD trong public/ns/cong_nhan.js (Luật vàng #2 — chống shell cũ)
SHELL_BUILD = "ns-cn1"


def _asset_version():
    return re.sub(r"[^0-9A-Za-z.\-T]", "-", now().replace(" ", "T").replace(":", "-"))


def get_context(context):
    user = frappe.session.user
    if not user or user == "Guest":
        frappe.local.flags.redirect_location = "/login?redirect-to=/phieuluong"
        raise frappe.Redirect
    context.no_cache = 1
    context.show_sidebar = 0
    context.no_breadcrumbs = 1
    context.title = "Phiếu lương"
    context.shell_build = SHELL_BUILD
    context.asset_version = _asset_version()

    la_hr = co_quyen(user)
    nv = (frappe.form_dict.get("nv") or "").strip()
    xem_thay = bool(nv and la_hr and frappe.db.exists("Employee", nv))
    emp = nv if xem_thay else nhan_vien_cua(user)
    e = frappe.db.get_value("Employee", emp, ["employee_name", "department"], as_dict=True) if emp else None

    context.co_nhan_vien = bool(emp)
    context.la_hr = la_hr
    context.cn_context = {
        "user": user,
        "full_name": frappe.db.get_value("User", user, "full_name") or user,
        "employee": emp,
        "employeeName": (e or {}).get("employee_name") or emp,
        "department": (e or {}).get("department"),
        "xemThay": xem_thay,
        "laHr": la_hr,
        "coNhanVien": bool(emp),
        "assetVersion": context.asset_version,
        "csrfToken": frappe.sessions.get_csrf_token(),
        "shellBuild": SHELL_BUILD,
        "today": today(),
    }
    return context
