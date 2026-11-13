"""Tài khoản xem lương (ns/api/tai_khoan.py + ns/setup/install.py) — màn cấp quyền ĐĂNG NHẬP, canh leo thang quyền.

  · chỉ HR Manager tạo / cấp lại / khoá / gỡ; HR User chỉ xem;
  · tài khoản mới: username = mobile_no = SĐT chuẩn hoá, role NS Cong Nhan (Website User — không vào Desk), gắn qua
    Employee.ns_tai_khoan, KHÔNG đụng Employee.user_id (ERPNext sẽ cấp role Employee có quyền ghi SalaryDay);
  · SĐT đã có tài khoản → KHÔNG tự gắn, phải xác nhận; tài khoản Desk không bị thêm role (home_page kéo sang /phieuluong);
  · cấp lại mật khẩu / khoá chỉ với tài khoản RIÊNG của app — không bao giờ với tài khoản dùng chung / Administrator;
  · một tài khoản chỉ gắn một hồ sơ; gỡ thì hết xem ngay; khoá / cấp lại thì đăng xuất mọi máy;
  · role tạo khi thiếu (Website, home_page phieuluong), không sửa role đã có.
Chạy: python3 scripts/test-taikhoan.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fakefrappe as F  # noqa: E402

F.cai()
M = F.nap_ns()
TK = M["tai_khoan"]
CN = M["cong_nhan"]
INS = M["install"]

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
    F.them("Role", "System Manager", role_name="System Manager", desk_access=1)
    F.them("Role", "SX Vao Hop", role_name="SX Vao Hop", desk_access=0)
    F.them_user("Administrator", ["System Manager"], mobile_no="0900000009")
    F.them_user("ql@x", ["HR Manager"])
    F.them_user("hr@x", ["HR User"])
    F.them_user("0911111111@sx.local", ["SX Vao Hop"], username="0911111111", mobile_no="0911111111",
                full_name="Phạm QC")                                         # QC có tài khoản app sx
    F.them_user("vp@cty.vn", ["HR User"], mobile_no="0922222222", full_name="Văn Phòng")   # có Desk
    F.them("Employee", "HR-EMP-1", employee_name="Nguyễn Thị An", status="Active", department="Công khoán - HGC",
           cell_number="+84 912 345 678", user_id=None)
    F.them("Employee", "HR-EMP-2", employee_name="Phạm QC", status="Active", department="Công khoán - HGC",
           cell_number="0911.111.111")
    F.them("Employee", "HR-EMP-3", employee_name="Văn Phòng", status="Active", department="Văn phòng - HGC",
           cell_number="0922222222")
    F.them("Employee", "HR-EMP-4", employee_name="Không Số", status="Active", department="Văn phòng - HGC",
           cell_number=None)
    F.them("Employee", "HR-EMP-5", employee_name="Đã Nghỉ", status="Left", department="Văn phòng - HGC",
           cell_number="0933333333")
    F.them("Employee", "HR-EMP-6", employee_name="Số Admin", status="Active", department="Văn phòng - HGC",
           cell_number="0900000009")
    F.META_FIELDS["SX Settings"] = {"ten_mien_user"}
    F.DB.setdefault("Singles", {})["SX Settings"] = {"ten_mien_user": ""}


nap_du_lieu()

print("-- tiện ích --")
kiem("chuẩn hoá SĐT: +84 / 84 / dấu chấm / khoảng trắng → 0xxxxxxxxx",
     [TK.chuan_sdt(x) for x in ("+84 912 345 678", "84912345678", "0912.345.678", "0912345678")] == ["0912345678"] * 4)
kiem("SĐT sai → chặn; trống → báo 'chưa có số điện thoại'",
     loi(lambda: TK.chuan_sdt("12345")) is not None and "chưa có số điện thoại" in (loi(lambda: TK.chuan_sdt(None)) or ""))
mk = [TK.mat_khau_moi() for _i in range(500)]
kiem("mật khẩu 8 ký tự, đủ hoa / thường / số, không ký tự dễ nhầm (0 O o 1 l I i)",
     all(len(m) == 8 and any(c.isupper() for c in m) and any(c.islower() for c in m) and any(c.isdigit() for c in m)
         and not set(m) & set("0Oo1lIi") for m in mk))
kiem("mật khẩu ngẫu nhiên (500 lần không trùng)", len(set(mk)) == 500)
kiem("tên miền email giả: SX Settings trống → sx.local (trùng cách app sx — một SĐT một tài khoản)",
     TK._ten_mien() == "sx.local")
F.CONF["ns_ten_mien_user"] = "@rvhg.local"
kiem("… site_config ns_ten_mien_user thắng", TK._ten_mien() == "rvhg.local")
F.CONF.clear()
del F.META_FIELDS["SX Settings"]
kiem("… không có app sx → ns.local", TK._ten_mien() == "ns.local")
F.META_FIELDS["SX Settings"] = {"ten_mien_user"}

print("\n-- role --")
kiem("role NS Cong Nhan chưa có → dam_bao_role tạo (không vào Desk, trang chủ phieuluong)",
     INS.dam_bao_role() == ["NS Cong Nhan"] and F.DB["Role"]["NS Cong Nhan"]["desk_access"] == 0
     and F.DB["Role"]["NS Cong Nhan"]["home_page"] == "phieuluong")
F.DB["Role"]["NS Cong Nhan"]["home_page"] = "me"                  # quản trị đổi trên Desk
kiem("role đã có → KHÔNG sửa (giữ chỉnh tay của quản trị qua các lần migrate)",
     INS.dam_bao_role() == [] and F.DB["Role"]["NS Cong Nhan"]["home_page"] == "me")
del F.DB["Role"]["NS Cong Nhan"]

print("\n-- quyền --")
F.dang_nhap("hr@x")
kiem("HR User xem được danh sách", TK.danh_sach()["tong_hop"]["so_nv"] == 5)
kiem("HR User KHÔNG tạo / cấp lại / khoá / gỡ được", all("PermissionError" in (loi(f) or "") for f in (
    lambda: TK.tao("HR-EMP-1"), lambda: TK.cap_lai("HR-EMP-1"), lambda: TK.khoa("HR-EMP-1"), lambda: TK.go("HR-EMP-1"))))
F.dang_nhap("0911111111@sx.local")
kiem("công nhân / QC không xem nổi danh sách tài khoản", "PermissionError" in (loi(lambda: TK.danh_sach()) or ""))

print("\n-- tạo tài khoản mới --")
F.dang_nhap("ql@x")
r = TK.tao("HR-EMP-1")
u = F.DB["User"].get("0912345678@sx.local") or {}
kiem("tạo tài khoản từ SĐT trên hồ sơ (chuẩn hoá), username = mobile_no = SĐT",
     r["user"] == "0912345678@sx.local" and u.get("username") == "0912345678" and u.get("mobile_no") == "0912345678",
     str(r))
kiem("role NS Cong Nhan (role được tạo luôn khi thiếu) → Website User, không vào Desk",
     [x["role"] for x in u["roles"]] == ["NS Cong Nhan"] and u["user_type"] == "Website User"
     and "NS Cong Nhan" in F.DB["Role"])
kiem("mật khẩu trả về một lần = mật khẩu đặt cho tài khoản; không gửi email chào",
     r["mat_khau"] and u.get("_mat_khau") == r["mat_khau"] and not u.get("send_welcome_email"))
kiem("gắn qua Employee.ns_tai_khoan, KHÔNG đụng user_id (tránh role Employee của ERPNext)",
     F.DB["Employee"]["HR-EMP-1"]["ns_tai_khoan"] == r["user"] and not F.DB["Employee"]["HR-EMP-1"].get("user_id"))
kiem("thẻ: tên, mã NV, SĐT, đường dẫn /phieuluong", (r["ten"], r["employee"], r["sdt"], r["url"])
     == ("Nguyễn Thị An", "HR-EMP-1", "0912345678", "https://a.example.vn/phieuluong"), str(r))
kiem("… QR mang mã chủ thẻ (?the=) để trang biết thẻ của ai khi máy đang đăng nhập tài khoản khác",
     r["url_qr"] == "https://a.example.vn/phieuluong?the=HR-EMP-1", r.get("url_qr"))
F.dang_nhap("0912345678@sx.local")
kiem("… đăng nhập tài khoản mới là thấy đúng hồ sơ của mình", CN.cac_thang()["employee"] == "HR-EMP-1")
F.dang_nhap("ql@x")
kiem("tạo lần nữa cho cùng hồ sơ → chặn (muốn đổi thì Gỡ trước)", "đã có tài khoản" in (loi(lambda: TK.tao("HR-EMP-1")) or ""))
F.DB["Employee"]["HR-EMP-4"]["cell_number"] = "0912345678"
kiem("hồ sơ khác cùng SĐT → tài khoản đang gắn người khác → chặn, nêu tên",
     "Nguyễn Thị An" in (loi(lambda: TK.tao("HR-EMP-4")) or ""))
F.DB["Employee"]["HR-EMP-4"]["cell_number"] = None
kiem("hồ sơ chưa có SĐT, không nhập → báo nhập số", "chưa có số điện thoại" in (loi(lambda: TK.tao("HR-EMP-4")) or ""))
r4 = TK.tao("HR-EMP-4", sdt="0944 444 444")
kiem("… nhập SĐT trong hộp thoại → tạo bằng số đó", r4["sdt"] == "0944444444" and r4["mat_khau"])

print("\n-- SĐT đã có tài khoản: phải xác nhận --")
r = TK.tao("HR-EMP-2")
kiem("QC có tài khoản app sx → CHƯA gắn, hỏi xác nhận kèm tên chủ tài khoản",
     r.get("can_xac_nhan") and r["ten_tai_khoan"] == "Phạm QC" and r["dung_chung"]
     and not F.DB["Employee"]["HR-EMP-2"].get("ns_tai_khoan"), str(r))
mk_cu = F.DB["User"]["0911111111@sx.local"].get("_mat_khau")
r = TK.tao("HR-EMP-2", xac_nhan=1)
u = F.DB["User"]["0911111111@sx.local"]
kiem("xác nhận → gắn; KHÔNG đổi mật khẩu (QC vẫn dùng mật khẩu sx)", r["lien_ket"] and r["mat_khau"] is None
     and u.get("_mat_khau") == mk_cu and F.DB["Employee"]["HR-EMP-2"]["ns_tai_khoan"] == "0911111111@sx.local")
kiem("… Website User được thêm role NS Cong Nhan (vào thẳng /phieuluong), giữ role sx",
     sorted(x["role"] for x in u["roles"]) == ["NS Cong Nhan", "SX Vao Hop"] and u["user_type"] == "Website User")
r = TK.tao("HR-EMP-3", xac_nhan=1)
u = F.DB["User"]["vp@cty.vn"]
kiem("tài khoản có Desk (theo mobile_no) → gắn nhưng KHÔNG thêm role (role có home_page kéo người Desk sang /phieuluong)",
     r["lien_ket"] and [x["role"] for x in u["roles"]] == ["HR User"], str(u["roles"]))
kiem("SĐT trùng Administrator → không gắn tài khoản hệ thống",
     "hệ thống" in (loi(lambda: TK.tao("HR-EMP-6", xac_nhan=1)) or ""))

print("\n-- cấp lại / khoá / gỡ --")
F.PHIEN["0912345678@sx.local"] = 2
cu = F.DB["User"]["0912345678@sx.local"]["_mat_khau"]
r = TK.cap_lai("HR-EMP-1")
kiem("cấp lại: mật khẩu MỚI + đăng xuất mọi máy", r["mat_khau"] and r["mat_khau"] != cu
     and F.DB["User"]["0912345678@sx.local"]["_mat_khau"] == r["mat_khau"] and F.PHIEN["0912345678@sx.local"] == 0)
kiem("cấp lại / khoá tài khoản DÙNG CHUNG (QC sx, Desk) → chặn, mật khẩu không đổi",
     "dùng chung" in (loi(lambda: TK.cap_lai("HR-EMP-2")) or "") and "dùng chung" in (loi(lambda: TK.khoa("HR-EMP-3")) or "")
     and F.DB["User"]["0911111111@sx.local"].get("_mat_khau") == mk_cu and F.DB["User"]["vp@cty.vn"]["enabled"] == 1)
F.PHIEN["0912345678@sx.local"] = 1
TK.khoa("HR-EMP-1", 1)
kiem("khoá: tài khoản tắt + đăng xuất phiên đang mở", F.DB["User"]["0912345678@sx.local"]["enabled"] == 0
     and F.PHIEN["0912345678@sx.local"] == 0)
F.dang_nhap("0912345678@sx.local")
kiem("… phiên còn sót của tài khoản đã khoá cũng không đọc được lương", "PermissionError" in (loi(lambda: CN.cac_thang()) or ""))
F.dang_nhap("ql@x")
TK.khoa("HR-EMP-1", 0)
kiem("mở khoá", F.DB["User"]["0912345678@sx.local"]["enabled"] == 1)
TK.go("HR-EMP-2")
u = F.DB["User"]["0911111111@sx.local"]
kiem("gỡ tài khoản dùng chung: bỏ liên kết + bỏ role NS, tài khoản sx vẫn dùng bình thường",
     not F.DB["Employee"]["HR-EMP-2"].get("ns_tai_khoan") and [x["role"] for x in u["roles"]] == ["SX Vao Hop"]
     and u["enabled"] == 1)
F.dang_nhap("0911111111@sx.local")
kiem("… gỡ xong là hết xem lương ngay", "PermissionError" in (loi(lambda: CN.cac_thang()) or ""))
F.dang_nhap("ql@x")
TK.go("HR-EMP-1")
kiem("gỡ tài khoản riêng: bỏ liên kết + khoá (không để tài khoản mồ côi đăng nhập được)",
     not F.DB["Employee"]["HR-EMP-1"].get("ns_tai_khoan") and F.DB["User"]["0912345678@sx.local"]["enabled"] == 0)
r = TK.tao("HR-EMP-1", xac_nhan=1)
kiem("gắn lại tài khoản riêng đã khoá → mở lại, không đổi mật khẩu", r["lien_ket"]
     and F.DB["User"]["0912345678@sx.local"]["enabled"] == 1 and r["mat_khau"] is None)

print("\n-- danh sách --")
F.DB["Employee"]["HR-EMP-5"]["ns_tai_khoan"] = "vp@cty.vn"          # giả: người đã nghỉ còn tài khoản
F.DB["Employee"]["HR-EMP-3"]["ns_tai_khoan"] = None
d = TK.danh_sach()
ds = {x["employee"]: x for x in d["dong"]}
kiem("người đã nghỉ còn tài khoản vẫn hiện để HR khoá / gỡ; người đã nghỉ không tài khoản thì không",
     "HR-EMP-5" in ds and d["tong_hop"]["nghi_con_tk"] == 1, str(d["tong_hop"]))
kiem("đếm có / chưa có tài khoản trên người đang làm", (d["tong_hop"]["so_nv"], d["tong_hop"]["co_tk"])
     == (5, 2), str(d["tong_hop"]))
kiem("dòng tài khoản: SĐT, bật, riêng / dùng chung", ds["HR-EMP-1"]["tai_khoan"]["sdt"] == "0912345678"
     and ds["HR-EMP-1"]["tai_khoan"]["rieng"] and ds["HR-EMP-1"]["tai_khoan"]["bat"]
     and not ds["HR-EMP-5"]["tai_khoan"]["rieng"])
kiem("báo site đã cho đăng nhập bằng SĐT", d["dang_nhap_sdt"])
kiem("báo công nhân đang thấy cả phiếu tạm tính (mặc định)", d["cong_nhan_xem_nhap"] is True)
F.CONF["ns_cong_nhan_xem_nhap"] = 0
kiem("… tắt bằng site_config thì báo chỉ phiếu đã duyệt", TK.danh_sach()["cong_nhan_xem_nhap"] is False)
F.CONF.clear()
F.HE_THONG.update({"allow_login_using_mobile_number": 0, "allow_login_using_user_name": 0})
kiem("… chưa bật → cờ false để màn hình báo đỏ", not TK.danh_sach()["dang_nhap_sdt"])
F.META_FIELDS["Employee"] = {"employee_name", "department", "status", "cell_number"}
d = TK.danh_sach()
kiem("chưa migrate field → danh sách vẫn mở, báo co_field=false; tạo thì báo chạy migrate",
     not d["co_field"] and "migrate" in (loi(lambda: TK.tao("HR-EMP-3")) or ""))
del F.META_FIELDS["Employee"]

src = open(os.path.join(F.GOC, "ns", "public", "ns", "lib", "api.js"), encoding="utf-8").read()
import re  # noqa: E402
for m in sorted(set(re.findall(r"ns\.api\.tai_khoan\.(\w+)", src))):
    kiem(f"client gọi method có thật: tai_khoan.{m}", callable(getattr(TK, m, None)))

print("TAIKHOAN-OK" if not hong else f"TAIKHOAN: {hong} HỎNG")
sys.exit(1 if hong else 0)
