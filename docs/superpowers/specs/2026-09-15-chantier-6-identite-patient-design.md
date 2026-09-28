# Chantier 6 — Réparer l'identité patient et construire le dossier consolidé

**Date** : 2026-09-15
**Origine** : registre `L2` (identité patient rompue) et `L5` (politique d'accès, déjà tranchée) de `SUIVI-AVANCEMENT.md`, audit transversal du 2026-09-15
**Position** : troisième chantier de la remise à niveau (après chantier 5, fiabiliser les chiffres — terminé), avant chantier 7 (compléter le portage)

## Objectif

Faire en sorte qu'un même patient, quel que soit le domaine (clinique, toxicologie, spirituel) par lequel il entre dans le centre, corresponde à **un seul** enregistrement patient — et donner aux soignants une vue unique de son dossier complet, plutôt que des fragments dispersés et inaccessibles à la plupart des rôles.

## Pourquoi maintenant

L'audit du 2026-09-15 a établi que le problème n'est pas une interface manquante mais une donnée qui ne tient pas : l'admission toxicologique crée systématiquement un nouveau patient, sans jamais pouvoir rattacher un dossier à un patient existant. Construire une vue consolidée par-dessus cette donnée produirait des dossiers d'apparence complète mais faux. Il faut réparer l'identité avant la vue.

## Périmètre

**Inclus** :
- Rattachement à un patient existant lors de l'admission toxicologique (au lieu d'une création systématique)
- Drapeaux de domaine (`is_clinical`/`is_toxicology`/`is_spiritual`) fiabilisés — calculés, plus jamais déclaratifs
- Activation du filtre par rôle de la liste patients (`B6`), conservé inerte depuis le chantier 5 faute de drapeaux fiables
- Un nouvel endpoint de dossier consolidé, tolérant aux pannes par domaine
- Politique d'accès déjà tranchée le 2026-09-15 : soignants + admin + promoteur, protégée par journalisation de chaque consultation — réutilisant l'infrastructure d'audit déjà en place (`AuditUserAction`/`log_user_action`), pas une nouvelle
- Création du rôle `promoteur`

**Exclus explicitement** :
- Dédoublonnage des patients déjà dupliqués en base : décision du 2026-09-15, les données actuelles sont des données de test, destinées à être purgées avant la mise en production à la fin de tous les chantiers. Fusionner maintenant serait un risque pris pour rien.
- Les gardes de rôle des 4 modules existants (dossiers médicaux, prescriptions, consultations spirituelles, toxicologie — registre `L4b-e`) : laissées intactes. Le nouvel endpoint consolidé porte sa propre vérification d'accès ; les écrans existants gardent la leur. Toucher aux quatre fichiers de routes existants pour un gain marginal par rapport à l'objectif de ce chantier serait un risque de régression non justifié.
- Toute action hors ligne : ce chantier ne rend rien disponible hors connexion. Le hors-ligne s'ajoute en fin de chantier 7, module par module.

## Modèle de données — ce qui existe et ce qui change

Aucune migration de schéma. Toutes les tables et colonnes nécessaires existent déjà :
- `patients.patient_id`, `patients.national_id` (nullable, jamais renseigné par le parcours toxico), `patients.is_clinical`/`is_toxicology`/`is_spiritual` (colonnes conservées, mais leur donnée provient désormais d'un calcul, plus d'une écriture à la création)
- `medical_records.patient_id`, `toxico_dossiers.patient_id`, `consultation_spirituel.patient_id` — toutes des clés étrangères réelles vers `patients`, déjà vérifiées `NOT NULL` (sauf `consultation_spirituel.patient_id`, nullable — une consultation peut historiquement ne pas être rattachée à un patient existant en base ; ce cas reste possible, le dossier consolidé ne remonte alors rien pour ce domaine)
- `application_roles` (`role_id`, `role_name`) — une ligne à insérer pour `promoteur`
- `audit_user_actions` (`action_id`, `user_id`, `timestamp`, `resource_type`, `resource_id`, `action_performed`, `old_values`, `new_values`, `ip_address`, `username`) — déjà en place, déjà écrite par `AuditRepository.log_user_action()`, déjà appelée depuis 8 contrôleurs existants (dont `patient_controller.py`, `toxico_controller.py`). Ce chantier ajoute un appel de plus, pas de nouvelle table.

## Section 1 — Rattachement à un patient existant

**Décision (2026-09-15)** : recherche assistée avec confirmation humaine, jamais de rattachement automatique. Le numéro national d'identité existe en base mais n'est quasiment jamais renseigné (confirmé à l'audit) — un rapprochement automatique dessus couvrirait trop peu de cas réels pour justifier le risque d'un mauvais rattachement automatique sur un autre critère.

**Correction (vérifiée dans le code réel, corrige une hypothèse fausse de la première version de cette spec)** : l'admission toxicologique (`POST /toxico/admission`) est réservée à `ToxicoManager, admin, Assistant` — pas `secretaire`, malgré ce que la première version de cette spec supposait. La personne qui admet est donc un compte `Assistant` (le rôle réellement utilisé en pratique aujourd'hui, `ToxicoManager` n'ayant aucun compte) ou `admin`.

**Frontend** — `ToxicoAdmissionModal.vue` gagne une étape de recherche avant la saisie des données patient : un champ de recherche appelant `GET /patients/?search=...` (déjà fiabilisé et paginé au chantier 5). **Point à corriger en même temps** : le routeur `patients_endpoints.py` autorise aujourd'hui `medecin, nurse, secretaire, admin, manager` — ni `Assistant` ni `ToxicoManager` n'y figurent, donc la personne qui admet ne pourrait pas chercher un patient sans cet ajout. `Assistant` est ajouté à la dépendance de rôle du routeur (`role_required(...)`) — extension minimale et directement justifiée par ce besoin, distincte du nettoyage plus large des gardes de rôle `L4b-e` laissé hors périmètre : il ne s'agit pas de revoir la politique d'accès du module Patients, seulement de permettre à la personne qui admet en toxicologie de chercher un patient existant. `ToxicoManager` n'est pas ajouté (aucun compte ne porte ce rôle aujourd'hui, ajout sans effet observable, à faire si un compte est créé un jour).

Les résultats affichent code patient, nom, date de naissance. Deux issues : la personne qui admet sélectionne un patient existant (le formulaire retient son `patient_id`, saute la section « nouveau patient »), ou elle choisit « nouveau patient » (formulaire actuel, inchangé).

**Payload envoyé au backend** : soit `{"patient_id": 123, "toxico_data": {...}}` (rattachement), soit `{"patient_data": {...}, "toxico_data": {...}}` (création, comme aujourd'hui) — un seul des deux champs `patient_id`/`patient_data` est présent, jamais les deux.

**Backend** — `ToxicoController` (méthode d'admission actuelle, `controller/toxico_controller.py` autour de la ligne 136) : la création systématique via `self.patient_controller.create_patient(...)` devient conditionnelle :
```
si patient_id fourni dans les données reçues :
    vérifier que ce patient existe réellement (PatientController.get_patient(patient_id))
    si absent : lever une erreur claire (« patient introuvable, ID invalide »)
    utiliser ce patient_id directement pour la suite (création du dossier toxico)
sinon :
    comportement actuel inchangé : create_patient(patient_data_for_creation)
```
Aucune donnée du patient existant n'est modifiée par ce chemin — le rattachement ajoute un dossier toxico, il ne touche jamais aux champs du patient (nom, date de naissance, etc.), même si le formulaire d'admission en affichait de nouveaux. C'est une garde-fou délibéré : éviter qu'une saisie erronée côté toxico n'écrase silencieusement une donnée clinique déjà correcte.

## Section 2 — Drapeaux de domaine calculés, pas déclarés

**Cause du bug actuel** : `is_clinical`/`is_toxicology`/`is_spiritual` sont posés une seule fois, à la création du patient, d'après le rôle de la personne qui crée — jamais mis à jour quand un dossier est ajouté dans un autre domaine ensuite. Aucun trigger, aucune procédure ne les recalcule.

**Correction** : remplacer la lecture de ces colonnes stockées par un calcul à la demande, partout où le code les lit pour décider quoi afficher ou filtrer. Modèles réels à importer (vérifiés, noms de fichiers non triviaux) : `MedicalRecord` depuis `models/medical_record.py`, `ToxicoDossier` depuis `models/toxico.py`, `ConsultationSpirituel` depuis `models/consultation_spirituelle.py` (fichier au nom long, pas `models/cs.py`). Concrètement, dans `repositories/patient_repo.py`, une méthode réutilisable :

```python
def compute_domain_flags(self, patient_id: int) -> dict:
    """Calcule les drapeaux de domaine a la lecture, a partir de
    l'existence reelle de dossiers - jamais depuis une colonne stockee.
    Remplace patients.is_clinical/is_toxicology/is_spiritual comme source
    de verite pour toute decision d'affichage ou de filtrage."""
    return {
        "is_clinical": self.session.query(
            exists().where(MedicalRecord.patient_id == patient_id)
        ).scalar(),
        "is_toxicology": self.session.query(
            exists().where(ToxicoDossier.patient_id == patient_id)
        ).scalar(),
        "is_spiritual": self.session.query(
            exists().where(ConsultationSpirituel.patient_id == patient_id)
        ).scalar(),
    }
```

Pour la **liste** des patients (`list_patients`, `_list_by_flag` et consorts dans `patient_repo.py`), le filtre par domaine ne peut pas appeler cette méthode ligne par ligne sans coût — il doit s'exprimer comme un `EXISTS` corrélé directement dans la requête de liste, pas comme un appel Python répété par patient. Le filtre mort de `list_patients` (registre `B6`, conservé inerte depuis le chantier 5) devient :

```python
if filters.get('is_clinical'):
    query = query.filter(exists().where(MedicalRecord.patient_id == Patient.patient_id))
if filters.get('is_toxicology'):
    query = query.filter(exists().where(ToxicoDossier.patient_id == Patient.patient_id))
if filters.get('is_spiritual'):
    query = query.filter(exists().where(ConsultationSpirituel.patient_id == Patient.patient_id))
```
remplaçant les anciens `query.filter(Patient.is_clinical == True)` etc. Le filtre par rôle de `PatientController.list_patients` (aujourd'hui mort à cause du bug `B6` séparé — `role_name` inexistant sur `User`, voir ce registre) est activé en même temps, puisque c'est précisément ce qui manquait pour pouvoir l'activer sans danger.

**Pour l'affichage** (dossier patient, décision de quels onglets charger) : `compute_domain_flags()` est appelée une fois par consultation de dossier — coût négligeable à l'échelle d'un seul centre de santé (~100 patients aujourd'hui).

**Les colonnes `patients.is_clinical`/`is_toxicology`/`is_spiritual` ne sont pas supprimées** — hors périmètre (migration de schéma), et elles peuvent rester comme trace de l'intention à la création sans plus jamais être une source de vérité lue par l'application.

## Section 3 — Dossier consolidé

**Nouveau fichier** : `controller/patient_dossier_controller.py` — une responsabilité unique : composer les contrôleurs de domaine existants en une vue unifiée. Ne duplique aucune logique métier des contrôleurs existants, les appelle directement (composition de contrôleurs — motif déjà utilisé dans ce projet, `PrescriptionController` prend déjà `patient_controller` en dépendance).

```python
class PatientDossierController:
    def __init__(self, patient_ctrl, medical_ctrl, prescription_ctrl, lab_ctrl, cs_ctrl, toxico_ctrl, audit_repo, current_user):
        self.patient_ctrl = patient_ctrl
        self.medical_ctrl = medical_ctrl
        self.prescription_ctrl = prescription_ctrl
        self.lab_ctrl = lab_ctrl
        self.cs_ctrl = cs_ctrl
        self.toxico_ctrl = toxico_ctrl
        self.audit_repo = audit_repo
        self.current_user = current_user

    def get_full_dossier(self, patient_id: int) -> dict:
        patient = self.patient_ctrl.get_patient(patient_id)
        if not patient:
            raise ValueError(f"Patient {patient_id} introuvable")

        flags = self.patient_ctrl.repo.compute_domain_flags(patient_id)

        resultats = {}
        echecs = []
        for cle, appel in [
            ("resume_clinique", lambda: self.medical_ctrl.get_patient_dme_summary(patient_id)),
            ("historique_medical", lambda: self.medical_ctrl.get_patient_history(patient_id)),
            ("prescriptions", lambda: self.prescription_ctrl.get_patient_prescriptions(patient_id)),
            ("historique_labo", lambda: self.lab_ctrl.get_patient_lab_history(patient_id)),
            ("historique_spirituel", lambda: self.cs_ctrl.list_for_patient(patient_id)),
            ("dossier_toxico", lambda: self.toxico_ctrl.get_dossier_details(patient_id)),
        ]:
            try:
                resultats[cle] = appel()
            except Exception as e:
                echecs.append(cle)
                resultats[cle] = None
                logger.exception(f"Echec chargement '{cle}' pour le dossier patient {patient_id}")

        self.audit_repo.log_user_action(
            current_user=self.current_user,
            resource_type="Patient",
            resource_id=patient_id,
            action_performed="VIEW_DOSSIER_COMPLET",
            details=f"Domaines en echec: {echecs}" if echecs else None,
        )

        return {
            "patient": patient,
            "flags": flags,
            **resultats,
            "domaines_indisponibles": echecs,
        }
```

Même principe de tolérance aux pannes qu'au chantier 5 : un domaine en échec ne vide pas le dossier entier, et `domaines_indisponibles` permet au frontend d'afficher « Indisponible » plutôt qu'une absence silencieuse de données — jamais une liste vide qui ressemblerait à « ce patient n'a rien dans ce domaine ».

**Correction (vérifiée dans le code réel, corrige une hypothèse fausse de la première version de cette spec)** : le nouvel endpoint ne peut pas être ajouté à `api_backend/backend_app/routes/patients/patients_endpoints.py`. Ce routeur déclare une dépendance **au niveau du routeur** (pas de la route) : `APIRouter(prefix="/patients", tags=["Patients"], dependencies=[Depends(role_required("medecin", "nurse", "secretaire", "admin", "manager"))])`. FastAPI compose une dépendance de routeur et une dépendance de route par **ET**, jamais par remplacement — une route ajoutée dans ce même fichier avec sa propre liste de rôles se retrouverait restreinte à l'intersection des deux listes, pas à leur union. `psychologist`, `spiritualcounsellor`, `toxicomanager`, `laborantin`, `promoteur` sont absents de la liste du routeur : un compte avec l'un de ces rôles recevrait un 403 malgré une liste de rôles de route qui l'autorise explicitement. C'est le même constat qui a mené, au chantier 5, à créer un routeur neuf (`api_backend/backend_app/routes/finance/`) plutôt que d'étendre `caisse_endpoints.py`.

**Nouveau fichier** : `api_backend/backend_app/routes/patient_dossier/patient_dossier_endpoint.py` (+ `__init__.py` vide, même structure que `routes/finance/`), un routeur séparé, sans dépendance au niveau du routeur — chaque route porte sa propre liste de rôles :
```python
router = APIRouter(prefix="/patients", tags=["Dossier patient"])
```
(même préfixe `/patients` que le routeur existant — FastAPI route sur le chemin complet, deux routeurs peuvent partager un préfixe sans collision tant que les chemins exacts diffèrent ; `GET /patients/{id}/dossier` n'existe dans aucun des deux fichiers avant ce chantier)

**Nouvel endpoint** : `GET /patients/{id}/dossier`, dans ce nouveau fichier. Rôles autorisés — la politique tranchée le 2026-09-15 (soignants + admin + promoteur, secrétariat exclu) :
```python
@router.get(
    "/{patient_id}/dossier",
    dependencies=[Depends(role_required(
        "medecin", "nurse", "psychologist", "spiritualcounsellor",
        "toxicomanager", "laborantin", "assistant", "admin", "promoteur",
    ))],
)
```
(les noms canoniques exacts viennent de `api_backend/backend_app/security/role_map.py`, déjà en place pour tous sauf `promoteur`, ajouté en section 4). Ce nouveau routeur est enregistré dans `api_backend/backend_app/main.py` aux côtés des autres (`app.include_router(patient_dossier_endpoint.router)`), après `patients_endpoints.router` — l'ordre n'a pas d'incidence ici puisque les chemins exacts ne se recoupent pas.

**Frontend** — `patientDossierStore.js` : les 5 appels dispersés actuels (dont le résumé clinique, chargé **hors** du groupe tolérant, cause du 403 constaté pour un ToxicoManager) sont remplacés par un seul appel à ce nouvel endpoint. `PatientDetailView.vue` lit `domaines_indisponibles` pour décider quels onglets afficher « Indisponible » plutôt que vides, et lit `flags` (calculés, plus jamais lus depuis `patient.is_clinical` etc.) pour décider quels onglets proposer du tout. L'onglet TOXICO, aujourd'hui un encart statique jamais interrogé, devient un onglet réel consommant `dossier_toxico`.

## Section 4 — Rôle `promoteur`

**Décision (2026-09-15)** : rôle à part entière, pas une couverture par `admin` — le promoteur supervise le centre sans nécessairement administrer l'application elle-même (gestion des comptes, configuration système).

- `api_backend/backend_app/security/role_map.py` : ajout de `PROMOTEUR = "promoteur"`, entrée dans `ROLE_CANONICALS`, et dans `ROLE_ALIASES` (`{"promoteur", "promoter", "owner"}`).
- `application_roles` : une ligne `INSERT INTO application_roles (role_name) VALUES ('promoteur')` — écriture réelle en base, confirmation explicite de l'utilisateur requise avant application, comme pour toute modification de données réelles dans ce projet.
- Aucun compte n'est créé pour ce rôle dans ce chantier — juste le rôle lui-même, prêt à être assigné.

## Définition du « terminé »

- Un dossier toxico peut être créé en rattachement à un patient existant, sans dupliquer son identité — testé de bout en bout (recherche, sélection, création du dossier, vérification qu'un seul `patient_id` existe).
- Les drapeaux de domaine reflètent la réalité des dossiers existants, vérifiés par un test qui crée un dossier dans un domaine et confirme que le drapeau correspondant devient vrai sans aucune écriture manuelle du drapeau.
- Le filtre par rôle de la liste patients (`B6`) est actif et testé (un compte secrétaire ne voit plus les patients strictement cliniques, un compte médecin ne voit plus les patients strictement spirituels).
- `GET /patients/{id}/dossier` renvoie les 6 domaines en un appel, tolère l'échec d'un domaine sans vider les autres, journalise chaque consultation dans `audit_user_actions`, et refuse l'accès à un compte secrétaire (403).
- Le rôle `promoteur` existe en base et est reconnu par `role_required(...)`.
- Aucun écran existant (dossiers médicaux, prescriptions, consultations, toxico pris isolément) n'est modifié dans son contrôle d'accès.
- Suite de tests existante non régressée ; nouveaux tests pour chaque point ci-dessus.
