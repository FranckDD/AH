from view.admin_view.dashboard_admin_view       import AdminDashboardView
from view.dashboard_view import DashboardView
from view.default_dashboard_view     import DefaultDashboardView
from view.secretaire.dashboard_secretaire import SecretaireDashboardView
"""from view.nurse_dashboard       import NurseDashboardView"""
from view.laboviews.labo_dashboard import LaboratoryDashboardView


def get_dashboard_class(role_name: str):
    return {
        'admin'      : AdminDashboardView,
        'medecin'    : DashboardView,
        'nurse'    : DashboardView, 
        'secretaire': SecretaireDashboardView,  
        'laborantin': LaboratoryDashboardView    
    }.get(role_name, DefaultDashboardView)
