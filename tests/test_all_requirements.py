import json
from decimal import Decimal
from datetime import timedelta
from django.test import TestCase, Client
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.urls import reverse

from accounts.models import User, Role
from hr.models import Employee
from catalog.models import Product, Customer, Supplier, ProductCategory
from purchasing.models import PurchaseReceipt, PurchaseDetail, ReceiptStatus
from purchasing.services import complete_purchase_receipt, generate_receipt_code
from sales.models import SalesOrder, SalesOrderDetail, OrderStatus, PaymentMethod, PaymentStatus
from sales.services import complete_sales_order, generate_order_code
from inventory.models import InventoryTransaction, StockAdjustment, TransactionType
from devices.models import ProductItem, WarrantyReturn, ItemStatus, WarrantyStatus, WarrantyAction
from devices.services import create_warranty_claim, resolve_warranty_claim
from finance.models import Payable, CashLedger, LedgerType, PayableStatus
from finance.services import pay_payable, reverse_ledger_entry, get_financial_summary
from scm.models import PurchaseRequest, PurchaseRequestDetail, PurchaseRequestStatus
from scm.services import approve_purchase_request, convert_request_to_receipt
from dss.services import calculate_procurement_suggestion, forecast_demand_sma, optimize_procurement_ortools
from reports.services import get_dashboard_kpis

class G14SystemComprehensiveTestCase(TestCase):
    def setUp(self):
        # Create users
        self.admin = User.objects.create_superuser(username='admin_test', email='admin@g14.vn', password='password123', role=Role.ADMIN)
        self.manager = User.objects.create_user(username='ql_test', email='ql@g14.vn', password='password123', role=Role.QL)
        self.sales_staff = User.objects.create_user(username='bh_test', email='bh@g14.vn', password='password123', role=Role.BH)
        self.warehouse_staff = User.objects.create_user(username='kho_test', email='kho@g14.vn', password='password123', role=Role.KHO)
        self.accountant = User.objects.create_user(username='kt_test', email='kt@g14.vn', password='password123', role=Role.KT)

        # Create Supplier & Customer
        self.supplier = Supplier.objects.create(
            code='NCC-APPLE', name='Apple VN', phone='0909000001', payment_terms_days=30
        )
        self.customer = Customer.objects.create(
            code='KH001', name='Nguyễn Văn Khách', phone='0912000001', customer_type='RETAIL'
        )

        # Create Products: 1 with serial, 1 without serial
        self.phone_product = Product.objects.create(
            code='SP-IP15',
            name='iPhone 15 Pro Max',
            category=ProductCategory.PHONE,
            unit='Chiếc',
            price=Decimal('30000000'),
            cost_price=Decimal('25000000'),
            min_stock=3,
            has_serial=True,
            status='ACTIVE'
        )
        self.acc_product = Product.objects.create(
            code='SP-ANKER-65W',
            name='Sạc nhanh Anker 65W',
            category=ProductCategory.ACCESSORY,
            unit='Cái',
            price=Decimal('700000'),
            cost_price=Decimal('500000'),
            min_stock=10,
            has_serial=False,
            status='ACTIVE'
        )

    # 1. Tạo sản phẩm hợp lệ, kiểm tra mã định danh duy nhất (BR02)
    def test_01_create_product_and_unique_code(self):
        self.assertEqual(self.phone_product.code, 'SP-IP15')
        self.assertEqual(self.phone_product.current_stock, 0)
        # Verify duplicate code is rejected
        with self.assertRaises(Exception):
            Product.objects.create(
                code='SP-IP15',
                name='Duplicate iPhone',
                price=Decimal('30000000'),
                cost_price=Decimal('25000000')
            )

    # 2. Nhập 10 sản phẩm và kiểm tra tồn kho tăng đúng 10, tạo 1 công nợ (BR04, BR15)
    def test_02_purchasing_increases_inventory_and_creates_payable(self):
        receipt = PurchaseReceipt.objects.create(
            code=generate_receipt_code(),
            supplier=self.supplier,
            status=ReceiptStatus.DRAFT,
            created_by=self.warehouse_staff
        )
        # Enter 10 serial numbers
        serials = [f"IMEI-IP15-{i:03d}" for i in range(1, 11)]
        PurchaseDetail.objects.create(
            receipt=receipt,
            product=self.phone_product,
            quantity=10,
            unit_price=Decimal('25000000'),
            serials_text=",".join(serials)
        )
        complete_purchase_receipt(receipt, user=self.warehouse_staff)

        # Check stock = 10
        self.assertEqual(self.phone_product.get_current_stock(), 10)
        # Check items in stock
        self.assertEqual(ProductItem.objects.filter(product=self.phone_product, status=ItemStatus.IN_STOCK).count(), 10)
        # Check Payable created
        payables = Payable.objects.filter(purchase_receipt=receipt)
        self.assertEqual(payables.count(), 1)
        p = payables.first()
        self.assertEqual(p.total_amount, Decimal('250000000'))
        self.assertEqual(p.remaining_amount, Decimal('250000000'))
        self.assertEqual(p.status, PayableStatus.UNPAID)

    # 3. Bán 2 sản phẩm và kiểm tra tồn còn 8 (BR04)
    def test_03_selling_reduces_inventory(self):
        # Initial purchase 10
        self.test_02_purchasing_increases_inventory_and_creates_payable()
        self.assertEqual(self.phone_product.get_current_stock(), 10)

        # Create sales order for 2
        order = SalesOrder.objects.create(
            code=generate_order_code(),
            customer=self.customer,
            staff=self.sales_staff,
            status=OrderStatus.DRAFT,
            payment_method=PaymentMethod.CASH,
            created_by=self.sales_staff
        )
        SalesOrderDetail.objects.create(
            order=order,
            product=self.phone_product,
            quantity=2,
            unit_price=Decimal('30000000'),
            selected_serials_text='IMEI-IP15-001, IMEI-IP15-002'
        )
        complete_sales_order(order, payment_method=PaymentMethod.CASH, user=self.sales_staff)

        # Stock should now be 8
        self.assertEqual(self.phone_product.get_current_stock(), 8)
        self.assertEqual(ProductItem.objects.filter(product=self.phone_product, status=ItemStatus.IN_STOCK).count(), 8)
        self.assertEqual(ProductItem.objects.filter(product=self.phone_product, status=ItemStatus.SOLD).count(), 2)

    # 4. Phiếu Nháp không thay đổi tồn kho (BR04)
    def test_04_draft_receipt_does_not_change_inventory(self):
        receipt = PurchaseReceipt.objects.create(
            code=generate_receipt_code(),
            supplier=self.supplier,
            status=ReceiptStatus.DRAFT,
            created_by=self.warehouse_staff
        )
        PurchaseDetail.objects.create(
            receipt=receipt,
            product=self.acc_product,
            quantity=50,
            unit_price=Decimal('500000')
        )
        # Should still be 0 because receipt is DRAFT
        self.assertEqual(self.acc_product.get_current_stock(), 0)
        self.assertEqual(Payable.objects.filter(purchase_receipt=receipt).count(), 0)

    # 5. Đơn bán Nháp hoặc Hủy không làm thay đổi tồn và không ghi nhận doanh thu (BR04)
    def test_05_draft_or_cancelled_order_does_not_affect_stock_or_revenue(self):
        # Stock = 10
        self.test_02_purchasing_increases_inventory_and_creates_payable()

        order = SalesOrder.objects.create(
            code=generate_order_code(),
            customer=self.customer,
            staff=self.sales_staff,
            status=OrderStatus.DRAFT,
            total_amount=Decimal('60000000')
        )
        SalesOrderDetail.objects.create(
            order=order,
            product=self.phone_product,
            quantity=2,
            unit_price=Decimal('30000000')
        )
        # Stock still 10 while draft
        self.assertEqual(self.phone_product.get_current_stock(), 10)
        kpis = get_dashboard_kpis()
        self.assertEqual(kpis['total_revenue'], Decimal('0.00'))

    # 6. Không cho phép bán vượt tồn khả dụng (BR03)
    def test_06_cannot_oversell(self):
        # Current stock is 0
        order = SalesOrder.objects.create(
            code=generate_order_code(),
            customer=self.customer,
            staff=self.sales_staff,
            status=OrderStatus.DRAFT
        )
        SalesOrderDetail.objects.create(
            order=order,
            product=self.phone_product,
            quantity=5,
            unit_price=Decimal('30000000')
        )
        with self.assertRaises(ValidationError) as ctx:
            complete_sales_order(order, user=self.sales_staff)
        self.assertIn("không đủ tồn kho khả dụng", str(ctx.exception))

    # 7. Không cho phép dùng lại Serial/IMEI đã xuất bán (BR13)
    def test_07_cannot_reuse_sold_serial(self):
        self.test_03_selling_reduces_inventory()
        # IMEI-IP15-001 is already SOLD!
        order2 = SalesOrder.objects.create(
            code=generate_order_code(),
            customer=self.customer,
            staff=self.sales_staff,
            status=OrderStatus.DRAFT
        )
        SalesOrderDetail.objects.create(
            order=order2,
            product=self.phone_product,
            quantity=1,
            unit_price=Decimal('30000000'),
            selected_serials_text='IMEI-IP15-001'
        )
        with self.assertRaises(ValidationError) as ctx:
            complete_sales_order(order2, user=self.sales_staff)
        self.assertIn("không thể xuất bán", str(ctx.exception))

    # 8. Hoàn tất phiếu nhập chỉ tạo đúng 1 khoản công nợ (BR15)
    def test_08_single_payable_per_purchase_receipt(self):
        receipt = PurchaseReceipt.objects.create(
            code=generate_receipt_code(),
            supplier=self.supplier,
            status=ReceiptStatus.DRAFT,
            created_by=self.warehouse_staff
        )
        PurchaseDetail.objects.create(
            receipt=receipt,
            product=self.acc_product,
            quantity=10,
            unit_price=Decimal('500000')
        )
        complete_purchase_receipt(receipt, user=self.warehouse_staff)
        self.assertEqual(Payable.objects.filter(purchase_receipt=receipt).count(), 1)
        # Attempting to complete again raises ValidationError
        with self.assertRaises(ValidationError):
            complete_purchase_receipt(receipt, user=self.warehouse_staff)
        self.assertEqual(Payable.objects.filter(purchase_receipt=receipt).count(), 1)

    # 9. Không ghi nhận trùng doanh thu khi hoàn tất đơn nhiều lần (BR04)
    def test_09_cannot_duplicate_order_completion(self):
        self.test_02_purchasing_increases_inventory_and_creates_payable()
        order = SalesOrder.objects.create(
            code=generate_order_code(),
            customer=self.customer,
            staff=self.sales_staff,
            status=OrderStatus.DRAFT
        )
        SalesOrderDetail.objects.create(
            order=order,
            product=self.phone_product,
            quantity=1,
            unit_price=Decimal('30000000'),
            selected_serials_text='IMEI-IP15-001'
        )
        complete_sales_order(order, user=self.sales_staff)
        self.assertEqual(order.status, OrderStatus.COMPLETED)
        # Attempt duplicate completion
        with self.assertRaises(ValidationError):
            complete_sales_order(order, user=self.sales_staff)
        # Only one CashLedger entry created
        self.assertEqual(CashLedger.objects.filter(reference_id=order.code).count(), 1)

    # 10. Thanh toán vượt số nợ còn lại bị từ chối (BR16)
    def test_10_payable_payment_cannot_exceed_remaining(self):
        receipt = PurchaseReceipt.objects.create(
            code=generate_receipt_code(),
            supplier=self.supplier,
            status=ReceiptStatus.DRAFT,
            created_by=self.warehouse_staff
        )
        PurchaseDetail.objects.create(
            receipt=receipt,
            product=self.acc_product,
            quantity=10,
            unit_price=Decimal('500000')
        )
        complete_purchase_receipt(receipt, user=self.warehouse_staff)
        payable = Payable.objects.get(purchase_receipt=receipt)
        self.assertEqual(payable.remaining_amount, Decimal('5000000'))

        # Pay 2,000,000 -> remaining 3,000,000
        pay_payable(payable, amount=Decimal('2000000'), user=self.accountant)
        payable.refresh_from_db()
        self.assertEqual(payable.remaining_amount, Decimal('3000000'))
        self.assertEqual(payable.status, PayableStatus.PARTIAL)

        # Attempt to pay 4,000,000 (> 3,000,000) -> must fail!
        with self.assertRaises(ValidationError) as ctx:
            pay_payable(payable, amount=Decimal('4000000'), user=self.accountant)
        self.assertIn("không được vượt quá số còn nợ", str(ctx.exception))

    # 11. Đề nghị chưa được duyệt không thể chuyển thành phiếu nhập (BR19)
    def test_11_unapproved_purchase_request_cannot_be_converted(self):
        req = PurchaseRequest.objects.create(
            code='DN-TEST-01',
            status=PurchaseRequestStatus.PENDING,
            requester=self.warehouse_staff
        )
        PurchaseRequestDetail.objects.create(
            request=req,
            product=self.phone_product,
            suggested_supplier=self.supplier,
            requested_quantity=5,
            estimated_price=Decimal('25000000')
        )
        with self.assertRaises(ValidationError) as ctx:
            convert_request_to_receipt(req, user=self.warehouse_staff)
        self.assertIn("Chỉ đề nghị nhập hàng ở trạng thái 'Đã phê duyệt'", str(ctx.exception))

        # Approve and convert
        approve_purchase_request(req, user=self.manager)
        receipt = convert_request_to_receipt(req, user=self.warehouse_staff)
        self.assertIsNotNone(receipt)
        self.assertEqual(receipt.request, req)

        # Cannot convert twice
        with self.assertRaises(ValidationError):
            convert_request_to_receipt(req, user=self.warehouse_staff)

    # 12. Kiểm tra rollback khi lỗi trong transaction
    def test_12_transaction_rollback_on_error(self):
        self.test_02_purchasing_increases_inventory_and_creates_payable()
        order = SalesOrder.objects.create(
            code=generate_order_code(),
            customer=self.customer,
            staff=self.sales_staff,
            status=OrderStatus.DRAFT
        )
        # One valid line, but second line exceeds stock!
        SalesOrderDetail.objects.create(
            order=order, product=self.phone_product, quantity=2, unit_price=Decimal('30000000'),
            selected_serials_text='IMEI-IP15-001, IMEI-IP15-002'
        )
        SalesOrderDetail.objects.create(
            order=order, product=self.phone_product, quantity=100, unit_price=Decimal('30000000')
        )
        with self.assertRaises(ValidationError):
            complete_sales_order(order, user=self.sales_staff)

        # Everything must be rolled back: order still DRAFT, stock still 10, serial 001 still IN_STOCK!
        order.refresh_from_db()
        self.assertEqual(order.status, OrderStatus.DRAFT)
        self.assertEqual(self.phone_product.get_current_stock(), 10)
        item1 = ProductItem.objects.get(serial_number='IMEI-IP15-001')
        self.assertEqual(item1.status, ItemStatus.IN_STOCK)

    # 13. Phân quyền theo vai trò (BR01)
    def test_13_role_permissions_backend_enforcement(self):
        client = Client()
        # Sales staff (BH) attempts to access cash ledger (Only KT, QL, ADMIN)
        client.force_login(self.sales_staff)
        resp = client.get(reverse('finance:cash_ledger_list'))
        # Should redirect to dashboard with error message
        self.assertEqual(resp.status_code, 302)

        # Accountant (KT) attempts to create a product (Only QL, ADMIN)
        client.force_login(self.accountant)
        resp2 = client.get(reverse('catalog:product_create'))
        self.assertEqual(resp2.status_code, 302)

        # Manager (QL) accesses product create -> 200 OK
        client.force_login(self.manager)
        resp3 = client.get(reverse('catalog:product_create'))
        self.assertEqual(resp3.status_code, 200)

    # 14. Báo cáo & DSS chỉ sử dụng dữ liệu hợp lệ (BR08, BR22)
    def test_14_dss_and_reports_use_only_completed_transactions(self):
        # Create draft order -> should NOT show up in revenue or DSS
        order = SalesOrder.objects.create(
            code=generate_order_code(),
            customer=self.customer,
            staff=self.sales_staff,
            status=OrderStatus.DRAFT,
            total_amount=Decimal('500000000')
        )
        kpis = get_dashboard_kpis()
        self.assertEqual(kpis['total_revenue'], Decimal('0.00'))

        # DSS suggestion formula
        sugg = calculate_procurement_suggestion(self.phone_product)
        # Min stock = 3, available stock = 0, on order = 0 -> suggested = 3
        self.assertEqual(sugg['suggested_quantity'], 3)

