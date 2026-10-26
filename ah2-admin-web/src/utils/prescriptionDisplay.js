// Affichage d'une prescription dans l'onglet Traitements du dossier patient.
// Le serveur remplit "N/A" dans dosage/frequence/duree d'une demande d'examen
// (colonnes NOT NULL) : ces valeurs de remplissage ne doivent jamais s'afficher.

const KNOWN_STATUSES = ['active', 'completed', 'cancelled'];

export function prescriptionStatusLabelKey(status) {
  const s = String(status ?? '').trim().toLowerCase();
  return KNOWN_STATUSES.includes(s) ? `medical.prescription_status.${s}` : 'medical.prescription_status.unknown';
}

export function isPlaceholder(value) {
  const s = String(value ?? '').trim();
  return s === '' || s.toLowerCase() === 'n/a';
}

export function prescriptionDetails(p) {
  return [p?.dosage, p?.frequency, p?.duration].filter((v) => !isPlaceholder(v));
}

export function isActivePrescription(status) {
  return String(status ?? '').trim().toLowerCase() === 'active';
}
