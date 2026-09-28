# tests/test_lab_endpoints.py
"""
Tests pour LabController.create_batch_results - reception par lot hors
ligne (chantier 4 sous-projet 5, Task 3) : code LAB partage entre deux
appels HTTP separes du meme batch_uuid, rejeu idempotent d'un item deja
envoye, et propagation de origin_prescription_id.

Ce fichier n'existait pas avant cette tache (pas de fixtures
`laborantin_token`/`examen_id`/`client` a reutiliser dans tests/conftest.py
pour ce module). Comme tests/test_lab_repo.py (meme chantier, Task 2), on
teste avec un repo/session mockes plutot qu'un aller-retour HTTP complet
contre la vraie base Postgres (fixtures `api_client`/`db_session`) :
LabRepository.create_lab_result et get_lab_result_by_batch_uuid touchent
les colonnes lab_results.uuid/batch_uuid, et la migration correspondante
(012_lab_results_uuid_batch_uuid.py, Task 1 de ce chantier) n'a pas encore
ete appliquee a une base reelle - un test db_session planterait a l'INSERT
avec UndefinedColumn, ce qui est un etat transitoire deja accepte, pas un
bug a corriger ici. A completer avec des tests d'integration db_session/
api_client une fois la migration appliquee.
"""
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import uuid
import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock

from controller.lab_controller import LabController


class FakeLabRepo:
    """Reproduit le comportement pertinent de LabRepository.create_lab_result
    / get_lab_result_by_uuid / get_lab_result_by_batch_uuid (Task 2) en
    memoire, pour isoler la logique du controller (Task 3) de la base."""

    def __init__(self):
        self.session = MagicMock()  # resolve_patient_id n'est pas appele
        # (aucun test ici ne fournit patient_id/patient_uuid) mais le
        # controller lit self.repo.session sans condition prealable a l'appel.
        self._results = []
        self._next_id = 1
        self.calls = []  # payloads bruts passes a create_lab_result, pour inspection

    def create_lab_result(self, data):
        self.calls.append(dict(data))
        result_id = self._next_id
        self._next_id += 1
        code = data.get('code_lab_patient') or f"LAB-{result_id:04d}"
        r = SimpleNamespace(
            result_id=result_id,
            uuid=uuid.UUID(str(data['uuid'])) if data.get('uuid') else None,
            batch_uuid=data.get('batch_uuid'),
            batch_id=data.get('batch_id'),
            code_lab_patient=code,
            examen_id=data.get('examen_id'),
            origin_prescription_id=data.get('origin_prescription_id'),
        )
        self._results.append(r)
        return r

    def get_lab_result_by_uuid(self, client_uuid):
        target = uuid.UUID(str(client_uuid))
        for r in self._results:
            if r.uuid == target:
                return r
        return None

    def get_lab_result_by_batch_uuid(self, batch_uuid):
        candidates = [r for r in self._results if r.batch_uuid == batch_uuid]
        if not candidates:
            return None
        return min(candidates, key=lambda r: r.result_id)


def _make_controller():
    repo = FakeLabRepo()
    current_user = MagicMock(user_id=1, full_name="Tech Labo")
    controller = LabController(repo=repo, current_user=current_user)
    return controller, repo, current_user


def test_batch_results_shares_code_across_two_separate_calls():
    controller, repo, current_user = _make_controller()
    batch_uuid = "batch-test-001"
    item1_uuid = "11111111-1111-1111-1111-111111111111"
    item2_uuid = "22222222-2222-2222-2222-222222222222"

    r1 = controller.create_batch_results({
        "external_patient_info": {"nom": "Externe Un"},
        "batch_uuid": batch_uuid,
        "results": [{"examen_id": 1, "uuid": item1_uuid}],
    }, current_user)
    assert r1["success"] is True
    assert r1["count"] == 1
    code1 = r1["shared_code"]
    assert code1

    r2 = controller.create_batch_results({
        "external_patient_info": {"nom": "Externe Un"},
        "batch_uuid": batch_uuid,
        "results": [{"examen_id": 1, "uuid": item2_uuid}],
    }, current_user)
    assert r2["count"] == 1
    assert r2["shared_code"] == code1
    assert r2["batch_id"] == r1["batch_id"]
    # 2 lignes reellement creees (une par appel), toutes deux rattachees au meme lot.
    assert len(repo._results) == 2


def test_batch_results_replay_same_uuid_is_idempotent():
    controller, repo, current_user = _make_controller()
    item_uuid = "33333333-3333-3333-3333-333333333333"
    payload = {
        "external_patient_info": {"nom": "Externe Deux"},
        "batch_uuid": "batch-test-002",
        "results": [{"examen_id": 1, "uuid": item_uuid}],
    }

    r1 = controller.create_batch_results(payload, current_user)
    r2 = controller.create_batch_results(payload, current_user)

    assert r1["count"] == 1 and r2["count"] == 1
    assert r2["shared_code"] == r1["shared_code"]
    # Une seule ligne reellement creee en base malgre 2 appels identiques.
    assert len(repo._results) == 1
    assert len(repo.calls) == 1


def test_batch_results_propagates_origin_prescription_id():
    controller, repo, current_user = _make_controller()

    controller.create_batch_results({
        "patient_id": 7,
        "origin_prescription_id": 42,
        "batch_uuid": "batch-test-003",
        "results": [{"examen_id": 1, "uuid": "44444444-4444-4444-4444-444444444444"}],
    }, current_user)

    assert repo.calls[-1]["origin_prescription_id"] == 42
    assert repo._results[-1].origin_prescription_id == 42


def test_batch_results_multiple_items_one_call_share_generated_code():
    controller, repo, current_user = _make_controller()

    result = controller.create_batch_results({
        "external_patient_info": {"nom": "Externe Trois"},
        "batch_uuid": "batch-test-004",
        "results": [
            {"examen_id": 1, "uuid": "55555555-5555-5555-5555-555555555555"},
            {"examen_id": 2, "uuid": "66666666-6666-6666-6666-666666666666"},
        ],
    }, current_user)

    assert result["count"] == 2
    codes = {r.code_lab_patient for r in repo._results}
    assert len(codes) == 1  # le 2e item reutilise le code du 1er, pas de nouveau code genere


# ====================================================================
# TESTS POUR TASK 4 (resolve_lab_result_id_from_path)
# ====================================================================

from api_backend.backend_app.utils.patient_resolution import resolve_lab_result_id_from_path, resolve_lab_result_id


def test_update_values_by_result_uuid():
    """Test que resolve_lab_result_id_from_path accepte un uuid et le resout."""
    session = MagicMock()
    result_uuid = "a5b4c3d2-1e2d-3c4b-5a6b-7c8d9e0f1a2b"
    expected_result_id = 42

    # Mock la reponse du SELECT
    row = MagicMock()
    row.__getitem__ = lambda self, key: expected_result_id if key == 0 else None
    result = MagicMock()
    result.fetchone.return_value = row
    session.execute.return_value = result

    resolved_id = resolve_lab_result_id_from_path(session, result_uuid)

    assert resolved_id == expected_result_id


def test_update_values_unknown_uuid_returns_422():
    """Test que resolve_lab_result_id_from_path leve une HTTPException 422 pour uuid inconnu."""
    from fastapi import HTTPException, status

    session = MagicMock()
    unknown_uuid = "99999999-9999-9999-9999-999999999999"

    # Mock la reponse du SELECT pour retourner None
    result = MagicMock()
    result.fetchone.return_value = None
    session.execute.return_value = result

    try:
        resolve_lab_result_id_from_path(session, unknown_uuid)
        assert False, "Should have raised HTTPException"
    except HTTPException as e:
        assert e.status_code == 422


# ====================================================================
# REVUE FINALE (C3) : erreurs definitives -> 4xx, jamais 500
# ====================================================================

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError


def test_batch_results_integrity_error_becomes_422_with_rollback():
    """Examen supprime du catalogue (FK) -> 422 (quarantaine cote client),
    jamais une IntegrityError brute transformee en 500 (rejeu infini)."""
    controller, repo, current_user = _make_controller()

    def boom(data):
        raise IntegrityError("INSERT ...", {}, Exception("fk violation"))
    repo.create_lab_result = boom

    with pytest.raises(HTTPException) as exc:
        controller.create_batch_results({
            "external_patient_info": {"nom": "Externe FK"},
            "batch_uuid": "batch-test-fk",
            "results": [{"examen_id": 999, "uuid": "77777777-7777-7777-7777-777777777777"}],
        }, current_user)

    assert exc.value.status_code == 422
    assert "999" in exc.value.detail
    repo.session.rollback.assert_called_once()


def test_batch_endpoint_reraises_http_exception_unchanged():
    from api_backend.backend_app.routes.labo.lab_endpoints import create_batch_results
    from api_backend.backend_app.routes.labo.labo_schemas import BatchResultCreate

    ctrl = MagicMock()
    ctrl.create_batch_results.side_effect = HTTPException(status_code=422, detail="patient_uuid invalide")
    payload = BatchResultCreate(results=[{"examen_id": 1}], external_patient_info={"nom": "X"})

    with pytest.raises(HTTPException) as exc:
        create_batch_results(payload, ctrl=ctrl, current_user=MagicMock())
    assert exc.value.status_code == 422


def test_batch_endpoint_unexpected_error_still_500():
    from api_backend.backend_app.routes.labo.lab_endpoints import create_batch_results
    from api_backend.backend_app.routes.labo.labo_schemas import BatchResultCreate

    ctrl = MagicMock()
    ctrl.create_batch_results.side_effect = RuntimeError("panne")
    payload = BatchResultCreate(results=[{"examen_id": 1}], external_patient_info={"nom": "X"})

    with pytest.raises(HTTPException) as exc:
        create_batch_results(payload, ctrl=ctrl, current_user=MagicMock())
    assert exc.value.status_code == 500
