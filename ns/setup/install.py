import frappe


def after_install():
    """Việc sau cài: hiện tại chỉ ghi log hướng dẫn. Backfill chạy tay:
    bench --site <site> execute ns.setup.backfill.run
    (tách riêng để mrhuychien kiểm trước khi ghi dữ liệu)."""
    try:
        frappe.logger("ns").info(
            "ns installed — chạy `bench --site <site> execute ns.setup.backfill.run` để backfill."
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "ns.after_install")
