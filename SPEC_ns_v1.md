# SPEC — app `ns` · Quản lý người lao động RVHG (v1)

Ngày: 24/10/2026 · Site `site1.local` (a.rongvanghoanggia.com) · bench `/home/frappe/frappe-bench` · Frappe/ERPNext/HRMS v16 (Frappe 16.16.0, Python 3.14)
Skill dùng: `frappe-portal-spa` (trình duyệt), `nextcode-build` (DocType/fixtures/hooks), `frappe-app-shipping-gotchas` (cài & deploy).
Nguồn sự thật: `ns_dump.json` (meta + controller + thống kê, dump 24/10/2026). Mọi fieldname dưới đây lấy nguyên từ dump — KHÔNG đặt lại.

---

## 0. Bối cảnh & nguyên tắc

- RVHG **không dùng Salary Slip của HRMS**. Hai nguồn lương:
  - **Công nhật** → DocType `SalaryDay` (custom DocType trong DB, module Projects, submittable, 1 phiếu/người/tháng, naming `PLC`). Công thức tính nằm **100% trong Client Script `SalaryDay`** (chạy khi save trên Desk form).
  - **Công khoán** → DocType `SX Phieu Luong` (app `sx`, tính server-side lúc validate, naming `PL-{nam}-{thang}-{employee}`). Khoán = Employee thuộc Department `Công khoán - HGC`.
- Chấm công tay + đối chiếu máy Hikvision = **Web Page route `/chamcong2`** (bản ghi trong DB, không nằm trong app nào). Nó ghi `SalaryDay.chamcong` qua `frappe.client.save` / `frappe.client.insert`.
- App `ns` **không đổi schema** của `SalaryDay`, `SX Phieu Luong`, bảng con của chúng. Chỉ đọc. App chỉ thêm field/DocType của riêng mình, prefix `ns_`, fieldname ASCII không dấu.
- Mọi quyền kiểm ở server (guard trong từng whitelisted method). Ẩn nút ở client chỉ là tiện dụng.
- Không hardcode tham số nghiệp vụ mới. Tham số lương hiện hữu (ăn ca, chuyên cần, ngày công chuẩn…) đã có trong `SX Settings` — dùng chung, không tạo bản sao.

## 1. Hiện trạng dữ liệu (từ dump)

- 102 Employee: **78 Active** (Công khoán 27, Công nhật 24, Văn phòng 10, Bình Dương 5, Showroom 3, **chưa có bộ phận 9**), **18 Inactive** (toàn Công khoán — thời vụ), **6 Left** (Công nhật). Branch, Employment Type: trống hoàn toàn.
- Trong 78 Active: `custom_bảo_hiểm` > 0: **48** (= 48 người đóng BHXH, 30 không); `custom_cccd`: 38; `custom_lương_cơ_bản` > 0: 42; `attendance_device_id`: 29; `bank_ac_no`: 62; `custom_lương_tài_khoản` > 0: 17.
- Trống hoàn toàn (chưa ai dùng): `vn_contract_type`, `vn_tax_code`, `vn_number_of_dependents`, `vn_insurance_salary`, `contract_end_date`, `health_insurance_no`, `Employee Internal Work History`, `Employee Education`. Các field `vn_*` do app `erpnextvn` tạo (module "ERPNext Vietnam") — có sẵn, tái dùng.
- `SalaryDay`: dữ liệu từ 05/2026, 30–36 phiếu submitted/tháng, 10/2026 đang 40 nháp. Có 1 nháp + 2 huỷ với month=0/year=0 (rác). Print Format có sẵn: `Phiếu lương công nhật`.
- `SX Phieu Luong`: mới từ 10/2026 (23 nháp). Trước đó lương khoán ở DocType `SalaryProduct` (app lam-luong cũ, có thể còn trong DB) — xem §3.5.
- Web Page: `chamcong2` (đang dùng), `chamcong` (cũ).
- Role đang có trên site: `HR User`, `HR Manager` (14 user), `Ke Toan Tien Luong`, `Ke Toan Truong`, `SX Quan Ly`.

## 2. Phạm vi v1

**Làm:** app `ns`, route `/ns`, portal SPA (kiến trúc giống app bc/pkd theo skill `frappe-portal-spa`), 5 màn + 1 link, và hook tính lương server-side:
1. Danh sách NLĐ (4 tab: Đóng BHXH / Không đóng BHXH / Tạm nghỉ / Đã nghỉ)
2. Hồ sơ 1 người (Thông tin · Giấy tờ · Lịch sử · Công & lương)
3. Bổ sung thông tin còn thiếu (lưới điền nhanh + nhập/xuất Excel) — §5 `#/bo-sung`
4. Bảng lương tháng (công nhật + khoán, chỉ đọc, xuất Excel, danh sách chuyển khoản)
5. Việc cần làm
6. Chấm công → link sang `/chamcong2`
7. **P1 — tính lại `SalaryDay` phía server** (§7, đã duyệt, làm thành commit riêng sau khi 5 màn chạy)

Thứ tự commit: (a) data model + backfill → (b) API + SPA 5 màn → (c) P1 hook + script đối chiếu → (d) bật hook.

**Không làm v1:** tuyển dụng, đánh giá, đào tạo, nghỉ phép/ESS, báo tăng-giảm BHXH, thuế TNCN, báo cáo pháp định, in HĐ/quyết định, sửa `SX Phieu Luong`, port lại `/chamcong2`. Sửa phiếu lương nháp trên lưới (đặt `ngaysanxuat` hàng loạt, `thuongkhac`, `ancatoi`) để **v1.1**, chỉ làm sau khi P1 bật ổn.

---

## 3. Mô hình dữ liệu

### 3.1 Custom Field thêm vào `Employee` (fixture của app ns, `insert_after` = `vn_province`)

| fieldname | fieldtype | label | ghi chú |
|---|---|---|---|
| `ns_bhxh_section` | Section Break | BHXH & hồ sơ | |
| `ns_dong_bhxh` | Check | Đóng BHXH | **Cờ chính** cho 2 danh sách. Backfill = `custom_bảo_hiểm > 0`. |
| `ns_so_so_bhxh` | Data | Số sổ BHXH | |
| `ns_bhxh_tu_ngay` | Date | Đóng BHXH từ | |
| `ns_bhxh_den_ngay` | Date | Ngừng đóng từ | rỗng = đang đóng |
| `ns_col_bhxh` | Column Break | | |
| `ns_ly_do_khong_bhxh` | Select | Lý do không đóng BHXH | options: `\nThời vụ dưới 1 tháng\nĐang hưởng lương hưu\nThử việc (HĐ thử việc riêng)\nKhác`; `depends_on: eval:!doc.ns_dong_bhxh` |
| `ns_giay_to_section` | Section Break | Giấy tờ | |
| `ns_giay_to` | Table | Giấy tờ | options `NS Giay To` |

**Quy tắc đồng bộ (hook `Employee.validate`):** nếu `custom_bảo_hiểm > 0` → ép `ns_dong_bhxh = 1`. Cho phép `ns_dong_bhxh = 1` mà bảo hiểm = 0 (mới đăng ký, chưa biết mức trừ) — app hiện cảnh báo "chưa có mức trừ".

**Field có sẵn tái dùng, KHÔNG tạo trùng:** `custom_cccd`, `custom_zalo`, `custom_năm_gia_nhập`, `custom_lương_cơ_bản`, `custom_hỗ_trợ`, `custom_bảo_hiểm` (số tiền BHXH trừ mỗi tháng — SalaryDay fetch về `baohiem`), `custom_lương_tài_khoản` (phần chuyển khoản — SalaryDay fetch về `luongck`), `custom_ăn_ca_tối_tại_công_ty`, `custom_bankowner`, `vn_tax_code`, `vn_number_of_dependents`, `vn_insurance_salary`, `vn_contract_type`, `vn_province`, `contract_end_date`, `attendance_device_id`, `bank_name`, `bank_ac_no`, `salary_mode`, `health_insurance_no` (dùng làm mã thẻ BHYT), `date_of_joining`, `relieving_date`, `reason_for_leaving`, `status`, `cell_number`, `personal_email`, `current_address`, `permanent_address`, `person_to_be_contacted`, `emergency_phone_number`, `relation`, `image`.

Lưu ý kỹ thuật: fieldname có dấu (`custom_lương_cơ_bản`…) dùng được trong Python qua `doc.get("…")`/`frappe.get_all(fields=[…])`; trong SQL thô **bắt buộc backtick**.

### 3.2 DocType `NS Giay To` (istable=1, module NS)

| fieldname | type | label | in_list_view |
|---|---|---|---|
| `loai` | Select | Loại | ✓ — options: `CCCD\nHợp đồng lao động\nPhụ lục HĐLĐ\nGiấy khám sức khỏe\nXác nhận kiến thức ATTP\nSổ BHXH\nBằng cấp / chứng chỉ\nKhác` (reqd) |
| `so` | Data | Số | ✓ |
| `ngay_cap` | Date | Ngày cấp | ✓ |
| `noi_cap` | Data | Nơi cấp | |
| `ngay_het_han` | Date | Hết hạn | ✓ |
| `tep` | Attach | Tệp | |
| `ghi_chu` | Data | Ghi chú | |

### 3.3 DocType `NS Su Kien` (module NS, không submittable, `track_changes=1`)

naming: `naming_series` = `NSSK-.#####`

| fieldname | type | label | ghi chú |
|---|---|---|---|
| `employee` | Link Employee | Nhân viên | reqd, in_list_view |
| `employee_name` | Data | Tên | fetch_from `employee.employee_name`, read_only |
| `ngay` | Date | Ngày | reqd, in_list_view |
| `loai` | Select | Loại | reqd, in_list_view — options: `Vào làm\nKý HĐLĐ\nPhụ lục HĐLĐ\nThay đổi lương\nĐiều chuyển bộ phận\nBắt đầu đóng BHXH\nNgừng đóng BHXH\nKhen thưởng\nKỷ luật\nKhám sức khỏe\nTập huấn ATTP\nTạm nghỉ\nĐi làm lại\nNghỉ việc\nKhác` |
| `tieu_de` | Data | Tiêu đề | in_list_view |
| `noi_dung` | Small Text | Nội dung | |
| `gia_tri_cu` | Data | Giá trị cũ | |
| `gia_tri_moi` | Data | Giá trị mới | |
| `tep` | Attach | Tệp | |
| `nguon` | Select | Nguồn | `Tay\nTự động`, default `Tay`, read_only |
| `khoa_tu_dong` | Data | Khoá tự động | hidden, **unique** (idempotency cho sự kiện tự sinh) |

Permissions: System Manager / HR Manager: read, write, create, delete; HR User: read, write, create. Sự kiện `nguon = Tự động` không cho sửa `loai/ngay` từ app (chỉ thêm `noi_dung`).

### 3.4 Sự kiện tự động — `hooks.py` → `doc_events["Employee"]`

Bỏ qua toàn bộ khi `frappe.flags.ns_backfill = True`.

- `after_insert` → **Vào làm**, `ngay = date_of_joining`, `khoa_tu_dong = vao-lam:{name}`.
- `on_update` (so với `doc.get_doc_before_save()`), mỗi thay đổi 1 sự kiện, `ngay = today` trừ khi ghi khác:
  - `department` đổi → **Điều chuyển bộ phận** (`gia_tri_cu/moi` = tên bộ phận).
  - `custom_lương_cơ_bản` đổi → **Thay đổi lương** (cũ/mới số tiền).
  - `vn_contract_type` đổi → **Ký HĐLĐ** (cũ/mới).
  - `ns_dong_bhxh` 0→1 → **Bắt đầu đóng BHXH** (`ngay = ns_bhxh_tu_ngay or today`, `noi_dung` = mức trừ `custom_bảo_hiểm`); 1→0 → **Ngừng đóng BHXH** (`ngay = ns_bhxh_den_ngay or today`).
  - `status`: →`Inactive`/`Suspended` → **Tạm nghỉ**; `Inactive`→`Active` → **Đi làm lại**; →`Left` → **Nghỉ việc** (`ngay = relieving_date or today`, `noi_dung = reason_for_leaving`).
  - `khoa_tu_dong = {loai-slug}:{name}:{now_datetime isoformat}`.

### 3.5 Backfill một lần — `bench --site site1.local execute ns.setup.backfill.run`

Set `frappe.flags.ns_backfill = True`, idempotent (bỏ qua khoá đã có), in bảng đếm cuối cùng:
1. `ns_dong_bhxh = 1` cho mọi Employee có `custom_bảo_hiểm > 0` (`db_set`, không chạy hook).
2. **Vào làm** cho mọi Employee có `date_of_joining` (khoá `vao-lam:{name}`).
3. **Nghỉ việc** cho `status = Left`: `ngay = relieving_date`; nếu rỗng → `ngay = modified` và `noi_dung = "Backfill: không có ngày nghỉ việc, lấy ngày sửa hồ sơ gần nhất"`.
4. **Bắt đầu đóng BHXH** cho `ns_dong_bhxh = 1`: `ngay = today`, `noi_dung = "Ghi nhận khi khởi tạo app ns — ngày bắt đầu đóng thực tế chưa rõ, mức trừ {custom_bảo_hiểm}"`. Không bịa ngày.
5. Kiểm tra `frappe.db.exists("DocType", "SalaryProduct")`. Nếu còn: đọc meta; nếu có đủ `employee` + tháng/năm + tổng tiền thì đưa vào nguồn của timeline (§4.3) với nhãn **Lương khoán (cũ)**; nếu mapping không rõ → bỏ qua và ghi vào báo cáo cuối, không đoán.

Các tháng lương **không** sinh sự kiện — timeline đọc thẳng `SalaryDay` / `SX Phieu Luong` lúc render.

---

## 4. API — `ns/api/*.py`, tất cả `@frappe.whitelist()`

Guard chung `ns.api.guard()`: user phải có 1 trong `HR User`, `HR Manager`, `System Manager`; Guest và user chỉ có role `Employee` → `frappe.throw(PermissionError)`. Sau guard, đọc `SalaryDay` / `SX Phieu Luong` bằng `frappe.get_all(..., ignore_permissions=True)` (vì `SX Phieu Luong` chỉ mở cho `SX Quan Ly`). Ghi Employee / NS Su Kien đi qua `frappe.get_doc(...).save()` để hook chạy (ignore_permissions sau guard).

Quy ước chung: `loai_luong(emp) = "Khoán" if department == "Công khoán - HGC" else "Nhật"`; `tham_nien_nam = (today - date_of_joining) / 365.25`, 1 số lẻ.

### 4.1 `ns.api.nhan_vien`
- `danh_sach(tab, department=None, q=None)`
  - `tab`: `bhxh` (status Active, ns_dong_bhxh=1) · `khong_bhxh` (Active, ns_dong_bhxh=0) · `tam_nghi` (Inactive, Suspended) · `da_nghi` (Left)
  - `department`: tên bộ phận, hoặc `__none__` = chưa có bộ phận
  - `q`: like trên `employee_name`, `custom_cccd`, `attendance_device_id`, `name`
  - trả: `name, employee_name, department, loai_luong, date_of_joining, tham_nien_nam, custom_bảo_hiểm, ns_dong_bhxh, custom_lương_cơ_bản, cell_number, canh_bao[]` (mã cảnh báo theo §6) + `tong_so` mỗi tab.
- `chi_tiet(name)` → Employee (chỉ field trong whitelist §4.1.1) + `ns_giay_to[]` + `canh_bao[]` + `loai_luong`.
- `luu(name, data)` → chỉ nhận key trong whitelist; `ns_giay_to` thay cả bảng; validate: `custom_cccd` 12 chữ số nếu có, `date_of_joining` ≤ today, `relieving_date` bắt buộc khi status=Left. Lưu qua `get_doc().save()`. Trả `chi_tiet(name)`.
- `tao(data)` → tạo Employee mới: `first_name` = **họ tên đầy đủ** (theo cách RVHG đang dùng, không tách họ/đệm), `gender`, `date_of_birth`, `date_of_joining`, `department`, `custom_cccd`, `cell_number`; `company` = Company mặc định; `status = Active`; `naming_series = HR-EMP-`. Trả `name`.

**4.1.1 Whitelist field được sửa từ app:** `first_name, gender, date_of_birth, image, custom_cccd, cell_number, custom_zalo, personal_email, current_address, permanent_address, person_to_be_contacted, emergency_phone_number, relation, department, designation, date_of_joining, vn_contract_type, contract_end_date, attendance_device_id, status, relieving_date, reason_for_leaving, custom_lương_cơ_bản, custom_hỗ_trợ, custom_bảo_hiểm, custom_lương_tài_khoản, custom_ăn_ca_tối_tại_công_ty, ns_dong_bhxh, ns_so_so_bhxh, ns_bhxh_tu_ngay, ns_bhxh_den_ngay, ns_ly_do_khong_bhxh, vn_insurance_salary, vn_tax_code, vn_number_of_dependents, health_insurance_no, bank_name, bank_ac_no, custom_bankowner, salary_mode, ns_giay_to`.

Tệp đính kèm (giấy tờ, ảnh): client gọi `/api/method/upload_file` với `is_private=1, doctype=Employee, docname=<name>`, lấy `file_url` gán vào dòng.

### 4.2 `ns.api.su_kien`
- `them(employee, ngay, loai, tieu_de=None, noi_dung=None, tep=None)` → insert `NS Su Kien` nguồn Tay.
- `sua_noi_dung(name, noi_dung)` · `xoa(name)` (chỉ nguồn Tay, chỉ HR Manager/System Manager).

### 4.3 `ns.api.lich_su.get(employee)` → list sort `ngay` desc, mỗi phần tử `{ngay, loai, tieu_de, noi_dung, gia_tri_cu, gia_tri_moi, tep, nguon, ref_doctype, ref_name, trang_thai}`:
- `NS Su Kien` của employee.
- `SalaryDay` docstatus<2, group theo (year, month): ưu tiên bản docstatus=1, không có thì nháp mới nhất → `ngay = {year}-{month}-01`, `loai = "Lương công nhật"`, `tieu_de = "T{month}/{year}"`, `noi_dung = "{congngay} công · làm thêm {lamthem} · thực nhận {luongthucnhan}"`, `trang_thai = status + (Nháp nếu docstatus 0)`.
- `SX Phieu Luong` docstatus<2 tương tự: `loai = "Lương khoán"`, `noi_dung = "{ngay_cong} công · lương SP {luong_san_pham} · thực nhận {luong_thuc_nhan}"`, `trang_thai = trang_thai`.
- `SalaryProduct` nếu được map ở §3.5.

### 4.4 `ns.api.cong_luong.thang(employee, thang, nam)` → phiếu của tháng đó (SalaryDay ưu tiên submitted; hoặc SX Phieu Luong): header (toàn bộ field tổng hợp) + `dong[]` (SalaryDay: `chamcong` rows `ngaycc, congngay, themgio`; khoán: `dong` rows `ngay, thu, an_ca, an_dem, tien_an, luong_sp, he_so, thu_nhap_ngay` + `chi_tiet` rows) + `phat[]` + `in_url` (SalaryDay: `/printview?doctype=SalaryDay&name=…&format=Phiếu lương công nhật`; khoán: `/app/sx-phieu-luong/<name>`) + `desk_url`.

### 4.5 `ns.api.luong`
- `bang(thang, nam, loai, department=None)`, `loai ∈ {nhat, khoan}`:
  - Tập nhân viên: Active thuộc phạm vi (nhat: mọi bộ phận ≠ Công khoán; khoan: = Công khoán) ∪ nhân viên có phiếu tháng đó.
  - Mỗi dòng: thông tin NV + phiếu (docstatus<2; nếu nhiều phiếu: submitted trước, không thì nháp mới nhất; `trung = True` nếu >1 nháp) + `thieu_phieu = True` khi không có phiếu.
  - Cột **nhật** (từ SalaryDay): `ngaysanxuat, congngay, lamthem, luongngaycong, luonglamthem, anca, chuyencan, hotrongaycong, hotro, thuongkhac, thuongthamnien, tongtien, baohiem, tienphat, tongkhautru, luongthucnhan, luongck, status, docstatus, name`.
  - Cột **khoán** (từ SX Phieu Luong): `ngay_san_xuat, ngay_cong, luong_san_pham, tien_an, chuyen_can, ho_tro_ngay_cong, ho_tro, thuong_tham_nien, tong_tien, bao_hiem, tien_phat, tong_khau_tru, luong_thuc_nhan, trang_thai, docstatus, name`.
  - Trả thêm `tong` (sum từng cột số) và `so_thieu_phieu`, `so_nhap`, `so_duyet`.
- `xuat_excel(thang, nam, loai)` → `.xlsx` bằng `frappe.utils.xlsxutils.make_xlsx`, header tiếng Việt, dòng tổng; trả file qua `frappe.response` (`filename`, `filecontent`, `type = "download"`).
- `chuyen_khoan(thang, nam)` → `.xlsx` danh sách chuyển khoản: từ SalaryDay **submitted** của tháng, `luongck > 0`: `STT, Chủ tài khoản (chutaikhoan), Số TK (taikhoan), Ngân hàng (nganhang), Số tiền (luongck), Nội dung = "Luong T{thang}/{nam} {employee_name}"`; cộng tổng.

### 4.6 `ns.api.viec.tong_hop()` → các nhóm theo §6, mỗi nhóm `{ma, ten, so_luong, dong[]}`.

### 4.7 `ns.api.bo_sung` — bổ sung thông tin còn thiếu

Bộ field "hồ sơ tối thiểu" (`TRUONG_TOI_THIEU`, thứ tự cố định; đây là bộ cột của lưới và của file Excel):

| nhóm | field | áp dụng |
|---|---|---|
| Cá nhân | `custom_cccd`, `date_of_birth`, `gender`, `cell_number`, `custom_zalo`, `permanent_address` | tất cả |
| Công việc | `department`, `date_of_joining`, `vn_contract_type`, `contract_end_date`, `attendance_device_id` | mã máy: trừ Công khoán |
| Lương | `custom_lương_cơ_bản` | trừ Công khoán |
| BHXH | `ns_dong_bhxh`, `custom_bảo_hiểm`, `ns_so_so_bhxh`, `vn_insurance_salary`, `ns_bhxh_tu_ngay`, `ns_ly_do_khong_bhxh` | 4 field sau chỉ khi đóng; lý do chỉ khi không đóng |
| Thuế | `vn_tax_code`, `vn_number_of_dependents` | tất cả |
| Ngân hàng | `bank_ac_no`, `bank_name`, `custom_bankowner` | khi `custom_lương_tài_khoản > 0` |
| Giấy tờ | có dòng `NS Giay To` loại CCCD; loại HĐLĐ còn hạn; Giấy khám sức khỏe còn hạn; Xác nhận ATTP còn hạn | tất cả (giấy tờ chỉ đếm, không nhập qua lưới) |

- `tong_quan(department=None)` → với mỗi NV Active: `name, employee_name, department, thieu[]` (danh sách field thiếu theo bảng trên, có áp dụng điều kiện), `pct_du` (% field áp dụng đã có). Trả thêm `tong_hop`: số NV đủ 100%, trung bình %, đếm thiếu theo từng field (để vẽ thanh "Còn thiếu: CCCD 40 · Mã máy 22 · …").
- `luoi(department=None, chi_thieu=True)` → ma trận NV × field cho lưới sửa inline: mỗi ô `{gia_tri, thieu, ap_dung}`. `chi_thieu=True` chỉ trả NV còn thiếu ≥1 field.
- `luu_o(employee, field, gia_tri)` → lưu 1 ô (whitelist §4.1.1, validate như `luu`), trả `thieu[]` mới của NV đó. Lưu qua `get_doc().save()` để hook sự kiện chạy.
- `mau_excel(department=None)` → `.xlsx`: 1 dòng/NV Active, cột = `Mã NV, Họ tên, Bộ phận` + toàn bộ field bảng trên (header = label tiếng Việt, hàng 2 = fieldname ẩn màu xám để nhập lại không lệch), ô đã có dữ liệu điền sẵn, ô thiếu tô vàng. Select (giới tính, loại HĐ, lý do) có data validation list.
- `xem_truoc_excel(file_url)` → đọc file đã upload, khớp NV theo **Mã NV** (cột A, bắt buộc; không khớp theo tên), trả bảng diff: `{employee, employee_name, thay_doi: [{field, cu, moi, loi}]}` + `so_dong_loi`. Chỉ nhận field trong bảng trên; parse ngày `dd/mm/yyyy` và ISO; số bỏ dấu chấm/phẩy; Check nhận `1/0/x/có/không`. Ô trống trong Excel = **không đổi** (không xoá dữ liệu đang có).
- `ap_dung_excel(file_url, chi_dong=[...])` → áp các thay đổi đã xem trước (tuỳ chọn chỉ một số NV), mỗi NV 1 `save()`, trả `{thanh_cong, loi: [{employee, msg}]}`. Chạy trong 1 request, tối đa 200 NV; lỗi 1 NV không chặn NV khác (commit từng NV).

### 4.8 Context bridge — `www/ns.py`
`window.NS_CONTEXT = { user, full_name, isManager (HR Manager | System Manager), assetVersion, csrfToken, departments[] (5 bộ phận + "__none__"), today }`. Guest → redirect `/login?redirect-to=/ns`. User không qua guard → trang "Không có quyền".

---

## 5. Màn hình (hash router, mobile-first, CSS prefix `ns-`)

Cấu trúc file theo skill: `www/ns.py`, `www/ns.html` (import map + NS_CONTEXT), `public/ns/shell.js`, `public/ns/lib/{api,router,dom,format,store}.js`, `public/ns/components/`, `public/ns/views/{danh_sach,ho_so,bo_sung,luong,viec}.js`, `public/ns/shell.css`. Nav 5 mục: Nhân sự · Bổ sung · Lương · Việc · Chấm công.

### `#/` — Danh sách NLĐ
- 4 tab (số đếm trên tab): **Đóng BHXH** · **Không đóng BHXH** · **Tạm nghỉ** · **Đã nghỉ**.
- Thanh lọc: bộ phận (chip, có "Chưa có bộ phận"), ô tìm (tên / CCCD / mã máy / mã NV), nút **+ Thêm người**.
- Bảng: Mã · Họ tên · Bộ phận · Nhật/Khoán · Ngày vào · Thâm niên · BHXH (số tiền trừ, hoặc "—") · Lương CB · SĐT · Cảnh báo (icon có tooltip). Mobile: card 2 dòng.
- Click dòng → `#/nv/:name`.
- **Thêm người** → modal các field của `tao()`; tạo xong mở hồ sơ.

### `#/nv/:name` — Hồ sơ (tab)
1. **Thông tin** — form sửa trực tiếp, 4 nhóm: *Cá nhân* (họ tên, giới tính, ngày sinh, CCCD, SĐT, Zalo, email, địa chỉ hiện tại, thường trú, liên hệ khẩn cấp) · *Công việc* (bộ phận, chức danh, ngày vào, loại HĐ `vn_contract_type`, ngày hết hạn HĐ `contract_end_date`, mã máy chấm công, trạng thái, ngày nghỉ việc + lý do khi Left) · *Lương & BHXH* (lương CB, hỗ trợ, bảo hiểm, lương tài khoản, ăn ca tối; `ns_dong_bhxh`, số sổ, mức lương đóng BH, đóng từ / ngừng từ, lý do không đóng, MST, số người phụ thuộc, mã thẻ BHYT) · *Ngân hàng* (ngân hàng, số TK, chủ TK, hình thức trả). Nút Lưu / Huỷ; lỗi validate hiện ngay field.
2. **Giấy tờ** — bảng `ns_giay_to`, thêm/sửa/xoá dòng, upload tệp, badge: đỏ **Hết hạn**, vàng **≤30 ngày**. Lưu chung với hồ sơ.
3. **Lịch sử** — timeline từ `lich_su.get`, mới nhất trên; sự kiện Tự động có nhãn; nút **+ Thêm sự kiện**; dòng lương click → tab Công & lương tháng đó.
4. **Công & lương** — chọn tháng; hiện phiếu tháng đó (tổng hợp + bảng ngày); nút **In** / **Mở trong ERPNext**; không có phiếu → "Chưa có phiếu tháng này". Chỉ đọc.

### `#/bo-sung?bp=` — Bổ sung thông tin còn thiếu (màn HR dùng hằng ngày cho đến khi hồ sơ đủ)
- Đầu trang: thanh tiến độ "Hồ sơ đủ **X/78**" + dãy chip đếm thiếu theo field ("CCCD 40", "Mã máy 22", "Số sổ BHXH 48"…); click chip → lưới lọc còn đúng cột đó.
- Lọc: bộ phận (có "Chưa có bộ phận"), công tắc **Chỉ người còn thiếu** (mặc định bật), tìm tên.
- **Lưới NV × field** (`bo_sung.luoi`): sticky cột tên; ô thiếu nền vàng, ô không áp dụng gạch chéo xám; click ô → editor đúng kiểu (Data/Date/Select/Check/Currency/Link bộ phận); Enter hoặc blur → `luu_o` ngay, ô chuyển xanh, cập nhật tiến độ; lỗi → đỏ + tooltip, giữ giá trị người dùng gõ để sửa. Tab chuyển ô kế tiếp còn thiếu trên cùng hàng.
- Cột **Giấy tờ**: 4 ô đếm (CCCD / HĐLĐ / Khám SK / ATTP) — click mở hồ sơ tab Giấy tờ (không nhập giấy tờ qua lưới).
- Khối **Excel**: nút **Tải mẫu** (`mau_excel`, theo bộ phận đang lọc) → HR điền offline → **Nhập file**: upload (private) → `xem_truoc_excel` → bảng diff từng NV (cũ → mới, dòng lỗi đỏ, bỏ tick NV không muốn áp) → **Áp dụng** → báo thành công/lỗi, lưới tải lại.
- Trên hồ sơ (`#/nv/:name`) hiện banner "Còn thiếu: CCCD, mã máy, …" với link nhảy tới field; danh sách `#/` có cột `pct_du`.

### `#/luong?t=&n=&loai=` — Bảng lương tháng
- Chọn tháng/năm, tab **Công nhật** / **Công khoán**, lọc bộ phận, lọc trạng thái.
- Lưới cột theo §4.5, sticky cột tên, dòng tổng; đánh dấu đỏ `thieu_phieu`, cam `trung`, xám nháp.
- Nút: **Xuất Excel**, **Danh sách chuyển khoản** (tab nhật), **Mở phiếu** (desk), **In** (nhật).
- v1 chỉ đọc. Sửa công → `/chamcong2`; sửa phiếu → desk.

### `#/viec` — Việc cần làm
Thẻ theo nhóm §6, mỗi thẻ số lượng + danh sách click sang hồ sơ. Cũng là trang mặc định nếu có việc đỏ (hết hạn) — còn không mở `#/`.

### `#/chamcong`
`window.location.href = "/chamcong2"`. Trang chấm công hiện giữ nguyên; thêm vào Web Page đó một link "← Nhân sự" về `/ns` (sửa tay trong Web Page, không thuộc code app).

---

## 6. Cảnh báo / Việc cần làm — định nghĩa (dùng chung cho `canh_bao[]` và `viec.tong_hop`)

| mã | điều kiện | mức |
|---|---|---|
| `hd_het_han` | dòng `NS Giay To` loại HĐLĐ/Phụ lục mới nhất của NV có `ngay_het_han` ≤ today+30 (đã qua = đỏ, sắp = vàng); ∪ `contract_end_date` nếu có | đỏ/vàng |
| `kham_sk_het_han` | dòng Giấy khám sức khỏe mới nhất `ngay_het_han` ≤ today+30 | đỏ/vàng |
| `attp_het_han` | dòng Xác nhận kiến thức ATTP mới nhất ≤ today+30 | đỏ/vàng |
| `thieu_cccd` | Active, `custom_cccd` rỗng | vàng |
| `thieu_bo_phan` | Active, `department` rỗng | vàng |
| `thieu_ma_may` | Active, bộ phận ≠ Công khoán, `attendance_device_id` rỗng | vàng |
| `thieu_luong_cb` | Active, bộ phận ≠ Công khoán, `custom_lương_cơ_bản` = 0 | vàng |
| `thieu_tk` | `custom_lương_tài_khoản` > 0 mà `bank_ac_no` rỗng | vàng |
| `bhxh_rui_ro` | Active, `ns_dong_bhxh = 0`, `date_of_joining` ≤ today−30, `ns_ly_do_khong_bhxh` rỗng | đỏ |
| `bhxh_chua_muc` | `ns_dong_bhxh = 1` mà `custom_bảo_hiểm` = 0 | vàng |
| `sinh_nhat` | `date_of_birth` cùng tháng hiện tại | xanh |
| `luong_thieu_phieu` | tháng trước: NV Active không có phiếu (nhật/khoán) | vàng |
| `luong_con_nhap` | tháng trước: phiếu docstatus 0 | vàng |
| `luong_trung` | cùng NV cùng tháng có >1 phiếu nháp | đỏ |

---

## 7. P1 — tính lại `SalaryDay` phía server (ĐÃ DUYỆT, commit riêng, bật sau khi đối chiếu)

**Vấn đề:** công thức lương công nhật chỉ chạy trong Client Script → `/chamcong2` ghi `chamcong` bằng `frappe.client.save` thì **tổng/tiền trên phiếu không tính lại**; hiện kế toán phải mở từng phiếu trên Desk và Save (duyệt) thì số mới đúng. Lưới lương của app vì thế có thể hiện số cũ. `SX Phieu Luong` đã giải bài này (tính lúc validate) — làm tương tự cho SalaryDay.

**NGUYÊN TẮC TUYỆT ĐỐI:** công thức đang chạy là **đúng nghiệp vụ, đã được kế toán xác nhận**. Port **y nguyên** Client Script — kể cả mọi ngoại lệ theo mã nhân viên và các hằng số. KHÔNG "sửa cho hợp lý", KHÔNG gộp, KHÔNG đổi thứ tự điều kiện. Chỗ nào trông lạ thì giữ nguyên và ghi chú `# chép từ Client Script, giữ nguyên theo yêu cầu`.

**Cách làm:** `hooks.py` → `doc_events["SalaryDay"]["validate"] = "ns.salaryday.tinh_lai"`.

```
rows = doc.chamcong; phat = doc.bangghiloiphat
month, year lấy từ doc.ngay (set lại doc.month, doc.year)
NẾU rows rỗng → return (không tính gì, giống JS)

congngay = lamthemgio = anchinh = anthem = conglamthem = congchunhat = congbd = 0
với mỗi row:
    cn = weekday (Chủ nhật) ; mung1 = (ngày 1 tháng 1)
    congbd += floor(row.congngay)
    nếu cn hoặc mung1: conglamthem += row.congngay; congchunhat += row.congngay
    ngược lại:         congngay    += row.congngay
    lamthemgio += row.themgio
    anchinh += 1 nếu row.congngay == 1
    anthem  += 1 nếu row.themgio  > 3
tienphat = Σ (p.soluong * p.giatien)  (ghi p.thanhtienphat)

chuyencan = 0
nếu (congngay < ngaysanxuat và congngay + congchunhat > 25) hoặc congngay > ngaysanxuat: chuyencan = CC_DAT
nếu congngay + congchunhat >= ngaysanxuat - 0.5:                                        chuyencan = CC_DAT
nếu ngaysanxuat > 29 và ngaysanxuat - congngay - congchunhat < 1:
    chuyencan = CC_DU_CAO_DIEM nếu month in THANG_CAO_DIEM else CC_DU

hotrongaycong = 0
nếu ngaysanxuat < CHUAN và ngaysanxuat - congngay < 1 và congngay + conglamthem < CHUAN:
    thieu = CHUAN - congngay - conglamthem - (0.5 nếu ngaysanxuat - congngay == 0.5 else 0)
    hotrongaycong = thieu * HO_TRO_NGAY
nếu doc.ancatoi: anthem = 0

nếu doc.department == "Bình Dương - HGC":
    tienanca = congbd * AN_CA
    congngay = congngay + conglamthem + lamthemgio / 8
    conglamthem = lamthemgio = hotrongaycong = chuyencan = 0
ngược lại:
    tienanca = anchinh * AN_CA + anthem * AN_DEM

luongngaycong = luongcoban / 26 * congngay
luonglamthem  = luongcoban / 26 * (conglamthem + lamthemgio / 8) * HE_SO_LE
tongkhautru   = baohiem + tienphat
nếu employee == "HR-EMP-00035": tienanca = 0; chuyencan = 0                                        # đúng nghiệp vụ, giữ nguyên
nếu employee == "HR-EMP-00045": luonglamthem = luongcoban / 26 * (conglamthem + lamthemgio / 8.5) * HE_SO_LE   # đúng nghiệp vụ, giữ nguyên
nếu month == 2: hotrongaycong = 0

thâm niên (nếu doc.tinhthuongthamnien): congngay của SalaryDay tháng liền trước và tháng trước nữa (cùng employee, cùng month/year) —
    tra y như JS: frappe.db.get_value("SalaryDay", {employee, month, year}, "congngay") (bản mới sửa nhất, không lọc docstatus); không có → coi 0
    thamnienthangnay      = luongcoban/26 * congngay          * TY_LE
    thamnienthangtruoc    = luongcoban/26 * congngay_thang_1  * TY_LE
    thamnienthangtruocnua = luongcoban/26 * congngay_thang_2  * TY_LE
    thuongthamnien = tổng 3 số
ngược lại 4 field = 0

ghi: luongngaycong, congngay,
     lamthem = conglamthem + lamthemgio / 8.5 nếu employee == "HR-EMP-00035" else conglamthem + lamthemgio / 8   # đúng nghiệp vụ, giữ nguyên
     luonglamthem, anca = tienanca, tongkhautru, hotrongaycong, tienphat, chuyencan
tongtien = luongngaycong + luonglamthem + tienanca + chuyencan + hotrongaycong + hotro + thuongkhac + thuongthamnien
luongthucnhan = tongtien - tongkhautru
```

Tham số: đọc `SX Settings` qua `sx.utils.get_settings()` với fallback đúng giá trị JS đang dùng — `AN_CA = tien_an_ca (20000)`, `AN_DEM = tien_an_dem (10000)`, `HE_SO_LE = he_so_ngay_le (1.2)`, `CC_DAT = chuyen_can_dat (200000)`, `CC_DU = chuyen_can_du (300000)`, `CC_DU_CAO_DIEM = chuyen_can_du_cao_diem (1000000)`, `CHUAN = ngay_cong_chuan (22)`, `HO_TRO_NGAY = ho_tro_ngay_cong (70000)`, `TY_LE = ty_le_tham_nien (0.05)`, `THANG_CAO_DIEM = thang_cao_diem ("11,12,1")`. Nếu app `sx` không cài → dùng fallback.

Một khác biệt kỹ thuật không tránh được: JS tra thâm niên **bất đồng bộ** (2 lần `frappe.call` trong `validate`), nên trên Desk `tongtien` chỉ gồm thưởng thâm niên ở lần Save thứ hai; server tính đồng bộ → cho ngay kết quả của lần Save thứ hai. Số cuối cùng giống nhau, chỉ bớt một lần bấm. Ghi rõ trong docstring, không "sửa" gì thêm.

**Kiểm chứng trước khi bật:** `bench --site site1.local execute ns.salaryday.doi_chieu --kwargs "{'thang':9,'nam':2026}"` — với mọi SalaryDay docstatus=1 của tháng, chạy `tinh_lai` trên bản copy (không save), so **từng field tiền** (`luongngaycong, luonglamthem, anca, chuyencan, hotrongaycong, thuongthamnien, tongtien, tongkhautru, luongthucnhan`), in bảng lệch (tên, field, JS, server, chênh). Chạy cho 6, 7, 8, 9/2026. **Chỉ bật hook khi lệch = 0 trên mọi phiếu** (phiếu `tinhthuongthamnien = 1` được phép lệch đúng phần thâm niên nếu kế toán mới Save 1 lần — liệt kê riêng để mrhuychien kiểm). Có lệch khác → KHÔNG tự sửa công thức, báo lại kèm bảng.

Sau khi bật: Client Script giữ nguyên chạy song song 1 tháng (kết quả trùng, vô hại), rồi mới disable Client Script.

**v1.1 (sau khi P1 ổn):** sửa inline trên lưới lương với phiếu nháp — đặt hàng loạt `ngaysanxuat` cho cả bộ phận, sửa `thuongkhac`, `ancatoi`.

---

## 8. Việc làm tay ngoài code (mrhuychien làm trên Desk, Claude Code chỉ nhắc trong README)

- **Đã duyệt:** `SalaryDay` → Role Permission Manager → xoá dòng role `Employee` (đang `write = 1`). Làm ngay, không chờ app.
- `SX Phieu Luong.bao_hiem` nhập tay, không fetch từ `Employee.custom_bảo_hiểm` → cân nhắc `fetch_from` + `fetch_if_empty` (sửa trong app `sx`, không thuộc spec này).
- 14 user có `HR Manager` → rà lại.
- 3 `SalaryDay` có month=0/year=0 → xoá.
- Web Page `chamcong` (cũ) còn published → unpublish để khỏi nhầm.
- Thêm link "← Nhân sự" (`/ns`) vào Web Page `chamcong2`.

---

## 9. Cài đặt, deploy, nghiệm thu

```bash
cd /home/frappe/frappe-bench
bench new-app ns          # hoặc get-app từ repo mrhuychien/ns
bench --site site1.local install-app ns
bench --site site1.local migrate
bench build --app ns
bench restart
bench --site site1.local execute ns.setup.backfill.run
```
Checklist cài: mọi thư mục Python có `__init__.py`; fixtures chỉ export Custom Field `dt=Employee, fieldname like 'ns_%'`; không export Property Setter của Employee.

**Nghiệm thu v1:**
1. `/ns` với user `HR User`: 4 tab đếm đúng (Đóng BHXH = 48 ± thay đổi, Không đóng = 30, Tạm nghỉ = 18, Đã nghỉ = 6).
2. Mở 1 hồ sơ, sửa lương CB, lưu → tab Lịch sử có sự kiện **Thay đổi lương** cũ/mới.
3. Thêm giấy tờ HĐLĐ hết hạn 15 ngày tới → Việc cần làm hiện `hd_het_han` vàng.
4. Bật `ns_dong_bhxh` cho 1 người không đóng → sự kiện **Bắt đầu đóng BHXH**, người đó chuyển tab.
5. `#/luong?t=9&n=2026&loai=nhat`: tổng `luongthucnhan` = tổng cột trên báo cáo `SalaryDay` list view (Desk) cùng bộ lọc; Xuất Excel mở được; Danh sách chuyển khoản chỉ có người `luongck > 0`.
6. `#/luong?...&loai=khoan` tháng 10/2026: 23 phiếu nháp hiện đúng, cột thực nhận khớp form.
7. User chỉ có role `Employee` vào `/ns` → "Không có quyền"; gọi thẳng API → PermissionError.
8. `#/chamcong` → sang `/chamcong2`.
9. Mobile 390px: danh sách và hồ sơ dùng được, không scroll ngang.
10. `#/bo-sung`: tiến độ hiện đúng (ví dụ CCCD thiếu 40); sửa 1 ô CCCD → ô xanh, số đếm giảm 1, hồ sơ Desk có giá trị mới; nhập CCCD sai 11 số → ô đỏ, không lưu.
11. Tải mẫu Excel bộ phận Văn phòng → điền 2 ô → nhập file → diff hiện đúng 2 thay đổi, ô để trống không bị xoá dữ liệu cũ → áp dụng → lưới cập nhật.
12. P1: `doi_chieu` tháng 6–9/2026 lệch = 0 (trừ phần thâm niên được liệt kê riêng). Sau khi bật hook: sửa 1 ô công trên `/chamcong2` cho phiếu nháp tháng 10 → mở phiếu trên Desk, `luongthucnhan` đã đúng mà không cần Save lại.
