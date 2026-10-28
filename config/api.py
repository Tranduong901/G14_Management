from rest_framework import serializers, viewsets, permissions
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from catalog.models import Product, Customer, Supplier
from sales.models import SalesOrder, SalesOrderDetail
from inventory.models import InventoryTransaction
from dss.services import calculate_procurement_suggestion
from reports.services import get_dashboard_kpis

# Serializers
class ProductSerializer(serializers.ModelSerializer):
    current_stock = serializers.IntegerField(source='get_current_stock', read_only=True)
    class Meta:
        model = Product
        fields = ['id', 'code', 'name', 'category', 'unit', 'price', 'cost_price', 'min_stock', 'has_serial', 'status', 'current_stock']

class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ['id', 'code', 'name', 'phone', 'email', 'address', 'customer_type']

class SalesOrderSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    staff_name = serializers.CharField(source='staff.username', read_only=True)
    class Meta:
        model = SalesOrder
        fields = ['id', 'code', 'customer', 'customer_name', 'staff', 'staff_name', 'order_date', 'status', 'payment_method', 'payment_status', 'total_amount']

# ViewSets
class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]

class CustomerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [permissions.IsAuthenticated]

class SalesOrderViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SalesOrder.objects.all()
    serializer_class = SalesOrderSerializer
    permission_classes = [permissions.IsAuthenticated]

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def api_dashboard_stats(request):
    kpis = get_dashboard_kpis()
    # Convert Decimals to float for JSON
    res = {k: float(v) if hasattr(v, '__float__') else v for k, v in kpis.items()}
    return Response(res)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def api_procurement_suggestions(request):
    products = Product.objects.filter(status='ACTIVE')
    suggestions = []
    for p in products:
        s = calculate_procurement_suggestion(p)
        suggestions.append({
            'product_id': p.id,
            'product_code': p.code,
            'product_name': p.name,
            'available_stock': s['available_stock'],
            'min_stock': s['min_stock'],
            'forecast': s['forecast'],
            'suggested_quantity': s['suggested_quantity'],
            'is_low_stock': s['is_low_stock'],
            'estimated_cost': float(s['estimated_cost'])
        })
    return Response(suggestions)

