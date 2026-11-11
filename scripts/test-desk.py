"""Icon app NS ngoài trang chủ Desk — workspace "NS" + ô màn Apps + Desktop Icon + patch bố cục đã lưu.

Chép bài học app sx (D236 → D237 → D238, ba lần mới thấy icon trên site Frappe 16.16.0). Mọi thứ ở đây là tệp JSON nạp
khi `bench migrate`, KHÔNG chạy validate — sai là icon / trang chủ không hiện mà không ai báo:
  · workspace sai chỗ <app>/<module>/workspace/<tên>/<tên>.json → không bao giờ được nạp; content gọi card / shortcut
    không có dòng tương ứng → khối biến mất; link tới DocType KHÔNG có → Administrator mất sạch card
    (frappe.desk.desktop._prepare_item → get_meta → DoesNotExistError → get_links trả []);
  · route ô màn Apps không khớp mẫu Desk (^/desk) → mở /login khi đang đăng nhập bị đẩy ra màn chọn app; khai nhầm
    app_logo_url → đổi logo thanh điều hướng của cả Desk;
  · thư mục desktop_icon có tệp lạ (Frappe nạp MỌI tệp) → migrate gãy; tên tệp ≠ scrub(tên icon) → bộ dọn icon thừa xoá
    mất icon ở lần migrate sau; nhãn ≠ app_title và app ≠ app_name → Frappe không tìm được has_permission;
  · người đã tự sắp lưới icon không thấy icon mới (Desktop Layout) → patch thêm, chỉ cho người có quyền;
  · ô / icon NS hiện cho công nhân (Website User) hoặc người Desk không có vai HR.
Chạy: python3 scripts/test-desk.py   (verify.sh gọi sẵn)
"""
import ast
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fakefrappe as F  # noqa: E402

GOC = F.GOC
os.chdir(GOC)
hong = 0


def kiem(ten, dk, ct=""):
    global hong
    if not dk:
        hong += 1
    print(f"  {'ok  ' if dk else 'HỎNG'} {ten}{(' — ' + str(ct)) if ct and not dk else ''}")


def scrub(s):
    return s.replace(" ", "_").replace("-", "_").lower()


def slug(s):
    return s.lower().replace(" ", "-").replace("_", "-")


# DocType của app
DT = {}
for goc, _thu, tep in os.walk("ns"):
    for t in tep:
        if t.endswith(".json") and os.sep + "doctype" + os.sep in os.path.join(goc, t):
            d = json.load(open(os.path.join(goc, t), encoding="utf-8"))
            if isinstance(d, dict) and d.get("doctype") == "DocType":
                DT[d["name"]] = d
CHINH = {n for n, d in DT.items() if not d.get("istable")}
LOI = {"Employee", "Department", "Designation"}        # DocType của required_apps (erpnext / hrms) — chắc chắn có

H = open("ns/hooks.py", encoding="utf-8").read()
gan = {t.id: n.value for n in ast.parse(H).body if isinstance(n, ast.Assign) for t in n.targets
       if isinstance(t, ast.Name)}
APP, TITLE = ast.literal_eval(gan["app_name"]), ast.literal_eval(gan["app_title"])

TEP = "ns/ns/workspace/ns/ns.json"
W = json.load(open(TEP, encoding="utf-8"))
print("-- workspace NS: nạp được khi migrate --")
kiem("đúng chỗ <app>/<module>/workspace/<tên>/<tên>.json (sai chỗ là không bao giờ được nạp)",
     TEP == f"ns/{scrub(W['module'])}/workspace/{scrub(W['name'])}/{scrub(W['name'])}.json", TEP)
kiem("module có trong modules.txt và là package", W["module"] in open("ns/modules.txt").read().split()
     and os.path.exists(f"ns/{scrub(W['module'])}/__init__.py"))
kiem("tên ASCII, name = label; tiêu đề tiếng Việt", W["name"].isascii() and W["name"] == W["label"] == "NS"
     and W["title"] == "Nhân sự", (W["name"], W["title"]))
kiem("đủ ô bắt buộc v16 (label, title, type, module); công khai; doctype Workspace; app = ns",
     W["doctype"] == "Workspace" and W["type"] == "Workspace" and W["public"] == 1 and W["module"] == "NS"
     and W.get("app") == APP)
kiem("modified đúng dạng và mới (tệp cũ hơn bản trên site thì migrate bỏ qua)",
     datetime.fromisoformat(W["modified"]) >= datetime(2026, 11, 11))
C = json.loads(W["content"])
kiem("content là DANH SÁCH JSON (rỗng / không phải list → 'Content data shoud be a list')", isinstance(C, list) and C)
kiem("khối chỉ dùng loại có sẵn (header, shortcut, card, spacer), id không trùng",
     {b["type"] for b in C} <= {"header", "shortcut", "card", "spacer"} and len({b["id"] for b in C}) == len(C))
the = [b["data"]["card_name"] for b in C if b["type"] == "card"]
cb = [r["label"] for r in W["links"] if r["type"] == "Card Break"]
kiem("mỗi card trong content có đúng một Card Break cùng nhãn, và ngược lại", sorted(the) == sorted(cb)
     and len(set(cb)) == len(cb), (the, cb))
tat = [b["data"]["shortcut_name"] for b in C if b["type"] == "shortcut"]
sc = [r["label"] for r in W["shortcuts"]]
kiem("mỗi shortcut trong content có đúng một dòng shortcut cùng nhãn, nhãn không trùng", sorted(tat) == sorted(sc)
     and len(set(sc)) == len(sc), (tat, sc))
dem, sai_dem = None, []
for i, r in enumerate(W["links"]):
    if r["type"] == "Card Break":
        n = 0
        for x in W["links"][i + 1:]:
            if x["type"] == "Card Break":
                break
            n += 1
        if r["link_count"] != n:
            sai_dem.append((r["label"], r["link_count"], n))
kiem("link_count của từng card đúng số link theo sau", not sai_dem, sai_dem)
kiem("dòng đầu là Card Break", W["links"][0]["type"] == "Card Break")
kiem("mọi dòng có type + label", all(r.get("type") and r.get("label") for r in W["links"] + W["shortcuts"]))
link = [r for r in W["links"] if r["type"] == "Link"]
kiem("link nào cũng là DocType CHẮC CHẮN có (của app ns / erpnext), không trỏ bảng con — DocType thiếu làm "
     "Administrator mất sạch card", all(r["link_type"] == "DocType" and r["link_to"] in (CHINH | LOI) for r in link),
     [r["link_to"] for r in link])
kiem("mọi DocType chính của app có link", CHINH <= {r["link_to"] for r in link}, CHINH - {r["link_to"] for r in link})
kiem("nhãn link tiếng Việt, không để tên DocType trần", all(r["label"] != r["link_to"] for r in link))
shell = open("ns/public/ns/shell.js", encoding="utf-8").read()
tuyen = set(re.findall(r"route\('(/[^']*)'", shell))
url = [s for s in W["shortcuts"] if s["type"] == "URL"]
kiem("shortcut đầu: mở portal /ns", W["shortcuts"][0]["type"] == "URL" and W["shortcuts"][0]["url"] == "/ns")


def url_co_that(u):
    if u in ("/ns", "/phieuluong"):
        return os.path.exists(f"ns/www{u}.py") and os.path.exists(f"ns/www{u}.html")
    m = re.fullmatch(r"/ns#(/[\w-]*)", u)
    return bool(m) and m.group(1) in tuyen


kiem("shortcut URL trỏ trang có thật (www/*.py + route của shell.js)", all(url_co_that(s["url"]) for s in url),
     [s["url"] for s in url if not url_co_that(s["url"])])
kiem("shortcut DocType trỏ DocType có thật", all(s["link_to"] in (CHINH | LOI) for s in W["shortcuts"]
                                                  if s["type"] == "DocType"))

print("\n-- ai thấy ô / icon NS --")
F.cai()
NSAPI = F.nap("ns.api")
kiem("workspace chỉ hiện cho vai HR của app (một nguồn với guard của API và ô màn Apps)",
     {r["role"] for r in W["roles"]} == NSAPI.ROLE_DUOC_PHEP, {r["role"] for r in W["roles"]})


def thay(user, roles, loai):
    F.don_dep()
    if user != "Administrator":
        F.them_user(user, roles)
        F.DB["User"][user]["user_type"] = loai
    else:
        F.them_user("Administrator", ["System Manager"])
    F.dang_nhap(user)
    return NSAPI.co_quyen_app_desk()


kiem("HR User / HR Manager / System Manager (Desk) thấy",
     all(thay("u@x", [v], "System User") for v in ("HR User", "HR Manager", "System Manager")))
kiem("… Administrator thấy", thay("Administrator", [], None))
kiem("… công nhân (NS Cong Nhan, Website User) KHÔNG thấy", not thay("cn@x", ["NS Cong Nhan"], "Website User"))
kiem("… người Desk không có vai HR (kế toán) KHÔNG thấy", not thay("kt@x", ["Accounts User"], "System User"))
kiem("… có vai HR mà là Website User KHÔNG thấy (không vào được Desk)", not thay("w@x", ["HR User"], "Website User"))

print("\n-- hooks.py: ô màn Apps --")
apps = ast.literal_eval(gan["add_to_apps_screen"]) if "add_to_apps_screen" in gan else []
a = apps[0] if apps else {}
kiem("add_to_apps_screen: một ô, name = app_name, tiêu đề tiếng Việt", len(apps) == 1 and a.get("name") == APP
     and a.get("title") == "Nhân sự")
kiem("route khớp mẫu Desk của v16 (^/desk(/.*)?$) — không đẩy ra màn chọn app",
     re.match(r"^/desk(/.*)?$", a.get("route", "")) is not None, a.get("route"))
kiem("route trỏ đúng workspace (slug tên)", a.get("route") == f"/desk/{slug(W['name'])}", a.get("route"))
lg = a.get("logo", "")
tep_lg = lg.replace(f"/assets/{APP}/", f"{APP}/public/", 1)
kiem("logo có thật dưới ns/public, là SVG đọc được", lg.startswith(f"/assets/{APP}/") and os.path.exists(tep_lg)
     and ET.parse(tep_lg).getroot().tag.endswith("svg"), lg)
mod, ham = a.get("has_permission", "").rsplit(".", 1)
kiem("has_permission trỏ hàm có thật, gọi không tham số được (Frappe 16.16: frappe.call(path))",
     mod == "ns.api" and callable(getattr(NSAPI, ham, None)), a.get("has_permission"))
kiem("KHÔNG khai hook app_logo_url (Frappe dùng làm logo thanh điều hướng của cả Desk)", "app_logo_url" not in gan)

print("\n-- icon NS trên trang chủ Desk kiểu LƯỚI ICON (Desktop Icon) --")
THU = "ns/desktop_icon"
tep_icon = sorted(os.listdir(THU))
kiem("thư mục icon chỉ có tệp .json (Frappe nạp MỌI tệp trong đó — __init__.py hay tệp lạ là migrate gãy)",
     tep_icon and all(t.endswith(".json") for t in tep_icon), tep_icon)
I = json.load(open(f"{THU}/ns.json", encoding="utf-8"))
kiem("tên tệp = scrub(tên icon) — đúng đường bộ dọn icon thừa tìm, không bị xoá ở lần migrate sau",
     I["name"] == I["label"] and f"{scrub(I['name'].lower())}.json" == "ns.json", I["name"])
kiem("icon loại App, nhãn = app_title, app = app_name (Frappe kiểm quyền icon App theo nhãn / app → has_permission)",
     (I["doctype"], I["icon_type"], I["label"], I["app"]) == ("Desktop Icon", "App", TITLE, APP), I)
kiem("bấm icon mở đúng trang chủ (External → link = route ô màn Apps), cùng logo",
     (I["link_type"], I["link"], I["logo_url"]) == ("External", a.get("route"), a.get("logo")), I)
kiem("icon chuẩn, không ẩn, không giới hạn vai riêng (quyền theo has_permission của app)",
     (I["standard"], I["hidden"], I["roles"]) == (1, 0, []))
kiem("modified đúng dạng, mới (tệp cũ hơn bản trên site thì migrate bỏ qua)",
     datetime.fromisoformat(I["modified"]) >= datetime(2026, 11, 11))
O_ICON = {"label", "standard", "link", "icon", "idx", "logo_url", "icon_type", "app", "link_to", "parent_icon", "hidden",
          "link_type", "roles", "sidebar", "icon_image", "restrict_removal", "bg_color"}
kiem("chỉ ô có trong schema Desktop Icon v16.16 + ô hệ thống",
     set(I) - {"doctype", "name", "owner", "creation", "modified", "modified_by", "docstatus"} <= O_ICON, set(I) - O_ICON)
kiem("không trùng tên icon của app sx (SX) — hai app cùng site", I["name"] != "SX")

print("\n-- patch: icon NS vào bố cục trang chủ ĐÃ LƯU --")
P = F.nap("ns.patches.them_icon_ns_vao_bo_cuc", os.path.join(GOC, "ns", "patches", "them_icon_ns_vao_bo_cuc.py"))
CU = [{"name": "ERPNext", "label": "ERPNext", "icon_type": "App", "idx": 3, "parent_icon": None},
      {"name": "Accounting", "label": "Accounting", "icon_type": "Link", "idx": 9, "parent_icon": "ERPNext"},
      {"name": "SX", "label": "SX", "icon_type": "App", "idx": 5, "parent_icon": None}]
GHI = []


def dat():
    F.don_dep()
    F.them_user("Administrator", ["System Manager"])
    for u, roles, loai in (("hr@x", ["HR User"], "System User"), ("kt@x", ["Accounts User"], "System User"),
                           ("cn@x", ["NS Cong Nhan"], "Website User"), ("co@x", ["HR Manager"], "System User"),
                           ("hu@x", ["HR User"], "System User")):
        F.them_user(u, roles)
        F.DB["User"][u]["user_type"] = loai
    F.them("Desktop Icon", "NS", **{k: I.get(k) for k in ("label", "link", "link_type", "app", "icon_type", "idx",
                                                          "standard", "logo_url", "hidden", "restrict_removal")})
    for u in ("Administrator", "hr@x", "kt@x", "cn@x"):
        F.them("Desktop Layout", u, user=u, layout=json.dumps(CU), modified="2026-01-01 00:00:00")
    F.them("Desktop Layout", "co@x", user="co@x", layout=json.dumps(CU + [{"name": "NS", "label": "NS", "idx": 1,
                                                                          "parent_icon": None}]))
    F.them("Desktop Layout", "hu@x", user="hu@x", layout="{không phải json")


goc_set = F.set_value


def set_ghi(dt, ten, f, v=None, update_modified=True):
    GHI.append((dt, ten, f, update_modified))
    return goc_set(dt, ten, f, v, update_modified)


F.sys.modules["frappe"].db.set_value = set_ghi
dat()
P.execute()
bc = {u: F.DB["Desktop Layout"][u]["layout"] for u in F.DB["Desktop Layout"]}
moi = json.loads(bc["hr@x"])
kiem("HR (Desk) đã có bố cục: icon NS vào CUỐI hàng ngoài cùng (idx lớn nhất + 1, bỏ qua icon con)",
     moi[-1]["name"] == "NS" and moi[-1]["idx"] == 6 and moi[-1]["parent_icon"] is None and moi[-1]["link"] == "/desk/ns",
     moi[-1])
kiem("… sắp xếp cũ giữ nguyên từng icon", moi[:3] == CU)
kiem("… Administrator cũng có", json.loads(bc["Administrator"])[-1]["name"] == "NS")
kiem("… ghi đúng khuôn Frappe tự lưu (json.dumps mặc định — toàn ASCII)", bc["hr@x"] == json.dumps(moi)
     and bc["hr@x"].isascii())
kiem("người Desk KHÔNG có vai HR (kế toán): không đụng — bố cục đã lưu không qua lọc quyền", bc["kt@x"] == json.dumps(CU))
kiem("công nhân (Website User): không đụng", bc["cn@x"] == json.dumps(CU))
kiem("đã có icon NS (tự thêm / tự dời): không thêm lần hai", len([x for x in json.loads(bc["co@x"]) if x["name"] == "NS"]) == 1)
kiem("bố cục hỏng: bỏ qua, không gãy migrate", bc["hu@x"] == "{không phải json")
kiem("ghi thẳng ô layout, không đổi 'modified'", GHI and all(g[2] == "layout" and g[3] is False for g in GHI)
     and F.DB["Desktop Layout"]["hr@x"]["modified"] == "2026-01-01 00:00:00", GHI)
GHI.clear()
P.execute()
kiem("chạy lại: không ghi gì thêm (đã có icon thì thôi)", GHI == [], GHI)
dat()
del F.DB["Desktop Icon"]["NS"]
GHI.clear()
P.execute()
kiem("site chưa có dòng icon NS: không làm gì", GHI == [])
dat()
del F.DB["Desktop Layout"]
GHI.clear()
P.execute()
kiem("Frappe chưa có Desktop Layout: không làm gì", GHI == [])
pt = open("ns/patches.txt", encoding="utf-8").read()
kiem("patch đăng ký ở [post_model_sync] — chạy SAU khi migrate nạp icon NS",
     pt.index("ns.patches.them_icon_ns_vao_bo_cuc") > pt.index("[post_model_sync]"))

print("DESK-OK" if not hong else f"DESK: {hong} HỎNG")
sys.exit(1 if hong else 0)
