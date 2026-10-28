from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from accounts.models import Role
from accounts.decorators import role_required
from auditlog.models import AuditLog

@login_required
@role_required([Role.ADMIN, Role.QL, Role.KT])
def auditlog_list_view(request):
    logs = AuditLog.objects.select_related('user').all()

    q = request.GET.get('q', '').strip()
    action = request.GET.get('action', '')
    user_id = request.GET.get('user', '')
    app_label = request.GET.get('app_label', '')

    if q:
        logs = logs.filter(
            Q(object_repr__icontains=q) |
            Q(object_id__icontains=q) |
            Q(user__username__icontains=q)
        )
    if action:
        logs = logs.filter(action=action)
    if user_id:
        logs = logs.filter(user_id=user_id)
    if app_label:
        logs = logs.filter(app_label=app_label)

    paginator = Paginator(logs, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'auditlog/auditlog_list.html', {
        'page_obj': page_obj,
        'q': q,
        'action_filter': action,
        'user_filter': user_id,
        'app_filter': app_label,
        'actions': AuditLog.ACTION_CHOICES,
    })

@login_required
@role_required([Role.ADMIN, Role.QL, Role.KT])
def auditlog_detail_view(request, pk):
    log_item = get_object_or_404(AuditLog.objects.select_related('user'), pk=pk)
    return render(request, 'auditlog/auditlog_detail.html', {'log_item': log_item})

