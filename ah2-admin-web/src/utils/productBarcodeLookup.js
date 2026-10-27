// Recherche d'un produit par code-barres : parties pures, testees sous
// node:test. Les dependances (api, db, garde de role) sont injectees par
// CaisseGateway pour que ce module reste importable sans alias '@/'.

// Entree : espaces retires ; vide ou non numerique -> null (aucune requete).
export function normalizeBarcode(code) {
    const c = String(code == null ? '' : code).trim();
    return /^\d+$/.test(c) ? c : null;
}

// Ligne locale pharmacy_stock -> meme forme que le produit serveur.
export function mapStockRowToProduct(r) {
    return {
        medication_id: r.server_id,
        drug_name: r.drug_name,
        quantity: r.quantity,
        price: Number(r.price),
        forme: r.forme,
        dosage_mg: r.dosage_mg === null || r.dosage_mg === undefined || r.dosage_mg === ''
            ? null
            : Number(r.dosage_mg),
        barcode: r.barcode,
        has_photo: Number(r.has_photo) === 1,
        photo_version: Number(r.photo_version) || 0,
    };
}

// deps : { get(path) -> Promise<{data}>, getAll(sql, params), canFallback() }
export async function lookupProductByBarcode(code, deps) {
    const clean = normalizeBarcode(code);
    if (!clean) return { data: null };
    try {
        const resp = await deps.get(`/pharmacy/by-barcode/${encodeURIComponent(clean)}`);
        return { data: resp.data };
    } catch (err) {
        if (err && err.response && err.response.status === 404) return { data: null };
        if (err && !err.response && deps.canFallback()) {
            const rows = await deps.getAll(
                'SELECT * FROM pharmacy_stock WHERE barcode = ? LIMIT 1',
                [clean]
            );
            return { data: rows.length ? mapStockRowToProduct(rows[0]) : null };
        }
        throw err;
    }
}
