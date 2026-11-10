"""Phiếu lương XEM NHANH — chỉ đọc. Port từ app sx: thẻ Phiếu lương (D110) + từng ngày (D234).

Một "view model" chung cho cả hai nguồn lương của RVHG:
  · Công khoán → `SX Phieu Luong` (app sx): các khoản, sản phẩm trong tháng gộp theo mã, TỪNG NGÀY làm những
    gì (số lượng, đơn giá, thành tiền, cộng ngày = lương SP × hệ số + tiền ăn), lỗi phạt.
  · Công nhật → `SalaryDay`: các khoản, bảng chấm công từng ngày (công, thêm giờ), lỗi phạt.

Dùng ở ba chỗ: tab Công & lương của hồ sơ, bảng lương tháng (nút Xem) và trang công nhân tự xem
`/phieuluong`. Cùng MỘT hàm dựng → phòng nhân sự và công nhân nhìn đúng một con số.

Nguyên tắc giữ từ sx: MỌI SỐ TIỀN LẤY NGUYÊN TỪ PHIẾU (controller của sx / Client Script SalaryDay đã tính lúc
lưu), không tính lại — hai nơi tính là hai con số. Ở đây chỉ GỘP dòng để trình bày (cùng mã + cách làm + đơn
giá trong một ngày / cả tháng); tổng sau gộp luôn bằng tổng các dòng gốc.

Đọc mềm (gotcha #22): app ns không đổi schema của SalaryDay / SX Phieu Luong; cột thiếu → .get() ra None.
Quyền: hàm dựng KHÔNG kiểm quyền — người gọi (whitelisted method) kiểm trước: `xem` dưới đây cho phòng nhân
sự (guard), `ns.api.cong_nhan` cho công nhân (khoá về đúng nhân viên của phiên đăng nhập).
"""
import frappe
from frappe import _
from frappe.utils import cint, flt, getdate

from ns.api import guard

DT_NHAT = "SalaryDay"
DT_KHOAN = "SX Phieu Luong"
THU = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"]

# Bảng lỗi phạt của SalaryDay (bangghiloiphat): ô số là soluong / giatien / thanhtienphat (đã đối chiếu với
# Client Script — xem salaryday.py); ô LÝ DO chưa có trong dump → thử các tên hay gặp rồi mới tới ô chữ đầu tiên.
O_LY_DO_PHAT = ("loi", "loiphat", "tenloi", "tenloiphat", "ly_do", "lydo", "noidung", "noi_dung", "ten",
                "mota", "mo_ta", "diengiai", "dien_giai", "ghichu", "ghi_chu")
KIEU_CHU = ("Data", "Small Text", "Text", "Long Text", "Link", "Select")


def _ngay(v):
    """'YYYY-MM-DD' hoặc None (ô ngày trống / hỏng không làm vỡ cả phiếu)."""
    if not v:
        return None
    try:
        return str(getdate(v))
    except Exception:
        return None


def _thu(ngay):
    try:
        return THU[getdate(ngay).weekday()] if ngay else ""
    except Exception:
        return ""


def _khoan(cap):
    """[(tên, tiền)] → chỉ khoản khác 0, đúng thứ tự trên phiếu giấy (như thẻ sx)."""
    return [{"ten": t, "tien": flt(v)} for t, v in cap if flt(v)]


def _docstatus(doc):
    return cint(doc.get("docstatus"))


def _ten_nv(employee):
    if not employee:
        return ""
    return frappe.db.get_value("Employee", employee, "employee_name") or employee


# ─────────────────────────────────────────────────────────── công khoán ──


def _sp_cua_ngay(ds):
    """Dòng sản phẩm của MỘT ngày (D234): sản phẩm trước (giữ thứ tự ghi), làm theo giờ sau, giá cao trước."""
    return sorted(ds, key=lambda g: (1, -g["don_gia"]) if g.get("theo_gio") else (0, 0))


def xem_khoan(p):
    """SX Phieu Luong → view model. Cùng cách gộp với `sx.api.luong.chi_tiet` (D225 làm theo giờ, D233 mỗi mức giờ
    một dòng, D234 từng ngày)."""
    sp, gio_ngay, sp_ngay = {}, {}, {}
    for r in p.get("chi_tiet") or []:
        ngay = _ngay(r.get("ngay"))
        if cint(r.get("theo_gio")):
            # D225: làm theo giờ — gộp theo đơn giá / giờ, số lượng là số GIỜ
            k = ("", "gio", flt(r.get("don_gia")))
            moi = {"ten": _("Làm theo giờ"), "cach_lam": "", "theo_gio": True, "don_gia": flt(r.get("don_gia")),
                   "so_luong": 0.0, "thanh_tien": 0.0}
            sl = flt(r.get("so_gio"))
            gio_ngay[ngay] = gio_ngay.get(ngay, 0.0) + sl
        else:
            k = (r.get("san_pham") or "", r.get("cach_lam") or "", flt(r.get("don_gia")))
            moi = {"ten": r.get("ten_san_pham") or r.get("san_pham") or "", "cach_lam": r.get("cach_lam") or "",
                   "theo_gio": False, "don_gia": flt(r.get("don_gia")), "so_luong": 0, "thanh_tien": 0.0}
            sl = cint(r.get("so_luong"))
        # Cả tháng và từng ngày — mỗi bảng một bản riêng (dict(moi)), không cộng hai lần vào cùng một dòng
        for bang in (sp, sp_ngay.setdefault(ngay, {})):
            g = bang.setdefault(k, dict(moi))
            g["so_luong"] += sl
            g["thanh_tien"] += flt(r.get("thanh_tien"))

    ngay = []
    for r in sorted(p.get("dong") or [], key=lambda r: _ngay(r.get("ngay")) or ""):
        d = _ngay(r.get("ngay"))
        ngay.append({
            "ngay": d, "thu": r.get("thu") or _thu(d), "an_ca": cint(r.get("an_ca")), "an_dem": cint(r.get("an_dem")),
            "tien_an": flt(r.get("tien_an")), "luong_sp": flt(r.get("luong_sp")), "he_so": flt(r.get("he_so")),
            "so_gio": gio_ngay.get(d, 0.0), "thu_nhap": flt(r.get("thu_nhap_ngay")),
            "sp": _sp_cua_ngay(list(sp_ngay.get(d, {}).values())),
        })
    cong = [
        (_("Lương sản phẩm"), p.get("luong_san_pham")), (_("Tiền ăn ca + ăn đêm"), p.get("tien_an")),
        (_("Chuyên cần"), p.get("chuyen_can")), (_("Hỗ trợ ngày công"), p.get("ho_tro_ngay_cong")),
        (_("Thưởng thâm niên"), p.get("thuong_tham_nien")), (_("Hỗ trợ khác"), p.get("ho_tro")),
    ]
    tru = [(_("Tiền phạt"), p.get("tien_phat")), (_("Bảo hiểm"), p.get("bao_hiem"))]
    return {
        "loai": "khoan", "loai_ten": _("Lương công khoán"), "doctype": DT_KHOAN, "name": p.name,
        "employee": p.get("employee"), "ten": p.get("ten_nhan_vien") or _ten_nv(p.get("employee")),
        "thang": cint(p.get("thang")), "nam": cint(p.get("nam")),
        "docstatus": _docstatus(p), "da_duyet": _docstatus(p) == 1, "trang_thai": p.get("trang_thai") or "",
        "ngay_cong": flt(p.get("ngay_cong")), "ngay_san_xuat": flt(p.get("ngay_san_xuat")),
        "cong": _khoan(cong), "tru": _khoan(tru),
        "tong_tien": flt(p.get("tong_tien")), "tong_khau_tru": flt(p.get("tong_khau_tru")),
        "thuc_nhan": flt(p.get("luong_thuc_nhan")),
        "san_pham": sorted(sp.values(), key=lambda g: -g["thanh_tien"]),
        "ngay": ngay,
        "phat": [{"ly_do": r.get("ly_do") or "", "so_luong": flt(r.get("so_luong")),
                  "gia_tien": flt(r.get("gia_tien")), "tien": flt(r.get("thanh_tien"))}
                 for r in p.get("phat") or []],
        "ghi_chu": p.get("ghi_chu") or "",
        # Dòng sản phẩm 0 đồng = chưa có đơn giá (sx D99: phiếu còn dòng này thì chưa duyệt được)
        "chua_gia": sum(1 for g in sp.values() if not g["theo_gio"] and not flt(g["don_gia"])),
    }


# ─────────────────────────────────────────────────────────── công nhật ──


def _o_ly_do(doc, fieldname):
    """Ô chữ đầu tiên của bảng con (theo thứ tự meta) — dự phòng khi không trúng tên nào trong O_LY_DO_PHAT."""
    try:
        con = doc.meta.get_field(fieldname).options
        return [df.fieldname for df in frappe.get_meta(con).fields if df.fieldtype in KIEU_CHU]
    except Exception:
        return []


def _ly_do_phat(r, du_phong):
    for f in O_LY_DO_PHAT + tuple(du_phong):
        v = r.get(f)
        if v not in (None, ""):
            return str(v)
    return ""


def xem_nhat(p):
    """SalaryDay → view model. Các khoản cộng đúng như Client Script tính `tongtien`:
    lương ngày công + lương làm thêm + ăn ca + chuyên cần + hỗ trợ ngày công + hỗ trợ + thưởng khác + thâm niên;
    khấu trừ = bảo hiểm + tiền phạt. Ngày công / làm thêm đọc từ phiếu (Chủ nhật, 1-1, Bình Dương… Client Script
    đã xử lý) — bảng ngày chỉ là bảng chấm công gốc, không suy ra tiền từng ngày."""
    cong = [
        (_("Lương ngày công"), p.get("luongngaycong")), (_("Lương làm thêm"), p.get("luonglamthem")),
        (_("Tiền ăn ca"), p.get("anca")), (_("Chuyên cần"), p.get("chuyencan")),
        (_("Hỗ trợ ngày công"), p.get("hotrongaycong")), (_("Hỗ trợ"), p.get("hotro")),
        (_("Thưởng khác"), p.get("thuongkhac")), (_("Thưởng thâm niên"), p.get("thuongthamnien")),
    ]
    tru = [(_("Tiền phạt"), p.get("tienphat")), (_("Bảo hiểm"), p.get("baohiem"))]
    ngay = []
    for r in sorted(p.get("chamcong") or [], key=lambda r: _ngay(r.get("ngaycc")) or ""):
        d = _ngay(r.get("ngaycc"))
        ngay.append({"ngay": d, "thu": _thu(d), "cong": flt(r.get("congngay")), "them_gio": flt(r.get("themgio"))})
    du_phong = _o_ly_do(p, "bangghiloiphat") if p.get("bangghiloiphat") else []
    return {
        "loai": "nhat", "loai_ten": _("Lương công nhật"), "doctype": DT_NHAT, "name": p.name,
        "employee": p.get("employee"), "ten": p.get("employee_name") or _ten_nv(p.get("employee")),
        "thang": cint(p.get("month")), "nam": cint(p.get("year")),
        "docstatus": _docstatus(p), "da_duyet": _docstatus(p) == 1, "trang_thai": p.get("status") or "",
        "ngay_cong": flt(p.get("congngay")), "ngay_san_xuat": flt(p.get("ngaysanxuat")),
        "lam_them": flt(p.get("lamthem")), "luong_co_ban": flt(p.get("luongcoban")),
        "cong": _khoan(cong), "tru": _khoan(tru),
        "tong_tien": flt(p.get("tongtien")), "tong_khau_tru": flt(p.get("tongkhautru")),
        "thuc_nhan": flt(p.get("luongthucnhan")),
        "chuyen_khoan": flt(p.get("luongck")),
        "san_pham": [],
        "ngay": ngay,
        "phat": [{"ly_do": _ly_do_phat(r, du_phong), "so_luong": flt(r.get("soluong")),
                  "gia_tien": flt(r.get("giatien")), "tien": flt(r.get("thanhtienphat"))}
                 for r in p.get("bangghiloiphat") or []],
        "ghi_chu": p.get("ghichu") or p.get("ghi_chu") or "",
        "chua_gia": 0,
    }


# ─────────────────────────────────────────────────────────────── chung ──


def xem_doc(doc):
    """Document SalaryDay / SX Phieu Luong → view model (không kiểm quyền — người gọi kiểm)."""
    return xem_khoan(doc) if doc.doctype == DT_KHOAN else xem_nhat(doc)


def lay_doc(doctype, name):
    """Mở một phiếu lương sau khi người gọi đã kiểm quyền. Chỉ nhận đúng hai DocType lương."""
    if doctype not in (DT_NHAT, DT_KHOAN):
        frappe.throw(_("Không phải phiếu lương: {0}").format(doctype))
    if not frappe.db.table_exists(doctype):
        frappe.throw(_("Site chưa có bảng {0}.").format(doctype))
    if not name or not frappe.db.exists(doctype, name):
        frappe.throw(_("Không tìm thấy phiếu {0}.").format(name or ""), frappe.DoesNotExistError)
    return frappe.get_doc(doctype, name)


@frappe.whitelist()
def xem(doctype, name):
    """Phòng nhân sự xem một phiếu (bảng lương tháng → Xem). Đọc sau guard, bỏ qua quyền DocType
    (SX Phieu Luong chỉ mở cho SX Quan Ly — SPEC §4)."""
    guard()
    return xem_doc(lay_doc(doctype, name))
