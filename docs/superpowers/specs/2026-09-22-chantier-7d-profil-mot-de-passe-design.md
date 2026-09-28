# Chantier 7d — Profil et mot de passe : design

**Registre couvert :** `L3f` (`docs/superpowers/SUIVI-AVANCEMENT.md`) : « Changer son mot de passe » et « modifier son profil » absents pour tous les rôles.

**Ordre du chantier 7 confirmé par l'utilisateur :** `7c` (fait) → `7b` (fait) → `L4b-e` (fait) → **7d, ce document — dernier sous-projet du chantier 7**.

## 1. Constat

Vérifié dans le code réel avant d'écrire cette spec :

- `PUT /auth/password` (`api_backend/backend_app/routes/auth/auth_endpoints.py:226-243`) existe déjà, complet : vérifie l'ancien mot de passe, rejette un mot de passe identique, journalise un échec via `AuditRepo`, tout câblé côté `AuthController.change_user_password`. **Jamais appelé depuis le web.**
- `GET /auth/me` (même fichier, ligne 178-190) existe mais ne renvoie que `id`, `username`, `application_role` — pas `full_name`/`email`/`contact`, pourtant des colonnes réelles et non-nulles-sauf-pour-certaines du modèle `User` (`models/user.py:14-22` : `full_name` requis, `email`/`contact` nullable).
- Aucun endpoint self-service de modification de profil n'existe. Seul un admin/manager peut modifier `full_name`/`email`/`contact` d'un utilisateur via `PUT /users/{user_id}` (`api_backend/backend_app/routes/admin/users_endpoint.py:150`, gardé `role_required("admin", "manager")`), avec un schéma `UserUpdate` qui expose aussi `username`/`password`/`role_id`/`is_active`/`specialty_id` — inutilisable tel quel pour un endpoint self-service sans risque d'élévation de privilège.
- Aucune des 3 fenêtres indépendantes (`MainLayout.vue`, `SecretaireLayout.vue`, `MedicalLayout.vue`) n'a de menu de compte — seuls le nom d'utilisateur et le rôle sont affichés en lecture seule dans l'en-tête, à côté du bouton de déconnexion.
- `LabLayout.vue` (écran Laboratoire) est monté **à l'intérieur** de `/dashboard` (`router/index.js:63-67`, enfant de `MainLayout.vue`, pas une fenêtre indépendante comme `/secretariat` ou `/medical`) — un compte `laborantin`/`biologiste` reste donc dans la coquille de `MainLayout.vue` et hérite de son en-tête. Pas de 4ᵉ fenêtre à instrumenter séparément (confirmé avec l'utilisateur avant d'écrire cette spec).

## 2. Périmètre

**Dans le périmètre :**
1. `GET /auth/me` étendu pour inclure `full_name`, `email`, `contact`.
2. Nouveau `PUT /auth/profile`, self-service, restreint à `full_name`/`email`/`contact` — `username`/`password`/`role_id`/`is_active`/`specialty_id` explicitement exclus de ce chemin, `user_id` vient exclusivement du JWT (jamais du corps de la requête).
3. `PUT /auth/password` : aucun changement backend, juste enfin appelé depuis le web.
4. `AccountModal.vue` (nouveau, combiné : onglet Profil + onglet Mot de passe), réutilisé tel quel dans les 3 layouts.
5. Bouton/menu « Mon compte » ajouté à côté du nom d'utilisateur dans les 3 en-têtes (`MainLayout.vue`, `SecretaireLayout.vue`, `MedicalLayout.vue`) — couvre de fait tous les rôles, y compris `laborantin`/`biologiste` (via `MainLayout.vue`, voir §1).

**Hors périmètre :**
- Changement de rôle, de statut actif/inactif, de spécialité, ou de nom d'utilisateur — restent admin/manager seuls, via l'écran Utilisateurs existant.
- Réinitialisation de mot de passe par un tiers (déjà couvert par l'admin via `UserModal.vue`, hors sujet ici qui est le self-service).
- Avatar/photo de profil — aucune colonne ni infra de stockage de fichier pour ça, non demandé par le registre L3f.

## 3. Backend

### 3.1 `GET /auth/me` étendu

Ajoute `full_name`, `email`, `contact` à la réponse existante :

```python
@router.get("/auth/me", tags=["Authentication"])
def get_me(current_user=Depends(get_current_user)):
    return {
        "id": current_user.user_id,
        "username": getattr(current_user, "username", None),
        "full_name": getattr(current_user, "full_name", None),
        "email": getattr(current_user, "email", None),
        "contact": getattr(current_user, "contact", None),
        "application_role": {
            "id": getattr(current_user.application_role, "id", None),
            "role_name": getattr(current_user.application_role, "role_name", None),
        }
    }
```

Changement additif, rétrocompatible — aucun consommateur existant de `/auth/me` ne lit ces 3 clés aujourd'hui (vérifié par grep sur `authStore.user` : seuls `username`, `application_role.role_name`, et l'`id` implicite via le token sont lus actuellement).

### 3.2 Nouveau `PUT /auth/profile`

**Deux faits réels vérifiés en écrivant cette section, ni supposés ni copiés de l'endpoint admin sans relecture :**

1. `users_endpoint.py::get_user_controller` (la factory de dépendance qu'on aurait envie de réutiliser telle quelle) ne peut **pas** être importée dans `auth_endpoints.py` : `users_endpoint.py` importe déjà `get_current_user`/`role_required` **depuis** `auth_endpoints.py` (`users_endpoint.py:12`) — un import dans l'autre sens créerait un cycle. Le nouvel endpoint construit son propre `UserController` inline, à partir de `UserRepository`/`RoleRepository` (modules feuilles, aucun risque de cycle).
2. `UserController.update_user` (`controller/user_controller.py:39-53`) attrape aujourd'hui `except SQLAlchemyError` **seul** autour du `commit()` — et `IntegrityError` est une sous-classe de `SQLAlchemyError` en SQLAlchemy. Toute violation de contrainte (ex. email dupliqué) est donc déjà convertie en `RuntimeError` générique **avant** de sortir du contrôleur : le bloc `except IntegrityError` de l'endpoint admin existant (`users_endpoint.py:158-160`) n'a en réalité jamais pu s'exécuter, c'est du code mort qui masque un vrai bug pré-existant (un email dupliqué renvoie un 500 générique au lieu d'un 409 propre). Comme le nouvel endpoint self-service réutilise le même contrôleur et que ce chantier a explicitement besoin d'un 409 propre pour l'email (cas réaliste ici, contrairement à l'écran admin où c'est rare), `update_user` est corrigé pour laisser `IntegrityError` remonter distinctement — corrige au passage le même bug, silencieusement, pour l'endpoint admin existant.

Fix dans `controller/user_controller.py` (ajouter `IntegrityError` à l'import existant `from sqlalchemy.exc import SQLAlchemyError`) :

```python
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
```

```python
    def update_user(self, user_id: int, data: dict) -> User:
        user = self.user_repo.session.query(User).get(user_id)
        if not user:
            raise ValueError(f"Utilisateur {user_id} introuvable")
        for field in ('full_name','email', 'contact','postgres_role','is_active','role_id','specialty_id'):
            if field in data:
                setattr(user, field, data[field])
        if data.get('password'):
            user.set_password(data['password'])
        try:
            self.user_repo.session.commit()
            return user
        except IntegrityError:
            self.user_repo.session.rollback()
            raise
        except SQLAlchemyError as e:
            self.user_repo.session.rollback()
            raise RuntimeError(f"Erreur mise à jour utilisateur : {e}")
```

Nouveau schéma restreint (jamais réutiliser `UserUpdate`, qui expose des champs admin-only) :

```python
class SelfProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    contact: Optional[str] = None
```

Endpoint dans `auth_endpoints.py`, à la suite de `update_password`, avec sa propre factory de dépendance locale (pas d'import depuis `users_endpoint.py`, voir point 1 ci-dessus) :

```python
def get_self_user_controller(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserController:
    user_repo = UserRepository(session=db)
    role_repo = RoleRepository(session=db)
    return UserController(user_repo=user_repo, role_repo=role_repo)

@router.put("/auth/profile", tags=["Authentication"])
def update_my_profile(
    data: SelfProfileUpdate,
    user_ctrl: UserController = Depends(get_self_user_controller),
    current_user = Depends(get_current_user),
):
    try:
        payload = data.model_dump(exclude_unset=True)
        updated = user_ctrl.update_user(current_user.user_id, payload)
        return {
            "id": updated.user_id,
            "username": updated.username,
            "full_name": updated.full_name,
            "email": updated.email,
            "contact": updated.contact,
        }
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except IntegrityError as ie:
        try: user_ctrl.user_repo.session.rollback()
        except: pass
        raise translate_integrity_error(ie)
```

(new imports needed in `auth_endpoints.py` : `UserController`, `UserRepository`, `RoleRepository`, `IntegrityError`, `translate_integrity_error`, `EmailStr`/`Optional` déjà probablement disponibles via `pydantic`/`typing` mais à vérifier au moment du plan.)

`user_id` vient exclusivement de `current_user` (JWT décodé) — jamais du corps de la requête ou d'un paramètre d'URL, donc aucun moyen pour un utilisateur de modifier le profil de quelqu'un d'autre par ce chemin. `SelfProfileUpdate` n'a pas de champ `role_id`/`is_active`/`username`/`password` : même en réutilisant `UserController.update_user` (déjà utilisé par l'admin), l'élévation de privilège est structurellement impossible — le payload transmis au contrôleur ne peut physiquement contenir que les 3 champs autorisés.

### 3.3 `PUT /auth/password`

Inchangé.

## 4. Frontend

### 4.1 `authStore.js`

Deux nouvelles actions (store Options API existant) :

```javascript
async updateProfile(payload) {
    const response = await api.put('/auth/profile', payload);
    this.user = { ...this.user, ...response.data };
    localStorage.setItem('user', JSON.stringify(this.user));
    return response.data;
},

async changePassword(payload) {
    return api.put('/auth/password', payload);
}
```

`updateProfile` fusionne la réponse dans `this.user` directement (pas de second aller-retour vers `/auth/me`) — le store reste la source de vérité pour l'en-tête, qui affiche déjà `authStore.user?.username`.

### 4.2 `AccountModal.vue` (nouveau)

Modale à deux onglets :
- **Profil** : `full_name`, `email`, `contact`, pré-remplis depuis `authStore.user` à l'ouverture (déjà disponibles après connexion, `GET /auth/me` étendu au §3.1). Soumission → `authStore.updateProfile(...)`.
- **Mot de passe** : ancien mot de passe, nouveau mot de passe, confirmation (validation de correspondance déjà faite côté backend par `UserPasswordUpdate.passwords_match` — dupliquée côté client pour un retour immédiat, sans remplacer la validation serveur). Soumission → `authStore.changePassword(...)`.

Erreurs affichées inline par onglet (mêmes conventions `errorMessage`/`isSaving` déjà établies pour les modales de ce projet, ex. `PatientModal.vue`, `CaisseCancelModal.vue`) — un email déjà pris par un autre compte renvoie 409 (`translate_integrity_error`), un ancien mot de passe incorrect renvoie 400 (« L'ancien mot de passe est incorrect », déjà le message exact renvoyé par le backend).

### 4.3 Intégration dans les 3 en-têtes

`MainLayout.vue`, `SecretaireLayout.vue`, `MedicalLayout.vue` gagnent chacun un bouton « Mon compte » (icône `UserCircleIcon`, déjà dans la famille Heroicons utilisée partout ailleurs) à côté de l'affichage du nom d'utilisateur, ouvrant `AccountModal.vue`. Comportement et emplacement identiques dans les 3 fichiers — pas de logique spécifique à un rôle.

## 5. Erreurs et cas limites

- Email dupliqué : contrainte `UNIQUE` réelle sur `users.email` (vérifiée dans `models/user.py:21`) — `IntegrityError` → `translate_integrity_error` → 409, message déjà cohérent avec le reste du projet.
- Champ omis dans la requête `PUT /auth/profile` (`exclude_unset=True`) : laissé inchangé, même sémantique COALESCE-like déjà établie ailleurs dans ce projet — jamais interprété comme « vider le champ ».
- Ancien mot de passe incorrect / nouveau mot de passe identique à l'ancien : déjà gérés par le backend existant (400), affichés tels quels.
- `full_name` reste `NOT NULL` en base (`models/user.py:16`) — le formulaire empêche une soumission vide pour ce champ (le backend le refuserait de toute façon au niveau SQL si jamais None était envoyé, mais `exclude_unset=True` fait qu'un champ omis ne touche jamais la colonne).

## 6. Rôles et accès

Aucune nouvelle garde de rôle : `PUT /auth/profile` et `PUT /auth/password` sont accessibles à tout utilisateur authentifié (`Depends(get_current_user)`), exactement comme `GET /auth/me` aujourd'hui — c'est le point même de « self-service », pas une question de rôle.

## 7. Auto-review

- **Placeholders** : aucun — chaque endpoint/composant référence un fichier et un comportement réels, vérifiés avant rédaction.
- **Cohérence interne** : §3.2 (nouvel endpoint) et §4.1 (store) utilisent le même nom de champs (`full_name`/`email`/`contact`) de bout en bout, cohérent avec le modèle réel et avec `GET /auth/me` étendu au §3.1.
- **Portée** : un seul sous-projet cohérent, dernier du chantier 7 — pas de décomposition supplémentaire nécessaire.
- **Ambiguïté** : la question de la fenêtre Laboratoire (posée par l'utilisateur avant validation de cette spec) est explicitement tranchée au §1 — `LabLayout.vue` est un enfant de `MainLayout.vue`, pas une fenêtre indépendante, donc déjà couvert par les 3 en-têtes du périmètre, pas un 4ᵉ à ajouter.
- **Découvertes réelles pendant la rédaction, pas supposées** : (a) importer `get_user_controller` depuis `users_endpoint.py` dans `auth_endpoints.py` créerait un cycle d'import (le sens inverse existe déjà) — évité par une factory locale dans `auth_endpoints.py` (§3.2) ; (b) `UserController.update_user` attrapait `IntegrityError` sans distinction dans son `except SQLAlchemyError` générique, rendant le bloc `except IntegrityError` de l'endpoint admin existant inatteignable — un email dupliqué renvoyait déjà un 500 au lieu d'un 409 avant ce chantier, corrigé au passage puisque le nouvel endpoint self-service en a directement besoin (§3.2).
