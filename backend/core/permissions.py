"""Role-based access.

Each view may declare `read_roles` and `write_roles` (sets of core.models.Role
values). Defaults: every authenticated staff member can read; only managers
can write. Superusers can do everything. A user without a linked Person has
no role and is refused (except superusers).
"""
from rest_framework.permissions import SAFE_METHODS, BasePermission

from .models import Role

ALL_ROLES = frozenset(Role.values)
MANAGERS = frozenset({Role.RESP_TECH, Role.ADJOINT, Role.DATA_OFFICER})
FIELD_ROLES = frozenset({Role.ZONE_TECH, Role.PUMP_FOCAL, Role.STORAGE_FOCAL, Role.SSE, Role.CONTRACTOR}) | MANAGERS
STOCK_ROLES = frozenset({Role.RESP_TECH, Role.ADJOINT, Role.DATA_OFFICER})
STAFF_ROLES = ALL_ROLES - {Role.FUNDER}
# Who may read operational data, KPIs, costs and the dashboard.
DASHBOARD_ROLES = MANAGERS | {Role.FUNDER, Role.SSE}


def set_roles(view, read=None, write=None):
    """Declare roles on a function view made with @api_view."""
    if read is not None:
        view.cls.read_roles = read
    if write is not None:
        view.cls.write_roles = write
    return view


def user_role(user):
    if not user or not user.is_authenticated:
        return None
    person = getattr(user, "person", None)
    return person.role if person else None


def user_site(user):
    person = getattr(user, "person", None)
    return person.site if person else None


class RolePermission(BasePermission):
    message = "Votre rôle ne permet pas cette action."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        role = user_role(user)
        if role is None:
            return False
        if request.method in SAFE_METHODS:
            return role in getattr(view, "read_roles", ALL_ROLES)
        return role in getattr(view, "write_roles", MANAGERS)
