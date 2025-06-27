#from view_pyqt6.admin_view.dashboard_admin_view import AdminDashboardView
from view_pyqt6.QT_medecin.dashboard_medical import DashboardView
from view_pyqt6.dashboard_default import DefaultDashboardView
from view_pyqt6.secretaire.secretaire_dashboard import SecretaireDashboardView

# from view_pyqt6.nurse_dashboard import NurseDashboardView
# from view_pyqt6.laborantin_dashboard import LaborantinDashboardView

def get_dashboard_class(role_name: str):
    """
    Retourne la classe de Dashboard PyQt6 correspondant au rôle métier.
    """
    return {
        #'admin'      : AdminDashboardView,
        'medecin'    : DashboardView,
        'nurse'      : DashboardView,
        'secretaire' : SecretaireDashboardView
    }.get(role_name, DefaultDashboardView)
