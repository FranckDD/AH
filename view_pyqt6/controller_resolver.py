#view_pyqt6/controller_resolver.py
from view_pyqt6.api_controller import ApiControllerProxy

# ---------- Utility resolver ----------
class ControllerResolver:
    """
    Fournit des sous-controllers utilisables par les vues :
    - priorise le controller local (`primary_controller`) si disponible
    - sinon fallback_controller si offline
    - sinon proxy dynamique vers le gateway (online)
    """
    def __init__(self, controllers):
        self.controllers = controllers
        self.gateway = getattr(controllers, "gateway", None)
        self.primary_controller = getattr(controllers, "controller", None)
        self.fallback_controller = getattr(controllers, "fallback_controller", None)
        self.network_manager = getattr(controllers, "network_manager", None)

        # Proxy générique vers le gateway
        self._api_proxy = ApiControllerProxy(self.gateway) if self.gateway else None

    def _offline_mode(self):
        return getattr(self.network_manager, "offline_mode", False)

    def _resolve_controller(self, attr_name: str):
        """
        Logique centralisée pour choisir le contrôleur selon la priorité :
        primary -> fallback offline -> api proxy
        """
        # primary controller
        if self.primary_controller and hasattr(self.primary_controller, attr_name):
            return getattr(self.primary_controller, attr_name)

        # fallback controller si offline
        if self._offline_mode() and self.fallback_controller and hasattr(self.fallback_controller, attr_name):
            return getattr(self.fallback_controller, attr_name)

        # api proxy
        if self._api_proxy:
            return self._api_proxy

        raise RuntimeError(f"No {attr_name} available")

    # ---------- Controllers ----------
    def patient_controller(self):
        return self._resolve_controller("patient_controller")

    def appointment_controller(self):
        return self._resolve_controller("appointment_controller")

    def medical_record_controller(self):
        return self._resolve_controller("medical_record_controller")

    def prescription_controller(self):
        return self._resolve_controller("prescription_controller")
    
    def lab_controller(self):
        return self._resolve_controller("lab_controller")
