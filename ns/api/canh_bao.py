"""§6 — Cảnh báo / Việc cần làm. Dùng chung cho canh_bao[] (danh sách, hồ sơ)
và viec.tong_hop(). Mỗi cảnh báo: {ma, muc: 'do'|'vang'|'xanh', chi_tiet}."""
import frappe
from frappe.utils import add_days, cint, flt, getdate, today

from ns.api import common
from ns.api.phieu import thong_ke_thang

LOAI_HD = {"Hợp đồng lao động", "Phụ lục HĐLĐ"}
LOAI_KHAM_SK = "Giấy khám sức khỏe"
LOAI_ATTP = "Xác nhận kiến thức ATTP"

TEN = {
    "hd_het_han": "Hợp đồng hết hạn / sắp hết hạn",
    "kham_sk_het_han": "Giấy khám sức khỏe hết hạn / sắp hết hạn",
    "attp_het_han": "Xác nhận ATTP hết hạn / sắp hết hạn",
    "thieu_cccd": "Thiếu CCCD",
    "thieu_bo_phan": "Chưa có bộ phận",
    "thieu_ma_may": "Thiếu mã máy chấm công",
    "thieu_luong_cb": "Thiếu lương cơ bản",
    "thieu_tk": "Có lương chuyển khoản nhưng thiếu số tài khoản",
    "bhxh_rui_ro": "Không đóng BHXH quá 30 ngày mà chưa ghi lý do",
    "bhxh_chua_muc": "Đóng BHXH nhưng chưa có mức trừ",
    "sinh_nhat": "Sinh nhật tháng này",
    "luong_thieu_phieu": "Tháng trước chưa có phiếu lương",
    "luong_con_nhap": "Tháng trước phiếu lương còn nháp",
    "luong_trung": "Trùng phiếu lương nháp",
}
THU_TU = list(TEN.keys())


def _nfc(s):
    return common.nfc(s or "")


def _moi_nhat(rows, loai_set):
    """Dòng giấy tờ mới nhất của 1 nhóm loại (ưu tiên ngay_het_han, rồi ngay_cap, rồi idx)."""
    cands = [r for r in rows if _nfc(r.get("loai")) in {_nfc(x) for x in loai_set}]
    if not cands:
        return None

    def key(r):
        return (
            str(r.get("ngay_het_han") or ""),
            str(r.get("ngay_cap") or ""),
            cint(r.get("idx")),
        )

    return sorted(cands, key=key)[-1]


def _muc_han(ngay_het_han, hom_nay, han):
    """None nếu còn xa; 'do' nếu đã qua; 'vang' nếu ≤ today+30."""
    if not ngay_het_han:
        return None
    d = getdate(ngay_het_han)
    if d < hom_nay:
        return "do"
    if d <= han:
        return "vang"
    return None


def ngu_canh(thang_truoc_ctx=True):
    """Ngữ cảnh chung tính 1 lần cho cả danh sách."""
    hom_nay = getdate(today())
    t, n = common.thang_truoc(hom_nay.month, hom_nay.year, 1)
    ctx = {
        "hom_nay": hom_nay,
        "han": add_days(hom_nay, 30),
        "moc_30": add_days(hom_nay, -30),
        "thang_truoc": (t, n),
        "phieu_thang_truoc": {},
        "phieu_thang_nay": {},
    }
    if thang_truoc_ctx:
        try:
            ctx["phieu_thang_truoc"] = thong_ke_thang(t, n)
            ctx["phieu_thang_nay"] = thong_ke_thang(hom_nay.month, hom_nay.year)
        except Exception:
            frappe.log_error(frappe.get_traceback(), "ns.canh_bao.ngu_canh")
    return ctx


def tinh(emp, giay_to, ctx):
    """Trả list cảnh báo cho 1 Employee (dict từ get_all)."""
    out = []
    hom_nay, han = ctx["hom_nay"], ctx["han"]
    active = emp.get("status") == "Active"
    khoan = common.la_khoan(emp.get("department"))

    def add(ma, muc, chi_tiet=None):
        out.append({"ma": ma, "ten": TEN[ma], "muc": muc, "chi_tiet": chi_tiet})

    # Giấy tờ hết hạn (áp cho mọi trạng thái trừ Left)
    if emp.get("status") != "Left":
        hd = _moi_nhat(giay_to, LOAI_HD)
        muc_hd = _muc_han(hd.get("ngay_het_han"), hom_nay, han) if hd else None
        muc_ce = _muc_han(emp.get("contract_end_date"), hom_nay, han)
        muc = "do" if "do" in (muc_hd, muc_ce) else ("vang" if "vang" in (muc_hd, muc_ce) else None)
        if muc:
            ngay = (hd.get("ngay_het_han") if muc_hd else None) or emp.get("contract_end_date")
            add("hd_het_han", muc, f"Hết hạn {frappe.format(ngay, {'fieldtype': 'Date'})}")
        ksk = _moi_nhat(giay_to, {LOAI_KHAM_SK})
        if ksk:
            m = _muc_han(ksk.get("ngay_het_han"), hom_nay, han)
            if m:
                add("kham_sk_het_han", m, f"Hết hạn {frappe.format(ksk.get('ngay_het_han'), {'fieldtype': 'Date'})}")
        attp = _moi_nhat(giay_to, {LOAI_ATTP})
        if attp:
            m = _muc_han(attp.get("ngay_het_han"), hom_nay, han)
            if m:
                add("attp_het_han", m, f"Hết hạn {frappe.format(attp.get('ngay_het_han'), {'fieldtype': 'Date'})}")

    if active:
        if not emp.get("custom_cccd"):
            add("thieu_cccd", "vang")
        if not emp.get("department"):
            add("thieu_bo_phan", "vang")
        if not khoan and not emp.get("attendance_device_id"):
            add("thieu_ma_may", "vang")
        if not khoan and flt(emp.get(common.F_LUONG_CB)) == 0:
            add("thieu_luong_cb", "vang")
        if (
            not cint(emp.get("ns_dong_bhxh"))
            and emp.get("date_of_joining")
            and getdate(emp.get("date_of_joining")) <= ctx["moc_30"]
            and not emp.get("ns_ly_do_khong_bhxh")
        ):
            add("bhxh_rui_ro", "do")

    if flt(emp.get(common.F_LUONG_TK)) > 0 and not emp.get("bank_ac_no"):
        add("thieu_tk", "vang")
    if cint(emp.get("ns_dong_bhxh")) and flt(emp.get(common.F_BAO_HIEM)) == 0:
        add("bhxh_chua_muc", "vang")
    if emp.get("date_of_birth"):
        try:
            if getdate(emp.get("date_of_birth")).month == hom_nay.month:
                add("sinh_nhat", "xanh", frappe.format(emp.get("date_of_birth"), {"fieldtype": "Date"}))
        except Exception:
            pass

    # Lương tháng trước
    if active:
        t, n = ctx["thang_truoc"]
        p = ctx["phieu_thang_truoc"].get(emp.get("name"), {"nhat": [], "khoan": []})
        tat_ca = p["nhat"] + p["khoan"]
        da_vao_truoc = True
        if emp.get("date_of_joining"):
            doj = getdate(emp.get("date_of_joining"))
            da_vao_truoc = (doj.year, doj.month) <= (n, t)
        if not tat_ca and da_vao_truoc:
            add("luong_thieu_phieu", "vang", f"T{t}/{n}")
        elif tat_ca and all(cint(r.docstatus) == 0 for r in tat_ca):
            add("luong_con_nhap", "vang", f"T{t}/{n}")
        for nhan, (tt, nn) in (("thang_truoc", (t, n)), ("thang_nay", (hom_nay.month, hom_nay.year))):
            pp = ctx[f"phieu_{nhan}"].get(emp.get("name"), {"nhat": [], "khoan": []})
            for nguon in ("nhat", "khoan"):
                if len([r for r in pp[nguon] if cint(r.docstatus) == 0]) > 1:
                    add("luong_trung", "do", f"T{tt}/{nn} ({'công nhật' if nguon == 'nhat' else 'công khoán'})")
    out.sort(key=lambda c: ({"do": 0, "vang": 1, "xanh": 2}[c["muc"]], THU_TU.index(c["ma"])))
    return out
