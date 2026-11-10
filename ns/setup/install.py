import frappe

# Role cho công nhân tự xem phiếu lương (/phieuluong). Không vào Desk → Frappe xếp Website User.
# home_page: trang vào sau khi đăng nhập ở /login (frappe.website.utils.get_home_page đọc Role.home_page).
ROLE_CONG_NHAN = {"role_name": "NS Cong Nhan", "desk_access": 0, "home_page": "phieuluong"}


def after_install():
    """Việc sau cài: tạo role của app; backfill chạy tay:
    bench --site <site> execute ns.setup.backfill.run
    (tách riêng để mrhuychien kiểm trước khi ghi dữ liệu)."""
    try:
        dam_bao_role()
    except Exception:
        frappe.log_error(frappe.get_traceback(), "ns.after_install.dam_bao_role")
    try:
        frappe.logger("ns").info(
            "ns installed — chạy `bench --site <site> execute ns.setup.backfill.run` để backfill."
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "ns.after_install")


def after_migrate():
    try:
        dam_bao_role()
    except Exception:
        frappe.log_error(frappe.get_traceback(), "ns.after_migrate.dam_bao_role")


def dam_bao_role():
    """Tạo role của app nếu CHƯA có; role đã có thì KHÔNG đụng tới (bài học app sx D105).

    Không ship role qua fixtures: fixtures bị xoá - tạo lại mỗi lần migrate, tạo lại role là Frappe tính lại kiểu
    tài khoản của mọi người giữ role đó → đăng xuất họ. Và quản trị chỉnh role trên site (Home Page, Desk Access)
    thì phải giữ nguyên qua các lần deploy."""
    ten = ROLE_CONG_NHAN["role_name"]
    if frappe.db.exists("Role", ten):
        return []
    frappe.get_doc({"doctype": "Role", "is_custom": 1, **ROLE_CONG_NHAN}).insert(ignore_permissions=True)
    return [ten]
