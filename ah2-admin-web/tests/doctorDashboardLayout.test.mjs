import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dashboardBlocks, waitingSince, waitingTone } from '../src/utils/doctorDashboardLayout.js';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { default: i18n } = await import('../src/i18n.js');

// --- blocs selon le rôle ---
test('médecin : cinq cartes, panneau par statut, bouton de prise en charge', () => {
    const b = dashboardBlocks({ role: 'medecin', pendingCount: 2 });
    assert.deepEqual(b.statTiles, ['totalAppointments', 'distinctPatients', 'medicalRecords', 'prescriptions', 'hospitalizations']);
    assert.equal(b.showStatusPanel, true);
    assert.equal(b.showMotifPanel, true);
    assert.equal(b.canClaim, true);
    assert.equal(b.queueState, 'list');
});

test('infirmière : ni rendez-vous, ni patients distincts, ni prescriptions, ni statut, ni prise en charge', () => {
    for (const role of ['nurse', 'Nurse']) {
        const b = dashboardBlocks({ role, pendingCount: 2 });
        assert.deepEqual(b.statTiles, ['medicalRecords', 'hospitalizations']);
        assert.equal(b.showStatusPanel, false);
        assert.equal(b.showMotifPanel, true);
        assert.equal(b.canClaim, false);
        assert.equal(b.queueState, 'list');
    }
});

test('file vide ou donnée absente : état vide, jamais d’erreur', () => {
    assert.equal(dashboardBlocks({ role: 'medecin', pendingCount: 0 }).queueState, 'empty');
    assert.equal(dashboardBlocks({ role: 'medecin' }).queueState, 'empty');
    assert.equal(dashboardBlocks({ role: 'medecin', pendingCount: null }).queueState, 'empty');
    assert.equal(dashboardBlocks().queueState, 'empty');
    assert.deepEqual(dashboardBlocks().statTiles, ['medicalRecords', 'hospitalizations']);
});

test('rôle inconnu : traité comme l’infirmière (jamais plus de droits)', () => {
    const b = dashboardBlocks({ role: 'secretaire', pendingCount: 1 });
    assert.equal(b.canClaim, false);
    assert.equal(b.showStatusPanel, false);
});

test('erreur de chargement signalée', () => {
    assert.equal(dashboardBlocks({ role: 'medecin', error: 'boom' }).showLoadError, true);
    assert.equal(dashboardBlocks({ role: 'medecin', error: null }).showLoadError, false);
});

// --- ancienneté, au jour près (la consultation est datée du jour, sans heure fiable) ---
const NOW = new Date(2026, 9, 22, 15, 30); // 22 octobre 2026, 15h30 heure locale

test('waitingSince : aujourd’hui, hier, plusieurs jours, date absente ou invalide', () => {
    assert.deepEqual(waitingSince('2026-10-22', NOW), { kind: 'today', days: 0 });
    assert.deepEqual(waitingSince('2026-10-22T00:00:00', NOW), { kind: 'today', days: 0 });
    assert.deepEqual(waitingSince('2026-10-21T23:59:00', NOW), { kind: 'days', days: 1 });
    assert.deepEqual(waitingSince('2026-10-19', NOW), { kind: 'days', days: 3 });
    assert.deepEqual(waitingSince('2026-11-02', NOW), { kind: 'today', days: 0 });
    for (const bad of [null, undefined, '', 'abc']) {
        assert.deepEqual(waitingSince(bad, NOW), { kind: 'unknown', days: 0 });
    }
});

test('waitingTone : attention seulement à partir d’un jour', () => {
    assert.equal(waitingTone({ kind: 'today', days: 0 }), 'neutral');
    assert.equal(waitingTone({ kind: 'unknown', days: 0 }), 'neutral');
    assert.equal(waitingTone({ kind: 'days', days: 1 }), 'warning');
    assert.equal(waitingTone({ kind: 'days', days: 5 }), 'warning');
    assert.equal(waitingTone(undefined), 'neutral');
});

// --- clés i18n ajoutées ---
const KEYS = [
    'queue_help', 'queue_empty_help', 'waiting_today', 'waiting_days', 'load_error',
    'quick_title', 'quick_appointments', 'quick_hospitalizations', 'quick_patients', 'stats_title',
];

test('clés doctorKpi.* ajoutées présentes en FR et EN, pluriel des jours', () => {
    const msgs = i18n.global.messages.value;
    for (const locale of ['fr', 'en']) {
        for (const k of KEYS) {
            assert.equal(typeof msgs[locale].doctorKpi?.[k], 'string', `${locale}.doctorKpi.${k} manquante`);
        }
    }
    const { t } = i18n.global;
    assert.equal(t('doctorKpi.waiting_days', { n: 1 }, { locale: 'fr', plural: 1 }), 'Depuis 1 jour');
    assert.equal(t('doctorKpi.waiting_days', { n: 3 }, { locale: 'fr', plural: 3 }), 'Depuis 3 jours');
    assert.equal(t('doctorKpi.waiting_days', { n: 3 }, { locale: 'en', plural: 3 }), 'For 3 days');
});

// --- contrat de la vue : rien de perdu ---
const view = readFileSync(new URL('../src/views/modules/doctors/DoctorKpiView.vue', import.meta.url), 'utf8');

test('contrat : appels du store et actions conservés', () => {
    for (const needle of [
        'kpiStore.fetchKpiData()', 'kpiStore.setDates(', 'kpiStore.claimRecord(',
        'kpiStore.pendingReview', 'kpiStore.claimError', 'kpiStore.filters.startDate', 'kpiStore.filters.endDate',
        'kpiStore.stats.totalAppointments', 'kpiStore.stats.distinctPatients', 'kpiStore.stats.medicalRecordsCount',
        'kpiStore.stats.prescriptionsCount', 'kpiStore.stats.hospitalizationsCurrentCount',
        'countByStatus', 'consultationDistribution',
        "`/medical/patients/${record.patient_id}`", 'record: record.record_id',
    ]) {
        assert.ok(view.includes(needle), `« ${needle} » absent de DoctorKpiView.vue`);
    }
});

test('contrat : clés existantes réutilisées', () => {
    for (const key of [
        'doctorKpi.title', 'doctorKpi.subtitle', 'doctorKpi.period_from', 'doctorKpi.period_to',
        'doctorKpi.total_appointments', 'doctorKpi.distinct_patients', 'doctorKpi.medical_records_total',
        'doctorKpi.prescriptions_total', 'doctorKpi.hospitalizations_current', 'doctorKpi.pending_review_title',
        'doctorKpi.pending_review_empty', 'doctorKpi.pending_review_by', 'doctorKpi.claim_button',
        'doctorKpi.by_status', 'doctorKpi.by_motif', 'doctorKpi.no_data',
    ]) {
        assert.ok(view.includes(key), `${key} n'est plus utilisée`);
    }
});

test('contrat : aucune couleur de marque ou d’état en dur, composants ui/ utilisés', () => {
    assert.doesNotMatch(view, /#[0-9a-fA-F]{6}\b/);
    assert.doesNotMatch(view, /\b(indigo|emerald|slate|teal|amber|rose|sky|gray|red)-\d{2,3}\b/);
    assert.match(view, /@\/components\/ui/);
    assert.match(view, /dashboardBlocks/);
});

test('la file « à prendre en charge » vient avant les statistiques', () => {
    assert.ok(view.indexOf('doctorKpi.pending_review_title') < view.indexOf('doctorKpi.stats_title'));
});
