// Regle « consultation passee = lecture seule » (2026-10-21), miroir local de
// repositories/consultation_lock.py. Le serveur reste l'autorite (409) et
// renvoie is_editable sur chaque consultation/prescription : ce flag est
// TOUJOURS prioritaire. Le calcul local ne sert que pour les lignes PowerSync
// (hors ligne / pas encore resynchronisees), qui n'ont pas ce champ.
//
// Ordre (identique au serveur) : date de consultation la plus recente, puis
// plus grand id serveur. Une consultation locale pas encore synchronisee
// (aucun id serveur) vient d'etre saisie : elle est plus recente que toute
// consultation synchronisee ; entre deux non synchronisees : date locale,
// puis uuid local (ordre deterministe - exactement une gagne).

export const LOCKED_MESSAGE_FR =
    "Cette consultation n'est plus modifiable : une consultation plus récente existe pour ce patient.";

const serverId = (rec) => rec?.record_id ?? rec?.server_id ?? null;
const localId = (rec) => String(rec?.id ?? rec?.local_id ?? '');
const recKey = (rec) => {
    const sid = serverId(rec);
    return sid != null ? `s:${sid}` : `l:${localId(rec)}`;
};

function parseDate(v) {
    const t = v ? Date.parse(v) : NaN;
    return Number.isNaN(t) ? -Infinity : t;
}

// Tuple de comparaison : [synchronisee?0:1, date, id serveur, uuid local].
function rank(rec) {
    const sid = serverId(rec);
    return sid == null
        ? [1, parseDate(rec?.consultation_date), 0, localId(rec)]
        : [0, parseDate(rec?.consultation_date), Number(sid), ''];
}

function newer(a, b) {
    const ra = rank(a);
    const rb = rank(b);
    for (let i = 0; i < ra.length; i += 1) {
        if (ra[i] !== rb[i]) return ra[i] > rb[i];
    }
    return false;
}

// Regroupe par patient : deux lignes sont du meme patient si elles partagent
// patient_id OU patient_uuid (union-find - une ligne locale peut n'avoir que
// l'uuid, une ligne synchronisee que l'id, une troisieme les deux).
function groupOf(records) {
    const parent = new Map();
    const find = (k) => {
        while (parent.get(k) !== k) k = parent.get(k);
        return k;
    };
    const union = (a, b) => {
        const ra = find(a);
        const rb = find(b);
        if (ra !== rb) parent.set(ra, rb);
    };
    const keysOf = (rec) => {
        const ks = [];
        if (rec?.patient_id != null && rec.patient_id !== '') ks.push(`id:${rec.patient_id}`);
        if (rec?.patient_uuid) ks.push(`uuid:${rec.patient_uuid}`);
        if (!ks.length) ks.push(`rec:${recKey(rec)}`);
        return ks;
    };
    for (const rec of records) {
        const ks = keysOf(rec);
        ks.forEach((k) => { if (!parent.has(k)) parent.set(k, k); });
        ks.slice(1).forEach((k) => union(ks[0], k));
    }
    return (rec) => find(keysOf(rec)[0]);
}

// Map groupe patient -> recKey de la consultation la plus recente.
export function latestRecordKeys(records, { samePatient = false } = {}) {
    const list = records || [];
    const group = samePatient ? () => 'all' : groupOf(list);
    const best = new Map();
    for (const rec of list) {
        const g = group(rec);
        const cur = best.get(g);
        if (!cur || newer(rec, cur)) best.set(g, rec);
    }
    return new Map([...best].map(([g, rec]) => [g, recKey(rec)]));
}

// allRecords : soit des consultations de plusieurs patients (regroupees par
// patient_id/patient_uuid), soit - samePatient: true - les consultations
// deja filtrees par l'appelant pour CE patient (comparees toutes entre elles).
export function isRecordEditable(record, allRecords, { samePatient = false } = {}) {
    if (typeof record?.is_editable === 'boolean') return record.is_editable;
    const list = allRecords && allRecords.length ? [...allRecords] : [];
    if (!list.some((r) => recKey(r) === recKey(record))) list.push(record);
    const group = samePatient ? () => 'all' : groupOf(list);
    const latest = latestRecordKeys(list, { samePatient });
    return latest.get(group(record)) === recKey(record);
}

export function findLinkedRecord(link, allRecords) {
    if (link == null || link === '') return null;
    return (allRecords || []).find(
        (r) => String(serverId(r)) === String(link) || String(r?.id) === String(link) || String(r?.local_id) === String(link)
    ) || null;
}

// Consultations du meme patient qu'une ligne (patient_id OU patient_uuid).
export function samePatientRecords(ref, allRecords) {
    return (allRecords || []).filter((r) =>
        (ref?.patient_id != null && r?.patient_id != null && String(r.patient_id) === String(ref.patient_id))
        || (ref?.patient_uuid && r?.patient_uuid && r.patient_uuid === ref.patient_uuid));
}

export function isPrescriptionEditable(prescription, allRecords) {
    if (typeof prescription?.is_editable === 'boolean') return prescription.is_editable;
    const rec = findLinkedRecord(prescription?.medical_record_id, allRecords);
    if (!rec) return true; // sans consultation, ou inconnue localement : le serveur tranchera
    return isRecordEditable({ ...rec, is_editable: undefined }, allRecords);
}

// Refus serveur cause par CETTE regle (409 + message exact du backend).
export function isConsultationLockedRejection(error) {
    return error?.response?.status === 409 && error?.response?.data?.detail === LOCKED_MESSAGE_FR;
}

// Entree de quarantaine (sync_quarantine) pour une ecriture hors ligne
// refusee par la regle : conserve le texte clinique saisi (ligne locale
// complete, pas seulement op.opData qui, sur un PATCH, ne contient que les
// colonnes modifiees) pour qu'il puisse etre relu / ressaisi.
export function buildLockedQuarantineEntry(op, localRow, error) {
    const isRecord = op?.table === 'medical_records';
    return {
        kind: isRecord ? 'medical_record_locked' : 'prescription_locked',
        localId: op?.id,
        // null : le patient existe cote serveur (le refus porte sur la
        // consultation) - jamais rattache aux groupes « patient refuse » ni
        // purge par reattachToExistingPatient.
        patientUuid: null,
        payload: { ...(op?.opData || {}), ...(localRow || {}), _op: op?.op, _table: op?.table },
        error: error?.response?.data?.detail || LOCKED_MESSAGE_FR,
    };
}
