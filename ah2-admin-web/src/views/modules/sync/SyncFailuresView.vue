<template>
  <div class="space-y-6 w-full">
    <div class="bg-white p-6 rounded-2xl shadow-xs border border-gray-100">
      <h1 class="text-2xl font-extrabold text-gray-800 tracking-tight">Échecs de synchronisation</h1>
      <p class="text-sm text-gray-500 mt-1">
        Patients créés hors ligne refusés par le serveur (par exemple un numéro d'identité nationale déjà utilisé).
        Leurs consultations et prescriptions sont conservées ici, jamais envoyées au mauvais patient.
      </p>
    </div>

    <div v-if="isLoading" class="p-10 text-center">
      <span class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-teal-600"></span>
    </div>

    <div v-else-if="groups.length === 0 && labOrphans.length === 0" class="bg-white p-10 rounded-2xl border border-gray-100 text-center text-gray-500">
      Aucun échec de synchronisation.
    </div>

    <div v-for="g in groups" :key="g.patientUuid" class="bg-white p-6 rounded-2xl shadow-xs border border-red-100 space-y-3">
      <div class="flex flex-wrap justify-between gap-2">
        <div>
          <p class="text-lg font-semibold text-gray-900">{{ g.name }}</p>
          <p class="text-xs text-gray-500">Né(e) le {{ g.birthDate || '—' }} · N° d'identité : {{ g.nationalId || '—' }}</p>
        </div>
        <span class="inline-flex items-center px-2 py-0.5 h-fit rounded-sm text-xs font-medium bg-red-100 text-red-800">
          Échec de synchronisation
        </span>
      </div>
      <p class="text-sm text-red-700">Motif : {{ g.error }}</p>
      <p class="text-sm text-gray-600">
        Données retenues : {{ g.recordCount }} consultation(s), {{ g.prescriptionCount }} prescription(s),
        {{ g.labResultCount }} dossier(s) labo, {{ g.labResultDetailCount }} valeur(s) de dossier labo.
      </p>

      <div class="flex flex-wrap items-end gap-2 pt-2 border-t border-gray-100">
        <div class="flex-1 min-w-[200px]">
          <label :for="`code-${g.patientUuid}`" class="text-xs font-bold text-gray-500 uppercase mb-1 block">
            Code du patient existant (AH2-…)
          </label>
          <input :id="`code-${g.patientUuid}`" v-model="codes[g.patientUuid]" type="text"
                 class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-teal-500 focus:border-teal-500 sm:text-sm" />
        </div>
        <button type="button" @click="handleReattach(g)" :disabled="busy[g.patientUuid]"
                class="px-4 py-2 bg-teal-600 text-white rounded-lg hover:bg-teal-700 font-medium disabled:opacity-50">
          {{ busy[g.patientUuid] ? 'Rattachement…' : 'Rattacher à ce patient' }}
        </button>
      </div>
      <p v-if="messages[g.patientUuid]" class="text-sm" :class="messages[g.patientUuid].ok ? 'text-emerald-700' : 'text-red-700'">
        {{ messages[g.patientUuid].text }}
      </p>
    </div>

    <!-- Dossiers/valeurs labo refuses pour une raison propre au dossier
         (ex. examen retire du catalogue), sans patient en quarantaine :
         consultation seule, aucune action de resolution ici. -->
    <div v-if="!isLoading && labOrphans.length" class="bg-white p-6 rounded-2xl shadow-xs border border-red-100 space-y-3">
      <p class="text-lg font-semibold text-gray-900">Laboratoire : éléments refusés par le serveur</p>
      <ul class="divide-y divide-gray-100">
        <li v-for="l in labOrphans" :key="l.id" class="py-2 text-sm">
          <span class="font-medium text-gray-800">{{ l.kind === 'lab_result' ? 'Dossier labo' : 'Valeur de dossier labo' }}</span>
          <span v-if="l.examenId" class="text-gray-500"> · examen n° {{ l.examenId }}</span>
          <span class="text-gray-400"> · {{ l.createdAt }}</span>
          <p class="text-red-700">Motif : {{ l.error || '—' }}</p>
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import api from '@/services/api';
import { listQuarantine, reattachToExistingPatient } from '@/powersync-client/syncQuarantine';

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
