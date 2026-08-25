"""
Shared access-control gates for the reports views.

Split out of reports/views.py (see docs/CODEBASE_REFACTOR_ROADMAP.md
item 3) - a pure move, no logic changed.
"""

from accounts.utils import has_permission
from utils.api_response import forbidden_response


def _require_admin_reports_permission(request):
    """Shared gate for the admin reports/analytics endpoints below.
    Returns a 403 response if the user lacks generate_admin_reports, else None.

    export_data holders are also let through: ReportExportView (below) calls
    straight into these same view classes to fetch the underlying report
    data before exporting it, so an export_data-only user (e.g. Line
    Manager) needs to pass this gate too, not just the export endpoint's
    own check."""
    if (
        request.user.is_superuser
        or has_permission(request.user, "generate_admin_reports")
        or has_permission(request.user, "export_data")
    ):
        return None
    return forbidden_response(
        message="You do not have permission to view admin reports"
    )


def _resolve_department_scope(request):
    """Access + scoping gate for DepartmentalReportsView.

    System Admins (superuser or the system_admin permission) may view any
    department: returns (True, None), and the caller's own ?department=
    query param is honored as-is (or all departments if omitted).

    Everyone else holding generate_admin_reports/export_data/
    view_department_requests is locked to their own department: returns
    (True, str(user.department_id)), regardless of what ?department= the
    caller passed - this prevents a HOD from requesting another
    department's data even though they also hold generate_admin_reports.

    Returns (False, None) if the user has none of the above permissions,
    or is department-locked but has no department assigned.
    """
    user = request.user

    if user.is_superuser or has_permission(user, "system_admin"):
        return True, None

    is_department_scoped_role = (
        has_permission(user, "generate_admin_reports")
        or has_permission(user, "export_data")
        or has_permission(user, "view_department_requests")
    )
    if not is_department_scoped_role:
        return False, None

    if not user.department_id:
        return False, None

    return True, str(user.department_id)
