// Refus d'affectation du planning : le serveur renvoie 409 avec detail = { code, message }
// (message francais de repli). Le code est traduit ici (FR/EN) ; code inconnu ou
// ancien format (texte brut) : on affiche le message du serveur.
const KNOWN_CODES = ['shift_night_exclusive', 'shift_rest_after_night', 'shift_already_assigned'];

export function shiftErrorMessage(err, t) {
  const detail = err?.response?.data?.detail;
  if (detail && typeof detail === 'object') {
    if (KNOWN_CODES.includes(detail.code)) return t(`nurseShift.errors.${detail.code}`);
    if (detail.message) return detail.message;
  }
  if (typeof detail === 'string' && detail) return detail;
  return t('nurseShift.errors.generic');
}
