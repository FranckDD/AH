# tests/test_lab_repo.py
"""
Tests unitaires (session mockee) pour LabRepository - resolution
uuid/batch_uuid (chantier 4 sous-projet 5, offline sync labo).

Mockee plutot que la fixture `db_session` (session transactionnelle contre
la base Postgres AH2 reelle, voir tests/conftest.py) : la migration
012_lab_results_uuid_batch_uuid.py (Task 1 de ce chantier) n'a pas encore
ete appliquee a une base reelle au moment de ce chantier - db_session
pointerait vers une base sans les colonnes uuid/batch_uuid et casserait
des l'INSERT. Meme motif/pattern que tests/test_prescription_repo.py
(MagicMock injectee dans le repo). A completer avec des tests db_session
d'integration une fois la migration appliquee.
"""
from unittest.mock import MagicMock
import uuid

from repositories.lab_repo import LabRepository


def make_repo_with_mock_session():
    mock_session = MagicMock()
    repo = LabRepository(session=mock_session)
    return repo, mock_session


def test_create_lab_result_stores_client_uuid():
    repo, mock_session = make_repo_with_mock_session()
    client_uuid = str(uuid.uuid4())

    result = repo.create_lab_result({
        "uuid": client_uuid,
        # code_lab_patient fourni explicitement pour eviter la branche de
        # generation automatique (qui interroge le catalogue d'examens et
        # ferait planter la session mockee) - hors perimetre de ce test.
        "code_lab_patient": "LAB-TEST-0001",
        "patient_id": None,
        "external_patient_info": {"nom": "Externe Test"},
    })

    assert result.uuid == uuid.UUID(client_uuid)
    mock_session.add.assert_called_once_with(result)
    mock_session.commit.assert_called_once()


def test_get_lab_result_by_uuid_roundtrip():
    repo, mock_session = make_repo_with_mock_session()
    client_uuid = str(uuid.uuid4())
    fake_result = MagicMock(result_id=42)
    mock_session.query.return_value.filter.return_value.first.return_value = fake_result

    found = repo.get_lab_result_by_uuid(client_uuid)

    assert found is fake_result
    mock_session.query.return_value.filter.return_value.first.assert_called_once()


def test_get_lab_result_by_batch_uuid_finds_sibling():
    repo, mock_session = make_repo_with_mock_session()
    batch_uuid = str(uuid.uuid4())
    fake_result = MagicMock(result_id=7)
    mock_session.query.return_value.filter.return_value.order_by.return_value.first.return_value = fake_result

    sibling = repo.get_lab_result_by_batch_uuid(batch_uuid)

    assert sibling is fake_result
    mock_session.query.return_value.filter.return_value.order_by.return_value.first.assert_called_once()


# ====================================================================
# REVUE FINALE (C4) : cle negative = -parametre_id, sans ambiguite
# ====================================================================

from models.lab import LabResult, LabResultDetail


def _repo_for_save_values(detail_lookup):
    """Session mockee : query(LabResult) renvoie un dossier externe,
    query(LabResultDetail).filter(*conds) delegue a detail_lookup(conds)."""
    mock_session = MagicMock()
    repo = LabRepository(session=mock_session)
    fake_result = MagicMock(result_id=10, patient=None, external_patient_info={"sexe": "M"})
    filter_calls = []

    def query(model):
        q = MagicMock()
        if model is LabResult:
            q.options.return_value.filter.return_value.first.return_value = fake_result
        elif model is LabResultDetail:
            def _filter(*conds):
                filter_calls.append(conds)
                f = MagicMock()
                f.first.return_value = detail_lookup(conds)
                return f
            q.filter.side_effect = _filter
        return q

    mock_session.query.side_effect = query
    return repo, filter_calls


def _cols(conds):
    return {c.left.key: c.right.value for c in conds}


def test_save_values_negative_key_resolves_by_parametre_id_only():
    detail = MagicMock(parametre=MagicMock(input_type="text"))

    def lookup(conds):
        cols = _cols(conds)
        return detail if cols.get("parametre_id") == 5 else None

    repo, filter_calls = _repo_for_save_values(lookup)
    repo.save_results_values(10, {"-5": {"valeur": "positif"}})

    assert len(filter_calls) == 1
    cols = _cols(filter_calls[0])
    assert cols == {"parametre_id": 5, "result_id": 10}
    assert "detail_id" not in cols
    assert detail.valeur_text == "positif"


def test_save_values_positive_key_still_tries_detail_id_first():
    detail = MagicMock(parametre=MagicMock(input_type="text"))

    def lookup(conds):
        return detail if _cols(conds).get("detail_id") == 5 else None

    repo, filter_calls = _repo_for_save_values(lookup)
    repo.save_results_values(10, {"5": {"valeur": "negatif"}})

    assert _cols(filter_calls[0]) == {"detail_id": 5, "result_id": 10}
    assert len(filter_calls) == 1
    assert detail.valeur_text == "negatif"
