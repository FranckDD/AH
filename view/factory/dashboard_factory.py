from view.admin_view.dashboard_admin_view       import AdminDashboardView
from view.dashboard_view import DashboardView
from view.default_dashboard_view     import DefaultDashboardView
"""from view.secretaire_dashboard  import SecretaireDashboardView
from view.nurse_dashboard       import NurseDashboardView
from view.laborantin_dashboard  import LaborantinDashboardView
"""

def get_dashboard_class(role_name: str):
    return {
        'admin'      : AdminDashboardView,
        'medecin'    : DashboardView,
        'nurse'    : DashboardView,        
    }.get(role_name, DefaultDashboardView)
