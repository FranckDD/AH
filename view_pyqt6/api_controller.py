# view_pyqt6/api_controller.py
import inspect
import datetime
import json
from typing import Any, Callable, Dict, Iterable

class ApiGatewayError(RuntimeError):
    """Exception raised when gateway returns an error container (e.g. {'error': ...})."""
    pass

class ApiControllerProxy:
    """
    Proxy adaptatif qui forwarde dynamiquement les appels vers `gateway`.
    - conversion automatique datetime/date -> isoformat
    - normalisation des réponses 'list_*'
    - levée d'erreur ApiGatewayError en cas de {'error': ...}
    - logging de debug raisonnable
    """
    def __init__(self, gateway: Any):
        if gateway is None:
            raise ValueError("gateway cannot be None for ApiControllerProxy")
        self.gateway = gateway

    def _is_paginated_like(self, res: Any) -> bool:
        return isinstance(res, dict) and "data" in res

    def _normalize_list_response(self, name: str, res: Any):
        # Preserve paginated dicts if they contain data + total
        if isinstance(res, dict) and "data" in res and "total" in res:
            #print(f"DEBUG Normalize: Preserving paginated structure for {name}")
            return res

        #print(f"DEBUG Normalize: Applying normalization to {type(res)} for {name}")
        if res is None:
            return []
        if isinstance(res, dict):
            for k in ("data", "items", "results", "rows"):
                if k in res and isinstance(res[k], list):
                    return res[k]
            if "_items" in res and isinstance(res["_items"], list):
                return res["_items"]
            if "payload" in res and isinstance(res["payload"], dict) and isinstance(res["payload"].get("data"), list):
                return res["payload"]["data"]
        if isinstance(res, list):
            return res
        if isinstance(res, Iterable) and not isinstance(res, (str, bytes, dict)):
            try:
                return list(res)
            except Exception:
                pass
        return res

    def _should_disable_remapping(self, method_name: str, kwargs: Dict[str, Any]) -> bool:
        # ...
        preserve_prefixes = (
            'get_', 'create_', 'update_', 'delete_', 'count_', 'kpi_', 'post_',
            'add_', 'settle_'  # <--- AJOUTER 'add_' et 'settle_' ICI
        )
        return any(method_name.startswith(p) for p in preserve_prefixes)

    def _remap_kwargs_common(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        kw = dict(kwargs)
        # page/per_page -> skip/limit
        page = kw.pop("page", None)
        per_page = kw.pop("per_page", None) or kw.pop("limit", None) or None
        if page is not None:
            try:
                per = int(per_page) if per_page is not None else 15
                skip = max(0, (int(page) - 1) * per)
                kw.setdefault("skip", skip)
                kw.setdefault("limit", per)
            except Exception:
                kw.setdefault("page", page)
                if per_page is not None:
                    kw.setdefault("limit", per_page)
        else:
            if per_page is not None:
                kw.setdefault("limit", per_page)

        # search -> q / query
        if "search" in kw:
            sval = kw.pop("search")
            if "q" not in kw:
                kw["q"] = sval
            if "query" not in kw:
                kw["query"] = sval

        # unify id names
        if "patient_id" in kw and "id" not in kw:
            kw.setdefault("id", kw["patient_id"])
        if "record_id" in kw and "id" not in kw:
            kw.setdefault("id", kw["record_id"])

        return kw

    def _build_positional_from_kwargs(self, fn: Callable, kwargs: Dict[str, Any]):
        try:
            sig = inspect.signature(fn)
            params = []
            for p in sig.parameters.values():
                if p.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD):
                    params.append(p.name)
            args = []
            for name in params:
                if name in kwargs:
                    args.append(kwargs[name])
            return args
        except Exception:
            return []

    def _preprocess_args_kwargs(self, args, kwargs):
        """
        Convert datelike objects to isoformat strings, and handle inner containers.
        """
        def conv(v):
            # don't modify strings
            if isinstance(v, str):
                return v
            if isinstance(v, (datetime.date, datetime.datetime)):
                return v.isoformat()
            if isinstance(v, dict):
                return {k: conv(val) for k, val in v.items()}
            if isinstance(v, (list, tuple)):
                return type(v)(conv(i) for i in v)
            return v

        new_args = tuple(conv(a) for a in args)
        new_kwargs = {k: conv(v) for k, v in kwargs.items()}
        return new_args, new_kwargs

    def __getattr__(self, name: str):
        # ===================================================================
        # SPÉCIAL : find_by_code → on redirige proprement vers le gateway
        # ===================================================================
        if name == "find_by_code":
            def _find_by_code_handler(code: str):
                try:
                    # Ton endpoint dédié existe déjà → on l'utilise
                    result = self.gateway.find_patient_by_code(code.strip().upper())
                    if isinstance(result, dict) and "error" in result:
                        raise ApiGatewayError(f"Patient non trouvé : {result.get('error')}")
                    return result
                except AttributeError:
                    # Fallback sécurité si la méthode change de nom un jour
                    result = self.gateway.request(
                        "GET", "/patients/find_by_code", params={"code": code.strip().upper()}
                    )
                    if isinstance(result, dict) and "error" in result:
                        raise ApiGatewayError(result["error"])
                    return result
            return _find_by_code_handler

        # ===================================================================
        # Code original du proxy (inchangé, juste renommé le wrapper interne)
        # ===================================================================
        gw = self.gateway
        target = getattr(gw, name, None)
        if target is None:
            alternatives = [
                name,
                name.replace("list_", ""),
                name.replace("get_", "get"),
                name.replace("create_", "post_")
            ]
            for alt_name in alternatives:
                if alt_name != name and hasattr(gw, alt_name):
                    target = getattr(gw, alt_name)
                    break
            if target is None:
                raise AttributeError(f"Gateway has no attribute '{name}'")

        # Nom changé pour éviter le conflit avec le handler ci-dessus
        def _dynamic_proxy(*args, **kwargs):
            args_conv, kwargs_conv = self._preprocess_args_kwargs(args, kwargs)

            if args_conv and isinstance(args_conv[0], dict) and not kwargs_conv:
                args_conv = ({k: v for k, v in args_conv[0].items() if v is not None},) + args_conv[1:]

            if self._should_disable_remapping(name, kwargs_conv):
                raw = target(*args_conv, **kwargs_conv)
                return self._post_process(name, raw)

            # Essai direct
            try:
                raw = target(*args_conv, **kwargs_conv)
                return self._post_process(name, raw)
            except TypeError as e_direct:
                last_exc = e_direct

                # Remappage des kwargs
                try:
                    remapped = self._remap_kwargs_common(kwargs_conv)
                    try:
                        raw = target(*args_conv, **remapped)
                        return self._post_process(name, raw)
                    except TypeError:
                        pos = self._build_positional_from_kwargs(target, remapped)
                        raw = target(*pos)
                        return self._post_process(name, raw)
                except Exception:
                    pass

                # Autres essais (positional, sans args, etc.)
                try:
                    pos2 = self._build_positional_from_kwargs(target, kwargs_conv)
                    raw = target(*pos2)
                    return self._post_process(name, raw)
                except Exception as e3:
                    last_exc = e3

                try:
                    raw = target()
                    return self._post_process(name, raw)
                except Exception as e_final:
                    last_exc = e_final

                raise last_exc from last_exc

            except Exception:
                raise

        return _dynamic_proxy

    def _post_process(self, name: str, res: Any):
        # explicit gateway-level error => raise a dedicated exception
        if isinstance(res, dict) and "error" in res:
            details = res.get("details")
            try:
                if isinstance(details, str):
                    parsed = json.loads(details)
                    msg = parsed.get("detail") or details
                else:
                    msg = details or res.get("error")
            except Exception:
                msg = details or res.get("error")
            raise ApiGatewayError(f"Gateway error: {res.get('error')} - {msg}")

        # convenience: single-key dict -> return value directly (KPI helpers)
        if isinstance(res, dict) and len(res) == 1:
            return list(res.values())[0]

        # count_ helpers: extract count if present
        if name.startswith("count_") and isinstance(res, dict):
            if "count" in res:
                return res["count"]
            if "_count" in res:
                return res["_count"]
            return res

        # list-like methods: normalize (but preserve paginated-like dicts)
        if (name.startswith("list_") or name.endswith("_list") or name.endswith("s_list") or name.endswith("_all")):
            if isinstance(res, dict) and "data" in res:
                #print(f"DEBUG Proxy: Keeping paginated-like response for {name}, total={res.get('total')}")
                return res
            #print(f"DEBUG Proxy: Normalizing response for {name}")
            return self._normalize_list_response(name, res)

        # default: return as-is
        #print(f"DEBUG Proxy: Returning non-list response for {name}: {res!r}")
        return res
    
    
