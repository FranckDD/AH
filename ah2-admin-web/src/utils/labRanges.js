// Plage de reference a afficher pour un patient. Le serveur renvoie la plage retenue
// (`applicable_range`, calculee avec l'age, le sexe et la SA du dossier : celle qui a produit le drapeau
// enregistre). Hors ligne, `selectRange` reproduit EXACTEMENT la regle du serveur
// (utils/lab_reference.py::select_range) ; les deux sont verifies sur les memes cas
// (tests/fixtures/lab_range_cases.json).

const MALE = new Set(['m', 'male', 'homme', 'man', 'masculin', 'h']);
const FEMALE = new Set(['f', 'female', 'femme', 'woman', 'feminin', 'féminin']);

export function normalizeSex(raw) {
  const s = String(raw ?? '').trim().toLowerCase();
  if (MALE.has(s)) return 'M';
  if (FEMALE.has(s)) return 'F';
  return 'X';
}

const INF = Infinity;
const OPEN_UPPER_DAYS = 120 * 365;

const intOrNull = (v) => (v === null || v === undefined || v === '' ? null : Math.trunc(Number(v)));

// (min, max) en jours inclusifs, null = ouvert. Colonnes en jours si l'une est renseignee, sinon
// lecture heritee des annees entieres : [age_min*365, (age_max+1)*365-1].
export function ageBoundsDays(rr) {
  let lo = intOrNull(rr.age_min_days);
  let hi = intOrNull(rr.age_max_days);
  if (lo === null && hi === null) {
    const ymin = intOrNull(rr.age_min);
    const ymax = intOrNull(rr.age_max);
    lo = ymin === null ? null : ymin * 365;
    hi = ymax === null ? null : (ymax + 1) * 365 - 1;
  }
  if (lo !== null && lo <= 0) lo = null;
  if (hi !== null && hi >= OPEN_UPPER_DAYS) hi = null;
  return [lo, hi];
}

// Plage applicable : memes candidates et memes departages que le serveur (sexe, age en jours, SA ;
// le plus de criteres, puis l'intervalle d'age le plus etroit, puis la borne basse la plus haute,
// puis le plus petit id).
export function selectRange(ranges, sexCode, ageDays, gaWeeks = null) {
  const sex = sexCode === 'M' || sexCode === 'F' ? sexCode : 'X';
  const age = ageDays === undefined ? null : ageDays;
  const ga = gaWeeks === undefined ? null : gaWeeks;
  let bestKey = null;
  let best = null;
  for (const rr of ranges || []) {
    const rsex = String(rr.sexe || 'X').trim().toUpperCase();
    const sexSpecific = rsex === 'M' || rsex === 'F';
    if (sexSpecific && rsex !== sex) continue;
    const [lo, hi] = ageBoundsDays(rr);
    const hasAge = lo !== null || hi !== null;
    if (hasAge) {
      if (age === null) continue;
      if ((lo !== null && age < lo) || (hi !== null && age > hi)) continue;
    }
    const gmin = intOrNull(rr.ga_min_weeks);
    const gmax = intOrNull(rr.ga_max_weeks);
    const hasGa = gmin !== null || gmax !== null;
    if (hasGa) {
      if (ga === null) continue;
      if ((gmin !== null && ga < gmin) || (gmax !== null && ga > gmax)) continue;
    }
    const count = Number(sexSpecific) + Number(hasAge) + Number(hasGa);
    const width = (hi === null ? INF : hi) - (lo === null ? 0 : lo);
    const rid = rr.id === null || rr.id === undefined ? INF : rr.id;
    const key = [-count, width, -(lo === null ? 0 : lo), rid];
    let less = false;
    if (bestKey === null) {
      less = true;
    } else {
      for (let i = 0; i < key.length; i += 1) {
        if (key[i] < bestKey[i]) { less = true; break; }
        if (key[i] > bestKey[i]) break;
      }
    }
    if (less) { bestKey = key; best = rr; }
  }
  return best;
}

const fmt = (r) => `${r.min} - ${r.max}`;

// Texte de la colonne « valeurs de reference » d'un parametre. `detail.applicable_range` (cle presente,
// meme nulle) vient du serveur et fait foi ; sinon (lecture hors ligne) on applique selectRange aux
// plages locales avec l'age en jours et la SA du dossier.
export function rangeLabelForDetail(detail, sexe, ageDays = null, gaWeeks = null) {
  if (!detail) return '-';
  if (Object.prototype.hasOwnProperty.call(detail, 'applicable_range')) {
    const a = detail.applicable_range;
    return a ? (a.text || fmt(a)) : '-';
  }
  const picked = selectRange(detail.ranges || [], normalizeSex(sexe), ageDays, gaWeeks);
  return picked ? fmt(picked) : '-';
}
