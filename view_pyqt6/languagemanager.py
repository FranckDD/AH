# language_manager.py
class LanguageManager:
    """
    Utility to manage UI translations for 'fr' and 'en'.
    Usage:
        from language_manager import lang
        lang.set_language('en')
        text = lang.t('patient_code')  # returns translation
    """
    def __init__(self):
        self._lang = 'fr'
        self._translations = {
            'fr': {
                'language':       'Langue',
                'patient_code':   'Code patient :',
                'load':           'Charger',
                'patient_not_found': 'Patient introuvable.',
                'date_time':      'Date/Heure :',
                'advance_amount': 'Avance (€) :',
                'trans_types':    'Type transac. :',
                'consultation':   'Consultation',
                'sale_medication':'Vente Médicament',
                'sale_booklet':   'Vente Carnet',
                'payment_method':'Mode paiement :',
                'note':           'Note :',
                'lines':          'Lignes :',
                'add_line':       'Ajouter ligne',
                'remove_line':    'Supprimer ligne',
                'total_amount':   'Montant total :',
                'save':           'Enregistrer',
                'cancel':         'Annuler',
                'transaction_list': 'Liste des Transactions',
                'search':         'Rechercher :',
                'search_ph':      'Type ou utilisateur…',
                'filter':         'Appliquer filtres',
                'reset':          'Réinitialiser',
                'from':           'Du :',
                'to':             'Au :',
                'new':            'Nouveau',
                'edit':           'Éditer',
                'cancel_tx':      'Annuler Tx',
                'delete_tx':      'Supprimer Tx',
                'make_withdrawal':'Effectuer retrait',
                'refresh':        'Rafraîchir',
                'warning':        'Attention',
            },
            'en': {
                'language':       'Language',
                'patient_code':   'Patient code:',
                'load':           'Load',
                'patient_not_found':'Patient not found.',
                'date_time':      'Date/Time:',
                'advance_amount': 'Advance (€):',
                'trans_types':    'Trans. type:',
                'consultation':   'Consultation',
                'sale_medication':'Sale Medication',
                'sale_booklet':   'Sale Booklet',
                'payment_method':'Payment method:',
                'note':           'Note:',
                'lines':          'Lines:',
                'add_line':       'Add Line',
                'remove_line':    'Remove Line',
                'total_amount':   'Total amount:',
                'save':           'Save',
                'cancel':         'Cancel',
                'transaction_list': 'Transaction List',
                'search':         'Search:',
                'search_ph':      'Type or user…',
                'filter':         'Apply filters',
                'reset':          'Reset',
                'from':           'From:',
                'to':             'To:',
                'new':            'New',
                'edit':           'Edit',
                'cancel_tx':      'Cancel Tx',
                'delete_tx':      'Delete Tx',
                'make_withdrawal':'Make Withdrawal',
                'refresh':        'Refresh',
                'warning':        'Warning',
            }
        }

    def set_language(self, lang_code: str):
        if lang_code in self._translations:
            self._lang = lang_code
        else:
            raise ValueError(f"Unsupported language: {lang_code}")

    def t(self, key: str) -> str:
        return self._translations.get(self._lang, {}).get(key, key)

# singleton
lang = LanguageManager()
