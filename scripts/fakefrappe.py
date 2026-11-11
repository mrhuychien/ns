"""Frappe GIẢ cho bài test của app ns — nạp module THẬT của ns trên một "DB" là dict (phỏng theo
sx/scripts/fakefrappe.py).

Đủ cho các API phiếu lương / công nhân / tài khoản: get_all (lọc, sắp nhiều khoá, chọn cột, pluck, limit),
db.get_value / exists / set_value / table_exists / has_column / get_single_value, get_doc (đọc + dựng mới), insert /
save của User (tự tính kiểu tài khoản như User.set_system_user: có role vào Desk → System User), Has Role suy từ
bảng con roles của User, phiên đăng nhập (đếm để kiểm "đăng xuất mọi máy"), site_config, System Settings.

Giống Frappe THẬT ở những chỗ test dựa vào (đã đối chiếu source v16 — xem README mục kiểm thử):
  · get_all KHÔNG kiểm quyền; xin cột không có trong meta của bảng app khác → nổ "Unknown column" như MariaDB.
  · Ô Check / Int trống khớp bộ lọc = 0 (NOT NULL DEFAULT 0).
  · get_meta(dt).has_field(f) theo META_FIELDS — tắt một field để giả "chưa migrate".

Dùng:
    import fakefrappe as F
    F.cai()                                   # trước khi nạp module ns
    M = F.nap("ns.api.cong_nhan")
"""

import copy
import importlib.util
import os
import sys
import types
from datetime import date, datetime

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))     # thư mục repo ns
DB = {}                     # doctype → {name: dict}
CONF = {}                   # site_config
HE_THONG = {"allow_login_using_mobile_number": 1, "allow_login_using_user_name": 0}
NGUOI = {"u": "Guest"}
PHIEN = {}                  # user → số phiên đang mở
DA_DANG_XUAT = []           # (user, force)
META_FIELDS = {}            # doctype → set fieldname (cho has_field); thiếu doctype → coi như có mọi field
COT = {}                    # doctype → set cột (cho has_column / kiểm cột get_all); thiếu → không kiểm
SO = {"n": 0}
VAI_DESK = {"System Manager": 1, "HR User": 1, "HR Manager": 1, "Employee": 1, "SX Quan Ly": 1,
            "SX Vao Hop": 0, "NS Cong Nhan": 0}


class Loi(Exception):
    pass


class PermissionError(Loi):
    pass


class DoesNotExistError(Loi):
    pass


class ValidationError(Loi):
    pass


class Redirect(Exception):
    pass


class Doc(dict):
    def __getattr__(self, k):
        if k.startswith("__"):
            raise AttributeError(k)
        return self.get(k)

    def __setattr__(self, k, v):
        self[k] = v


def bang(dt):
    return DB.setdefault(dt, {})


def don_dep():
    DB.clear()
    CONF.clear()
    PHIEN.clear()
    DA_DANG_XUAT.clear()
    META_FIELDS.clear()
    COT.clear()
    HE_THONG.update({"allow_login_using_mobile_number": 1, "allow_login_using_user_name": 0})
    NGUOI["u"] = "Guest"


def dang_nhap(user):
    NGUOI["u"] = user
    if user and user != "Guest":
        PHIEN[user] = PHIEN.get(user, 0) + 1


def _s(v):
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(v, date):
        return v.isoformat()
    return str(v if v is not None else "")


def khop(h, f):
    if isinstance(f, (list, tuple)):
        f = {c[-3]: (c[-2], c[-1]) for c in f}
    for k, v in (f or {}).items():
        x = h.get(k)
        if isinstance(v, (tuple, list)) and len(v) == 2 and isinstance(v[0], str) and v[0] in (
                "<", "<=", ">", ">=", "!=", "in", "not in", "is", "like", "="):
            op, m = v
            if op == "is":
                if (m == "set") != (x not in (None, "")):
                    return False
            elif op == "in":
                if _s(x) not in [_s(i) for i in m]:
                    return False
            elif op == "not in":
                if _s(x) in [_s(i) for i in m]:
                    return False
            elif op == "like":
                if str(m).strip("%").lower() not in _s(x).lower():
                    return False
            elif op == "!=":
                if _s(x) == _s(m):
                    return False
            elif op == "=":
                if _s(x) != _s(m):
                    return False
            else:
                try:
                    a, b = float(x or 0), float(m)
                except (TypeError, ValueError):
                    a, b = _s(x), _s(m)
                if not {"<": a < b, "<=": a <= b, ">": a > b, ">=": a >= b}[op]:
                    return False
        elif _s(x) != _s(v):
            if not ((x is None or x == "") and _s(v) == "0"):
                return False
    return True


def _sap(ds, order_by):
    for phan in reversed([p.strip() for p in (order_by or "").split(",") if p.strip()]):
        bits = phan.split()
        f = bits[0].split(".")[-1].strip("`")
        lui = len(bits) > 1 and bits[1].lower() == "desc"

        def k(r, f=f):
            v = r.get(f)
            return (0, float(v)) if isinstance(v, (int, float)) else (1, _s(v))
        ds.sort(key=k, reverse=lui)
    return ds


def _kiem_cot(dt, fields):
    if dt not in COT:
        return
    for f in fields or []:
        c = f.split(" as ")[0].strip()
        if c not in COT[dt] and c not in ("name", "docstatus", "modified", "creation", "*"):
            raise Loi(f"(1054, \"Unknown column '{c}' in 'SELECT'\") [{dt}]")


def _has_role_rows():
    out = []
    for u in bang("User").values():
        for r in u.get("roles") or []:
            out.append(Doc(parent=u["name"], parenttype="User", role=r["role"]))
    return out


def get_all(dt, filters=None, fields=None, order_by=None, limit=None, limit_page_length=None, pluck=None,
            or_filters=None, ignore_permissions=None, group_by=None, **k):
    _kiem_cot(dt, fields)
    nguon = _has_role_rows() if dt == "Has Role" else [Doc(copy.deepcopy(x)) for x in bang(dt).values()]
    ds = [x for x in nguon if khop(x, filters)]
    if or_filters:
        ds = [x for x in ds if any(khop(x, {c[-3]: (c[-2], c[-1])}) for c in or_filters)]
    _sap(ds, order_by or "")
    n = limit or limit_page_length
    if n:
        ds = ds[:n]
    if pluck:
        return [x.get(pluck) for x in ds]
    if fields and fields != ["*"]:
        return [Doc({f.split(" as ")[-1].strip(): x.get(f.split(" as ")[0].strip()) for f in fields}) for x in ds]
    return ds


def get_value(dt, ten, fld=None, as_dict=False, **k):
    if isinstance(ten, dict):
        h = next((x for x in bang(dt).values() if khop(x, ten)), None)
    else:
        h = bang(dt).get(ten)
    if h is None:
        return None
    if fld is None:
        fld = "name"
    if isinstance(fld, str):
        return copy.deepcopy(h.get(fld))
    d = Doc({c: copy.deepcopy(h.get(c)) for c in fld})
    return d if as_dict else tuple(d.values())


def exists(dt, ten=None):
    if dt == "DocType":
        return ten if (ten in DB or ten in META_FIELDS) else None
    if isinstance(ten, dict):
        h = next((x for x in bang(dt).values() if khop(x, ten)), None)
        return h["name"] if h else None
    return ten if ten in bang(dt) else None


def set_value(dt, ten, f, v=None, update_modified=True):
    dd = f if isinstance(f, dict) else {f: v}
    if ten not in bang(dt):
        raise DoesNotExistError(f"{dt} {ten}")
    # Ô unique (Employee.ns_tai_khoan) — MariaDB chặn trùng; NULL không tính
    if dt == "Employee" and dd.get("ns_tai_khoan"):
        for n, x in bang(dt).items():
            if n != ten and x.get("ns_tai_khoan") == dd["ns_tai_khoan"]:
                raise Loi("Duplicate entry for key 'ns_tai_khoan'")
    bang(dt)[ten].update(copy.deepcopy(dd))


def table_exists(dt):
    return dt in DB


def has_column(dt, c):
    return c in COT[dt] if dt in COT else True


def get_single_value(dt, f):
    if dt not in META_FIELDS or f not in META_FIELDS[dt]:
        raise DoesNotExistError(f"Field {f} does not exist on {dt}")
    return (DB.get("Singles", {}).get(dt) or {}).get(f)


class Meta:
    def __init__(self, dt):
        self.dt = dt
        self.fields = [Doc(fieldname=f, fieldtype=t, options=o) for f, t, o in
                       (META_CHI_TIET.get(dt) or [])]

    def has_field(self, f):
        return f in META_FIELDS[self.dt] if self.dt in META_FIELDS else True

    def get_field(self, f):
        return next((x for x in self.fields if x.fieldname == f), None)


META_CHI_TIET = {}          # doctype → [(fieldname, fieldtype, options)] — cho meta.fields / get_field


def get_meta(dt):
    return Meta(dt)


def getdate(x=None):
    if isinstance(x, datetime):
        return x.date()
    if isinstance(x, date):
        return x
    return date.fromisoformat(str(x)[:10]) if x else date(2026, 11, 10)


def cint(v):
    try:
        return int(float(v or 0))
    except (TypeError, ValueError):
        return 0


def flt(v, p=None):
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


# ─────────────────────────────────────────────────────────────── Document ──


class Document:
    def __init__(self, dt, d):
        self.__dict__["doctype"] = dt
        self.__dict__["_d"] = Doc(copy.deepcopy(d))
        self.__dict__["flags"] = types.SimpleNamespace(ignore_permissions=False)
        for k, v in list(self._d.items()):
            if isinstance(v, list):
                self._d[k] = [Doc(r) if isinstance(r, dict) else r for r in v]

    def __getattr__(self, k):
        if k == "meta":
            return Meta(self.doctype)
        return self._d.get(k)

    def __setattr__(self, k, v):
        self._d[k] = v

    def get(self, k, default=None):
        v = self._d.get(k)
        return default if v is None else v

    def as_dict(self):
        return Doc(copy.deepcopy(self._d))

    def append(self, f, row):
        self._d.setdefault(f, []).append(Doc(row))

    @property
    def name(self):
        return self._d.get("name")

    # ── vòng đời rút gọn ──
    def _kiem_quyen_ghi(self):
        if not self.flags.ignore_permissions and not ({"System Manager"} & set(get_roles())):
            raise PermissionError(f"Không có quyền ghi {self.doctype}")

    def _tinh_user(self):
        roles = {r["role"] for r in self._d.get("roles") or []}
        self._d["user_type"] = "System User" if any(VAI_DESK.get(r, 1) for r in roles) else "Website User"
        self._d["email"] = self._d.get("email") or self._d.get("name")
        self._d["full_name"] = self._d.get("first_name") or self._d.get("full_name")
        mk = self._d.pop("new_password", None)
        if mk:
            self._d["_mat_khau"] = mk
        if self._d.get("username") and any(
                x.get("username") == self._d["username"] and n != self._d.get("name")
                for n, x in bang("User").items()):
            self._d["username"] = ""          # như User.validate_username của Website User
        if not cint(self._d.get("enabled")):
            PHIEN[self._d["name"]] = 0        # check_enable_disable → login_manager.logout

    def insert(self, ignore_permissions=None):
        if ignore_permissions:
            self.flags.ignore_permissions = True
        self._kiem_quyen_ghi()
        if self.doctype == "User":
            self._d["name"] = self._d["email"]
            if self._d["name"] in bang("User"):
                raise Loi(f"DuplicateEntryError: User {self._d['name']}")
            self._d.setdefault("enabled", 1)
            self._tinh_user()
        elif self.doctype == "Role":
            self._d["name"] = self._d["role_name"]
            if self._d["name"] in bang("Role"):
                raise Loi("DuplicateEntryError: Role")
        else:
            if not self._d.get("name"):
                SO["n"] += 1
                self._d["name"] = f"{self.doctype}-{SO['n']}"
        bang(self.doctype)[self._d["name"]] = copy.deepcopy(dict(self._d))
        return self

    def save(self, ignore_permissions=None):
        if ignore_permissions:
            self.flags.ignore_permissions = True
        self._kiem_quyen_ghi()
        if self.doctype == "User":
            self._tinh_user()
        bang(self.doctype)[self._d["name"]] = copy.deepcopy(dict(self._d))
        return self

    def add_roles(self, *roles):
        cur = {r["role"] for r in self._d.get("roles") or []}
        for r in roles:
            if r not in bang("Role"):
                raise Loi(f"Could not find Role: {r}")
            if r not in cur:
                self.append("roles", {"role": r})
        self.save()

    def remove_roles(self, *roles):
        self._d["roles"] = [r for r in self._d.get("roles") or [] if r["role"] not in roles]
        self.save()


def get_doc(dt, name=None, **k):
    if isinstance(dt, dict):
        d = dict(dt)
        return Document(d.pop("doctype"), d)
    h = bang(dt).get(name)
    if h is None:
        raise DoesNotExistError(f"{dt} {name} not found")
    return Document(dt, h)


def get_roles(user=None):
    user = user or NGUOI["u"]
    if not user or user == "Guest":
        return ["Guest"]
    u = bang("User").get(user) or {}
    return [r["role"] for r in u.get("roles") or []] + ["All", "Guest"]


def throw(msg, exc=None, **k):
    raise (exc or ValidationError)(str(msg))


def clear_sessions(user=None, keep_current=False, force=False):
    PHIEN[user] = 0
    DA_DANG_XUAT.append((user, force))


# ─────────────────────────────────────────────────────────────────── cài ──


def cai():
    """Dựng sys.modules['frappe'] (+ utils, sessions, model.document). Gọi trước khi nạp module ns."""
    fr = types.ModuleType("frappe")
    fr.throw = throw
    fr.whitelist = lambda *a, **k: (lambda f: f)
    fr.PermissionError = PermissionError
    fr.DoesNotExistError = DoesNotExistError
    fr.ValidationError = ValidationError
    fr.Redirect = Redirect
    fr.get_roles = get_roles
    fr.get_all = get_all
    fr.get_list = get_all
    fr.get_doc = get_doc
    fr.get_meta = get_meta
    fr.get_cached_value = lambda dt, ten, f: get_value(dt, ten, f)
    fr.conf = CONF
    fr.get_system_settings = lambda k: HE_THONG.get(k)
    fr.__dict__["_"] = lambda s, *a, **k: s
    class _Phien:
        user = property(lambda self: NGUOI["u"])
    fr.session = _Phien()
    fr.local = types.SimpleNamespace(flags=types.SimpleNamespace(redirect_location=None))
    fr.form_dict = Doc()
    fr.log_error = lambda *a, **k: None
    fr.get_traceback = lambda: ""
    fr.logger = lambda *a, **k: types.SimpleNamespace(info=lambda *a, **k: None)
    fr.db = types.SimpleNamespace(
        get_value=get_value, exists=exists, set_value=set_value, table_exists=table_exists,
        has_column=has_column, get_single_value=get_single_value, commit=lambda: None, rollback=lambda: None)
    fu = types.ModuleType("frappe.utils")
    fu.cint = cint
    fu.flt = flt
    fu.getdate = getdate
    fu.today = lambda: "2026-11-10"
    fu.now = lambda: "2026-11-10 08:00:00.000000"
    fu.get_url = lambda p="": "https://a.example.vn" + (p or "")
    fu.fmt_money = lambda v, precision=0: f"{flt(v):,.0f}"
    fr.utils = fu
    fs = types.ModuleType("frappe.sessions")
    fs.clear_sessions = clear_sessions
    fs.get_csrf_token = lambda: "csrf-test"
    fr.sessions = fs
    sys.modules["frappe"] = fr
    sys.modules["frappe.utils"] = fu
    sys.modules["frappe.sessions"] = fs
    for g in ("ns", "ns.api", "ns.setup", "ns.www"):
        if g not in sys.modules:
            m = types.ModuleType(g)
            m.__path__ = [os.path.join(GOC, *g.split("."))]
            sys.modules[g] = m
    return fr


def nap(ten, duong=None):
    """Nạp module THẬT của app: nap("ns.api.cong_nhan") → ns/api/cong_nhan.py (gói → __init__.py)."""
    if ten in sys.modules and getattr(sys.modules[ten], "__file__", None):
        return sys.modules[ten]
    p = duong or os.path.join(GOC, *ten.split(".")) + ".py"
    if not os.path.exists(p):
        p = os.path.join(GOC, *ten.split("."), "__init__.py")
    sp = importlib.util.spec_from_file_location(ten, p)
    mo = importlib.util.module_from_spec(sp)
    sys.modules[ten] = mo
    sp.loader.exec_module(mo)
    goc, _, la = ten.rpartition(".")
    if goc in sys.modules:
        setattr(sys.modules[goc], la, mo)
    return mo


def nap_ns():
    """Nạp các module ns cần cho phiếu lương / công nhân / tài khoản theo đúng thứ tự import."""
    out = {}
    for t in ("ns.api", "ns.api.common", "ns.api.phieu", "ns.api.phieu_luong", "ns.api.cong_luong",
              "ns.setup.install", "ns.api.cong_nhan", "ns.api.tai_khoan"):
        out[t.split(".")[-1] if t != "ns.api" else "api"] = nap(t)
    return out


# ────────────────────────────────────────────────────────── dữ liệu mẫu ──


def them(dt, name, **kw):
    d = {"name": name, "docstatus": 0, "modified": "2026-11-01 00:00:00"}
    d.update(kw)
    bang(dt)[name] = d
    return d


def them_user(name, roles=(), enabled=1, **kw):
    d = {"name": name, "email": name, "enabled": enabled, "roles": [{"role": r} for r in roles],
         "full_name": kw.pop("full_name", name)}
    d.update(kw)
    d["user_type"] = "System User" if any(VAI_DESK.get(r, 1) for r in roles) else "Website User"
    bang("User")[name] = d
    return d
