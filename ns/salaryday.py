"""P1 (§7) — tính lại SalaryDay phía server.

Port Y NGUYÊN Client Script `SalaryDay` (công thức đã được kế toán xác nhận), kể cả
ngoại lệ theo mã nhân viên và hằng số. KHÔNG "sửa cho hợp lý", KHÔNG gộp,
KHÔNG đổi thứ tự điều kiện. Chỗ nào trông lạ: giữ nguyên + ghi chú
`# chép từ Client Script, giữ nguyên theo yêu cầu`.

Khác biệt kỹ thuật không tránh được: JS tra thâm niên BẤT ĐỒNG BỘ (2 lần frappe.call
trong validate) nên trên Desk `tongtien` chỉ gồm thưởng thâm niên ở lần Save thứ hai;
server tính đồng bộ → cho ngay kết quả của lần Save thứ hai. Số cuối cùng giống nhau,
chỉ bớt một lần bấm.

Bật hook: `bench --site <site> set-config ns_tinh_lai_salaryday 1` rồi `bench restart`
— CHỈ sau khi `doi_chieu` lệch = 0 trên mọi phiếu (xem README).
"""
import math

import frappe
from frappe.utils import cint, flt, getdate

FALLBACK = {
    "AN_CA": 20000,
    "AN_DEM": 10000,
    "HE_SO_LE": 1.2,
    "CC_DAT": 200000,
    "CC_DU": 300000,
    "CC_DU_CAO_DIEM": 1000000,
    "CHUAN": 22,
    "HO_TRO_NGAY": 70000,
    "TY_LE": 0.05,
    "THANG_CAO_DIEM": "11,12,1",
}
MAP_SX = {
    "AN_CA": "tien_an_ca",
    "AN_DEM": "tien_an_dem",
    "HE_SO_LE": "he_so_ngay_le",
    "CC_DAT": "chuyen_can_dat",
    "CC_DU": "chuyen_can_du",
    "CC_DU_CAO_DIEM": "chuyen_can_du_cao_diem",
    "CHUAN": "ngay_cong_chuan",
    "HO_TRO_NGAY": "ho_tro_ngay_cong",
    "TY_LE": "ty_le_tham_nien",
    "THANG_CAO_DIEM": "thang_cao_diem",
}
FIELD_TIEN = [
    "luongngaycong", "luonglamthem", "anca", "chuyencan", "hotrongaycong",
    "thuongthamnien", "tongtien", "tongkhautru", "luongthucnhan",
]
FIELD_THAM_NIEN = ["thuongthamnien", "tongtien", "luongthucnhan"]


def tham_so():
    """Đọc SX Settings qua sx.utils.get_settings(); thiếu app sx / thiếu field → fallback (giá trị JS)."""
    out = dict(FALLBACK)
    try:
        from sx.utils import get_settings  # type: ignore

        s = get_settings()
    except Exception:
        s = None
    if s is not None:
        for k, sx_key in MAP_SX.items():
            v = s.get(sx_key) if hasattr(s, "get") else getattr(s, sx_key, None)
            if v not in (None, ""):
                out[k] = v
    for k in out:
        if k != "THANG_CAO_DIEM":
            out[k] = flt(out[k])
    return out


def _thang_cao_diem(ts):
    return {cint(x) for x in str(ts.get("THANG_CAO_DIEM") or "").replace(";", ",").split(",") if str(x).strip()}


def _lui_thang(month, year, lui):
    m, y = cint(month), cint(year)
    for _ in range(lui):
        m -= 1
        if m <= 0:
            m, y = 12, y - 1
    return m, y


def _congngay_thang(employee, month, year):
    """Tra y như JS: frappe.db.get_value("SalaryDay", {employee, month, year}, "congngay")
    — bản mới sửa nhất, không lọc docstatus; không có → 0."""
    v = frappe.db.get_value("SalaryDay", {"employee": employee, "month": month, "year": year}, "congngay",
                            order_by="modified desc")
    return flt(v)


def _set(doc, field, value):
    if doc.meta.has_field(field):
        doc.set(field, value)


def tinh_lai(doc, ts=None):
    """Tính lại toàn bộ tiền trên doc SalaryDay (in-memory, không save)."""
    ts = ts or tham_so()
    AN_CA, AN_DEM, HE_SO_LE = ts["AN_CA"], ts["AN_DEM"], ts["HE_SO_LE"]
    CC_DAT, CC_DU, CC_DU_CAO_DIEM = ts["CC_DAT"], ts["CC_DU"], ts["CC_DU_CAO_DIEM"]
    CHUAN, HO_TRO_NGAY, TY_LE = ts["CHUAN"], ts["HO_TRO_NGAY"], ts["TY_LE"]
    THANG_CAO_DIEM = _thang_cao_diem(ts)

    rows = doc.get("chamcong") or []
    phat = doc.get("bangghiloiphat") or []
    if doc.get("ngay"):
        d = getdate(doc.ngay)
        doc.month = d.month
        doc.year = d.year
    month = cint(doc.get("month"))
    year = cint(doc.get("year"))
    if not rows:
        return  # không tính gì, giống JS

    congngay = lamthemgio = anchinh = anthem = conglamthem = congchunhat = congbd = 0.0
    for row in rows:
        cn = mung1 = False
        if row.get("ngaycc"):
            dd = getdate(row.ngaycc)
            cn = dd.weekday() == 6  # Chủ nhật
            mung1 = dd.day == 1 and dd.month == 1
        cong = flt(row.get("congngay"))
        them = flt(row.get("themgio"))
        congbd += math.floor(cong)
        if cn or mung1:
            conglamthem += cong
            congchunhat += cong
        else:
            congngay += cong
        lamthemgio += them
        if cong == 1:
            anchinh += 1
        if them > 3:
            anthem += 1
    tienphat = 0.0
    for p in phat:
        p.thanhtienphat = flt(p.get("soluong")) * flt(p.get("giatien"))
        tienphat += p.thanhtienphat

    ngaysanxuat = flt(doc.get("ngaysanxuat"))
    luongcoban = flt(doc.get("luongcoban"))
    baohiem = flt(doc.get("baohiem"))
    hotro = flt(doc.get("hotro"))
    thuongkhac = flt(doc.get("thuongkhac"))

    chuyencan = 0.0
    if (congngay < ngaysanxuat and congngay + congchunhat > 25) or congngay > ngaysanxuat:
        chuyencan = CC_DAT
    if congngay + congchunhat >= ngaysanxuat - 0.5:
        chuyencan = CC_DAT
    if ngaysanxuat > 29 and ngaysanxuat - congngay - congchunhat < 1:
        chuyencan = CC_DU_CAO_DIEM if month in THANG_CAO_DIEM else CC_DU

    hotrongaycong = 0.0
    if ngaysanxuat < CHUAN and ngaysanxuat - congngay < 1 and congngay + conglamthem < CHUAN:
        thieu = CHUAN - congngay - conglamthem - (0.5 if ngaysanxuat - congngay == 0.5 else 0)
        hotrongaycong = thieu * HO_TRO_NGAY
    if cint(doc.get("ancatoi")):
        anthem = 0

    if (doc.get("department") or "") == "Bình Dương - HGC":
        tienanca = congbd * AN_CA
        congngay = congngay + conglamthem + lamthemgio / 8
        conglamthem = lamthemgio = hotrongaycong = chuyencan = 0.0
    else:
        tienanca = anchinh * AN_CA + anthem * AN_DEM

    luongngaycong = luongcoban / 26 * congngay
    luonglamthem = luongcoban / 26 * (conglamthem + lamthemgio / 8) * HE_SO_LE
    tongkhautru = baohiem + tienphat
    if doc.get("employee") == "HR-EMP-00035":  # chép từ Client Script, giữ nguyên theo yêu cầu
        tienanca = 0.0
        chuyencan = 0.0
    if doc.get("employee") == "HR-EMP-00045":  # chép từ Client Script, giữ nguyên theo yêu cầu
        luonglamthem = luongcoban / 26 * (conglamthem + lamthemgio / 8.5) * HE_SO_LE
    if month == 2:
        hotrongaycong = 0.0

    if cint(doc.get("tinhthuongthamnien")):
        m1, y1 = _lui_thang(month, year, 1)
        m2, y2 = _lui_thang(month, year, 2)
        congngay_thang_1 = _congngay_thang(doc.get("employee"), m1, y1)
        congngay_thang_2 = _congngay_thang(doc.get("employee"), m2, y2)
        thamnienthangnay = luongcoban / 26 * congngay * TY_LE
        thamnienthangtruoc = luongcoban / 26 * congngay_thang_1 * TY_LE
        thamnienthangtruocnua = luongcoban / 26 * congngay_thang_2 * TY_LE
        thuongthamnien = thamnienthangnay + thamnienthangtruoc + thamnienthangtruocnua
    else:
        thamnienthangnay = thamnienthangtruoc = thamnienthangtruocnua = thuongthamnien = 0.0

    _set(doc, "luongngaycong", luongngaycong)
    _set(doc, "congngay", congngay)
    if doc.get("employee") == "HR-EMP-00035":  # chép từ Client Script, giữ nguyên theo yêu cầu
        _set(doc, "lamthem", conglamthem + lamthemgio / 8.5)
    else:
        _set(doc, "lamthem", conglamthem + lamthemgio / 8)
    _set(doc, "luonglamthem", luonglamthem)
    _set(doc, "anca", tienanca)
    _set(doc, "tongkhautru", tongkhautru)
    _set(doc, "hotrongaycong", hotrongaycong)
    _set(doc, "tienphat", tienphat)
    _set(doc, "chuyencan", chuyencan)
    _set(doc, "thamnienthangnay", thamnienthangnay)
    _set(doc, "thamnienthangtruoc", thamnienthangtruoc)
    _set(doc, "thamnienthangtruocnua", thamnienthangtruocnua)
    _set(doc, "thuongthamnien", thuongthamnien)
    tongtien = luongngaycong + luonglamthem + tienanca + chuyencan + hotrongaycong + hotro + thuongkhac + thuongthamnien
    _set(doc, "tongtien", tongtien)
    _set(doc, "luongthucnhan", tongtien - tongkhautru)
    return doc


def bat_hook():
    return bool(cint(frappe.conf.get("ns_tinh_lai_salaryday")))


def validate_hook(doc, method=None):
    """doc_events SalaryDay.validate — chỉ chạy khi site_config ns_tinh_lai_salaryday = 1.
    Không throw: lỗi tính toán ghi Error Log, không chặn /chamcong2 lưu công."""
    if not bat_hook():
        return
    try:
        tinh_lai(doc)
    except Exception:
        frappe.log_error(frappe.get_traceback(), f"ns.salaryday.tinh_lai {doc.name}")


def doi_chieu(thang, nam, in_bang=True):
    """bench --site site1.local execute ns.salaryday.doi_chieu --kwargs "{'thang':9,'nam':2026}"

    Với mọi SalaryDay docstatus=1 của tháng: chạy tinh_lai trên bản trong bộ nhớ (không save),
    so từng field tiền, in bảng lệch. Phiếu tinhthuongthamnien=1 chỉ lệch đúng phần thâm niên
    được liệt kê riêng để mrhuychien kiểm."""
    thang, nam = cint(thang), cint(nam)
    ts = tham_so()
    names = frappe.get_all("SalaryDay", filters={"docstatus": 1, "month": thang, "year": nam}, pluck="name",
                           order_by="employee asc", limit_page_length=0)
    lech, lech_tham_nien, khop = [], [], 0
    for n in names:
        doc = frappe.get_doc("SalaryDay", n)
        truoc = {f: flt(doc.get(f)) for f in FIELD_TIEN}
        tinh_lai(doc, ts)
        sau = {f: flt(doc.get(f)) for f in FIELD_TIEN}
        diff = [(f, truoc[f], sau[f], sau[f] - truoc[f]) for f in FIELD_TIEN if abs(sau[f] - truoc[f]) > 0.005]
        if not diff:
            khop += 1
            continue
        chi_tham_nien = (
            cint(doc.get("tinhthuongthamnien")) == 1
            and all(f in FIELD_THAM_NIEN for f, *_ in diff)
            and len({round(d, 2) for _f, _a, _b, d in diff}) == 1
        )
        rec = {"name": n, "employee": doc.get("employee"), "diff": diff}
        (lech_tham_nien if chi_tham_nien else lech).append(rec)
    frappe.db.rollback()  # chắc chắn không ghi gì
    if in_bang:
        print(f"\n=== Đối chiếu SalaryDay T{thang}/{nam}: {len(names)} phiếu submitted · khớp {khop} · lệch {len(lech)} · chỉ lệch thâm niên {len(lech_tham_nien)} ===")
        for nhan, ds in (("LỆCH (phải báo, KHÔNG tự sửa công thức)", lech), ("CHỈ LỆCH THÂM NIÊN (kế toán mới Save 1 lần?)", lech_tham_nien)):
            if not ds:
                continue
            print(f"\n-- {nhan} --")
            print(f"{'Phiếu':22s} {'Employee':14s} {'Field':16s} {'JS':>16s} {'Server':>16s} {'Chênh':>14s}")
            for r in ds:
                for f, a, b, d in r["diff"]:
                    print(f"{r['name']:22s} {r['employee'] or '':14s} {f:16s} {a:16,.2f} {b:16,.2f} {d:14,.2f}")
        print("\nTham số dùng:", {k: v for k, v in ts.items()})
    return {"thang": thang, "nam": nam, "so_phieu": len(names), "khop": khop, "lech": lech, "lech_tham_nien": lech_tham_nien, "tham_so": ts}
