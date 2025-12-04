# repositories/caisse_repo.py

from sqlalchemy.orm import Session
from sqlalchemy.orm import relationship,joinedload
from datetime import datetime, date
from sqlalchemy import select, func, or_
from typing import List, Dict

from models.caisse import Caisse
from models.caisse_item import CaisseItem
from models.pharmacy import Pharmacy
from utils.invoice_pdf_generator import export_invoice_to_pdf_bytes
from models.paiement_echelonne import PaiementEchelonne
from models.stock_movement import StockMovement


class CaisseRepository:
    def __init__(self, session: Session):
        self.session = session

    def list_all(self):
        """
        Retourne toutes les transactions (Caisse) avec leurs lignes (CaisseItem), triées par paid_at DESC.
        """
        return (
            self.session
                .query(Caisse)
                .order_by(Caisse.paid_at.desc())
                .all()
        )

    def get_by_id(self, transaction_id: int) -> Caisse:
        """
        Récupère une transaction par son ID (avec ses items).
        """
        return self.session.get(Caisse, transaction_id)

    def list_by_patient(self, patient_id: int):
        """
        Retourne toutes les transactions associées à un patient (même NULLABLE), triées par paid_at DESC.
        """
        return (
            self.session
                .query(Caisse)
                .filter(Caisse.patient_id == patient_id)
                .order_by(Caisse.paid_at.desc())
                .all()
        )

    def list_by_payment_method(self, payment_method: str):
        """
        Filtre par mode de paiement (ex. 'Espèces', 'Carte', 'Chèque', ...), triées par paid_at DESC.
        """
        return (
            self.session
                .query(Caisse)
                .filter(Caisse.payment_method == payment_method)
                .order_by(Caisse.paid_at.desc())
                .all()
        )

    def list_by_date_range(self, date_from: date, date_to: date):
        """
        Liste les transactions dont paid_at est entre date_from et date_to (inclus),
        triées par paid_at DESC.
        """
        return (
            self.session
                .query(Caisse)
                .filter(func.date(Caisse.paid_at).between(date_from, date_to))
                .order_by(Caisse.paid_at.desc())
                .all()
        )

    def get_daily_total(self, for_date: date) -> float:
        """
        Somme des montants encaissés pour la date spécifiée.
        """
        total = (
            self.session
                .query(func.coalesce(func.sum(Caisse.amount), 0.0))
                .filter(func.date(Caisse.paid_at) == for_date)
                .scalar()
        )
        # scalar() retourne un Decimal ou un int ; on force en float avant de renvoyer
        return float(total or 0.0)

    def search_transactions(
        self,
        term: str = None,
        payment_method: str = None,
        status: str = None,  # <--- NOUVEAU PARAMÈTRE
        date_from: date = None,
        date_to: date = None,
        page: int = 1,
        per_page: int = 50
    ):
        """
        Recherche avec filtres (Terme, Paiement, Statut, Dates) ET pagination SQL.
        Retourne un tuple : (liste_des_items, total_count)
        """
        query = self.session.query(Caisse)

        # --- 1. Application des Filtres ---
        
        # Filtre par terme (Type ou Créateur)
        if term:
            term_like = f"%{term.lower()}%"
            query = query.filter(
                or_(
                    func.lower(Caisse.transaction_type).like(term_like),
                    func.lower(Caisse.created_by_name).like(term_like)
                )
            )
        
        # Filtre par Mode de Paiement (Orange Money, Espèces, etc.)
        if payment_method and payment_method.lower() not in ("tous", "all"):
            query = query.filter(Caisse.payment_method == payment_method)

        # Filtre par Statut (Active / Cancelled)
        # <--- AJOUT ICI
        if status and status.lower() not in ("tous", "all"):
            query = query.filter(Caisse.status == status)
            
        # Filtre par Dates
        if date_from and date_to:
            query = query.filter(func.date(Caisse.paid_at).between(date_from, date_to))
        elif date_from:
            query = query.filter(func.date(Caisse.paid_at) >= date_from)
        elif date_to:
            query = query.filter(func.date(Caisse.paid_at) <= date_to)

        # --- 2. Calcul du nombre total (avant pagination) ---
        total_count = query.count()

        # --- 3. Application de la Pagination SQL ---
        query = query.order_by(Caisse.paid_at.desc())
        
        if page > 0 and per_page > 0:
            offset = (page - 1) * per_page
            query = query.offset(offset).limit(per_page)

        items = query.all()

        return items, total_count

    def get_total_transactions(
        self,
        status: str = None,
        date_from: datetime | None = None,
        date_to:   datetime | None = None
    ) -> float:
        """
        Calcule la somme des montants (Caisse.amount) de toutes les transactions
        dans l’intervalle [date_from .. date_to] (bornes inclusives).
        - date_from / date_to : si None, on n’applique pas la borne correspondante.
        - Renvoie 0.0 si aucune transaction dans la plage.
        """
        # On utilise coalesce(sum(amount), 0.0) pour éviter None
        query = self.session.query(func.coalesce(func.sum(Caisse.amount), 0.0))

        # --- AJOUT DU FILTRE STATUT ---
        if status:
            query = query.filter(Caisse.status == status)

        if date_from is not None:
            query = query.filter(Caisse.paid_at >= date_from)

        if date_to is not None:
            query = query.filter(Caisse.paid_at <= date_to)

        total = query.scalar()
        return float(total or 0.0)

    def create_transaction(self, data: dict, current_user) -> Caisse:
        """
        Crée une transaction complète :
        1. En-tête Caisse
        2. Lignes CaisseItem
        3. Déduction du Stock (Pharmacy) + Création Mouvement Stock (StockMovement)
        4. Enregistrement du premier paiement (si avance > 0)
        """
        # --- 1. Création de l'en-tête (Facture) ---
        # Note: advance_amount est mis à 0 ici, il sera mis à jour à l'étape 4
        tx = Caisse(
            patient_id       = data.get("patient_id"),
            patient_label    = data.get("patient_label"),
            amount           = data["amount"],      # Montant TOTAL de la facture
            advance_amount   = 0.0,                 # Initialisé à 0
            paid_at          = data.get("paid_at", datetime.now()),
            created_by_name  = current_user.username,
            handled_by       = current_user.user_id,
            payment_method   = data["payment_method"], # Méthode préférée (sera utilisée pour le 1er paiement)
            transaction_type = data["transaction_type"],
            note             = data.get("note"),
            status           = 'active'
        )
        self.session.add(tx)
        self.session.flush() # Récupère tx.transaction_id

        # --- 2. Traitement des Lignes et du Stock ---
        items = data.get("items", [])
        if not items and data.get("amount") > 0:
             # Sécurité si aucune ligne n'est envoyée
             pass 

        for line in items:
            item_type = line["item_type"]
            ref_id    = line["item_ref_id"]
            qty       = int(line["quantity"])
            
            # A. GESTION DU STOCK (Uniquement pour Médicaments et Carnets)
            # Adapte les strings selon tes besoins ("médicament", "medication", etc.)
            if item_type.lower() in ("médicament", "medication", "vente médicament", "carnet", "booklet", "vente carnet"):
                
                # 1. Récupérer le produit
                product = self.session.get(Pharmacy, ref_id)
                if not product:
                    raise ValueError(f"Produit (ID: {ref_id}) introuvable dans le stock.")

                # 2. Vérifier la disponibilité (BLOQUANT)
                if product.quantity < qty:
                    raise ValueError(
                        f"Stock insuffisant pour '{product.drug_name}'. "
                        f"Demandé: {qty}, Disponible: {product.quantity}"
                    )

                # 3. Déduire du stock
                old_qty = product.quantity
                product.quantity -= qty
                
                # Mise à jour du statut de stock (Normal, Bas, Rupture)
                if hasattr(product, 'update_stock_status'):
                    product.update_stock_status() # Si tu as cette méthode dans le modèle
                else:
                    # Logique simple de secours
                    if product.quantity == 0: product.stock_status = 'rupture'
                    elif product.quantity <= product.threshold: product.stock_status = 'bas'
                    else: product.stock_status = 'normal'
                
                self.session.add(product)

                # 4. Créer la trace du mouvement (StockMovement) - TRES IMPORTANT
                movement = StockMovement(
                    medication_id = product.medication_id,
                    change_qty    = -qty, # Négatif car sortie
                    movement_type = "VENTE",
                    created_by    = current_user.username,
                    note          = f"Vente Transaction #{tx.transaction_id}"
                )
                self.session.add(movement)

            # B. Création de la ligne de facture (CaisseItem)
            caisse_item = CaisseItem(
                transaction_id = tx.transaction_id,
                item_type      = item_type,
                item_ref_id    = ref_id,
                unit_price     = line["unit_price"],
                quantity       = qty,
                line_total     = line["line_total"],
                note           = line.get("note"),
                status         = 'active'
            )
            self.session.add(caisse_item)

        # --- 3. Gestion du Premier Paiement (Acompte / Avance) ---
        initial_advance = float(data.get("advance_amount", 0.0))
        
        if initial_advance > 0:
            # On utilise notre méthode interne, mais avec commit=False pour rester dans la même transaction atomique
            payment_data = {
                "paid_amount": initial_advance,
                "payment_method": data["payment_method"],
                "payment_type": "AVANCE", # Premier versement
                "note": "Paiement initial lors de la création"
            }
            # Appel interne de la méthode qu'on a créée plus haut
            self.add_payment_installment(tx.transaction_id, payment_data, current_user, commit=False)

        # --- 4. Commit Final ---
        try:
            self.session.commit()
            self.session.refresh(tx)
            return tx
        except Exception as e:
            self.session.rollback()
            raise e
    
    def add_payment_installment(self, transaction_id: int, data: dict, current_user, commit=True) -> PaiementEchelonne:
        """
        Enregistre un versement (Avance, Solde, etc.) pour une transaction.
        Met à jour automatiquement le champ 'advance_amount' de la transaction parente.
        """
        # 1. Vérification de la transaction
        tx = self.session.get(Caisse, transaction_id)
        if not tx:
            raise ValueError(f"Transaction {transaction_id} introuvable.")
        
        if tx.status == 'cancelled':
            raise ValueError("Impossible d'ajouter un paiement sur une transaction annulée.")

        # 2. Création de l'enregistrement de paiement
        payment = PaiementEchelonne(
            transaction_id = transaction_id,
            paid_amount    = data["paid_amount"],
            payment_method = data["payment_method"],
            payment_type   = data.get("payment_type", "VERSEMENT"), # Par défaut 'VERSEMENT'
            handled_by     = current_user.user_id,
            note           = data.get("note", "")
        )
        self.session.add(payment)
        self.session.flush() # Pour générer l'ID du paiement

        # 3. Mise à jour du total payé dans la table Caisse (Cache)
        # On ajoute le nouveau montant au montant déjà existant
        current_total = float(tx.advance_amount or 0.0)
        new_total = current_total + float(data["paid_amount"])
        
        # Sécurité : On s'assure de ne pas dépasser le montant total dû (optionnel mais conseillé)
        # if new_total > float(tx.amount):
        #     raise ValueError(f"Le montant total payé ({new_total}) dépasse le montant de la facture ({tx.amount}).")

        tx.advance_amount = new_total
        self.session.add(tx)

        if commit:
            self.session.commit()
            
        return payment


    def update_transaction(self, transaction_id: int, data: dict, current_user) -> Caisse:
        """
        Met à jour une transaction existante, et ajuste le stock si nécessaire.
        Refuse si tx.status='cancelled'.
        """
        tx = self.get_by_id(transaction_id)
        if not tx:
            raise ValueError(f"Aucune transaction trouvée pour l'ID={transaction_id}")

        # 1) Empêcher la MAJ si status = 'cancelled'
        if tx.status == 'cancelled':
            raise ValueError(f"Impossible de modifier une transaction annulée (ID={transaction_id}).")

        # 2) Rétablir d'abord le stock des anciennes lignes (avant MAJ)
        existing_items = list(tx.items)
        for old_item in existing_items:
            if old_item.item_type.lower() in ("médicament", "medication", "carnet", "booklet"):
                med = self.session.get(Pharmacy, old_item.item_ref_id)
                if med:
                    med.quantity += old_item.quantity
                    med.update_stock_status()
                    self.session.add(med)
        # Supprimer les anciennes lignes
        for old_item in existing_items:
            self.session.delete(old_item)
        self.session.flush()

        # 3) Mettre à jour les champs de l’en-tête
        if "amount" in data:
            tx.amount = data["amount"]
        if "advance_amount" in data:
            tx.advance_amount = data["advance_amount"]
        if "payment_method" in data:
            tx.payment_method = data["payment_method"]
        if "transaction_type" in data:
            tx.transaction_type = data["transaction_type"]
        if "patient_id" in data:
            tx.patient_id = data["patient_id"]
        if "patient_label" in data:
            tx.patient_label = data["patient_label"]
        if "note" in data:
            tx.note = data["note"]
        if "paid_at" in data:
            tx.paid_at = data["paid_at"]
        # status reste inchangé (normalement 'active')

        # 4) Réinsérer les nouvelles lignes
        new_items = data.get("items", [])
        for line in new_items:
            item_type = line["item_type"]
            ref_id    = line["item_ref_id"]
            unit_price= line["unit_price"]
            qty       = line["quantity"]
            line_tot  = line["line_total"]
            item_note = line.get("note")

            if item_type.lower() in ("médicament", "medication", "carnet", "booklet"):
                med = self.session.get(Pharmacy, ref_id)
                if not med:
                    raise ValueError(f"Produit introuvable pour ID={ref_id}")
                if med.quantity < qty:
                    raise ValueError(
                        f"Stock insuffisant pour produit ID={ref_id}. "
                        f"Demandé={qty}, disponible={med.quantity}"
                    )
                med.quantity -= qty
                med.update_stock_status()
                self.session.add(med)

            new_item = CaisseItem(
                transaction_id = transaction_id,
                item_type      = item_type,
                item_ref_id    = ref_id,
                unit_price     = unit_price,
                quantity       = qty,
                line_total     = line_tot,
                note           = item_note,
                status         = 'active'
            )
            self.session.add(new_item)

        # 5) Commit final
        self.session.commit()
        return tx

    def cancel_transaction(self, transaction_id: int, current_user) -> Caisse:
        """
        Annule la transaction et restaure le stock.
        VERSION AVEC LOGS DE DEBUG pour comprendre pourquoi le stock ne remonte pas.
        """
        print(f"--- DÉBUT ANNULATION TRANSACTION #{transaction_id} ---")
        
        tx = self.get_by_id(transaction_id)
        if not tx:
            raise ValueError(f"Aucune transaction trouvée pour l'ID={transaction_id}")

        if tx.status == 'cancelled':
            print("Transaction déjà annulée.")
            return tx

        # 1) Rétablir le stock
        count_restored = 0
        
        for item in tx.items:
            # Nettoyage de la chaîne (minuscule, sans espace autour)
            raw_type = str(item.item_type)
            t_type = raw_type.lower().strip()
            
            print(f"Traitement Ligne ID: {item.item_id} | Type brut: '{raw_type}' | Type nettoyé: '{t_type}' | RefID: {item.item_ref_id}")

            # Mots-clés déclencheurs (basés sur vos données réelles)
            keywords = ["médicament", "medicament", "carnet", "booklet"]
            
            # Vérifie si l'un des mots-clés est DANS le type
            is_stock_item = any(k in t_type for k in keywords)

            if is_stock_item:
                print(f"   -> C'est un article de stock. Tentative de récupération Pharmacy ID {item.item_ref_id}...")
                
                # Récupération du produit
                med = self.session.get(Pharmacy, item.item_ref_id)
                
                if med:
                    old_qty = med.quantity
                    med.quantity += item.quantity
                    
                    # Mise à jour statut
                    if med.threshold and med.quantity <= med.threshold: med.stock_status = 'bas'
                    elif med.quantity == 0: med.stock_status = 'rupture'
                    else: med.stock_status = 'normal'
                    
                    self.session.add(med)
                    
                    print(f"   -> SUCCÈS : {med.drug_name} stock {old_qty} + {item.quantity} = {med.quantity}")

                    # Traceabilité
                    movement = StockMovement(
                        medication_id = med.medication_id,
                        change_qty    = item.quantity,
                        movement_type = "ANNULATION_VENTE",
                        created_by    = getattr(current_user, "username", "System"),
                        note          = f"Annul. Tx #{tx.transaction_id}"
                    )
                    self.session.add(movement)
                    count_restored += 1
                else:
                    print(f"   -> ERREUR CRITIQUE : Produit ID {item.item_ref_id} introuvable dans la table Pharmacy !")
            else:
                print("   -> Ignoré (pas un médicament ni un carnet).")

        # 2) Marquer tout comme annulé
        tx.status = 'cancelled'
        self.session.add(tx)

        for item in tx.items:
            item.status = 'cancelled'
            self.session.add(item)

        self.session.commit()
        print(f"--- FIN ANNULATION ({count_restored} articles restaurés) ---")
        return tx

    def delete_transaction(self, transaction_id: int) -> Caisse:
        """
        Supprime définitivement la transaction (usage exceptionnel, sans remettre en stock).
        """
        tx = self.get_by_id(transaction_id)
        if tx:
            self.session.delete(tx)
            self.session.commit()
        return tx
    
    def settle_transaction(self, transaction_id: int, user_id: int) -> Caisse:
        """
        Solde une transaction : met l'avance égale au montant total.
        """
        tx = self.get_by_id(transaction_id)
        if not tx:
            raise ValueError("Transaction introuvable")
        
        if tx.status == 'cancelled':
            raise ValueError("Impossible de solder une transaction annulée")

        # Mise à jour : l'avance devient le total (tout est payé)
        tx.advance_amount = tx.amount
        # On pourrait aussi ajouter une note système ici si on voulait
        # tx.note = (tx.note or "") + f"\n[Soldé par user {user_id} le {datetime.now()}]"
        
        self.session.commit()
        self.session.refresh(tx)
        return tx
    
    def get_transaction_details_for_invoice(self, transaction_id: int) -> dict | None:
        """
        Récupère l'objet Caisse et le convertit en un dictionnaire complet.
        CORRECTION : Utilise 'patient_by_id' au lieu de 'patient'.
        """
        tx = self.get_by_id(transaction_id) 

        if not tx:
            return None
        
        # --- CORRECTION ICI ---
        # 1. On récupère l'objet patient via la relation correcte : 'patient_by_id'
        patient_obj = getattr(tx, "patient_by_id", None)
        
        # 2. On détermine le nom
        patient_name = tx.patient_label or "Inconnu" # Valeur par défaut (le label saisi manuellement)

        if patient_obj:
            # Si l'objet patient existe, on essaie de construire le nom complet
            if hasattr(patient_obj, 'full_name'):
                patient_name = patient_obj.full_name
            else:
                # Construction manuelle si 'full_name' n'existe pas dans le modèle Patient
                fname = getattr(patient_obj, 'first_name', '') or ""
                lname = getattr(patient_obj, 'last_name', '') or ""
                patient_name = f"{fname} {lname}".strip()
        
        # Le nom de l'enregistreur
        user_name = getattr(tx, "created_by_name", "Système")
        
        # Construction des lignes d'articles
        items_list = []
        for item in tx.items:
            # Sécurisation du nom de l'article
            i_name = getattr(item, "item_name", item.item_type)
            
            items_list.append({
                "item_type": item.item_type,
                "item_ref_id": item.item_ref_id,
                "quantity": item.quantity,
                "unit_price": float(item.unit_price), # Force float
                "line_total": float(item.line_total), # Force float
                "note": item.note,
                "item_name": i_name
            })
            
        return {
            "transaction_id": tx.transaction_id,
            "patient_name": patient_name,
            "user_name": user_name,
            "amount": float(tx.amount),
            "advance_amount": float(tx.advance_amount),
            "paid_at": tx.paid_at.isoformat() if tx.paid_at else None,
            "status": tx.status,
            "items": items_list,
        }
    
    # Dans repositories/caisse_repo.py

    def get_total_payments(
        self,
        status: str = None,
        date_from: datetime | None = None,
        date_to:   datetime | None = None
    ) -> float:
        """
        Calcule la somme des ENCAISSEMENTS RÉELS (advance_amount) et non du facturé.
        C'est ce montant qui constitue l'argent physique en caisse.
        """
        # NOTEZ BIEN : On somme 'advance_amount' ici
        query = self.session.query(func.coalesce(func.sum(Caisse.advance_amount), 0.0))

        if status:
            query = query.filter(Caisse.status == status)

        if date_from is not None:
            query = query.filter(Caisse.paid_at >= date_from)

        if date_to is not None:
            query = query.filter(Caisse.paid_at <= date_to)

        total = query.scalar()
        return float(total or 0.0)
    
    def generate_invoice_pdf_content(self, transaction_id: int) -> bytes:
        """
        1. Récupère toutes les données nécessaires pour la facture.
        2. Appelle la fonction utilitaire qui construit le fichier PDF.
        """

        # 1. Récupération des Données de la Transaction
        transaction_data = self.get_transaction_details_for_invoice(transaction_id) 

        if not transaction_data:
            raise ValueError(f"Transaction ID {transaction_id} non trouvée pour génération PDF.")

        # 2. Génération du PDF
        # REMPLACER LE BLOC TRY...EXCEPT PAR CES DEUX LIGNES :
        pdf_bytes = export_invoice_to_pdf_bytes(transaction_data) 
        return pdf_bytes
    
    def get_unpaid_transactions_details(
        self, 
        date_from: date | None = None, 
        date_to: date | None = None
    ) -> List[Dict]:
        """
        Récupère la liste détaillée des transactions impayées (amount > advance_amount) 
        pour la période donnée (sur la base de Caisse.paid_at).
        """
        
        # On pré-charge la relation patient_by_id pour éviter N+1 queries
        query = self.session.query(Caisse).options(joinedload(Caisse.patient_by_id))
        
        # 1. Filtre principal : transactions impayées (reste à payer > 0)
        query = query.filter(Caisse.amount > Caisse.advance_amount)
        
        # 2. Filtre de statut : seulement les transactions actives (non 'cancelled')
        query = query.filter(Caisse.status != 'cancelled') 

        # 3. Filtre de période (basé sur paid_at)
        if date_from and date_to:
            query = query.filter(func.date(Caisse.paid_at).between(date_from, date_to))
        elif date_from:
            query = query.filter(func.date(Caisse.paid_at) >= date_from)
        elif date_to:
            query = query.filter(func.date(Caisse.paid_at) <= date_to)

        # Trier par le montant restant dû (le plus gros impayé en premier)
        query = query.order_by((Caisse.amount - Caisse.advance_amount).desc()) 

        unpaid_transactions = query.all()

        unpaid_list = []
        for tx in unpaid_transactions:
            patient_obj = getattr(tx, "patient_by_id", None)
            
            # Récupération sécurisée des infos patient
            patient_name = tx.patient_label or "N/A"
            patient_contact = "N/A"
            
            if patient_obj:
                # On réutilise la logique de get_transaction_details_for_invoice
                fname = getattr(patient_obj, 'first_name', '') or ""
                lname = getattr(patient_obj, 'last_name', '') or ""
                patient_name = f"{fname} {lname}".strip() or tx.patient_label
                patient_contact = getattr(patient_obj, 'contact', 'N/A')

            unpaid_list.append({
                "transaction_id": tx.transaction_id,
                "patient_name": patient_name,
                "patient_contact": patient_contact,
                "date": tx.paid_at.isoformat() if tx.paid_at else None,
                "total_amount": float(tx.amount),
                "paid_amount": float(tx.advance_amount),
                "remaining_due": float(tx.amount) - float(tx.advance_amount),
                "status": tx.status
            })

        return unpaid_list
    
    def get_caisse_kpis(self, date_from: date, date_to: date) -> Dict:
        """
        Calcule les KPIs financiers (Encaissements, Total Facturé, Montant Impayé)
        pour la période spécifiée.
        """
        
        # 1. Filtre de Période (Transactions actives dans la plage)
        query_base = self.session.query(Caisse).filter(
            Caisse.status != 'cancelled',
            func.date(Caisse.paid_at).between(date_from, date_to)
        )

        # 2. Agrégations
        total_factured_query = query_base.with_entities(func.coalesce(func.sum(Caisse.amount), 0.0))
        total_paid_query = query_base.with_entities(func.coalesce(func.sum(Caisse.advance_amount), 0.0))
        total_transactions_query = query_base.with_entities(func.count(Caisse.transaction_id))

        total_factured = float(total_factured_query.scalar() or 0.0)
        total_paid = float(total_paid_query.scalar() or 0.0)
        total_transactions = total_transactions_query.scalar()

        # 3. Calcul des Impayés et Taux
        # L'impayé est la différence entre Facturé et Payé (pour la période)
        remaining_due = total_factured - total_paid
        
        # Taux de recouvrement (pour la période)
        recouvrement_rate = (total_paid / total_factured) * 100 if total_factured > 0 else 0.0

        return {
            "total_paid": total_paid,
            "total_factured": total_factured,
            "remaining_due": remaining_due,
            "recouvrement_rate": round(recouvrement_rate, 2),
            "total_transactions": total_transactions,
        }
    
    def get_payment_mode_distribution(self, date_from: date, date_to: date) -> List[Dict]:
        """
        KPI: Calcule la somme des encaissements (advance_amount) groupée par mode de paiement.
        """
        query = (
            self.session.query(
                Caisse.payment_method, 
                func.sum(Caisse.advance_amount) 
            )
            .filter(Caisse.status != 'cancelled')
            .filter(func.date(Caisse.paid_at).between(date_from, date_to))
            .group_by(Caisse.payment_method) 
        )
        
        results = query.all()
        
        distribution = []
        for method, total in results:
            distribution.append({
                "method": method or "Non spécifié",
                "total": float(total or 0.0)
            })
            
        return distribution
    
    # Dans repositories/caisse_repo.py

    def get_total_remaining_due(
        self,
        status: str = None,
        date_from: datetime | None = None,
        date_to:   datetime | None = None
    ) -> float:
        """
        Calcule la somme totale des montants restants dûs (amount - advance_amount)
        pour les transactions actives.
        """
        # Formule : SUM(amount) - SUM(advance_amount)
        remaining_due_expr = Caisse.amount - Caisse.advance_amount
        
        # On utilise une requête pour la somme de l'expression
        query = self.session.query(func.coalesce(func.sum(remaining_due_expr), 0.0))

        # IMPORTANT : On ne veut que les transactions actives (ou à votre convenance)
        query = query.filter(Caisse.status == (status or 'active'))

        if date_from is not None:
            # On filtre sur la date de paiement (ou de création, selon votre besoin)
            query = query.filter(Caisse.paid_at >= date_from) 

        if date_to is not None:
            query = query.filter(Caisse.paid_at <= date_to)

        total = query.scalar()
        return float(total or 0.0)
