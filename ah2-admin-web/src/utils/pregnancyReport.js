// Aides pures de l'ecran "Rapport de suivi de grossesse" (promoteur et admin). Miroir des regles du serveur
// (api_backend/backend_app/routes/labo/pregnancy_report_endpoints.py) : dates AAAA-MM-JJ, debut <= fin, 366 jours au plus.

export const MAX_RANGE_DAYS = 366;

function dayNumber(iso) {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(iso || ''));
  if (!m) return null;
  const t = Date.UTC(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
  const d = new Date(t);
  if (d.getUTCFullYear() !== Number(m[1]) || d.getUTCMonth() !== Number(m[2]) - 1 || d.getUTCDate() !== Number(m[3])) return null;
  return Math.round(t / 86400000);
}

// Periode par defaut : du premier du mois a aujourd'hui.
export function defaultPeriod(todayIso) {
  return { from: `${String(todayIso).slice(0, 8)}01`, to: todayIso };
}

// null si la periode est valable, sinon 'invalid' | 'order' | 'range'.
export function periodError(from, to) {
  const a = dayNumber(from);
  const b = dayNumber(to);
  if (a === null || b === null) return 'invalid';
  if (b < a) return 'order';
  if (b - a + 1 > MAX_RANGE_DAYS) return 'range';
  return null;
}

export function reportParams(from, to) {
  return { from, to };
}

export function frDate(iso) {
  return iso ? String(iso).slice(0, 10).split('-').reverse().join('/') : '';
}
