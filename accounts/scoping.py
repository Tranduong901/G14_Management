from accounts.models import DataScope

def get_scoped_queryset(queryset, user, branch_field='branch', user_field=None):
    """
    Enforces branch and data scoping based on the user's role, data_scope, and branch.
    - Superusers and users with data_scope == ALL can view all records.
    - BRANCH scope restricts results to the user's branch.
    - PERSONAL scope restricts results to records created by or assigned to the user.
    """
    if not user or not user.is_authenticated:
        return queryset.none()

    if user.is_superuser or getattr(user, 'data_scope', '') == DataScope.ALL:
        return queryset

    if user.data_scope == DataScope.PERSONAL and user_field:
        return queryset.filter(**{user_field: user})

    if user.data_scope == DataScope.BRANCH or not user_field:
        if getattr(user, 'branch_id', None):
            return queryset.filter(**{branch_field: user.branch})
        return queryset

    return queryset
