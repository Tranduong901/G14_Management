from django.apps import AppConfig

class CatalogConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'catalog'
    verbose_name = 'Quản lý danh mục (Sản phẩm, Khách hàng, Nhà cung cấp)'

