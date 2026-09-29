import { column, Schema, Table } from '@powersync/web';

// La cle primaire "id" de chaque table est implicite (texte, geree par
// PowerSync) et DOIT contenir la valeur de la colonne "uuid" Postgres,
// jamais l'entier "id" de Postgres - voir sync-config.yaml (deja en place)
// qui fait deja cet aliasing cote serveur (SELECT uuid::text AS id, ...).
// "server_id" ci-dessous est l'entier Postgres, disponible seulement une
// fois la ligne confirmee par le serveur (null pour une creation encore
// hors ligne, jamais uploadee).

const appointments = new Table(
  {
    server_id: column.integer,
    patient_id: column.integer,
    doctor_id: column.integer,
    specialty: column.text,
    appointment_date: column.text,
    appointment_time: column.text,
    reason: column.text,
    status: column.text,
    created_at: column.text,
    updated_at: column.text,
  },
  { indexes: { by_doctor: ['doctor_id'], by_date: ['appointment_date'] } }
);

const patients_lookup = new Table({
  patient_id: column.integer,
  code_patient: column.text,
  first_name: column.text,
  last_name: column.text,
  contact_phone: column.text,
});

const doctors_lookup = new Table({
  user_id: column.integer,
  username: column.text,
  full_name: column.text,
});

// Table de lecture complete du dossier patient (medecin/nurse) - distincte
// de patients_lookup (utilisee par le pilote RDV, colonnes minimales pour
// n'afficher qu'un nom sur un RDV). is_toxicology/is_spiritual sont de
// simples booleens d'existence (deja affiches cote dossier consolide,
// chantier perimetre medical "flags") - jamais les donnees toxico/
// spirituelles elles-memes, qui ne transitent par aucun stream de ce plan.
const patients = new Table({
  server_id: column.integer,
  code_patient: column.text,
  first_name: column.text,
  last_name: column.text,
  birth_date: column.text,
  gender: column.text,
  contact_phone: column.text,
  is_clinical: column.integer,
  is_toxicology: column.integer,
  is_spiritual: column.integer,
  // Champs du formulaire de creation (patient cree hors ligne, chantier 4
  // sous-projet 4) - jamais descendus par clinical_patients, remplis
  // uniquement par une ecriture locale et relus par le connecteur.
  residence: column.text,
  national_id: column.text,
  assurance: column.text,
  father_name: column.text,
  mother_name: column.text,
});

const medical_records = new Table(
  {
    server_id: column.integer,
    patient_id: column.integer,
    consultation_date: column.text,
    marital_status: column.text,
    bp: column.text,
    temperature: column.real,
    weight: column.real,
    height: column.real,
    medical_history: column.text,
    allergies: column.text,
    symptoms: column.text,
    diagnosis: column.text,
    treatment: column.text,
    severity: column.text,
    notes: column.text,
    motif_code: column.text,
    appointment_id: column.integer,
    created_by: column.integer,
    created_by_name: column.text,
    // uuid du patient quand celui-ci a ete cree hors ligne (pas encore de
    // server_id) - resolu cote serveur (POST /medical_records patient_uuid).
    patient_uuid: column.text,
    needs_doctor_review: column.integer,
    assigned_doctor_id: column.integer,
  },
  { indexes: { by_patient: ['patient_id'], by_patient_uuid: ['patient_uuid'] } }
);

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
    patient_uuid: column.text,
  },
  { indexes: { by_patient: ['patient_id'], by_medical_record: ['medical_record_id'], by_patient_uuid: ['patient_uuid'] } }
);

// Ecriture locale pour laborantin (reception + saisie hors ligne, chantier 4
// sous-projet 5) - PATCH via lab_result_details separee (une ligne par
// parametre, voir plus bas), jamais directement sur lab_results. Lecture
// seule pour medecin/nurse (stream clinical_lab_results, status='completed'
// uniquement) - conventions PK differentes coexistent sans risque car les
// roles sont mutuellement exclusifs par session et les filtres de statut ne
// se recouvrent jamais (completed vs pending/partial).
const lab_results = new Table(
  {
    server_id: column.integer,
    patient_id: column.integer,
    patient_uuid: column.text,
    test_type: column.text,
    test_date: column.text,
    status: column.text,
    note: column.text,
    examen_id: column.integer,
    code_lab_patient: column.text,
    prescribed_by_name: column.text,
    prescribed_by: column.integer,
    origin_prescription_id: column.integer,
    batch_uuid: column.text,
    external_patient_info: column.text,
  },
  { indexes: { by_patient: ['patient_id'], by_batch_uuid: ['batch_uuid'] } }
);

// Une ligne par parametre d'un dossier lab_results local (reception +
// saisie hors ligne). PK locale = son propre uuid client (genere a la
// reception, jamais l'entier detail_id serveur - inconnu tant que le
// dossier n'est pas confirme). result_uuid pointe vers lab_results.id
// (uuid du dossier parent, PAS son server_id - meme motif que
// prescriptions.medical_record_id pouvant chainer une consultation creee
// dans le meme geste hors ligne).
//
// result_id (entier, colonne separee) sert uniquement aux lignes
// TELECHARGEES depuis le serveur (stream lab_active_result_details) :
// PowerSync (Streams) interdit de projeter une colonne issue d'une autre
// table dans un SELECT (JOIN utilisable seulement pour filtrer en WHERE,
// et une sous-requete scalaire en position SELECT est elle aussi rejetee -
// "Invalid position for subqueries. Subqueries are only supported in WHERE
// clauses.", erreur fatale constatee empiriquement au redemarrage du
// service PowerSync). Or lab_result_details n'a pas de colonne uuid propre
// cote Postgres (voir ci/schema_only.sql) : impossible de peupler
// result_uuid directement depuis le serveur. Le stream synchronise donc
// l'entier result_id natif ; la resolution vers l'uuid du dossier parent
// (deja present localement via lab_active_results -> lab_results.id) se
// fait cote client par une jointure locale SQLite (Task 8), hors de
// portee des restrictions PowerSync. Une ligne donnee n'a donc jamais les
// deux colonnes renseignees en meme temps : result_uuid pour une ligne
// creee hors ligne, result_id pour une ligne telechargee.
const lab_result_details = new Table(
  {
    result_uuid: column.text,
    result_id: column.integer,
    parametre_id: column.integer,
    valeur_text: column.text,
    valeur_num: column.text,
  },
  { indexes: { by_result: ['result_uuid'], by_result_id: ['result_id'] } }
);

// Prescriptions medicales actives de type examen, pas encore transformees
// en dossier labo - alimente le pre-remplissage des examens a la reception
// d'un patient interne (LabReception.vue). Lecture seule.
const lab_pending_prescriptions = new Table({
  server_id: column.integer,
  patient_id: column.integer,
  prescribed_by_name: column.text,
  lab_exams_list: column.text,
  start_date: column.text,
});

// Parametres definis pour chaque examen (ex: Leucocytes pour une NFS) -
// necessaires pour construire les lignes lab_result_details a la reception
// hors ligne (une ligne vide par parametre de l'examen choisi, meme motif
// que create_lab_result cote serveur). Lecture seule.
const reference_lab_params = new Table({
  server_id: column.integer,
  examen_id: column.integer,
  nom_parametre: column.text,
  unite: column.text,
  type_valeur: column.text,
  input_type: column.text,
  options_list: column.text,
}, { indexes: { by_examen: ['examen_id'] } });

// Valeurs de reference par age/sexe - affichage INDICATIF uniquement cote
// client (l'interpretation qui fait autorite reste calculee serveur a la
// synchronisation, jamais dupliquee ici). Lecture seule.
const reference_lab_ranges = new Table({
  server_id: column.integer,
  parametre_id: column.integer,
  sexe: column.text,
  age_min: column.integer,
  age_max: column.integer,
  valeur_min: column.text,
  valeur_max: column.text,
}, { indexes: { by_parametre: ['parametre_id'] } });

const caisse = new Table(
  {
    server_id: column.integer,
    patient_id: column.integer,
    patient_label: column.text,
    // items : les lignes de facture ne sont JAMAIS creees/modifiees
    // independamment de leur transaction parente (aucun flux "ajouter une
    // ligne a une facture existante" dans l'API) - stockees ici en JSON
    // texte plutot que dans une table enfant separee. Plus simple ET plus
    // robuste qu'un caisse_item local : une seule ligne PowerSync a
    // ecrire/uploader par vente, pas de resolution parent->enfant a gerer.
    // LIMITE CONNUE (a verifier empiriquement en Tache 10, pas suppose) :
    // le stream secretariat_caisse (Tache 3) ne selectionne PAS cette
    // colonne (caisse_item vit dans une table serveur separee, jamais
    // synchronisee) - si le merge de lignes PowerSync remplace la ligne
    // locale entiere a chaque confirmation serveur, "items" pourrait
    // redevenir vide apres synchronisation complete d'une vente. Purement
    // cosmetique si constate (la vraie donnee reste intacte cote Postgres,
    // consultable en ligne) - documenter dans SUIVI-AVANCEMENT.md comme
    // limite connue si confirme, ne pas complexifier ce plan pour le
    // corriger a priori sans preuve du comportement reel.
    items: column.text,
    amount: column.text,
    advance_amount: column.text,
    paid_at: column.text,
    payment_method: column.text,
    transaction_type: column.text,
    note: column.text,
    status: column.text,
    // Garde-fou anti-perte-silencieuse (voir Tache 1/5) - jamais nul cote
    // serveur pour une ligne saine, rempli seulement si l'upload a
    // definitivement echoue.
    upload_error: column.text,
  },
  { indexes: { by_patient: ['patient_id'] } }
);

const caisse_retrait = new Table({
  server_id: column.integer,
  amount: column.text,
  justification: column.text,
  retrait_at: column.text,
  status: column.text,
  category: column.text,
  payment_method: column.text,
});

const paiement_echelonne = new Table(
  {
    server_id: column.integer,
    // transaction_id : entier server_id d'une transaction DEJA
    // synchronisee (paiement echelonne hors ligne desactive tant que la
    // transaction visee n'a pas de server_id, decision utilisateur
    // 2026-09-23 - jamais un uuid local ici, contrairement a
    // prescriptions.medical_record_id qui pouvait chainer 2 creations dans
    // le meme geste).
    transaction_id: column.integer,
    paid_amount: column.text,
    payment_date: column.text,
    payment_method: column.text,
    payment_type: column.text,
    note: column.text,
  },
  { indexes: { by_transaction: ['transaction_id'] } }
);

// Lecture seule - jamais d'ecriture locale (pas de PUT/PATCH pour
// pharmacy_stock dans DossierConnector.js). Stock affiche a titre
// informatif au moment de la vente hors ligne, jamais verifie/deduit cote
// client - decision utilisateur 2026-09-23.
const pharmacy_stock = new Table(
  {
    server_id: column.integer,
    drug_name: column.text,
    quantity: column.integer,
    threshold: column.integer,
    price: column.text,
    stock_status: column.text,
  },
);

// Catalogues de reference, lecture seule (streams reference_exam_catalog /
// reference_motifs) - jamais ecrits localement.
const exam_catalog = new Table({
  server_id: column.integer,
  code: column.text,
  nom: column.text,
  categorie: column.text,
  prix: column.text,
});

const motifs = new Table({
  code: column.text,
  label_fr: column.text,
  label_en: column.text,
});

// Quarantaine des envois refuses definitivement (patient en doublon et ses
// consultations/prescriptions). localOnly : jamais synchronisee, donc jamais
// purgee par une reconciliation PowerSync - une donnee medicale retenue ici
// ne peut ni disparaitre ni partir vers le mauvais patient.
const sync_quarantine = new Table(
  {
    kind: column.text,
    local_id: column.text,
    patient_uuid: column.text,
    payload: column.text,
    error: column.text,
    created_at: column.text,
  },
  { localOnly: true, indexes: { by_patient_uuid: ['patient_uuid'] } }
);

export const AppSchema = new Schema({
  appointments,
  patients_lookup,
  doctors_lookup,
  patients,
  medical_records,
  prescriptions,
  lab_results,
  lab_result_details,
  lab_pending_prescriptions,
  reference_lab_params,
  reference_lab_ranges,
  caisse,
  caisse_retrait,
  paiement_echelonne,
  pharmacy_stock,
  exam_catalog,
  motifs,
  sync_quarantine,
});
