from datetime import timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from accounts.models import User, Role
from hr.models import Employee
from catalog.models import Product, Customer, Supplier, ProductCategory
from scm.models import SupplierProduct, PurchaseRequest, PurchaseRequestDetail, PurchaseRequestStatus, PurchaseRequestSource
from purchasing.models import PurchaseReceipt, PurchaseDetail, ReceiptStatus
from purchasing.services import complete_purchase_receipt
from sales.models import SalesOrder, SalesOrderDetail, OrderStatus, PaymentMethod, PaymentStatus
from sales.services import complete_sales_order
from devices.models import ProductItem, WarrantyReturn, ItemStatus, WarrantyStatus, WarrantyAction
from finance.models import Payable, CashLedger, LedgerType, PaymentMethod as FinancePaymentMethod, PayableStatus
from finance.services import pay_payable
from dss.models import ForecastResult

class Command(BaseCommand):
    help = "Seeds initial demo data for G14 Management System according to specs."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting database seeding for G14 System..."))

        # 1. Create Users for 5 roles
        users_info = [
            ('admin', 'admin123', 'Trần', 'Quản Trị', 'admin@g14.vn', Role.ADMIN, True),
            ('quanly', 'admin123', 'Nguyễn', 'Quản Lý', 'quanly@g14.vn', Role.QL, False),
            ('banhang', 'admin123', 'Lê', 'Bán Hàng', 'banhang@g14.vn', Role.BH, False),
            ('kho', 'admin123', 'Phạm', 'Thủ Kho', 'kho@g14.vn', Role.KHO, False),
            ('ketoan', 'admin123', 'Đỗ', 'Kế Toán', 'ketoan@g14.vn', Role.KT, False),
        ]

        user_objs = {}
        for username, pwd, fname, lname, email, role, is_super in users_info:
            u, created = User.objects.get_or_create(username=username, defaults={
                'first_name': fname,
                'last_name': lname,
                'email': email,
                'role': role,
                'is_staff': True,
                'is_superuser': is_super,
            })
            u.set_password(pwd)
            u.role = role
            u.save()
            user_objs[role] = u

        self.stdout.write("Created 5 role users: admin, quanly, banhang, kho, ketoan.")

        # 2. Employees
        emp_data = [
            ('NV001', 'Trần Quản Trị', 'IT', 'Trưởng phòng IT', '0901000001', user_objs[Role.ADMIN]),
            ('NV002', 'Nguyễn Quản Lý', 'BQL', 'Giám đốc Điều hành', '0901000002', user_objs[Role.QL]),
            ('NV003', 'Lê Bán Hàng', 'KD', 'Chuyên viên Bán hàng', '0901000003', user_objs[Role.BH]),
            ('NV004', 'Phạm Thủ Kho', 'KHO', 'Trưởng kho thiết bị', '0901000004', user_objs[Role.KHO]),
            ('NV005', 'Đỗ Kế Toán', 'KT', 'Kế toán trưởng', '0901000005', user_objs[Role.KT]),
        ]
        for code, name, dept, pos, phone, u in emp_data:
            Employee.objects.update_or_create(code=code, defaults={
                'full_name': name,
                'department': dept,
                'position': pos,
                'phone': phone,
                'status': 'ACTIVE',
                'user': u
            })
        self.stdout.write("Created 5 employee profiles.")

        # 3. Suppliers
        suppliers_info = [
            ('NCC01', 'Công ty TNHH Apple Việt Nam', '02838999001', 'contact@apple.vn', 'Tòa nhà Bitexco, Q.1, TP.HCM', 30),
            ('NCC02', 'Công ty TNHH Điện tử Samsung Vina', '02838999002', 'b2b@samsung.vn', 'Số 2 Hải Triều, Q.1, TP.HCM', 15),
            ('NCC03', 'Công ty Cổ phần Công nghệ Asus VN', '02438999003', 'sales@asus.vn', 'Tầng 12 Keangnam Landmark 72, Hà Nội', 30),
            ('NCC04', 'Nhà phân phối Phụ kiện Anker VN', '02438999004', 'info@anker.vn', '128 Cầu Giấy, Hà Nội', 0),
        ]
        supplier_objs = {}
        for code, name, phone, email, addr, terms in suppliers_info:
            s, _ = Supplier.objects.update_or_create(code=code, defaults={
                'name': name, 'phone': phone, 'email': email, 'address': addr, 'payment_terms_days': terms
            })
            supplier_objs[code] = s
        self.stdout.write("Created 4 suppliers.")

        # 4. Customers
        customers_info = [
            ('KH001', 'Công ty TNHH Giải Pháp Alpha', '0912000001', 'contact@alpha.com', 'Tòa nhà FPT, Cầu Giấy, Hà Nội', 'WHOLESALE'),
            ('KH002', 'Nguyễn Văn An', '0912000002', 'an.nguyen@gmail.com', '15 Tràng Tiền, Hoàn Kiếm, Hà Nội', 'RETAIL'),
            ('KH003', 'Trần Thị Bình', '0912000003', 'binh.tran@gmail.com', '88 Nguyễn Trãi, Thanh Xuân, Hà Nội', 'RETAIL'),
            ('KH004', 'Hoàng Minh Đức', '0912000004', 'duc.hoang@gmail.com', '45 Lê Duẩn, Ba Đình, Hà Nội', 'RETAIL'),
        ]
        customer_objs = {}
        for code, name, phone, email, addr, ctype in customers_info:
            c, _ = Customer.objects.update_or_create(code=code, defaults={
                'name': name, 'phone': phone, 'email': email, 'address': addr, 'customer_type': ctype
            })
            customer_objs[code] = c
        self.stdout.write("Created 4 customers.")

        # 5. Products
        products_info = [
            ('SP01', 'iPhone 15 Pro Max 256GB', ProductCategory.PHONE, 'Chiếc', Decimal('29990000'), Decimal('25000000'), 5, True),
            ('SP02', 'Samsung Galaxy S24 Ultra 256GB', ProductCategory.PHONE, 'Chiếc', Decimal('27990000'), Decimal('23000000'), 5, True),
            ('SP03', 'Laptop Asus ROG Strix G16 2024', ProductCategory.LAPTOP, 'Chiếc', Decimal('35990000'), Decimal('30000000'), 3, True),
            ('SP04', 'iPad Pro M4 11 inch 256GB Wifi', ProductCategory.TABLET, 'Chiếc', Decimal('24990000'), Decimal('21000000'), 4, True),
            ('SP05', 'Củ sạc nhanh Anker GaN 65W 3 cổng', ProductCategory.ACCESSORY, 'Cái', Decimal('690000'), Decimal('450000'), 15, False),
            ('SP06', 'Cáp sạc Type-C to Type-C Anker 100W', ProductCategory.ACCESSORY, 'Sợi', Decimal('250000'), Decimal('150000'), 20, False),
        ]
        product_objs = {}
        for code, name, cat, unit, price, cost, min_s, has_sn in products_info:
            p, _ = Product.objects.update_or_create(code=code, defaults={
                'name': name, 'category': cat, 'unit': unit, 'price': price, 'cost_price': cost, 'min_stock': min_s, 'has_serial': has_sn, 'status': 'ACTIVE'
            })
            product_objs[code] = p
        self.stdout.write("Created 6 products.")

        # 6. Supplier Products
        SupplierProduct.objects.update_or_create(supplier=supplier_objs['NCC01'], product=product_objs['SP01'], defaults={'last_purchase_price': Decimal('25000000'), 'standard_lead_days': 2})
        SupplierProduct.objects.update_or_create(supplier=supplier_objs['NCC01'], product=product_objs['SP04'], defaults={'last_purchase_price': Decimal('21000000'), 'standard_lead_days': 2})
        SupplierProduct.objects.update_or_create(supplier=supplier_objs['NCC02'], product=product_objs['SP02'], defaults={'last_purchase_price': Decimal('23000000'), 'standard_lead_days': 3})
        SupplierProduct.objects.update_or_create(supplier=supplier_objs['NCC03'], product=product_objs['SP03'], defaults={'last_purchase_price': Decimal('30000000'), 'standard_lead_days': 4})
        SupplierProduct.objects.update_or_create(supplier=supplier_objs['NCC04'], product=product_objs['SP05'], defaults={'last_purchase_price': Decimal('450000'), 'standard_lead_days': 1})
        SupplierProduct.objects.update_or_create(supplier=supplier_objs['NCC04'], product=product_objs['SP06'], defaults={'last_purchase_price': Decimal('150000'), 'standard_lead_days': 1})

        # 7. SCM Purchase Requests
        # Req 1: Approved
        req1, _ = PurchaseRequest.objects.get_or_create(code='DN-2026-001', defaults={
            'status': PurchaseRequestStatus.APPROVED,
            'source': PurchaseRequestSource.SYSTEM_SUGGESTION,
            'requester': user_objs[Role.KHO],
            'approver': user_objs[Role.QL],
            'approved_at': timezone.now() - timedelta(days=5),
            'notes': 'Kế hoạch bổ sung tồn kho quý 4 theo khuyến nghị DSS',
        })
        PurchaseRequestDetail.objects.get_or_create(request=req1, product=product_objs['SP01'], defaults={
            'suggested_supplier': supplier_objs['NCC01'], 'requested_quantity': 5, 'estimated_price': Decimal('25000000')
        })

        # Req 2: Pending approval
        req2, _ = PurchaseRequest.objects.get_or_create(code='DN-2026-002', defaults={
            'status': PurchaseRequestStatus.PENDING,
            'source': PurchaseRequestSource.MANUAL,
            'requester': user_objs[Role.KHO],
            'notes': 'Đề xuất nhập thêm Samsung S24 Ultra chuẩn bị chiến dịch Black Friday',
        })
        PurchaseRequestDetail.objects.get_or_create(request=req2, product=product_objs['SP02'], defaults={
            'suggested_supplier': supplier_objs['NCC02'], 'requested_quantity': 10, 'estimated_price': Decimal('23000000')
        })

        # 8. Purchase Receipts & Inventory
        # Receipt 1: Completed from NCC01
        receipt1, created1 = PurchaseReceipt.objects.get_or_create(code='PN-2026-001', defaults={
            'supplier': supplier_objs['NCC01'],
            'request': req1,
            'receipt_date': timezone.now().date() - timedelta(days=3),
            'status': ReceiptStatus.DRAFT,
            'notes': 'Nhập kho lô hàng iPhone 15 Pro Max chính hãng',
            'created_by': user_objs[Role.KHO]
        })
        if created1:
            serials_ip15 = "\n".join([f"35890010000000{i}" for i in range(1, 6)])
            PurchaseDetail.objects.create(
                receipt=receipt1, product=product_objs['SP01'], quantity=5,
                unit_price=Decimal('25000000'), serials_text=serials_ip15, created_by=user_objs[Role.KHO]
            )
            complete_purchase_receipt(receipt1, user=user_objs[Role.KHO])

        # Receipt 2: Completed from NCC04 (Accessories)
        receipt2, created2 = PurchaseReceipt.objects.get_or_create(code='PN-2026-002', defaults={
            'supplier': supplier_objs['NCC04'],
            'receipt_date': timezone.now().date() - timedelta(days=2),
            'status': ReceiptStatus.DRAFT,
            'emergency_reason': 'Nhập bổ sung phụ kiện sạc cáp Anker',
            'created_by': user_objs[Role.KHO]
        })
        if created2:
            PurchaseDetail.objects.create(
                receipt=receipt2, product=product_objs['SP05'], quantity=30,
                unit_price=Decimal('450000'), created_by=user_objs[Role.KHO]
            )
            PurchaseDetail.objects.create(
                receipt=receipt2, product=product_objs['SP06'], quantity=50,
                unit_price=Decimal('150000'), created_by=user_objs[Role.KHO]
            )
            complete_purchase_receipt(receipt2, user=user_objs[Role.KHO])

        self.stdout.write("Completed initial purchase receipts and populated stock.")

        # 9. Historical Sales Orders for 3-month moving average
        # Month -2 (August)
        order_m2, created_m2 = SalesOrder.objects.get_or_create(code='DH-202608-01', defaults={
            'customer': customer_objs['KH002'],
            'staff': user_objs[Role.BH],
            'order_date': timezone.now() - timedelta(days=65),
            'status': OrderStatus.COMPLETED,
            'payment_method': PaymentMethod.CASH,
            'payment_status': PaymentStatus.PAID,
            'total_amount': Decimal('59980000'),
            'completed_at': timezone.now() - timedelta(days=65),
            'created_by': user_objs[Role.BH]
        })
        if created_m2:
            SalesOrderDetail.objects.create(
                order=order_m2, product=product_objs['SP01'], quantity=2,
                unit_price=Decimal('29990000'), total_price=Decimal('59980000'),
                selected_serials_text='HISTORICAL-01, HISTORICAL-02'
            )

        # Month -1 (September)
        order_m1, created_m1 = SalesOrder.objects.get_or_create(code='DH-202609-01', defaults={
            'customer': customer_objs['KH003'],
            'staff': user_objs[Role.BH],
            'order_date': timezone.now() - timedelta(days=35),
            'status': OrderStatus.COMPLETED,
            'payment_method': PaymentMethod.BANK_TRANSFER,
            'payment_status': PaymentStatus.PAID,
            'total_amount': Decimal('89970000'),
            'completed_at': timezone.now() - timedelta(days=35),
            'created_by': user_objs[Role.BH]
        })
        if created_m1:
            SalesOrderDetail.objects.create(
                order=order_m1, product=product_objs['SP01'], quantity=3,
                unit_price=Decimal('29990000'), total_price=Decimal('89970000'),
                selected_serials_text='HISTORICAL-03, HISTORICAL-04, HISTORICAL-05'
            )

        # Recent Sales Order (Completed today with real in-stock items)
        order_now, created_now = SalesOrder.objects.get_or_create(code='DH-202610-01', defaults={
            'customer': customer_objs['KH001'],
            'staff': user_objs[Role.BH],
            'order_date': timezone.now() - timedelta(hours=3),
            'status': OrderStatus.DRAFT,
            'payment_method': PaymentMethod.BANK_TRANSFER,
            'notes': 'Đơn hàng bán lẻ doanh nghiệp kèm sạc nhanh',
            'created_by': user_objs[Role.BH]
        })
        if created_now:
            # Pick 2 available serials of SP01
            avail_items = list(ProductItem.objects.filter(product=product_objs['SP01'], status=ItemStatus.IN_STOCK)[:2])
            serials_str = ", ".join([it.serial_number for it in avail_items])
            SalesOrderDetail.objects.create(
                order=order_now, product=product_objs['SP01'], quantity=2,
                unit_price=Decimal('29990000'), selected_serials_text=serials_str, created_by=user_objs[Role.BH]
            )
            SalesOrderDetail.objects.create(
                order=order_now, product=product_objs['SP05'], quantity=2,
                unit_price=Decimal('690000'), created_by=user_objs[Role.BH]
            )
            complete_sales_order(order_now, payment_method=PaymentMethod.BANK_TRANSFER, user=user_objs[Role.BH])

        self.stdout.write("Created sales orders and verified multi-period history.")

        # 10. Financial payments (Pay partial debt)
        payable1 = Payable.objects.filter(purchase_receipt=receipt1).first()
        if payable1 and payable1.remaining_amount > 0 and payable1.paid_amount == 0:
            pay_payable(payable1, amount=Decimal('50000000'), payment_method=FinancePaymentMethod.BANK_TRANSFER, notes='Trả trước 50 triệu đợt 1', user=user_objs[Role.KT])
            self.stdout.write("Executed partial payable payment for receipt 1.")

        # 11. Warranty Claim
        sold_item = ProductItem.objects.filter(status=ItemStatus.SOLD).first()
        if sold_item:
            from devices.services import create_warranty_claim
            try:
                create_warranty_claim(
                    item=sold_item,
                    customer=customer_objs['KH001'],
                    issue_description='Máy bị sọc màn hình nhẹ góc phải sau 2 tuần sử dụng.',
                    action_type=WarrantyAction.REPAIR,
                    user=user_objs[Role.BH],
                    notes='Đã tiếp nhận kiểm tra màn hình và bo mạch.'
                )
                self.stdout.write("Created demo warranty claim ticket.")
            except Exception:
                pass

        # 12. Forecast Results
        ForecastResult.objects.update_or_create(
            product=product_objs['SP01'],
            forecast_period='2026-11',
            defaults={
                'method': 'SMA_3M',
                'forecasted_quantity': Decimal('2.3'),
                'actual_quantity': None,
                'error_rate': None
            }
        )

        self.stdout.write(self.style.SUCCESS("G14 System database seeding completed successfully!"))

