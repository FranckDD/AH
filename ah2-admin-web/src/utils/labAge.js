// Age exact pour le laboratoire : port JavaScript FIDELE de utils/lab_age.py (meme arrondi, memes bornes).
// Les deux sont verifies contre tests/fixtures/lab_age_cases.json (test pytest et test node).
// Dates en chaines ISO AAAA-MM-JJ (jour calendaire, sans heure ni fuseau).

export const MONTH_DAYS = 30.4375;
export const YEAR_DAYS = 365.25;
export const MAX_YEARS = 130;
export const MAX_DAYS = 47500;
export const AGE_UNITS = ['jours', 'semaines', 'mois', 'ans'];

const UNIT_FACTORS = { jours: 1, semaines: 7, mois: MONTH_DAYS, ans: YEAR_DAYS };

// Arrondi au plus proche, moitie vers le pair (comme round() de Python).
function roundHalfEven(x) {
  const f = Math.floor(x);
  const diff = x - f;
  if (diff < 0.5) return f;
  if (diff > 0.5) return f + 1;
  return f % 2 === 0 ? f : f + 1;
}

function isoToDayNumber(iso) {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(iso || ''));
  if (!m) return null;
  const t = Date.UTC(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
  const d = new Date(t);
  if (d.getUTCFullYear() !== Number(m[1]) || d.getUTCMonth() !== Number(m[2]) - 1 || d.getUTCDate() !== Number(m[3])) return null;
  return Math.round(t / 86400000);
}

// Age en jours entre une naissance et une date de reference. Leve une erreur si la naissance suit la reference.
export function ageInDays(birthIso, refIso) {
  const b = isoToDayNumber(birthIso);
  const r = isoToDayNumber(refIso);
  if (b === null || r === null) throw new Error('invalid date');
  if (b > r) throw new Error('birth date is after reference date');
  return r - b;
}

function plural(n, singular, pluralForm) {
  return `${n} ${n === 1 ? singular : pluralForm}`;
}

function monthStart(k) {
  return Math.floor(k * MONTH_DAYS);
}

function fullMonths(days) {
  let k = Math.trunc(days / MONTH_DAYS);
  while (monthStart(k + 1) <= days) k += 1;
  while (k > 0 && monthStart(k) > days) k -= 1;
  return k;
}

export function formatAge(days) {
  if (!Number.isInteger(days) || days < 0) throw new Error('days must be an integer >= 0');
  if (days < 7) return days <= 1 ? `${days} jour` : `${days} jours`;
  if (days < 30) {
    const weeks = Math.floor(days / 7);
    const rest = days % 7;
    let out = plural(weeks, 'semaine', 'semaines');
    if (rest) out += ' ' + plural(rest, 'jour', 'jours');
    return out;
  }
  if (days < 365) {
    const k = fullMonths(days);
    const weeks = Math.floor((days - monthStart(k)) / 7);
    let out = `${k} mois`;
    if (weeks >= 1) out += ' ' + plural(weeks, 'semaine', 'semaines');
    return out;
  }
  if (days < 1826) {
    const k = fullMonths(days);
    const years = Math.floor(k / 12);
    const months = k % 12;
    let out = plural(years, 'an', 'ans');
    if (months) out += ` ${months} mois`;
    return out;
  }
  return `${Math.max(5, Math.trunc(days / YEAR_DAYS))} ans`;
}

// Age saisi (nombre + unite) -> jours. Leve une erreur si la valeur ou l'unite est invalide.
export function ageFromExternal(value, unit) {
  if (typeof value !== 'number' || !Number.isInteger(value)) throw new Error('value must be an integer');
  if (value < 0) throw new Error('value must be >= 0');
  const factor = UNIT_FACTORS[unit];
  if (factor === undefined) throw new Error(`unknown unit: ${unit}`);
  if (unit === 'ans' && value > MAX_YEARS) throw new Error('age too large');
  const days = unit === 'jours' ? value : roundHalfEven(factor * value);
  if (days > MAX_DAYS) throw new Error('age too large');
  return days;
}

// Versions tolerantes pour l'ecran : renvoient null au lieu de lever.
export function tryAgeFromExternal(value, unit) {
  try {
    return ageFromExternal(value, unit);
  } catch {
    return null;
  }
}

export function tryAgeInDays(birthIso, refIso) {
  try {
    return ageInDays(birthIso, refIso);
  } catch {
    return null;
  }
}

// Libelle exact de l'age d'un patient dont on connait la date de naissance (vide si inconnue ou future).
export function ageLabelFromBirth(birthIso, refIso) {
  const d = tryAgeInDays(birthIso, refIso);
  return d === null ? '' : formatAge(d);
}

// Semaines d'amenorrhee proposees depuis la date presumee d'accouchement :
// SA = 40 - floor((DPA - date de reference) / 7), bornee a 0..45 (la valeur reste modifiable).
// null si la DPA est hors de la fenetre [-4 semaines, +46 semaines] autour de la reference (miroir de lab_age.py).
export function gestationalFromDpa(dpaIso, refIso) {
  const d = isoToDayNumber(dpaIso);
  const r = isoToDayNumber(refIso);
  if (d === null || r === null) return null;
  const delta = d - r;
  if (delta < -28 || delta > 46 * 7) return null;
  return Math.max(0, Math.min(45, 40 - Math.floor(delta / 7)));
}

// Jour calendaire local de l'appareil en AAAA-MM-JJ.
export function localTodayIso(now = new Date()) {
  const p = (n) => String(n).padStart(2, '0');
  return `${now.getFullYear()}-${p(now.getMonth() + 1)}-${p(now.getDate())}`;
}
