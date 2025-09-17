from locust import HttpUser, TaskSet, task, between
import random

class UserBehavior(TaskSet):
    token = None
    headers = {}

    def on_start(self):
        """Connexion et récupération du token JWT"""
        login_payload = {
            "username": "Med2",   # ⚠️ remplacer par utilisateur test
            "password": "medecin123"
        }
        with self.client.post("/auth/login", data=login_payload, catch_response=True) as response:
            if response.status_code == 200:
                self.token = response.json().get("access_token")
                self.headers = {"Authorization": f"Bearer {self.token}"}
                response.success()
            else:
                response.failure(f"Login failed: {response.text}")

    # -------- Tests Patients --------
    @task(2)
    def list_patients(self):
        """Liste les patients"""
        with self.client.get("/patients?page=1&per_page=5", headers=self.headers, catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"list_patients failed: {response.text}")

    @task(1)
    def get_patient(self):
        """Vérifie un patient précis (id = 1 par défaut, ou random si tu veux)"""
        patient_id = 1
        with self.client.get(f"/patients/{patient_id}", headers=self.headers, catch_response=True) as response:
            if response.status_code in [200, 404]:
                response.success()  # On considère 404 comme un cas valide
            else:
                response.failure(f"get_patient failed: {response.text}")

    # -------- Tests Rendez-vous --------
    @task(1)
    def get_appointment(self):
        """Vérifie un rendez-vous"""
        appointment_id = random.randint(1, 5)  # ⚠️ adapter selon tes données
        with self.client.get(f"/appointments/{appointment_id}", headers=self.headers, catch_response=True) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"get_appointment failed: {response.text}")

    # -------- Tests Prescriptions --------
    @task(1)
    def get_prescription(self):
        """Vérifie une prescription"""
        prescription_id = 1
        with self.client.get(f"/prescriptions/{prescription_id}", headers=self.headers, catch_response=True) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"get_prescription failed: {response.text}")


class WebsiteUser(HttpUser):
    tasks = [UserBehavior]
    wait_time = between(1, 3)
