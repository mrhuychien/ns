"""Trang /phieuluong — công nhân tự xem phiếu lương của chính mình.

Thẻ đăng nhập in QR `/phieuluong?the=<mã NV chủ thẻ>`. Guest → /login?redirect-to=<đúng địa chỉ đó> (giữ ?the=). Đăng
nhập rồi:
  · tài khoản gắn hồ sơ (Employee.ns_tai_khoan) → xem phiếu của hồ sơ đó (thẻ của chính mình, hoặc không có ?the=);
  · người có quyền HR + ?nv=<mã NV> (nút 👁) hoặc ?the=<mã NV> (quét thẻ của công nhân) → XEM NHƯ CÔNG NHÂN;
  · người KHÔNG có quyền HR quét thẻ của người khác → "thẻ này không phải của tài khoản đang đăng nhập" + nút đăng
    xuất; KHÔNG tải phiếu nào, KHÔNG nói thẻ của ai (mã trên địa chỉ ai cũng gõ được);
  · còn lại → "chưa gắn hồ sơ" + đang đăng nhập bằng tài khoản nào + nút đăng xuất.
Điện thoại hay đang đăng nhập sẵn một tài khoản khác (vd. phòng nhân sự quét thử thẻ trên máy mình) — vì thế màn nào
cũng ghi rõ tài khoản đang đăng nhập và có nút đăng xuất để đăng nhập bằng thẻ.
Đây chỉ là khung + context; số liệu lấy qua ns.api.cong_nhan (kiểm quyền lại ở mọi lần gọi).
"""
import re
from urllib.parse import quote

import frappe
from frappe.utils import now, today

from ns.api import co_quyen
from ns.api.cong_nhan import dia_chi_the, nhan_vien_cua

no_cache = 1
sitemap = 0

# PHẢI khớp BUILD trong public/ns/cong_nhan.js (Luật vàng #2 — chống shell cũ)
SHELL_BUILD = "ns-cn4"


def _asset_version():
    return re.sub(r"[^0-9A-Za-z.\-T]", "-", now().replace(" ", "T").replace(":", "-"))


def get_context(context):
    user = frappe.session.user
    the = (frappe.form_dict.get("the") or "").strip()      # mã NV in trong QR của thẻ
    if not user or user == "Guest":
        frappe.local.flags.redirect_location = "/login?redirect-to=" + quote(dia_chi_the(the), safe="")
        raise frappe.Redirect
    context.no_cache = 1
    context.show_sidebar = 0
    context.no_breadcrumbs = 1
    context.title = "Phiếu lương"
    context.shell_build = SHELL_BUILD
    context.asset_version = _asset_version()

    la_hr = co_quyen(user)
    cua_toi = nhan_vien_cua(user)
    nv = (frappe.form_dict.get("nv") or "").strip()
    muc_tieu = nv or the
    xem_thay = bool(la_hr and muc_tieu and muc_tieu != cua_toi and frappe.db.exists("Employee", muc_tieu))
    # Thẻ của người khác mà không có quyền HR: không tải phiếu nào, chỉ mời đăng xuất.
    the_khac = bool(the and not xem_thay and the != cua_toi)
    emp = None if the_khac else (muc_tieu if xem_thay else cua_toi)
    e = frappe.db.get_value("Employee", emp, ["employee_name", "department"], as_dict=True) if emp else None
    ten_tk = frappe.db.get_value("User", user, "full_name") or user

    context.co_nhan_vien = bool(emp)
    context.la_hr = la_hr
    context.the_khac = the_khac
    context.co_ho_so_rieng = bool(cua_toi)
    context.ten_tk = ten_tk
    context.cn_context = {
        "user": user,
        "full_name": ten_tk,
        "employee": emp,
        "employeeName": (e or {}).get("employee_name") or emp,
        "department": (e or {}).get("department"),
        "xemThay": xem_thay,
        "tuThe": bool(xem_thay and the and not nv),       # HR đang xem nhờ quét thẻ (không phải nút 👁)
        "the": the or None,
        "laHr": la_hr,
        "coNhanVien": bool(emp),
        "assetVersion": context.asset_version,
        "csrfToken": frappe.sessions.get_csrf_token(),
        "shellBuild": SHELL_BUILD,
        "today": today(),
    }
    return context
