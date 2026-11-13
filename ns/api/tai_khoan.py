"""Tài khoản XEM LƯƠNG cho công nhân — màn /ns → Tài khoản và ô tài khoản ở hồ sơ → Công & lương.

Xưởng không có email → tài khoản định danh bằng SỐ ĐIỆN THOẠI, cùng cách app sx cấp tài khoản cho QC (sx D81):
username = mobile_no = SĐT chuẩn hoá 0xxxxxxxxx; email giả `{SĐT}@{tên miền}` chỉ để đủ chỗ Frappe đòi (không ai
gửi thư tới đó). Công nhân đăng nhập ở /login bằng SĐT + mật khẩu — site phải bật System Settings → "Allow Login
using Mobile Number" (hoặc "… User Name"); màn Tài khoản báo đỏ khi chưa bật.

═══ GẮN TÀI KHOẢN ↔ NHÂN VIÊN: Employee.ns_tai_khoan — KHÔNG dùng Employee.user_id ═══
ERPNext: Employee có user_id thì MỖI LẦN lưu hồ sơ tự cấp role "Employee" cho tài khoản đó (employee.py
update_user) — role đang có quyền GHI SalaryDay trên site (SPEC §8) và vào được Desk. Field riêng của app (unique,
chỉ đọc trên Desk) tránh hẳn chuyện đó, và chỉ màn này gắn / gỡ (có kiểm bên dưới).

═══ ROLE "NS Cong Nhan" ═══
Không vào Desk → Frappe tự xếp Website User. Trang vào sau đăng nhập = /phieuluong (Role.home_page). Tạo bởi
ns.setup.install.dam_bao_role (chỉ tạo khi thiếu, không sửa role đã có — bài học sx D105). Quyền xem lương KHÔNG
dựa vào role mà dựa vào liên kết ns_tai_khoan (ns.api.cong_nhan) — role chỉ để định trang chủ và nhận diện.

═══ CHỈ ĐỤNG TÀI KHOẢN CỦA APP NÀY ═══
Cấp lại mật khẩu / khoá / mở chỉ làm với tài khoản RIÊNG của app: mọi role ⊆ {NS Cong Nhan}. Tài khoản dùng chung
(QC đã có tài khoản sx, nhân viên văn phòng có Desk…) chỉ được GẮN / GỠ — mật khẩu, trạng thái quản ở nơi cấp.
Không có chặn này thì màn "tài khoản công nhân" đổi được mật khẩu của Administrator.

═══ GẮN VÀO TÀI KHOẢN SẴN CÓ PHẢI XÁC NHẬN ═══
SĐT trên hồ sơ gõ nhầm một số là trùng tài khoản của người khác → người đó đọc được lương của hồ sơ này. Tìm thấy
tài khoản sẵn có thì KHÔNG tự gắn: trả tên chủ tài khoản để HR nhìn rồi gọi lại với xac_nhan=1.

Mật khẩu chỉ hiện ĐÚNG MỘT LẦN (Frappe lưu băm). Mất thẻ → Cấp lại (mật khẩu mới + đăng xuất mọi máy).
Quyền: xem = guard() (HR User trở lên); tạo / cấp lại / khoá / gỡ = guard_quan_ly() (HR Manager, System Manager)
— cấp quyền đăng nhập là việc của quản lý.
"""
import re
import secrets

import frappe
from frappe import _
from frappe.utils import cint, get_url

from ns.api import guard, guard_quan_ly
from ns.api.cong_nhan import dia_chi_the

ROLE_CN = "NS Cong Nhan"
F_TK = "ns_tai_khoan"
TRANG_CN = "/phieuluong"

# Mật khẩu người ta CHÉP TAY từ thẻ: bỏ 0 O o, 1 l I i. Viết THẲNG từng bảng chữ (sx đã dính: .lower() của
# "…KLM…" đẻ lại đúng chữ l vừa loại).
CHU_HOA = "ABCDEFGHJKLMNPQRSTUVWXYZ"      # không I, không O
CHU_THUONG = "abcdefghjkmnpqrstuvwxyz"    # không i, l, o
CHU_SO = "23456789"                       # không 0, 1
KHO_KY_TU = CHU_HOA + CHU_THUONG + CHU_SO
DO_DAI_MK = 8                              # gõ trên điện thoại; 55^8 ≈ 8·10^13 tổ hợp, Frappe khoá sau 10 lần sai


# ──────────────────────────────────────────────────────────────── tiện ích ──


def chuan_sdt(sdt):
    """SĐT Việt Nam về dạng 0xxxxxxxxx, hoặc throw. Nhận '+84 912 345 678', '84912345678', '0912.345.678' —
    cùng một người phải ra cùng một tài khoản (giống sx.api.nguoidung.chuan_sdt)."""
    so = re.sub(r"[^0-9+]", "", str(sdt or ""))
    if so.startswith("+84"):
        so = "0" + so[3:]
    elif so.startswith("84") and len(so) >= 11:
        so = "0" + so[2:]
    so = so.lstrip("+")
    if not re.fullmatch(r"0\d{9,10}", so):
        if not str(sdt or "").strip():
            frappe.throw(_("Hồ sơ chưa có số điện thoại — nhập số để làm tên đăng nhập."))
        frappe.throw(_("Số điện thoại '{0}' không hợp lệ. Cần 10 số bắt đầu bằng 0 (ví dụ 0912345678).").format(sdt))
    return so


def mat_khau_moi(n=DO_DAI_MK):
    """Mật khẩu ngẫu nhiên đọc được: đủ chữ hoa / thường / số (chính sách mật khẩu của site có thể đòi), không ký
    tự dễ nhìn nhầm, không ký tự đặc biệt (bàn phím điện thoại phải chuyển bảng)."""
    rd = secrets.SystemRandom()
    ds = [rd.choice(CHU_HOA), rd.choice(CHU_THUONG), rd.choice(CHU_SO)]
    ds += [rd.choice(KHO_KY_TU) for _i in range(max(0, n - len(ds)))]
    rd.shuffle(ds)
    return "".join(ds)


def _ten_mien():
    """Tên miền của email giả. site_config ns_ten_mien_user → SX Settings (cùng tên miền với tài khoản app sx cấp,
    để một SĐT không thành hai tài khoản) → ns.local. Đừng dùng tên miền thật đang nhận thư."""
    tm = (frappe.conf.get("ns_ten_mien_user") or "").strip().lstrip("@")
    if tm:
        return tm
    try:
        if frappe.db.exists("DocType", "SX Settings") and frappe.get_meta("SX Settings").has_field("ten_mien_user"):
            return (frappe.db.get_single_value("SX Settings", "ten_mien_user") or "").strip().lstrip("@") or "sx.local"
    except Exception:
        pass
    return "ns.local"


def _co_field():
    return frappe.get_meta("Employee").has_field(F_TK)


def _can_field():
    if not _co_field():
        frappe.throw(_("Employee chưa có field ns_tai_khoan — chạy bench migrate."))


def _tim_user(sdt):
    """Tài khoản sẵn có của SĐT: theo username, mobile_no, rồi email giả."""
    for loc in ({"username": sdt}, {"mobile_no": sdt}):
        u = frappe.db.get_value("User", loc, "name")
        if u:
            return u
    return frappe.db.get_value("User", f"{sdt}@{_ten_mien()}", "name")


def _roles(users):
    """{user: {role,...}} — role GÁN TRỰC TIẾP (Has Role), không tính All / Guest."""
    out = {u: set() for u in users}
    if users:
        for r in frappe.get_all("Has Role", filters={"parenttype": "User", "parent": ("in", list(users))},
                                fields=["parent", "role"], limit_page_length=0):
            out.setdefault(r.parent, set()).add(r.role)
    return out


def la_tk_rieng(user, roles=None):
    """Tài khoản riêng của app: không phải tài khoản hệ thống, mọi role ⊆ {NS Cong Nhan}."""
    if not user or user in ("Administrator", "Guest"):
        return False
    roles = _roles([user])[user] if roles is None else roles
    return roles <= {ROLE_CN}


def _co_desk(user):
    return frappe.db.get_value("User", user, "user_type") == "System User"


def _dang_nhap_sdt():
    """Site cho đăng nhập bằng SĐT chưa (Mobile Number hoặc User Name)?"""
    try:
        return bool(cint(frappe.get_system_settings("allow_login_using_mobile_number"))
                    or cint(frappe.get_system_settings("allow_login_using_user_name")))
    except Exception:
        return False


def _nv(employee):
    _can_field()
    e = frappe.db.get_value("Employee", employee, ["name", "employee_name", "cell_number", "status", "department",
                                                   F_TK], as_dict=True)
    if not e:
        frappe.throw(_("Không có nhân viên {0}.").format(employee), frappe.DoesNotExistError)
    return e


def _gan(employee, user):
    # db.set_value: KHÔNG chạy validate / on_update của Employee (ERPNext) — chỉ ghi một ô của app.
    frappe.db.set_value("Employee", employee, F_TK, user, update_modified=False)


def _dat_bat(user, bat):
    """Khoá / mở qua User.save(): Frappe tự đăng xuất tài khoản vừa khoá (check_enable_disable) và xoá cache; ghi
    thẳng db.set_value thì phiên đang mở vẫn sống. Gọi thêm clear_sessions cho chắc."""
    doc = frappe.get_doc("User", user)
    if cint(doc.enabled) != cint(bat):
        doc.enabled = cint(bat)
        doc.flags.ignore_permissions = True
        doc.save()
    if not cint(bat):
        _dang_xuat_het(user)


def _dang_xuat_het(user):
    from frappe.sessions import clear_sessions

    clear_sessions(user=user, force=True)


def _can_role():
    """Role NS Cong Nhan phải có trước khi gán (deploy quên migrate vẫn chạy được) — chỉ tạo khi thiếu."""
    from ns.setup.install import dam_bao_role

    dam_bao_role()


def _the(e, user, mat_khau=None, **them):
    """Dữ liệu một thẻ đăng nhập (màn in thẻ). `url` (ngắn) in thành chữ để gõ tay; `url_qr` nằm trong QR và mang mã
    chủ thẻ (?the=) — máy đang đăng nhập tài khoản khác thì trang biết thẻ là của ai: phòng nhân sự xem như công nhân,
    người khác được mời đăng xuất rồi đăng nhập bằng thẻ (xem www/phieuluong.py)."""
    u = frappe.db.get_value("User", user, ["username", "mobile_no", "full_name"], as_dict=True) or {}
    return {
        "employee": e.name, "ten": e.employee_name or e.name, "user": user,
        "sdt": u.get("username") or u.get("mobile_no") or "", "mat_khau": mat_khau,
        "url": get_url(TRANG_CN), "url_qr": get_url(dia_chi_the(e.name)), **them,
    }


def _dong_tk(user, info, roles):
    if not user:
        return None
    i = info.get(user) or {}
    return {
        "user": user, "sdt": i.get("username") or i.get("mobile_no") or "", "ten": i.get("full_name") or user,
        "bat": bool(cint(i.get("enabled"))), "lan_cuoi": str(i.get("last_login")) if i.get("last_login") else None,
        "desk": i.get("user_type") == "System User", "rieng": la_tk_rieng(user, roles.get(user, set())),
        "co_that": bool(i),
    }


def _thong_tin_user(users):
    if not users:
        return {}
    return {u.name: u for u in frappe.get_all(
        "User", filters={"name": ("in", list(users))},
        fields=["name", "username", "mobile_no", "full_name", "enabled", "last_login", "user_type"],
        limit_page_length=0)}


# ──────────────────────────────────────────────────────────────────── đọc ──


@frappe.whitelist()
def danh_sach():
    """Mọi nhân viên đang làm + nhân viên đã nghỉ / tạm nghỉ còn tài khoản. Lọc / tìm ở trình duyệt (≈100 dòng)."""
    guard()
    co_field = _co_field()
    fields = ["name", "employee_name", "department", "status", "cell_number"] + ([F_TK] if co_field else [])
    nv = frappe.get_all("Employee", filters={"status": "Active"}, fields=fields, order_by="employee_name asc",
                        limit_page_length=0)
    if co_field:
        nv += frappe.get_all("Employee", filters={"status": ("!=", "Active"), F_TK: ("is", "set")}, fields=fields,
                             order_by="employee_name asc", limit_page_length=0)
    users = {e.get(F_TK) for e in nv if e.get(F_TK)}
    info, roles = _thong_tin_user(users), _roles(users)
    dong = []
    for e in nv:
        tk = _dong_tk(e.get(F_TK), info, roles)
        dong.append({"employee": e.name, "employee_name": e.employee_name, "department": e.department,
                     "status": e.status, "cell_number": e.cell_number, "tai_khoan": tk})
    active = [d for d in dong if d["status"] == "Active"]
    return {
        "co_field": co_field, "dang_nhap_sdt": _dang_nhap_sdt(), "url": get_url(TRANG_CN), "dong": dong,
        "tong_hop": {
            "so_nv": len(active),
            "co_tk": sum(1 for d in active if d["tai_khoan"]),
            "chua_tk": sum(1 for d in active if not d["tai_khoan"]),
            "bi_khoa": sum(1 for d in dong if d["tai_khoan"] and not d["tai_khoan"]["bat"]),
            "nghi_con_tk": sum(1 for d in dong if d["status"] != "Active" and d["tai_khoan"]
                               and d["tai_khoan"]["bat"]),
        },
    }


@frappe.whitelist()
def cua_nv(employee):
    """Tài khoản của MỘT nhân viên (ô tài khoản trong hồ sơ)."""
    guard()
    if not _co_field():
        return {"co_field": False, "tai_khoan": None, "dang_nhap_sdt": _dang_nhap_sdt()}
    e = _nv(employee)
    user = e.get(F_TK)
    users = {user} if user else set()
    return {"co_field": True, "employee": e.name, "cell_number": e.cell_number, "dang_nhap_sdt": _dang_nhap_sdt(),
            "url": get_url(TRANG_CN), "tai_khoan": _dong_tk(user, _thong_tin_user(users), _roles(users))}


# ─────────────────────────────────────────────────────────────────── ghi ──


@frappe.whitelist()
def tao(employee, sdt=None, xac_nhan=0):
    """Cấp tài khoản xem lương cho một nhân viên.

    - SĐT chưa có tài khoản → tạo tài khoản riêng (role NS Cong Nhan), trả mật khẩu (hiện một lần) để in thẻ.
    - SĐT đã có tài khoản → CHƯA gắn: trả {can_xac_nhan, ten_tai_khoan, …}; HR xác nhận thì gọi lại xac_nhan=1 →
      gắn, không đổi mật khẩu (người đó đăng nhập bằng mật khẩu đang dùng).
    """
    guard_quan_ly()
    e = _nv(employee)
    if e.get(F_TK):
        frappe.throw(_("{0} đã có tài khoản xem lương ({1}). Muốn đổi thì Gỡ trước.").format(
            e.employee_name, e.get(F_TK)))
    so = chuan_sdt(sdt or e.cell_number)
    user = _tim_user(so)
    if user:
        if user in ("Administrator", "Guest"):
            frappe.throw(_("Không gắn được tài khoản hệ thống."))
        khac = frappe.db.get_value("Employee", {F_TK: user, "name": ("!=", e.name)}, ["name", "employee_name"],
                                   as_dict=True)
        if khac:
            frappe.throw(_("Số {0} là tài khoản đang gắn với hồ sơ {1} ({2}). Mỗi tài khoản chỉ xem lương của một "
                           "người — kiểm lại số điện thoại.").format(so, khac.employee_name, khac.name))
        u = frappe.db.get_value("User", user, ["full_name", "enabled", "user_type"], as_dict=True) or {}
        rieng = la_tk_rieng(user)
        if not cint(xac_nhan):
            return {"can_xac_nhan": True, "employee": e.name, "ten": e.employee_name, "sdt": so, "user": user,
                    "ten_tai_khoan": u.get("full_name") or user, "bat": bool(cint(u.get("enabled"))),
                    "dung_chung": not rieng, "desk": u.get("user_type") == "System User"}
        _gan(e.name, user)
        if rieng and not cint(u.get("enabled")):
            _dat_bat(user, 1)                                    # tài khoản riêng của app đang khoá → mở lại
        if u.get("user_type") != "System User":
            # Website User: thêm role để vào thẳng /phieuluong sau đăng nhập. Tài khoản Desk thì KHÔNG — role có
            # home_page sẽ kéo cả người dùng Desk sang /phieuluong mỗi lần đăng nhập.
            doc = frappe.get_doc("User", user)
            if ROLE_CN not in {r.role for r in doc.roles}:
                _can_role()
                doc.flags.ignore_permissions = True
                doc.add_roles(ROLE_CN)
        return _the(e, user, None, lien_ket=True, dung_chung=not rieng)

    _can_role()
    mk = mat_khau_moi()
    doc = frappe.get_doc({
        "doctype": "User",
        "email": f"{so}@{_ten_mien()}",
        "username": so,
        "mobile_no": so,
        "first_name": e.employee_name or so,
        "enabled": 1,
        # Không đặt user_type: Frappe tự tính lúc lưu (role không vào Desk → Website User).
        "send_welcome_email": 0,
        "new_password": mk,
        "roles": [{"role": ROLE_CN}],
    })
    doc.flags.ignore_permissions = True
    doc.insert()
    _gan(e.name, doc.name)
    return _the(e, doc.name, mk, lien_ket=False, dung_chung=False)


def _tk_cua(employee, rieng=True):
    e = _nv(employee)
    user = e.get(F_TK)
    if not user:
        frappe.throw(_("{0} chưa có tài khoản xem lương.").format(e.employee_name))
    if not frappe.db.exists("User", user):
        frappe.throw(_("Tài khoản {0} không còn trên hệ thống — bấm Gỡ rồi tạo lại.").format(user))
    if rieng and not la_tk_rieng(user):
        frappe.throw(_("Tài khoản {0} dùng chung với chức năng khác (app sx / Desk) — mật khẩu và khoá / mở quản "
                       "ở nơi cấp tài khoản đó. Ở đây chỉ Gỡ được.").format(user))
    return e, user


@frappe.whitelist()
def cap_lai(employee):
    """Mật khẩu mới cho tài khoản riêng của app + đăng xuất mọi máy đang dùng (mất thẻ / quên mật khẩu)."""
    guard_quan_ly()
    e, user = _tk_cua(employee)
    mk = mat_khau_moi()
    doc = frappe.get_doc("User", user)
    doc.new_password = mk
    doc.flags.ignore_permissions = True
    doc.save()
    _dang_xuat_het(user)
    return _the(e, user, mk, lien_ket=False, dung_chung=False)


@frappe.whitelist()
def khoa(employee, khoa=1):
    """Khoá (khoa=1) / mở (khoa=0) tài khoản riêng của app. Khoá thì đăng xuất luôn mọi máy — Frappe không tự cắt
    phiên đang mở của tài khoản vừa bị khoá."""
    guard_quan_ly()
    _e, user = _tk_cua(employee)
    khoa = cint(khoa)
    _dat_bat(user, 0 if khoa else 1)
    return {"employee": employee, "user": user, "bat": not khoa}


@frappe.whitelist()
def go(employee):
    """Gỡ liên kết tài khoản ↔ hồ sơ: người đó hết xem được phiếu lương của hồ sơ này ngay lập tức.
    Tài khoản riêng của app thì khoá luôn (không còn việc gì để làm); tài khoản dùng chung chỉ bỏ role NS Cong Nhan."""
    guard_quan_ly()
    e = _nv(employee)
    user = e.get(F_TK)
    if not user:
        return {"employee": e.name, "user": None}
    _gan(e.name, None)
    if frappe.db.exists("User", user):
        rieng = la_tk_rieng(user)
        doc = frappe.get_doc("User", user)
        if ROLE_CN in {r.role for r in doc.roles} and not rieng:
            doc.flags.ignore_permissions = True
            doc.remove_roles(ROLE_CN)
        if rieng:
            _dat_bat(user, 0)
    return {"employee": e.name, "user": user}
