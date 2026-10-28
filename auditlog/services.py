import json
from auditlog.models import AuditLog

def get_client_ip(request):
    if not request:
        return None
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def log_activity(user, action, obj=None, changes=None, request=None, ip_address=None):
    """
    Service helper to create audit log records across the entire system.
    Follows BR09: logs who, when, what action, and what target.
    """
    if not ip_address and request:
        ip_address = get_client_ip(request)

    app_label = ''
    model_name = ''
    object_id = ''
    object_repr = ''

    if obj is not None:
        if hasattr(obj, '_meta'):
            app_label = obj._meta.app_label
            model_name = obj._meta.model_name
            object_id = str(getattr(obj, 'pk', ''))
            object_repr = str(obj)
        else:
            object_repr = str(obj)
    elif changes and 'object_repr' in changes:
        object_repr = changes.pop('object_repr')

    # Ensure clean json serializable dict
    sanitized_changes = {}
    if changes and isinstance(changes, dict):
        for k, v in changes.items():
            # Don't log passwords or sensitive keys
            if 'password' in k.lower() or 'secret' in k.lower():
                continue
            sanitized_changes[k] = str(v)

    return AuditLog.objects.create(
        user=user if getattr(user, 'is_authenticated', False) else None,
        action=action,
        app_label=app_label,
        model_name=model_name,
        object_id=object_id,
        object_repr=object_repr[:250],
        changes_json=sanitized_changes,
        ip_address=ip_address
    )

