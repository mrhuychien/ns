"""§4.4 — Công & lương của 1 người trong 1 tháng (chỉ đọc)."""
import frappe
from frappe.utils import cint, flt

from ns.api import common, guard
from ns.api.phieu import chon_phieu, doc_bang_con, phieu_khoan, phieu_nhat

IN_FORMAT_NHAT = "Phiếu lương công nhật"


def _header(doc, bo):
    d = {}
    for f in doc.meta.fields:
        if f.fieldtype in ("Table", "Section Break", "Column Break", "Tab Break", "HTML"):
            continue
        d[f.fieldname] = doc.get(f.fieldname)
    d["name"] = doc.name
    d["docstatus"] = doc.docstatus
    return d


@frappe.whitelist()
def thang(employee, thang, nam):
    """Phiếu của tháng: SalaryDay (ưu tiên submitted) hoặc SX Phieu Luong."""
    guard()
    thang, nam = cint(thang), cint(nam)
    r_nhat, trung_nhat = chon_phieu(phieu_nhat(thang, nam, [employee]))
    r_khoan, trung_khoan = chon_phieu(phieu_khoan(thang, nam, [employee]))
    out = {"employee": employee, "thang": thang, "nam": nam, "phieu": []}
    if r_nhat:
        doc = frappe.get_doc("SalaryDay", r_nhat.name)
        bang = doc_bang_con(doc)
        dong = [
            {"ngay": x.get("ngaycc"), "cong": flt(x.get("congngay")), "them_gio": flt(x.get("themgio"))}
            for x in bang.get("chamcong", [])
        ]
        phat = [
            {"noi_dung": x.get("loi") or x.get("noidung") or x.get("ten") or "", "so_luong": flt(x.get("soluong")),
             "gia_tien": flt(x.get("giatien")), "thanh_tien": flt(x.get("thanhtienphat")), "raw": x}
            for x in bang.get("bangghiloiphat", [])
        ]
        name_q = frappe.utils.quote(doc.name) if hasattr(frappe.utils, "quote") else doc.name
        out["phieu"].append({
            "loai": "Nhật", "doctype": "SalaryDay", "name": doc.name, "docstatus": doc.docstatus,
            "trung": trung_nhat, "header": _header(doc, "nhat"), "dong": dong, "phat": phat, "bang_con": bang,
            "in_url": f"/printview?doctype=SalaryDay&name={doc.name}&format={IN_FORMAT_NHAT}&no_letterhead=0",
            "desk_url": f"/app/salaryday/{doc.name}",
        })
    if r_khoan:
        doc = frappe.get_doc("SX Phieu Luong", r_khoan.name)
        bang = doc_bang_con(doc)
        dong = [
            {"ngay": x.get("ngay"), "thu": x.get("thu"), "an_ca": x.get("an_ca"), "an_dem": x.get("an_dem"),
             "tien_an": flt(x.get("tien_an")), "luong_sp": flt(x.get("luong_sp")), "he_so": flt(x.get("he_so")),
             "thu_nhap_ngay": flt(x.get("thu_nhap_ngay"))}
            for x in bang.get("dong", [])
        ]
        phat = [
            {"noi_dung": x.get("noi_dung") or x.get("loi") or "", "so_luong": flt(x.get("so_luong")),
             "gia_tien": flt(x.get("gia_tien") or x.get("don_gia")), "thanh_tien": flt(x.get("thanh_tien")), "raw": x}
            for x in bang.get("phat", [])
        ]
        out["phieu"].append({
            "loai": "Khoán", "doctype": "SX Phieu Luong", "name": doc.name, "docstatus": doc.docstatus,
            "trung": trung_khoan, "header": _header(doc, "khoan"), "dong": dong, "chi_tiet": bang.get("chi_tiet", []),
            "phat": phat, "bang_con": bang,
            "in_url": f"/app/sx-phieu-luong/{doc.name}", "desk_url": f"/app/sx-phieu-luong/{doc.name}",
        })
    return out
