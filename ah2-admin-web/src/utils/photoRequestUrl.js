// URL de la requete reseau d'une photo produit : la version fait partie de l'URL pour que le cache HTTP
// du navigateur (Cache-Control: max-age=3600) ne serve jamais l'ancienne image apres un remplacement.
export function photoRequestUrl(medicationId, version) {
    return `/pharmacy/${medicationId}/photo?v=${Number(version) || 0}`;
}
