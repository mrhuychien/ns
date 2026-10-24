# ns — Quản lý người lao động RVHG (v1)

App Frappe/ERPNext/HRMS v16 cho site `site1.local` (a.rongvanghoanggia.com). Portal SPA tại **`/ns`**
(mobile-first, hash router, không build step) + hook server-side. Spec gốc: `SPEC_ns_v1.md`.

Nguyên tắc: **không đổi schema** `SalaryDay` / `SX Phieu Luong` (chỉ đọc); chỉ thêm field/DocType
prefix `ns_`; mọi quyền kiểm ở server (`ns.api.guard`); tham số lương dùng chung `SX Settings`.

## Cài đặt & deploy

```bash
cd /home/frappe/frappe-bench
bench get-app ns https://github.com/mrhuychien/ns        # hoặc đã có sẵn trong apps/
bench --site site1.local install-app ns
bench --site site1.local migrate                          # Custom Field ns_* trên Employee + 2 DocType
bench build --app ns                                      # đẩy public/ns ra /assets/ns/ns
bench restart
bench --site site1.local execute ns.setup.backfill.run    # backfill 1 lần (idempotent; thêm --kwargs "{'dry_run':1}" để xem trước)
```

Nghiệm thu nhanh: mở `https://a.rongvanghoanggia.com/ns` bằng user có role **HR User** → 4 tab đếm đúng
(Đóng BHXH ≈ 48 · Không đóng ≈ 30 · Tạm nghỉ 18 · Đã nghỉ 6). User chỉ có role `Employee` → trang
"Không có quyền"; gọi thẳng API → `PermissionError`. Guest → chuyển về `/login?redirect-to=/ns`.

## Cấu trúc

```
ns/
  hooks.py                 doc_events Employee (validate/after_insert/on_update) · SalaryDay.validate (P1) · fixtures Custom Field ns_*
  api/                     mọi @frappe.whitelist(), dòng đầu guard()
    __init__.py            guard() / guard_quan_ly() — HR User | HR Manager | System Manager
    common.py              hằng số, whitelist field §4.1.1, validate, helper đọc Employee
    phieu.py               đọc MỀM SalaryDay / SX Phieu Luong (table_exists / has_column)
    canh_bao.py            §6 cảnh báo (dùng chung danh sách / hồ sơ / việc)
    nhan_vien.py           danh_sach · chi_tiet · luu · tao
    su_kien.py · lich_su.py · cong_luong.py · luong.py · viec.py · bo_sung.py
  events/employee.py       đồng bộ ns_dong_bhxh ← custom_bảo_hiểm; sự kiện tự động (khoa_tu_dong idempotent)
  salaryday.py             P1: tinh_lai (port y nguyên Client Script) · validate_hook · doi_chieu
  setup/backfill.py        §3.5
  ns/doctype/ns_giay_to    bảng con Giấy tờ (Employee.ns_giay_to)
  ns/doctype/ns_su_kien    sự kiện timeline, NSSK-.#####
  fixtures/custom_field.json   9 Custom Field ns_* trên Employee (insert_after vn_province)
  www/ns.py · www/ns.html  context bridge NS_CONTEXT + import map (cache-bust) + build handshake
  public/ns/               shell.js · shell.css · lib/ · components/ · views/{danh_sach,ho_so,bo_sung,luong,viec}.js
```

## Màn hình (`/ns`)

| Route | Nội dung |
|---|---|
| `#/` | Danh sách NLĐ: 4 tab, chip bộ phận (+ "Chưa có bộ phận"), tìm tên/CCCD/mã máy/mã NV, cảnh báo, % hồ sơ, **+ Thêm người** |
| `#/nv/:name` | Hồ sơ: Thông tin (4 nhóm, sửa trực tiếp) · Giấy tờ (badge hết hạn/≤30 ngày, upload) · Lịch sử (timeline + thêm sự kiện) · Công & lương (chỉ đọc, In / Mở ERPNext) |
| `#/bo-sung?bp=` | Tiến độ hồ sơ, chip đếm thiếu theo field, lưới NV × field sửa inline (Enter/blur lưu, Tab sang ô thiếu kế), Tải mẫu / Nhập Excel (xem diff → áp dụng) |
| `#/luong?t=&n=&loai=` | Bảng lương tháng nhật/khoán, dòng tổng, đỏ thiếu phiếu · cam trùng · xám nháp, Xuất Excel, Danh sách chuyển khoản |
| `#/viec` | Việc cần làm theo nhóm §6; là trang mặc định khi có việc đỏ |
| `#/chamcong` | → `/chamcong2` |

Sau khi sửa code: `bench build --app ns && bench restart`, refresh trình duyệt là đủ (import map lo
cache shared module). Mỗi lần đổi route/shell: tăng `BUILD` trong `public/ns/shell.js` **và**
`SHELL_BUILD` trong `www/ns.py` (lệch → banner đỏ "bản cũ do cache").

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

## Việc làm tay trên Desk (§8 — ngoài code)

- [ ] **Đã duyệt:** `SalaryDay` → Role Permission Manager → xoá dòng role `Employee` (đang `write = 1`). Làm ngay.
- [ ] 3 `SalaryDay` có month=0/year=0 → xoá.
- [ ] Web Page `chamcong` (cũ) → unpublish. Web Page `chamcong2` → thêm link "← Nhân sự" về `/ns`.
- [ ] 14 user có `HR Manager` → rà lại.
- [ ] `SX Phieu Luong.bao_hiem` nhập tay → cân nhắc `fetch_from Employee.custom_bảo_hiểm` + `fetch_if_empty` (sửa trong app `sx`).

## Kiểm trước khi ship (đã chạy 0 ERROR)

```bash
R=~/.claude/skills/nextcode-build/references
python3 $R/validate_fixtures.py ns && python3 $R/validate_shipped_docs.py ns
python3 $R/check_doctype_json.py ns/ns/doctype && python3 $R/lint_patches.py ns
python3 -m py_compile $(find ns -name '*.py'); for f in ns/public/ns/**/*.js ns/public/ns/*.js; do node --check "$f"; done
```

## Không làm v1 / v1.1

Tuyển dụng, đánh giá, đào tạo, nghỉ phép/ESS, báo tăng-giảm BHXH, thuế TNCN, báo cáo pháp định, in HĐ,
sửa `SX Phieu Luong`, port lại `/chamcong2`. **v1.1** (sau khi P1 ổn): sửa inline phiếu nháp trên lưới
lương (`ngaysanxuat` hàng loạt, `thuongkhac`, `ancatoi`).
