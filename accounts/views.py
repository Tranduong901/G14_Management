from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from accounts.models import User, Role
from accounts.forms import LoginForm, UserCreateForm, UserUpdateForm
from accounts.decorators import role_required
from auditlog.services import log_activity

def login_view(request):
    if request.user.is_authenticated:
        return redirect('reports:dashboard')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            user = form.user
            login(request, user)
            log_activity(
                user=user,
                action='LOGIN',
                obj=user,
                changes={'status': 'Đăng nhập thành công'},
                request=request
            )
            messages.success(request, f"Chào mừng {user.get_full_name() or user.username} ({user.get_role_display()}) đăng nhập thành công!")
            next_url = request.GET.get('next') or request.POST.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('reports:dashboard')
    else:
        form = LoginForm()

    return render(request, 'accounts/login.html', {'form': form})

def logout_view(request):
    if request.user.is_authenticated:
        user = request.user
        log_activity(
            user=user,
            action='LOGOUT',
            obj=user,
            changes={'status': 'Đăng xuất'},
            request=request
        )
        logout(request)
        messages.info(request, "Bạn đã đăng xuất khỏi hệ thống.")
    return redirect('accounts:login')

@login_required
def profile_view(request):
    user = request.user
    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()

        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.phone = phone
        user.save()
        messages.success(request, "Cập nhật thông tin cá nhân thành công!")
        return redirect('accounts:profile')

    return render(request, 'accounts/profile.html', {'user_obj': user})

@login_required
@role_required([Role.ADMIN])
def user_list_view(request):
    query = request.GET.get('q', '').strip()
    role_filter = request.GET.get('role', '')
    users = User.objects.all().order_by('-date_joined')

    if query:
        users = users.filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query) |
            Q(phone__icontains=query)
        )
    if role_filter:
        users = users.filter(role=role_filter)

    paginator = Paginator(users, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'accounts/user_list.html', {
        'page_obj': page_obj,
        'query': query,
        'role_filter': role_filter,
        'roles': Role.choices,
    })

@login_required
@role_required([Role.ADMIN])
def user_create_view(request):
    if request.method == 'POST':
        form = UserCreateForm(request.POST)
        if form.is_valid():
            new_user = form.save()
            log_activity(
                user=request.user,
                action='CREATE',
                obj=new_user,
                changes={'username': new_user.username, 'role': new_user.role},
                request=request
            )
            messages.success(request, f"Đã tạo tài khoản {new_user.username} thành công!")
            return redirect('accounts:user_list')
    else:
        form = UserCreateForm()

    return render(request, 'accounts/user_form.html', {'form': form, 'title': 'Thêm mới tài khoản'})

@login_required
@role_required([Role.ADMIN])
def user_edit_view(request, pk):
    user_obj = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        form = UserUpdateForm(request.POST, instance=user_obj)
        if form.is_valid():
            updated_user = form.save()
            log_activity(
                user=request.user,
                action='UPDATE',
                obj=updated_user,
                changes={'username': updated_user.username, 'role': updated_user.role, 'is_active': updated_user.is_active},
                request=request
            )
            messages.success(request, f"Cập nhật tài khoản {updated_user.username} thành công!")
            return redirect('accounts:user_list')
    else:
        form = UserUpdateForm(instance=user_obj)

    return render(request, 'accounts/user_form.html', {'form': form, 'title': f'Sửa tài khoản {user_obj.username}'})

@login_required
@role_required([Role.ADMIN])
def user_toggle_active_view(request, pk):
    user_obj = get_object_or_404(User, pk=pk)
    if user_obj == request.user:
        messages.error(request, "Không thể tự khóa tài khoản của chính mình!")
        return redirect('accounts:user_list')

    user_obj.is_active = not user_obj.is_active
    user_obj.save()
    status_str = "Kích hoạt" if user_obj.is_active else "Khóa"
    log_activity(
        user=request.user,
        action='UPDATE',
        obj=user_obj,
        changes={'is_active': user_obj.is_active, 'status': status_str},
        request=request
    )
    messages.success(request, f"Đã {status_str} tài khoản {user_obj.username} thành công!")
    return redirect('accounts:user_list')

