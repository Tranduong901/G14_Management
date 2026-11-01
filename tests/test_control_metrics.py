from datetime import datetime
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from accounts.models import Role, User
from catalog.models import Customer, Product
from dss.models import ForecastResult
from sales.models import SalesOrder, SalesOrderDetail, OrderStatus, PaymentStatus
from reports.control_metrics import get_control_metrics


class ControlMetricsTestCase(TestCase):
    def test_empty_database_returns_all_control_metric_groups(self):
        metrics = get_control_metrics()

        self.assertEqual(set(metrics), {f'TC{number:02d}' for number in range(1, 30)})
        self.assertEqual(metrics['TC01']['revenue'], 0)
        self.assertEqual(metrics['TC17']['denied_operations'], 0)

    def test_forecast_accuracy_updates_only_closed_period(self):
        product = Product.objects.create(
            code='METRIC-P01',
            name='Metric product',
            price=Decimal('100'),
            cost_price=Decimal('60'),
            status='ACTIVE',
        )
        customer = Customer.objects.create(code='METRIC-C01', name='Metric customer')
        order = SalesOrder.objects.create(
            code='METRIC-O01',
            customer=customer,
            order_date=timezone.make_aware(datetime(2026, 10, 15)),
            status=OrderStatus.COMPLETED,
            payment_status=PaymentStatus.PAID,
            total_amount=Decimal('200'),
        )
        SalesOrderDetail.objects.create(
            order=order,
            product=product,
            quantity=2,
            unit_price=Decimal('100'),
            total_price=Decimal('200'),
        )
        closed = ForecastResult.objects.create(
            product=product,
            forecast_period='2026-10',
            forecasted_quantity=Decimal('4'),
        )
        current = ForecastResult.objects.create(
            product=product,
            forecast_period='2026-11',
            forecasted_quantity=Decimal('4'),
        )
        manager = User.objects.create_user(
            username='metric_manager',
            password='password123',
            role=Role.QL,
        )
        self.client.force_login(manager)

        response = self.client.post('/dss/forecast/update-accuracy/')

        self.assertEqual(response.status_code, 302)
        closed.refresh_from_db()
        current.refresh_from_db()
        self.assertEqual(closed.actual_quantity, Decimal('2'))
        self.assertEqual(closed.error_rate, Decimal('100.00'))
        self.assertIsNone(current.actual_quantity)
        self.assertIsNone(current.error_rate)

    def test_forecast_accuracy_requires_manager_or_admin(self):
        user = User.objects.create_user(
            username='metric_sales',
            password='password123',
            role=Role.BH,
        )
        self.client.force_login(user)

        response = self.client.post('/dss/forecast/update-accuracy/')

        self.assertEqual(response.status_code, 302)
