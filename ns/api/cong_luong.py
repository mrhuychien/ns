"""§4.4 — Công & lương của 1 người trong 1 tháng (chỉ đọc).

Mỗi phiếu kèm `xem` — view model phiếu lương dựng chung ở `ns.api.phieu_luong` (port thẻ Phiếu lương của sx:
các khoản → tổng thu nhập → trừ → thực nhận, sản phẩm trong tháng, từng ngày, lỗi phạt). Tab Công & lương vẽ từ
`xem`; trang công nhân `/phieuluong` vẽ từ đúng view model đó.
"""
from urllib.parse import quote, urlencode

import frappe
from frappe.utils import cint

from ns.api import guard
from ns.api.phieu import chon_phieu, phieu_khoan, phieu_nhat
from ns.api.phieu_luong import DT_KHOAN, DT_NHAT, lay_doc, xem_doc

IN_FORMAT_NHAT = "Phiếu lương công nhật"


@frappe.whitelist()
def thang(employee, thang, nam):
    """Phiếu của tháng: SalaryDay (ưu tiên submitted) và/hoặc SX Phieu Luong (đổi bộ phận giữa tháng thì có cả hai)."""
    guard()
    thang, nam = cint(thang), cint(nam)
    r_nhat, trung_nhat = chon_phieu(phieu_nhat(thang, nam, [employee]))
    r_khoan, trung_khoan = chon_phieu(phieu_khoan(thang, nam, [employee]))
    out = {"employee": employee, "thang": thang, "nam": nam, "phieu": []}
    if r_nhat:
        doc = lay_doc(DT_NHAT, r_nhat.name)
        out["phieu"].append({
            "loai": "Nhật", "doctype": DT_NHAT, "name": doc.name, "docstatus": cint(doc.docstatus),
            "trung": trung_nhat, "xem": xem_doc(doc),
            "in_url": "/printview?" + urlencode({"doctype": DT_NHAT, "name": doc.name, "format": IN_FORMAT_NHAT,
                                                 "no_letterhead": 0}),
            "desk_url": f"/app/salaryday/{quote(doc.name)}",
        })
    if r_khoan:
        doc = lay_doc(DT_KHOAN, r_khoan.name)
        out["phieu"].append({
            "loai": "Khoán", "doctype": DT_KHOAN, "name": doc.name, "docstatus": cint(doc.docstatus),
            "trung": trung_khoan, "xem": xem_doc(doc),
            "in_url": None, "desk_url": f"/app/sx-phieu-luong/{quote(doc.name)}",
        })
    return out
