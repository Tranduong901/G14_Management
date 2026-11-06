from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from accounts.models import Role
from auditlog.models import AccessDeniedLog

def user_can_view_payroll_management(user):
    """
    Checks if a user is permitted to view the full payroll table.
    - HR, KT, and QL have operational access.
    - Admin: ONLY if explicitly granted via can_view_payroll flag.
    - Standard employees: Never permitted to see global payroll.
    """
    if not user or not user.is_authenticated:
        return False
    
    role = getattr(user, 'role', '')

    if role in [Role.HR, Role.KT, Role.QL]:
        return True

    if role == Role.ADMIN or user.is_superuser:
        return getattr(user, 'can_view_payroll', False)

    return getattr(user, 'can_view_payroll', False)

def payroll_access_required(view_func):
    """Decorator ensuring strict payroll confidentiality."""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')

        if user_can_view_payroll_management(request.user):
            return view_func(request, *args, **kwargs)

        messages.error(request, "Bạn không được cấp quyền truy cập bảng lương (Quy định bảo mật thông tin lương).")
        AccessDeniedLog.objects.create(
            user=request.user,
            role=getattr(request.user, 'role', ''),
            path=request.path,
            method=request.method,
        )
        return redirect('hr:my_payslips')
    return _wrapped
