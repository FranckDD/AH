// Refus du serveur sur une ligne de reception : le serveur renvoie un code stable, la ligne et des parametres ;
// l'ecran traduit le code et nomme la ligne par son produit (jamais par un identifiant interne).
// Renvoie '' quand l'erreur n'est pas de cette forme (l'appelant garde alors son repli).
export function describeStockLineError(err, lines, t, te) {
    const d = err?.response?.data?.detail;
    if (!d || typeof d !== 'object' || Array.isArray(d) || !d.code) return '';
    const key = `stockOps.server_err.${d.code}`;
    const params = { ...(d.params || {}) };
    if (params.field && te(`stockOps.${params.field}`)) params.field = t(`stockOps.${params.field}`);
    const msg = te(key) ? t(key, params) : (d.message || '');
    const line = (lines || []).find((l) => l.id === d.line_id);
    return line && line.product_name ? `${line.product_name} : ${msg}` : msg;
}
