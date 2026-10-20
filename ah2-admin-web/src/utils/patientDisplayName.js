// Nom d'affichage d'une facture hors ligne : patient enregistre (ligne de
// patients_lookup) > patient_label libre > null. Meme regle que le serveur
// (utils/patient_display.py).
export function resolvePatientName(row, lookup) {
    if (lookup) {
        const name = [lookup.first_name, lookup.last_name]
            .map((p) => String(p || '').trim())
            .filter(Boolean)
            .join(' ');
        if (name) return name;
    }
    const label = String(row?.patient_label || '').trim();
    return label || null;
}
