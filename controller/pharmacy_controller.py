# controllers/pharmacy_controller.py

class PharmacyController:
    def __init__(self, repo, current_user):
        self.repo = repo
        self.user = current_user  

    def list_products(self):
        return self.repo.list_all()
    
    def search_products(self, term=None, type_filter=None, status_filter=None):
        return self.repo.search(term, type_filter, status_filter)

    def get_product(self, medication_id: int):
        prod = self.repo.get_by_id(medication_id)
        if not prod:
            raise ValueError(f"Aucun produit trouvé pour l'ID {medication_id}")
        return prod

    def create_product(self, data: dict):
        """
        data doit contenir :
          - drug_name (str)
          - quantity (int)
          - threshold (int)
          - medication_type (str, libre)
          - dosage_mg (float) [facultatif]
          - expiry_date (datetime) [facultatif]
          - prescribed_by (int) [facultatif]
          - name_dr (str) [facultatif]
        """
        return self.repo.create(data, self.user)

    def update_product(self, medication_id: int, data: dict):
        """
        data peut contenir n’importe quel sous-ensemble de :
          drug_name, quantity, threshold, medication_type, dosage_mg, expiry_date, prescribed_by, name_dr
        """
        return self.repo.update(medication_id, data, self.user)

    def delete_product(self, medication_id: int):
        return self.repo.delete(medication_id)

    def renew_stock(self, medication_id: int, added_quantity: int):
        """
        Réapprovisionne le stock d’un produit existant.
        """
        return self.repo.renew_stock(medication_id, added_quantity, self.user)

    def list_critical_or_empty(self):
        return self.repo.get_critical_or_empty()
