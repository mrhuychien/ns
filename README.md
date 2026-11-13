# ns — Quản lý người lao động RVHG (v1)

App Frappe/ERPNext/HRMS v16 cho site `site1.local` (a.rongvanghoanggia.com). Portal SPA tại **`/ns`**
(mobile-first, hash router, không build step) + hook server-side. Spec gốc: `SPEC_ns_v1.md`.

**Công nhân tự xem phiếu lương** tại **`/phieuluong`** (đăng nhập bằng số điện thoại + mật khẩu, chỉ thấy phiếu
**đã duyệt** của chính mình). Phiếu lương trình bày theo thẻ Phiếu lương của app `sx` (D110 + từng ngày D234) — cùng
một component cho phòng nhân sự và công nhân. Xem mục [Phiếu lương](#phiếu-lương-port-từ-app-sx-d110--d234) và
[Công nhân đăng nhập xem phiếu lương](#công-nhân-đăng-nhập-xem-phiếu-lương-phieuluong).

Nguyên tắc: **không đổi schema** `SalaryDay` / `SX Phieu Luong` (chỉ đọc); chỉ thêm field/DocType
prefix `ns_`; mọi quyền kiểm ở server (`ns.api.guard`); tham số lương dùng chung `SX Settings`.

## Cài đặt & deploy

```bash
cd /home/frappe/frappe-bench
bench get-app ns https://github.com/mrhuychien/ns        # hoặc đã có sẵn trong apps/
bench --site site1.local install-app ns
bench --site site1.local migrate                          # Custom Field ns_* trên Employee + 2 DocType + role NS Cong Nhan
bench build --app ns                                      # đẩy public/ns ra /assets/ns/ns
bench restart
bench --site site1.local execute ns.setup.backfill.run    # backfill 1 lần (idempotent; thêm --kwargs "{'dry_run':1}" để xem trước)
```

Công nhân đăng nhập bằng **số điện thoại** → site phải bật một lần (Desk → System Settings → Login):
**Allow Login using Mobile Number** (hoặc *Allow Login using User Name*). Màn `#/tai-khoan` báo đỏ khi chưa bật.

Nghiệm thu nhanh: mở `https://a.rongvanghoanggia.com/ns` bằng user có role **HR User** → 4 tab đếm đúng
(Đóng BHXH ≈ 48 · Không đóng ≈ 30 · Tạm nghỉ 18 · Đã nghỉ 6). User chỉ có role `Employee` → trang
"Không có quyền"; gọi thẳng API → `PermissionError`. Guest → chuyển về `/login?redirect-to=/ns`.

Nghiệm thu phiếu lương công nhân: HR Manager vào `/ns#/tai-khoan` → **＋ Tạo tài khoản** cho 1 công nhân → **In thẻ**
→ quét QR bằng điện thoại. Máy đang đăng nhập tài khoản phòng nhân sự thì thấy phiếu của chủ thẻ ở chế độ *xem như
công nhân* → bấm **Đăng xuất để thử đăng nhập bằng thẻ** → đăng nhập SĐT + mật khẩu trên thẻ → quay lại đúng thẻ, thấy
phiếu đã duyệt của người đó, không có tháng còn nháp; sửa địa chỉ thành `/phieuluong?nv=<mã người khác>` → vẫn chỉ là
phiếu của mình.

## Cấu trúc

```
ns/
  hooks.py                 doc_events Employee (validate/after_insert/on_update) · SalaryDay.validate (P1) · fixtures Custom Field ns_*
                           · add_to_apps_screen (ô "Nhân sự" trên màn Apps của Desk)
  desktop_icon/ns.json     icon NS trên trang chủ Desk kiểu lưới icon (migrate nạp; CHỈ tệp .json trong thư mục này)
  ns/workspace/ns/ns.json  trang chủ app trên Desk /desk/ns (workspace "NS", tiêu đề "Nhân sự")
  patches/them_icon_ns_vao_bo_cuc.py   thêm icon NS vào bố cục lưới đã lưu của người có quyền (chạy một lần)
  public/images/ns-logo.svg            logo NS (ô màn Apps + icon)
  api/                     mọi @frappe.whitelist(), dòng đầu guard()
    __init__.py            guard() / guard_quan_ly() — HR User | HR Manager | System Manager
    common.py              hằng số, whitelist field §4.1.1, validate, helper đọc Employee
    phieu.py               đọc MỀM SalaryDay / SX Phieu Luong (table_exists / has_column)
    canh_bao.py            §6 cảnh báo (dùng chung danh sách / hồ sơ / việc)
    phieu_luong.py         view model phiếu lương (port thẻ sx D110 + D234) cho SalaryDay + SX Phieu Luong · xem (HR)
    cong_nhan.py           công nhân tự xem: cac_thang · phieu — nhân viên suy từ phiên đăng nhập (ns_tai_khoan)
    tai_khoan.py           tài khoản xem lương: danh_sach · cua_nv · tao · cap_lai · khoa · go
    nhan_vien.py           danh_sach · chi_tiet · luu · tao
    su_kien.py · lich_su.py · cong_luong.py · luong.py · viec.py · bo_sung.py
  events/employee.py       đồng bộ ns_dong_bhxh ← custom_bảo_hiểm; sự kiện tự động (khoa_tu_dong idempotent)
  salaryday.py             P1: tinh_lai (port y nguyên Client Script) · validate_hook · doi_chieu
  setup/backfill.py        §3.5
  setup/install.py         dam_bao_role: tạo role NS Cong Nhan nếu thiếu (after_install / after_migrate)
  ns/doctype/ns_giay_to    bảng con Giấy tờ (Employee.ns_giay_to)
  ns/doctype/ns_su_kien    sự kiện timeline, NSSK-.#####
  fixtures/custom_field.json   11 Custom Field ns_* trên Employee (insert_after vn_province) — gồm ns_tai_khoan
  www/ns.py · www/ns.html  context bridge NS_CONTEXT + import map (cache-bust) + build handshake
  www/phieuluong.py/.html  trang công nhân /phieuluong (Guest → /login?redirect-to=/phieuluong)
  public/ns/               shell.js · shell.css · lib/ · components/ · views/{danh_sach,ho_so,bo_sung,luong,viec,tai_khoan}.js
    cong_nhan.js           trang /phieuluong (BUILD khớp SHELL_BUILD của www/phieuluong.py)
    components/phieu_luong.js  HTML phiếu lương dùng chung (HR + công nhân)
    components/tai_khoan.js    tạo / cấp lại / khoá / gỡ / tạo hàng loạt + hiện mật khẩu một lần
    lib/inthe.js · vendor/qrcode.js   in thẻ đăng nhập (QR SVG, MIT — chép từ app sx)
scripts/                   verify.sh · fakefrappe.py · server-thu.py · test-*.py · test-giaodien.mjs (xem "Kiểm trước khi ship")
```

## Màn hình (`/ns`)

| Route | Nội dung |
|---|---|
| `#/` | Danh sách NLĐ: 4 tab, chip bộ phận (+ "Chưa có bộ phận"), tìm tên/CCCD/mã máy/mã NV, cảnh báo, % hồ sơ, **+ Thêm người** |
| `#/nv/:name` | Hồ sơ: Thông tin (4 nhóm, sửa trực tiếp) · Giấy tờ (badge hết hạn/≤30 ngày, upload) · Lịch sử (timeline + thêm sự kiện) · Công & lương (phiếu lương kiểu sx: các khoản, sản phẩm, từng ngày; ô 🔑 tài khoản xem lương; In / Mở ERPNext) |
| `#/bo-sung?bp=` | Tiến độ hồ sơ, chip đếm thiếu theo field, lưới NV × field sửa inline (Enter/blur lưu, Tab sang ô thiếu kế), Tải mẫu / Nhập Excel (xem diff → áp dụng) |
| `#/luong?t=&n=&loai=` | Bảng lương tháng nhật/khoán, dòng tổng, đỏ thiếu phiếu · cam trùng · xám nháp, Xuất Excel, Danh sách chuyển khoản; **🧾 Xem** mỗi dòng → phiếu đầy đủ (modal) |
| `#/viec` | Việc cần làm theo nhóm §6; là trang mặc định khi có việc đỏ |
| `#/tai-khoan` | Tài khoản xem lương: ai có / chưa, tạo (từng người / hàng loạt), cấp lại mật khẩu, khoá, gỡ, in thẻ, 👁 xem như công nhân. Desktop: mục trên thanh điều hướng; điện thoại: menu 👤 và nút trên màn Lương |
| `#/chamcong` | → `/chamcong2` |
| **`/phieuluong`** | **Trang công nhân** (ngoài `/ns`): chọn tháng ‹ ›, phiếu lương của chính mình; 👤 → Đổi mật khẩu / Đăng xuất |

Sau khi sửa code: `bench build --app ns && bench restart`, refresh trình duyệt là đủ (import map lo
cache shared module). Mỗi lần đổi route/shell: tăng `BUILD` trong `public/ns/shell.js` **và**
`SHELL_BUILD` trong `www/ns.py` (lệch → banner đỏ "bản cũ do cache"). Trang `/phieuluong` có cặp riêng: `BUILD` trong
`public/ns/cong_nhan.js` ↔ `SHELL_BUILD` trong `www/phieuluong.py`. Thêm module dùng chung mới → thêm vào import map
của trang dùng nó (`scripts/test-importmap.py` bắt thiếu).

## P1 — tính lại `SalaryDay` phía server (§7)

Hook `SalaryDay.validate → ns.salaryday.validate_hook` **đã đăng ký nhưng TẮT mặc định**: chỉ chạy khi
`site_config.json` có `ns_tinh_lai_salaryday = 1`. Quy trình bật:

```bash
# 1) Đối chiếu từng tháng (không ghi gì, chỉ in bảng lệch)
bench --site site1.local execute ns.salaryday.doi_chieu --kwargs "{'thang':6,'nam':2026}"
bench --site site1.local execute ns.salaryday.doi_chieu --kwargs "{'thang':7,'nam':2026}"
bench --site site1.local execute ns.salaryday.doi_chieu --kwargs "{'thang':8,'nam':2026}"
bench --site site1.local execute ns.salaryday.doi_chieu --kwargs "{'thang':9,'nam':2026}"
# 2) CHỈ khi lệch = 0 trên mọi phiếu (phiếu tinhthuongthamnien=1 chỉ lệch đúng phần thâm niên
#    được liệt kê riêng để kiểm) → bật:
bench --site site1.local set-config ns_tinh_lai_salaryday 1
bench restart
# 3) Client Script SalaryDay giữ chạy song song 1 tháng, rồi mới disable.
```

Có lệch khác → **không tự sửa công thức**, gửi lại bảng lệch. Công thức port y nguyên Client Script
(kể cả ngoại lệ `HR-EMP-00035`, `HR-EMP-00045`, Bình Dương, tháng 2); tham số đọc `SX Settings` qua
`sx.utils.get_settings()` với fallback đúng giá trị JS. Khác biệt duy nhất: thâm niên tính đồng bộ
(JS cần Save 2 lần) — số cuối cùng giống nhau.

## Phiếu lương (port từ app sx: D110 + D234)

Một view model (`ns/api/phieu_luong.py`) + một component (`components/phieu_luong.js`) cho cả hai nguồn lương, dùng
ở tab **Công & lương** của hồ sơ, nút **🧾 Xem** của bảng lương và trang công nhân — HR và công nhân nhìn đúng một con số.
Thứ tự như phiếu giấy (thẻ Phiếu lương của sx):

- **Thực nhận** (to) · ngày công / ngày SX (+ làm thêm, lương cơ bản với công nhật).
- **Các khoản** → **Tổng thu nhập** → trừ (tiền phạt, bảo hiểm) → **Thực nhận**; chỉ hiện khoản khác 0. Công nhật thêm
  dòng *Trong đó chuyển khoản* (`luongck`).
- **Sản phẩm trong tháng** (khoán): gộp theo mã + cách làm + đơn giá; làm theo giờ mỗi mức một dòng (số GIỜ × đơn giá).
- **Từng ngày** (khoán, D234): bảng *Sản phẩm · SL · Đơn giá · Thành tiền*, mỗi ngày một nhóm — đầu ngày (thứ, chấm ăn),
  sản phẩm của ngày (giữ thứ tự ghi, làm theo giờ xuống cuối, giá cao trước), **Cộng ngày** = thu nhập ngày của phiếu,
  có hệ số / tiền ăn thì ghi phép tính (`lương SP 214.500 × 1,2 + tiền ăn 20.000`). Dòng chưa có giá ghi **⚠ chưa có giá**.
- **Chấm công từng ngày** (công nhật): ngày · thứ (Chủ nhật tô nền) · công · thêm giờ — số gốc của bảng chấm công.
- **Lỗi phạt** (lý do, số lượng × giá) · ghi chú.

Nguyên tắc giữ từ sx: **mọi số tiền lấy nguyên từ phiếu** (controller sx / Client Script SalaryDay đã tính) — ns chỉ
gộp dòng để trình bày, không tính lại. Đọc mềm: site thiếu app sx / thiếu cột → không vỡ. Bảng vừa màn 360px (không
kéo ngang), đầu cột dính khi cuộn (cả trong modal). Lý do phạt của SalaryDay đọc mềm (ô `loi`/`noidung`/… rồi ô chữ
đầu tiên của bảng con); phạt của khoán đọc đúng ô `ly_do` (bản trước đọc nhầm `noi_dung` → rỗng).

## Công nhân đăng nhập xem phiếu lương (`/phieuluong`)

**Quy trình HR:** `/ns#/tai-khoan` (HR Manager) → chọn người → **＋ Tạo tài khoản** (SĐT lấy từ hồ sơ, sửa được) hoặc
tích nhiều người → **Tạo tài khoản cho người đã chọn** → **🖨️ In thẻ** (tên, mã NV, QR mở `/phieuluong`, SĐT, mật khẩu)
→ đưa tận tay. Mật khẩu **chỉ hiện một lần**; mất thẻ / quên → **Cấp lại mật khẩu** (mật khẩu mới + đăng xuất mọi máy).
Công nhân quét QR → đăng nhập SĐT + mật khẩu → vào thẳng phiếu lương; 👤 → Đổi mật khẩu (`/update-password`).

**Thiết kế (kiểm ở server, test trong `scripts/`):**

| | |
|---|---|
| Gắn tài khoản ↔ hồ sơ | Custom Field **`Employee.ns_tai_khoan`** (Link User, unique, chỉ đọc trên Desk; cấp / gỡ ở `#/tai-khoan`). **Không dùng `Employee.user_id`**: ERPNext gắn user_id thì mỗi lần lưu hồ sơ tự cấp role `Employee` — role đang có quyền **ghi SalaryDay** (§8) và vào Desk |
| Role **`NS Cong Nhan`** | Không vào Desk → Website User; `home_page = phieuluong` (đăng nhập xong vào thẳng phiếu). Tạo khi thiếu ở after_install / after_migrate, **không sửa role đã có** (không ship qua fixtures — bài học sx D105). Quyền xem lương **không** dựa vào role mà dựa vào liên kết |
| Tài khoản | username = mobile_no = SĐT chuẩn hoá `0xxxxxxxxx`; email giả `{SĐT}@{tên miền}` — tên miền: `site_config ns_ten_mien_user` → `SX Settings.ten_mien_user` (cùng tài khoản app sx cấp) → `sx.local`/`ns.local`. Mật khẩu 8 ký tự đọc được (bỏ 0 O o 1 l I i) |
| SĐT đã có tài khoản | Không tự gắn: hiện tên chủ tài khoản, HR xác nhận mới gắn (SĐT gõ nhầm = lộ lương cho người khác). Tài khoản có Desk thì không thêm role (role có home_page sẽ kéo cả người dùng Desk sang `/phieuluong`) |
| Tài khoản dùng chung | (QC có tài khoản sx, văn phòng có Desk) chỉ **Gắn / Gỡ**; cấp lại mật khẩu / khoá chỉ với tài khoản riêng của app (mọi role ⊆ {NS Cong Nhan}) — không bao giờ đụng Administrator / tài khoản khác |
| Công nhân thấy gì | Chỉ hồ sơ gắn với **phiên đăng nhập** (trình duyệt không gửi mã nhân viên); tài khoản khoá / chưa gắn → chặn. Mặc định chỉ phiếu **đã duyệt**; phiếu huỷ không bao giờ |
| Xem phiếu nháp (tuỳ chọn) | `bench --site site1.local set-config ns_cong_nhan_xem_nhap 1` → hiện thêm phiếu nháp, ghi **Tạm tính**. SalaryDay nháp chỉ hiện khi P1 đã bật (`ns_tinh_lai_salaryday = 1`) — trước P1 số nháp chỉ đúng sau khi kế toán Save trên Desk |
| Xem như công nhân | HR (HR User trở lên) mở `/phieuluong?nv=<mã NV>` (nút 👁 ở `#/tai-khoan` và hồ sơ) hoặc quét thẻ — thấy màn công nhân đang thấy **và cả phiếu tạm tính** (chưa duyệt, như ở `/ns`): tháng tạm tính ghi *Tạm tính T12/2026*, phiếu ghi rõ **"Công nhân chưa thấy phiếu này — chỉ hiện với công nhân sau khi duyệt"** (trừ khi đã bật cho công nhân xem nháp). Người không phải HR thêm `?nv=` thì bị bỏ qua |
| Quyền màn Tài khoản | Xem: HR User / HR Manager / System Manager. Tạo / cấp lại / khoá / gỡ: **HR Manager / System Manager** |
| Gỡ | Hết xem lương ngay; tài khoản riêng bị khoá luôn (không để tài khoản mồ côi), tài khoản dùng chung chỉ bỏ role NS |

QR trên thẻ chứa **địa chỉ trang + mã NV chủ thẻ** — `/phieuluong?the=<mã NV>` (không phải mã đăng nhập một lần như
thẻ QC của sx; chữ in trên thẻ vẫn là địa chỉ ngắn `…/phieuluong` để gõ tay). Người nhặt được thẻ vẫn cần mật khẩu,
nhưng mật khẩu in ngay trên thẻ nên vẫn dặn giữ thẻ như chìa khoá. HR cấp lại mật khẩu thì Frappe gửi thông báo "mật
khẩu đã đổi" tới email giả (không ai nhận) — đúng như tài khoản sx.

**Quét thẻ khi điện thoại đang đăng nhập sẵn** (Safari giữ phiên — hay gặp khi phòng nhân sự quét thử thẻ trên máy
mình; trước bản này ra "Tài khoản chưa gắn với hồ sơ nhân viên"):

| Đang đăng nhập bằng | Quét thẻ của X thì thấy |
|---|---|
| chưa đăng nhập | trang đăng nhập → đăng nhập xong **quay lại đúng thẻ** (`redirect-to` giữ `?the=`) |
| chính X | phiếu lương của X |
| tài khoản phòng nhân sự | phiếu của X ở chế độ **xem như công nhân** — có cả phiếu tạm tính — + thanh "Thẻ của X…" + nút **Đăng xuất để thử đăng nhập bằng thẻ** |
| người khác (không phải HR) | "Thẻ này không phải của tài khoản đang đăng nhập" + tên tài khoản đang đăng nhập + nút **Đăng xuất để đăng nhập bằng thẻ này** — không tải phiếu nào, không nói thẻ của ai (mã trên địa chỉ ai cũng gõ được) |

Thẻ in trước bản này (QR là `/phieuluong` trơn) vẫn dùng bình thường trên máy công nhân; quét trên máy đang đăng nhập
tài khoản khác thì màn báo ghi rõ **đang đăng nhập bằng tài khoản nào** kèm nút đăng xuất — không cần in lại.

## Icon NS ngoài trang chủ Desk

Trang chủ Desk (`/desk`) có icon **NS** (logo xanh) cạnh icon SX; màn Apps có ô **Nhân sự**. Bấm vào → trang chủ app
trên Desk **`/desk/ns`** (workspace "NS", tiêu đề "Nhân sự"):

- Lối tắt: **Mở trang Nhân sự** (`/ns`) · Việc cần làm · Bảng lương tháng · Bổ sung hồ sơ · Tài khoản xem lương ·
  Trang phiếu lương công nhân (`/phieuluong`) · Nhân viên · Sự kiện nhân sự.
- Tất cả chức năng: *Hồ sơ nhân sự* (Nhân viên, Sự kiện nhân sự) · *Danh mục* (Bộ phận, Chức danh). Chỉ link DocType
  chắc chắn có trên site (của ns / ERPNext) — link tới DocType không có làm Administrator mất sạch các card.
- **Ai thấy**: người dùng Desk có vai HR User / HR Manager / System Manager, và Administrator
  (`ns.api.co_quyen_app_desk`, một nguồn với guard của API). Công nhân (Website User) không thấy — họ vào `/phieuluong`.

Làm đủ ba lớp như app sx đã phải làm qua ba lần (D236 → D237 → D238) trên chính site này (Frappe 16.16.0):

| Lớp | Vì sao cần |
|---|---|
| `add_to_apps_screen` trong hooks.py — route `/desk/ns`, `has_permission` | Màn Apps đọc hook này lúc chạy; route `/desk/…` khớp mẫu Desk của v16 nên đăng nhập vẫn vào `/desk` (route ngoài Desk như `/ns` làm Frappe đẩy người dùng ra màn chọn app). Lưới icon cũng lấy quyền icon App từ `has_permission` này. Không khai `app_logo_url` (sẽ đổi logo thanh điều hướng của cả Desk) |
| `ns/desktop_icon/ns.json` (Desktop Icon loại App, nhãn = `app_title` "NS") | Lưới icon chỉ tự tạo icon **lúc cài app** — app đã cài thì phải ship tệp icon, migrate nạp. Tên tệp đúng `scrub(tên).json`, không thì bộ dọn icon thừa của Frappe xoá icon ở lần migrate sau |
| Patch `ns.patches.them_icon_ns_vao_bo_cuc` (post_model_sync, chạy một lần) | Frappe 16.16 vẽ trang chủ theo **bố cục đã lưu** của từng người (ai từng kéo thả lưới) và không tự thêm icon chuẩn mới vào đó. Patch thêm icon NS vào **cuối** bố cục của người có quyền, giữ nguyên sắp xếp cũ; người không có quyền không đụng |

**Cập nhật**: `git pull` → `bench --site site1.local migrate` → `bench restart` → tải lại Desk (Ctrl+Shift+R).
Vẫn không thấy icon (vd. người tạo bố cục sau khi patch đã chạy): ở trang chủ Desk bấm ảnh đại diện →
**Reset Desktop Layout** (mất sắp xếp riêng, lưới về mặc định có icon NS) — hoặc thêm icon NS vào lưới bằng tay.
Sửa bố cục workspace trên site (kéo thả, thêm khối) thì Frappe lưu bản tuỳ biến riêng, cập nhật app không mất.

## Việc làm tay trên Desk (§8 — ngoài code)

- [ ] **Đã duyệt:** `SalaryDay` → Role Permission Manager → xoá dòng role `Employee` (đang `write = 1`). Làm ngay.
- [ ] 3 `SalaryDay` có month=0/year=0 → xoá.
- [ ] Web Page `chamcong` (cũ) → unpublish. Web Page `chamcong2` → thêm link "← Nhân sự" về `/ns`.
- [ ] 14 user có `HR Manager` → rà lại.
- [ ] `SX Phieu Luong.bao_hiem` nhập tay → cân nhắc `fetch_from Employee.custom_bảo_hiểm` + `fetch_if_empty` (sửa trong app `sx`).
- [ ] **System Settings → Allow Login using Mobile Number** (cho công nhân đăng nhập bằng SĐT) — nếu chưa bật.
- [ ] Sau `migrate`: kiểm role **NS Cong Nhan** có *Home Page* = `phieuluong`, *Desk Access* tắt (Desk → Role).

## Kiểm trước khi ship (đã chạy 0 ERROR)

```bash
bash scripts/verify.sh        # → VERIFY-OK
```

Gồm: `py_compile` + `node --check`; validator của skill nextcode-build (`validate_fixtures`, `validate_shipped_docs`,
`check_doctype_json`, `lint_patches`); `test-importmap.py` (import map của `/ns` và `/phieuluong` là JSON hợp lệ và
phủ đủ module dùng chung — Luật vàng #1; BUILD khớp — Luật vàng #2); `test-phieuluong.py` (view model: gộp sản phẩm,
từng ngày, giờ, chưa có giá, Σ khoản = tổng thu nhập, quyền), `test-congnhan.py` (rò rỉ: Guest / chưa gắn / bị khoá /
truyền mã người khác, chỉ phiếu đã duyệt, cờ xem nháp + P1, xem như công nhân), `test-taikhoan.py` (tạo theo SĐT,
xác nhận gắn tài khoản sẵn có, không đụng tài khoản dùng chung / Administrator, khoá → đăng xuất, gỡ);
`test-desk.py` (workspace nạp được — đúng chỗ, content ↔ card / shortcut, link chỉ tới DocType chắc có, URL trỏ màn
có thật; ô màn Apps — route khớp mẫu Desk, logo SVG, has_permission, không app_logo_url; icon — thư mục chỉ .json, tên
tệp = scrub(tên), nhãn = app_title, link = route; ai thấy; patch bố cục đã lưu — chỉ người có quyền, cuối hàng, giữ thứ
tự, ASCII, chạy lại không ghi); `test-giaodien.mjs` — Chromium thật ở màn 360px, chạy **API Python thật** trên Frappe giả (`scripts/server-thu.py`),
trang dựng từ chính `www/*.html`: bảng từng ngày đúng cột (port test D234 của sx), không kéo ngang, đầu cột dính,
không chèn HTML, chọn tháng / tải lại giữ tháng, trình duyệt không gửi mã nhân viên, đăng xuất, màn Tài khoản (tạo hàng
loạt, in thẻ có QR, HR User không thấy nút sửa), modal Xem phiếu, hồ sơ → Công & lương. `NS_SHOT=<thư mục>` để chụp ảnh.

## Không làm v1 / v1.1

Tuyển dụng, đánh giá, đào tạo, nghỉ phép/ESS, báo tăng-giảm BHXH, thuế TNCN, báo cáo pháp định, in HĐ,
sửa `SX Phieu Luong`, port lại `/chamcong2`. **v1.1** (sau khi P1 ổn): sửa inline phiếu nháp trên lưới
lương (`ngaysanxuat` hàng loạt, `thuongkhac`, `ancatoi`).
