// Conversion d'un produit de l'ecran vers le corps attendu par l'API pharmacie (fonction pure, testee).

// Le champ « Dosage » est libre ("500mg", "2,5") : l'API stocke un nombre (dosage_mg). Rien d'exploitable -> null.
export function parseDosageMg(raw) {
    if (raw === null || raw === undefined || raw === '') return null;
    const n = parseFloat(String(raw).replace(',', '.'));
    return Number.isFinite(n) && n >= 0 ? n : null;
}

export function mapProductToApi(p) {
    let typeDb = 'Autre';
    if (p.category === 'PHARMA') typeDb = 'pharmaceutique';
    else if (p.category === 'NATUREL') typeDb = 'Naturel';
    else if (p.category === 'MATERIEL') typeDb = 'Materiel';

    return {
        drug_name: p.name,
        medication_type: typeDb,
        quantity: parseInt(p.quantity),
        threshold: parseInt(p.minThreshold),
        price: parseFloat(p.price),
        // Une chaine vide n'est pas une date : l'API la refusait avec un objet d'erreur illisible.
        expiry_date: p.expiryDate ? p.expiryDate : null,
        forme: p.forme || 'Autre',
        dosage_mg: parseDosageMg(p.dosage)
    };
}
