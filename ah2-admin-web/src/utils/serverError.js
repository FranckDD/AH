// Message lisible d'un refus du serveur (fonction pure, testee). Une erreur de validation FastAPI (422) renvoie
// une LISTE [{ loc, msg }] : sans ce formatage on n'affichait que « donnees refusees » sans dire quel champ.
export function describeServerError(error, fallback = '') {
    const detail = error?.response?.data?.detail;
    if (typeof detail === 'string' && detail) return detail;
    if (Array.isArray(detail) && detail.length) {
        return detail
            .map((d) => {
                const field = Array.isArray(d?.loc) ? d.loc.filter((p) => p !== 'body').join('.') : '';
                const msg = d?.msg || '';
                return field ? `${field} : ${msg}` : msg;
            })
            .filter(Boolean)
            .join(' ; ') || fallback;
    }
    return fallback;
}
