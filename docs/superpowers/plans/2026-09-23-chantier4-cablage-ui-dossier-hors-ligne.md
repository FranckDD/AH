# Chantier 4, sous-projet 2 (suite) — Câblage UI du dossier patient sur PowerSync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Faire réellement consommer par l'écran dossier patient (lecture ET écriture consultation/prescription) l'infrastructure PowerSync déjà construite (backend uuid, règles de sync, `DossierConnector.js`), pour `medecin`/`nurse` uniquement.

**Architecture:** Écriture toujours locale pour ces 2 rôles (en ligne comme hors ligne, `db.execute()`, même pattern que `appointmentStore.js`). Lecture HTTP par défaut, secours local en lecture seule uniquement sur échec réseau réel (pas de `db.watch()` continu pour ce document — périmètre volontairement réduit, décision utilisateur).

**Tech Stack:** Vue 3 / Pinia, `@powersync/web` (`db.execute`, `db.getAll`).

**Spec:** `docs/superpowers/specs/2026-09-23-chantier4-cablage-ui-dossier-hors-ligne-design.md`

## Global Constraints

- Rôles concernés : `medecin`, `nurse` uniquement (`authStore.hasRole(['medecin', 'nurse'])`, `ah2-admin-web/src/stores/auth.js:41-46`, déjà en place).
- Tous les autres rôles gardent leur chemin HTTP actuel strictement inchangé — brancher explicitement sur `authStore.hasRole(...)`, jamais un changement de comportement par défaut.
- Le secours de lecture hors ligne ne doit **jamais** recalculer `last_bp`/`last_weight`/`last_temp`/`last_diagnosis`/`last_consultation_date` (décision utilisateur explicite) — ces champs restent `null` en secours.
- Aucun stream/table locale ne doit jamais exposer de donnée `toxico_dossiers`/`consultation_spirituelle` — déjà garanti par les Tâches 4/5 du plan précédent, ce document ne les modifie pas.
- **Aucun commit git** — convention constante de ce projet.
- Distinguer une erreur réseau réelle d'une erreur applicative HTTP via l'absence de `err.response` sur l'exception axios (une réponse HTTP reçue, même en erreur, peuple toujours ce champ).

---

### Task 1: Lecture — secours local sur échec réseau (`patientDossierStore.js`)

**Files:**
- Modify: `ah2-admin-web/src/stores/patientDossierStore.js`

**Interfaces:**
- Consumes: tables locales PowerSync `patients`/`medical_records`/`prescriptions`/`lab_results` (déjà créées, plan précédent Tâche 5) ; `authStore.hasRole(['medecin', 'nurse'])`.
- Produces: `fetchDossierComplete(patientId)` inchangé dans sa signature, mais avec secours local pour medecin/nurse. Nouvelles fonctions `refreshMedicalHistoryLocal(patientId)` et `refreshPrescriptionHistoryLocal(patientId)`, exportées par le store — consommées par la Tâche 4 (`PatientDetailView.vue`).

- [ ] **Step 1: Importer `db` et `useAuthStore`, ajouter le secours local à `fetchDossierComplete`**

Dans `ah2-admin-web/src/stores/patientDossierStore.js`, ajouter en tête de fichier (après les imports existants) :

```javascript
import { db } from '@/powersync-client/client';
import { useAuthStore } from '@/stores/auth';
```

Remplacer le corps du `catch` de `fetchDossierComplete` (actuellement lignes 94-97) :

```javascript
        } catch (err) {
            console.error("Erreur chargement dossier:", err);
            error.value = "Impossible de charger le dossier complet.";
        } finally {
```

par :

```javascript
        } catch (err) {
            const authStore = useAuthStore();
            // err.response n'est peuple par axios que si une reponse HTTP a
            // reellement ete recue (meme en erreur 4xx/5xx) - son absence
            // signifie une vraie coupure reseau, jamais une erreur applicative
            // (404 patient inexistant, 403 perimetre medical) qu'il ne faut
            // surtout pas masquer par un faux mode degrade.
            const isNetworkFailure = !err.response;
            if (isNetworkFailure && authStore.hasRole(['medecin', 'nurse'])) {
                console.warn('Dossier hors ligne - secours sur les tables locales PowerSync:', err);
                await loadDossierFromLocalDb(patientId);
            } else {
                console.error("Erreur chargement dossier:", err);
                error.value = "Impossible de charger le dossier complet.";
            }
        } finally {
```

- [ ] **Step 2: Écrire `loadDossierFromLocalDb` (secours lecture seule)**

Ajouter cette nouvelle fonction juste avant `fetchDossierComplete` dans le même fichier :

```javascript
    // Secours hors ligne (medecin/nurse uniquement, appele seulement sur
    // echec reseau reel par fetchDossierComplete ci-dessous) - lit les
    // tables locales PowerSync deja synchronisees. Ne recalcule JAMAIS le
    // resume clinique (last_bp/last_weight/last_temp/last_diagnosis/
    // last_consultation_date restent null) - decision utilisateur
    // explicite, pour ne pas dupliquer la logique serveur.
    async function loadDossierFromLocalDb(patientId) {
        const rows = await db.getAll(
            'SELECT * FROM patients WHERE server_id = ?',
            [patientId]
        );
        const p = rows[0];

        if (p) {
            patientSummary.value = {
                patient_id: p.server_id,
                full_name: `${p.first_name || ''} ${p.last_name || ''}`.trim(),
                code: p.code_patient,
                age: calculerAge(p.birth_date),
                gender: p.gender,
                flags: {
                    is_clinical: !!p.is_clinical,
                    is_toxicology: !!p.is_toxicology,
                    is_spiritual: !!p.is_spiritual,
                },
                last_consultation_date: null,
                last_bp: null,
                last_weight: null,
                last_temp: null,
                last_diagnosis: null,
                allergies: null,
            };
        } else {
            // Patient jamais synchronise localement (jamais consulte avant
            // la coupure reseau) - rien a afficher, pas une erreur en soi.
            patientSummary.value = null;
        }

        await refreshMedicalHistoryLocal(patientId);
        await refreshPrescriptionHistoryLocal(patientId);

        labHistory.value = await db.getAll(
            'SELECT * FROM lab_results WHERE patient_id = ? ORDER BY test_date DESC',
            [patientId]
        );

        // Cloisonnement medecin/nurse (chantier perimetre medical) : ces
        // domaines ne transitent par aucun stream clinical_* - il n'y a
        // physiquement rien a lire localement, toujours restreint hors ligne.
        spiritualHistory.value = [];
        toxicoDossier.value = null;
        toxicoRestreint.value = true;
        spirituelRestreint.value = true;
        domainesIndisponibles.value = ['toxicologie', 'spirituel'];

        error.value = null;
    }
```

- [ ] **Step 3: Écrire `refreshMedicalHistoryLocal`/`refreshPrescriptionHistoryLocal`**

Ajouter ces 2 fonctions juste après `loadDossierFromLocalDb`, avant `fetchDossierComplete` :

```javascript
    // Lecture locale ponctuelle (pas un watch continu - perimetre reduit de
    // ce document) - utilisee par loadDossierFromLocalDb ci-dessus ET, pour
    // rafraichir l'affichage juste apres une ecriture locale reussie (voir
    // Taches 2/3/4), sans jamais repasser par un appel HTTP qui echouerait
    // ou lirait une valeur pas encore synchronisee au serveur.
    async function refreshMedicalHistoryLocal(patientId) {
        medicalHistory.value = await db.getAll(
            'SELECT * FROM medical_records WHERE patient_id = ? ORDER BY consultation_date DESC',
            [patientId]
        );
    }

    async function refreshPrescriptionHistoryLocal(patientId) {
        prescriptionHistory.value = await db.getAll(
            'SELECT * FROM prescriptions WHERE patient_id = ? ORDER BY start_date DESC',
            [patientId]
        );
    }
```

- [ ] **Step 4: Exposer les 2 nouvelles fonctions dans le `return` du store**

Modifier le `return { ... }` final de `patientDossierStore.js` pour ajouter `refreshMedicalHistoryLocal` et `refreshPrescriptionHistoryLocal` à la liste déjà exportée (garder tout le reste identique) :

```javascript
    return {
        patientSummary,
        medicalHistory,
        prescriptionHistory,
        labHistory,
        spiritualHistory,
        toxicoDossier,
        domainesIndisponibles,
        toxicoRestreint,
        spirituelRestreint,
        isLoading,
        error,
        fetchDossierComplete,
        refreshMedicalHistory,
        refreshMedicalHistoryLocal,
        refreshPrescriptionHistoryLocal,
        isToxicology,
        isSpiritual,
        isClinical,
        fullName,
        code,
        vitals,
        isDomaineIndisponible
    };
```

- [ ] **Step 5: Vérifier le build**

Run: `cd ah2-admin-web && npx vite build --mode production`
Expected: build réussi, aucune erreur.

---

### Task 2: Écriture — création/modification consultation (`medicalRecordStore.js`)

**Files:**
- Modify: `ah2-admin-web/src/stores/medicalRecordStore.js`

**Interfaces:**
- Consumes: table locale `medical_records` (plan précédent Tâche 5) ; `authStore.hasRole(['medecin', 'nurse'])`.
- Produces: `createMedicalRecord(data)` retourne toujours `{ record_id: <id> }` (id local `uuid` pour medecin/nurse, id serveur réel sinon) — déjà le contrat attendu par `PatientDetailView.vue:247` (Tâche 4 de ce document). `updateMedicalRecord(recordId, data)` inchangé dans sa signature.

- [ ] **Step 1: Importer `db` et `useAuthStore`**

Dans `ah2-admin-web/src/stores/medicalRecordStore.js`, ajouter après les imports existants :

```javascript
import { db } from '@/powersync-client/client';
import { useAuthStore } from '@/stores/auth';
```

- [ ] **Step 2: Brancher `createMedicalRecord` sur l'écriture locale pour medecin/nurse**

Remplacer entièrement la fonction (actuellement lignes 59-64) :

```javascript
    async function createMedicalRecord(data) {
        const res = await MedicalRecordGateway.createMedicalRecord(data);
        filters.value.page = 1;
        await fetchMedicalRecords();
        return res.data;
    }
```

par :

```javascript
    // Ecriture locale (pas d'appel REST direct) pour medecin/nurse - en
    // ligne comme hors ligne, PowerSync met l'INSERT en file et appelle
    // DossierConnector.uploadData() en arriere-plan (voir plan precedent,
    // Tache 6). crypto.randomUUID() genere le uuid client, qui devient la
    // cle primaire locale ET la colonne uuid Postgres une fois synchronise.
    // { record_id: uuid } prend la place du vrai record_id (pas encore
    // confirme par le serveur) - contrat deja attendu par
    // PatientDetailView.vue pour proposer une prescription liee juste
    // apres cette consultation.
    async function createMedicalRecord(data) {
        const authStore = useAuthStore();
        if (authStore.hasRole(['medecin', 'nurse'])) {
            const uuid = crypto.randomUUID();
            await db.execute(
                `INSERT INTO medical_records (
                    id, patient_id, consultation_date, motif_code, appointment_id,
                    marital_status, severity, bp, temperature, weight, height,
                    medical_history, allergies, symptoms, diagnosis, treatment, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
                [
                    uuid, data.patientId, data.consultationDate || null, data.motifCode, data.appointmentId || null,
                    data.maritalStatus || null, data.severity || null, data.bp || null,
                    data.temperature ?? null, data.weight ?? null, data.height ?? null,
                    data.medicalHistory || null, data.allergies || null, data.symptoms || null,
                    data.diagnosis || null, data.treatment || null, data.notes || null,
                ]
            );
            return { record_id: uuid };
        }

        const res = await MedicalRecordGateway.createMedicalRecord(data);
        filters.value.page = 1;
        await fetchMedicalRecords();
        return res.data;
    }
```

- [ ] **Step 3: Brancher `updateMedicalRecord` sur l'écriture locale pour medecin/nurse**

Remplacer entièrement la fonction (actuellement lignes 66-69) :

```javascript
    async function updateMedicalRecord(recordId, data) {
        await MedicalRecordGateway.updateMedicalRecord(recordId, data);
        await fetchMedicalRecords();
    }
```

par :

```javascript
    // recordId peut etre soit l'id local (uuid, consultation creee/editee
    // hors ligne dans cette meme session), soit le vrai server_id entier
    // (consultation deja synchronisee, ouverte depuis une liste chargee en
    // HTTP) - WHERE id = ? OR server_id = ? couvre les deux cas. String()
    // sur le premier binding : comparer un entier a la colonne "id" (TEXT)
    // ne doit jamais matcher par coincidence de type.
    async function updateMedicalRecord(recordId, data) {
        const authStore = useAuthStore();
        if (authStore.hasRole(['medecin', 'nurse'])) {
            await db.execute(
                `UPDATE medical_records SET
                    patient_id = ?, consultation_date = ?, motif_code = ?, marital_status = ?,
                    severity = ?, bp = ?, temperature = ?, weight = ?, height = ?,
                    medical_history = ?, allergies = ?, symptoms = ?, diagnosis = ?,
                    treatment = ?, notes = ?
                 WHERE id = ? OR server_id = ?`,
                [
                    data.patientId, data.consultationDate || null, data.motifCode, data.maritalStatus || null,
                    data.severity || null, data.bp || null, data.temperature ?? null, data.weight ?? null,
                    data.height ?? null, data.medicalHistory || null, data.allergies || null,
                    data.symptoms || null, data.diagnosis || null, data.treatment || null, data.notes || null,
                    String(recordId), recordId,
                ]
            );
            return;
        }

        await MedicalRecordGateway.updateMedicalRecord(recordId, data);
        await fetchMedicalRecords();
    }
```

- [ ] **Step 4: Vérifier le build**

Run: `cd ah2-admin-web && npx vite build --mode production`
Expected: build réussi.

---

### Task 3: Écriture — création prescription (`prescriptionStore.js` + `PrescriptionModal.vue`)

**Lacune trouvée en préparant cette tâche, corrigée au passage** : le plan précédent
(`docs/superpowers/plans/2026-09-23-chantier4-dossier-patient-hors-ligne.md`, déjà clos) n'a
jamais donné de colonne `lab_exams_list` à la table locale `prescriptions` (`AppSchema.js`), et
`DossierConnector.js` ne la transmet pas au gateway — une prescription "demande d'examen" créée
hors ligne perdrait silencieusement sa liste d'examens (même défaut de fond que le registre N1
déjà corrigé côté lecture). Cette tâche referme aussi ce point, puisqu'elle est précisément
celle qui rend `createPrescription` réellement fonctionnel hors ligne.

**Files:**
- Modify: `ah2-admin-web/src/stores/prescriptionStore.js`
- Modify: `ah2-admin-web/src/components/prescriptions/PrescriptionModal.vue:182-185`
- Modify: `ah2-admin-web/src/powersync-client/AppSchema.js`
- Modify: `ah2-admin-web/src/powersync-client/DossierConnector.js`

**Interfaces:**
- Consumes: table locale `prescriptions` (plan précédent Tâche 5) ; `authStore.hasRole(['medecin', 'nurse'])` ; `{ record_id: uuid }` de la Tâche 2 (uuid local en tant que `medicalRecordId` prefilled).
- Produces: `createPrescription(data)` inchangé dans sa signature. Nouvelle colonne locale `prescriptions.lab_exams_list` (texte JSON).

- [ ] **Step 1: Ajouter `lab_exams_list` à la table locale `prescriptions`**

Dans `ah2-admin-web/src/powersync-client/AppSchema.js`, dans la définition de `prescriptions`
(plan précédent Tâche 5), ajouter la colonne `lab_exams_list: column.text,` juste après
`is_lab_order: column.integer,` :

```javascript
const prescriptions = new Table(
  {
    server_id: column.integer,
    patient_id: column.integer,
    medical_record_id: column.integer,
    medication: column.text,
    dosage: column.text,
    frequency: column.text,
    duration: column.text,
    start_date: column.text,
    end_date: column.text,
    notes: column.text,
    status: column.text,
    prescribed_by: column.integer,
    prescribed_by_name: column.text,
    is_lab_order: column.integer,
    lab_exams_list: column.text,
  },
  { indexes: { by_patient: ['patient_id'], by_medical_record: ['medical_record_id'] } }
);
```

Rien d'autre dans ce fichier ne change (les 3 autres tables, `appointments`/`patients_lookup`/
`doctors_lookup`/`patients`/`medical_records`/`lab_results`, restent identiques).

- [ ] **Step 2: Forwarder `lab_exams_list` dans `DossierConnector.js`**

Dans `ah2-admin-web/src/powersync-client/DossierConnector.js`, case `'prescriptions:PUT'` (déjà
créé au plan précédent Tâche 6), ajouter `labExamsList` à l'appel
`PrescriptionGateway.createPrescription({...})` déjà présent :

```javascript
            await PrescriptionGateway.createPrescription({
              patientId: op.opData.patient_id,
              medicalRecordId: medicalRecordServerId,
              isLabOrder: !!op.opData.is_lab_order,
              medication: op.opData.medication,
              dosage: op.opData.dosage,
              frequency: op.opData.frequency,
              duration: op.opData.duration,
              startDate: op.opData.start_date,
              endDate: op.opData.end_date,
              notes: op.opData.notes,
              labExamsList: op.opData.lab_exams_list ? JSON.parse(op.opData.lab_exams_list) : [],
              uuid: op.id,
            });
```

(Seule la ligne `labExamsList: ...` est ajoutée — le reste de l'objet et tout le reste du
fichier restent identiques au plan précédent.)

- [ ] **Step 3: Élargir le type de la prop `prefilledMedicalRecordId`**

Dans `ah2-admin-web/src/components/prescriptions/PrescriptionModal.vue`, lignes 182-185, remplacer :

```javascript
  prefilledMedicalRecordId: {
    type: Number,
    default: null,
  },
```

par :

```javascript
  // [Number, String] : un id local (uuid, cree hors ligne par
  // medicalRecordStore.createMedicalRecord - voir Tache 2) est une chaine,
  // pas un entier. Number seul produirait un avertissement Vue console a
  // chaque enchainement consultation->prescription pour medecin/nurse.
  prefilledMedicalRecordId: {
    type: [Number, String],
    default: null,
  },
```

- [ ] **Step 4: Importer `db` et `useAuthStore` dans `prescriptionStore.js`**

Ajouter après les imports existants :

```javascript
import { db } from '@/powersync-client/client';
import { useAuthStore } from '@/stores/auth';
```

- [ ] **Step 5: Brancher `createPrescription` sur l'écriture locale pour medecin/nurse**

Remplacer entièrement la fonction (actuellement lignes 63-67) :

```javascript
    async function createPrescription(data) {
        await PrescriptionGateway.createPrescription(data);
        filters.value.page = 1;
        await fetchPrescriptions();
    }
```

par :

```javascript
    // Ecriture locale pour medecin/nurse, meme motif que
    // medicalRecordStore.createMedicalRecord (Tache 2). data.medicalRecordId
    // peut etre l'id local (uuid) d'une consultation creee dans le meme
    // geste hors ligne - stocke tel quel dans la colonne medical_record_id
    // (declaree column.integer mais SQLite est faiblement type, accepte le
    // texte sans erreur - deja le comportement anticipe par
    // DossierConnector.js, qui resout le vrai server_id au moment de
    // l'upload). lab_exams_list serialise en JSON texte, aucune colonne
    // array/JSON native cote PowerSync.
    async function createPrescription(data) {
        const authStore = useAuthStore();
        if (authStore.hasRole(['medecin', 'nurse'])) {
            const uuid = crypto.randomUUID();
            await db.execute(
                `INSERT INTO prescriptions (
                    id, patient_id, medical_record_id, medication, dosage, frequency,
                    duration, start_date, end_date, notes, is_lab_order, lab_exams_list
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
                [
                    uuid, data.patientId, data.medicalRecordId || null, data.medication || null,
                    data.dosage || null, data.frequency || null, data.duration || null,
                    data.startDate || null, data.endDate || null, data.notes || null,
                    data.isLabOrder ? 1 : 0, JSON.stringify(data.labExamsList || []),
                ]
            );
            return;
        }

        await PrescriptionGateway.createPrescription(data);
        filters.value.page = 1;
        await fetchPrescriptions();
    }
```

- [ ] **Step 6: Vérifier le build**

Run: `cd ah2-admin-web && npx vite build --mode production`
Expected: build réussi.

---

### Task 4: `PatientDetailView.vue` — rafraîchissement local après écriture

**Files:**
- Modify: `ah2-admin-web/src/views/modules/patients/PatientDetailView.vue:232-256,267-276`

**Interfaces:**
- Consumes: `dossierStore.refreshMedicalHistoryLocal`/`refreshPrescriptionHistoryLocal` (Tâche 1), `medicalRecordStore.createMedicalRecord` (Tâche 2, `{ record_id }` déjà uuid-compatible), `prescriptionStore.createPrescription` (Tâche 3).
- Produces: rien de nouveau consommé ailleurs — dernière tâche du plan.

- [ ] **Step 1: Éviter le refresh HTTP après une écriture locale dans `handleConsultationSave`**

Remplacer entièrement la fonction (actuellement lignes 232-256) :

```javascript
async function handleConsultationSave(data) {
    try {
        const record = await medicalRecordStore.createMedicalRecord(data);
        await dossierStore.refreshMedicalHistory(route.params.id);

        if (data.appointmentId) {
            try {
                await appointmentStore.completeAppointment(data.appointmentId);
            } catch (err) {
                console.error('Erreur complétion RDV:', err);
                alert(t('medical.consultation_flow.appointment_complete_failed'));
            }
        }

        closeConsultationModal();
        if (record && record.record_id) {
            prescriptionOffer.value = { visible: true, medicalRecordId: record.record_id };
        } else {
            console.warn('Dossier medical cree mais record_id indisponible (reponse de secours du backend) - proposition de prescription liee non affichee.');
        }
    } catch (err) {
        console.error('Erreur enregistrement dossier medical:', err);
        alert('Erreur lors de l\'enregistrement : ' + (err.response?.data?.detail || err.message));
    }
}
```

par :

```javascript
async function handleConsultationSave(data) {
    try {
        const record = await medicalRecordStore.createMedicalRecord(data);

        // medecin/nurse : l'ecriture ci-dessus est locale (Tache 2), un
        // refresh HTTP juste apres lirait avant que DossierConnector.js
        // n'ait eu le temps d'uploader vers le serveur (course) - on relit
        // directement la meme table locale qui vient d'etre ecrite.
        // Autres roles : comportement HTTP inchange.
        if (authStore.hasRole(['medecin', 'nurse'])) {
            await dossierStore.refreshMedicalHistoryLocal(route.params.id);
        } else {
            await dossierStore.refreshMedicalHistory(route.params.id);
        }

        if (data.appointmentId) {
            try {
                await appointmentStore.completeAppointment(data.appointmentId);
            } catch (err) {
                console.error('Erreur complétion RDV:', err);
                alert(t('medical.consultation_flow.appointment_complete_failed'));
            }
        }

        closeConsultationModal();
        if (record && record.record_id) {
            prescriptionOffer.value = { visible: true, medicalRecordId: record.record_id };
        } else {
            console.warn('Dossier medical cree mais record_id indisponible (reponse de secours du backend) - proposition de prescription liee non affichee.');
        }
    } catch (err) {
        console.error('Erreur enregistrement dossier medical:', err);
        alert('Erreur lors de l\'enregistrement : ' + (err.response?.data?.detail || err.message));
    }
}
```

- [ ] **Step 2: Rafraîchir localement après une prescription pour medecin/nurse**

Remplacer entièrement `handlePrescriptionSave` (actuellement lignes 267-276) :

```javascript
async function handlePrescriptionSave(data) {
    try {
        await prescriptionStore.createPrescription(data);
        showPrescriptionModal.value = false;
        prescriptionOffer.value = { visible: false, medicalRecordId: null };
    } catch (err) {
        console.error('Erreur enregistrement prescription:', err);
        alert('Erreur lors de l\'enregistrement : ' + (err.response?.data?.detail || err.message));
    }
}
```

par :

```javascript
async function handlePrescriptionSave(data) {
    try {
        await prescriptionStore.createPrescription(data);

        if (authStore.hasRole(['medecin', 'nurse'])) {
            await dossierStore.refreshPrescriptionHistoryLocal(route.params.id);
        }

        showPrescriptionModal.value = false;
        prescriptionOffer.value = { visible: false, medicalRecordId: null };
    } catch (err) {
        console.error('Erreur enregistrement prescription:', err);
        alert('Erreur lors de l\'enregistrement : ' + (err.response?.data?.detail || err.message));
    }
}
```

- [ ] **Step 3: Vérifier le build**

Run: `cd ah2-admin-web && npx vite build --mode production`
Expected: build réussi, aucune référence cassée (`authStore` déjà importé et instancié ligne 200, aucun nouvel import nécessaire dans ce fichier).

---

### Task 5: Vérification finale (hors tâches, à la charge du contrôleur)

Aucun outil de navigateur disponible dans cet environnement agentique.

- [ ] Build frontend complet (`cd ah2-admin-web && npx vite build --mode production`).
- [ ] Suite backend complète (`python -m pytest tests/ -q`) — aucun fichier backend n'est touché par ce document, confirmer simplement l'absence de régression accidentelle.
- [ ] Demander à l'utilisateur de rejouer le protocole de test avec une **vraie coupure réseau** (débrancher/couper le Wi-Fi, pas seulement le toggle DevTools — leçon tirée du registre N ci-dessus, où l'ambiguïté sur ce qui avait été réellement testé a coûté un cycle d'investigation) : ouvrir un dossier patient déjà consulté en ligne au préalable (pour qu'il soit synchronisé localement) → couper le réseau → recharger la page/rouvrir le dossier (doit afficher les données déjà synchronisées, résumé clinique vide) → créer une consultation + accepter la proposition de prescription liée → reconnecter → vérifier côté serveur (re-ouvrir le dossier en ligne) que la consultation ET la prescription apparaissent avec leurs vrais `record_id`/`prescription_id`, et que `medical_record_id` de la prescription pointe bien vers la bonne consultation.
