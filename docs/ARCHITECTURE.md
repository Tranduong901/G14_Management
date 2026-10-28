# TÀI LIỆU KIẾN TRÚC HỆ THỐNG G14 MANAGEMENT
## HỆ THỐNG THÔNG TIN QUẢN TRỊ DOANH NGHIỆP PHÂN PHỐI SẢN PHẨM CÔNG NGHỆ

---

## 1. TỔNG QUAN KIẾN TRÚC HỆ THỐNG

Hệ thống G14 Management được xây dựng theo **Kiến trúc ba lớp (Three-Tier Architecture)** kết hợp với **Mô hình Hướng Dịch Vụ (Service-Oriented / Service Layer Pattern)** trên nền tảng **Python Django + MySQL**:

```text
+-----------------------------------------------------------------------------------+
|                            LỚP GIAO DIỆN (PRESENTATION TIER)                      |
|   - Django Templates (HTML5, Bootstrap 5, Bootstrap Icons)                        |
|   - Biểu đồ tương tác thời gian thực: Chart.js (Line, Doughnut, Bar)              |
|   - Bố cục: Responsive Sidebar, Top Navbar, Modal xác nhận, In hóa đơn/phiếu BH   |
+-----------------------------------------------------------------------------------+
                                         │  HTTP / POST / REST API
                                         ▼
+-----------------------------------------------------------------------------------+
|                            LỚP NGHIỆP VỤ (SERVICE LAYER TIER)                     |
|   - accounts.decorators: Phân quyền theo vai trò (ADMIN, QL, BH, KHO, KT)         |
|   - sales.services: Kiểm tra tồn, chốt đơn, kích hoạt bảo hành, ghi sổ thu        |
|   - purchasing.services: Nhập kho, kiểm soát Serial/IMEI, tự tạo công nợ          |
|   - inventory.services: Giao dịch kho, kiểm kê, kiểm soát hạn mức điều chỉnh     |
|   - devices.services: Tiếp nhận bảo hành, đổi mới 1-1, truy vết vòng đời thiết bị |
|   - finance.services: Sổ quỹ thu/chi, thanh toán công nợ, bút toán đảo           |
|   - scm.services: Lập & duyệt đề nghị nhập hàng, đánh giá năng lực nhà cung cấp   |
|   - dss.services: Dự báo nhu cầu 3 kỳ tháng (SMA-3M), gợi ý nhập hàng, OR-Tools  |
|   - auditlog.services: Ghi vết toàn bộ hành vi quan trọng (BR09)                  |
+-----------------------------------------------------------------------------------+
                                         │  Django ORM / transaction.atomic()
                                         ▼
+-----------------------------------------------------------------------------------+
|                            LỚP DỮ LIỆU DÙNG CHUNG (DATA TIER)                     |
|   - Cơ sở dữ liệu quan hệ dùng chung: MySQL (InnoDB, utf8mb4)                     |
|   - Khóa chính, Khóa ngoại, Chỉ mục tối ưu, Khóa duy nhất (Unique Constraints)   |
|   - Phục vụ báo cáo BI trực tiếp qua các SQL Views chuẩn bị sẵn                  |
+-----------------------------------------------------------------------------------+
```

---

## 2. PHÂN RÃ CÁC DJANGO APPS VÀ TRÁCH NHIỆM

Hệ thống được tổ chức thành 12 Django apps nghiệp vụ độc lập, có ranh giới trách nhiệm rõ ràng:

1. **`accounts` (FR-01):** Quản lý định danh người dùng (`User`), vai trò (`Role`: ADMIN, QL, BH, KHO, KT), xác thực, phân quyền theo URL và views.
2. **`hr` (FR-08):** Hồ sơ nhân viên (`Employee`), phòng ban, trạng thái công tác và liên kết tài khoản hệ thống.
3. **`catalog` (FR-02, FR-03, FR-04):** Danh mục Sản phẩm (`Product`), Khách hàng (`Customer`), Nhà cung cấp (`Supplier`).
4. **`devices` (FR-11):** Quản lý định danh từng máy theo Serial/IMEI (`ProductItem`), kích hoạt bảo hành điện tử và xử lý đổi trả bảo hành (`WarrantyReturn`).
5. **`inventory` (FR-07):** Quản lý biến động kho Nhập - Xuất - Tồn (`InventoryTransaction`), kiểm kê và điều chỉnh tồn kho (`StockAdjustment`).
6. **`purchasing` (FR-06):** Quản lý phiếu nhập hàng (`PurchaseReceipt`, `PurchaseDetail`), đối soát NCC.
7. **`sales` (FR-05):** Quản lý đơn bán hàng (`SalesOrder`, `SalesOrderDetail`), thanh toán, in hóa đơn.
8. **`finance` (FR-12, FR-13):** Phân hệ ERP tài chính cơ bản gồm Sổ quỹ thu - chi (`CashLedger`) và Công nợ phải trả NCC (`Payable`, `PayablePayment`).
9. **`scm` (FR-14, FR-15):** Phân hệ SCM gồm Đề nghị nhập hàng (`PurchaseRequest`), duyệt đề nghị, hồ sơ giá và đánh giá năng lực nhà cung cấp (`SupplierProduct`).
10. **`dss` (FR-16, FR-17):** Phân hệ DSS hỗ trợ ra quyết định gồm dự báo nhu cầu bán hàng (`ForecastResult`), công thức gợi ý nhập hàng và bộ giải tối ưu hóa ngân sách bằng Google OR-Tools.
11. **`reports` (FR-09):** Tổng hợp dữ liệu quản trị: Dashboard điều hành, báo cáo doanh thu, tồn kho, mua hàng, phân tích khách hàng.
12. **`auditlog` (FR-10):** Ghi nhật ký hệ thống toàn diện, truy vết người thực hiện, thời điểm, hành vi và chi tiết thay đổi dữ liệu (BR09).

---

## 3. CÁC LUỒNG DỮ LIỆU LIÊN PHÂN HỆ XUYÊN SUỐT (CROSS-MODULE DATA FLOWS)

Hệ thống loại bỏ hoàn toàn các trang CRUD rời rạc bằng cách xây dựng 2 luồng dữ liệu nghiệp vụ trọng tâm chạy xuyên suốt qua Service Layer:

### 3.1. Luồng A — Bán Hàng & Hoàn Tất Đơn (Sales Flow)
```text
[Nhân viên BH] Lập đơn bán (SalesOrder: DRAFT)
       │
       ▼
[sales.services.complete_sales_order] ──> Bắt đầu transaction.atomic()
       │
       ├─► 1. [catalog]: Kiểm tra tồn kho khả dụng (product.get_current_stock() >= qty) (BR03)
       ├─► 2. [devices]: Kiểm tra các mã Serial/IMEI đã chọn phải ở trạng thái 'IN_STOCK' (BR13)
       │                 Chuyển trạng thái IMEI sang 'SOLD' và kích hoạt thời hạn bảo hành (BR11)
       ├─► 3. [inventory]: Ghi nhận giao dịch kho OUT (InventoryTransaction)
       ├─► 4. [finance]: Ghi nhận bút toán Thu (CashLedger: RECEIPT) vào sổ quỹ (BR04, BR17)
       ├─► 5. [sales]: Cập nhật trạng thái đơn sang 'COMPLETED', ghi nhận KPI cho nhân viên (BR12)
       ├─► 6. [auditlog]: Ghi vết nhật ký hành động COMPLETE đơn hàng (BR09)
       ▼
   Commit Transaction -> Dữ liệu phản ánh tức thời lên Reports & DSS
```

### 3.2. Luồng B — Chuỗi Cung Ứng & Nhập Hàng (Procurement Flow)
```text
[DSS / Kho] Phát hiện tồn thấp -> Tính gợi ý số lượng nhập -> Lập Đề nghị nhập (SCM: DRAFT)
       │
       ▼
[Nhân viên Kho] Gửi duyệt đề nghị (PurchaseRequest: PENDING)
       │
       ▼
[Quản lý (QL)] Phê duyệt đề nghị (PurchaseRequest: APPROVED) (BR19)
       │
       ▼
[scm.services.convert_request_to_receipt] Chuyển đề nghị đã duyệt thành Phiếu nhập (DRAFT)
       │
       ▼
[purchasing.services.complete_purchase_receipt] ──> Bắt đầu transaction.atomic()
       │
       ├─► 1. [devices]: Kiểm tra tính hợp lệ và duy nhất của các mã IMEI nhập về
       │                 Tạo các bản ghi ProductItem với trạng thái 'IN_STOCK' (BR13)
       ├─► 2. [inventory]: Ghi nhận giao dịch kho IN (InventoryTransaction), tăng tồn kho (BR04)
       ├─► 3. [finance]: Tự động tạo đúng 01 khoản công nợ phải trả (Payable: UNPAID) (BR15)
       │                 Hạn thanh toán = Ngày nhập + Số ngày điều khoản NCC
       ├─► 4. [scm]: Ghi nhận thời gian giao hàng thực tế -> Cập nhật đánh giá NCC (TC24, TC25)
       ├─► 5. [purchasing]: Cập nhật trạng thái phiếu nhập sang 'COMPLETED'
       ├─► 6. [auditlog]: Ghi vết nhật ký nhập kho (BR09)
       ▼
   Commit Transaction -> Kho cập nhật, phát sinh công nợ phải trả trên Dashboard
```

---

## 4. MÔ HÌNH THỰC THỂ QUAN HỆ (ERD - LOGICAL & PHYSICAL DESIGN)

### 4.1. Thực thể chính và Quan hệ
- `accounts_user` (1) ── (1) `hr_employee`
- `accounts_user` (1) ── (N) `auditlog_auditlog`
- `catalog_customer` (1) ── (N) `sales_salesorder`
- `sales_salesorder` (1) ── (N) `sales_salesorderdetail`
- `catalog_product` (1) ── (N) `sales_salesorderdetail`
- `catalog_product` (1) ── (N) `devices_productitem`
- `catalog_product` (1) ── (N) `inventory_inventorytransaction`
- `devices_productitem` (1) ── (N) `devices_warrantyreturn`
- `catalog_supplier` (1) ── (N) `purchasing_purchasereceipt`
- `purchasing_purchasereceipt` (1) ── (N) `purchasing_purchasedetail`
- `purchasing_purchasereceipt` (1) ── (1) `finance_payable`
- `finance_payable` (1) ── (N) `finance_payablepayment`
- `finance_payablepayment` (1) ── (1) `finance_cashledger`
- `scm_purchaserequest` (1) ── (N) `scm_purchaserequestdetail`
- `scm_purchaserequest` (1) ── (N) `purchasing_purchasereceipt`

### 4.2. Ràng buộc toàn vẹn dữ liệu
- Khóa chính tự tăng `BigAutoField` trên mọi bảng.
- Khóa ngoại có ràng buộc `on_delete=models.PROTECT` đối với các bảng danh mục quan trọng (sản phẩm, khách hàng, nhà cung cấp) để ngăn chặn việc xóa dữ liệu đang được tham chiếu trong đơn hàng hoặc phiếu nhập.
- Khóa duy nhất (Unique Constraint) trên: Mã sản phẩm, Mã khách hàng, Mã nhà cung cấp, Mã Serial/IMEI, Mã đơn bán, Mã phiếu nhập, Mã công nợ, Mã đề nghị nhập hàng.
- Toàn bộ số tiền được lưu bằng kiểu dữ liệu `DecimalField(max_digits=15, decimal_places=2)` để triệt tiêu sai số làm tròn số thực.

