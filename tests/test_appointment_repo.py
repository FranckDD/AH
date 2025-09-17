# tests/test_appointment_repo.py
from unittest.mock import MagicMock
import pytest
import sys
import os

# Ajouter le dossier racine du projet au PATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


# Adapte l'import ci-dessous si ta structure diffère
from repositories.appointment_repo import AppointmentRepository

def make_repo_with_mock_session():
    mock_session = MagicMock()
    repo = AppointmentRepository(session=mock_session)
    return repo, mock_session

def test_update_appointment_success():
    repo, mock_session = make_repo_with_mock_session()

    # Simule un objet appointment retourné par one_or_none()
    appt = MagicMock()
    appt.id = 123
    appt.some_field = "old"

    # config the chained calls: session.query(...).filter(...).one_or_none() -> appt
    mock_query = mock_session.query.return_value
    mock_filter = mock_query.filter.return_value
    mock_filter.one_or_none.return_value = appt

    update_data = {"some_field": "new", "status": "confirmed"}

    result = repo.update(appointment_id=123, data=update_data)

    # Vérifications sur la mise à jour des attributs
    assert result is appt
    assert appt.some_field == "new"
    assert appt.status == "confirmed"
    # commit and refresh called
    mock_session.commit.assert_called_once()
    mock_session.refresh.assert_called_once_with(appt)

def test_update_appointment_not_found():
    repo, mock_session = make_repo_with_mock_session()

    # one_or_none renvoie None si introuvable
    mock_session.query.return_value.filter.return_value.one_or_none.return_value = None

    result = repo.update(appointment_id=9999, data={"any": "value"})

    assert result is None
    # commit/refresh ne doivent pas être appelés
    mock_session.commit.assert_not_called()
    mock_session.refresh.assert_not_called()
