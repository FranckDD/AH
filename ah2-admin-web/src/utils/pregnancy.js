// Regles d'affichage et de saisie de la grossesse (donnee sensible). Miroir de utils/pregnancy_visibility.py :
// lecture medecin, infirmier, laboratoire, admin, promoteur ; ecriture medecin, infirmier, laboratoire, admin.
// La secretaire ne voit ni ne saisit ces champs : aucun bloc, aucun libelle, aucune cle dans ses requetes.

export const PREGNANCY_READ_ROLES = ['medecin', 'nurse', 'laborantin', 'admin', 'promoteur'];
export const PREGNANCY_WRITE_ROLES = ['medecin', 'nurse', 'laborantin', 'admin'];
// Roles qui peuvent enregistrer la fiche patient (PUT /patients/{id}) : laboratoire et promoteur n'y ecrivent pas.
export const PATIENT_FILE_PREGNANCY_WRITE_ROLES = ['medecin', 'nurse', 'admin'];
export const PREGNANCY_REPORT_ROLES = ['promoteur', 'admin'];
export const PREGNANCY_STATUSES = ['inconnu', 'enceinte', 'non_enceinte'];
export const GA_MIN = 0;
export const GA_MAX = 45;
export const PROGRAM_NUMBER_MAX = 50;

export function canSeePregnancy(authStore) {
  return !!authStore && authStore.hasRole(PREGNANCY_READ_ROLES);
}

export function canWritePregnancy(authStore) {
  return !!authStore && authStore.hasRole(PREGNANCY_WRITE_ROLES);
}

export function canEditPregnancyOnPatientFile(authStore) {
  return !!authStore && authStore.hasRole(PATIENT_FILE_PREGNANCY_WRITE_ROLES);
}

// Le bloc grossesse n'a de sens que pour une femme ou un sexe inconnu.
export function pregnancyApplies(sex) {
  const s = String(sex || '').trim().toUpperCase();
  return s === '' || s === 'F' || s === 'X' || s === '-' || s === 'A' || s === 'FEMME' || s === 'FEMALE';
}

// SA valide : entier 0..45, ou vide.
export function parseGestationalWeeks(raw) {
  if (raw === null || raw === undefined || raw === '') return { ok: true, value: null };
  const n = typeof raw === 'number' ? raw : Number(String(raw).trim());
  if (!Number.isInteger(n) || n < GA_MIN || n > GA_MAX) return { ok: false, value: null };
  return { ok: true, value: n };
}

// Champs de grossesse a joindre a la demande de reception d'un patient EXTERNE. Renvoie {} pour un role
// qui n'ecrit pas la grossesse, ou quand le bloc ne s'applique pas : aucune cle n'est alors envoyee.
export function externalPregnancyPayload(form, authStore) {
  if (!canWritePregnancy(authStore) || !pregnancyApplies(form.gender)) return {};
  const out = {};
  const status = PREGNANCY_STATUSES.includes(form.pregnancy_status) ? form.pregnancy_status : 'inconnu';
  out.pregnancy_status = status;
  if (status === 'enceinte') {
    if (form.expected_delivery_date) out.expected_delivery_date = form.expected_delivery_date;
    const prog = String(form.pregnancy_program_number || '').trim();
    if (prog) out.pregnancy_program_number = prog.slice(0, PROGRAM_NUMBER_MAX);
  }
  return out;
}

// Statut de grossesse choisi pour la demande (cliche du rapport de subvention) : rien pour un role qui
// n'ecrit pas la grossesse ou quand le bloc ne s'applique pas.
export function pregnancyStatusAtResult(status, blockShown, authStore) {
  if (!canWritePregnancy(authStore) || !blockShown) return null;
  return PREGNANCY_STATUSES.includes(status) ? status : 'inconnu';
}

// SA du lot (colonne gestational_age_weeks) : seulement quand la patiente est enceinte et l'utilisateur ecrit.
export function batchGestationalWeeks(status, weeksRaw, authStore) {
  if (!canWritePregnancy(authStore) || status !== 'enceinte') return null;
  const r = parseGestationalWeeks(weeksRaw);
  return r.ok ? r.value : null;
}
