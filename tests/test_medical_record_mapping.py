from api_backend.backend_app.routes.medical_records.mapping import normalize_medical_record_data


class FakePatient:
    def __init__(self, patient_id, code_patient, first_name, last_name):
        self.patient_id = patient_id
        self.code_patient = code_patient
        self.first_name = first_name
        self.last_name = last_name


class FakeMedicalRecord:
    def __init__(self, patient=None):
        self.record_id = 1
        self.patient_id = 42
        self.consultation_date = "2026-08-14T00:00:00"
        self.motif_code = "CONSULT"
        self.marital_status = None
        self.bp = None
        self.temperature = None
        self.weight = None
        self.height = None
        self.medical_history = None
        self.allergies = None
        self.symptoms = None
        self.diagnosis = None
        self.treatment = None
        self.severity = None
        self.notes = None
        self.created_by = None
        self.created_by_name = "Dr Test"
        self.last_updated_by = None
        self.last_updated_by_name = None
        self.patient = patient


def test_normalize_includes_patient_dict_when_relation_loaded():
    fake_patient = FakePatient(42, "AH2-000042AB", "Jean", "Dupont")
    record = FakeMedicalRecord(patient=fake_patient)

    result = normalize_medical_record_data(record)

    assert result["patient"] == {
        "patient_id": 42,
        "code_patient": "AH2-000042AB",
        "first_name": "Jean",
        "last_name": "Dupont",
    }


def test_normalize_handles_missing_patient_relation_gracefully():
    record = FakeMedicalRecord(patient=None)

    result = normalize_medical_record_data(record)

    assert result.get("patient") is None
