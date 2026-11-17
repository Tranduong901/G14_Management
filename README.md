# HỆ THỐNG THÔNG TIN QUẢN TRỊ DOANH NGHIỆP G14 (G14 SYSTEM)
## PHÂN PHỐI VÀ KINH DOANH THIẾT BỊ CÔNG NGHỆ

Hệ thống thông tin quản trị doanh nghiệp toàn diện phục vụ chuỗi phân phối thiết bị công nghệ (Smartphone, Tablet, Laptop, Phụ kiện), quản lý từng thiết bị theo mã Serial/IMEI, bảo hành điện tử, chuỗi cung ứng SCM, kế toán quản trị dòng tiền ERP và hệ thống hỗ trợ ra quyết định DSS tối ưu hóa bằng Google OR-Tools.

---

## 1. CÔNG NGHỆ NỀN TẢNG

- **Backend:** Python 3.12 + Django 6.1.2.
- **Database:** PostgreSQL trên Render (kết nối qua `DATABASE_URL`, SSL bắt buộc).
- **ORM:** Django ORM với Service Layer Pattern & Transaction Atomic (ACID).
- **Frontend:** Django Templates, HTML5, CSS3, JavaScript, Bootstrap 5.3, Bootstrap Icons.
- **Biểu đồ trực quan:** Chart.js (Line chart, Doughnut chart, Bar chart).
- **Tối ưu hóa toán học:** Google OR-Tools (MIP Linear Programming với bộ giải SCIP / CBC).
- **REST API:** Django REST Framework (DRF) v3.15+.
- **Quản lý cấu hình:** python-dotenv (`.env`).

---

## 2. DANH SÁCH TÀI KHOẢN DEMO HỆ THỐNG

Hệ thống đã chuẩn bị sẵn 6 tài khoản tương ứng với 6 vai trò phân quyền nghiệp vụ độc lập:

| Tên đăng nhập | Mật khẩu mặc định | Vai trò (Role) | Chức danh mẫu | Quyền hạn chính trong hệ thống |
| :--- | :--- | :---: | :--- | :--- |
| `admin` | `admin123` | **ADMIN** | Quản trị hệ thống | Quản trị tài khoản, phân quyền, cấu hình chi nhánh, xem toàn bộ nhật ký hệ thống (Audit Log). *Bị chặn xem lương nếu không có cờ `can_view_payroll`*. |
| `quanly` | `admin123` | **QL** | Giám đốc điều hành | Xem Dashboard điều hành toàn hệ thống, xem báo cáo doanh thu, phê duyệt đề nghị nhập hàng (SCM), phê duyệt kiểm kê kho, phê duyệt bảng lương, phân tích DSS. |
| `banhang` | `admin123` | **BH** | Chuyên viên bán hàng | Tra cứu sản phẩm, quản lý Lead/Cơ hội CRM, lập đơn bán hàng, chỉ định Serial/IMEI, tiếp nhận bảo hành, xem phiếu lương cá nhân. |
| `kho` | `admin123` | **KHO** | Trưởng kho thiết bị | Nhập hàng, khai báo Serial/IMEI, kiểm kê điều chỉnh kho, điều chuyển kho nội bộ, lập đề nghị nhập hàng (SCM). |
| `ketoan` | `admin123` | **KT** | Kế toán trưởng | Xem doanh thu bán hàng, quản lý sổ quỹ thu - chi, theo dõi công nợ NCC, chi trả nợ, duyệt bảng lương và thực hiện chi lương ra sổ quỹ. |
| `nhansu` | `admin123` | **HR** | Quản trị nhân sự | Quản lý hồ sơ nhân viên (D1), hợp đồng lao động, chấm công thủ công (D2), phê duyệt đơn nghỉ phép, lập và tính toán bảng lương (D3). |

---

## 3. CẤU TRÚC THƯ MỤC PROJECT

```text
g14_system/
├── manage.py
├── requirements.txt
├── .env.example
├── .env
├── README.md
├── config/
│   ├── settings/
│   │   ├── base.py       # Cấu hình trung tâm, kết nối Render PostgreSQL
│   │   ├── dev.py        # Thiết lập môi trường phát triển
│   │   └── prod.py       # Thiết lập môi trường Production (Render Web Service)
│   ├── urls.py           # Định tuyến URL trung tâm cho 14 app và REST API
│   ├── api.py            # DRF ViewSet & API Dashboard
│   ├── wsgi.py
│   └── asgi.py
├── accounts/         # FR-01: Tài khoản, phân quyền RBAC, Chi nhánh (Branch), DataScope, Scoping
├── approvals/        # Approval Engine: Cấu hình quy trình & phê duyệt đa bước (LEAVE, SCM, PAYROLL)
├── catalog/          # FR-02, 03, 04: Sản phẩm, Khách hàng, NCC, Nhóm hàng
├── crm/              # CRM cơ bản: Quản lý Lead, Cơ hội bán hàng, Hoạt động chăm sóc & Phễu bán hàng
├── devices/          # FR-11: Quản lý Serial/IMEI, bảo hành điện tử, đổi mới 1-1
├── dss/              # FR-16, 17: DSS Dự báo nhu cầu SMA-3M, gợi ý nhập hàng, tối ưu hóa OR-Tools
├── finance/          # FR-12, 13: ERP Sổ quỹ thu chi (CashLedger), Công nợ NCC (Payable)
├── hr/               # FR-08, 26: HR mở rộng D1 (Hồ sơ, HĐLĐ), D2 (Chấm công thủ công, Phép), D3 (Tính lương)
├── inventory/        # FR-07, 24: Kho hàng (Warehouse), Biến động xuất nhập, Kiểm kê, Chuyển kho
├── purchasing/       # FR-06, 24: Phiếu nhập hàng, kiểm soát IMEI nhập về, đối soát NCC
├── reports/          # FR-09: Executive Dashboard, 6 nhóm báo cáo quản trị, chỉ tiêu TC01-TC29
├── sales/            # FR-05, 24: Đơn bán hàng đa chi nhánh, thanh toán, in hóa đơn
├── scm/              # FR-14, 15: SCM Đề nghị nhập hàng, phê duyệt SCM, hồ sơ giá NCC
├── auditlog/         # FR-10: Nhật ký hệ thống toàn diện, truy vết dữ liệu & chống xâm nhập
├── templates/        # Giao diện tiếng Việt chuẩn Bootstrap 5.3 theo 14 app
├── static/           # Tài nguyên tĩnh CSS, JavaScript
├── tests/            # Bộ kiểm thử tự động toàn diện 39 ca kiểm thử (100% Passed)
│   ├── test_all_requirements.py        # 14 ca kiểm thử tích hợp liên phân hệ cốt lõi
│   ├── test_control_metrics.py         # 3 ca kiểm thử số liệu kiểm soát điều hành TC01-TC29
│   ├── test_phase1_approvals_branch.py # 3 ca kiểm thử Engine phê duyệt & Phân quyền chi nhánh
│   ├── test_phase2_hr_and_payroll.py   # 5 ca kiểm thử Nghiệp vụ HR D1, D2, D3 & Bảo mật lương
│   ├── test_phase4_crm.py              # 4 ca kiểm thử Pipeline CRM, hoạt động & phễu bán hàng
│   └── test_phase5_regressions.py      # 10 ca kiểm thử kiểm soát biên, đa kho và hồi quy
└── docs/             # Tài liệu kiến trúc, so sánh công nghệ, test report, tài liệu hiện trạng
    ├── ARCHITECTURE.md          # Tài liệu kiến trúc 3 lớp, service layer và luồng liên phân hệ
    ├── TECHNOLOGY_COMPARISON.md # Nghiên cứu ERPNext, frePPLe/OR-Tools, BI Metabase/Power BI
    ├── TEST_REPORT.md           # Báo cáo chi tiết 39 ca kiểm thử thực thi trên PostgreSQL staging
    └── SYSTEM_DOCUMENTATION.md  # Tài liệu hiện trạng & audit toàn diện (FR-18~26, QT16~23, TC30~40)
```

---

## 4. HƯỚNG DẪN CÀI ĐẶT & KHỞI CHẠY TRÊN WINDOWS

### Bước 1: Mở Terminal tại thư mục dự án
```powershell
cd D:\QTHTTT\BTL\g14_system
```

### Bước 2: Cài đặt các thư viện cần thiết
```powershell
pip install -r requirements.txt
```

### Bước 3: Cấu hình PostgreSQL trên Render
1. Tạo PostgreSQL database trên Render và lấy Internal/External Database URL.
2. Cập nhật biến môi trường `DATABASE_URL` trong file `.env` khi chạy local hoặc trong Environment của Render:
   ```ini
   DATABASE_URL=postgresql://user:password@host/database
   ```
   Không commit `.env` hoặc chia sẻ `DATABASE_URL` vì URL có chứa thông tin xác thực.

### Bước 4: Thực thi Migrations tạo cấu trúc bảng
```powershell
python manage.py makemigrations
python manage.py migrate
```

### Bước 5: Nạp dữ liệu mẫu hoàn chỉnh (Seed Data)
```powershell
python manage.py seed_data
```
Lệnh này sẽ tự động khởi tạo:
- 5 tài khoản demo theo 5 vai trò.
- 5 hồ sơ nhân viên tương ứng.
- 4 nhà cung cấp hàng đầu (Apple, Samsung, Asus, Anker).
- 4 khách hàng mẫu (khách lẻ và doanh nghiệp).
- 6 sản phẩm công nghệ chủ lực có quản lý IMEI và phụ kiện.
- Lịch sử bán hàng đa kỳ để tính toán dự báo nhu cầu trung bình động 3 tháng.
- Phiếu nhập hàng, Serial/IMEI trong kho, khoản công nợ và sổ quỹ tiền mặt.

Sau khi kết thúc một kỳ dự báo, cập nhật số bán thực tế và TC28:
```powershell
python manage.py update_forecast_accuracy
```
QL cũng có thể bấm **Cập nhật kết quả kỳ trước** ngay trên màn hình Dự báo nhu cầu;
hệ thống chỉ cập nhật các kỳ nhỏ hơn tháng hiện tại.
Dashboard quản trị cung cấp nhóm số liệu kiểm soát TC01–TC29; TC26 mặc định
coi đề nghị ở trạng thái chờ duyệt quá 48 giờ là quá hạn.

### Bước 6: Chạy kiểm thử tự động
```powershell
python manage.py test tests
```
*Kết quả đã xác minh ngày 06/11/2026: `Ran 39 tests ... OK`.*

### Kiểm thử PostgreSQL staging trên Render
- Chỉ chạy `migrate` với `DATABASE_URL` của database staging đã xác minh; không chạy
  `flush`, `reset_db`, `seed_data` hoặc thao tác ghi dữ liệu production.
- Kiểm tra migration và schema:
  ```powershell
  python manage.py showmigrations --plan
  python manage.py migrate --noinput
  python manage.py check
  python manage.py makemigrations --check
  ```
- Chạy test trên database kiểm thử tách biệt của staging:
  ```powershell
  python manage.py test --keepdb
  ```
- Không đưa `DATABASE_URL` lên Git hoặc chia sẻ URL có thông tin xác thực.

### Bước 7: Khởi động máy chủ Web Django
```powershell
python manage.py runserver 127.0.0.1:8000
```
Truy cập hệ thống tại: **[http://127.0.0.1:8000](http://127.0.0.1:8000)**

### Triển khai trên Render Web Service
Thiết lập Build Command:
```bash
pip install -r requirements.txt
```

Thiết lập Start Command:
```bash
DJANGO_SETTINGS_MODULE=config.settings.prod python manage.py migrate --noinput && DJANGO_SETTINGS_MODULE=config.settings.prod python manage.py collectstatic --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
```

Trong Environment của Render, bắt buộc cấu hình `DATABASE_URL`, `SECRET_KEY`,
`DEBUG=False` và `ALLOWED_HOSTS` theo hostname của Web Service.

---

## 5. KỊCH BẢN TRÌNH DIỄN CÁC LUỒNG NGHIỆP VỤ LIÊN PHÂN HỆ

### Kịch bản 1: Bán hàng trực tiếp & Quản lý Serial/IMEI (Vai trò: `banhang`)
1. Đăng nhập bằng tài khoản `banhang` / `admin123`.
2. Vào menu **Đơn bán hàng** &rarr; Bấm **Tạo đơn bán mới**.
3. Chọn khách hàng (ví dụ: `Nguyễn Văn An`), chọn sản phẩm `iPhone 15 Pro Max`, nhập số lượng = 1.
4. Bấm **Lưu đơn hàng (Nháp)**.
5. Tại màn hình chi tiết, hệ thống tự động gán thiết bị IMEI đang ở trạng thái 'Trong kho'. Bấm **Xác nhận thanh toán & Hoàn tất**.
6. **Kiểm tra kết quả liên phân hệ:**
   - Đơn chuyển sang `Hoàn tất`.
   - Vào menu **Serial/IMEI**: máy đã chuyển sang `Đã xuất bán`, kích hoạt bảo hành 12 tháng.
   - Vào menu **Tồn kho**: số lượng tồn giảm đúng 1 chiếc.
   - Bấm nút **In hóa đơn** để hiển thị trang hóa đơn bán lẻ chuyên nghiệp.

### Kịch bản 2: Chuỗi cung ứng SCM & Nhập hàng (Vai trò: `kho` & `quanly`)
1. Đăng nhập tài khoản `kho` / `admin123`.
2. Vào **Đề nghị nhập hàng** &rarr; Bấm **Lập đề nghị nhập mới** (chọn mặt hàng tồn thấp từ gợi ý).
3. Bấm **Gửi duyệt đề nghị** (Đề nghị chuyển sang trạng thái `Chờ duyệt`).
4. Đăng xuất, đăng nhập tài khoản `quanly` / `admin123`.
5. Vào **Đề nghị nhập hàng**, mở đề nghị vừa gửi &rarr; Bấm **Phê duyệt đề nghị**.
6. Đăng nhập lại tài khoản `kho`, mở đề nghị đã duyệt &rarr; Bấm **Chuyển thành Phiếu nhập**.
7. Phiếu nhập được tạo tự động kế thừa đúng sản phẩm và giá dự kiến. Khai báo các mã Serial/IMEI nhập về &rarr; Bấm **Xác nhận hoàn tất nhập kho**.
8. **Kiểm tra kết quả liên phân hệ:**
   - Tồn kho tăng ngay lập tức.
   - Tự động sinh đúng 01 khoản **Công nợ phải trả NCC** tại phân hệ Tài chính (với hạn thanh toán chuẩn theo NCC).

### Kịch bản 3: Kế toán thanh toán công nợ & Đối soát tài chính (Vai trò: `ketoan`)
1. Đăng nhập bằng tài khoản `ketoan` / `admin123`.
2. Vào **Công nợ phải trả** &rarr; Xem danh sách các khoản nợ và cảnh báo nợ quá hạn (màu đỏ).
3. Mở một khoản công nợ &rarr; Nhập số tiền chi trả &rarr; Bấm **Xác nhận chi thanh toán**.
4. Vào **Sổ quỹ thu - chi**: Xuất hiện ngay bút toán Chi tương ứng, số dư quỹ được cập nhật giảm.
5. Vào **Đối soát tài chính**: Xem bảng so sánh tự động:
   - Doanh thu bán hàng hoàn tất vs Tổng thu sổ quỹ (Khớp 100%).
   - Giá trị nhập kho hoàn tất vs Tổng công nợ gốc phát sinh (Khớp 100%).

### Kịch bản 4: Tiếp nhận bảo hành & Đổi mới 1-1 (Vai trò: `banhang`)
1. Đăng nhập bằng `banhang` / `admin123`.
2. Vào **Tra cứu IMEI/SĐT bảo hành** trên thanh tiêu đề &rarr; Gõ IMEI hoặc số điện thoại khách hàng.
3. Bấm **Tiếp nhận BH** &rarr; Chọn hình thức `Đổi máy mới (Đổi 1-1)`, nhập mô tả lỗi &rarr; Bấm **Tiếp nhận**.
4. Mở phiếu bảo hành vừa tạo &rarr; Chọn thiết bị thay thế mới trong kho &rarr; Bấm **Lưu kết quả xử lý**.
5. Máy cũ chuyển sang trạng thái `Lỗi`, máy mới chuyển sang `Đã xuất bán` và kích hoạt thời hạn bảo hành mới.

### Kịch bản 5: Hỗ trợ ra quyết định DSS & Tối ưu hóa OR-Tools (Vai trò: `quanly`)
1. Đăng nhập bằng tài khoản `quanly` / `admin123`.
2. Vào **Hỗ trợ ra quyết định DSS** &rarr; **Biên lợi nhuận**: Xem phân tích tỷ suất lợi nhuận gộp theo từng sản phẩm và nhóm hàng.
3. Vào **Dự báo nhu cầu**: Xem dự báo trung bình động 3 tháng (SMA-3M) và đối chiếu số liệu bán lịch sử.
4. Vào **Gợi ý nhập hàng**: Xem bảng tính toán tự động theo công thức nghiệp vụ:
   `Gợi ý = Dự báo + Tồn tối thiểu - Tồn khả dụng - Đã duyệt chưa về`.
5. Vào **Tối ưu OR-Tools**: Nhập hạn mức ngân sách (ví dụ: `50.000.000 đ`) &rarr; Bấm **Chạy tối ưu hóa**.
6. Hệ thống hiển thị kế hoạch phân bổ số lượng nhập tối ưu từng sản phẩm nhằm tối đa hóa lợi nhuận kỳ vọng dưới hạn mức ngân sách được cấp.

### Kịch bản 6: Quản trị Nhân sự, Chấm công thủ công & Tính - Chi lương (Vai trò: `nhansu`, `quanly`, `ketoan`)
1. Đăng nhập bằng tài khoản `nhansu` / `admin123`.
2. Vào **Quản trị Nhân sự** &rarr; **Hồ sơ nhân viên**: Xem và quản lý hợp đồng lao động, thông tin CCCD, bảo hiểm, ngân hàng và người phụ thuộc (D1).
3. Vào **Bảng chấm công**: Nhập giờ vào/ra thủ công cho nhân viên theo ca; hệ thống tự động kiểm tra chống trùng lặp; nếu chỉnh sửa công, hệ thống yêu cầu lý do và ghi nhận vào `AttendanceAuditLog` (D2).
4. Vào **Đơn xin nghỉ phép**: Tạo và duyệt đơn nghỉ phép; hệ thống tự động kiểm tra quota và trừ số ngày phép còn lại.
5. Vào **Bảng lương** &rarr; Bấm **Tạo bảng lương tháng**:
   - Hệ thống tự động tính lương cố định, phụ cấp, hoa hồng doanh số bán hàng từ F04, khấu trừ bảo hiểm 10.5%, giảm trừ gia cảnh và tính thuế TNCN theo biểu lũy tiến từng phần 7 bậc (D3).
6. Bấm **Trình phê duyệt** (duyệt qua 2 cấp: Quản lý duyệt &rarr; Kế toán duyệt) &rarr; Bấm **Khóa bảng lương**.
7. Đăng nhập tài khoản `ketoan` &rarr; Bấm **Xác nhận chi lương**: Hệ thống tự động sinh bút toán Chi vào Sổ quỹ `CashLedger` (F08).
8. Đăng nhập tài khoản `banhang` &rarr; Vào **Phiếu lương của tôi**: Chỉ xem được phiếu lương của chính mình, bảo đảm bảo mật tuyệt đối.

### Kịch bản 7: Quản trị Quan hệ Khách hàng CRM & Chuyển đổi F04 (Vai trò: `banhang`)
1. Đăng nhập tài khoản `banhang` / `admin123`.
2. Vào **CRM** &rarr; **Khách hàng tiềm năng (Lead)**: Bấm **Tạo Lead mới** (nhập nguồn tiếp cận, thông tin liên hệ).
3. Tại chi tiết Lead, bấm **Thêm hoạt động**: Ghi nhận cuộc gọi tư vấn, lịch gặp gỡ hoặc gửi báo giá.
4. Bấm **Chuyển thành Cơ hội bán hàng**: Chọn giai đoạn đàm phán, xác suất thành công và doanh thu dự kiến.
5. Khi đàm phán thành công (Stage: `CLOSED_WON`), bấm **Chuyển đổi sang Bán hàng (F04)**:
   - Hệ thống tự động tạo hồ sơ Khách hàng chính thức trong danh mục (`catalog.Customer`).
   - Tự động khởi tạo Đơn bán hàng Nháp (`sales.SalesOrder`) kế thừa thông tin và chuyển sang phân hệ F04 để chốt đơn và xuất kho.
6. Vào **Phễu bán hàng (Sales Funnel)**: Xem biểu đồ trực quan Chart.js phân tích tỷ lệ chuyển đổi qua các giai đoạn.

### Kịch bản 8: Quản lý Đa chi nhánh, Đa kho & Chuyển kho nội bộ (Vai trò: `kho`, `admin`)
1. Đăng nhập tài khoản `admin` / `admin123`.
2. Vào menu cấu hình Chi nhánh và Kho hàng: Hệ thống quản lý các chi nhánh (Hà Nội, TP.HCM, Đà Nẵng) và các kho vật lý trực thuộc.
3. Người dùng thuộc chi nhánh nào chỉ thấy dữ liệu và kho thuộc chi nhánh đó (Branch Scoping qua `accounts.scoping.get_scoped_queryset`).
4. Đăng nhập tài khoản `kho` / `admin123` &rarr; Vào **Tồn kho & Chuyển kho**:
   - Chọn kho xuất (ví dụ: `Kho Tổng Hà Nội`) và kho đích (ví dụ: `Kho Chi Nhánh Cầu Giấy`).
   - Chọn sản phẩm, số lượng và các mã Serial/IMEI cần chuyển &rarr; Bấm **Xác nhận điều chuyển**.
   - Hệ thống ghi nhận cặp giao dịch xuất `OUT` và nhập `IN`, cập nhật kho cho các thiết bị IMEI, bảo toàn 100% tổng tồn toàn công ty mà không phát sinh doanh thu hay công nợ.

---

## 6. TỔNG HỢP HIỆN TRẠNG KIỂM THỬ VÀ ĐỐI CHIẾU ĐẶC TẢ

Hệ thống đã trải qua rà soát toàn diện mã nguồn đối chiếu với bộ đặc tả kỹ thuật và nghiệp vụ:

- **Kết quả Kiểm thử tự động:** **39/39 Test Cases ĐẠT (100% PASSED)** thực thi trên nền tảng PostgreSQL (`test_g14_management` với cờ `--keepdb`).
- **Phân hệ hoàn thiện (DONE):**
  - Quản lý đa chi nhánh và đa kho (FR-24, QT21, TC36).
  - Phân hệ Quản trị nhân sự và Tiền lương mở rộng D1, D2, D3 (FR-26, QT23, TC39).
  - Động cơ phê duyệt đa bước có thể cấu hình (`approvals`).
  - Phân hệ Quản trị quan hệ khách hàng và Phễu bán hàng (`crm`).
  - 14 yêu cầu cốt lõi (FR-01 đến FR-17), 22 quy tắc nghiệp vụ (BR01 đến BR22) và 29 chỉ tiêu kiểm soát điều hành (TC01 đến TC29).
- **Phân hệ triển khai một phần (PARTIAL):**
  - Đổi trả & hoàn tiền (FR-23, QT20, TC34): Đã có bảo hành đổi mới 1-1 cho thiết bị IMEI, chưa có đổi trả thương mại hoàn tiền.
  - Tham số hệ thống (FR-18): Các giá trị cấu hình đang phân tán dưới dạng hằng số, chưa có bảng tham số tập trung.
  - Báo cáo chi nhánh (TC37): Dữ liệu chi nhánh đã có trên đơn bán, cần bổ sung hàm nhóm hiển thị riêng trên dashboard.
- **Phân hệ chưa triển khai (MISSING) theo lộ trình đề xuất (P1 - P3):**
  - Công nợ phải thu khách hàng (FR-20, QT16, TC32, TC33).
  - Bán hàng online & Cổng thanh toán (FR-21, QT19, TC35).
  - Quản lý giao vận và vận chuyển (FR-22, QT18, TC30, TC31).
  - Kế toán tổng hợp Double-Entry GL (FR-19, QT17, TC38).
  - Tích hợp EDI với nhà cung cấp (FR-25, QT22, TC40).

*Chi tiết toàn bộ kết quả rà soát, bảng ma trận và kiến trúc được ghi nhận tại thư mục `docs/`: [`SYSTEM_DOCUMENTATION.md`](docs/SYSTEM_DOCUMENTATION.md), [`ARCHITECTURE.md`](docs/ARCHITECTURE.md), [`TEST_REPORT.md`](docs/TEST_REPORT.md) và [`TECHNOLOGY_COMPARISON.md`](docs/TECHNOLOGY_COMPARISON.md).*
