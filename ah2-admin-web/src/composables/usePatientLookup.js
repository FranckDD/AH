import { ref } from 'vue';
import api from '@/services/api';
import { db } from '@/powersync-client/client';
import { useAuthStore } from '@/stores/auth';

// Composable partage de recherche patient par code (MedicalRecordModal,
// ConsultationModal, PrescriptionModal). Chantier 4 sous-projet 4 :
// secours local hors ligne sur patients_lookup (deja synchronise pour
// medecin/nurse/secretaire - memes patients qu'en ligne, GET /patients/
// etant ouvert a ces roles) et prise en charge d'un patient cree hors
// ligne, qui n'a pas encore d'id serveur ni de code : patientUuid.
export function usePatientLookup(getNotFoundMessage) {
  const patientCode = ref('');
  const patientId = ref(null);
  const patientUuid = ref(null);
  const patientName = ref('');
  const patientLookupMessage = ref('');

  let pendingLookup = null;
  let pendingLookupCode = null;

  function normalizeCode(raw) {
    const trimmed = (raw || '').trim();
    if (!trimmed) return '';
    let code = trimmed.toUpperCase();
    if (!code.startsWith('AH2-')) {
      code = `AH2-${code}`;
    }
    return code;
  }

  function applyMatch(match) {
    patientId.value = match.id || match.patient_id;
    patientUuid.value = null;
    patientName.value = [match.first_name, match.last_name].filter(Boolean).join(' ');
    patientLookupMessage.value = patientName.value;
  }

  function applyNotFound() {
    patientId.value = null;
    patientUuid.value = null;
    patientName.value = '';
    patientLookupMessage.value = getNotFoundMessage();
  }

  async function lookupPatient() {
    const code = normalizeCode(patientCode.value);
    if (!code) {
      patientId.value = null;
      patientUuid.value = null;
      patientName.value = '';
      patientLookupMessage.value = '';
      pendingLookup = null;
      pendingLookupCode = null;
      return;
    }
    patientCode.value = code;
    pendingLookupCode = code;

    pendingLookup = (async () => {
      try {
        const res = await api.get('/patients/', { params: { search: code, per_page: 5 } });
        const list = Array.isArray(res.data) ? res.data : (res.data.data || []);
        const match = list.find((p) => p.code_patient === code) || list[0] || null;
        if (match) applyMatch(match);
        else applyNotFound();
      } catch (err) {
        const authStore = useAuthStore();
        if (!err.response && authStore.hasRole(['medecin', 'nurse', 'secretaire'])) {
          const local = await db.getOptional(
            'SELECT patient_id, code_patient, first_name, last_name FROM patients_lookup WHERE code_patient = ?',
            [code]
          );
          if (local) {
            applyMatch(local);
            return;
          }
        } else {
          console.error('Erreur recherche patient:', err);
        }
        applyNotFound();
      }
    })();

    await pendingLookup;
  }

  async function ensureLookup() {
    const currentCode = normalizeCode(patientCode.value);
    if (!currentCode) return;

    if (pendingLookup && pendingLookupCode === currentCode) {
      await pendingLookup;
      return;
    }

    // Le code a change depuis le dernier lookup (ou aucun lookup n'a
    // encore ete declenche) : recherche fraiche plutot que d'attendre une
    // promesse perimee qui validerait le submit contre un autre patient.
    await lookupPatient();
  }

  // Patient deja connu (fiche patient, edition d'un dossier existant) :
  // marque comme resolu - ensureLookup() ne relance PAS de recherche pour ce
  // meme code (hors ligne, cette recherche echouait et effacait le patient).
  function setFromExisting({ patientId: pid, patientUuid: puuid, code, firstName, lastName }) {
    patientId.value = pid || null;
    patientUuid.value = pid ? null : (puuid || null);
    patientCode.value = code || '';
    pendingLookupCode = normalizeCode(code || '');
    pendingLookup = Promise.resolve();
    patientName.value = [firstName, lastName].filter(Boolean).join(' ');
    patientLookupMessage.value = patientName.value;
  }

  return {
    patientCode,
    patientId,
    patientUuid,
    patientName,
    patientLookupMessage,
    lookupPatient,
    ensureLookup,
    setFromExisting,
  };
}
