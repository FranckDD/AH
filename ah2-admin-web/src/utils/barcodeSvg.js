import JsBarcode from 'jsbarcode';

// Code 128 en SVG, chiffres lisibles sous les barres. Renvoie le balisage SVG
// (viewBox, sans taille fixe) : il se met a l'echelle de son conteneur, a l'ecran comme a l'impression.
export function barcodeSvgMarkup(value, { height = 40, fontSize = 14 } = {}) {
    const text = String(value ?? '').trim();
    if (!text) return '';
    try {
        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        JsBarcode(svg, text, {
            format: 'CODE128',
            displayValue: true,
            height,
            width: 2,
            margin: 0,
            fontSize,
            textMargin: 2,
            background: '#ffffff',
            lineColor: '#000000',
        });
        const w = svg.getAttribute('width');
        const h = svg.getAttribute('height');
        if (w && h) {
            svg.setAttribute('viewBox', `0 0 ${parseFloat(w)} ${parseFloat(h)}`);
            svg.removeAttribute('width');
            svg.removeAttribute('height');
        }
        svg.removeAttribute('style');
        svg.setAttribute('preserveAspectRatio', 'xMidYMid meet');
        svg.setAttribute('role', 'img');
        svg.setAttribute('aria-label', text);
        return svg.outerHTML;
    } catch {
        return '';
    }
}
