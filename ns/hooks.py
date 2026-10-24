app_name = "ns"
app_title = "NS"
app_publisher = "RVHG"
app_description = "Quản lý người lao động RVHG — portal /ns"
app_email = "mrhuychien@gmail.com"
app_license = "MIT"
required_apps = ["frappe", "erpnext", "hrms"]

# ═══ Website ═══
# Route /ns do www/ns.py + www/ns.html phục vụ (SPA hash router).
website_route_rules = [
    {"from_route": "/ns/<path:app_path>", "to_route": "ns"},
]

# ═══ DocType Events ═══
doc_events = {
    "Employee": {
        # Đồng bộ cờ ns_dong_bhxh theo custom_bảo_hiểm (§3.1) — chỉ tính toán, không throw.
        "validate": "ns.events.employee.validate",
        # Sự kiện tự động (§3.4). Bỏ qua khi frappe.flags.ns_backfill.
        "after_insert": "ns.events.employee.after_insert",
        "on_update": "ns.events.employee.on_update",
    },
    # P1 (§7): tính lại SalaryDay phía server. Hàm chỉ chạy khi site_config
    # có ns_tinh_lai_salaryday = 1 (bật sau khi `ns.salaryday.doi_chieu` lệch = 0).
    "SalaryDay": {
        "validate": "ns.salaryday.validate_hook",
    },
}

# ═══ Fixtures ═══
# Chỉ Custom Field prefix ns_ trên Employee. KHÔNG export Property Setter của Employee.
fixtures = [
    {
        "doctype": "Custom Field",
        "filters": [["dt", "=", "Employee"], ["fieldname", "like", "ns_%"]],
    },
]

# ═══ Install ═══
after_install = "ns.setup.install.after_install"
