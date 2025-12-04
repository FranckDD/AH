# view_pyqt6/controller_resolver.py
from typing import Optional
import logging

# Imports pour la factory et offline (avec try/except pour éviter erreurs si modules absents)
try:
    from controller.controller_offline.auth_controller_factory import get_auth_controller
    from controller.controller_offline.auth_controller_offline import AuthControllerOffline
    from repositories.repo_offline.sqlite_manager import SQLiteManager
    AUTH_FACTORY_AVAILABLE = True
except ImportError as e:
    logging.getLogger(__name__).warning(f"Imports offline/factory non disponibles: {e} (mode online only)")
    AUTH_FACTORY_AVAILABLE = False
    get_auth_controller = None  # type: ignore[assignment]  # ← Pylance OK : assigné explicitement
    AuthControllerOffline = None
    SQLiteManager = None

from view_pyqt6.api_controller import ApiControllerProxy

logger = logging.getLogger(__name__)

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

        # Cache spécifique pour auth_controller (évite réinstanciation)
        self._auth_cache: Optional[object] = None
        self._auth_backend: Optional[str] = None

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
    
    # -------------------------
    # NEW: user_controller()
    # -------------------------
    def user_controller(self):
        """
        Résout user_controller suivant la même priorité que les autres.
        Usage:
            uc = resolver.user_controller()
            uc.list_users(...)   # si uc est proxy, ApiControllerProxy résoudra list_users -> gateway.list_users()
        """
        return self._resolve_controller("user_controller")
    
    # -------------------------
    # OVERRIDE: auth_controller() – Spécial car auth est local (factory online/offline)
    # -------------------------
    def auth_controller(self):
        """
        Retourne l'AuthController approprié via factory (online/offline auto).
        - Utilise _offline_mode() pour mode.
        - Cache l'instance pour cohérence/session.
        - Ne passe PAS par _resolve_controller (qui fallback sur proxy/gateway, inadapté pour auth locale).
        """
        # Cache hit ?
        if self._auth_cache is not None:
            logger.debug(f"[RESOLVER] AuthController en cache (mode: {self._auth_backend})")
            return self._auth_cache

        # Détermine mode
        is_offline = self._offline_mode()
        mode = "offline" if is_offline else "auto"
        logger.info(f"[RESOLVER] Résolution auth_controller en mode '{mode}' (offline={is_offline})")

        if not AUTH_FACTORY_AVAILABLE:
            logger.error("[RESOLVER] Factory offline non disponible – impossible de résoudre auth_controller")
            return None

        try:
            # Guard pour Pylance : assure que get_auth_controller n'est pas None
            if get_auth_controller is None:
                raise ValueError("get_auth_controller non importé – vérifiez les dépendances offline")

            # Factory retourne (auth_ctrl, backend)
            auth_ctrl, backend = get_auth_controller(  # type: ignore[operator]  # ← Fix: ignore call sur Optional
                mode=mode,
                sqlite_path="offline.db"  # Ou configurable via self.controllers.settings si tu as
            )
            self._auth_cache = auth_ctrl
            self._auth_backend = backend

            # Vérif critique
            if not hasattr(auth_ctrl, 'authenticate'):
                raise AttributeError(f"Factory a retourné un objet sans 'authenticate' (type: {type(auth_ctrl)})")

            logger.info(f"[RESOLVER] AuthController résolu : {type(auth_ctrl).__name__} en mode {backend}")
            return auth_ctrl

        except Exception as e:
            logger.exception(f"[RESOLVER] Erreur résolution auth_controller: {e}")
            
            # Fallback hard offline
            logger.warning("[RESOLVER] Fallback hard à offline")
            try:
                # Guards pour Pylance : check None avant utilisation
                if AuthControllerOffline is not None and SQLiteManager is not None:
                    sqlite_mgr = SQLiteManager(db_path="offline.db")
                    auth_ctrl = AuthControllerOffline(session=sqlite_mgr.get_session())
                    self._auth_cache = auth_ctrl
                    self._auth_backend = "offline-fallback"
                    return auth_ctrl
                else:
                    raise ImportError("Modules offline non importables")
            except Exception as e2:
                logger.exception(f"[RESOLVER] Fallback offline échoué: {e2}")
                return None  # L'UI gérera (erreur dans _on_login)

    # Bonus : Méthode pour cleanup (appelée au logout)
    def close_auth(self):
        """Ferme l'auth_controller si instancié."""
        if self._auth_cache is not None and hasattr(self._auth_cache, "close"):  # type: ignore[union-attr]  # ← Fix: ignore sur hasattr (dynamique)
            try:
                self._auth_cache.close() # type: ignore
                logger.info("[RESOLVER] AuthController fermé")
            except Exception as e:
                logger.exception(f"[RESOLVER] Erreur close auth: {e}")
        self._auth_cache = None
        self._auth_backend = None

    # Add missing controller methods
    def consultation_spirituel_controller(self):
        """
        Résout consultation_spirituel_controller suivant la même priorité que les autres.
        Usage:
            csc = resolver.consultation_spirituel_controller()
            csc.list_consultations(...)  # Résout via primary, fallback ou proxy
        """
        return self._resolve_controller("cs_controller")

    def stock_controller(self):
        """
        Résout stock_controller suivant la même priorité que les autres.
        Usage:
            sc = resolver.stock_controller()
            sc.list_products(...)  # Résout via primary, fallback ou proxy
        """
        return self._resolve_controller("stock_controller")

    def caisse_controller(self):
        """
        Résout caisse_controller suivant la même priorité que les autres.
        Usage:
            cc = resolver.caisse_controller()
            cc.list_transactions(...)  # Résout via primary, fallback ou proxy
        """
        return self._resolve_controller("caisse_controller")

    def pharmacy_controller(self):
        """
        Résout pharmacy_controller suivant la même priorité que les autres.
        Usage:
            pc = resolver.pharmacy_controller()
            pc.get_products(...)  # Résout via primary, fallback ou proxy
        """
        return self._resolve_controller("pharmacy_controller")

    def caisse_retrait_controller(self):
        """
        Résout caisse_retrait_controller suivant la même priorité que les autres.
        Usage:
            crc = resolver.caisse_retrait_controller()
            crc.list_retraits(...)  # Résout via primary, fallback ou proxy
        """
        return self._resolve_controller("caisse_retrait_controller")  
    
    def get_financial_kpis(self, date_from, date_to):
        """Délègue au CaisseController résolu."""
        ctrl = self.caisse_controller()
        if hasattr(ctrl, "get_financial_kpis"):
            return ctrl.get_financial_kpis(date_from, date_to)
        # Fallback si la méthode n'existe pas (ne devrait pas arriver si tout est à jour)
        return {"total_paid": 0.0, "total_factured": 0.0, "remaining_due": 0.0, "recouvrement_rate": 0.0}

    def get_unpaid_action_list(self, date_from, date_to):
        """Délègue au CaisseController résolu."""
        ctrl = self.caisse_controller()
        if hasattr(ctrl, "get_unpaid_action_list"):
            return ctrl.get_unpaid_action_list(date_from, date_to)
        return []
    
    def get_payment_distribution_kpi(self, date_from, date_to):
        """
        Délègue au CaisseController résolu.
        Retourne la répartition des modes de paiement (ex: {'Espèces': 5000, ...})
        """
        ctrl = self.caisse_controller()
        if hasattr(ctrl, "get_payment_distribution_kpi"):
            return ctrl.get_payment_distribution_kpi(date_from, date_to)
        return {}

    # --- MÉTHODES KPI PATIENTS (Pour le Dashboard) ---

    def get_spiritual_new_patients_count_kpi(self, period="week"):
        """Délègue au PatientController résolu."""
        ctrl = self.patient_controller()
        if hasattr(ctrl, "get_spiritual_new_patients_count_kpi"):
            return ctrl.get_spiritual_new_patients_count_kpi(period=period)
        return {"new_patients_count": 0}
    
    def get_dashboard_critical_stock_kpi(self):
        """
        Délègue au PharmacyController résolu.
        Sert de pont pour éviter d'appeler directement le proxy sans méthode définie.
        """
        ctrl = self.pharmacy_controller()
        # On essaie d'abord la méthode spécifique dashboard
        if hasattr(ctrl, "get_dashboard_critical_stock_kpi"):
            return ctrl.get_dashboard_critical_stock_kpi()
        # Fallback sur l'ancien nom si le nouveau n'existe pas encore sur le ctrl
        if hasattr(ctrl, "get_critical_stock_count_kpi"):
            return ctrl.get_critical_stock_count_kpi()
        return {"stock_alerts_count": 0}

    def get_dashboard_expiring_stock_kpi(self, days=30):
        """Délègue au PharmacyController résolu."""
        ctrl = self.pharmacy_controller()
        if hasattr(ctrl, "get_dashboard_expiring_stock_kpi"):
            return ctrl.get_dashboard_expiring_stock_kpi(days=days)
        if hasattr(ctrl, "get_expiring_product_count_kpi"):
            return ctrl.get_expiring_product_count_kpi(days=days)
        return {"expiring_alerts_count": 0}

    def list_dashboard_critical_products(self):
        """Délègue au PharmacyController résolu."""
        ctrl = self.pharmacy_controller()
        if hasattr(ctrl, "list_dashboard_critical_products"):
            return ctrl.list_dashboard_critical_products()
        if hasattr(ctrl, "list_critical_or_empty"):
            return ctrl.list_critical_or_empty()
        return []
    
    
    
    
    
      


        