import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import api from '@/services/api';
import { db } from '@/powersync-client/client';
import { useAuthStore } from '@/stores/auth';

// Reproduit MedicalController._calculate_age() cote backend, pour le
// fallback de Finding 2 (revue finale chantier 6) quand resume_clinique
// echoue mais data.patient.birth_date est disponible.
function calculerAge(birthDate) {
    if (!birthDate) return null;
    const naissance = new Date(birthDate);
    if (Number.isNaN(naissance.getTime())) return null;
    const aujourdHui = new Date();
    let age = aujourdHui.getFullYear() - naissance.getFullYear();
    const moisDiff = aujourdHui.getMonth() - naissance.getMonth();
    if (moisDiff < 0 || (moisDiff === 0 && aujourdHui.getDate() < naissance.getDate())) {
        age--;
    }
    return age;
}

export const usePatientDossierStore = defineStore('patientDossier', () => {

    // --- ÉTAT (STATE) ---
    const patientSummary = ref(null);
    const medicalHistory = ref([]);
    const prescriptionHistory = ref([]);
    const labHistory = ref([]);
    const spiritualHistory = ref([]);
    const toxicoDossier = ref(null);
    const domainesIndisponibles = ref([]);
    const toxicoRestreint = ref(false);
    const spirituelRestreint = ref(false);

    const isLoading = ref(false);
    const error = ref(null);

    // --- ACTIONS ---

    // Secours hors ligne (medecin/nurse uniquement, appele seulement sur
    // echec reseau reel par fetchDossierComplete ci-dessous) - lit les
    // tables locales PowerSync deja synchronisees. Ne recalcule JAMAIS le
    // resume clinique (last_bp/last_weight/last_temp/last_diagnosis/
    // last_consultation_date restent null) - decision utilisateur
    // explicite, pour ne pas dupliquer la logique serveur.
    // L'identifiant de route est soit un patient_id serveur ("51"), soit
    // l'uuid local d'un patient cree hors ligne. Les colonnes entieres des
    // vues PowerSync ne correspondent jamais a une chaine : le patient_id
    // est lie en Number(), l'uuid en texte.
    function patientKeys(patientId) {
        const asNumber = Number(patientId);
        return {
            serverId: Number.isInteger(asNumber) ? asNumber : -1,
            localId: String(patientId),
        };
    }

    async function loadDossierFromLocalDb(patientId) {
        const { serverId, localId } = patientKeys(patientId);
        let p = await db.getOptional(
            'SELECT * FROM patients WHERE server_id = ? OR id = ?',
            [serverId, localId]
        );
        if (!p) {
            // Patient sans aucun dossier medical (donc absent de
            // clinical_patients) mais connu de patients_lookup : identite
            // seule, suffisante pour lui creer sa premiere consultation.
            const lookup = await db.getOptional(
                'SELECT patient_id, code_patient, first_name, last_name, contact_phone FROM patients_lookup WHERE patient_id = ?',
                [serverId]
            );
            if (lookup) {
                p = { ...lookup, server_id: lookup.patient_id, id: null };
            }
        }

        if (p) {
            patientSummary.value = {
                patient_id: p.server_id,
                patient_uuid: p.server_id ? null : p.id,
                full_name: `${p.first_name || ''} ${p.last_name || ''}`.trim(),
                code: p.code_patient || 'Code en attente',
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

        const labRows = await db.getAll(
            'SELECT * FROM lab_results WHERE patient_id = ? ORDER BY test_date DESC',
            [serverId]
        );
        // LabResultTable.vue attend result_id/examen_name/code_lab - la table
        // locale n'a que server_id/test_type/code_lab_patient (le nom reel de
        // l'examen, examen.nom, n'est pas synchronise - seul examen_id l'est).
        // test_type sert d'approximation lisible en secours hors ligne, pas
        // une lecture erronee de donnee : registre Important I2, revue finale
        // 2026-09-23.
        labHistory.value = labRows.map((r) => ({
            result_id: r.server_id,
            test_date: r.test_date,
            examen_name: r.test_type || '—',
            code_lab: r.code_lab_patient,
            status: r.status,
        }));

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

    // Lecture locale ponctuelle (pas un watch continu - perimetre reduit de
    // ce document) - utilisee par loadDossierFromLocalDb ci-dessus ET, pour
    // rafraichir l'affichage juste apres une ecriture locale reussie (voir
    // Taches 2/3/4), sans jamais repasser par un appel HTTP qui echouerait
    // ou lirait une valeur pas encore synchronisee au serveur.
    async function refreshMedicalHistoryLocal(patientId) {
        const { serverId, localId } = patientKeys(patientId);
        medicalHistory.value = await db.getAll(
            'SELECT * FROM medical_records WHERE patient_id = ? OR patient_uuid = ? ORDER BY consultation_date DESC',
            [serverId, localId]
        );
    }

    async function refreshPrescriptionHistoryLocal(patientId) {
        const { serverId, localId } = patientKeys(patientId);
        const rows = await db.getAll(
            'SELECT * FROM prescriptions WHERE patient_id = ? OR patient_uuid = ? ORDER BY start_date DESC',
            [serverId, localId]
        );
        prescriptionHistory.value = rows.map((r) => {
            let exams = [];
            try { exams = r.lab_exams_list ? JSON.parse(r.lab_exams_list) : []; } catch { exams = []; }
            return { ...r, prescription_id: r.server_id, is_lab_order: !!r.is_lab_order, lab_exams_list: Array.isArray(exams) ? exams : [] };
        });
    }

    async function fetchDossierComplete(patientId) {
        isLoading.value = true;
        error.value = null;

        const authStore = useAuthStore();

        // Identifiant non entier = uuid d'un patient cree localement : le
        // serveur ne le connait pas (ou pas encore). Comme l'ecriture est
        // toujours locale, c'est aussi le cas EN LIGNE juste apres la
        // creation (redirection automatique vers la fiche) - lecture locale
        // directe, jamais un GET /patients/<uuid>/dossier voue a l'echec.
        // Meme garde de role que le catch HTTP ci-dessous : les tables
        // locales patients/medical_records/prescriptions ne sont de toute
        // facon souscrites que pour medecin/nurse/secretaire, mais on
        // n'improvise pas un acces local sans le garde utilise partout
        // ailleurs dans ce fichier.
        if (!Number.isInteger(Number(patientId)) && authStore.hasRole(['medecin', 'nurse'])) {
            await loadDossierFromLocalDb(patientId);
            isLoading.value = false;
            return;
        }

        try {
            const { data } = await api.get(`/patients/${patientId}/dossier`);

            if (data.resume_clinique) {
                patientSummary.value = data.resume_clinique;
                patientSummary.value.flags = data.flags;
            } else if (data.patient) {
                // Finding 2 (revue finale chantier 6) : si le domaine
                // resume_clinique echoue seul, le backend renvoie quand
                // meme HTTP 200 avec data.patient (champs de base) et
                // data.flags (drapeaux de domaine calcules) pour permettre
                // une degradation gracieuse. Sans ce fallback, patientSummary
                // restait null et la page entiere affichait "patient
                // introuvable" alors que la requete avait reussi.
                const p = data.patient;
                patientSummary.value = {
                    patient_id: p.patient_id,
                    full_name: `${p.first_name || ''} ${p.last_name || ''}`.trim(),
                    code: p.code_patient,
                    // data.patient ne porte que birth_date (voir
                    // patient_repo.get_by_id) - resume_clinique calcule
                    // "age" cote backend (_calculate_age), on reproduit le
                    // meme calcul ici plutot que de lire un champ absent.
                    age: calculerAge(p.birth_date),
                    gender: p.gender,
                    flags: data.flags,
                    last_consultation_date: null,
                    last_bp: null,
                    last_weight: null,
                    last_temp: null,
                    last_diagnosis: null,
                    allergies: null,
                };
            } else {
                patientSummary.value = null;
            }

            medicalHistory.value = data.historique_medical || [];
            prescriptionHistory.value = data.prescriptions || [];
            labHistory.value = data.historique_labo || [];
            spiritualHistory.value = data.historique_spirituel || [];
            toxicoDossier.value = data.dossier_toxico ?? null;
            // La cle est litteralement absente de la reponse pour
            // medecin/nurse (backend, controller/patient_dossier_controller.py) -
            // distinct d'une valeur null qui, elle, signifie "existe mais pas
            // de donnees". Sans cette distinction, un patient reellement
            // toxico affichait "Aucun dossier toxicologie" a un medecin,
            // contredisant flags.is_toxicology=true affiche sur le meme ecran.
            toxicoRestreint.value = !('dossier_toxico' in data);
            spirituelRestreint.value = !('historique_spirituel' in data);
            domainesIndisponibles.value = data.domaines_indisponibles || [];
        } catch (err) {
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
            isLoading.value = false;
        }
    }

    async function refreshMedicalHistory(patientId) {
        try {
            const res = await api.get(`/medical_records/patient/${patientId}/history`);
            medicalHistory.value = res.data || [];

            const sumRes = await api.get(`/medical_records/patient/${patientId}/dme_summary`);
            patientSummary.value = sumRes.data;
        } catch (err) {
            console.error("Erreur refresh medical:", err);
        }
    }

    // Rafraichissement "best effort" du seul resume clinique (constantes
    // vitales), sans jamais toucher medicalHistory - a la difference de
    // refreshMedicalHistory ci-dessus, qui ecraserait l'historique local
    // fraichement ecrit par une valeur HTTP potentiellement en retard
    // (DossierConnector.js n'a peut-etre pas encore uploade). Echec
    // silencieux (hors ligne ou pas encore synchronise) - la valeur
    // precedente (perimee) reste affichee plutot que de casser l'ecran.
    // Registre Important I3, revue finale 2026-09-23.
    async function refreshVitalsSummaryLocal(patientId) {
        try {
            const sumRes = await api.get(`/medical_records/patient/${patientId}/dme_summary`);
            patientSummary.value = sumRes.data;
        } catch (err) {
            console.warn('Resume clinique non rafraichi (hors ligne ou pas encore synchronise):', err);
        }
    }

    // --- GETTERS (Inchangés) ---
    const isToxicology = computed(() => patientSummary.value?.flags?.is_toxicology || false);
    const isSpiritual = computed(() => patientSummary.value?.flags?.is_spiritual || false);
    const isClinical = computed(() => patientSummary.value?.flags?.is_clinical || false);
    const fullName = computed(() => patientSummary.value?.full_name || 'Patient Inconnu');
    const code = computed(() => patientSummary.value?.code || '-');
    const isDomaineIndisponible = (cle) => domainesIndisponibles.value.includes(cle);

    const vitals = computed(() => ({
        bp: patientSummary.value?.last_bp || '-',
        weight: patientSummary.value?.last_weight ? `${patientSummary.value.last_weight} kg` : '-',
        temp: patientSummary.value?.last_temp ? `${patientSummary.value.last_temp}°C` : '-',
        lastDate: patientSummary.value?.last_consultation_date
            ? new Date(patientSummary.value.last_consultation_date).toLocaleDateString('fr-FR')
            : '-'
    }));

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
        refreshVitalsSummaryLocal,
        isToxicology,
        isSpiritual,
        isClinical,
        fullName,
        code,
        vitals,
        isDomaineIndisponible
    };
});
