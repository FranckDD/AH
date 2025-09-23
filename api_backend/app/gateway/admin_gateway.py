# gateway/admin_gateway.py
import requests

class AdminGateway:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def list_users(self, search: str = None):
        params = {}
        if search:
            params["search"] = search
        r = requests.get(f"{self.base_url}/users", params=params)
        r.raise_for_status()
        return r.json()

    def get_user(self, user_id: int):
        r = requests.get(f"{self.base_url}/users/{user_id}")
        r.raise_for_status()
        return r.json()

    def create_user(self, data: dict):
        r = requests.post(f"{self.base_url}/users", json=data)
        r.raise_for_status()
        return r.json()

    def update_user(self, user_id: int, data: dict):
        r = requests.put(f"{self.base_url}/users/{user_id}", json=data)
        r.raise_for_status()
        return r.json()

    def delete_user(self, user_id: int):
        r = requests.delete(f"{self.base_url}/users/{user_id}")
        r.raise_for_status()
        return r.json()
