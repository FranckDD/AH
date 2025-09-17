class DashboardService:
    def __init__(self, remote_gateway):
        self.api = remote_gateway

    # Patients distincts
    def distinct_patients_count(self, start, end):
        return self.api.get_distinct_patients_count(start, end)

    # RDV
    def total_appointments(self, start, end):
        return self.api.get_total_appointments(start, end)

    def count_by_status(self, start, end):
        return self.api.get_appointments_status_count(start, end)

    def appointments_time_series(self, start, end):
        return self.api.get_appointments_time_series(start, end)

    def get_by_day(self, date):
        return self.api.get_appointments_by_day(date)

    def upcoming_today(self):
        return self.api.get_today_appointments()

    def upcoming_appointments(self, limit):
        return self.api.get_upcoming_appointments(limit)

    def modify_appointment(self, appointment_id, data):
        return self.api.modify_appointment(appointment_id, data)

    def accept_appointment(self, appointment_id):
        return self.api.accept_appointment(appointment_id)

    def cancel_appointment(self, appointment_id):
        return self.api.cancel_appointment(appointment_id)

    def complete_appointment(self, appointment_id):
        return self.api.complete_appointment(appointment_id)

    # Patients
    def count_registered(self, period="day"):
        return self.api.get_registered_patients_count(period)

    def patients_for_day(self, date):
        return self.api.get_patients_registered_on(date)

    def get_patient(self, patient_id):
        return self.api.get_patient(patient_id)

    def find_patient(self, query=None, code=None):
        if code:
            return self.api.find_patient_by_code(code)
        return self.api.find_patient(query)

    def find_patient_by_code(self, code):
        return self.api.find_patient_by_code(code)

    def find_patient_for_prescription(self, q):
        return self.api.find_patient_for_prescription(q)

    # Médical records
    def count_consultations(self, period="day"):
        return self.api.get_consultations_count(period)

    def list_records(self, page, per_page, **kwargs):
        return self.api.list_medical_records(page, per_page, **kwargs)

    def get_by_day_records(self, date):
        return self.api.list_medical_records(date_from=date, date_to=date)

    def list_records_for_patient(self, patient_id):
        return self.api.list_medical_records_by_patient(patient_id)

    def get_record(self, record_id):
        return self.api.get_medical_record(record_id)

    def get_last_for_patient(self, patient_id):
        return self.api.get_last_for_patient(patient_id)

    # Prescriptions
    def count_prescriptions(self, period="day"):
        return self.api.get_prescriptions_count(period)

    def create_prescription(self, payload):
        return self.api.create_prescription(payload)

    def list_prescriptions(self, patient_id, **kwargs):
        return self.api.list_prescriptions(patient_id=patient_id, **kwargs)

    def renewals_for_doctor(self, within_days=14):
        return self.api.get_renewals_for_doctor(within_days)
