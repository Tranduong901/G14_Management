from django import forms
from django.forms import inlineformset_factory
from sales.models import SalesOrder, SalesOrderDetail, PaymentMethod
from catalog.models import Product, Customer

class SalesOrderForm(forms.ModelForm):
    class Meta:
        model = SalesOrder
        fields = ['customer', 'warehouse', 'payment_method', 'notes']
        widgets = {
            'customer': forms.Select(attrs={'class': 'form-select'}),
            'warehouse': forms.Select(attrs={'class': 'form-select'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Ghi chú cho đơn hàng...'}),
        }

class SalesOrderDetailForm(forms.ModelForm):
    class Meta:
        model = SalesOrderDetail
        fields = ['product', 'quantity', 'unit_price', 'selected_serials_text']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-select product-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control qty-input', 'min': '1'}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control price-input', 'min': '0', 'step': '1000'}),
            'selected_serials_text': forms.TextInput(attrs={'class': 'form-control serial-input', 'placeholder': 'Để trống để tự động chọn IMEI trong kho...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['product'].queryset = Product.objects.filter(status='ACTIVE')

SalesOrderDetailFormSet = inlineformset_factory(
    SalesOrder,
    SalesOrderDetail,
    form=SalesOrderDetailForm,
    extra=1,
    can_delete=True
)

class OrderCompleteForm(forms.Form):
    payment_method = forms.ChoiceField(
        choices=PaymentMethod.choices,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Xác nhận phương thức thanh toán"
    )
