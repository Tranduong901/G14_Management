from functools import wraps
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages
from accounts.models import Role

def role_required(allowed_roles=None):
    """
    Decorator for views that checks whether a user has a specific role.
    Usage: @role_required(['ADMIN', 'QL'])
    """
    if allowed_roles is None:
        allowed_roles = []

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('accounts:login')
            
            # Superuser always has full access
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            # Check if user's role is in allowed_roles
            if request.user.role in allowed_roles:
                return view_func(request, *args, **kwargs)

            messages.error(request, "Bạn không có quyền truy cập vào chức năng này (Mã lỗi: BR01).")
            # If request is AJAX or expects JSON, or redirect back
            referer = request.META.get('HTTP_REFERER')
            if referer and referer != request.build_absolute_uri():
                return redirect(referer)
            return redirect('reports:dashboard')
        return _wrapped_view
    return decorator

class RoleRequiredMixin:
    """CBV Mixin to enforce role access control."""
    allowed_roles = []

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        if request.user.is_superuser or request.user.role in self.allowed_roles:
            return super().dispatch(request, *args, **kwargs)
        messages.error(request, "Bạn không có quyền thực hiện hành động này (Mã lỗi: BR01).")
        return redirect('reports:dashboard')

