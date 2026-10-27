// Mise en page des etiquettes de codes-barres (fonction pure, sans Vue ni DOM).
// Mode 'roll' : une page par etiquette, a la taille exacte de l'etiquette.
// Mode 'a4'   : grille sur une feuille A4 portrait avec une marge de decoupe ;
//               les etiquettes qui ne tiennent plus passent a la page suivante.

export const A4_WIDTH_MM = 210;
export const A4_HEIGHT_MM = 297;
export const A4_MARGIN_MM = 5;
export const MIN_LABEL_MM = 20;
export const MAX_LABEL_MM = 120;
export const MAX_NAME_LENGTH = 28;
export const MAX_COPIES = 200;

export function truncateName(name, max = MAX_NAME_LENGTH) {
    const text = String(name ?? '').trim();
    if (text.length <= max) return text;
    return text.slice(0, max - 3).trimEnd() + '...';
}

function checkSize(size) {
    const w = size && size.widthMm;
    const h = size && size.heightMm;
    for (const v of [w, h]) {
        if (typeof v !== 'number' || !Number.isFinite(v) || v < MIN_LABEL_MM || v > MAX_LABEL_MM) {
            throw new Error(`Invalid label size: width and height must be numbers between ${MIN_LABEL_MM} and ${MAX_LABEL_MM} mm.`);
        }
    }
    return { widthMm: w, heightMm: h };
}

function expand(items) {
    if (!Array.isArray(items)) throw new Error('Label items must be a list.');
    const labels = [];
    items.forEach((item, idx) => {
        const copies = item ? item.copies : undefined;
        if (typeof copies !== 'number' || !Number.isInteger(copies) || copies < 1) {
            throw new Error(`Invalid number of copies for item ${idx + 1}: a positive whole number is required.`);
        }
        const barcode = item.barcode == null ? '' : String(item.barcode).trim();
        if (!barcode) throw new Error(`Item ${idx + 1} has no barcode.`);
        const name = truncateName(item.name);
        for (let i = 0; i < copies; i += 1) labels.push({ name, barcode });
    });
    return labels;
}

// Page : { mode, widthMm, heightMm, labelWidthMm, labelHeightMm, labels: [{ name, barcode, xMm, yMm }] }
export function buildLabelPages(items, size, mode) {
    const { widthMm, heightMm } = checkSize(size);
    if (mode !== 'roll' && mode !== 'a4') throw new Error("Invalid print mode: use 'roll' or 'a4'.");
    const labels = expand(items);

    if (mode === 'roll') {
        return labels.map((l) => ({
            mode: 'roll',
            widthMm,
            heightMm,
            labelWidthMm: widthMm,
            labelHeightMm: heightMm,
            labels: [{ ...l, xMm: 0, yMm: 0 }],
        }));
    }

    const cols = Math.floor((A4_WIDTH_MM - 2 * A4_MARGIN_MM) / widthMm);
    const rows = Math.floor((A4_HEIGHT_MM - 2 * A4_MARGIN_MM) / heightMm);
    const perPage = Math.max(1, cols) * Math.max(1, rows);
    // Centre la grille dans la feuille pour garder des marges egales.
    const gridW = Math.max(1, cols) * widthMm;
    const gridH = Math.max(1, rows) * heightMm;
    const offsetX = Math.max(A4_MARGIN_MM, (A4_WIDTH_MM - gridW) / 2);
    const offsetY = Math.max(A4_MARGIN_MM, (A4_HEIGHT_MM - gridH) / 2);
    const pages = [];
    for (let start = 0; start < labels.length; start += perPage) {
        const chunk = labels.slice(start, start + perPage);
        pages.push({
            mode: 'a4',
            widthMm: A4_WIDTH_MM,
            heightMm: A4_HEIGHT_MM,
            labelWidthMm: widthMm,
            labelHeightMm: heightMm,
            columns: Math.max(1, cols),
            rows: Math.max(1, rows),
            labels: chunk.map((l, i) => ({
                ...l,
                xMm: offsetX + (i % Math.max(1, cols)) * widthMm,
                yMm: offsetY + Math.floor(i / Math.max(1, cols)) * heightMm,
            })),
        });
    }
    return pages;
}
