# controller/lab_catalogue_controller.py
"""Edition du catalogue du laboratoire par la cheffe du laboratoire ou l'admin.

Regles : le prix n'est jamais touche ; un examen ou parametre deja utilise par un resultat ne se
supprime pas (409, desactivation a la place) ; chaque ecriture est auditee (avant / apres, sans
donnee patient) dans la meme transaction.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Optional, Set

from sqlalchemy.exc import IntegrityError

from models.lab import Examen, Parametre, ReferenceRange
from repositories.audit_repo import AuditRepository
from repositories.lab_catalogue_repo import LabCatalogueRepository

EXAM_AUDIT_FIELDS = ("code", "nom", "categorie", "section", "print_title", "method", "layout_family",
                     "signature_label", "sort_order", "is_active", "fixed_notes")
PARAM_AUDIT_FIELDS = ("examen_id", "nom_parametre", "unite", "print_label", "result_kind", "choices",
                      "ordre", "is_active", "group_label", "norm_text")
RANGE_AUDIT_FIELDS = ("parametre_id", "sexe", "age_min_days", "age_max_days", "ga_min_weeks", "ga_max_weeks",
                      "valeur_min", "valeur_max", "display_text")

DEFAULT_POS_NEG = ["Positif", "Negatif"]
IN_USE_HINT = "Des resultats utilisent deja cet element : il ne peut pas etre supprime. Desactivez-le (is_active=false) a la place."


class CatalogueError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message

    def detail(self) -> Dict[str, str]:
        return {"code": self.code, "message": self.message}


def _plain(v: Any) -> Any:
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, (list, tuple)):
        return [_plain(x) for x in v]
    return v


def _snap(obj, fields) -> Dict[str, Any]:
    return {f: _plain(getattr(obj, f, None)) for f in fields}


def _notes_value(notes: Optional[List[Any]]) -> Optional[List[Dict[str, str]]]:
    """Notes fixes -> liste de {position, text, style} ; vide -> NULL (une nouvelle liste : le JSONB doit changer)."""
    out = []
    for n in notes or []:
        n = n if isinstance(n, dict) else n.model_dump()
        out.append({"position": n["position"], "text": n["text"], "style": n.get("style") or "normal"})
    return out or None


def _derive_columns(kind: str, choices: Optional[List[str]]) -> Dict[str, Any]:
    """Colonnes historiques du banc de saisie (type_valeur / input_type / options_list) a partir du genre."""
    if kind == "numeric":
        return {"type_valeur": "numeric", "input_type": "numeric", "options_list": None, "choices": None}
    if kind == "text":
        return {"type_valeur": "text", "input_type": "text", "options_list": None, "choices": None}
    if kind == "pos_neg":
        choices = choices or list(DEFAULT_POS_NEG)
    return {"type_valeur": "text", "input_type": "select", "options_list": ",".join(choices or []),
            "choices": list(choices or [])}


class LabCatalogueController:
    def __init__(self, repo: LabCatalogueRepository, current_user: Any):
        self.repo = repo
        self.session = repo.session
        self.user = current_user

    # ------------------------------------------------------------ audit / commit
    def _audit(self, entity: str, action: str, entity_id: Optional[int], old: Dict[str, Any], new: Dict[str, Any]):
        audit = AuditRepository(self.session)
        if action == "UPDATE":
            keys = [k for k in new if str(old.get(k)) != str(new.get(k))]
            old = {k: old.get(k) for k in keys}
            new = {k: new.get(k) for k in keys}
        audit.log_user_action(current_user=self.user, resource_type=entity, action_performed=action,
                              resource_id=entity_id, old_values=old or None, new_values=new or None,
                              details=audit.summarize_changes(old, new) or None)

    def _commit(self):
        try:
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            raise CatalogueError(409, "conflict", "Conflit avec une donnee existante ou liee (code deja pris ou element utilise).")
        except Exception:
            self.session.rollback()
            raise

    # ------------------------------------------------------------ serialisation
    def _ser_range(self, r: ReferenceRange) -> Dict[str, Any]:
        return {"id": r.id, "parametre_id": r.parametre_id, "sexe": r.sexe,
                "age_min_days": r.age_min_days, "age_max_days": r.age_max_days,
                "ga_min_weeks": r.ga_min_weeks, "ga_max_weeks": r.ga_max_weeks,
                "valeur_min": float(r.valeur_min), "valeur_max": float(r.valeur_max),
                "display_text": r.display_text}

    def _ser_param(self, p: Parametre, used: Optional[Set[int]] = None) -> Dict[str, Any]:
        in_use = (p.id in used) if used is not None else self.repo.parameter_in_use(p.id)
        ranges = sorted(p.reference_ranges, key=lambda r: (r.sexe, r.age_min_days if r.age_min_days is not None else -1,
                                                           r.ga_min_weeks if r.ga_min_weeks is not None else -1, r.id))
        return {"id": p.id, "examen_id": p.examen_id, "nom_parametre": p.nom_parametre, "unite": p.unite or "",
                "print_label": p.print_label, "result_kind": p.result_kind, "choices": p.choices,
                "group_label": p.group_label, "norm_text": p.norm_text,
                "ordre": p.ordre, "is_active": bool(p.is_active), "in_use": in_use,
                "ranges": [self._ser_range(r) for r in ranges]}

    def _ser_exam(self, e: Examen, include_inactive: bool = True, used_exams: Optional[Set[int]] = None,
                  used_params: Optional[Set[int]] = None) -> Dict[str, Any]:
        in_use = (e.id in used_exams) if used_exams is not None else self.repo.exam_in_use(e.id)
        params = sorted(e.parametres, key=lambda p: (p.ordre or 0, p.id))
        if not include_inactive:
            params = [p for p in params if p.is_active]
        return {"id": e.id, "code": e.code, "nom": e.nom, "categorie": e.categorie, "section": e.section,
                "print_title": e.print_title, "method": e.method, "layout_family": e.layout_family,
                "signature_label": e.signature_label, "sort_order": e.sort_order, "is_active": bool(e.is_active),
                "fixed_notes": list(e.fixed_notes or []),
                "prix": float(e.prix) if e.prix is not None else 0.0, "in_use": in_use,
                "parameters": [self._ser_param(p, used_params) for p in params]}

    # ------------------------------------------------------------ lecture
    def list_exams(self, include_inactive: bool = False) -> List[Dict[str, Any]]:
        exams = self.repo.list_exams(include_inactive)
        used_e, used_p = self.repo.used_exam_ids(), self.repo.used_parameter_ids()
        return [self._ser_exam(e, include_inactive, used_e, used_p) for e in exams]

    # ------------------------------------------------------------ examens
    def create_exam(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if self.repo.get_exam_by_code(data["code"]):
            raise CatalogueError(409, "duplicate_code", f"Le code '{data['code']}' existe deja.")
        data = dict(data)
        data["fixed_notes"] = _notes_value(data.get("fixed_notes"))
        ex = Examen(**data)  # prix : defaut 0, jamais fourni
        ex.prix = 0
        self.repo.add(ex)
        self._audit("LabExam", "CREATE", ex.id, {}, _snap(ex, EXAM_AUDIT_FIELDS))
        self._commit()
        return self._ser_exam(ex)

    def update_exam(self, examen_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        ex = self.repo.get_exam(examen_id)
        if ex is None:
            raise CatalogueError(404, "not_found", "Examen introuvable.")
        data = {k: v for k, v in data.items() if k in EXAM_AUDIT_FIELDS and k != "code"}
        for k in ("nom", "categorie", "layout_family", "sort_order", "is_active"):
            if k in data and data[k] is None:
                data.pop(k)  # colonnes NOT NULL : ignorer un null explicite
        if "fixed_notes" in data:
            data["fixed_notes"] = _notes_value(data["fixed_notes"])
        before = _snap(ex, EXAM_AUDIT_FIELDS)
        for k, v in data.items():
            setattr(ex, k, v)
        self.session.flush()
        self._audit("LabExam", "UPDATE", ex.id, before, _snap(ex, EXAM_AUDIT_FIELDS))
        self._commit()
        return self._ser_exam(ex)

    def delete_exam(self, examen_id: int) -> None:
        ex = self.repo.get_exam(examen_id)
        if ex is None:
            raise CatalogueError(404, "not_found", "Examen introuvable.")
        if self.repo.exam_in_use(examen_id):
            raise CatalogueError(409, "in_use", IN_USE_HINT)
        before = _snap(ex, EXAM_AUDIT_FIELDS)
        self.repo.delete_exam_cascade(ex)
        self._audit("LabExam", "DELETE", examen_id, before, {})
        self._commit()

    def _renumber(self, siblings: list, moved_id: int, position: int, attr: str) -> Optional[Any]:
        ids = [s.id for s in siblings]
        if moved_id not in ids:
            return None
        ids.remove(moved_id)
        ids.insert(min(position, len(ids) + 1) - 1, moved_id)
        by_id = {s.id: s for s in siblings}
        for pos, sid in enumerate(ids, start=1):
            setattr(by_id[sid], attr, pos)
        self.session.flush()
        return by_id[moved_id]

    def move_exam(self, examen_id: int, position: int) -> Dict[str, Any]:
        ex = self.repo.get_exam(examen_id)
        if ex is None:
            raise CatalogueError(404, "not_found", "Examen introuvable.")
        before = ex.sort_order
        self._renumber(self.repo.exams_ordered(), examen_id, position, "sort_order")
        self._audit("LabExam", "UPDATE", ex.id, {"sort_order": before}, {"sort_order": ex.sort_order})
        self._commit()
        return self._ser_exam(ex)

    def order_exams(self, ids: List[int]) -> List[Dict[str, Any]]:
        if len(ids) != len(set(ids)):
            raise CatalogueError(422, "invalid_order", "Chaque examen ne doit apparaitre qu'une fois.")
        exams = {e.id: e for e in self.repo.exams_ordered()}
        if not set(ids) <= set(exams):
            raise CatalogueError(422, "invalid_order", "Examen inconnu dans la liste.")
        rest = [e.id for e in exams.values() if e.id not in set(ids)]
        before = {i: exams[i].sort_order for i in ids}
        for pos, eid in enumerate(list(ids) + rest, start=1):
            exams[eid].sort_order = pos
        self.session.flush()
        self._audit("LabExam", "UPDATE", None, {"sort_order": before}, {"sort_order": {i: exams[i].sort_order for i in ids}})
        self._commit()
        return [self._ser_exam(exams[i]) for i in ids]

    # ------------------------------------------------------------ parametres
    def create_parameter(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if self.repo.get_exam(data["examen_id"]) is None:
            raise CatalogueError(404, "not_found", "Examen introuvable.")
        kind = data["result_kind"]
        derived = _derive_columns(kind, data.get("choices"))
        p = Parametre(examen_id=data["examen_id"], nom_parametre=data["nom_parametre"], unite=data.get("unite") or "",
                      print_label=data.get("print_label"), result_kind=kind, is_active=data.get("is_active", True),
                      group_label=data.get("group_label"), norm_text=data.get("norm_text"),
                      ordre=self.repo.next_parameter_order(data["examen_id"]), **derived)
        self.repo.add(p)
        self._audit("LabParameter", "CREATE", p.id, {}, _snap(p, PARAM_AUDIT_FIELDS))
        self._commit()
        return self._ser_param(p)

    def update_parameter(self, param_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        p = self.repo.get_parameter(param_id)
        if p is None:
            raise CatalogueError(404, "not_found", "Parametre introuvable.")
        before = _snap(p, PARAM_AUDIT_FIELDS)
        for k in ("nom_parametre", "unite", "is_active"):
            if data.get(k) is not None:
                setattr(p, k, data[k])
        for k in ("print_label", "group_label", "norm_text"):
            if k in data:
                setattr(p, k, data[k])
        new_kind = data.get("result_kind") or p.result_kind
        if new_kind != p.result_kind and self.repo.parameter_in_use(p.id):
            raise CatalogueError(409, "in_use", "Des resultats utilisent ce parametre : son type de resultat ne peut plus changer. Creez un nouveau parametre et desactivez celui-ci.")
        if "result_kind" in data or "choices" in data:
            choices = data["choices"] if data.get("choices") is not None else (p.choices if new_kind == p.result_kind else None)
            if new_kind == "choice" and not choices:
                raise CatalogueError(422, "invalid_choices", "Un parametre a choix doit lister ses choix.")
            derived = _derive_columns(new_kind, choices)
            p.result_kind = new_kind
            for k, v in derived.items():
                setattr(p, k, v)
        self.session.flush()
        self._audit("LabParameter", "UPDATE", p.id, before, _snap(p, PARAM_AUDIT_FIELDS))
        self._commit()
        return self._ser_param(p)

    def delete_parameter(self, param_id: int) -> None:
        p = self.repo.get_parameter(param_id)
        if p is None:
            raise CatalogueError(404, "not_found", "Parametre introuvable.")
        if self.repo.parameter_in_use(param_id):
            raise CatalogueError(409, "in_use", IN_USE_HINT)
        before = _snap(p, PARAM_AUDIT_FIELDS)
        self.repo.delete_parameter_cascade(p)
        self._audit("LabParameter", "DELETE", param_id, before, {})
        self._commit()

    def move_parameter(self, param_id: int, position: int) -> Dict[str, Any]:
        p = self.repo.get_parameter(param_id)
        if p is None:
            raise CatalogueError(404, "not_found", "Parametre introuvable.")
        before = p.ordre
        self._renumber(self.repo.parameters_ordered(p.examen_id), param_id, position, "ordre")
        self._audit("LabParameter", "UPDATE", p.id, {"ordre": before}, {"ordre": p.ordre})
        self._commit()
        return self._ser_param(p)

    def order_parameters(self, examen_id: int, ids: List[int]) -> List[Dict[str, Any]]:
        if self.repo.get_exam(examen_id) is None:
            raise CatalogueError(404, "not_found", "Examen introuvable.")
        params = {p.id: p for p in self.repo.parameters_ordered(examen_id)}
        if len(ids) != len(set(ids)) or set(ids) != set(params):
            raise CatalogueError(422, "invalid_order", "La liste doit contenir exactement les parametres de cet examen, une seule fois chacun.")
        before = {i: params[i].ordre for i in ids}
        for pos, pid in enumerate(ids, start=1):
            params[pid].ordre = pos
        self.session.flush()
        self._audit("LabParameter", "UPDATE", None, {"ordre": before}, {"ordre": {i: params[i].ordre for i in ids}})
        self._commit()
        return [self._ser_param(params[i]) for i in ids]

    # ------------------------------------------------------------ plages
    def create_range(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if self.repo.get_parameter(data["parametre_id"]) is None:
            raise CatalogueError(404, "not_found", "Parametre introuvable.")
        if self.repo.find_duplicate_range(data["parametre_id"], data):
            raise CatalogueError(409, "duplicate_range", "Cette plage existe deja pour ce parametre.")
        # Colonnes en annees (heritees) laissees NULL : seules les bornes en jours / SA sont ecrites.
        r = ReferenceRange(age_min=None, age_max=None, **data)
        self.repo.add(r)
        self._audit("LabRange", "CREATE", r.id, {}, _snap(r, RANGE_AUDIT_FIELDS))
        self._commit()
        return self._ser_range(r)

    def update_range(self, range_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        r = self.repo.get_range(range_id)
        if r is None:
            raise CatalogueError(404, "not_found", "Plage introuvable.")
        if self.repo.find_duplicate_range(r.parametre_id, data, exclude_id=range_id):
            raise CatalogueError(409, "duplicate_range", "Cette plage existe deja pour ce parametre.")
        before = _snap(r, RANGE_AUDIT_FIELDS)
        for k, v in data.items():
            setattr(r, k, v)
        r.age_min = None
        r.age_max = None
        self.session.flush()
        self._audit("LabRange", "UPDATE", r.id, before, _snap(r, RANGE_AUDIT_FIELDS))
        self._commit()
        return self._ser_range(r)

    def delete_range(self, range_id: int) -> None:
        r = self.repo.get_range(range_id)
        if r is None:
            raise CatalogueError(404, "not_found", "Plage introuvable.")
        before = _snap(r, RANGE_AUDIT_FIELDS)
        self.repo.delete(r)
        self._audit("LabRange", "DELETE", range_id, before, {})
        self._commit()
