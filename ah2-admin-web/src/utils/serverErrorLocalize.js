// Messages d'erreur du serveur rendus dans la langue de l'interface.
//
// Deux voies :
//  1. detail = { code, message } (schema du planning infirmier et des corrections de stock) : si le code figure
//     dans serverErrors.<code>, il est traduit ; sinon le message du serveur sert de repli.
//  2. detail = texte francais du serveur : reconnu par RULES (texte normalise, sans accent) et traduit
//     seulement si la langue courante est l'anglais. Un texte inconnu est laisse tel quel.
// Fonctions pures : t et te viennent de l'appelant, testees sans navigateur.

function norm(s) {
    return String(s).normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[‘’]/g, "'").toLowerCase();
}

// [motif sur le texte normalise, cle serverErrors.*]. Du plus precis au plus general.
export const RULES = [
    [/ce dossier a deja ete pris en charge/, 'record_already_taken'],
    [/seul un medecin peut prendre en charge/, 'only_doctor_takes_record'],
    [/ancien mot de passe (est )?incorrect|^mot de passe incorrect/, 'password_wrong'],
    [/trop de tentatives/, 'too_many_attempts'],
    [/identifiants invalides/, 'bad_credentials'],
    // laboratoire : facture deja recue
    [/ligne de facture a deja ete recue|examen de l'ordonnance a deja ete recu/, 'lab_line_already_received'],
    [/ligne de facture invalide/, 'lab_line_invalid'],
    // remises
    [/demande introuvable/, 'discount_not_found'],
    [/cette demande n'est plus en attente/, 'discount_not_pending'],
    [/cette demande ne vous est pas adressee/, 'discount_not_addressed'],
    [/seul l'auteur de la demande peut l'annuler/, 'discount_author_only'],
    [/un refus ne peut pas etre accompagne/, 'discount_refusal_extras'],
    [/decision_percent doit etre/, 'discount_percent_values'],
    [/decision d'approbation doit accorder/, 'discount_approval_needs_grant'],
    [/destinataire choisi n'est pas un manager/, 'discount_bad_recipient'],
    [/aucune avance ne peut etre encaissee/, 'discount_no_advance'],
    // fabrication
    [/cet achat est annule/, 'fab_purchase_cancelled'],
    [/cet achat a deja ete consomme/, 'fab_purchase_consumed'],
    [/cet intrant est desactive|un intrant de cet achat est desactive|un intrant consomme est desactive/, 'fab_input_disabled'],
    [/un achat consomme est annule/, 'fab_purchase_cancelled'],
    [/un achat ne peut figurer qu'une fois/, 'fab_purchase_once'],
    [/quantite consommee superieure au restant/, 'fab_quantity_over_remaining'],
    [/le lot n'a aucune consommation/, 'fab_lot_no_consumption'],
    [/exactement une consommation de contenant/, 'fab_one_container'],
    [/seul un lot brouillon est modifiable/, 'fab_only_draft_editable'],
    [/seul un lot termine peut etre rouvert/, 'fab_only_finished_reopened'],
    [/transition impossible/, 'fab_bad_transition'],
    [/annulez d'abord les sorties declarees/, 'fab_cancel_outputs_first'],
    [/aucune bouteille bonne|toutes les bouteilles sont sorties/, 'fab_nothing_to_ship'],
    [/manque hors tolerance/, 'fab_justification_required'],
    [/une sortie ne se declare que sur un lot termine|une sortie ne s'annule que sur un lot termine/, 'fab_output_needs_finished'],
    [/cette sortie est deja annulee/, 'fab_output_already_cancelled'],
    [/^(lot|achat|intrant|produit|sortie) introuvable/, 'not_found'],
    // cloture de caisse
    [/cloture de caisse est deja en cours/, 'cash_in_progress'],
    [/periode vient deja d'etre cloturee/, 'cash_already_closed'],
    [/caisse non initialisee/, 'cash_not_initialized'],
    [/caisse est deja initialisee/, 'cash_already_initialized'],
    [/cette correction a deja ete traitee/, 'cash_correction_done'],
    [/comptage manquant pour/, 'cash_count_missing'],
    [/ce commentaire est reserve/, 'cash_comment_reserved'],
    [/motif de la correction est obligatoire/, 'cash_reason_required'],
    [/les especes ne peuvent pas etre desactivees/, 'cash_cannot_disable_cash'],
    [/cloture introuvable|correction introuvable/, 'not_found'],
    [/ne pouvez pas (valider|rejeter|decider).*que vous avez saisie/, 'not_own_entry'],
    // comptes utilisateurs, stock, reception, comptage, fichiers
    [/nom d'utilisateur existe deja/, 'username_exists'],
    [/adresse e-mail est deja utilisee/, 'email_exists'],
    [/conflit d'integrite.*dupliquee/, 'duplicate_value'],
    [/conflit d'integrite/, 'integrity_conflict'],
    [/stock insuffisant/, 'insufficient_stock'],
    [/une reception est liee a ce lot/, 'reception_linked_to_lot'],
    [/une reception valide existe deja/, 'reception_duplicate'],
    [/un produit actif nomme/, 'active_product_exists'],
    [/vous avez deja un comptage en cours/, 'count_already_open'],
    [/ce comptage n'est plus en cours/, 'count_not_open'],
    [/le total trouve depasse l'attendu/, 'count_total_exceeds'],
    [/fichier.*(depasse 5 mo|taille maximale)/, 'file_too_large'],
    [/doit etre un pdf, un jpeg ou un png/, 'file_bad_type'],
    // generiques
    [/non trouve|introuvable|not found/, 'not_found'],
    [/est obligatoire|est requis|field required/, 'required'],
    [/depasse la limite|depasse \d+ caracteres/, 'too_large'],
    [/invalide/, 'invalid'],
];

const STATUS_KEYS = { 401: 'unauthorized', 403: 'forbidden', 404: 'not_found' };
// Textes anglais par defaut de FastAPI/Starlette (ni francais ni traduits).
const ENGLISH_DEFAULTS = /^(forbidden|not found|not authenticated|could not validate credentials|unauthorized)$/i;

export function localizeDetail(detail, status, lang, t, te) {
    if (detail && typeof detail === 'object' && !Array.isArray(detail)) {
        if (detail.code && te(`serverErrors.${detail.code}`)) return t(`serverErrors.${detail.code}`);
        return undefined;
    }
    if (typeof detail !== 'string' || !detail) return undefined;
    if (ENGLISH_DEFAULTS.test(detail.trim()) && STATUS_KEYS[status]) return t(`serverErrors.${STATUS_KEYS[status]}`);
    if (lang !== 'en') return undefined;
    const text = norm(detail);
    for (const [re, key] of RULES) if (re.test(text)) return t(`serverErrors.${key}`);
    if (STATUS_KEYS[status] === 'forbidden') return t('serverErrors.forbidden');
    return undefined;
}

// Intercepteur de reponse : remplace response.data.detail par le texte localise (l'original reste dans
// detail_raw), de sorte que tous les ecrans qui affichent detail beneficient de la traduction.
export function localizeAxiosError(error, lang, t, te) {
    const data = error?.response?.data;
    if (!data || typeof data !== 'object') return error;
    const localized = localizeDetail(data.detail, error.response.status, lang, t, te);
    if (localized !== undefined) {
        data.detail_raw = data.detail;
        data.detail = localized;
    }
    return error;
}
