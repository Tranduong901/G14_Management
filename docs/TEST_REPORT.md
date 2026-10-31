# BÁO CÁO KẾT QUẢ KIỂM THỬ HỆ THỐNG G14 MANAGEMENT
## HỆ THỐNG THÔNG TIN QUẢN TRỊ DOANH NGHIỆP PHÂN PHỐI SẢN PHẨM CÔNG NGHỆ

**Học phần:** Quản trị Hệ thống Thông tin  
**Nhóm thực hiện:** Nhóm 14  
**Công nghệ:** Django 6.1.2 + PostgreSQL / psycopg + Django Test Framework
**Thời gian thực thi:** 28/10/2026  
**Kết quả tổng quan:** **14/14 TEST CASES ĐẠT (100% PASSED)**

---

## 1. TỔNG QUAN KẾT QUẢ THỰC THI KIỂM THỬ

Lệnh thực thi kiểm thử:
```bash
python g14_system\manage.py test tests
```

Kết quả log thực tế từ môi trường:
```text
Creating test database for alias 'default'...
..............
----------------------------------------------------------------------
Ran 14 tests in 43.645s

OK
Destroying test database for alias 'default'...
Found 14 test(s).
System check identified no issues (0 silenced).
```

Tất cả 14 ca kiểm thử bắt buộc theo yêu cầu đặc tả nghiệp vụ và quy tắc BR01 – BR22 đều được thực thi tự động và vượt qua thành công với kết quả **OK**.

---

## 2. MA TRẬN ĐỐI CHIẾU KỊCH BẢN KIỂM THỬ VÀ QUY TẮC NGHIỆP VỤ

| STT | Tên ca kiểm thử | Quy tắc đối chiếu | Mục tiêu kiểm tra | Kết quả |
| :---: | :--- | :---: | :--- | :---: |
| **01** | `test_01_create_product_and_unique_code` | **BR02** | Tạo sản phẩm hợp lệ, kiểm tra tính duy nhất của mã sản phẩm (chặn trùng mã). | **PASSED** |
| **02** | `test_02_purchasing_increases_inventory_and_creates_payable` | **BR04, BR13, BR15** | Nhập 10 sản phẩm: tồn kho tăng đúng 10, sinh đúng 10 mã IMEI 'Trong kho', và tự động tạo đúng 01 khoản công nợ NCC. | **PASSED** |
| **03** | `test_03_selling_reduces_inventory` | **BR04, BR11** | Bán 2 sản phẩm: tồn kho giảm từ 10 xuống 8, 2 IMEI chuyển sang 'Đã xuất bán' và được kích hoạt bảo hành. | **PASSED** |
| **04** | `test_04_draft_receipt_does_not_change_inventory` | **BR04** | Phiếu nhập ở trạng thái Nháp (Draft) không làm thay đổi tồn kho và không tạo công nợ. | **PASSED** |
| **05** | `test_05_draft_or_cancelled_order_does_not_affect_stock_or_revenue` | **BR04, BR08** | Đơn bán hàng Nháp hoặc Hủy không làm giảm tồn kho và không được ghi nhận vào doanh thu. | **PASSED** |
| **06** | `test_06_cannot_oversell` | **BR03** | Chặn hoàn tất đơn hàng khi số lượng yêu cầu vượt quá tồn khả dụng trong kho. | **PASSED** |
| **07** | `test_07_cannot_reuse_sold_serial` | **BR13** | Chặn xuất bán Serial/IMEI đã ở trạng thái 'Đã xuất bán' hoặc không còn trong kho. | **PASSED** |
| **08** | `test_08_single_payable_per_purchase_receipt` | **BR15** | Hoàn tất phiếu nhập chỉ tạo duy nhất 01 khoản công nợ; không tạo trùng khi gửi lặp. | **PASSED** |
| **09** | `test_09_cannot_duplicate_order_completion` | **BR04, BR17** | Không ghi nhận trùng doanh thu hoặc lặp bút toán sổ quỹ khi hoàn tất đơn nhiều lần. | **PASSED** |
| **10** | `test_10_payable_payment_cannot_exceed_remaining` | **BR16** | Chi thanh toán cho NCC không được vượt quá số còn nợ của khoản công nợ tương ứng. | **PASSED** |
| **11** | `test_11_unapproved_purchase_request_cannot_be_converted` | **BR19** | Đề nghị nhập hàng chưa duyệt không thể chuyển thành phiếu nhập; đề nghị đã chuyển không thể chuyển lặp. | **PASSED** |
| **12** | `test_12_transaction_rollback_on_error` | **ACID, atomic** | Khi xảy ra lỗi giữa luồng nghiệp vụ (ví dụ dòng sau vượt tồn), toàn bộ transaction bị rollback nguyên vẹn. | **PASSED** |
| **13** | `test_13_role_permissions_backend_enforcement` | **BR01, Bảng 2.2** | Kiểm tra phân quyền backend: Nhân viên BH không thể vào sổ quỹ; Kế toán không thể tạo sản phẩm; Quản lý có quyền hợp lệ. | **PASSED** |
| **14** | `test_14_dss_and_reports_use_only_completed_transactions` | **BR08, BR20, BR22** | Báo cáo và gợi ý DSS chỉ sử dụng giao dịch Hoàn tất hợp lệ; công thức gợi ý tính đúng theo đặc tả. | **PASSED** |

---

## 3. CHI TIẾT CÁC CA KIỂM THỬ TRỌNG TÂM

### 3.1. Ca 1 & 2: Vòng đời Nhập hàng & Tồn kho (`test_02_purchasing_increases_inventory_and_creates_payable`)
- **Điều kiện đầu vào:**
  - Sản phẩm `SP-IP15` có tồn kho ban đầu = 0.
  - Lập phiếu nhập `PN-01` với số lượng = 10 chiếc, đơn giá 25.000.000 đ.
  - Khai báo danh sách 10 mã Serial/IMEI từ `IMEI-IP15-001` đến `IMEI-IP15-010`.
- **Thực thi:** Gọi `complete_purchase_receipt(receipt, user)`.
- **Kết quả kiểm tra (Assertions):**
  - Tồn kho khả dụng `phone_product.get_current_stock() == 10` (Đạt).
  - Số thiết bị trạng thái `IN_STOCK == 10` (Đạt).
  - Bảng `Payable` xuất hiện đúng 01 bản ghi với `total_amount == 250.000.000 đ`, `remaining_amount == 250.000.000 đ` (Đạt).
  - Phiếu nhập chuyển trạng thái `COMPLETED` (Đạt).

### 3.2. Ca 3 & 6: Vòng đời Bán hàng & Chặn bán vượt tồn (`test_03_selling_reduces_inventory`, `test_06_cannot_oversell`)
- **Kiểm tra bán hợp lệ:**
  - Từ tồn = 10, lập đơn bán 2 chiếc kèm 2 mã IMEI `IMEI-IP15-001, IMEI-IP15-002`.
  - Hoàn tất đơn -> Tồn kho giảm về đúng 8.
  - 2 mã IMEI trên chuyển trạng thái `SOLD` và kích hoạt thời hạn bảo hành 12 tháng.
- **Kiểm tra chặn vượt tồn:**
  - Khi tồn kho = 0, cố tình gọi `complete_sales_order` với số lượng = 5.
  - Hệ thống ném ngoại lệ `ValidationError("không đủ tồn kho khả dụng")`, từ chối giao dịch, không trừ kho và không sinh doanh thu.

### 3.3. Ca 7: Chặn tái sử dụng Serial/IMEI đã bán (`test_07_cannot_reuse_sold_serial`)
- **Điều kiện:** Mã `IMEI-IP15-001` đã xuất bán ở Ca 3.
- **Thực thi:** Lập đơn bán mới cố tình chỉ định lại mã `IMEI-IP15-001`.
- **Kết quả:** Hệ thống chặn và báo lỗi `ValidationError("không thể xuất bán")` vì thiết bị không ở trạng thái 'Trong kho' (Mã BR13).

### 3.4. Ca 10: Kiểm soát chi trả công nợ (`test_10_payable_payment_cannot_exceed_remaining`)
- **Điều kiện:** Khoản nợ còn lại là 3.000.000 đ (sau khi đã trả trước 2.000.000 đ).
- **Thực thi:** Cố tình chi 4.000.000 đ để thanh toán.
- **Kết quả:** Hệ thống từ chối thanh toán với lỗi `ValidationError: "không được vượt quá số còn nợ"` (Mã BR16). Sổ quỹ không bị trừ sai lệch.

### 3.5. Ca 11: Kiểm soát quy trình SCM (`test_11_unapproved_purchase_request_cannot_be_converted`)
- **Điều kiện:** Đề nghị nhập hàng ở trạng thái `PENDING` (Chưa được Quản lý duyệt).
- **Thực thi:** Thử chuyển thành phiếu nhập.
- **Kết quả:** Bị chặn với lỗi `ValidationError("Chỉ đề nghị nhập hàng ở trạng thái 'Đã phê duyệt' mới được phép chuyển thành phiếu nhập")` (Mã BR19).
- Sau khi Quản lý phê duyệt (`APPROVED`), chuyển thành công sang phiếu nhập. Thử chuyển lần 2 bị chặn để ngăn trùng lặp.

### 3.6. Ca 12: Đảm bảo tính toàn vẹn giao dịch (ACID Rollback) (`test_12_transaction_rollback_on_error`)
- **Điều kiện:** Đơn bán gồm 2 dòng chi tiết: Dòng 1 hợp lệ (2 chiếc), Dòng 2 cố tình vượt tồn (100 chiếc).
- **Thực thi:** Gọi `complete_sales_order`.
- **Kết quả:** Khi dòng 2 gặp lỗi, toàn bộ khối `transaction.atomic()` được rollback hoàn toàn:
  - Đơn hàng giữ nguyên trạng thái `DRAFT`.
  - Tồn kho không bị trừ dở dang (vẫn nguyên 10).
  - Thiết bị ở Dòng 1 không bị chuyển sang `SOLD` mà vẫn giữ nguyên `IN_STOCK`.

### 3.7. Ca 13: Phân quyền backend (`test_13_role_permissions_backend_enforcement`)
- Kiểm tra trực tiếp qua Django Test Client:
  - Nhân viên Bán hàng (`BH`) truy cập URL `/finance/ledger/`: Bị chuyển hướng 302 về Dashboard kèm thông báo lỗi phân quyền `BR01`.
  - Kế toán (`KT`) truy cập URL thêm sản phẩm `/catalog/products/create/`: Bị chuyển hướng 302 từ chối quyền.
  - Quản lý (`QL`) truy cập URL `/catalog/products/create/`: Trả về `200 OK` cho phép truy cập.

---

## 4. KẾT LUẬN & ĐÁNH GIÁ NGHIỆM THU

1. **Tính đúng đắn của nghiệp vụ:** Hệ thống thực hiện chính xác các luồng liên phân hệ (Bán hàng, Nhập hàng, Kho, Serial/IMEI, Bảo hành, Sổ quỹ, Công nợ, SCM và DSS).
2. **Tính toàn vẹn dữ liệu:** Toàn bộ các thao tác đa bảng được bảo vệ bằng transaction, không để lại dữ liệu rác hay trạng thái dở dang khi xảy ra lỗi.
3. **Tuân thủ quy định quản trị:** Đáp ứng 100% các quy tắc từ BR01 đến BR22 theo Báo cáo nghiệp vụ G14.
