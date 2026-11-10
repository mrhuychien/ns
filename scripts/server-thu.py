"""Server THỬ cho bài test trình duyệt (scripts/test-giaodien.mjs) — chạy API THẬT của ns trên Frappe giả.

Không cần bench: phục vụ
  · GET  /assets/ns/ns/*           → ns/public/ns/* (bỏ ?v=)
  · GET  /ns, /phieuluong          → render CHÍNH www/*.html bằng jinja2 (templates/web.html giả tối thiểu) với context
                                     của CHÍNH www/*.py — import map, NS_CONTEXT, build handshake là bản thật
  · POST /api/method/<dotted>      → gọi hàm Python thật; lỗi trả như Frappe (403 PermissionError, 417 ValidationError,
                                     404 DoesNotExist, kèm _server_messages) để lib/api.js đọc đúng như production
  · POST /api/method/logout        → xoá cookie
  · GET  /__test/dang_nhap?u=…      → đặt cookie phiên (người dùng giả); /__test/goi → nhật ký lượt gọi API
Người dùng của request = cookie `sid`. Một luồng (HTTPServer, không Threading): state frappe giả là biến toàn cục.

Chạy: python3 -B scripts/server-thu.py <port>   (test-giaodien.mjs tự bật / tắt)
"""
import json
import os
import sys
import traceback
from datetime import date
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, unquote, urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fakefrappe as F  # noqa: E402

import jinja2  # noqa: E402

fr = F.cai()
M = F.nap_ns()
W_NS = F.nap("ns.www.ns", os.path.join(F.GOC, "ns", "www", "ns.py"))
W_PL = F.nap("ns.www.phieuluong", os.path.join(F.GOC, "ns", "www", "phieuluong.py"))
PUB = os.path.join(F.GOC, "ns", "public", "ns")
GOI = []

WEB_HTML = """<!doctype html><html lang="vi"><head><meta charset="utf-8"><title>{% block title %}{% endblock %}</title>
{% block head_include %}{% endblock %}</head><body>
{% block navbar %}<nav class="navbar navbar-light">NAVBAR ERPNext</nav>{% endblock %}
<main class="page-content">{% block page_content %}{% endblock %}</main>
{% block footer %}<footer class="web-footer">FOOTER</footer>{% endblock %}</body></html>"""
ENV = jinja2.Environment(loader=jinja2.ChoiceLoader([
    jinja2.DictLoader({"templates/web.html": WEB_HTML}),
    jinja2.FileSystemLoader(os.path.join(F.GOC, "ns", "www")),
]), autoescape=False)


def seed():
    """Dữ liệu mẫu: một công nhân khoán (An), một công nhật (Bình), một người chưa có tài khoản (Cường)."""
    F.don_dep()
    D = date
    for r, d in (("System Manager", 1), ("HR Manager", 1), ("HR User", 1), ("SX Vao Hop", 0)):
        F.them("Role", r, role_name=r, desk_access=d)
    F.them_user("ql@x", ["HR Manager"], full_name="Chị Quản Lý")
    F.them_user("hr@x", ["HR User"], full_name="Anh Nhân Sự")
    F.them_user("an@x", ["SX Vao Hop"], username="0912345678", mobile_no="0912345678", full_name="Nguyễn Thị An")
    F.them_user("binh@x", [], username="0987654321", mobile_no="0987654321", full_name="Trần Văn Bình")
    F.them_user("lac@x", [], full_name="Tài khoản lạc")
    F.them("Employee", "HR-EMP-00001", employee_name="Nguyễn Thị An", status="Active", department="Công khoán - HGC",
           cell_number="0912345678", ns_tai_khoan="an@x", date_of_joining="2024-03-01")
    F.them("Employee", "HR-EMP-00002", employee_name="Trần Văn Bình", status="Active", department="Văn phòng - HGC",
           cell_number="0987654321", ns_tai_khoan="binh@x", date_of_joining="2023-01-10")
    F.them("Employee", "HR-EMP-00003", employee_name="Lê Văn Cường", status="Active", department="Công khoán - HGC",
           cell_number="0901 234 567", date_of_joining="2025-06-01")
    F.them("Employee", "HR-EMP-00004", employee_name="Phạm Không Số", status="Active", department="Văn phòng - HGC",
           cell_number=None)
    F.them("Department", "Công khoán - HGC", is_group=0)
    F.them("Department", "Văn phòng - HGC", is_group=0)

    # Phiếu khoán T11 của An (đã duyệt) — đúng bộ dữ liệu của test-phieuluong.mjs bên app sx (D234)
    F.them("SX Phieu Luong", "PL-2026-11-HR-EMP-00001", employee="HR-EMP-00001", ten_nhan_vien="Nguyễn Thị An",
           thang=11, nam=2026, docstatus=1, trang_thai="Đã duyệt", ngay_cong=2.5, ngay_san_xuat=0,
           luong_san_pham=15_772_400, tien_an=50_000, chuyen_can=0, ho_tro_ngay_cong=0, thuong_tham_nien=0,
           ho_tro=0, tien_phat=0, bao_hiem=0, tong_tien=15_822_400, tong_khau_tru=0, luong_thuc_nhan=15_822_400,
           ghi_chu="",
           chi_tiet=[
               dict(ngay=D(2026, 11, 1), san_pham="TP-SEN", ten_san_pham="Bánh đậu xanh sen", cach_lam="Máy",
                    so_luong=110, don_gia=1200, thanh_tien=132_000),
               dict(ngay=D(2026, 11, 1), theo_gio=1, so_gio=2.5, ten_san_pham="Làm theo giờ", don_gia=33_000,
                    thanh_tien=82_500),
               dict(ngay=D(2026, 11, 2), san_pham="TP-TT", ten_san_pham="Bánh TT", cach_lam="Tay", so_luong=5,
                    don_gia=0, thanh_tien=0),
               dict(ngay=D(2026, 11, 2), theo_gio=1, so_gio=3, ten_san_pham="Làm theo giờ", don_gia=30_000,
                    thanh_tien=90_000),
               dict(ngay=D(2026, 11, 4), san_pham="TP-DB",
                    ten_san_pham="Bánh trung thu nhân đậu xanh sầu riêng trứng muối đặc biệt hộp bốn cái",
                    cach_lam="Máy hỗ trợ", so_luong=1234, don_gia=12_500, thanh_tien=15_425_000),
               dict(ngay=D(2026, 11, 4), san_pham="TP-LA", ten_san_pham="Bánh <i>lạ</i>", cach_lam=None,
                    so_luong=10, don_gia=1250, thanh_tien=12_500)],
           dong=[
               dict(ngay=D(2026, 11, 1), thu="Chủ nhật", an_ca=1, an_dem=0, tien_an=20_000, luong_sp=214_500,
                    he_so=1.2, thu_nhap_ngay=277_400),
               dict(ngay=D(2026, 11, 2), thu="Thứ 2", an_ca=0, an_dem=0, tien_an=0, luong_sp=90_000, he_so=1,
                    thu_nhap_ngay=90_000),
               dict(ngay=D(2026, 11, 3), thu="Thứ 3", an_ca=1, an_dem=1, tien_an=30_000, luong_sp=0, he_so=1,
                    thu_nhap_ngay=30_000),
               dict(ngay=D(2026, 11, 4), thu="Thứ 4", an_ca=0, an_dem=0, tien_an=0, luong_sp=15_437_500, he_so=1,
                    thu_nhap_ngay=15_437_500)],
           phat=[])
    F.them("SX Phieu Luong", "PL-2026-10-HR-EMP-00001", employee="HR-EMP-00001", ten_nhan_vien="Nguyễn Thị An",
           thang=10, nam=2026, docstatus=1, ngay_cong=24, luong_san_pham=7_000_000, tien_an=480_000,
           chuyen_can=300_000, tong_tien=7_780_000, bao_hiem=500_000, tien_phat=20_000, tong_khau_tru=520_000,
           luong_thuc_nhan=7_260_000, chi_tiet=[], dong=[],
           phat=[dict(ly_do="Hộp móp", so_luong=2, gia_tien=10_000, thanh_tien=20_000)])
    F.them("SX Phieu Luong", "PL-2026-12-HR-EMP-00001", employee="HR-EMP-00001", ten_nhan_vien="Nguyễn Thị An",
           thang=12, nam=2026, docstatus=0, luong_thuc_nhan=1_000_000, tong_tien=1_000_000, chi_tiet=[], dong=[],
           phat=[])                                                        # nháp — công nhân không thấy
    F.them("SalaryDay", "PLC-0010", employee="HR-EMP-00002", month=10, year=2026, docstatus=1, status="",
           ngaysanxuat=26, congngay=24, lamthem=1.5, luongcoban=6_500_000, luongngaycong=6_000_000,
           luonglamthem=450_000, anca=480_000, chuyencan=200_000, hotro=300_000, thuongkhac=100_000,
           tongtien=7_530_000, baohiem=550_000, tienphat=30_000, tongkhautru=580_000, luongthucnhan=6_950_000,
           luongck=5_000_000,
           chamcong=[dict(ngaycc=D(2026, 10, d), congngay=1 if d != 3 else 0.5, themgio=2.5 if d == 1 else 0)
                     for d in range(1, 27)],
           bangghiloiphat=[dict(noidung="Đi muộn", soluong=3, giatien=10_000, thanhtienphat=30_000)])


# Màn hồ sơ gọi nhan_vien.chi_tiet (cả bộ cảnh báo / bổ sung) — ngoài phạm vi test này nên trả mẫu đúng SHAPE thật.
def _chi_tiet_mau(name):
    e = F.DB["Employee"][name]
    return {"name": name, "employee_name": e["employee_name"], "department": e["department"], "status": "Active",
            "loai_luong": "Khoán" if "khoán" in e["department"] else "Nhật", "tham_nien_nam": 2.7, "canh_bao": [],
            "thieu": [], "pct_du": 100, "field_co": ["first_name"], "tuy_chon": {}, "ns_giay_to": [],
            "first_name": e["employee_name"], "image": None}


GIA = {
    "ns.api.nhan_vien.chi_tiet": lambda name: _chi_tiet_mau(name),
    "ns.api.viec.tong_hop": lambda: {"co_do": False, "nhom": []},
}


def goi_ham(dotted, args):
    if dotted in GIA:
        return GIA[dotted](**args)
    mod, _, ten = dotted.rpartition(".")
    if not mod.startswith("ns.api."):
        raise F.PermissionError(f"Không được gọi {dotted}")
    m = F.nap(mod)
    return getattr(m, ten)(**args)


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _user(self):
        c = SimpleCookie(self.headers.get("Cookie") or "")
        return unquote(c["sid"].value) if "sid" in c and c["sid"].value else "Guest"

    def _gui(self, code, body, ctype="text/html; charset=utf-8", them=None):
        b = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        for k, v in (them or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        u = urlparse(self.path)
        p = u.path
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        if p.startswith("/assets/ns/ns/"):
            f = os.path.normpath(os.path.join(PUB, p[len("/assets/ns/ns/"):]))
            if not f.startswith(PUB) or not os.path.isfile(f):
                return self._gui(404, "404")
            ct = "text/javascript" if f.endswith(".js") else "text/css" if f.endswith(".css") else "text/plain"
            return self._gui(200, open(f, "rb").read(), ct + "; charset=utf-8")
        if p == "/__test/dang_nhap":
            return self._gui(200, "ok", them={"Set-Cookie": f"sid={q.get('u', '')}; Path=/"})
        if p == "/__test/goi":
            return self._gui(200, json.dumps(GOI), "application/json")
        if p == "/__test/seed":
            seed()
            GOI.clear()
            return self._gui(200, "ok")
        if p == "/__test/db":
            return self._gui(200, json.dumps(F.DB.get(q["dt"], {}).get(q["name"]), default=str), "application/json")
        if p in ("/ns", "/phieuluong"):
            F.dang_nhap(self._user())
            fr.form_dict = F.Doc(q)
            fr.local.flags.redirect_location = None
            ctx = F.Doc()
            try:
                (W_NS if p == "/ns" else W_PL).get_context(ctx)
            except F.Redirect:
                return self._gui(302, "", them={"Location": fr.local.flags.redirect_location})
            html = ENV.get_template("ns.html" if p == "/ns" else "phieuluong.html").render(
                frappe=fr, **ctx)
            return self._gui(200, html)
        if p == "/login":
            return self._gui(200, "<!doctype html><title>Đăng nhập</title><h1 id='login'>Đăng nhập</h1>")
        return self._gui(404, "404")

    def do_POST(self):
        p = urlparse(self.path).path
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n) if n else b""
        if p == "/api/method/logout":
            GOI.append({"method": "logout", "user": self._user(), "csrf": self.headers.get("X-Frappe-CSRF-Token")})
            return self._gui(200, json.dumps({}), "application/json", {"Set-Cookie": "sid=; Path=/; Max-Age=0"})
        if not p.startswith("/api/method/"):
            return self._gui(404, "404")
        dotted = p[len("/api/method/"):]
        try:
            args = json.loads(raw or b"{}")
        except ValueError:
            args = {}
        user = self._user()
        F.dang_nhap(user)
        GOI.append({"method": dotted, "args": args, "user": user, "csrf": self.headers.get("X-Frappe-CSRF-Token")})
        try:
            kq = goi_ham(dotted, args)
            return self._gui(200, json.dumps({"message": kq}, default=str), "application/json")
        except F.Loi as e:
            code = 403 if isinstance(e, F.PermissionError) else 404 if isinstance(e, F.DoesNotExistError) else 417
            msg = json.dumps([json.dumps({"message": str(e)})])
            return self._gui(code, json.dumps({"exc_type": type(e).__name__, "_server_messages": msg}),
                             "application/json")
        except Exception as e:  # lỗi code thật → 500 + traceback để test in ra
            traceback.print_exc()
            return self._gui(500, json.dumps({"exc_type": type(e).__name__, "exception": str(e)}), "application/json")


if __name__ == "__main__":
    seed()
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8124
    srv = HTTPServer(("127.0.0.1", port), H)
    print(f"server-thu: http://127.0.0.1:{port}", flush=True)
    srv.serve_forever()
