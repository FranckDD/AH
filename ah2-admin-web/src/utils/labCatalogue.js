// Aides pures de l'ecran de gestion du catalogue du laboratoire (testees dans tests/labCatalogue.test.mjs).
// Les regles miroir celles du serveur (lab_catalogue_schemas.py, controller/lab_catalogue_controller.py) ;
// le serveur reste juge. Les fonctions renvoient des CLES i18n (labCatalogue.errors.*), jamais du texte.
import { AGE_UNITS, MAX_DAYS, ageFromExternal } from './labAge.js';

export const LAYOUT_FAMILIES = ['table', 'three_columns', 'label_value', 'narrative', 'boxed'];
export const RESULT_KINDS = ['numeric', 'text', 'choice', 'pos_neg'];
export const SEXES = ['M', 'F', 'X'];
export const GA_MAX = 45;
export const CODE_PATTERN = /^[A-Z0-9_-]+$/;
export const NOTE_POSITIONS = ['before_body', 'after_body', 'after_conclusion'];
export const NOTE_STYLES = ['normal', 'bold', 'italic'];
export { AGE_UNITS };

const LIMITS = { code: 20, nom: 200, categorie: 100, section: 120, print_title: 200, method: 1000, signature_label: 200,
    nom_parametre: 200, unite: 40, print_label: 200, choice: 60, choices: 30, sort_order: 100000,
    group_label: 80, norm_text: 200, display_text: 60, note_text: 1000, notes: 12 };
export const CATALOGUE_LIMITS = LIMITS;

const E = (k) => `labCatalogue.errors.${k}`;
const trimmed = (v) => (v === null || v === undefined ? '' : String(v).trim());

// Caractere de controle (le serveur les refuse : le NUL fait echouer la base). Le retour a la ligne est permis
// dans le texte d'une note fixe seulement.
export function hasControlChars(text, allowNewline = false) {
    for (const ch of String(text ?? '')) {
        const c = ch.charCodeAt(0);
        if (c < 32 && !(allowNewline && (c === 10 || c === 13 || c === 9))) return true;
    }
    return false;
}

// ---------------------------------------------------------------- notes fixes de la fiche (examens.fixed_notes)
export const blankNote = () => ({ position: 'after_body', style: 'normal', text: '' });

// Erreur d'une note : cle i18n ou null.
export function validateNote(note) {
    if (!NOTE_POSITIONS.includes(note?.position)) return E('note_position_invalid');
    if (!NOTE_STYLES.includes(note?.style)) return E('note_style_invalid');
    const text = trimmed(note?.text);
    if (!text) return E('note_text_required');
    if (text.length > LIMITS.note_text) return E('too_long');
    if (hasControlChars(text, true)) return E('control_chars');
    return null;
}

// Liste de notes : { items: [cle|null par note], list: cle|null }.
export function validateNotes(notes) {
    const list = Array.isArray(notes) ? notes : [];
    return {
        items: list.map(validateNote),
        list: list.length > LIMITS.notes ? E('notes_too_many') : null,
    };
}

// Charge utile : liste ordonnee de { position, text, style } (texte rogne) ; liste vide = aucune note.
export function notesPayload(notes) {
    return (Array.isArray(notes) ? notes : []).map((n) => ({ position: n.position, text: trimmed(n.text), style: n.style || 'normal' }));
}

// Copie de travail des notes d'un examen du serveur.
export function notesFromExam(exam) {
    return (exam?.fixed_notes || []).map((n) => ({ position: n.position, style: n.style || 'normal', text: n.text || '' }));
}

// ---------------------------------------------------------------- age : unite <-> jours
// Memes regles que utils/lab_age.py::age_from_external (jours exacts, semaines x 7, mois 30.4375 et annees 365.25
// arrondis au plus proche, moitie vers le pair). Renvoie null si la valeur n'est pas un entier >= 0 ou si l'age
// depasse la limite (47500 jours).
export function toDays(value, unit) {
    if (value === '' || value === null || value === undefined) return null;
    const n = typeof value === 'number' ? value : Number(String(value).trim().replace(',', '.'));
    if (!Number.isInteger(n)) return null;
    try {
        return ageFromExternal(n, unit);
    } catch {
        return null;
    }
}

// Jours -> { value, unit } avec la plus grande unite qui redonne EXACTEMENT ce nombre de jours (ans, mois, semaines,
// sinon jours). Nul si days n'est pas un entier >= 0. 0 jour reste 0 jours.
export function fromDays(days) {
    if (days === null || days === undefined || days === '' || !Number.isInteger(Number(days)) || Number(days) < 0) return null;
    const d = Number(days);
    if (d === 0) return { value: 0, unit: 'jours' };
    for (const unit of ['ans', 'mois', 'semaines']) {
        const approx = unit === 'ans' ? 365.25 : unit === 'mois' ? 30.4375 : 7;
        const guess = Math.round(d / approx);
        for (const v of [guess, guess - 1, guess + 1]) {
            if (v >= 1 && toDays(v, unit) === d) return { value: v, unit };
        }
    }
    return { value: d, unit: 'jours' };
}

// Libelle d'une borne d'age en jours pour l'affichage (« 4 semaines », « 29 jours »...), via la cle d'unite.
export function ageBoundLabel(days, t) {
    const f = fromDays(days);
    if (!f) return '';
    return `${f.value} ${t(`labCatalogue.units.${f.unit}`)}`;
}

// ---------------------------------------------------------------- plages
const num = (v) => {
    if (v === null || v === undefined || v === '') return null;
    const n = typeof v === 'number' ? v : Number(String(v).trim().replace(',', '.'));
    return Number.isFinite(n) ? n : NaN;
};
const intOrNull = (v) => (v === null || v === undefined || v === '' ? null : Number(v));

// Normalise une plage du formulaire ou du serveur en { sexe, age_min_days, ... } (nombres ou null).
export function normalizeRange(r) {
    return {
        sexe: String(r?.sexe || '').toUpperCase(),
        age_min_days: intOrNull(r?.age_min_days),
        age_max_days: intOrNull(r?.age_max_days),
        ga_min_weeks: intOrNull(r?.ga_min_weeks),
        ga_max_weeks: intOrNull(r?.ga_max_weeks),
        valeur_min: num(r?.valeur_min),
        valeur_max: num(r?.valeur_max),
        display_text: trimmed(r?.display_text),
    };
}

const sameCriteria = (a, b) => a.sexe === b.sexe && a.age_min_days === b.age_min_days && a.age_max_days === b.age_max_days
    && a.ga_min_weeks === b.ga_min_weeks && a.ga_max_weeks === b.ga_max_weeks;

const interval = (lo, hi) => [lo === null ? -Infinity : lo, hi === null ? Infinity : hi];
const overlaps = (aLo, aHi, bLo, bHi) => {
    const [a1, a2] = interval(aLo, aHi);
    const [b1, b2] = interval(bLo, bHi);
    return a1 <= b2 && b1 <= a2;
};
const criteriaKind = (r) => `${r.sexe === 'X' ? 0 : 1}${r.age_min_days !== null || r.age_max_days !== null ? 1 : 0}${r.ga_min_weeks !== null || r.ga_max_weeks !== null ? 1 : 0}`;

// Valide une plage. `others` = les autres plages du meme parametre (sans celle qu'on modifie).
// Renvoie { errors: [cles], warnings: [cles] }.
//  erreurs : sexe, valeurs manquantes ou non numeriques, min > max, age min > age max, age hors limites,
//            SA hors 0..45 ou min > max, doublon exact (memes criteres et memes valeurs, comme le serveur).
//  avertissement : deux plages du meme sexe dont les ages ET les SA se chevauchent avec les memes criteres
//            renseignes (le serveur departage, mais le resultat est ambigu pour la lectrice).
export function validateRange(range, others = []) {
    const r = normalizeRange(range);
    const errors = [];
    const warnings = [];
    if (!SEXES.includes(r.sexe)) errors.push(E('range_sex'));
    if (r.valeur_min === null || r.valeur_max === null) errors.push(E('range_values_required'));
    else if (Number.isNaN(r.valeur_min) || Number.isNaN(r.valeur_max)) errors.push(E('range_values_number'));
    else if (r.valeur_min > r.valeur_max) errors.push(E('range_min_gt_max'));

    for (const v of [r.age_min_days, r.age_max_days]) {
        if (v !== null && (!Number.isInteger(v) || v < 0 || v > MAX_DAYS)) { errors.push(E('range_age_bounds')); break; }
    }
    if (r.age_min_days !== null && r.age_max_days !== null && r.age_min_days > r.age_max_days) errors.push(E('range_age_order'));
    for (const v of [r.ga_min_weeks, r.ga_max_weeks]) {
        if (v !== null && (!Number.isInteger(v) || v < 0 || v > GA_MAX)) { errors.push(E('range_ga_bounds')); break; }
    }
    if (r.ga_min_weeks !== null && r.ga_max_weeks !== null && r.ga_min_weeks > r.ga_max_weeks) errors.push(E('range_ga_order'));
    if (r.display_text.length > LIMITS.display_text) errors.push(E('too_long'));
    else if (hasControlChars(r.display_text)) errors.push(E('control_chars'));

    if (errors.length === 0) {
        for (const o of others.map(normalizeRange)) {
            if (sameCriteria(r, o) && o.valeur_min === r.valeur_min && o.valeur_max === r.valeur_max) {
                errors.push(E('range_duplicate'));
                break;
            }
        }
    }
    if (errors.length === 0) {
        for (const o of others.map(normalizeRange)) {
            if (o.sexe === r.sexe && criteriaKind(o) === criteriaKind(r)
                && overlaps(r.age_min_days, r.age_max_days, o.age_min_days, o.age_max_days)
                && overlaps(r.ga_min_weeks, r.ga_max_weeks, o.ga_min_weeks, o.ga_max_weeks)) {
                warnings.push(E('range_overlap'));
                break;
            }
        }
    }
    return { errors: [...new Set(errors)], warnings };
}

// Charge utile d'ecriture d'une plage (jamais de prix) : ages en jours deja convertis, nombres JSON.
export function rangePayload(range) {
    const r = normalizeRange(range);
    return {
        sexe: r.sexe,
        age_min_days: r.age_min_days,
        age_max_days: r.age_max_days,
        ga_min_weeks: r.ga_min_weeks,
        ga_max_weeks: r.ga_max_weeks,
        valeur_min: r.valeur_min,
        valeur_max: r.valeur_max,
        display_text: r.display_text || null,
    };
}

// ---------------------------------------------------------------- examens

export function validateExam(form, { isNew = false } = {}) {
    const errors = {};
    if (isNew) {
        const code = trimmed(form?.code).toUpperCase();
        if (!code) errors.code = E('code_required');
        else if (code.length > LIMITS.code || !CODE_PATTERN.test(code)) errors.code = E('code_format');
    }
    const nom = trimmed(form?.nom);
    if (!nom) errors.nom = E('name_required');
    else if (nom.length > LIMITS.nom) errors.nom = E('too_long');
    const cat = trimmed(form?.categorie);
    if (!cat) errors.categorie = E('category_required');
    else if (cat.length > LIMITS.categorie) errors.categorie = E('too_long');
    for (const k of ['section', 'print_title', 'method', 'signature_label']) {
        if (trimmed(form?.[k]).length > LIMITS[k]) errors[k] = E('too_long');
    }
    if (!LAYOUT_FAMILIES.includes(form?.layout_family)) errors.layout_family = E('family_invalid');
    const noteVerdict = validateNotes(form?.fixed_notes);
    if (noteVerdict.list) errors.fixed_notes = noteVerdict.list;
    else if (noteVerdict.items.some(Boolean)) errors.fixed_notes = noteVerdict.items.find(Boolean);
    const so = form?.sort_order;
    if (so !== '' && so !== null && so !== undefined) {
        const n = Number(so);
        if (!Number.isInteger(n) || n < 0 || n > LIMITS.sort_order) errors.sort_order = E('sort_order_invalid');
    }
    return errors;
}

// Charge utile d'un examen : AUCUN champ de prix. Le code n'est envoye qu'a la creation.
export function examPayload(form, { isNew = false } = {}) {
    const out = {
        nom: trimmed(form.nom),
        categorie: trimmed(form.categorie),
        section: trimmed(form.section) || null,
        print_title: trimmed(form.print_title) || null,
        method: trimmed(form.method) || null,
        layout_family: form.layout_family,
        signature_label: trimmed(form.signature_label) || null,
        sort_order: form.sort_order === '' || form.sort_order === null || form.sort_order === undefined ? 0 : Number(form.sort_order),
        is_active: !!form.is_active,
        fixed_notes: notesPayload(form.fixed_notes),
    };
    if (isNew) out.code = trimmed(form.code).toUpperCase();
    return out;
}

// ---------------------------------------------------------------- parametres
// Liste de choix saisie en texte (un choix par ligne ou separes par une virgule/point-virgule) -> liste propre.
export function parseChoices(text) {
    return String(text ?? '').split(/[\n;,]/).map((c) => c.trim()).filter(Boolean);
}

export function validateParam(form) {
    const errors = {};
    const nom = trimmed(form?.nom_parametre);
    if (!nom) errors.nom_parametre = E('param_name_required');
    else if (nom.length > LIMITS.nom_parametre) errors.nom_parametre = E('too_long');
    if (trimmed(form?.unite).length > LIMITS.unite) errors.unite = E('too_long');
    if (trimmed(form?.print_label).length > LIMITS.print_label) errors.print_label = E('too_long');
    if (trimmed(form?.group_label).length > LIMITS.group_label) errors.group_label = E('too_long');
    else if (hasControlChars(form?.group_label)) errors.group_label = E('control_chars');
    if (trimmed(form?.norm_text).length > LIMITS.norm_text) errors.norm_text = E('too_long');
    else if (hasControlChars(form?.norm_text)) errors.norm_text = E('control_chars');
    if (!RESULT_KINDS.includes(form?.result_kind)) errors.result_kind = E('kind_invalid');
    if (form?.result_kind === 'choice') {
        const list = Array.isArray(form.choices) ? form.choices.map(trimmed) : parseChoices(form.choices_text);
        if (list.length === 0) errors.choices = E('choices_required');
        else if (list.length > LIMITS.choices) errors.choices = E('choices_too_many');
        else if (list.some((c) => !c || c.length > LIMITS.choice || c.includes(','))) errors.choices = E('choices_invalid');
        else if (new Set(list).size !== list.length) errors.choices = E('choices_duplicate');
    }
    return errors;
}

export function paramPayload(form) {
    const out = {
        nom_parametre: trimmed(form.nom_parametre),
        unite: trimmed(form.unite),
        print_label: trimmed(form.print_label) || null,
        group_label: trimmed(form.group_label) || null,
        norm_text: trimmed(form.norm_text) || null,
        result_kind: form.result_kind,
        is_active: form.is_active !== false,
    };
    if (form.result_kind === 'choice') out.choices = Array.isArray(form.choices) ? form.choices.map(trimmed) : parseChoices(form.choices_text);
    return out;
}

// ---------------------------------------------------------------- ordre
// Nouvel ordre des ids apres avoir deplace l'element `index` de `delta` (-1 haut, +1 bas). null si impossible.
export function moveInList(ids, index, delta) {
    const to = index + delta;
    if (!Array.isArray(ids) || index < 0 || index >= ids.length || to < 0 || to >= ids.length) return null;
    const out = ids.slice();
    [out[index], out[to]] = [out[to], out[index]];
    return out;
}

// ---------------------------------------------------------------- liste groupee par section
export function normalizeText(s) {
    return String(s ?? '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
}

// Examens groupes par section, dans l'ordre du serveur (sort_order puis nom) ; groupes dans l'ordre de leur
// premier examen ; examens sans section regroupes en fin sous la cle ''. `query` filtre sur code, nom, titre.
export function groupExams(exams, query = '', showInactive = true) {
    const q = normalizeText(query).trim();
    const groups = new Map();
    for (const ex of exams || []) {
        if (!showInactive && ex.is_active === false) continue;
        if (q) {
            const hay = normalizeText(`${ex.code} ${ex.nom} ${ex.print_title || ''}`);
            if (!hay.includes(q)) continue;
        }
        const key = trimmed(ex.section);
        if (!groups.has(key)) groups.set(key, []);
        groups.get(key).push(ex);
    }
    const out = [...groups.entries()].map(([section, items]) => ({ section, items }));
    out.sort((a, b) => (a.section === '' ? 1 : 0) - (b.section === '' ? 1 : 0));
    return out;
}

// ---------------------------------------------------------------- erreurs serveur
// Code metier d'une erreur (detail = { code, message } ; l'intercepteur peut avoir deja remplace detail par le texte
// traduit et garde l'original dans detail_raw).
export function serverCode(err) {
    const data = err?.response?.data;
    const raw = data?.detail_raw ?? data?.detail;
    return raw && typeof raw === 'object' && !Array.isArray(raw) ? raw.code || null : null;
}

// Message affichable : texte du detail (deja traduit par l'intercepteur quand une cle serverErrors.<code> existe),
// message du serveur pour un detail objet, sinon liste de champs refuses, sinon repli.
export function catalogueErrorMessage(err, fallback = '') {
    const detail = err?.response?.data?.detail;
    if (detail && typeof detail === 'object' && !Array.isArray(detail)) return detail.message || fallback;
    if (typeof detail === 'string' && detail) return detail;
    if (Array.isArray(detail) && detail.length) {
        return detail.map((d) => {
            const field = Array.isArray(d?.loc) ? d.loc.filter((p) => p !== 'body').join('.') : '';
            return field ? `${field} : ${d?.msg || ''}` : d?.msg || '';
        }).filter(Boolean).join(' ; ') || fallback;
    }
    return fallback;
}

export function isNetworkFailure(err) {
    return !!err && !err.response;
}
