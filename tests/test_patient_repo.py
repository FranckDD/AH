# tests/test_patient_repo.py
from unittest.mock import MagicMock
import pytest
import sys
import os

# Ajouter le dossier racine du projet au PATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


# Adapte l'import selon ton projet
from repositories.patient_repo import PatientRepository

def make_repo_with_mock_session():
    mock_session = MagicMock()
    repo = PatientRepository(session=mock_session)
    return repo, mock_session

def test_update_patient_success():
    repo, mock_session = make_repo_with_mock_session()

    patient = MagicMock()
    patient.id = 1
    patient.first_name = "Alice"

    mock_session.query.return_value.filter.return_value.one_or_none.return_value = patient

    data = {
        "first_name": "Alicia",
        "residence": "Douala"
    }

    res = repo.update_patient(patient_id=1, data=data, current_user={"id": 99, "name": "admin"})
    # selon implémentation, update_patient peut retourner le patient ou un code ; on adapte l'assertion
    # Ici on suppose qu'il retourne l'entité mise à jour
    assert res is not None
    assert patient.first_name == "Alicia"
    assert patient.residence == "Douala"
    mock_session.commit.assert_called_once()
    mock_session.refresh.assert_called_once_with(patient)

def test_update_patient_not_found():
    repo, mock_session = make_repo_with_mock_session()

    mock_session.query.return_value.filter.return_value.one_or_none.return_value = None

    res = repo.update_patient(patient_id=999, data={"first_name": "X"}, current_user={"id": 1})
    assert res is None
    mock_session.commit.assert_not_called()
