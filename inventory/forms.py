from django import forms
from inventory.models import StockAdjustment
from catalog.models import Product

class StockAdjustmentForm(forms.ModelForm):
    class Meta:
        model = StockAdjustment
        fields = ['product', 'actual_quantity', 'reason']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-select'}),
            'actual_quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'placeholder': 'Nhập số lượng đếm được thực tế'}),
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Ghi rõ nguyên nhân phát sinh chênh lệch (bắt buộc)...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Prefer non-serial products or all products
        self.fields['product'].queryset = Product.objects.filter(status='ACTIVE')

