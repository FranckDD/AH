<template>
  <div class="grid w-full gap-6">

    <PageHeader
      title="Échecs de synchronisation"
      subtitle="Patients créés hors ligne refusés par le serveur (par exemple un numéro d'identité nationale déjà utilisé). Leurs consultations et prescriptions sont conservées ici, jamais envoyées au mauvais patient."
    />

    <p v-if="isLoading" class="p-10 text-center text-base text-ink-muted" role="status">{{ t('common.loading') }}</p>

    <div v-else-if="groups.length === 0 && labOrphans.length === 0 && lockedRejections.length === 0" class="rounded-card border border-tone-neutral-border bg-white shadow-card">
      <EmptyState title="Aucun échec de synchronisation." message="Tout ce qui a été saisi hors ligne a bien été envoyé au serveur." />
    </div>

    <section v-for="g in groups" :key="g.patientUuid" class="grid gap-3 rounded-card border border-tone-danger-border bg-white p-4 shadow-card md:p-6">
      <div class="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p class="text-lg font-semibold text-ink">{{ g.name }}</p>
          <p class="text-base text-ink-muted">Né(e) le {{ g.birthDate || '-' }}, N° d'identité : {{ g.nationalId || '-' }}</p>
        </div>
        <StatusBadge tone="danger" label="Échec de synchronisation" />
      </div>
      <p class="text-base font-medium text-tone-danger-text">Motif : {{ g.error }}</p>
      <p class="text-base text-ink">
        Données retenues : {{ g.recordCount }} consultation(s), {{ g.prescriptionCount }} prescription(s),
        {{ g.labResultCount }} dossier(s) labo, {{ g.labResultDetailCount }} valeur(s) de dossier labo.
      </p>

      <div class="grid gap-3 border-t border-tone-neutral-border pt-3 sm:grid-cols-[1fr_auto] sm:items-end">
        <FormField :id="`code-${g.patientUuid}`" label="Code du patient existant (AH2-...)" v-slot="{ describedBy }">
          <input :id="`code-${g.patientUuid}`" v-model="codes[g.patientUuid]" type="text" :aria-describedby="describedBy"
                 class="block w-full min-h-11 rounded-control border border-tone-neutral-border bg-white px-3 text-base text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600" />
        </FormField>
        <AppButton @click="handleReattach(g)" :disabled="busy[g.patientUuid]" :loading="busy[g.patientUuid]">
          {{ busy[g.patientUuid] ? 'Rattachement...' : 'Rattacher à ce patient' }}
        </AppButton>
      </div>
      <p v-if="messages[g.patientUuid]" role="status" class="text-base font-medium" :class="messages[g.patientUuid].ok ? 'text-tone-success-text' : 'text-tone-danger-text'">
        {{ messages[g.patientUuid].text }}
      </p>
    </section>

    <!-- Dossiers/valeurs labo refuses pour une raison propre au dossier
         (ex. examen retire du catalogue), sans patient en quarantaine :
         consultation seule, aucune action de resolution ici. -->
    <section v-if="!isLoading && labOrphans.length" class="grid gap-3 rounded-card border border-tone-danger-border bg-white p-4 shadow-card md:p-6">
      <p class="text-lg font-semibold text-ink">Laboratoire : éléments refusés par le serveur</p>
      <ul class="divide-y divide-tone-neutral-border">
        <li v-for="l in labOrphans" :key="l.id" class="py-3 text-base">
          <span class="font-medium text-ink">{{ l.kind === 'lab_result' ? 'Dossier labo' : 'Valeur de dossier labo' }}</span>
          <span v-if="l.examenId" class="text-ink-muted">, examen n° {{ l.examenId }}</span>
          <span class="text-ink-muted">, {{ l.createdAt }}</span>
          <p class="font-medium text-tone-danger-text">Motif : {{ l.error || '-' }}</p>
        </li>
      </ul>
    </section>

    <!-- Ecritures hors ligne refusees par la regle « consultation passee =
         lecture seule » : texte clinique conserve pour relecture. -->
    <section v-if="!isLoading && lockedRejections.length" class="grid gap-3 rounded-card border border-tone-warning-border bg-white p-4 shadow-card md:p-6">
      <p class="text-lg font-semibold text-ink">{{ t('medical.readonly.quarantine_title') }}</p>
      <p class="text-base text-ink-muted">{{ t('medical.readonly.quarantine_intro') }}</p>
      <ul class="divide-y divide-tone-neutral-border">
        <li v-for="l in lockedRejections" :key="l.id" class="space-y-2 py-3 text-base">
          <div class="flex flex-wrap items-center justify-between gap-2">
            <span class="font-medium text-ink">
              {{ l.kind === 'medical_record_locked' ? t('medical.readonly.quarantine_record') : t('medical.readonly.quarantine_prescription') }}
              <span class="font-normal text-ink-muted">, {{ l.createdAt }}</span>
            </span>
            <AppButton variant="secondary" @click="handleDismiss(l)">
              {{ t('medical.readonly.quarantine_dismiss') }}
            </AppButton>
          </div>
          <p class="font-medium text-tone-danger-text">{{ l.error || '-' }}</p>
          <dl class="grid grid-cols-1 gap-x-4 gap-y-1 text-ink sm:grid-cols-2">
            <template v-for="f in l.fields" :key="f.key">
              <dt class="text-sm font-bold uppercase text-ink-muted">{{ f.key }}</dt>
              <dd class="whitespace-pre-line">{{ f.value }}</dd>
            </template>
          </dl>
        </li>
      </ul>
    </section>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import api from '@/services/api';
import { useI18n } from 'vue-i18n';
import { listQuarantine, reattachToExistingPatient, dismissQuarantineEntry } from '@/powersync-client/syncQuarantine';
import { AppButton, PageHeader, FormField, StatusBadge, EmptyState } from '@/components/ui';

const { t } = useI18n();
const lockedRejections = ref([]);
const LOCKED_FIELDS = ['consultation_date', 'motif_code', 'symptoms', 'diagnosis', 'treatment', 'notes', 'medical_history',
  'allergies', 'bp', 'temperature', 'weight', 'height', 'medication', 'dosage', 'frequency', 'duration', 'start_date', 'end_date'];

async function handleDismiss(l) {
  await dismissQuarantineEntry(l.id);
  await load();
}

const isLoading = ref(false);
const groups = ref([]);
const labOrphans = ref([]);
const codes = reactive({});
const busy = reactive({});
const messages = reactive({});

async function load() {
  isLoading.value = true;
  try {
    const rows = await listQuarantine();
    const patients = rows.filter((r) => r.kind === 'patient');
    groups.value = patients.map((p) => {
      const payload = JSON.parse(p.payload || '{}');
      const children = rows.filter((r) => r.patient_uuid === p.local_id && r.kind !== 'patient');
      return {
        patientUuid: p.local_id,
        name: [payload.first_name, payload.last_name].filter(Boolean).join(' ') || 'Patient sans nom',
        birthDate: payload.birth_date,
        nationalId: payload.national_id,
        error: p.error,
        recordCount: children.filter((c) => c.kind === 'medical_record').length,
        prescriptionCount: children.filter((c) => c.kind === 'prescription').length,
        labResultCount: children.filter((c) => c.kind === 'lab_result').length,
        labResultDetailCount: children.filter((c) => c.kind === 'lab_result_detail').length,
      };
    });
    const quarantinedPatientIds = new Set(patients.map((p) => p.local_id));
    labOrphans.value = rows
      .filter((r) => (r.kind === 'lab_result' || r.kind === 'lab_result_detail')
        && !(r.patient_uuid && quarantinedPatientIds.has(r.patient_uuid)))
      .map((r) => {
        let payload = {};
        try { payload = JSON.parse(r.payload || '{}'); } catch { payload = {}; }
        return {
          id: r.id,
          kind: r.kind,
          examenId: payload.examen_id || null,
          error: r.error,
          createdAt: r.created_at,
        };
      });
    lockedRejections.value = rows
      .filter((r) => r.kind === 'medical_record_locked' || r.kind === 'prescription_locked')
      .map((r) => {
        let payload = {};
        try { payload = JSON.parse(r.payload || '{}'); } catch { payload = {}; }
        return {
          id: r.id,
          kind: r.kind,
          error: r.error,
          createdAt: r.created_at,
          fields: LOCKED_FIELDS.filter((k) => payload[k] != null && payload[k] !== '').map((k) => ({ key: k, value: String(payload[k]) })),
        };
      });
  } finally {
    isLoading.value = false;
  }
}

function normalizeCode(raw) {
  const code = (raw || '').trim().toUpperCase();
  if (!code) return '';
  return code.startsWith('AH2-') ? code : `AH2-${code}`;
}

// Resolution du patient existant par son code : necessite le reseau
// (source de verite serveur, jamais une copie locale pour une decision
// d'identite medicale).
async function handleReattach(g) {
  const code = normalizeCode(codes[g.patientUuid]);
  if (!code) {
    messages[g.patientUuid] = { ok: false, text: 'Saisissez le code du patient existant.' };
    return;
  }
  busy[g.patientUuid] = true;
  messages[g.patientUuid] = null;
  try {
    const res = await api.get('/patients/', { params: { search: code, per_page: 5 } });
    const list = Array.isArray(res.data) ? res.data : (res.data.data || []);
    const match = list.find((p) => p.code_patient === code);
    if (!match) {
      messages[g.patientUuid] = { ok: false, text: `Aucun patient avec le code ${code}.` };
      return;
    }
    await reattachToExistingPatient(g.patientUuid, match.patient_id || match.id);
    messages[g.patientUuid] = { ok: true, text: `Données rattachées à ${match.first_name} ${match.last_name}.` };
    await load();
  } catch (err) {
    messages[g.patientUuid] = {
      ok: false,
      text: err.response ? 'Erreur serveur, réessayez.' : 'Connexion requise pour rattacher un patient.',
    };
  } finally {
    busy[g.patientUuid] = false;
  }
}

onMounted(load);
</script>
