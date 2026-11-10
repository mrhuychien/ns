"""Import map của /ns và /phieuluong phải là JSON HỢP LỆ và phủ ĐỦ module dùng chung (Luật vàng #1, frappe-portal-spa).

Import map hỏng KHÔNG báo lỗi ở chỗ nó hỏng: thừa một dấu phẩy là trình duyệt vứt cả khối, mọi module nạp không `?v`
— app vẫn chạy, chỉ là chạy BẢN CŨ trong cache ("sửa rồi mà máy vẫn thế"). Thiếu một module dùng chung thì sau lần
sửa kế tiếp module đó dính cache 1 năm → "does not provide an export named …". Bài này chốt:
  1. khối importmap parse được thành JSON, mỗi khoá trỏ về chính nó kèm ?v=;
  2. không khoá nào trỏ vào file không có;
  3. MỌI module dùng chung (lib/ components/ vendor/) mà trang nạp tới — đi theo import tĩnh từ file vào của trang
     (shell.js + mọi view với /ns; cong_nhan.js với /phieuluong) — đều có khoá trong map của trang đó.
Chạy: python3 scripts/test-importmap.py
"""
import json
import os
import posixpath
import re
import sys

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUB = os.path.join(GOC, "ns", "public", "ns")
TIEN_TO = "/assets/ns/ns/"
hong = 0


def kiem(ten, dk, ct=""):
    global hong
    if not dk:
        hong += 1
    print(f"  {'ok  ' if dk else 'HỎNG'} {ten}{(' — ' + ct) if ct and not dk else ''}")


def url_cua(f):
    return TIEN_TO + os.path.relpath(f, PUB).replace(os.sep, "/")


def import_tinh(url):
    """Các URL tuyệt đối mà file (theo URL) import tĩnh — đúng cách trình duyệt resolve đường dẫn tương đối."""
    f = os.path.join(PUB, url[len(TIEN_TO):])
    src = open(f, encoding="utf-8").read()
    out = []
    for m in re.findall(r"""^\s*import\s+(?:[\s\S]*?\s+from\s+)?['"]([^'"]+)['"]""", src, re.M):
        if m.startswith("/"):
            out.append(m)
        else:
            out.append(posixpath.normpath(posixpath.join(posixpath.dirname(url), m)))
    return out


def dong_kin(goc_urls):
    """Bao đóng import tĩnh từ các file vào."""
    da, cho = set(), list(goc_urls)
    while cho:
        u = cho.pop()
        if u in da:
            continue
        da.add(u)
        if os.path.exists(os.path.join(PUB, u[len(TIEN_TO):])):
            cho += import_tinh(u)
    return da


def kiem_trang(html_file, vao):
    print(f"-- {html_file} --")
    html = open(os.path.join(GOC, "ns", "www", html_file), encoding="utf-8").read()
    khoi = re.search(r'<script type="importmap">(.*?)</script>', html, re.S)
    kiem("có khối importmap", bool(khoi))
    if not khoi:
        return
    tho = re.sub(r"\{\{\s*asset_version\s*\}\}", "X", khoi.group(1))
    try:
        data = json.loads(tho)
    except ValueError as e:
        kiem("importmap là JSON hợp lệ", False, str(e))
        return
    kiem("importmap là JSON hợp lệ", True)
    imp = data.get("imports", {})
    kiem("mọi khoá trỏ về chính nó kèm ?v=", all(v == f"{k}?v=X" for k, v in imp.items()),
         ", ".join(k for k, v in imp.items() if v != f"{k}?v=X"))
    chet = [k for k in imp if not os.path.isfile(os.path.join(PUB, k[len(TIEN_TO):]))]
    kiem("không khoá nào trỏ vào file không có", not chet, ", ".join(chet))
    can = sorted(u for u in dong_kin(vao) if re.match(rf"{re.escape(TIEN_TO)}(lib|components|vendor)/", u))
    thieu = [u for u in can if u not in imp]
    kiem(f"đủ {len(can)} module dùng chung trang nạp tới", not thieu, "THIẾU: " + ", ".join(thieu))
    for u in can:
        if not os.path.isfile(os.path.join(PUB, u[len(TIEN_TO):])):
            kiem(f"module import có thật: {u}", False)


views = [url_cua(os.path.join(PUB, "views", f)) for f in sorted(os.listdir(os.path.join(PUB, "views")))]
kiem_trang("ns.html", [TIEN_TO + "shell.js"] + views)
kiem_trang("phieuluong.html", [TIEN_TO + "cong_nhan.js"])

shell = open(os.path.join(PUB, "shell.js"), encoding="utf-8").read()
for v in re.findall(r"import\(withV\('\./views/(\w+)\.js'\)\)", shell):
    kiem(f"view của shell có file: views/{v}.js", os.path.isfile(os.path.join(PUB, "views", f"{v}.js")))
ns_py = open(os.path.join(GOC, "ns", "www", "ns.py"), encoding="utf-8").read()
b1 = re.search(r'SHELL_BUILD = "([^"]+)"', ns_py).group(1)
b2 = re.search(r"const BUILD = '([^']+)'", shell).group(1)
kiem("BUILD shell.js khớp SHELL_BUILD www/ns.py (Luật vàng #2)", b1 == b2, f"{b2} ≠ {b1}")

print("IMPORTMAP-OK" if not hong else f"IMPORTMAP: {hong} HỎNG")
sys.exit(1 if hong else 0)
