from django import forms
from inventory.models import StockAdjustment, Warehouse
from catalog.models import Product

class StockAdjustmentForm(forms.ModelForm):
    class Meta:
        model = StockAdjustment
        fields = ['warehouse', 'product', 'actual_quantity', 'reason']
        widgets = {
            'warehouse': forms.Select(attrs={'class': 'form-select'}),
            'product': forms.Select(attrs={'class': 'form-select'}),
            'actual_quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'placeholder': 'Nhập số lượng đếm được thực tế'}),
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Ghi rõ nguyên nhân phát sinh chênh lệch (bắt buộc)...'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        warehouses = Warehouse.objects.filter(is_active=True).select_related('branch')
        if user and not user.is_superuser and getattr(user, 'data_scope', '') != 'ALL':
            if getattr(user, 'branch_id', None):
                warehouses = warehouses.filter(branch_id=user.branch_id)
        self.fields['warehouse'].queryset = warehouses
        # Prefer non-serial products or all products
        self.fields['product'].queryset = Product.objects.filter(status='ACTIVE')
