from django import forms
from catalog.models import Product, Customer, Supplier

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['code', 'name', 'category', 'unit', 'price', 'cost_price', 'min_stock', 'has_serial', 'status', 'description']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'VD: SP-IP15PM'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'VD: iPhone 15 Pro Max 256GB'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'unit': forms.TextInput(attrs={'class': 'form-control'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '1000', 'min': '0'}),
            'cost_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '1000', 'min': '0'}),
            'min_stock': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'has_serial': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ['code', 'name', 'phone', 'email', 'address', 'customer_type', 'notes']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'VD: KH001'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'VD: Nguyễn Văn A'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'VD: 0912345678'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'VD: customer@email.com'}),
            'address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'VD: 123 Cầu Giấy, Hà Nội'}),
            'customer_type': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ['code', 'name', 'phone', 'email', 'address', 'payment_terms_days', 'notes']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'VD: NCC-APPLE'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'VD: Công ty TNHH Apple Việt Nam'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'VD: 02838999999'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'VD: contact@apple.vn'}),
            'address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'VD: Tòa nhà Bitexco, Q.1, TP.HCM'}),
            'payment_terms_days': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

