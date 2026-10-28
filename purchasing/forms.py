from django import forms
from django.forms import inlineformset_factory
from purchasing.models import PurchaseReceipt, PurchaseDetail
from catalog.models import Product, Supplier

class PurchaseReceiptForm(forms.ModelForm):
    class Meta:
        model = PurchaseReceipt
        fields = ['supplier', 'receipt_date', 'emergency_reason', 'notes']
        widgets = {
            'supplier': forms.Select(attrs={'class': 'form-select'}),
            'receipt_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'emergency_reason': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ghi lý do nếu nhập hàng ngoài kế hoạch...'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Ghi chú phiếu nhập...'}),
        }

class PurchaseDetailForm(forms.ModelForm):
    class Meta:
        model = PurchaseDetail
        fields = ['product', 'quantity', 'unit_price', 'serials_text']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-select product-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control qty-input', 'min': '1'}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control price-input', 'min': '0', 'step': '1000'}),
            'serials_text': forms.Textarea(attrs={'class': 'form-control serials-input', 'rows': 2, 'placeholder': 'Nhập Serial/IMEI cách nhau bởi dấu phẩy...'}),
        }

PurchaseDetailFormSet = inlineformset_factory(
    PurchaseReceipt,
    PurchaseDetail,
    form=PurchaseDetailForm,
    extra=1,
    can_delete=True
)

