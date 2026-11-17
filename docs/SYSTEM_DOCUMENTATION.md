# Tài liệu hiện trạng hệ thống G14 Management

> **Phạm vi:** tài liệu này mô tả hiện trạng được kiểm tra từ mã nguồn, migration, cấu hình và test trong repository.  
> **Ngày rà soát:** 31/10/2026.  
> Các nội dung ghi là “chưa có” nghĩa là không tìm thấy trong mã nguồn hiện tại, không phải là tính năng được ngầm suy ra từ tài liệu thiết kế.

## 1. Cấu trúc thư mục dự án

### 1.1. Cây thư mục cấp cao

```text
G14_Management/
├── manage.py
├── requirements.txt
├── .env
├── .env.example
├── README.md
├── config/
│   ├── __init__.py
│   ├── api.py                   # DRF ViewSet và API dashboard
│   ├── asgi.py
│   ├── urls.py                  # URL root, include các app và api/v1
│   ├── wsgi.py
│   └── settings/
│       ├── __init__.py
│       ├── base.py               # cấu hình dùng chung, database, app, middleware
│       ├── dev.py                # DEBUG=True
│       └── prod.py               # DEBUG=False và thiết lập bảo mật cơ bản
├── accounts/                     # User, role, đăng nhập, decorator phân quyền
├── approvals/                    # Cấu hình và xử lý workflow phê duyệt
├── auditlog/                     # AuditLog, middleware và service ghi nhật ký
├── catalog/                      # Product, Customer, Supplier
├── devices/                      # ProductItem/Serial-IMEI và bảo hành
├── dss/                          # ForecastResult, dự báo và tối ưu mua hàng
├── finance/                      # CashLedger, Payable, PayablePayment
├── hr/                           # Employee
├── inventory/                    # InventoryTransaction, StockAdjustment
├── purchasing/                  # PurchaseReceipt, PurchaseDetail
├── reports/                     # dashboard và các báo cáo
├── sales/                       # SalesOrder, SalesOrderDetail
├── scm/                         # PurchaseRequest và hồ sơ NCC/sản phẩm
├── crm/                         # Lead, Opportunity, hoạt động và phễu bán hàng
├── templates/                   # giao diện Django Templates theo từng app
├── tests/
│   ├── test_all_requirements.py
│   ├── test_control_metrics.py
│   ├── test_phase1_approvals_branch.py
│   ├── test_phase2_hr_and_payroll.py
│   ├── test_phase4_crm.py
│   └── test_phase5_regressions.py
└── docs/
    ├── ARCHITECTURE.md
    ├── TECHNOLOGY_COMPARISON.md
    ├── TEST_REPORT.md
    └── SYSTEM_DOCUMENTATION.md  # tài liệu này
```

Không tìm thấy file `docker-compose.yml` hoặc `docker-compose.yaml` trong repository. Cấu hình hiện tại của `config/settings/base.py` yêu cầu PostgreSQL qua `DATABASE_URL`; không có cấu hình MySQL/SQLite fallback trong source hiện tại.

### 1.2. Các app Django và file chính

Mỗi app nghiệp vụ thường có các file:

- `apps.py`: khai báo `AppConfig`.
- `models.py`: model và enum/trạng thái dữ liệu.
- `services.py`: luồng nghiệp vụ có giao dịch (không phải app nào cũng có).
- `views.py`, `urls.py`, `forms.py`: giao diện và xử lý request.
- `admin.py`: đăng ký Django Admin.
- `migrations/0001_initial.py`: migration khởi tạo.

Các app cụ thể:

| App | Trách nhiệm | File nghiệp vụ chính |
|---|---|---|
| `accounts` | User, role, login, decorator | `models.py`, `decorators.py`, `context_processors.py`, `management/commands/seed_data.py` |
| `catalog` | Sản phẩm, khách hàng, nhà cung cấp | `models.py`, `forms.py`, `views.py` |
| `hr` | Hồ sơ nhân viên | `models.py`, `forms.py`, `views.py` |
| `sales` | Đơn bán và chi tiết đơn | `models.py`, `services.py`, `views.py` |
| `purchasing` | Phiếu nhập và chi tiết nhập | `models.py`, `services.py`, `views.py` |
| `inventory` | Giao dịch kho, kiểm kê/điều chỉnh | `models.py`, `services.py`, `views.py` |
| `devices` | Serial/IMEI, bảo hành/đổi máy | `models.py`, `services.py`, `views.py` |
| `finance` | Sổ quỹ, công nợ, thanh toán | `models.py`, `services.py`, `views.py` |
| `scm` | Đề nghị nhập hàng, giá và lead time NCC | `models.py`, `services.py`, `views.py` |
| `dss` | Dự báo, gợi ý nhập, OR-Tools | `models.py`, `services.py`, `views.py` |
| `reports` | Dashboard và báo cáo | `services.py`, `views.py` |
| `auditlog` | Nhật ký và middleware audit | `models.py`, `services.py`, `middleware.py`, `views.py` |

`config/urls.py` đăng ký URL HTML của 14 app và API DRF tại `/api/v1/`. `config/settings/base.py` là cấu hình trung tâm; `dev.py` và `prod.py` thay đổi thiết lập môi trường.

## 2. Môi trường và thư viện

### 2.1. Phiên bản

| Thành phần | Hiện trạng |
|---|---|
| Python đã kiểm tra trong môi trường hiện tại | **3.12.8** |
| Django đã kiểm tra trong môi trường hiện tại | **6.1.2** |
| Khoảng Django trong `requirements.txt` | `>=5.1.0,<6.2.0` |
| Cơ sở dữ liệu mục tiêu | PostgreSQL qua biến `DATABASE_URL`, SSL mặc định `require` |
| Driver PostgreSQL | `psycopg[binary] >=3.2.0` |
| API | Django REST Framework `>=3.15.0` |

Phiên bản Python/Django nêu trên là kết quả kiểm tra môi trường hiện tại; `requirements.txt` không khóa phiên bản Python.

### 2.2. `requirements.txt`

```text
Django>=5.1.0,<6.2.0
psycopg[binary]>=3.2.0
djangorestframework>=3.15.0
python-dotenv>=1.0.0
ortools>=9.10.0
pandas>=2.2.0
numpy>=1.26.0
openpyxl>=3.1.0
```

Không có Celery, Redis client, `django-celery-beat`, `kombu` hoặc thư viện message broker trong danh sách hiện tại.

### 2.3. Cấu hình database

`.env.example` đặt PostgreSQL:

```ini
DATABASE_URL=******host/database
```

`config/settings/base.py` ném lỗi nếu `DATABASE_URL` không được đặt, phân tích URL để cấu hình PostgreSQL và tự thêm `sslmode=require` nếu chưa có.

## 3. Mô hình dữ liệu

### 3.1. Bảng/model dùng chung

`accounts.BaseModel` là abstract model được nhiều app kế thừa, gồm:

- `created_at`: `DateTimeField(auto_now_add=True)`.
- `updated_at`: `DateTimeField(auto_now=True)`.
- `created_by`: nullable `ForeignKey` đến `accounts.User`, `on_delete=SET_NULL`.

Model người dùng tùy biến là `accounts.User`, kế thừa `AbstractUser`:

- các trường chuẩn của Django `AbstractUser`;
- `role`: `ADMIN`, `QL`, `BH`, `KHO`, `KT`, mặc định `BH`;
- `phone`;
- các property `is_admin`, `is_ql`, `is_bh`, `is_kho`, `is_kt`.

### 3.2. Danh mục và nhân sự

| Model | Trường chính |
|---|---|
| `catalog.Product` | `code`, `name`, `category`, `unit`, `price`, `cost_price`, `min_stock`, `has_serial`, `status`, `description` |
| `catalog.Customer` | `code`, `name`, `phone`, `email`, `address`, `customer_type`, `notes` |
| `catalog.Supplier` | `code`, `name`, `phone`, `email`, `address`, `payment_terms_days`, `notes` |
| `hr.Employee` | `code`, `full_name`, `department`, `position`, `phone`, `email`, `status`, `join_date`, `user` |

`Product.get_current_stock(branch=None, warehouse=None)` đếm `devices.ProductItem` ở trạng thái `IN_STOCK` cho hàng có serial; với hàng không serial, tính tổng các `inventory.InventoryTransaction` theo loại `IN/ADJUST_INC` trừ `OUT/ADJUST_DEC/WARRANTY_OUT`. Có thể lọc theo chi nhánh hoặc kho. Khi không truyền bộ lọc, dữ liệu cũ chưa gắn kho vẫn được tính trong tổng tồn toàn hệ thống.

`inventory.Warehouse` thuộc một `accounts.Branch`. Phiếu nhập, đơn bán, giao dịch kho và ProductItem mới đều lưu kho liên quan. `inventory.services.transfer_stock()` tạo cặp giao dịch xuất/nhập và chuyển ProductItem giữa hai kho, nên không làm thay đổi tổng tồn toàn hệ thống.

### 3.3. Bán hàng và mua hàng

| Model | Trường chính |
|---|---|
| `sales.SalesOrder` | `code`, `customer`, `staff`, `branch`, `warehouse`, `order_date`, `status`, `payment_method`, `payment_status`, `total_amount`, `completed_at`, `notes` |
| `sales.SalesOrderDetail` | `order`, `product`, `quantity`, `unit_price`, `total_price`, `selected_serials_text` |
| `purchasing.PurchaseReceipt` | `code`, `supplier`, `warehouse`, `request`, `receipt_date`, `status`, `total_amount`, `emergency_reason`, `notes`, `completed_at` |
| `purchasing.PurchaseDetail` | `receipt`, `product`, `quantity`, `unit_price`, `total_price`, `serials_text` |

Trạng thái nghiệp vụ chính:

- Đơn bán: `DRAFT`, `COMPLETED`, `CANCELLED`.
- Phiếu nhập: `DRAFT`, `COMPLETED`, `CANCELLED`.

### 3.4. Các model được yêu cầu kiểm tra

#### `auditlog.AuditLog` (bảng logic `auditlog_auditlog`)

- `user`: FK đến `accounts.User`, nullable, `SET_NULL`.
- `action`: `LOGIN`, `LOGOUT`, `CREATE`, `UPDATE`, `DELETE`, `COMPLETE`, `CANCEL`, `APPROVE`, `REJECT`, `ADJUST`, `PAYMENT`, `REVERSE`.
- `app_label`, `model_name`, `object_id`, `object_repr`.
- `changes_json`: `JSONField(default=dict)`.
- `ip_address`.
- `created_at`.

Middleware và `auditlog.services.log_activity` được dùng để ghi vết các hành động quan trọng.

#### `finance.CashLedger` (bảng logic `finance_cashledger`)

- `code`, `entry_date`, `transaction_type` (`RECEIPT`/`PAYMENT`), `amount`.
- `payment_method` (`CASH`/`BANK_TRANSFER`).
- `reference_type`, `reference_id`, `reason`.
- `recorded_by`: FK đến User.
- `is_reversed`, `reversal_of`: FK tự tham chiếu nullable.

#### `inventory.InventoryTransaction` (bảng logic `inventory_inventorytransaction`)

- `transaction_type`: `IN`, `OUT`, `ADJUST_INC`, `ADJUST_DEC`, `WARRANTY_OUT`.
- `product`: FK đến `catalog.Product`, `PROTECT`.
- `warehouse`: FK đến `inventory.Warehouse`, nullable để tương thích dữ liệu cũ.
- `quantity`, `reference_code`, `notes`, `transaction_date`.

Đây là lịch sử biến động kho; tồn hiện tại được tính từ các giao dịch hoặc đếm ProductItem tùy loại sản phẩm.

#### `devices.ProductItem` (bảng logic `devices_productitem`)

- `serial_number`: mã Serial/IMEI duy nhất.
- `product`: FK đến Product, `PROTECT`.
- `status`: `IN_STOCK`, `SOLD`, `DEFECTIVE`, `RETURNED`.
- `purchase_receipt`: FK nullable đến PurchaseReceipt, `SET_NULL`.
- `sales_order`: FK nullable đến SalesOrder, `SET_NULL`.
- `warehouse`: FK nullable đến Warehouse, `SET_NULL`.
- `warranty_months`, `warranty_start_date`, `warranty_end_date`.

Khi hoàn tất đơn bán, ProductItem chuyển từ `IN_STOCK` sang `SOLD` và kích hoạt ngày bắt đầu/kết thúc bảo hành.

#### `outbox_event` và `idempotency_key`

Không tìm thấy model, migration, bảng, service, command hoặc chuỗi tham chiếu đến `OutboxEvent`, `outbox_event`, `IdempotencyKey` hay `idempotency_key`. Hai bảng này **chưa được triển khai**.

### 3.5. Các model nghiệp vụ còn lại

| App/model | Mục đích và trường đáng chú ý |
|---|---|
| `devices.WarrantyReturn` | `code`, `item`, `customer`, `issue_description`, `action_type`, `replacement_item`, `status`, ngày tiếp nhận/giải quyết |
| `finance.Payable` | `code`, `supplier`, `purchase_receipt` (OneToOne), `total_amount`, `paid_amount`, `remaining_amount`, `due_date`, `status` |
| `finance.PayablePayment` | `payable`, `payment_date`, `amount`, `payment_method`, `ledger_entry`, `notes` |
| `inventory.StockAdjustment` | `code`, `product`, tồn hệ thống/thực tế/chênh lệch, giá trị chênh lệch, lý do, trạng thái duyệt, người duyệt |
| `scm.SupplierProduct` | `supplier`, `product`, `last_purchase_price`, `standard_lead_days` |
| `scm.PurchaseRequest` | `code`, `status`, `source`, requester/approver, thời điểm duyệt, lý do từ chối |
| `scm.PurchaseRequestDetail` | request, product, supplier đề xuất, số lượng, giá và tổng tiền dự kiến |
| `dss.ForecastResult` | product, kỳ/phương pháp dự báo, số lượng dự báo/thực tế, error rate, thời điểm tính |
| `auditlog.AuditLog` | nhật ký hành động và dữ liệu thay đổi dạng JSON |

## 4. Ràng buộc dữ liệu

### 4.1. Unique đã khai báo

Các trường `unique=True`:

- `Product.code`.
- `Customer.code`, `Customer.phone`.
- `Supplier.code`, `Supplier.phone`.
- `Employee.code`.
- `SalesOrder.code`.
- `PurchaseReceipt.code`.
- `ProductItem.serial_number`.
- `WarrantyReturn.code`.
- `CashLedger.code`.
- `Payable.code`.
- `StockAdjustment.code`.
- `PurchaseRequest.code`.

Ràng buộc kết hợp:

- `scm.SupplierProduct.Meta.unique_together = ['supplier', 'product']`.

Ràng buộc One-to-one:

- `finance.Payable.purchase_receipt` là `OneToOneField`, nên mỗi phiếu nhập chỉ có tối đa một Payable.
- `hr.Employee.user` là `OneToOneField`, nên một User chỉ có tối đa một hồ sơ Employee.

### 4.2. Khóa ngoại và hành vi xóa

- Các quan hệ nghiệp vụ tới Product, Customer, Supplier và ProductItem chủ yếu dùng `PROTECT` để ngăn xóa dữ liệu đã phát sinh giao dịch.
- Quan hệ audit/người tạo dùng `SET_NULL` để giữ lịch sử khi User bị xóa.
- Chi tiết đơn/phiếu dùng `CASCADE` theo bản ghi cha.
- ProductItem liên kết phiếu nhập/đơn bán dùng `SET_NULL`.
- Payable liên kết PurchaseReceipt dùng `PROTECT`; PayablePayment liên kết Payable dùng `CASCADE`.
- CashLedger.reversal_of dùng `SET_NULL`.

### 4.3. Ràng buộc và optimistic locking

- Không tìm thấy `models.CheckConstraint`, `CheckConstraint`, `UniqueConstraint` hoặc `RunSQL` tạo CHECK trong các model/migration hiện tại.
- `choices` chỉ là ràng buộc ở tầng Django/model form; không được khai báo thành CHECK constraint ở database.
- Không có trường `version` trong `BaseModel` hoặc các model nghiệp vụ.
- Không có cơ chế kiểm tra version kiểu optimistic locking (`UPDATE ... WHERE version = ...`) trong service.
- Các quy tắc như số lượng dương, trạng thái chuyển tiếp, không bán vượt tồn và không dùng lại serial hiện chủ yếu được kiểm tra trong service và test.

## 5. Tích hợp và xử lý sự kiện

### 5.1. Cách ghi “sự kiện” hiện tại

Hệ thống hiện không có transactional outbox. Các service ghi trực tiếp nhiều bảng trong cùng transaction:

- Hoàn tất bán hàng: tạo `InventoryTransaction(OUT)`, cập nhật `ProductItem`, cập nhật `SalesOrder`, tạo/lấy `CashLedger(RECEIPT)`, rồi ghi `AuditLog`.
- Hoàn tất nhập hàng: tạo ProductItem, tạo `InventoryTransaction(IN)`, cập nhật `SupplierProduct`, cập nhật `PurchaseReceipt`, tạo/lấy `Payable`, rồi ghi `AuditLog`.
- Thanh toán công nợ/đảo sổ quỹ: cập nhật finance và ghi audit trực tiếp.

`CashLedger` và `AuditLog` là các bản ghi nghiệp vụ/audit, không phải outbox event để giao cho worker bên ngoài.

### 5.2. Command, handler và broker

| Hạng mục | Hiện trạng |
|---|---|
| Model/bảng `outbox_event` | Chưa có |
| Model/bảng `idempotency_key` | Chưa có |
| `process_outbox` management command | Chưa có |
| Event handler/consumer | Chưa có |
| Celery | Chưa có trong code và requirements |
| Redis | Chưa có trong code, requirements hoặc cấu hình |
| Tác vụ bất đồng bộ | Chưa có worker/broker; service chạy đồng bộ trong request/command |
| Django management command | Có `accounts/management/commands/seed_data.py` để tạo dữ liệu mẫu |

### 5.3. API và tích hợp hiện có

DRF router được đăng ký tại `/api/v1/` cho `products`, `customers`, `orders`; ngoài ra có:

- `/api/v1/dashboard-stats/`.
- `/api/v1/procurement-suggestions/`.

Đây là REST API đồng bộ, không phải cơ chế phát sự kiện bất đồng bộ.

## 6. Transaction và khóa

### 6.1. Các nơi dùng `transaction.atomic`

Decorator `@transaction.atomic` đã được tìm thấy tại:

- `sales/services.py`: hoàn tất và hủy đơn hàng.
- `purchasing/services.py`: hoàn tất và hủy phiếu nhập.
- `inventory/services.py`: tạo, áp dụng, duyệt và từ chối điều chỉnh kho.
- `finance/services.py`: các thao tác ghi sổ, thanh toán/đảo bút toán.
- `devices/services.py`: xử lý claim bảo hành/đổi máy.
- `scm/services.py`: gửi duyệt, phê duyệt, từ chối và chuyển đề nghị thành phiếu nhập.

Các transaction này bảo đảm rollback khi service ném `ValidationError`. Test `test_12_transaction_rollback_on_error` kiểm tra trường hợp lỗi ở dòng sau không để lại cập nhật dở dang.

### 6.2. Khóa hàng và kiểm tra version

- `select_for_update()` có trong các service hoàn tất bán hàng, nhập hàng và thanh toán công nợ để khóa các bản ghi liên quan trong transaction.
- Không có `version` field và không có kiểm tra version.
- Do đó, các luồng đọc tồn rồi cập nhật ProductItem/InventoryTransaction chưa thể hiện cơ chế khóa pessimistic hoặc optimistic locking rõ ràng.
- Tính “idempotent” hiện tại chủ yếu là kiểm tra trạng thái (`COMPLETED`/`CANCELLED`) và dùng `get_or_create` cho Payable/CashLedger; chưa có khóa idempotency theo request/event.

## 7. Phân quyền

### 7.1. Vai trò đang có

`accounts.Role` khai báo 6 vai trò:

| Mã | Ý nghĩa | Quyền nghiệp vụ theo thiết kế |
|---|---|---|
| `ADMIN` | Quản trị hệ thống | Toàn quyền; superuser luôn được cho qua decorator |
| `QL` | Quản lý doanh nghiệp | Dashboard, báo cáo, phê duyệt và các thao tác quản lý |
| `BH` | Nhân viên bán hàng | Sản phẩm, khách hàng, đơn bán, serial/bảo hành liên quan |
| `KHO` | Nhân viên kho | Nhập kho, serial/IMEI, kiểm kê, đề nghị nhập |
| `KT` | Kế toán | Sổ quỹ, công nợ, thanh toán và đối soát |
| `HR` | Nhân sự | Hồ sơ nhân viên, chấm công, nghỉ phép và bảng lương |

`seed_data` tạo các tài khoản demo cho các vai trò nghiệp vụ; danh sách cụ thể cần đối chiếu trực tiếp với command tại thời điểm triển khai.

### 7.2. Cơ chế thực thi

- View dùng `@role_required([...])` hoặc `RoleRequiredMixin`.
- User chưa đăng nhập được chuyển tới login.
- Superuser được bypass kiểm tra role.
- User sai role nhận thông báo và được chuyển về dashboard.
- `AUTH_USER_MODEL = 'accounts.User'`.

### 7.3. Django Groups/Permissions

Django vẫn có các bảng mặc định `auth_group`, `auth_permission` và quan hệ `User.groups`, `User.user_permissions` do `AbstractUser` kế thừa. Tuy nhiên:

- Không tìm thấy code tạo các Group nghiệp vụ tương ứng với 5 role.
- Không tìm thấy code gán `Permission` theo role.
- Phân quyền đang dùng role string và decorator, không dùng Django Group/Permission làm nguồn kiểm tra chính.

## 8. Chức năng đã kiểm thử và phần còn dở

### 8.1. Bộ test đã có

`tests/test_all_requirements.py` chứa lớp `G14SystemComprehensiveTestCase`. Ngoài ra repository hiện có các nhóm test approval/branch, control metrics, HR/payroll, CRM và regression; tổng cộng 39 method `test_` được phát hiện trong source.

```text
Ran 14 tests in 43.645s
OK
```

Đoạn log trên là kết quả lịch sử được lưu trong tài liệu cũ, không phải kết quả
thực thi mới của toàn bộ 39 test. Xem [TEST_REPORT.md](TEST_REPORT.md) để biết
trạng thái xác minh hiện tại.

Các nhóm chức năng đã được kiểm thử:

1. Tạo Product và chặn trùng mã.
2. Hoàn tất nhập hàng làm tăng tồn, tạo ProductItem và Payable.
3. Hoàn tất bán hàng làm giảm tồn, chuyển serial sang SOLD và kích hoạt bảo hành.
4. Phiếu nhập nháp không cập nhật tồn/công nợ.
5. Đơn nháp/hủy không ảnh hưởng tồn và doanh thu.
6. Chặn bán vượt tồn.
7. Chặn tái sử dụng serial đã bán.
8. Không tạo trùng Payable cho một phiếu nhập.
9. Không hoàn tất đơn bán hai lần, không ghi trùng doanh thu/sổ quỹ.
10. Không cho thanh toán Payable vượt số còn nợ.
11. Chặn chuyển đề nghị nhập chưa duyệt hoặc chuyển lặp.
12. Rollback toàn bộ transaction khi lỗi giữa luồng.
13. Kiểm tra phân quyền backend cho BH, KT và QL.
14. Báo cáo/DSS chỉ dùng giao dịch hoàn tất và kiểm tra gợi ý mua hàng.

Ngoài ra, code đã có các luồng giao diện cho catalog, sales, purchasing, inventory, devices, finance, SCM, DSS, reports, auditlog, accounts và HR; có API DRF cơ bản.

### 8.2. Các phần chưa có hoặc cần hoàn thiện

Các hạng mục sau chưa được triển khai hoặc chưa có bằng chứng trong repository:

- `outbox_event`, `idempotency_key`, `process_outbox` và event handlers.
- Celery, Redis và worker bất đồng bộ.
- Cột `version` và optimistic locking; một số service đã dùng `select_for_update` nhưng chưa phải mọi luồng cập nhật đều có cơ chế khóa đồng nhất.
- CHECK constraints ở database cho các điều kiện số lượng, số tiền và trạng thái.
- Cấu hình `docker-compose.yml` cho PostgreSQL và các dịch vụ phụ trợ.
- Seed Django Groups/Permissions; hiện chỉ seed User role.
- Bộ test concurrency, khóa hàng, retry event, duplicate request và crash giữa commit/dispatch.
- Cơ chế retry/dead-letter/monitoring cho tích hợp bất đồng bộ.

### 8.3. Các điểm cần lưu ý khi triển khai

- `base.py` yêu cầu `DATABASE_URL` PostgreSQL; cần cung cấp biến môi trường và kiểm tra SSL khi triển khai production.
- `requirements.txt` dùng khoảng phiên bản, không khóa chính xác phiên bản; nên dùng lock file nếu cần tái lập môi trường.
- Mật khẩu demo và `SECRET_KEY` trong `.env.example` chỉ phù hợp cho môi trường học tập/dev, không dùng nguyên trạng ở production.
- Những quy tắc đang chỉ kiểm tra tại service nên vẫn cần bổ sung ràng buộc database hoặc cơ chế khóa nếu hệ thống chạy đồng thời nhiều worker/request.
