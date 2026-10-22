// Logique pure (testee) de la resolution d'un patient refuse par le serveur : suppression de l'entree et
// correction du numero d'identite.

// Table locale de chaque type de ligne retenue en quarantaine. Liste fermee : jamais de nom de table construit
// a partir d'une valeur lue en base.
const TABLE_BY_KIND = {
    medical_record: 'medical_records',
    prescription: 'prescriptions',
    lab_result: 'lab_results',
    lab_result_detail: 'lab_result_details',
};

// Lignes locales a effacer avec le patient refuse : [{ table, id }]. Le patient lui-meme et ses entrees de
// quarantaine sont traites a part par l'appelant.
export function discardPlan(children) {
    if (!Array.isArray(children)) return [];
    return children
        .filter((c) => c && TABLE_BY_KIND[c.kind] && c.local_id)
        .map((c) => ({ table: TABLE_BY_KIND[c.kind], id: c.local_id }));
}

const normalize = (v) => String(v ?? '').trim().toUpperCase();

// Un numero vide ne corrige rien (pour retirer l'entree, il y a « supprimer ») ; un numero identique serait
// de nouveau refuse.
export function validateNationalIdCorrection(oldId, newId) {
    const next = normalize(newId);
    if (!next) return { ok: false, error: 'empty' };
    if (next === normalize(oldId)) return { ok: false, error: 'same' };
    return { ok: true };
}

// Corps de POST /patients/ pour renvoyer le patient : memes champs que l'envoi d'origine (connecteur
// d'envoi, cas patients:PUT), nouveau numero, MEME uuid : le serveur traite un rejeu du meme uuid sans doublon.
export function buildResendPayload(opData, newNationalId, uuid) {
    const d = opData || {};
    return {
        first_name: d.first_name,
        last_name: d.last_name,
        birth_date: d.birth_date,
        gender: d.gender || null,
        national_id: String(newNationalId ?? '').trim(),
        contact_phone: d.contact_phone || null,
        assurance: d.assurance || null,
        residence: d.residence || null,
        father_name: d.father_name || null,
        mother_name: d.mother_name || null,
        uuid,
    };
}
