from accounts.models import Role

def user_role_context(request):
    """Provides user role information to all templates."""
    if not request.user.is_authenticated:
        return {
            'is_admin': False,
            'is_ql': False,
            'is_bh': False,
            'is_kho': False,
            'is_kt': False,
            'current_role': None,
            'Role': Role,
        }
    
    user = request.user
    role = getattr(user, 'role', '')
    is_super = user.is_superuser

    return {
        'is_admin': role == Role.ADMIN or is_super,
        'is_ql': role in [Role.QL, Role.ADMIN] or is_super,
        'is_bh': role in [Role.BH, Role.ADMIN] or is_super,
        'is_kho': role in [Role.KHO, Role.ADMIN] or is_super,
        'is_kt': role in [Role.KT, Role.ADMIN] or is_super,
        'current_role': role,
        'current_role_display': user.get_role_display() if hasattr(user, 'get_role_display') else '',
        'Role': Role,
    }

