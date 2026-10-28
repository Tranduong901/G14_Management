# HỆ THỐNG THÔNG TIN QUẢN TRỊ DOANH NGHIỆP G14 (G14 SYSTEM)
## PHÂN PHỐI VÀ KINH DOANH THIẾT BỊ CÔNG NGHỆ

Hệ thống thông tin quản trị doanh nghiệp toàn diện phục vụ chuỗi phân phối thiết bị công nghệ (Smartphone, Tablet, Laptop, Phụ kiện), quản lý từng thiết bị theo mã Serial/IMEI, bảo hành điện tử, chuỗi cung ứng SCM, kế toán quản trị dòng tiền ERP và hệ thống hỗ trợ ra quyết định DSS tối ưu hóa bằng Google OR-Tools.

---

## 1. CÔNG NGHỆ NỀN TẢNG

- **Backend:** Python 3.12 + Django 6.1.2.
- **Database:** MySQL 8.x / MariaDB (kết nối qua PyMySQL với cấu hình utf8mb4, InnoDB, strict mode).
- **ORM:** Django ORM với Service Layer Pattern & Transaction Atomic (ACID).
- **Frontend:** Django Templates, HTML5, CSS3, JavaScript, Bootstrap 5.3, Bootstrap Icons.
- **Biểu đồ trực quan:** Chart.js (Line chart, Doughnut chart, Bar chart).
- **Tối ưu hóa toán học:** Google OR-Tools (MIP Linear Programming với bộ giải SCIP / CBC).
- **REST API:** Django REST Framework (DRF) v3.15+.
- **Quản lý cấu hình:** python-dotenv (`.env`).

---

## 2. DANH SÁCH TÀI KHOẢN DEMO HỆ THỐNG

Hệ thống đã chuẩn bị sẵn 5 tài khoản tương ứng với 5 vai trò phân quyền nghiệp vụ độc lập:

| Tên đăng nhập | Mật khẩu mặc định | Vai trò (Role) | Chức danh mẫu | Quyền hạn chính trong hệ thống |
| :--- | :--- | :---: | :--- | :--- |
| `admin` | `admin123` | **ADMIN** | Quản trị hệ thống | Quản trị tài khoản, phân quyền, xem toàn bộ nhật ký hệ thống (Audit Log). |
| `quanly` | `admin123` | **QL** | Giám đốc điều hành | Xem Dashboard điều hành, xem báo cáo doanh thu, phê duyệt đề nghị nhập hàng (SCM), phê duyệt kiểm kê kho, phân tích DSS. |
| `banhang` | `admin123` | **BH** | Chuyên viên bán hàng | Tra cứu sản phẩm, quản lý khách hàng, lập đơn bán hàng, chỉ định Serial/IMEI, tiếp nhận bảo hành. |
| `kho` | `admin123` | **KHO** | Trưởng kho thiết bị | Nhập hàng, khai báo Serial/IMEI, kiểm kê điều chỉnh kho, lập đề nghị nhập hàng (SCM). |
| `ketoan` | `admin123` | **KT** | Kế toán trưởng | Xem doanh thu bán hàng, quản lý sổ quỹ thu - chi, theo dõi công nợ NCC, chi trả nợ và đối soát tài chính. |

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
│   │   ├── base.py
│   │   ├── dev.py
│   │   └── prod.py
│   ├── urls.py
│   ├── api.py
│   ├── wsgi.py
│   └── asgi.py
├── accounts/         # FR-01: Tài khoản, phân quyền RBAC
├── catalog/          # FR-02, 03, 04: Sản phẩm, Khách hàng, NCC
├── hr/               # FR-08: Quản lý nhân viên
├── sales/            # FR-05: Đơn bán hàng, thanh toán, in hóa đơn
├── purchasing/       # FR-06: Phiếu nhập hàng, kiểm soát IMEI
├── inventory/        # FR-07: Kho hàng, lịch sử xuất nhập, kiểm kê
├── devices/          # FR-11: Quản lý Serial/IMEI, bảo hành, đổi mới
├── finance/          # FR-12, 13: ERP Sổ quỹ thu chi, công nợ NCC
├── scm/              # FR-14, 15: SCM Đề nghị nhập, đánh giá NCC
├── dss/              # FR-16, 17: DSS Dự báo SMA, gợi ý nhập, OR-Tools
├── reports/          # FR-09: Executive Dashboard, 6 nhóm báo cáo
├── auditlog/         # FR-10: Nhật ký hệ thống & truy vết
├── templates/        # Giao diện tiếng Việt chuẩn Bootstrap 5
├── static/           # Tài nguyên tĩnh CSS, JS
├── tests/            # Test suite 14 ca kiểm thử bắt buộc
└── docs/             # Tài liệu kiến trúc, so sánh công nghệ, test report
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

### Bước 3: Cấu hình Cơ sở dữ liệu MySQL
1. Khởi động MySQL Server (ví dụ qua XAMPP, WampServer hoặc Windows MySQL Service).
2. Tạo database:
   ```sql
   CREATE DATABASE g14_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```
3. Cập nhật thông tin kết nối trong file `.env`:
   ```ini
   DB_ENGINE=django.db.backends.mysql
   DB_NAME=g14_db
   DB_USER=root
   DB_PASSWORD=root
   DB_HOST=127.0.0.1
   DB_PORT=3306
   DB_FALLBACK_SQLITE=True
   ```
   *(Ghi chú: Nếu môi trường máy chưa bật MySQL server, hệ thống sẽ tự động fallback sang SQLite dev database để đảm bảo server và test suite chạy mượt mà không bị crash).*

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

### Bước 6: Chạy kiểm thử tự động (14 Test Cases bắt buộc)
```powershell
python manage.py test tests
```
*Kết quả mong đợi: `Ran 14 tests ... OK (100% Passed)`.*

### Bước 7: Khởi động máy chủ Web Django
```powershell
python manage.py runserver 127.0.0.1:8000
```
Truy cập hệ thống tại: **[http://127.0.0.1:8000](http://127.0.0.1:8000)**

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

