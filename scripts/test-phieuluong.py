"""Phiếu lương dựng chung (ns/api/phieu_luong.py) — port thẻ Phiếu lương app sx (D110 + D234) sang ns.

Là TIỀN LƯƠNG: sai thì sai kiểu người ta tin và đọc to cho công nhân. Canh:
  · khoán: gộp sản phẩm theo mã + cách làm + đơn giá (tháng và từng ngày, không cộng hai lần), làm theo giờ mỗi mức
    một dòng, thứ tự trong ngày, dòng chưa có giá, ngày chỉ chấm ăn, số lấy NGUYÊN từ phiếu (cùng ca với
    sx/scripts/test-luong.py — hai app phải ra một kết quả);
  · nhật: các khoản cộng ĐỦ thành phần của tongtien (Client Script), bảng chấm công xếp theo ngày + thứ, lý do phạt
    đọc mềm, phần chuyển khoản;
  · quyền: chỉ HR xem qua `xem`; tab Công & lương trả view model cho cả hai loại.
Chạy: python3 scripts/test-phieuluong.py
"""
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fakefrappe as F  # noqa: E402

F.cai()
M = F.nap_ns()
PL = M["phieu_luong"]
CL = M["cong_luong"]

hong = 0


def kiem(ten, dk, ct=""):
    global hong
    if not dk:
        hong += 1
    print(f"  {'ok  ' if dk else 'HỎNG'} {ten}{(' — ' + ct) if ct and not dk else ''}")


def thu(fn):
    try:
        return fn(), None
    except F.Loi as e:
        return None, f"{type(e).__name__}: {e}"


def nap_du_lieu():
    F.don_dep()
    F.them_user("hr@x", ["HR User"])
    F.them_user("cn@x", ["NS Cong Nhan"])
    F.them("Employee", "HR-EMP-1", employee_name="Nguyễn Thị An", status="Active", department="Công khoán - HGC")
    F.them("Employee", "HR-EMP-2", employee_name="Trần Văn Bình", status="Active", department="Văn phòng - HGC")
    D = date
    # Phiếu khoán CỐ Ý lộn xộn như sau khi sửa tay trên Desk / chốt lại ngày cũ (cùng dữ liệu PL-4 của sx test-luong)
    F.them("SX Phieu Luong", "PL-2026-8-HR-EMP-1", employee="HR-EMP-1", ten_nhan_vien="Nguyễn Thị An", thang=8,
           nam=2026, docstatus=0, trang_thai="Nháp", ngay_cong=2.5, ngay_san_xuat=0, luong_san_pham=214_500,
           tien_an=50_000, chuyen_can=0, ho_tro_ngay_cong=0, thuong_tham_nien=10_725, ho_tro=0, tien_phat=20_000,
           bao_hiem=0, tong_tien=275_225, tong_khau_tru=20_000, luong_thuc_nhan=255_225, ghi_chu="",
           chi_tiet=[
               dict(ngay=D(2026, 8, 3), theo_gio=1, so_gio=2, san_pham=None, ten_san_pham="Làm theo giờ", cach_lam=None,
                    so_luong=0, don_gia=30_000, thanh_tien=60_000),
               dict(ngay=D(2026, 8, 3), san_pham="TP-SEN", ten_san_pham="Bánh sen", cach_lam="Máy", so_luong=40,
                    don_gia=900, thanh_tien=36_000),
               dict(ngay=D(2026, 8, 4), san_pham="TP-TT", ten_san_pham="Bánh TT", cach_lam="Tay", so_luong=30,
                    don_gia=0, thanh_tien=0),
               dict(ngay=D(2026, 8, 4), san_pham="TP-TT", ten_san_pham="Bánh TT", cach_lam="Máy", so_luong=12,
                    don_gia=0, thanh_tien=0),
               dict(ngay=D(2026, 8, 3), theo_gio=1, so_gio=1.5, san_pham=None, ten_san_pham="Làm theo giờ",
                    cach_lam=None, so_luong=0, don_gia=33_000, thanh_tien=49_500),
               dict(ngay=D(2026, 8, 3), san_pham="TP-TT", ten_san_pham="Bánh TT", cach_lam="Tay", so_luong=30,
                    don_gia=2_000, thanh_tien=60_000),
               dict(ngay=D(2026, 8, 3), san_pham="TP-SEN", ten_san_pham="Bánh sen", cach_lam="Máy", so_luong=10,
                    don_gia=900, thanh_tien=9_000)],
           dong=[
               dict(ngay=D(2026, 8, 4), thu="Thứ 3", an_ca=0, an_dem=0, tien_an=0, luong_sp=0, he_so=1,
                    thu_nhap_ngay=0),
               dict(ngay=D(2026, 8, 2), thu="Chủ nhật", an_ca=1, an_dem=1, tien_an=30_000, luong_sp=0, he_so=1.2,
                    thu_nhap_ngay=30_000),
               dict(ngay=D(2026, 8, 3), thu="Thứ 2", an_ca=1, an_dem=0, tien_an=20_000, luong_sp=214_500, he_so=1,
                    thu_nhap_ngay=234_500)],
           phat=[dict(ly_do="Hộp móp", so_luong=2, gia_tien=10_000, thanh_tien=20_000)])
    # SalaryDay: số khớp đúng công thức tongtien của Client Script (ns/salaryday.py)
    F.them("SalaryDay", "PLC-0001", employee="HR-EMP-2", month=10, year=2026, docstatus=1, status="Đã thanh toán",
           ngaysanxuat=26, congngay=24, lamthem=1.5, luongcoban=6_500_000, luongngaycong=6_000_000,
           luonglamthem=450_000, anca=480_000, chuyencan=200_000, hotrongaycong=0, hotro=300_000, thuongkhac=100_000,
           thuongthamnien=0, tongtien=7_530_000, baohiem=550_000, tienphat=30_000, tongkhautru=580_000,
           luongthucnhan=6_950_000, luongck=5_000_000, ghichu="Tăng ca kiểm kê",
           chamcong=[dict(ngaycc=D(2026, 10, 4), congngay=1, themgio=0),       # Chủ nhật
                     dict(ngaycc=D(2026, 10, 1), congngay=1, themgio=2.5),
                     dict(ngaycc=D(2026, 10, 2), congngay=0.5, themgio=0),
                     dict(ngaycc=D(2026, 10, 3), congngay=0, themgio=0)],
           bangghiloiphat=[dict(noidung="Đi muộn", soluong=3, giatien=10_000, thanhtienphat=30_000)])


nap_du_lieu()
F.dang_nhap("hr@x")

print("-- công khoán: từng ngày làm những gì, đơn giá, thành tiền (D234) --")
p = PL.xem_khoan(F.get_doc("SX Phieu Luong", "PL-2026-8-HR-EMP-1"))
ng = {x["ngay"]: x for x in p["ngay"]}
dong_sp = lambda d: [(x["ten"], x["cach_lam"], x["so_luong"], x["don_gia"], x["thanh_tien"], bool(x.get("theo_gio")))
                     for x in ng[d]["sp"]]
kiem("ngày 03/08: sản phẩm của ĐÚNG ngày đó; cùng mã + cách làm + đơn giá gộp một dòng (40 + 10); sản phẩm giữ thứ "
     "tự ghi, làm theo giờ sau (giá cao trước) dù dòng giờ 30.000 ghi đầu tiên",
     dong_sp("2026-08-03") == [("Bánh sen", "Máy", 50, 900.0, 45_000.0, False),
                               ("Bánh TT", "Tay", 30, 2_000.0, 60_000.0, False),
                               ("Làm theo giờ", "", 1.5, 33_000.0, 49_500.0, True),
                               ("Làm theo giờ", "", 2.0, 30_000.0, 60_000.0, True)], str(dong_sp("2026-08-03")))
kiem("… cộng thành tiền các dòng của ngày = lương SP ngày trên phiếu (214.500)",
     sum(x["thanh_tien"] for x in ng["2026-08-03"]["sp"]) == ng["2026-08-03"]["luong_sp"] == 214_500)
kiem("… tiền ăn + thu nhập ngày lấy NGUYÊN từ phiếu", (ng["2026-08-03"]["tien_an"], ng["2026-08-03"]["thu_nhap"])
     == (20_000, 234_500), str(ng["2026-08-03"]))
kiem("… số giờ của ngày cộng mọi mức (2 + 1,5)", ng["2026-08-03"]["so_gio"] == 3.5, str(ng["2026-08-03"]["so_gio"]))
kiem("ngày 04/08: dòng chưa có giá vẫn hiện (0 đồng); cùng mã cùng giá khác cách làm là HAI dòng",
     dong_sp("2026-08-04") == [("Bánh TT", "Tay", 30, 0.0, 0.0, False), ("Bánh TT", "Máy", 12, 0.0, 0.0, False)],
     str(dong_sp("2026-08-04")))
kiem("ngày 02/08 chỉ chấm ăn: không dòng sản phẩm, thu nhập = tiền ăn, hệ số Chủ nhật giữ nguyên",
     ng["2026-08-02"]["sp"] == [] and ng["2026-08-02"]["thu_nhap"] == 30_000 and ng["2026-08-02"]["he_so"] == 1.2)
kiem("ngày xếp theo thứ tự ngày dù dòng ngày trên phiếu lộn xộn", list(ng) == ["2026-08-02", "2026-08-03",
                                                                             "2026-08-04"], str(list(ng)))
sen = [x for x in p["san_pham"] if x["ten"] == "Bánh sen"]
kiem("sản phẩm trong tháng KHÔNG bị cộng hai lần khi tách thêm theo ngày (sen 50, không 100)",
     [(x["so_luong"], x["thanh_tien"]) for x in sen] == [(50, 45_000.0)], str(sen))
kiem("… tổng thành tiền cả tháng = tổng các ngày = lương SP",
     sum(x["thanh_tien"] for x in p["san_pham"]) == sum(x["thanh_tien"] for d in p["ngay"] for x in d["sp"])
     == p["cong"][0]["tien"] == 214_500)
kiem("… sản phẩm trong tháng xếp theo thành tiền giảm dần",
     [x["thanh_tien"] for x in p["san_pham"]] == sorted([x["thanh_tien"] for x in p["san_pham"]], reverse=True))
gio = sorted((x["so_luong"], x["don_gia"]) for x in p["san_pham"] if x["theo_gio"])
kiem("làm theo giờ: mỗi mức một dòng, số lượng là số GIỜ (D225/D233)", gio == [(1.5, 33_000), (2.0, 30_000)], str(gio))
kiem("đếm dòng chưa có giá (Bánh TT Tay + Máy = 2)", p["chua_gia"] == 2, str(p["chua_gia"]))
kiem("chỉ hiện khoản khác 0, đúng thứ tự phiếu giấy", [x["ten"] for x in p["cong"]]
     == ["Lương sản phẩm", "Tiền ăn ca + ăn đêm", "Thưởng thâm niên"], str(p["cong"]))
kiem("khấu trừ tách riêng, thực nhận = số trên phiếu", p["tru"] == [{"ten": "Tiền phạt", "tien": 20_000}]
     and p["thuc_nhan"] == 255_225 and p["tong_tien"] == 275_225, str(p["tru"]))
kiem("Σ khoản cộng = tổng thu nhập trên phiếu (không sót thành phần nào)",
     sum(x["tien"] for x in p["cong"]) == p["tong_tien"])
kiem("lỗi phạt đọc đúng ô ly_do của SX Phieu Luong Phat (bản cũ đọc nhầm noi_dung → rỗng)",
     p["phat"] == [{"ly_do": "Hộp móp", "so_luong": 2.0, "gia_tien": 10_000.0, "tien": 20_000.0}], str(p["phat"]))
kiem("thông tin đầu phiếu", (p["loai"], p["thang"], p["nam"], p["da_duyet"], p["ten"], p["ngay_cong"])
     == ("khoan", 8, 2026, False, "Nguyễn Thị An", 2.5), str({k: p[k] for k in ("loai", "thang", "nam", "ten")}))

print("\n-- công nhật (SalaryDay) --")
n = PL.xem_nhat(F.get_doc("SalaryDay", "PLC-0001"))
kiem("các khoản theo thứ tự, bỏ khoản 0 (hỗ trợ ngày công, thâm niên)", [x["ten"] for x in n["cong"]] == [
    "Lương ngày công", "Lương làm thêm", "Tiền ăn ca", "Chuyên cần", "Hỗ trợ", "Thưởng khác"], str(n["cong"]))
kiem("Σ khoản cộng = tongtien của phiếu (đủ 8 thành phần như Client Script)",
     sum(x["tien"] for x in n["cong"]) == n["tong_tien"] == 7_530_000)
kiem("khấu trừ: tiền phạt + bảo hiểm; thực nhận nguyên số phiếu", n["tru"] == [
    {"ten": "Tiền phạt", "tien": 30_000}, {"ten": "Bảo hiểm", "tien": 550_000}] and n["thuc_nhan"] == 6_950_000)
kiem("phần chuyển khoản, lương cơ bản, ngày công / làm thêm lấy từ phiếu",
     (n["chuyen_khoan"], n["luong_co_ban"], n["ngay_cong"], n["ngay_san_xuat"], n["lam_them"])
     == (5_000_000, 6_500_000, 24, 26, 1.5))
kiem("bảng chấm công xếp theo ngày, kèm thứ (04/10/2026 là Chủ nhật)",
     [(x["ngay"], x["thu"], x["cong"], x["them_gio"]) for x in n["ngay"]] == [
         ("2026-10-01", "Thứ 5", 1.0, 2.5), ("2026-10-02", "Thứ 6", 0.5, 0.0), ("2026-10-03", "Thứ 7", 0.0, 0.0),
         ("2026-10-04", "Chủ nhật", 1.0, 0.0)], str(n["ngay"]))
kiem("lý do phạt đọc mềm (ô noidung)", n["phat"] == [{"ly_do": "Đi muộn", "so_luong": 3.0, "gia_tien": 10_000.0,
                                                      "tien": 30_000.0}], str(n["phat"]))
kiem("tên nhân viên tra từ Employee khi phiếu không có ô tên", n["ten"] == "Trần Văn Bình", n["ten"])
kiem("trạng thái của phiếu (status) + đã duyệt", n["trang_thai"] == "Đã thanh toán" and n["da_duyet"])
kiem("ghi chú", n["ghi_chu"] == "Tăng ca kiểm kê")
# Ô lý do tên lạ → lấy ô chữ đầu tiên của bảng con theo meta
F.META_CHI_TIET["SalaryDay"] = [("bangghiloiphat", "Table", "SalaryDay Phat")]
F.META_CHI_TIET["SalaryDay Phat"] = [("soluong", "Float", None), ("motaloi", "Data", None), ("giatien", "Currency", None)]
F.bang("SalaryDay")["PLC-0001"]["bangghiloiphat"] = [dict(motaloi="Làm vỡ cốc", soluong=1, giatien=5_000,
                                                          thanhtienphat=5_000)]
n2 = PL.xem_nhat(F.get_doc("SalaryDay", "PLC-0001"))
kiem("ô lý do tên lạ → ô chữ đầu tiên của bảng con (theo meta)", n2["phat"][0]["ly_do"] == "Làm vỡ cốc", str(n2["phat"]))
F.bang("SalaryDay")["PLC-0001"]["bangghiloiphat"] = [dict(soluong=1, giatien=5_000, thanhtienphat=5_000)]
kiem("không có ô chữ nào → lý do rỗng, không lỗi", PL.xem_nhat(F.get_doc("SalaryDay", "PLC-0001"))["phat"][0]["ly_do"] == "")
F.bang("SalaryDay")["PLC-0001"]["chamcong"].append(dict(ngaycc=None, congngay=1, themgio=0))
kiem("dòng chấm công thiếu ngày không làm vỡ cả phiếu", len(PL.xem_nhat(F.get_doc("SalaryDay", "PLC-0001"))["ngay"]) == 5)

print("\n-- API: quyền + tab Công & lương --")
nap_du_lieu()
F.dang_nhap("cn@x")
kiem("công nhân KHÔNG gọi được xem (API của phòng nhân sự)",
     "PermissionError" in (thu(lambda: PL.xem("SalaryDay", "PLC-0001"))[1] or ""))
kiem("… cũng không gọi được Công & lương", "PermissionError" in (thu(lambda: CL.thang("HR-EMP-2", 10, 2026))[1] or ""))
F.dang_nhap("Guest")
kiem("Guest bị chặn", "PermissionError" in (thu(lambda: PL.xem("SalaryDay", "PLC-0001"))[1] or ""))
F.dang_nhap("hr@x")
kiem("HR xem được phiếu", PL.xem("SX Phieu Luong", "PL-2026-8-HR-EMP-1")["thuc_nhan"] == 255_225)
kiem("DocType lạ (không phải phiếu lương) → chặn, không mở doc tuỳ ý",
     thu(lambda: PL.xem("User", "hr@x"))[1] is not None and thu(lambda: PL.xem("Employee", "HR-EMP-1"))[1] is not None)
kiem("phiếu không có → DoesNotExistError", "DoesNotExist" in (thu(lambda: PL.xem("SalaryDay", "X"))[1] or ""))
del F.DB["SX Phieu Luong"]
kiem("site không có app sx (không có bảng SX Phieu Luong) → báo rõ, không vỡ",
     "chưa có bảng" in (thu(lambda: PL.xem("SX Phieu Luong", "PL-1"))[1] or ""))
nap_du_lieu()
F.dang_nhap("hr@x")
c = CL.thang("HR-EMP-2", 10, 2026)
kiem("Công & lương: mỗi phiếu kèm view model `xem` + link In / Desk",
     len(c["phieu"]) == 1 and c["phieu"][0]["xem"]["thuc_nhan"] == 6_950_000
     and c["phieu"][0]["in_url"].startswith("/printview?doctype=SalaryDay&name=PLC-0001&format=")
     and c["phieu"][0]["desk_url"] == "/app/salaryday/PLC-0001", str(c["phieu"][0].get("in_url")))
c = CL.thang("HR-EMP-1", 8, 2026)
kiem("… phiếu khoán: không có nút In, Desk trỏ sx-phieu-luong", c["phieu"][0]["in_url"] is None
     and c["phieu"][0]["desk_url"] == "/app/sx-phieu-luong/PL-2026-8-HR-EMP-1" and c["phieu"][0]["xem"]["loai"] == "khoan")
kiem("tháng không có phiếu → danh sách rỗng", CL.thang("HR-EMP-1", 9, 2026)["phieu"] == [])

print("PHIEULUONG-OK" if not hong else f"PHIEULUONG: {hong} HỎNG")
sys.exit(1 if hong else 0)
