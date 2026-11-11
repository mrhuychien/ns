app_name = "ns"
app_title = "NS"
app_publisher = "RVHG"
app_description = "Quản lý người lao động RVHG — portal /ns"
app_email = "mrhuychien@gmail.com"
app_license = "MIT"
required_apps = ["frappe", "erpnext", "hrms"]

# ═══ App trên Desk: ô màn Apps + icon trang chủ (lưới icon) ═══
# Bấm vào → trang chủ app trên Desk /desk/ns (workspace "NS", tiêu đề "Nhân sự": lối vào portal /ns, các màn của
# portal, danh mục Desk). Route /desk/…: khớp mẫu Desk của v16 (frappe.apps.DESK_APP_PATTERN) nên đăng nhập vẫn vào
# /desk, không bị đẩy ra màn chọn app (cách app sx D236 đã chạy). Ai thấy: ns.api.co_quyen_app_desk — người dùng Desk
# có vai HR; công nhân (Website User) không. Lưới icon đọc icon từ ns/desktop_icon/ns.json (migrate nạp), không đọc
# hook này. KHÔNG khai app_logo_url (Frappe lấy làm logo thanh điều hướng của cả Desk).
add_to_apps_screen = [
    {
        "name": "ns",
        "logo": "/assets/ns/images/ns-logo.svg",
        "title": "Nhân sự",
        "route": "/desk/ns",
        "has_permission": "ns.api.co_quyen_app_desk",
    }
]

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
# Role "NS Cong Nhan" (công nhân tự xem phiếu lương ở /phieuluong): CHỈ tạo khi thiếu — không ship qua fixtures
# (fixtures xoá - tạo lại role mỗi lần migrate → Frappe đăng xuất người giữ role, bài học app sx D105).
after_install = "ns.setup.install.after_install"
after_migrate = "ns.setup.install.after_migrate"
