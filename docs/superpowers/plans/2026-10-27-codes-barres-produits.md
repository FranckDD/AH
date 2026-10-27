# Codes-barres produits, zone photo et fenetre agrandissable - Plan d'implementation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ajouter, sans rien enlever, un code-barres unique par produit (scan dans New invoice), une zone photo du produit, un bouton agrandir/restaurer sur la fenetre New invoice et l'impression d'etiquettes.

**Architecture:** Le code est genere par la base (sequence + valeur par defaut), donc tout chemin de creation d'un produit (stock, fabrication) en recoit un. Le serveur expose une recherche par code et la gestion d'une photo reduite. Hors ligne, le scan lit la table locale `pharmacy_stock` (flux PowerSync enrichi). Cote web, un champ de scan dans New invoice, un panneau produit, un bouton `maximizable` additif sur `FullScreenPanel`, et un ecran d'impression d'etiquettes depuis la liste des produits.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, PostgreSQL, PowerSync, Vue 3, vue-i18n, JsBarcode (Code 128, version exacte et ancienne d'au moins 2 semaines), Pillow (si deja present, sinon a ajouter).

**Spec:** `docs/superpowers/specs/2026-10-27-codes-barres-produits-design.md` (approuvee 2026-10-27).

## Global Constraints

- On ajoute des options : la recherche par nom, le prix verrouille, la quantite, les avertissements de stock, le circuit de reduction restent inchanges.
- Roles verifies cote serveur ; table des routes comparee dans les tests de roles. Gestion (photo, code visible, etiquettes) : roles `admin`, `Assistant`, `ToxicoManager` (garde des ecritures de `/pharmacy`). Lecture et scan : tous les roles du routeur `/pharmacy` (dont `secretaire`).
- UI : jetons seulement, textes >= 13 px, cibles >= 44 px, FR/EN a cles identiques, ponctuation ASCII (ni tiret long, ni fleche, ni point median), dates jj/mm/aaaa, `authStore.hasRole()`.
- Code-barres : 8 chiffres, premier chiffre 1, jamais reutilise, jamais modifie, jamais accepte dans un PUT/POST.
- Migration Alembic : id `033_product_barcodes` (<= 32 caracteres), `down_revision = '032_psy_scope_transfers'` ; appliquee a la base de developpement ; miroir dans `ci/schema_only.sql`.
- PowerSync : toute colonne lue hors ligne passe par `powersync/sync-config.yaml` (alias `FROM pharmacy AS pharmacy_stock` obligatoire) et `AppSchema.js` ; le conteneur PowerSync doit etre recharge.
- Photo : fichier sur disque du serveur (`storage/product_photos`, nom UUID), lecture authentifiee, jamais de fichier public.
- Le scan ne contourne aucune regle : stock, prix verrouille et reduction restent ceux de la saisie manuelle.

## Review Focus

- Deux produits de meme nom recoivent deux codes differents ; un produit cree par la fabrication a aussi un code (valeur par defaut de la base, pas du code Python).
- Le code ne change jamais : un PUT qui contient `barcode` ne le modifie pas.
- Un code inconnu, vide, avec espaces ou lettres : message clair, aucune ligne ajoutee, le champ de scan reste pret.
- Scans rapides repetes du meme produit : quantite 2, 3, ... sur la premiere ligne Pharmacie de ce produit, y compris si la quantite a ete tapee a la main ; produit en rupture : ligne ajoutee et avertissement de stock habituel.
- Hors ligne (secretaire) : scan d'un code synchronise marche ; code pas encore synchronise donne « code inconnu » ; autre role hors ligne voit l'erreur reseau (garde de role comme `searchProducts`).
- Photo : fichier non image ou trop lourd refuse ; lecture sans connexion refusee (401) ; remplacement change la version, donc le cache.
- Le bouton agrandir ne casse ni la touche Echap, ni la boucle de focus, ni l'affichage sur telephone.

---

### Task 1: Code-barres en base et recherche par code (serveur)

**Files:**
- Create: `alembic/versions/033_product_barcodes.py`
- Modify: `models/pharmacy.py`, `api_backend/backend_app/routes/pharmacy/pharmacy_schemas.py` (reponse), `api_backend/backend_app/routes/pharmacy/mapping.py`, `repositories/pharmacy_repo.py`, `controller/pharmacy_controller.py`, `api_backend/backend_app/routes/pharmacy/pharmacy_endpoints.py`, `ci/schema_only.sql`
- Test: `tests/test_pharmacy_barcode.py`, `tests/test_pharmacy_write_guards.py` (cas du PUT avec `barcode`)

**Interfaces:**
- Produces: colonne `pharmacy.barcode VARCHAR(12) NOT NULL UNIQUE DEFAULT nextval('pharmacy_barcode_seq')::text` (sequence demarrant a 10000000) ; champ `barcode: str` dans `PharmacyResponse` et `normalize_pharmacy_data` ; `PharmacyRepository.get_by_barcode(code: str) -> Pharmacy | None` ; `GET /pharmacy/by-barcode/{code}` -> meme corps que `GET /pharmacy/{id}` (404 si inconnu), **declare avant** `GET /{medication_id}`.
- Consumes: rien.

- [ ] **Step 1: Tests (echouent d'abord)** dans `tests/test_pharmacy_barcode.py` : `test_new_products_get_distinct_barcodes` (deux produits de meme nom, codes differents, 8 chiffres commencant par 1), `test_product_created_outside_pharmacy_repo_gets_barcode` (insertion directe via le modele, comme la fabrication), `test_by_barcode_returns_product_and_404_for_unknown`, `test_by_barcode_allowed_for_secretaire_and_denied_for_other_roles`, `test_put_cannot_change_barcode`, `test_post_ignores_barcode_in_payload`.
- [ ] **Step 2: Migration** `033_product_barcodes` : creer la sequence, ajouter la colonne avec la valeur par defaut volatile (remplit chaque produit existant), puis contrainte d'unicite ; `downgrade` la retire. La migration doit etre rejouable sans doublon. L'appliquer a la base de developpement ; mettre a jour `ci/schema_only.sql`.
- [ ] **Step 3: Implementer** la colonne dans `Pharmacy` (valeur par defaut serveur, relecture apres insertion), `get_by_barcode`, le champ de reponse, l'endpoint. `PharmacyCreate`/`PharmacyUpdate` n'acceptent pas `barcode`.
- [ ] **Step 4: Lancer** `pytest tests/test_pharmacy_barcode.py tests/test_pharmacy_write_guards.py tests/test_pharmacy_qty_guard.py` (un seul pytest a la fois, `REDIS_URL=redis://localhost:6379/0`) : tout passe.
- [ ] **Step 5: Commit** (le controleur ne committe pas ; l'implementeur non plus, voir ledger).

### Task 2: Photo du produit et reglage de taille d'etiquette (serveur)

**Files:**
- Modify: `alembic/versions/033_product_barcodes.py` (colonnes ajoutees a la meme migration), `models/pharmacy.py`, `models/organization_config.py`, `repositories/pharmacy_repo.py`, `controller/pharmacy_controller.py`, `pharmacy_endpoints.py`, `pharmacy_schemas.py`, `mapping.py`, le routeur de configuration de structure (celui qui sert `GET /config/structure`), `ci/schema_only.sql`
- Test: `tests/test_pharmacy_photo.py`, `tests/test_label_settings.py`

**Interfaces:**
- Produces: colonnes `pharmacy.photo_path VARCHAR NULL`, `pharmacy.photo_version INTEGER NOT NULL DEFAULT 0`, `organization_config.label_width_mm` / `label_height_mm` (defauts 50 et 30) ; champs `has_photo: bool` et `photo_version: int` dans la reponse produit ; `PUT /pharmacy/{id}/photo` (multipart, roles de gestion) ; `DELETE /pharmacy/{id}/photo` (roles de gestion) ; `GET /pharmacy/{id}/photo` (tous les roles du routeur, 404 si pas de photo, `Cache-Control: private`) ; largeur et hauteur d'etiquette lisibles par les roles de gestion et modifiables par l'admin seulement.
- Consumes: Task 1 (migration, reponse produit).

- [ ] **Step 1: Tests** : `test_upload_resizes_to_small_jpeg` (image large reduite, taille <= 100 Ko, version +1), `test_upload_rejects_non_image_and_oversize`, `test_photo_requires_login`, `test_photo_roles` (secretaire lit, ne peut ni envoyer ni supprimer), `test_replace_bumps_version_and_removes_old_file`, `test_delete_photo`, `test_label_size_defaults_and_admin_only_write`, `test_label_size_rejects_out_of_range` (bornes 20 a 120 mm).
- [ ] **Step 2: Implementer** : redimensionnement (cote le plus long 480 px, JPEG), stockage `storage/product_photos/<uuid>.jpg`, suppression de l'ancien fichier au remplacement, suivre le motif de `GET /toxico/dossiers/{id}/consent` pour la lecture authentifiee. Ajouter les colonnes a la migration 033 (non encore commitee) et a `schema_only.sql`.
- [ ] **Step 3: Lancer** les deux fichiers de tests ci-dessus : tout passe.
- [ ] **Step 4: Verifier** la table des roles : ajouter les nouvelles routes aux tests de roles existants (`tests/` ou ils comparent la table des routes).

### Task 3: Synchronisation hors ligne et passerelle web (produit par code, photo)

**Files:**
- Modify: `powersync/sync-config.yaml` (flux `secretariat_pharmacy_stock`), `ah2-admin-web/src/powersync-client/AppSchema.js` (`pharmacy_stock`), `ah2-admin-web/src/services/CaisseGateway.js`
- Create: `ah2-admin-web/src/services/ProductPhotoGateway.js`
- Test: `ah2-admin-web/tests/productBarcodeGateway.test.mjs`

**Interfaces:**
- Produces: colonnes locales `barcode`, `forme`, `dosage_mg` (text), `has_photo` (integer), `photo_version` dans `pharmacy_stock` ; `CaisseGateway.findProductByBarcode(code: string) -> Promise<{ data: Product | null }>` (en ligne : `GET /pharmacy/by-barcode/{code}`, 404 -> `{ data: null }` ; hors ligne secretaire : lecture de `pharmacy_stock WHERE barcode = ?`, meme forme que la reponse de `searchProducts` plus `forme`, `dosage_mg`, `barcode`, `has_photo`, `photo_version` ; autre role hors ligne : l'erreur reseau est propagee) ; `ProductPhotoGateway.getPhotoUrl(medicationId: number, version: number) -> Promise<string | null>` (recupere l'image authentifiee, la garde en cache navigateur par couple id et version, renvoie une URL d'objet ou `null`) ; `uploadPhoto(id, file)` et `deletePhoto(id)`.
- Consumes: Tasks 1 et 2 (endpoints, colonnes).

- [ ] **Step 1: Test** `productBarcodeGateway.test.mjs` : 404 devient `{ data: null }` ; hors ligne secretaire lit la table locale ; hors ligne admin propage l'erreur ; la forme de retour hors ligne contient les memes cles que celle du serveur utilisees par la modale.
- [ ] **Step 2: Implementer** le flux (SELECT enrichi, alias conserve), le schema local, les deux passerelles. Recharger le conteneur PowerSync et verifier que la secretaire voit les nouvelles colonnes.
- [ ] **Step 3: Lancer** `cd ah2-admin-web && node --test tests/productBarcodeGateway.test.mjs tests/productApiMapping.test.mjs` : tout passe.

### Task 4: New invoice - scan, panneau produit, agrandir/restaurer

**Files:**
- Create: `ah2-admin-web/src/utils/barcodeScan.js`, `ah2-admin-web/src/components/caisse/InvoiceProductPanel.vue`
- Modify: `ah2-admin-web/src/components/caisse/CaisseInvoiceModal.vue`, `ah2-admin-web/src/components/ui/FullScreenPanel.vue`, `ah2-admin-web/src/i18n.js` (FR et EN)
- Test: `ah2-admin-web/tests/barcodeScan.test.mjs`, `ah2-admin-web/tests/caisseInvoiceScanContract.test.mjs`, `ah2-admin-web/tests/uiComponents.test.mjs` (cas `maximizable`)

**Interfaces:**
- Produces: `normalizeScan(raw: string) -> string | null` (retire espaces et fins de ligne, renvoie `null` si ce n'est pas 1 a 12 chiffres) ; `applyScanToLines(lines: Line[], product: Product) -> { line: Line, created: boolean }` (pure : si une ligne Pharmacie a deja ce `refId`, `quantity += 1` sur la premiere ; sinon cree la ligne remplie comme `selectProductLine`) ; prop `maximizable: Boolean` (defaut `false`) sur `FullScreenPanel` avec bouton agrandir/restaurer (aria-pressed, libelles i18n) ; composant `InvoiceProductPanel` (props `product: Product | null`, affiche photo via `ProductPhotoGateway`, nom, forme, dosage, prix ; image neutre sans photo).
- Consumes: Task 3 (gateways).

- [ ] **Step 1: Tests purs** `barcodeScan.test.mjs` : `normalizeScan('10000001\n') === '10000001'`, `' 1000 0001 '` -> `null`, `'abc'` -> `null`, `''` -> `null` ; `applyScanToLines` : premier scan cree une ligne a quantite 1 ; deuxieme scan du meme produit -> meme ligne, quantite 2 ; quantite tapee a 5 puis scan -> 6 ; produit different -> nouvelle ligne.
- [ ] **Step 2: Test de contrat** `caisseInvoiceScanContract.test.mjs` (motif des autres `*Contract.test.mjs`) : le modal contient un champ de scan, appelle `findProductByBarcode`, affiche un message d'erreur FR/EN pour un code inconnu, passe `maximizable` a `FullScreenPanel`, et les cles i18n FR/EN sont identiques.
- [ ] **Step 3: Implementer** : champ de scan visible en tete de la section des lignes, pret a l'ouverture et refocalise apres chaque scan, ajout ou suppression de ligne ; Entree valide ; code inconnu -> message, rien ajoute. Le panneau produit se met a jour au scan, a la selection par nom et au clic sur une ligne. `FullScreenPanel` : bouton additif, taille actuelle <-> plein ecran, Echap et boucle de focus inchanges, rien ne change si `maximizable` est faux.
- [ ] **Step 4: Lancer** `cd ah2-admin-web && node --test tests/barcodeScan.test.mjs tests/caisseInvoiceScanContract.test.mjs tests/uiComponents.test.mjs tests/caisseInvoiceContract.test.mjs tests/catalogPriceLockContract.test.mjs` : tout passe. Construire (`VITE_API_URL=http://127.0.0.1:8000 NODE_OPTIONS=--max-old-space-size=2048 npx vite build`).
- [ ] **Step 5: Verification navigateur** (fenetre New invoice, deux produits, un avec photo, un sans) : scan, double scan, code inconnu, agrandir/restaurer, hors ligne.

### Task 5: Fiche produit - photo, code, impression des etiquettes

**Files:**
- Create: `ah2-admin-web/src/utils/labelLayout.js`, `ah2-admin-web/src/components/stock/LabelPrintModal.vue`
- Modify: `ah2-admin-web/package.json` (JsBarcode, version exacte), `ah2-admin-web/src/components/stock/ProductModal.vue`, `ah2-admin-web/src/views/modules/stock/StockList.vue`, `ah2-admin-web/src/stores/stockStore.js` (champs `barcode`, `hasPhoto`, `photoVersion`), `ah2-admin-web/src/utils/productApi.js` si necessaire, `ah2-admin-web/src/i18n.js`
- Test: `ah2-admin-web/tests/labelLayout.test.mjs`, `ah2-admin-web/tests/stockLabelsContract.test.mjs`, `ah2-admin-web/tests/productApiMapping.test.mjs`

**Interfaces:**
- Produces: `buildLabelPages(items: { name: string, barcode: string, copies: number }[], size: { widthMm: number, heightMm: number }, mode: 'roll' | 'a4') -> Page[]` (pure : mode `roll` = une page par etiquette a la taille donnee ; mode `a4` = grille avec traits de decoupe, au moins une ligne et une colonne, jamais de depassement de page) ; `LabelPrintModal` (choix des produits, nombre d'etiquettes, mode rouleau/A4, impression par la boite du navigateur avec une regle de page a la taille de l'etiquette) ; section photo de `ProductModal` (envoyer, remplacer, supprimer, apercu) et affichage du code en lecture seule ; champ de taille d'etiquette (admin) dans l'ecran de configuration de structure.
- Consumes: Tasks 1 a 3.

- [ ] **Step 1: Tests purs** `labelLayout.test.mjs` : 3 produits x 2 copies en mode `roll` donnent 6 pages de la taille demandee ; mode `a4` : 100 etiquettes se repartissent sur plusieurs pages sans depassement ; nombre de copies <= 0 ou non entier est rejete ; nom trop long est tronque sans casser la mise en page.
- [ ] **Step 2: Test de contrat** `stockLabelsContract.test.mjs` : boutons visibles seulement pour les roles de gestion (`admin`, `Assistant`, `ToxicoManager`) et jamais pour la secretaire ; `ProductModal` ne permet pas d'editer le code ; cles i18n FR/EN identiques.
- [ ] **Step 3: Implementer** puis `cd ah2-admin-web && node --test tests/labelLayout.test.mjs tests/stockLabelsContract.test.mjs tests/productApiMapping.test.mjs tests/uiComponents.test.mjs` : tout passe ; reconstruire.
- [ ] **Step 4: Verification navigateur** : ajouter une photo, la remplacer, imprimer 3 etiquettes (apercu d'impression), puis scanner (ou saisir) le code imprime dans New invoice.

### Task 6: Documentation, guides et cloture

**Files:**
- Modify: `docs/superpowers/SUIVI-AVANCEMENT.md`, guides `docs/user-guides/src/secretary-*` (facture, scan, zone photo, agrandir) et le guide de stock concerne, `docs/superpowers/DEFAUTS-RELEVES-PAR-LES-GUIDES.md` si utile
- Test: `python docs/user-guides/tools/check_style.py` sur les guides modifies

- [ ] **Step 1:** mettre a jour le suivi (nouvelle section datee), les guides touches (texte et figures reprises avec `retake_lib.py`), regenerer seulement les PDF concernes.
- [ ] **Step 2:** lancer la suite backend complete (un seul pytest) et les tests node ; seuls les 6 echecs connus lies aux donnees de demonstration sont acceptes.
- [ ] **Step 3:** revue finale de la branche (modele le plus capable), puis attendre la demande de commit de l'utilisateur.
