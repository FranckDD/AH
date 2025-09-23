#view_pywt6/fallback_controlle.py
class _FallbackResolver:
    """Fallback minimal qui expose patient_controller(), appointment_controller(), ..."""
    def __init__(self, controllers):
        self.controllers = controllers
        self.gateway = getattr(controllers, "gateway", None)
        self.primary_controller = getattr(controllers, "controller", None)
        self.fallback_controller = getattr(controllers, "fallback_controller", None)
        self.network_manager = getattr(controllers, "network_manager", None)

    def _offline_mode(self):
        nm = self.network_manager
        return bool(getattr(nm, "offline_mode", False))

    # renvoie un "controller" ou None
    def appointment_controller(self):
        if self.primary_controller and hasattr(self.primary_controller, "appointment_controller"):
            return self.primary_controller.appointment_controller
        if self._offline_mode() and self.fallback_controller and hasattr(self.fallback_controller, "appointment_controller"):
            return self.fallback_controller.appointment_controller
        return getattr(self.controllers, "appointment_controller", None) or getattr(self.gateway, "appointment_controller", None)

    def patient_controller(self):
        if self.primary_controller and hasattr(self.primary_controller, "patient_controller"):
            return self.primary_controller.patient_controller
        if self._offline_mode() and self.fallback_controller and hasattr(self.fallback_controller, "patient_controller"):
            return self.fallback_controller.patient_controller
        return getattr(self.controllers, "patient_controller", None) or getattr(self.gateway, "patient_controller", None)

    def medical_record_controller(self):
        if self.primary_controller and hasattr(self.primary_controller, "medical_record_controller"):
            return self.primary_controller.medical_record_controller
        if self._offline_mode() and self.fallback_controller and hasattr(self.fallback_controller, "medical_record_controller"):
            return self.fallback_controller.medical_record_controller
        return getattr(self.controllers, "medical_record_controller", None) or getattr(self.gateway, "medical_record_controller", None)
    
    def prescription_controller(self):
        if self.primary_controller and hasattr(self.primary_controller, "prescription_controller"):
            return self.primary_controller.prescription_controller
        if self._offline_mode() and self.fallback_controller and hasattr(self.fallback_controller, "prescription_controller"):
            return self.fallback_controller.prescription_controller
        return getattr(self.controllers, "prescription_controller", None) or getattr(self.gateway, "prescription_controller", None)

    def lab_controller(self):
        if self.primary_controller and hasattr(self.primary_controller, "lab_controller"):
            return self.primary_controller.lab_controller
        if self._offline_mode() and self.fallback_controller and hasattr(self.fallback_controller, "lab_controller"):
            return self.fallback_controller.lab_controller
        return getattr(self.controllers, "lab_controller", None) or getattr(self.gateway, "lab_controller", None)
    
        # -------------------------
    # NEW: user_controller()
    # -------------------------
    def user_controller(self):
        """
        Same priority logic as others: primary -> fallback (if offline) -> controllers.gateway fallback.
        Retourne un objet controller (local/fallback) ou None.
        """
        if self.primary_controller and hasattr(self.primary_controller, "user_controller"):
            return self.primary_controller.user_controller
        if self._offline_mode() and self.fallback_controller and hasattr(self.fallback_controller, "user_controller"):
            return self.fallback_controller.user_controller
        return getattr(self.controllers, "user_controller", None) or getattr(self.gateway, "user_controller", None)