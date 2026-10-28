# scripts/create_first_admin.py
"""Creation du premier compte administrateur (usage unique, base neuve).

    # saisie masquee (recommande, rien dans l'historique du shell) :
    docker compose exec -it api python scripts/create_first_admin.py

    # sans terminal (pas de -it) : le mot de passe est lu sur UNE ligne de l'entree standard,
    # a fournir depuis un fichier protege (jamais en clair dans la commande ni l'historique) :
    docker compose exec -T api python scripts/create_first_admin.py < /chemin/secret.txt
    # (ligne 1 = identifiant, ligne 2 = mot de passe ; ou AH2_ADMIN_USER dans l'environnement
    #  et seulement le mot de passe dans le fichier)

L'identifiant et le mot de passe peuvent aussi venir des variables AH2_ADMIN_USER et
AH2_ADMIN_PASSWORD de l'environnement du conteneur (jamais en argument de ligne de commande).

Refuse : mot de passe vide, compose d'espaces ou avec des espaces au debut ou a la fin, de moins
de 12 caracteres (ou de plus de 72 octets, limite de bcrypt), et toute execution si un utilisateur au role admin existe deja. Le mot de passe et son
empreinte ne sont jamais affiches ni journalises. Code 0 en cas de succes, 1 sinon.

Note : le modele User n'a aucun champ "changer le mot de passe a la premiere connexion" ;
l'admin doit le changer lui-meme (PUT /auth/profile, ecran Profil) apres sa premiere connexion.
"""
import getpass
import logging
import os
import sys

if __package__ in (None, ""):  # lance comme fichier : la racine du projet dans le chemin d'import
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

log = logging.getLogger("create_first_admin")

MIN_PASSWORD_LENGTH = 12
MAX_PASSWORD_BYTES = 72  # bcrypt ignore / refuse au-dela
ADMIN_ROLE_NAME = "admin"
ADMIN_POSTGRES_ROLE = "app_admin"  # valeur de users.postgres_role pour le role admin (cf. base de dev)


class AdminCreationError(Exception):
    """Refus metier (mot de passe invalide, admin deja present, role absent...)."""


def create_first_admin(session, username: str, password: str) -> int:
    """Cree l'admin et renvoie son user_id. Commit inclus. Ne journalise jamais le mot de passe."""
    from models.application_role import ApplicationRole
    from models.user import User, pwd_context

    username = (username or "").strip()
    if not username:
        raise AdminCreationError("Identifiant vide.")
    if len(username) > 50:
        raise AdminCreationError("Identifiant trop long (50 caracteres au plus).")
    if not password or not password.strip():
        raise AdminCreationError("Mot de passe vide.")
    if password != password.strip():
        raise AdminCreationError("Le mot de passe ne doit pas commencer ni finir par un espace.")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise AdminCreationError(
            f"Mot de passe trop court ({MIN_PASSWORD_LENGTH} caracteres au minimum)."
        )
    if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        raise AdminCreationError(f"Mot de passe trop long ({MAX_PASSWORD_BYTES} octets au plus).")

    role = session.query(ApplicationRole).filter_by(role_name=ADMIN_ROLE_NAME).one_or_none()
    if role is None:
        raise AdminCreationError(
            "Le role 'admin' n'existe pas : lancer d'abord scripts/init_prod_db.sh."
        )
    already = session.query(User.user_id).filter(User.role_id == role.role_id).first()
    if already is not None:
        raise AdminCreationError("Un compte administrateur existe deja : rien n'a ete cree.")
    if session.query(User.user_id).filter(User.username == username).first() is not None:
        raise AdminCreationError("Cet identifiant est deja utilise.")

    user = User(
        username=username,
        password_hash=pwd_context.hash(password),
        full_name="Administrateur",
        postgres_role=ADMIN_POSTGRES_ROLE,
        role_id=role.role_id,
        is_active=True,
    )
    session.add(user)
    session.flush()
    user_id = int(user.user_id)
    session.commit()
    log.info("Compte administrateur cree (user_id=%s, identifiant=%s).", user_id, username)
    return user_id


def _default_factory():
    from api_backend.backend_app.database import SessionLocal
    return SessionLocal()


def main(session_factory=None, env=None, getpass_fn=None, input_fn=None,
         is_tty=None, stdin_readline=None) -> int:
    env = os.environ if env is None else env
    getpass_fn = getpass_fn or getpass.getpass
    input_fn = input_fn or input
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    session = None
    try:
        interactive = bool(is_tty()) if is_tty is not None else sys.stdin.isatty()
        username = env.get("AH2_ADMIN_USER") or input_fn("Identifiant de l'administrateur : ")
        password = env.get("AH2_ADMIN_PASSWORD")
        if not password:
            if interactive:
                password = getpass_fn("Mot de passe (12 caracteres au minimum) : ")
                if password != getpass_fn("Confirmer le mot de passe : "):
                    print("Les deux saisies different : rien n'a ete cree.", file=sys.stderr)
                    return 1
            else:
                # Pas de terminal : getpass ferait ECHO du mot de passe. On lit une ligne de
                # l'entree standard (fichier / tube), sans rien afficher.
                print("Entree standard non interactive : mot de passe lu sur une ligne de stdin.",
                      file=sys.stderr)
                password = (stdin_readline or sys.stdin.readline)().rstrip("\r\n")
        session = (session_factory or _default_factory)()
        user_id = create_first_admin(session, username, password)
        print(f"Administrateur cree : identifiant={username.strip()} id={user_id}")
        print("A faire : se connecter puis changer le mot de passe (ecran Profil), "
              "l'application n'impose pas ce changement.")
        return 0
    except AdminCreationError as exc:
        print(f"Refus : {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # jamais le detail : une erreur SQL peut contenir l'empreinte
        print(f"Echec inattendu ({type(exc).__name__}) : rien n'a ete cree.", file=sys.stderr)
        if session is not None:
            try:
                session.rollback()
            except Exception:
                pass
        return 1
    finally:
        if session is not None:
            session.close()


if __name__ == "__main__":
    sys.exit(main())
