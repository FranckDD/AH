// Scan code-barres a la caisse : parties pures (aucun import Vue), testees
// sous node:test. Une douchette tape les chiffres puis Entree.

// Retire espaces et fins de ligne ; renvoie la chaine si 1 a 12 chiffres, sinon null.
export function normalizeScan(raw) {
    const c = String(raw == null ? '' : raw).replace(/[\r\n]+$/g, '').trim();
    return /^\d{1,12}$/.test(c) ? c : null;
}

// Ajoute le produit scanne aux lignes. Si une ligne Pharmacie a deja ce
// refId, sa quantite augmente de 1 (premiere ligne trouvee, meme si la
// quantite a ete tapee a la main) ; sinon une ligne est creee, remplie comme
// selectProductLine. `lines` est le tableau (reactif ou non) des lignes.
export function applyScanToLines(lines, product, makeLine) {
    const existing = lines.find((l) => l.itemType === 'Médicament' && l.refId === product.medication_id);
    if (existing) {
        existing.quantity = (Number(existing.quantity) || 0) + 1;
        return { line: existing, created: false };
    }
    const base = {
        key: lines.reduce((m, l) => Math.max(m, Number(l.key) || 0), 0) + 1,
        itemType: 'Médicament',
        refId: product.medication_id,
        refLabel: product.drug_name,
        label: '',
        searchQuery: '',
        searchResults: [],
        quantity: 1,
        unitPrice: Number(product.price) || 0,
        knownStock: product.quantity != null ? Number(product.quantity) : null,
        catalogLine: true,
    };
    const line = makeLine ? makeLine(base) : base;
    lines.push(line);
    return { line, created: true };
}

// Chiffre tape hors de tout champ (curseur sur le fond de la fenetre) : il
// vient tres probablement de la douchette, donc on le redirige vers le champ
// de scan. Jamais dans un champ de saisie, un bouton, une liste ou avec un modificateur.
export function shouldRedirectToScan(ev) {
    if (!ev || typeof ev.key !== 'string' || !/^\d$/.test(ev.key)) return false;
    if (ev.ctrlKey || ev.metaKey || ev.altKey) return false;
    const tag = String(ev.target?.tagName || '').toLowerCase();
    if (['input', 'textarea', 'select', 'button'].includes(tag)) return false;
    if (ev.target?.isContentEditable) return false;
    return true;
}
