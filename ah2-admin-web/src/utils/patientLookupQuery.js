// Recherche patient hors ligne de la caisse (secretaire) sur la table
// locale patients_lookup - fonctions pures, testees sous node:test.
// Pas de filtre is_deleted : le stream patients_lookup filtre deja.
export function buildPatientLookupQuery(query) {
    const term = String(query || '').trim().toLowerCase().replace(/[\\%_]/g, (c) => `\\${c}`);
    const pattern = `%${term}%`;
    const sql =
        "SELECT * FROM patients_lookup WHERE LOWER(first_name) LIKE ? ESCAPE '\\' " +
        "OR LOWER(last_name) LIKE ? ESCAPE '\\' OR LOWER(code_patient) LIKE ? ESCAPE '\\' " +
        'ORDER BY last_name, first_name LIMIT 8';
    return { sql, params: [pattern, pattern, pattern] };
}

// Meme forme que GET /patients/ (CaisseInvoiceModal lit is_staff === true ;
// is_staff === null = statut inconnu, facturation bloquee).
export function mapLookupRow(r) {
    return {
        patient_id: r.patient_id,
        code_patient: r.code_patient,
        first_name: r.first_name,
        last_name: r.last_name,
        // NULL = statut pas encore replique (inconnu), distinct de 0 (pas personnel).
        is_staff: r.is_staff == null ? null : Number(r.is_staff) === 1,
    };
}
