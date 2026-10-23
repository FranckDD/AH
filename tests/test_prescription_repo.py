# tests/test_prescription_repo.py
from unittest.mock import MagicMock
import pytest
import sys
import os

# Ajouter le dossier racine du projet au PATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


# Adapte l'import selon ton projet
from repositories.prescription_repo import PrescriptionRepository
from models.prescription import Prescription

def make_repo_with_mock_session():
    mock_session = MagicMock()
    repo = PrescriptionRepository(session=mock_session)
    return repo, mock_session

def test_create_prescription_success():
    """
    repo.create() passe par l'ORM (plus de procedure stockee) : il ajoute la ligne, valide la transaction,
    rafraichit l'objet (identifiant et valeurs par defaut) et RENVOIE l'objet Prescription - pas un booleen.
    """
    repo, mock_session = make_repo_with_mock_session()

    data = {
        "patient_id": 1,
        "medication": "Amoxicillin",
        "dosage": "500mg",
        "frequency": "TID",
        "duration": "7 days",
        "medical_record_id": 10,
        "start_date": "2025-01-01",
        "end_date": "2025-01-08",
        "notes": "Take after meals",
        "prescribed_by": 2,
        "prescribed_by_name": "Dr. X"
    }

    res = repo.create(data)

    assert isinstance(res, Prescription)
    assert res.medication == "Amoxicillin"
    assert res.patient_id == 1
    mock_session.add.assert_called_once_with(res)
    mock_session.commit.assert_called_once()
    mock_session.refresh.assert_called_once_with(res)
    mock_session.rollback.assert_not_called()


def test_create_prescription_db_error_rollback_and_raise():
    repo, mock_session = make_repo_with_mock_session()

    data = {"patient_id": 1, "medication": "X"}

    # Simule une exception lors de l'exécution SQL
    mock_session.execute.side_effect = Exception("DB error")

    with pytest.raises(Exception):
        repo.create(data)

    # s'assurer que rollback a été appelé en cas d'erreur
    mock_session.rollback.assert_called_once()
    mock_session.commit.assert_not_called()
