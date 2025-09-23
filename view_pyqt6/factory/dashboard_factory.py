from view_pyqt6.admin_view_pyqt.dashboard_admin_pyqt import DashboardAdminView
from view_pyqt6.dashboard_view_qt import DashboardView
from view_pyqt6.dashboard_default import DefaultDashboardView
from view_pyqt6.secretaire.secretaire_dashboard import SecretaireDashboardView

# from view_pyqt6.nurse_dashboard import NurseDashboardView
# from view_pyqt6.laborantin_dashboard import LaborantinDashboardView

def get_dashboard_class(role_name: str):
    """
    Retourne la classe de Dashboard PyQt6 correspondant au rôle métier.
    """
    return {
        'admin'      : DashboardAdminView,
        'medecin'    : DashboardView,
        'nurse'      : DashboardView,
        'secretaire' : SecretaireDashboardView
    }.get(role_name, DefaultDashboardView)
