"""Icon NS vào BỐ CỤC ĐÃ LƯU của trang chủ Desk (lưới icon) — người có quyền mới được thêm. Chép cách app sx D238.

Frappe 16.16 (lưới icon): trang chủ /desk vẽ theo Desktop Layout riêng của từng người NẾU đã có (người từng kéo thả /
sửa lưới; bố cục là bản chép đầy đủ danh sách icon lúc lưu). Icon chuẩn thêm sau — icon NS ship ở ns/desktop_icon —
không tự vào bố cục đó: dòng Desktop Icon "NS" có trong DB mà người đã có bố cục không thấy (app sx đã gặp trên site).

Thêm icon NS vào CUỐI bố cục đã lưu của người có quyền (ns.api.co_quyen_app_desk — cùng điều kiện với ô NS), giữ
nguyên mọi sắp xếp khác. Người không có quyền: không đụng (bố cục đã lưu không qua lọc quyền — thêm vào là họ thấy
icon). Patch chạy MỘT lần; sau đó bố cục là của người dùng — họ dời / ẩn icon thì thôi. Người chưa có bố cục đã thấy
icon từ danh sách chuẩn, không cần gì.
"""

import json

import frappe

TEN = "NS"
# Ô của một icon như danh sách icon trên trang chủ (frappe.desk.doctype.desktop_icon.desktop_icon.get_desktop_icons).
TRUONG = ("label", "bg_color", "link", "link_type", "app", "icon_type", "parent_icon", "icon", "link_to", "idx",
          "standard", "logo_url", "hidden", "name", "restrict_removal", "icon_image")


def them_icon(ds, icon):
    """Bố cục `ds` (danh sách icon) thêm `icon` vào cuối hàng ngoài cùng → danh sách mới; không cần thêm (đã có, bố cục
    không phải danh sách) → None."""
    if not isinstance(ds, list):
        return None
    if any(isinstance(x, dict) and (x.get("name") == icon["name"] or x.get("label") == icon["label"]) for x in ds):
        return None
    idx = max([int(x.get("idx") or 0) for x in ds if isinstance(x, dict) and not x.get("parent_icon")] or [0]) + 1
    return ds + [dict(icon, idx=idx, parent_icon=None, hidden=0, child_icons=[])]


def execute():
    if not (frappe.db.table_exists("Desktop Layout") and frappe.db.exists("Desktop Icon", TEN)):
        return
    from ns.api import co_quyen_app_desk

    icon = frappe.db.get_value("Desktop Icon", TEN, [f for f in TRUONG if frappe.db.has_column("Desktop Icon", f)],
                               as_dict=True)
    so = 0
    for bc in frappe.get_all("Desktop Layout", fields=["name", "user", "layout"]):
        user = bc.user or bc.name
        if not co_quyen_app_desk(user):
            continue
        try:
            ds = json.loads(bc.layout or "null")
        except ValueError:
            continue
        moi = them_icon(ds, icon)
        if moi is None:
            continue
        # Đúng khuôn Frappe tự lưu (desktop_layout.save_layout: json.dumps mặc định, toàn ASCII) — trang chủ chèn chuỗi
        # này thẳng vào HTML (#desktop-layout) rồi JSON.parse lại.
        frappe.db.set_value("Desktop Layout", bc.name, "layout", json.dumps(moi), update_modified=False)
        so += 1
        print(f"ns: thêm icon NS vào trang chủ của {user}")
    frappe.db.commit()
    print(f"ns: xong — {so} bố cục trang chủ có thêm icon NS")
