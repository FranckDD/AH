import { UpdateType } from '@powersync/web';
import { useAuthStore } from '@/stores/auth';
import { AppointmentGateway } from '@/services/AppointmentGateway';
import { MedicalRecordGateway } from '@/services/MedicalRecordGateway';
import { PrescriptionGateway } from '@/services/PrescriptionGateway';
import { CaisseGateway } from '@/services/CaisseGateway';
import api, { API_URL } from '@/services/api';
import { isPatientQuarantined, isLabResultQuarantined, quarantine } from '@/powersync-client/syncQuarantine';

// URL du service PowerSync self-hoste (voir powersync/.env, PS_PORT) -
// distincte de l'API FastAPI (API_URL). A definir dans .env.local du
// frontend si elle differe de la valeur par defaut locale.
const POWERSYNC_URL = import.meta.env.VITE_POWERSYNC_URL || 'http://localhost:18080';

// Codes d'erreur qu'il ne faut JAMAIS re-essayer indefiniment - abandonner
// l'operation et la retirer de la file plutot que de bloquer toute la
// synchronisation dessus.
function isFatalUploadError(error) {
  const status = error?.response?.status;
  return status === 400 || status === 404 || status === 409 || status === 422;
}

// Envoi d'une operation labo avec quarantaine PAR OPERATION (labo
// uniquement - les autres tables gardent le traitement global du catch de
// uploadData, inchange). Une reception multi-examens produit plusieurs
// lab_results:PUT dans UNE seule transaction CRUD PowerSync : sans ce
// traitement local, un refus definitif de l'examen A faisait completer la
// transaction entiere dans le catch global, retirant de la file l'examen B
// jamais tente et jamais mis en quarantaine. Ici, une erreur fatale met
// l'operation courante en quarantaine et la boucle continue ; une erreur
// transitoire est relancee telle quelle (rejeu de toute la transaction,
// idempotent cote serveur via les uuid et les garde-fous
// isLabResultQuarantined avant chaque envoi).
async function sendLabOp(database, send, quarantineEntry) {
  try {
    await send();
  } catch (error) {
    if (!isFatalUploadError(error)) throw error;
    console.error('Operation labo refusee definitivement, mise en quarantaine:', quarantineEntry.localId, error);
    try {
      await quarantine(database, {
        ...quarantineEntry,
        error: error?.response?.data?.detail || quarantineEntry.error,
      });
    } catch (quarantineError) {
      console.error('Impossible de mettre l\'operation labo en quarantaine:', quarantineError);
    }
  }
}

export class DossierConnector {
  async fetchCredentials() {
    const authStore = useAuthStore();
    if (!authStore.token) {
      throw new Error('Aucun token d\'authentification disponible pour PowerSync.');
    }
    return {
      endpoint: POWERSYNC_URL,
      token: authStore.token,
    };
  }

  async uploadData(database) {
    const transaction = await database.getNextCrudTransaction();
    if (!transaction) {
      return;
    }

    let lastOp = null;
    try {
      for (const op of transaction.crud) {
        lastOp = op;

        switch (`${op.table}:${op.op}`) {
          case 'appointments:PUT': {
            await AppointmentGateway.createAppointment({
              patientId: op.opData.patient_id,
              specialty: op.opData.specialty,
              appointmentDate: op.opData.appointment_date,
              appointmentTime: op.opData.appointment_time,
              reason: op.opData.reason,
              uuid: op.id,
            });
            break;
          }
          case 'appointments:PATCH': {
            // Modification RDV : necessite server_id, pas le uuid local.
            // Relit la ligne locale COMPLETE (pas op.opData, qui peut
            // n'avoir que les colonnes modifiees) - meme motif que le
            // pilote : PowerSync a deja applique l'ecriture locale avant
            // de mettre l'operation en file.
            const current = await database.getOptional(
              'SELECT server_id, patient_id, specialty, appointment_date, appointment_time, reason FROM appointments WHERE id = ?',
              [op.id]
            );
            if (!current?.server_id) {
              console.warn(`RDV ${op.id} : modification hors ligne d'une creation pas encore confirmee, ignoree pour cet upload (sera reprise via le prochain PUT).`);
              break;
            }
            await AppointmentGateway.updateAppointment(current.server_id, {
              patientId: current.patient_id,
              specialty: current.specialty,
              appointmentDate: current.appointment_date,
              appointmentTime: current.appointment_time,
              reason: current.reason,
            });
            break;
          }
          case 'patients:PUT': {
            // Patient cree hors ligne (medecin/nurse/secretaire). Meme appel
            // que patientStore.addPatient en ligne (pas de gateway patient
            // dediee). Rejeu du meme uuid = 200 idempotent cote serveur.
            await api.post('/patients/', {
              first_name: op.opData.first_name,
              last_name: op.opData.last_name,
              birth_date: op.opData.birth_date,
              gender: op.opData.gender || null,
              national_id: op.opData.national_id || null,
              contact_phone: op.opData.contact_phone || null,
              assurance: op.opData.assurance || null,
              residence: op.opData.residence || null,
              father_name: op.opData.father_name || null,
              mother_name: op.opData.mother_name || null,
              uuid: op.id,
            });
            break;
          }
          case 'medical_records:PUT': {
            // Patient en quarantaine (refuse definitivement) : la consultation
            // est retenue avec lui au lieu d'etre envoyee vers un patient qui
            // n'existe pas cote serveur (elle serait refusee puis perdue).
            if (await isPatientQuarantined(database, op.opData.patient_uuid)) {
              await quarantine(database, {
                kind: 'medical_record',
                localId: op.id,
                patientUuid: op.opData.patient_uuid,
                payload: op.opData,
                error: 'Patient en echec de synchronisation',
              });
              break;
            }
            await MedicalRecordGateway.createMedicalRecord({
              patientId: op.opData.patient_id,
              patientUuid: op.opData.patient_uuid,
              consultationDate: op.opData.consultation_date,
              motifCode: op.opData.motif_code,
              appointmentId: op.opData.appointment_id,
              maritalStatus: op.opData.marital_status,
              severity: op.opData.severity,
              bp: op.opData.bp,
              temperature: op.opData.temperature,
              weight: op.opData.weight,
              height: op.opData.height,
              medicalHistory: op.opData.medical_history,
              allergies: op.opData.allergies,
              symptoms: op.opData.symptoms,
              diagnosis: op.opData.diagnosis,
              treatment: op.opData.treatment,
              notes: op.opData.notes,
              needsDoctorReview: !!op.opData.needs_doctor_review,
              assignedDoctorId: op.opData.assigned_doctor_id || null,
              uuid: op.id,
            });
            break;
          }
          case 'medical_records:PATCH': {
            // Modification d'une consultation existante - EN PERIMETRE
            // (contrairement aux prescriptions/RDV, la spec inclut
            // explicitement "creer/modifier une consultation medicale").
            // Meme motif que appointments:PATCH : necessite server_id,
            // relit la ligne locale COMPLETE (pas op.opData) pour ne pas
            // ecraser un champ non modifie localement avec null.
            const currentRecord = await database.getOptional(
              `SELECT server_id, patient_id, consultation_date, motif_code, marital_status,
                      severity, bp, temperature, weight, height, medical_history, allergies,
                      symptoms, diagnosis, treatment, notes
               FROM medical_records WHERE id = ?`,
              [op.id]
            );
            if (!currentRecord?.server_id) {
              console.warn(`Consultation ${op.id} : modification hors ligne d'une creation pas encore confirmee, ignoree pour cet upload (sera reprise via le prochain PUT).`);
              break;
            }
            await MedicalRecordGateway.updateMedicalRecord(currentRecord.server_id, {
              patientId: currentRecord.patient_id,
              consultationDate: currentRecord.consultation_date,
              motifCode: currentRecord.motif_code,
              maritalStatus: currentRecord.marital_status,
              severity: currentRecord.severity,
              bp: currentRecord.bp,
              temperature: currentRecord.temperature,
              weight: currentRecord.weight,
              height: currentRecord.height,
              medicalHistory: currentRecord.medical_history,
              allergies: currentRecord.allergies,
              symptoms: currentRecord.symptoms,
              diagnosis: currentRecord.diagnosis,
              treatment: currentRecord.treatment,
              notes: currentRecord.notes,
            });
            break;
          }
          case 'prescriptions:PUT': {
            // Si la prescription est liee a une consultation creee dans
            // le meme geste hors ligne, sa ligne locale medical_records n'a
            // pas forcement encore de server_id (la file d'envoi est videe
            // AVANT tout re-telechargement qui l'ecrirait en local) - dans
            // ce cas, on transmet l'uuid local de la consultation, que le
            // serveur resout lui-meme (resolve_medical_record_id, meme
            // motif que patient_uuid). Correctif Critical revue finale :
            // l'ancien comportement abandonnait purement et simplement la
            // prescription dans ce cas, en pretendant a tort qu'elle serait
            // "reprise au prochain cycle" (transaction.complete() la
            // retirait quand meme definitivement de la file).
            if (await isPatientQuarantined(database, op.opData.patient_uuid)) {
              await quarantine(database, {
                kind: 'prescription',
                localId: op.id,
                patientUuid: op.opData.patient_uuid,
                payload: op.opData,
                error: 'Patient en echec de synchronisation',
              });
              break;
            }
            let medicalRecordServerId = null;
            let medicalRecordUuid = null;
            if (op.opData.medical_record_id) {
              const linkedRecord = await database.getOptional(
                'SELECT server_id FROM medical_records WHERE id = ?',
                [op.opData.medical_record_id]
              );
              if (linkedRecord?.server_id) {
                medicalRecordServerId = linkedRecord.server_id;
              } else {
                medicalRecordUuid = op.opData.medical_record_id;
              }
            }
            await PrescriptionGateway.createPrescription({
              patientId: op.opData.patient_id,
              patientUuid: op.opData.patient_uuid,
              medicalRecordId: medicalRecordServerId,
              medicalRecordUuid: medicalRecordUuid,
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
            break;
          }
          case 'prescriptions:PATCH': {
            // Modification hors ligne d'une prescription synchronisee (bouton
            // "modifier" desactive tant qu'elle n'a pas de server_id). Relit
            // la ligne locale COMPLETE (pas op.opData, qui peut n'avoir que
            // les colonnes modifiees) - meme motif que appointments:PATCH.
            const currentPresc = await database.getOptional(
              `SELECT server_id, patient_id, medical_record_id, medication, dosage, frequency,
                      duration, start_date, end_date, notes, is_lab_order, lab_exams_list
               FROM prescriptions WHERE id = ?`,
              [op.id]
            );
            if (!currentPresc?.server_id) {
              console.warn(`Prescription ${op.id} : modification d'une creation pas encore confirmee, ignoree pour cet upload.`);
              break;
            }
            let exams = [];
            try { exams = currentPresc.lab_exams_list ? JSON.parse(currentPresc.lab_exams_list) : []; } catch { exams = []; }
            await PrescriptionGateway.updatePrescription(currentPresc.server_id, {
              patientId: currentPresc.patient_id,
              medicalRecordId: currentPresc.medical_record_id,
              isLabOrder: !!currentPresc.is_lab_order,
              medication: currentPresc.medication,
              dosage: currentPresc.dosage,
              frequency: currentPresc.frequency,
              duration: currentPresc.duration,
              startDate: currentPresc.start_date,
              endDate: currentPresc.end_date,
              notes: currentPresc.notes,
              labExamsList: Array.isArray(exams) ? exams : [],
            });
            break;
          }
          case 'caisse:PUT': {
            // items stocke en JSON texte localement (voir AppSchema.js,
            // Tache 4) - reconstruit en tableau avant l'appel gateway, qui
            // envoie exactement le meme payload que le formulaire en ligne
            // (CaisseInvoiceModal.vue) - toute la logique metier (stock,
            // paiement initial) reste geree cote serveur, jamais reproduite
            // ici.
            await CaisseGateway.createInvoice({
              patient_id: op.opData.patient_id,
              patient_label: op.opData.patient_label,
              amount: Number(op.opData.amount),
              advance_amount: Number(op.opData.advance_amount),
              payment_method: op.opData.payment_method,
              transaction_type: op.opData.transaction_type,
              note: op.opData.note,
              items: op.opData.items ? JSON.parse(op.opData.items) : [],
              uuid: op.id,
            });
            break;
          }
          case 'caisse_retrait:PUT': {
            await CaisseGateway.createRetrait({
              amount: Number(op.opData.amount),
              justification: op.opData.justification,
              category: op.opData.category,
              payment_method: op.opData.payment_method,
              uuid: op.id,
            });
            break;
          }
          case 'lab_results:PUT': {
            // Patient interne en quarantaine (refuse definitivement) : le
            // dossier labo qui le reference rejoint la quarantaine au lieu
            // d'etre envoye vers un patient inexistant - meme motif que
            // medical_records/prescriptions au sous-projet 4.
            if (op.opData.patient_uuid && await isPatientQuarantined(database, op.opData.patient_uuid)) {
              await quarantine(database, {
                kind: 'lab_result',
                localId: op.id,
                patientUuid: op.opData.patient_uuid,
                payload: op.opData,
                error: 'Patient en echec de synchronisation',
              });
              break;
            }
            // Deja en quarantaine (rejeu de la transaction apres une erreur
            // transitoire sur une operation suivante) : ne pas renvoyer.
            if (await isLabResultQuarantined(database, op.id)) {
              break;
            }
            // Appel HTTP direct (pas LabGateway) : le connecteur doit
            // echouer reellement si l'API est injoignable, jamais retomber
            // sur une ecriture locale - meme motif que les autres cas.
            await sendLabOp(database, () => api.post('/labo/results/batch', {
              patient_id: op.opData.patient_id || null,
              patient_uuid: op.opData.patient_uuid || null,
              prescribed_by_id: op.opData.prescribed_by || null,
              prescribed_by_name: op.opData.prescribed_by_name || null,
              external_patient_info: op.opData.external_patient_info ? JSON.parse(op.opData.external_patient_info) : null,
              origin_prescription_id: op.opData.origin_prescription_id || null,
              batch_uuid: op.opData.batch_uuid,
              results: [{ examen_id: op.opData.examen_id, uuid: op.id }],
            }), {
              kind: 'lab_result',
              localId: op.id,
              patientUuid: op.opData.patient_uuid || null,
              payload: op.opData,
              error: 'Dossier labo refuse par le serveur.',
            });
            break;
          }
          case 'lab_result_details:PUT':
          case 'lab_result_details:PATCH': {
            // Le dossier parent peut lui-meme etre en quarantaine (memes
            // conditions que lab_results:PUT ci-dessus, valeur saisie hors
            // ligne AVANT que l'echec de reception ne soit connu - cas rare
            // mais possible, spec section 4). On la retient avec lui plutot
            // que de tenter un envoi qui echouera de toute facon (le dossier
            // lui-meme n'existera jamais cote serveur).
            //
            // PUT et PATCH partagent le meme corps : Task 7 pre-cree une
            // ligne lab_result_details vide par parametre (INSERT -> PUT),
            // puis Task 8 y ecrit la valeur saisie via UPDATE (-> PATCH,
            // puisque PowerSync emet PATCH pour une ecriture locale sur une
            // ligne locale deja existante). Dans le scenario principal de ce
            // sous-projet (dossier cree ET rempli hors ligne dans la meme
            // session), CHAQUE saisie de valeur produit un PATCH, jamais un
            // PUT - sans ce cas, ces operations tomberaient dans le defaut
            // (console.warn, aucun envoi) et la saisie hors ligne serait
            // silencieusement perdue cote serveur (perte de donnees critique).
            // Rien ne distingue les deux cote serveur : save_results_values
            // resout la ligne cible et ecrase sa valeur de facon idempotente
            // que ce soit un premier envoi ou une mise a jour.
            //
            // op.opData n'est PAS fiable ici : sur un PATCH, PowerSync ne
            // met dans opData que les colonnes reellement modifiees (voir
            // CrudEntry.ts - "PATCH = Update existing row. Contains the id,
            // and value of each changed column."). Or l'ecriture locale qui
            // produit ce PATCH (labGateway.js::updateResultValues, branche
            // locale) ne fait que UPDATE lab_result_details SET valeur_text
            // = ? WHERE id = ? - donc op.opData ne contient QUE valeur_text,
            // jamais result_uuid ni parametre_id. Meme motif que
            // appointments:PATCH/medical_records:PATCH/prescriptions:PATCH
            // ci-dessus : on relit la ligne locale COMPLETE via op.id, qui
            // identifie la cle primaire locale quel que soit le type d'op.
            //
            // Deux sortes de lignes (voir AppSchema.js et
            // labGateway.js::getResultDetail) :
            //  - creee hors ligne (result_uuid seul) : cle de valeur envoyee
            //    = -parametre_id (convention negative, jamais en collision
            //    avec un vrai detail_id - voir lab_repo.save_results_values),
            //    dossier designe par son uuid ;
            //  - telechargee (result_id seul, dossier deja synchronise puis
            //    saisi hors ligne) : op.id EST le vrai detail_id serveur,
            //    dossier designe par son result_id entier. Sans ce cas, une
            //    saisie hors ligne sur un dossier deja synchronise etait
            //    silencieusement ignoree a l'envoi.
            const current = await database.getOptional(
              'SELECT result_uuid, result_id, parametre_id, valeur_text FROM lab_result_details WHERE id = ?',
              [op.id]
            );
            if (!current || (!current.result_uuid && current.result_id == null)) {
              console.warn(`Detail labo ${op.id} : ligne locale introuvable, ignore pour cet upload.`);
              break;
            }
            const isLocalRow = !!current.result_uuid;
            const parent = isLocalRow
              ? await database.getOptional('SELECT id, patient_uuid FROM lab_results WHERE id = ?', [current.result_uuid])
              : await database.getOptional('SELECT id, patient_uuid FROM lab_results WHERE server_id = ?', [current.result_id]);
            const detailPayload = {
              ...op.opData,
              result_uuid: current.result_uuid || parent?.id || null,
              parametre_id: current.parametre_id,
              valeur_text: current.valeur_text,
            };
            if (parent?.patient_uuid && await isPatientQuarantined(database, parent.patient_uuid)) {
              await quarantine(database, {
                kind: 'lab_result_detail',
                localId: op.id,
                patientUuid: parent.patient_uuid,
                payload: detailPayload,
                error: 'Dossier labo en echec de synchronisation',
              });
              break;
            }
            // Dossier parent lui-meme refuse (ex. examen supprime du
            // catalogue) : la valeur est retenue avec lui, pas envoyee vers
            // un dossier qui n'existe pas cote serveur.
            if (parent?.id && await isLabResultQuarantined(database, parent.id)) {
              await quarantine(database, {
                kind: 'lab_result_detail',
                localId: op.id,
                patientUuid: parent.patient_uuid || null,
                payload: detailPayload,
                error: 'Dossier labo en echec de synchronisation',
              });
              break;
            }
            const pathId = isLocalRow ? current.result_uuid : current.result_id;
            const valueKey = isLocalRow ? -Number(current.parametre_id) : Number(op.id);
            await sendLabOp(database, () => api.put(`/labo/results/${pathId}/values`, {
              values: { [valueKey]: current.valeur_text },
              completed: false,
              // null = note non modifiee cote serveur ; la note passe par
              // lab_results:PATCH ci-dessous.
              note: null,
            }), {
              kind: 'lab_result_detail',
              localId: op.id,
              patientUuid: parent?.patient_uuid || null,
              payload: detailPayload,
              error: 'Valeur de dossier labo refusee par le serveur.',
            });
            break;
          }
          case 'lab_results:PATCH': {
            // Ecritures locales possibles sur lab_results apres sa creation
            // (labGateway.js::updateResultValues, branche locale) : la note
            // (toute sauvegarde) et, pour "Valider & Cloturer" hors ligne,
            // UPDATE lab_results SET status = '_local_completing'.
            // PowerSync ne genere jamais de PATCH a partir d'une ligne
            // telechargee (seulement a partir d'une ecriture locale).
            // Porte le signal mark_completed jusqu'au serveur : sans ce cas,
            // "Valider & Cloturer" hors ligne n'aurait aucun effet cote
            // serveur (les valeurs arriveraient via lab_result_details:PUT
            // ci-dessus, mais le dossier resterait indefiniment pending/
            // partial) - violerait la spec section 3 ("mark_completed
            // transite tel quel").
            //
            // Seule la sentinelle LOCALE '_local_completing' (jamais envoyee
            // par le serveur) signifie "Valider & Cloturer" hors ligne -
            // 'partial' est aussi le statut serveur legitime d'un dossier
            // deja partiellement saisi, qu'un simple brouillon hors ligne
            // (PATCH de la note seule) aurait alors finalise a tort.
            // Tout autre PATCH est un brouillon : envoye avec completed:false
            // et la note locale - exactement ce que fait la meme sauvegarde
            // brouillon en ligne - sinon une note saisie hors ligne en
            // brouillon n'atteindrait jamais le serveur.
            const current = await database.getOptional(
              'SELECT status, note, patient_uuid FROM lab_results WHERE id = ?',
              [op.id]
            );
            if (!current) {
              break;
            }
            if (current.patient_uuid && await isPatientQuarantined(database, current.patient_uuid)) {
              break;
            }
            if (await isLabResultQuarantined(database, op.id)) {
              break;
            }
            const completing = current.status === '_local_completing';
            await sendLabOp(database, () => api.put(`/labo/results/${op.id}/values`, {
              values: {},
              completed: completing,
              note: current.note ?? null,
            }), {
              kind: 'lab_result',
              localId: op.id,
              patientUuid: current.patient_uuid || null,
              payload: { ...op.opData, status: current.status, note: current.note },
              error: 'Dossier labo refuse par le serveur.',
            });
            break;
          }
          case 'paiement_echelonne:PUT': {
            // Desactive cote UI tant que la transaction visee n'a pas de
            // server_id (Tache 9) - ce garde-fou existe aussi ici en
            // seconde ligne de defense, meme motif que la resolution
            // consultation->prescription du sous-projet 2.
            if (!op.opData.transaction_id) {
              console.warn(`Versement ${op.id} : aucune transaction_id associee, ignore pour cet upload.`);
              break;
            }
            await CaisseGateway.addPayment(op.opData.transaction_id, {
              paid_amount: Number(op.opData.paid_amount),
              payment_method: op.opData.payment_method,
              payment_type: op.opData.payment_type,
              note: op.opData.note,
              uuid: op.id,
            });
            break;
          }
          default: {
            // DELETE (toutes tables), PATCH caisse/patients : hors perimetre
            // (ecritures locales purement cosmetiques ou suppressions de
            // lignes abandonnees par la quarantaine) - log defensif.
            console.warn(`Operation ${op.op} sur ${op.table}/${op.id} recue par le connecteur mais hors perimetre - ignoree.`);
          }
        }
      }

      await transaction.complete();
    } catch (error) {
      console.error('Erreur upload PowerSync:', lastOp, error);
      if (isFatalUploadError(error)) {
        console.error(`Operation ${lastOp?.op} sur ${lastOp?.table}/${lastOp?.id} abandonnee (erreur non recuperable) - retiree de la file.`);
        // Garde-fou (registre Important, sous-projet 3) : une vente caisse
        // ne doit JAMAIS disparaitre silencieusement (ex. stock insuffisant
        // au moment de l'upload, alors qu'elle a ete reellement encaissee
        // au guichet). Persiste un signal visible au lieu du simple log
        // console habituel pour les autres tables.
        if (lastOp?.table === 'caisse') {
          try {
            const detail = error?.response?.data?.detail || 'Echec de synchronisation - contacter un administrateur.';
            await database.execute('UPDATE caisse SET upload_error = ? WHERE id = ?', [detail, lastOp.id]);
          } catch (markError) {
            console.error('Impossible de marquer la transaction en echec de sync:', markError);
          }
        }
        // Patient refuse definitivement (doublon national_id, donnees
        // invalides) : mis en quarantaine locale - ses consultations et
        // prescriptions suivantes y seront retenues (cases ci-dessus) au lieu
        // d'etre envoyees vers un patient inexistant. Protege par son propre
        // try/catch : ne doit jamais faire planter le connecteur.
        if (lastOp?.table === 'patients') {
          try {
            await quarantine(database, {
              kind: 'patient',
              localId: lastOp.id,
              patientUuid: lastOp.id,
              payload: lastOp.opData,
              error: error?.response?.data?.detail || 'Patient refuse par le serveur.',
            });
          } catch (quarantineError) {
            console.error('Impossible de mettre le patient en quarantaine:', quarantineError);
          }
        }
        // Dossier labo refuse definitivement par le serveur (ex. examen_id
        // introuvable dans le catalogue entre la reception hors ligne et
        // l'envoi) : spec sous-projet, section Tests, cas manuel #3 -
        // "422 -> quarantaine du dossier, jamais un 500, jamais une perte
        // silencieuse". Protege par son propre try/catch : une erreur de
        // quarantaine ne doit jamais faire planter le connecteur.
        if (lastOp?.table === 'lab_results') {
          try {
            const current = await database.getOptional(
              'SELECT patient_uuid FROM lab_results WHERE id = ?',
              [lastOp.id]
            );
            await quarantine(database, {
              kind: 'lab_result',
              localId: lastOp.id,
              patientUuid: current?.patient_uuid || lastOp.opData?.patient_uuid || null,
              payload: lastOp.opData,
              error: error?.response?.data?.detail || 'Dossier labo refuse par le serveur.',
            });
          } catch (quarantineError) {
            console.error('Impossible de mettre le dossier labo en quarantaine:', quarantineError);
          }
        }
        // Meme garde-fou pour une valeur de dossier labo (lab_result_details).
        // lastOp.opData peut ne pas porter result_uuid de maniere fiable sur
        // une erreur fatale PATCH (meme limitation deja corrigee ailleurs
        // dans ce fichier) - lookup defensif best-effort, null accepte en
        // repli, chemin secondaire rare, contrairement au cas principal
        // lab_results:PUT/PATCH deja durci.
        if (lastOp?.table === 'lab_result_details') {
          try {
            const detailRow = await database.getOptional(
              'SELECT result_uuid FROM lab_result_details WHERE id = ?',
              [lastOp.id]
            );
            await quarantine(database, {
              kind: 'lab_result_detail',
              localId: lastOp.id,
              patientUuid: null,
              payload: { ...lastOp.opData, result_uuid: detailRow?.result_uuid || null },
              error: error?.response?.data?.detail || 'Valeur de dossier labo refusee par le serveur.',
            });
          } catch (quarantineError) {
            console.error('Impossible de mettre la valeur labo en quarantaine:', quarantineError);
          }
        }
        await transaction.complete();
      } else {
        // Erreur reseau/serveur transitoire - ne pas completer la
        // transaction, PowerSync retentera plus tard.
        throw error;
      }
    }
  }
}
