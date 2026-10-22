// Lien d'une prescription vers sa consultation, tel qu'il doit partir au serveur (fonction pure, testee).
// La colonne locale medical_record_id contient soit l'uuid d'une consultation creee dans le meme geste hors ligne,
// soit l'identifiant serveur ENTIER d'une consultation deja synchronisee. Le serveur attend un entier dans
// medical_record_id et une chaine dans medical_record_uuid : envoyer l'entier comme uuid donnait une 422.
export function resolveMedicalRecordLink(localValue, linkedServerId) {
    if (localValue === null || localValue === undefined || localValue === '' || localValue === 0) {
        return { serverId: null, uuid: null };
    }
    if (linkedServerId) return { serverId: linkedServerId, uuid: null };
    if (typeof localValue === 'number' || /^\d+$/.test(String(localValue))) {
        return { serverId: Number(localValue), uuid: null };
    }
    return { serverId: null, uuid: String(localValue) };
}
