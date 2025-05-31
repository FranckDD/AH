# controllers/pharmacy_controller.py
class PharmacyController:
    def __init__(self, repo, current_user):
        self.repo = repo
        self.user = current_user

    def list_products(self):
        return self.repo.list_all()

    def create_product(self, data: dict):
        return self.repo.create(data, self.user)