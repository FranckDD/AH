// Un echec de chargement qui doit s'afficher comme tel (et non comme "0" ou "Aucun ...") : pas de reponse du
// serveur (hors ligne, API injoignable) ou erreur serveur 5xx. Un refus applicatif (4xx) garde son message.
export function isLoadFailure(err) {
    if (!err) return false;
    if (!err.response) return true;
    return Number(err.response.status) >= 500;
}
