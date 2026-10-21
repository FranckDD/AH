from repositories.caisse_repo import CaisseRepository
from tests.conftest import create_test_user
from tests.test_stock_item_types import _sale, _line

def test_cancel_exam_only_invoice(db_session):
    """Annuler une facture sans ligne de stock avec un utilisateur expire : une seule ecriture."""
    user = create_test_user(db_session, "t_cancel_exam", "secretaire")
    repo = CaisseRepository(db_session)
    tx = _sale(repo, user, [_line("Examen", 1, 1)])
    db_session.expire(user)
    out = repo.cancel_transaction(tx.transaction_id, user, "erreur de saisie")
    assert out.status == "cancelled"
    assert out.cancelled_by == user.user_id
    assert out.cancel_justification == "erreur de saisie"
