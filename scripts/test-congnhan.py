"""Công nhân tự xem phiếu lương (ns/api/cong_nhan.py + trang www/phieuluong.py) — canh RÒ RỈ trước hết.

Lương là dữ liệu nhạy cảm giữa đồng nghiệp: một lỗ là cả xưởng biết lương nhau. Canh:
  · Guest / tài khoản chưa gắn / tài khoản bị khoá / site chưa migrate → PermissionError, không lộ gì;
  · công nhân chỉ thấy phiếu CỦA MÌNH — truyền mã người khác cũng bị chặn (chỉ HR xem thay được);
  · mặc định chỉ phiếu ĐÃ DUYỆT; nháp chỉ hiện khi bật ns_cong_nhan_xem_nhap, SalaryDay nháp còn cần P1;
  · phiếu đã huỷ không bao giờ hiện; tháng mới nhất trước; tổng thực nhận theo tháng lấy nguyên số phiếu;
  · trang /phieuluong: Guest → /login?redirect-to=/phieuluong; ?nv= chỉ có tác dụng với HR.
Chạy: python3 scripts/test-congnhan.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fakefrappe as F  # noqa: E402

F.cai()
M = F.nap_ns()
CN = M["cong_nhan"]
W = F.nap("ns.www.phieuluong", os.path.join(F.GOC, "ns", "www", "phieuluong.py"))

hong = 0


def kiem(ten, dk, ct=""):
    global hong
    if not dk:
        hong += 1
    print(f"  {'ok  ' if dk else 'HỎNG'} {ten}{(' — ' + ct) if ct and not dk else ''}")


def loi(fn):
    try:
        fn()
        return None
    except F.Loi as e:
        return f"{type(e).__name__}: {e}"


def nap_du_lieu():
    F.don_dep()
    F.them_user("an@x", ["NS Cong Nhan"])
    F.them_user("binh@x", ["NS Cong Nhan"])
    F.them_user("khoa@x", ["NS Cong Nhan"], enabled=0)
    F.them_user("lac@x", ["NS Cong Nhan"])            # chưa gắn hồ sơ nào
    F.them_user("hr@x", ["HR User"])
    F.them("Employee", "HR-EMP-1", employee_name="Nguyễn Thị An", status="Active", department="Công khoán - HGC",
           ns_tai_khoan="an@x")
    F.them("Employee", "HR-EMP-2", employee_name="Trần Văn Bình", status="Active", department="Văn phòng - HGC",
           ns_tai_khoan="binh@x")
    F.them("Employee", "HR-EMP-3", employee_name="Lê Khoá", status="Active", department="Văn phòng - HGC",
           ns_tai_khoan="khoa@x")
    k = dict(ten_nhan_vien="Nguyễn Thị An", ngay_cong=20, luong_san_pham=5_000_000, tong_tien=5_400_000,
             tong_khau_tru=0, chi_tiet=[], dong=[], phat=[])
    F.them("SX Phieu Luong", "PL-2026-8-HR-EMP-1", employee="HR-EMP-1", thang=8, nam=2026, docstatus=1,
           luong_thuc_nhan=5_400_000, **k)
    F.them("SX Phieu Luong", "PL-2026-9-HR-EMP-1", employee="HR-EMP-1", thang=9, nam=2026, docstatus=1,
           luong_thuc_nhan=5_900_000, **k)
    F.them("SX Phieu Luong", "PL-2026-10-HR-EMP-1", employee="HR-EMP-1", thang=10, nam=2026, docstatus=0,
           luong_thuc_nhan=6_100_000, **k)                                      # nháp — chưa chốt
    F.them("SX Phieu Luong", "PL-2026-7-HR-EMP-1", employee="HR-EMP-1", thang=7, nam=2026, docstatus=2,
           luong_thuc_nhan=9_999_999, **k)                                      # đã huỷ
    n = dict(congngay=24, luongngaycong=6_000_000, tongtien=6_000_000, tongkhautru=0, chamcong=[], bangghiloiphat=[])
    F.them("SalaryDay", "PLC-0001", employee="HR-EMP-2", month=9, year=2026, docstatus=1, luongthucnhan=6_000_000, **n)
    F.them("SalaryDay", "PLC-0002", employee="HR-EMP-2", month=10, year=2026, docstatus=0, luongthucnhan=6_200_000,
           **n)
    # An đổi sang công nhật giữa tháng 9: có cả phiếu nhật lẫn khoán tháng 9
    F.them("SalaryDay", "PLC-0003", employee="HR-EMP-1", month=9, year=2026, docstatus=1, luongthucnhan=1_000_000,
           **n)


nap_du_lieu()

print("-- ai được xem --")
F.dang_nhap("Guest")
kiem("Guest → PermissionError", "PermissionError" in (loi(lambda: CN.cac_thang()) or ""))
F.dang_nhap("lac@x")
kiem("tài khoản chưa gắn hồ sơ → PermissionError (không đoán hồ sơ theo tên / SĐT)",
     "PermissionError" in (loi(lambda: CN.cac_thang()) or "") and "PermissionError" in (loi(lambda: CN.phieu(9, 2026)) or ""))
F.dang_nhap("khoa@x")
kiem("tài khoản đã khoá mà phiên còn sống → vẫn chặn", "PermissionError" in (loi(lambda: CN.cac_thang()) or ""))
F.dang_nhap("an@x")
kiem("công nhân truyền mã NGƯỜI KHÁC → PermissionError (không lộ lương đồng nghiệp)",
     "PermissionError" in (loi(lambda: CN.phieu(9, 2026, employee="HR-EMP-2")) or "")
     and "PermissionError" in (loi(lambda: CN.cac_thang(employee="HR-EMP-2")) or ""))
kiem("… truyền chính mã mình cũng không được (chỉ HR xem thay)",
     "PermissionError" in (loi(lambda: CN.phieu(9, 2026, employee="HR-EMP-1")) or ""))

print("\n-- công nhân thấy gì --")
t = CN.cac_thang()
kiem("tháng mới nhất trước; chỉ tháng có phiếu ĐÃ DUYỆT (nháp T10 và phiếu huỷ T7 không hiện)",
     [(x["thang"], x["nam"]) for x in t["thang"]] == [(9, 2026), (8, 2026)], str(t["thang"]))
kiem("T9 có cả phiếu nhật + khoán → cộng thực nhận nguyên số hai phiếu, đếm 2 phiếu",
     (t["thang"][0]["thuc_nhan"], t["thang"][0]["so_phieu"]) == (6_900_000, 2), str(t["thang"][0]))
kiem("thông tin người xem đúng hồ sơ gắn tài khoản", (t["employee"], t["employee_name"], t["xem_thay"])
     == ("HR-EMP-1", "Nguyễn Thị An", False))
p = CN.phieu(9, 2026)
kiem("phiếu T9: hai phiếu (nhật + khoán), đều của chính mình", sorted(x["loai"] for x in p["phieu"]) == ["khoan", "nhat"]
     and all(x["employee"] == "HR-EMP-1" for x in p["phieu"]), str([x["name"] for x in p["phieu"]]))
kiem("phiếu nháp T10 KHÔNG xem được kể cả gọi thẳng tháng", CN.phieu(10, 2026)["phieu"] == [])
kiem("phiếu đã huỷ T7 không bao giờ hiện", CN.phieu(7, 2026)["phieu"] == [])
kiem("tháng lạ → chặn", loi(lambda: CN.phieu(13, 2026)) is not None and loi(lambda: CN.phieu(1, 1900)) is not None)
F.dang_nhap("binh@x")
kiem("Bình chỉ thấy phiếu của Bình (T9 nhật), không thấy phiếu của An",
     [x["name"] for x in CN.phieu(9, 2026)["phieu"]] == ["PLC-0001"])

print("\n-- bật cho xem phiếu nháp (tạm tính) --")
F.CONF["ns_cong_nhan_xem_nhap"] = 1
F.dang_nhap("an@x")
t = CN.cac_thang()
kiem("khoán nháp T10 hiện, gắn cờ tạm tính", t["thang"][0]["thang"] == 10 and t["thang"][0]["tam_tinh"]
     and not t["thang"][1]["tam_tinh"], str(t["thang"]))
kiem("… phiếu T10 có docstatus 0 (giao diện ghi 'Tạm tính')", [x["docstatus"] for x in CN.phieu(10, 2026)["phieu"]] == [0])
F.dang_nhap("binh@x")
kiem("SalaryDay nháp VẪN ẩn khi P1 chưa bật (số nháp chỉ đúng sau khi kế toán Save trên Desk)",
     CN.phieu(10, 2026)["phieu"] == [] and [x["thang"] for x in CN.cac_thang()["thang"]] == [9])
F.CONF["ns_tinh_lai_salaryday"] = 1
kiem("… P1 bật → SalaryDay nháp hiện", [x["name"] for x in CN.phieu(10, 2026)["phieu"]] == ["PLC-0002"])
F.CONF.clear()

print("\n-- phòng nhân sự xem như công nhân --")
F.dang_nhap("hr@x")
kiem("HR không truyền mã → tài khoản HR không gắn hồ sơ → chặn", "PermissionError" in (loi(lambda: CN.cac_thang()) or ""))
t = CN.cac_thang(employee="HR-EMP-1")
kiem("HR xem thay → thấy cả tháng chỉ có phiếu TẠM TÍNH (T10 nháp), mới nhất trước, xem_thay=True",
     [x["thang"] for x in t["thang"]] == [10, 9, 8] and t["xem_thay"], str(t))
kiem("… tháng tạm tính đánh dấu tam_tinh + công nhân CHƯA thấy; tháng đã duyệt công nhân thấy",
     (t["thang"][0]["tam_tinh"], t["thang"][0]["cong_nhan_thay"]) == (True, False)
     and all(x["cong_nhan_thay"] and not x["tam_tinh"] for x in t["thang"][1:]), str(t["thang"]))
p10 = CN.phieu(10, 2026, employee="HR-EMP-1")["phieu"]
kiem("… mở phiếu tạm tính T10: docstatus 0, ghi rõ công nhân chưa thấy",
     [(x["name"], x["docstatus"], x["cong_nhan_thay"]) for x in p10] == [("PL-2026-10-HR-EMP-1", 0, False)], str(p10))
kiem("… phiếu đã duyệt: công nhân thấy", all(x["cong_nhan_thay"] for x in CN.phieu(9, 2026, employee="HR-EMP-1")["phieu"]))
kiem("… phiếu ĐÃ HUỶ vẫn không bao giờ hiện, kể cả với HR", CN.phieu(7, 2026, employee="HR-EMP-1")["phieu"] == [])
t = CN.cac_thang(employee="HR-EMP-2")
kiem("… công nhật: SalaryDay nháp T10 cũng hiện với HR (như ở /ns), công nhân chưa thấy",
     [(x["thang"], x["tam_tinh"], x["cong_nhan_thay"]) for x in t["thang"]] == [(10, True, False), (9, False, True)],
     str(t["thang"]))
F.CONF["ns_cong_nhan_xem_nhap"] = 1
kiem("bật cho công nhân xem nháp → phiếu khoán tạm tính ghi 'công nhân thấy'",
     [x["cong_nhan_thay"] for x in CN.phieu(10, 2026, employee="HR-EMP-1")["phieu"]] == [True])
kiem("… SalaryDay nháp vẫn 'công nhân chưa thấy' khi P1 chưa bật",
     [x["cong_nhan_thay"] for x in CN.phieu(10, 2026, employee="HR-EMP-2")["phieu"]] == [False])
F.CONF.clear()
F.dang_nhap("an@x")
kiem("công nhân tự xem KHÔNG đổi: vẫn không thấy tháng tạm tính T10",
     [x["thang"] for x in CN.cac_thang()["thang"]] == [9, 8] and CN.phieu(10, 2026)["phieu"] == [])
F.dang_nhap("hr@x")
kiem("HR truyền mã không có → DoesNotExistError", "DoesNotExist" in (loi(lambda: CN.phieu(9, 2026, employee="X")) or ""))

print("\n-- site chưa migrate field ns_tai_khoan --")
F.META_FIELDS["Employee"] = {"employee_name", "department", "status"}
F.dang_nhap("an@x")
kiem("chưa có field → coi như chưa gắn, chặn (không nổ Unknown column)",
     "PermissionError" in (loi(lambda: CN.cac_thang()) or ""))
del F.META_FIELDS["Employee"]

print("\n-- trang /phieuluong --")


def trang(user, nv=None, the=None):
    F.dang_nhap(user)
    F.sys.modules["frappe"].form_dict = F.Doc({k: v for k, v in (("nv", nv), ("the", the)) if v})
    F.sys.modules["frappe"].local.flags.redirect_location = None
    ctx = F.Doc()
    try:
        W.get_context(ctx)
    except F.Redirect:
        return None, F.sys.modules["frappe"].local.flags.redirect_location
    return ctx, None


ctx, di = trang("Guest")
kiem("Guest → chuyển tới đăng nhập, quay lại đúng /phieuluong", ctx is None and di == "/login?redirect-to=%2Fphieuluong", di)
ctx, di = trang("Guest", the="HR-EMP-1")
kiem("Guest quét thẻ → đăng nhập xong quay lại ĐÚNG thẻ (?the= giữ nguyên)",
     ctx is None and di == "/login?redirect-to=%2Fphieuluong%3Fthe%3DHR-EMP-1", di)
ctx, _di = trang("an@x")
kiem("công nhân: context mang đúng hồ sơ của mình", ctx.cn_context["employee"] == "HR-EMP-1" and ctx.co_nhan_vien
     and not ctx.cn_context["xemThay"])
ctx, _di = trang("an@x", nv="HR-EMP-2")
kiem("công nhân thêm ?nv=<người khác> → bỏ qua, vẫn là hồ sơ của mình", ctx.cn_context["employee"] == "HR-EMP-1"
     and not ctx.cn_context["xemThay"])
ctx, _di = trang("lac@x")
kiem("tài khoản chưa gắn → trang báo, không có hồ sơ", not ctx.co_nhan_vien and ctx.cn_context["employee"] is None)
ctx, _di = trang("hr@x", nv="HR-EMP-2")
kiem("HR ?nv= → xem như công nhân", ctx.cn_context["employee"] == "HR-EMP-2" and ctx.cn_context["xemThay"])
ctx, _di = trang("hr@x", nv="KHONG-CO")
kiem("HR ?nv= mã không có → không vỡ, coi như không xem thay", not ctx.co_nhan_vien)

print("\n-- quét thẻ (?the=) khi máy đang đăng nhập sẵn --")
ctx, _di = trang("an@x", the="HR-EMP-1")
kiem("chủ thẻ quét thẻ của mình → xem phiếu của mình", ctx.co_nhan_vien and ctx.cn_context["employee"] == "HR-EMP-1"
     and not ctx.the_khac and not ctx.cn_context["xemThay"])
ctx, _di = trang("an@x", the="HR-EMP-2")
kiem("công nhân quét thẻ của NGƯỜI KHÁC → báo 'thẻ không phải của tài khoản đang đăng nhập', không tải phiếu nào",
     ctx.the_khac and not ctx.co_nhan_vien and ctx.cn_context["employee"] is None)
kiem("… không lộ tên / bộ phận chủ thẻ (mã trên địa chỉ ai cũng gõ được)",
     "Trần Văn Bình" not in str(ctx) and ctx.cn_context["employeeName"] is None and ctx.co_ho_so_rieng)
kiem("… ghi rõ tài khoản đang đăng nhập", ctx.ten_tk == "an@x" or ctx.ten_tk == F.DB["User"]["an@x"]["full_name"])
ctx, _di = trang("lac@x", the="HR-EMP-1")
kiem("tài khoản chưa gắn hồ sơ quét thẻ → cũng báo thẻ người khác, không có lối 'phiếu của tôi'",
     ctx.the_khac and not ctx.co_nhan_vien and not ctx.co_ho_so_rieng)
ctx, _di = trang("hr@x", the="HR-EMP-2")
kiem("phòng nhân sự quét thẻ → xem như công nhân ĐÚNG chủ thẻ, đánh dấu 'từ thẻ' (hiện nút đăng xuất để thử thẻ)",
     ctx.co_nhan_vien and ctx.cn_context["employee"] == "HR-EMP-2" and ctx.cn_context["xemThay"]
     and ctx.cn_context["tuThe"] and not ctx.the_khac)
ctx, _di = trang("hr@x", nv="HR-EMP-2")
kiem("… nút 👁 (?nv=) vẫn là xem thay, không phải 'từ thẻ'", ctx.cn_context["xemThay"] and not ctx.cn_context["tuThe"])
ctx, _di = trang("hr@x")
kiem("phòng nhân sự mở trang trơn (QR thẻ in trước đây) → màn báo tài khoản phòng nhân sự, không phải lỗi",
     not ctx.co_nhan_vien and not ctx.the_khac and ctx.la_hr)
src = open(os.path.join(F.GOC, "ns", "www", "phieuluong.py"), encoding="utf-8").read()
js = open(os.path.join(F.GOC, "ns", "public", "ns", "cong_nhan.js"), encoding="utf-8").read()
import re  # noqa: E402
b1 = re.search(r'SHELL_BUILD = "([^"]+)"', src).group(1)
b2 = re.search(r"const BUILD = '([^']+)'", js).group(1)
kiem("BUILD của trang khớp cong_nhan.js (Luật vàng #2)", b1 == b2, f"{b1} ≠ {b2}")
for m in sorted(set(re.findall(r"ns\.api\.cong_nhan\.(\w+)", js))):
    kiem(f"trang gọi method có thật: {m}", callable(getattr(CN, m, None)))

print("CONGNHAN-OK" if not hong else f"CONGNHAN: {hong} HỎNG")
sys.exit(1 if hong else 0)
