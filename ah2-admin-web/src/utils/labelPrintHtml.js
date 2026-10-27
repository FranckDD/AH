// Balisage HTML des pages d'etiquettes (apercu et impression partagent le meme rendu).
// Aucune dependance Vue/DOM : le rendu du code-barres est injecte (renderBarcode(code) -> markup SVG).

const escapeHtml = (v) => String(v ?? '')
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

const mm = (n) => `${Math.round(n * 1000) / 1000}mm`;

export function labelPagesCss(pages, { preview = false } = {}) {
    const first = pages[0];
    const pageRule = first && first.mode === 'roll'
        ? `@page { size: ${mm(first.widthMm)} ${mm(first.heightMm)}; margin: 0; }`
        : '@page { size: A4 portrait; margin: 0; }';
    // En apercu (dans la page de l'application) on n'emet que les regles propres aux etiquettes.
    const docRules = preview ? '' : `${pageRule}
html, body { margin: 0; padding: 0; background: #fff; }
* { box-sizing: border-box; }
`;
    return `${docRules}.lbl-page { position: relative; overflow: hidden; background: #fff; page-break-after: always; break-after: page; }
.lbl-page:last-child { page-break-after: auto; break-after: auto; }
.lbl, .lbl * { box-sizing: border-box; }
.lbl { position: absolute; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 0.6mm; padding: 1.2mm; overflow: hidden; font-family: Arial, Helvetica, sans-serif; color: #000; }
.lbl.cut { border: 0.15mm dashed #888; }
.lbl-name { width: 100%; text-align: center; font-size: 8pt; font-weight: 700; line-height: 1.1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; flex: 0 0 auto; }
.lbl-code { width: 100%; flex: 1 1 auto; min-height: 0; display: flex; align-items: center; justify-content: center; }
.lbl-code svg { width: 100%; height: 100%; max-height: 100%; }`;
}

export function labelPagesBody(pages, renderBarcode) {
    return pages.map((p) => {
        const cut = p.mode === 'a4' ? ' cut' : '';
        const labels = p.labels.map((l) => (
            `<div class="lbl${cut}" style="left:${mm(l.xMm)};top:${mm(l.yMm)};width:${mm(p.labelWidthMm)};height:${mm(p.labelHeightMm)}">`
            + `<div class="lbl-name">${escapeHtml(l.name)}</div>`
            + `<div class="lbl-code">${renderBarcode(l.barcode)}</div></div>`
        )).join('');
        return `<div class="lbl-page" style="width:${mm(p.widthMm)};height:${mm(p.heightMm)}">${labels}</div>`;
    }).join('');
}

export function labelPrintDocument(pages, renderBarcode) {
    return `<!doctype html><html><head><meta charset="utf-8"><title>Labels</title><style>${labelPagesCss(pages)}</style></head><body>${labelPagesBody(pages, renderBarcode)}</body></html>`;
}
