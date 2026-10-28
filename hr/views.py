from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from accounts.models import Role
from accounts.decorators import role_required
from hr.models import Employee
from hr.forms import EmployeeForm
from auditlog.services import log_activity

@login_required
@role_required([Role.QL, Role.ADMIN])
def employee_list_view(request):
    employees = Employee.objects.select_related('user').all()
    q = request.GET.get('q', '').strip()
    dept = request.GET.get('department', '')
    status = request.GET.get('status', '')

    if q:
        employees = employees.filter(
            Q(code__icontains=q) |
            Q(full_name__icontains=q) |
            Q(phone__icontains=q) |
            Q(email__icontains=q)
        )
    if dept:
        employees = employees.filter(department=dept)
    if status:
        employees = employees.filter(status=status)

    paginator = Paginator(employees, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'hr/employee_list.html', {
        'page_obj': page_obj,
        'q': q,
        'department_filter': dept,
        'status_filter': status,
        'departments': Employee.DEPARTMENT_CHOICES,
        'statuses': Employee.STATUS_CHOICES,
    })

@login_required
@role_required([Role.QL, Role.ADMIN])
def employee_create_view(request):
    if request.method == 'POST':
        form = EmployeeForm(request.POST)
        if form.is_valid():
            employee = form.save(commit=False)
            employee.created_by = request.user
            employee.save()
            log_activity(
                user=request.user,
                action='CREATE',
                obj=employee,
                changes={'code': employee.code, 'full_name': employee.full_name},
                request=request
            )
            messages.success(request, f"Đã thêm nhân viên {employee.full_name} ({employee.code}) thành công!")
            return redirect('hr:employee_list')
    else:
        form = EmployeeForm()

    return render(request, 'hr/employee_form.html', {'form': form, 'title': 'Thêm mới nhân viên'})

@login_required
@role_required([Role.QL, Role.ADMIN])
def employee_edit_view(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    if request.method == 'POST':
        form = EmployeeForm(request.POST, instance=employee)
        if form.is_valid():
            updated = form.save()
            log_activity(
                user=request.user,
                action='UPDATE',
                obj=updated,
                changes={'code': updated.code, 'full_name': updated.full_name, 'status': updated.status},
                request=request
            )
            messages.success(request, f"Cập nhật hồ sơ nhân viên {updated.full_name} thành công!")
            return redirect('hr:employee_list')
    else:
        form = EmployeeForm(instance=employee)

    return render(request, 'hr/employee_form.html', {'form': form, 'title': f'Sửa nhân viên {employee.full_name}'})

