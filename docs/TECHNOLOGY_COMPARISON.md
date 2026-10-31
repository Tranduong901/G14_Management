# BÁO CÁO NGHIÊN CỨU & SO SÁNH CÔNG NGHỆ
## HỆ THỐNG QUẢN TRỊ DOANH NGHIỆP G14 MANAGEMENT

Tài liệu này trình bày kết quả nghiên cứu công nghệ, đánh giá so sánh và kế hoạch tích hợp đối với 3 nhóm giải pháp trọng tâm:
1. **ERP: ERPNext vs Kiến trúc Django Apps G14**
2. **Hoạch định cung ứng & Tối ưu hóa: frePPLe vs Google OR-Tools**
3. **Khai phá dữ liệu & Báo cáo BI: Power BI vs Metabase**

---

## 1. PHÂN HỆ ERP: NGHIÊN CỨU ERPNEXT VÀ ĐỐI CHIẾU VỚI G14 DJANGO

### 1.1. Giới thiệu tổng quan về ERPNext
ERPNext là hệ thống ERP mã nguồn mở hàng đầu thế giới được xây dựng trên nền tảng **Frappe Framework (Python + MariaDB/MySQL + JavaScript/Vue)**. ERPNext cung cấp một bộ giải pháp toàn diện cho doanh nghiệp từ sản xuất, phân phối, bán lẻ đến nhân sự và tài chính kế toán.

### 1.2. So sánh các phân hệ chức năng giữa ERPNext và G14 Django System

| Phân hệ nghiệp vụ | Chức năng trong ERPNext | Chức năng tương ứng trong G14 System | Đánh giá so sánh |
| :--- | :--- | :--- | :--- |
| **Mua hàng (Purchasing)** | Material Request, Request for Quotation (RFQ), Purchase Order (PO), Purchase Receipt, Purchase Invoice. | `scm`: PurchaseRequest (lập & duyệt).<br>`purchasing`: PurchaseReceipt & PurchaseDetail. | ERPNext có luồng RFQ phức tạp hơn; G14 tinh gọn vào quy trình đề nghị - duyệt - phiếu nhập, trực tiếp gắn với NCC theo chuẩn BR19. |
| **Bán hàng (Sales)** | Quotation, Sales Order, Delivery Note, Sales Invoice. Hỗ trợ điểm bán hàng POS. | `sales`: SalesOrder & SalesOrderDetail.<br>In hóa đơn bán hàng trực tiếp. | G14 tối ưu hóa cho bán lẻ công nghệ trực tiếp tại quầy, kiểm tra tồn khả dụng tức thời và gán Serial/IMEI ngay khi chốt đơn. |
| **Quản lý Kho (Inventory)** | Item Master, Serial No & Batch No tracking, Stock Entry, Stock Reconciliation, Multi-warehouse. | `inventory`: InventoryTransaction, StockAdjustment.<br>`devices`: ProductItem (IMEI), WarrantyReturn. | G14 chuyên biệt hóa cho sản phẩm công nghệ: mỗi máy một IMEI độc nhất, tự động kích hoạt bảo hành điện tử khi bán và xử lý đổi trả 1-1. |
| **Tài chính (Finance/Accounting)** | Sổ cái (General Ledger), Bảng cân đối, Thuế, Đa tiền tệ, Tài khoản ngân hàng, Khấu hao tài sản. | `finance`: Sổ quỹ (CashLedger - Thu/Chi) & Công nợ phải trả NCC (Payable). | ERPNext cung cấp hệ thống kế toán tài chính chuyên sâu (Chart of Accounts). G14 tập trung vào kế toán quản trị dòng tiền thực tế (Cashflow) và đối soát công nợ mua hàng (BR15 - BR17). |
| **Nhân sự (HR)** | Chấm công, Bảng lương, Tuyển dụng, Đánh giá năng lực. | `hr`: Employee (hồ sơ nhân viên, phòng ban, liên kết tài khoản và tính doanh số KPI). | G14 tinh giản hóa phục vụ quản lý thông tin nhân viên và gắn trực tiếp với hiệu suất bán hàng (TC06). |

### 1.3. Phương án tích hợp hoặc lý do lựa chọn tự xây dựng trên Django
* **Lý do lựa chọn tự xây dựng trên Django:**
  1. **Tính linh hoạt và độc lập nghiệp vụ:** Doanh nghiệp G14 là mô hình phân phối công nghệ quy mô vừa, quy trình theo dõi Serial/IMEI và bảo hành đổi trả đòi hỏi tính thời gian thực và liên kết chặt chẽ với đơn bán hàng mà không bị ràng buộc bởi các bước thủ tục hạch toán kế toán quá cồng kềnh của ERPNext.
  2. **Hiệu năng và khả năng làm chủ công nghệ:** Django cung cấp ORM mạnh mẽ, mô hình service layer tách bạch (`services.py`), bảo đảm toàn vẹn giao dịch ACID bằng `transaction.atomic()`, dễ bảo trì và mở rộng hơn so với việc tùy biến hệ thống monolithic phức tạp của ERPNext.
  3. **Tối ưu trải nghiệm tiếng Việt:** Giao diện Django Templates kết hợp Bootstrap 5 giúp tùy biến linh hoạt, thân thiện và chính xác với thuật ngữ quản trị nội bộ của G14.
* **Phương án tích hợp với ERPNext (nếu doanh nghiệp mở rộng quy mô):**
  - Sử dụng REST API của ERPNext (`/api/resource/Purchase Invoice`, `/api/resource/Sales Invoice`).
  - G14 đóng vai trò Front-Office & Kho vận vận hành: khi đơn bán hoặc phiếu nhập hoàn tất, G14 đẩy dữ liệu giao dịch sang ERPNext qua Webhook/REST API để hạch toán sổ cái và báo cáo thuế tập trung.

---

## 2. HOẠCH ĐỊNH CUNG ỨNG: SO SÁNH FREPPLE VÀ PYTHON OR-TOOLS

### 2.1. Mục đích, sự khác biệt và trường hợp sử dụng

| Tiêu chí | frePPLe | Google OR-Tools |
| :--- | :--- | :--- |
| **Bản chất** | Hệ thống lập kế hoạch cung ứng nâng cao hoàn chỉnh (Advanced Planning and Scheduling - APS). | Bộ thư viện mã nguồn mở giải các bài toán tối ưu hóa toán học (Operations Research). |
| **Công nghệ nền tảng** | C++ core solver kết hợp giao diện Web Django + PostgreSQL. | C++ wrapper cho Python, Java, C#, C++. |
| **Trường hợp sử dụng** | Lập kế hoạch sản xuất đa tầng (BOM), điều độ chuyền sản xuất, dự báo nhu cầu đa chuỗi phức tạp. | Tối ưu hóa phân bổ nguồn lực, tối ưu ngân sách nhập hàng (Knapsack/MIP), định tuyến xe (VRP), xếp lịch ca làm việc. |
| **Độ phức tạp triển khai** | Nặng, đòi hỏi cơ sở hạ tầng server riêng, cấu hình cơ sở dữ liệu và đồng bộ định kỳ. | Nhẹ, nhúng trực tiếp dạng module Python (`import ortools`) vào backend Django. |
| **Tính phù hợp với G14** | Phù hợp với nhà máy sản xuất linh kiện; **quá phức tạp** đối với chuỗi bán lẻ 1 cơ sở của G14. | **Rất phù hợp:** Tích hợp trực tiếp vào phân hệ DSS để giải bài toán tối ưu hóa phân bổ ngân sách nhập hàng. |

### 2.2. Thử nghiệm thực tế bài toán tối ưu hóa nhập hàng bằng OR-Tools trong G14

G14 đã triển khai thành công bài toán **Quy hoạch tuyến tính số nguyên hỗn hợp (Mixed-Integer Programming - MIP)** trong module `dss.services.optimize_procurement_ortools`.

#### Mô hình toán học:
- **Biến quyết định:** $x_i \in \mathbb{Z}_{\ge 0}$ là số lượng sản phẩm $i$ cần nhập.
- **Hàm mục tiêu:** Tối đa hóa tổng lợi nhuận gộp kỳ vọng:
  $$\max \sum_{i} x_i \times (\text{price}_i - \text{cost\_price}_i)$$
- **Ràng buộc:**
  1. Hạn mức ngân sách khả dụng:
     $$\sum_{i} x_i \times \text{cost\_price}_i \le \text{Budget}$$
  2. Giới hạn nhu cầu tiêu thụ và sức chứa kho:
     $$x_i \le \text{Demand\_Cap}_i$$
  3. Mức tối thiểu cho các sản phẩm đang có tồn kho dưới ngưỡng an toàn:
     $$x_i \ge 1 \quad (\text{với các mặt hàng tồn thấp})$$

#### Kết quả thực nghiệm với ngân sách 50.000.000 VNĐ:
- **Trạng thái Solver:** `OPTIMAL` (Thuật toán SCIP / CBC tìm thấy nghiệm tối ưu toàn cục).
- **Phân bổ tối ưu:**
  - Nhập 02 chiếc iPad Pro M4 (SP04) (Vốn: 42.000.000 đ | Lợi nhuận kỳ vọng: 7.980.000 đ)
  - Nhập 11 chiếc Củ sạc nhanh Anker 65W (SP05) (Vốn: 4.950.000 đ | Lợi nhuận kỳ vọng: 2.640.000 đ)
  - Nhập 20 sợi Cáp Type-C Anker 100W (SP06) (Vốn: 3.000.000 đ | Lợi nhuận kỳ vọng: 2.000.000 đ)
- **Tổng vốn sử dụng:** 49.950.000 VNĐ / 50.000.000 VNĐ (Hiệu suất sử dụng vốn: **99.9%**).
- **Tổng lợi nhuận kỳ vọng:** **12.620.000 VNĐ**.

---

## 3. BÁO CÁO VÀ TRUY VẤN BI: SO SÁNH POWER BI VÀ METABASE

### 3.1. So sánh Power BI và Metabase

| Tiêu chí | Microsoft Power BI | Metabase |
| :--- | :--- | :--- |
| **Loại hình** | Nền tảng phân tích doanh nghiệp thương mại (Desktop + Cloud Service). | Nền tảng BI mã nguồn mở (Self-hosted trên Docker / Web JAR). |
| **Kết nối cơ sở dữ liệu** | Trực tiếp qua PostgreSQL connector, import data hoặc DirectQuery. | Kết nối trực tiếp native qua JDBC Driver tới PostgreSQL. |
| **Giao diện & Trực quan** | Rất mạnh, nhiều biểu đồ tùy biến, DAX engine tính toán phức tạp. | Giao diện Web trực quan, thân thiện cho người dùng phi kỹ thuật (hỏi đáp dữ liệu). |
| **Tự động hóa & Nhúng** | Yêu cầu license Power BI Pro/Premium để nhúng (Power BI Embedded). | Rất dễ nhúng trực tiếp qua Iframe có ký token JWT vào giao diện Web Django. |
| **Chi phí** | Bản Desktop miễn phí, chia sẻ báo cáo yêu cầu 10$/user/tháng. | Miễn phí hoàn toàn với bản Community self-hosted. |

### 3.2. Chuẩn bị truy vấn SQL / View phục vụ kết nối BI trực tiếp từ PostgreSQL G14

Hệ thống G14 chuẩn bị sẵn các câu lệnh SQL View tối ưu hóa phục vụ kết nối BI (Power BI & Metabase) để truy vấn không làm ảnh hưởng tới hiệu năng bảng giao dịch:

#### View 1: Phân tích Doanh thu và Lợi nhuận bán hàng theo ngày & nhóm hàng (`v_bi_sales_performance`)
```sql
CREATE OR REPLACE VIEW v_bi_sales_performance AS
SELECT 
    DATE(o.completed_at) AS sale_date,
    EXTRACT(YEAR FROM o.completed_at) AS sale_year,
    EXTRACT(MONTH FROM o.completed_at) AS sale_month,
    p.code AS product_code,
    p.name AS product_name,
    p.category AS category_code,
    c.customer_type,
    u.username AS staff_username,
    d.quantity AS sold_quantity,
    d.unit_price AS selling_price,
    d.total_price AS total_revenue,
    (d.quantity * p.cost_price) AS cogs_amount,
    (d.total_price - (d.quantity * p.cost_price)) AS gross_profit,
    ROUND((d.total_price - (d.quantity * p.cost_price)) / d.total_price * 100, 2) AS gross_margin_pct
FROM sales_salesorder o
JOIN sales_salesorderdetail d ON o.id = d.order_id
JOIN catalog_product p ON d.product_id = p.id
JOIN catalog_customer c ON o.customer_id = c.id
LEFT JOIN accounts_user u ON o.staff_id = u.id
WHERE o.status = 'COMPLETED' AND o.payment_status = 'PAID';
```

#### View 2: Tổng hợp Tồn kho và Định giá tài sản (`v_bi_inventory_valuation`)
```sql
CREATE OR REPLACE VIEW v_bi_inventory_valuation AS
SELECT 
    p.id AS product_id,
    p.code AS product_code,
    p.name AS product_name,
    p.category,
    p.min_stock,
    p.cost_price,
    p.price AS retail_price,
    CASE 
        WHEN p.has_serial = 1 THEN (
            SELECT COUNT(*) FROM devices_productitem pi 
            WHERE pi.product_id = p.id AND pi.status = 'IN_STOCK'
        )
        ELSE COALESCE((
            SELECT SUM(CASE 
                WHEN it.transaction_type IN ('IN', 'ADJUST_INC') THEN it.quantity 
                WHEN it.transaction_type IN ('OUT', 'ADJUST_DEC', 'WARRANTY_OUT') THEN -it.quantity 
                ELSE 0 END)
            FROM inventory_inventorytransaction it 
            WHERE it.product_id = p.id
        ), 0)
    END AS current_stock_qty,
    (
        CASE 
            WHEN p.has_serial = 1 THEN (SELECT COUNT(*) FROM devices_productitem pi WHERE pi.product_id = p.id AND pi.status = 'IN_STOCK')
            ELSE COALESCE((SELECT SUM(CASE WHEN it.transaction_type IN ('IN', 'ADJUST_INC') THEN it.quantity ELSE -it.quantity END) FROM inventory_inventorytransaction it WHERE it.product_id = p.id), 0)
        END
    ) * p.cost_price AS total_valuation_amount
FROM catalog_product p
WHERE p.status = 'ACTIVE';
```

#### View 3: Đánh giá Năng lực Cung ứng & Công nợ Nhà cung cấp (`v_bi_supplier_scorecard`)
```sql
CREATE OR REPLACE VIEW v_bi_supplier_scorecard AS
SELECT 
    s.id AS supplier_id,
    s.code AS supplier_code,
    s.name AS supplier_name,
    s.payment_terms_days,
    COUNT(pr.id) AS completed_receipt_count,
    COALESCE(SUM(pr.total_amount), 0) AS total_purchased_val,
    COALESCE(SUM(pay.remaining_amount), 0) AS total_debt_remaining,
    COALESCE(SUM(CASE WHEN pay.remaining_amount > 0 AND pay.due_date < CURRENT_DATE THEN pay.remaining_amount ELSE 0 END), 0) AS overdue_debt_amount
FROM catalog_supplier s
LEFT JOIN purchasing_purchasereceipt pr ON s.id = pr.supplier_id AND pr.status = 'COMPLETED'
LEFT JOIN finance_payable pay ON pr.id = pay.purchase_receipt_id
GROUP BY s.id, s.code, s.name, s.payment_terms_days;
```

### 3.3. Tuyên bố mức độ tích hợp thực tế
- **Đã tích hợp thực tế trong hệ thống G14:**
  - **Google OR-Tools:** Đã tích hợp trực tiếp mã nguồn vào backend `dss/services.py` và có giao diện web tương tác `dss/optimizer/` chạy giải toán trực tiếp.
  - **Chart.js:** Đã tích hợp trực tiếp trên Dashboard điều hành và các trang báo cáo, hiển thị biểu đồ xu hướng doanh thu, cơ cấu nhóm hàng và tỷ lệ thực tế.
  - **SQL BI Views:** Đã chuẩn hóa và xây dựng cấu trúc SQL sẵn sàng cho cổng kết nối PostgreSQL Render (Port 5432).
- **Mức độ nghiên cứu & chuẩn bị:**
  - **ERPNext:** Nghiên cứu kiến trúc, so sánh chức năng và thiết lập mô hình tích hợp dữ liệu qua REST API.
  - **frePPLe:** Nghiên cứu đối sánh với OR-Tools để chọn giải pháp tối ưu cho chuỗi phân phối.
  - **Power BI & Metabase:** Đã chuẩn bị đầy đủ các bảng dữ liệu tổng hợp và script SQL View phục vụ kết nối trực tiếp khi doanh nghiệp triển khai server BI chuyên dụng.
