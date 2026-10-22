<script setup>
// Fenêtre « patient enregistré » (infirmière et secrétaire) : le code reste affiché jusqu'à ce qu'on clique sur OK
// (aucune fermeture au clic à côté ni par Échap), pour qu'elle ait le temps de le noter sur le carnet.
// Hors ligne ou code pas encore arrivé : on ne bloque pas, OK reste disponible.
// Patient refusé par le serveur (doublon de numéro d'identité...) : il est mis en quarantaine par le connecteur
// d'envoi ; la fenêtre le détecte, le dit clairement et renvoie vers « Échecs de synchronisation ».
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRouter } from 'vue-router';
import api from '@/services/api';
import { db } from '@/powersync-client/client';
import { useConnectionStatus } from '@/composables/useConnectionStatus';
import { pollPatientCode, codeDialogState, quarantineReason } from '@/utils/newPatientFlow';
import { toneClasses } from '@/design/tones';
import AppButton from '@/components/ui/AppButton.vue';

const props = defineProps({
  localUuid: { type: String, required: true },
  firstName: { type: String, default: '' },
  lastName: { type: String, default: '' },
  // Page « Échecs de synchronisation » de l'espace de l'utilisateur (bouton affiché en cas de refus).
  failuresPath: { type: String, default: '' },
});
const emit = defineEmits(['ok']);

const { t } = useI18n();
const router = useRouter();
const { state } = useConnectionStatus();

const code = ref('');
const patientId = ref(null);
const timedOut = ref(false);
const rejected = ref(false);
const rejectedReason = ref('');
const copied = ref(false);
const controller = new AbortController();
const okButton = ref(null);

const offline = computed(() => state.value === 'offline');
const dialogState = computed(() => codeDialogState({ code: code.value, offline: offline.value, timedOut: timedOut.value, rejected: rejected.value }));
const fullName = computed(() => `${props.firstName} ${props.lastName}`.trim());

// Hors ligne l'envoi attend : on ne sonde le serveur que connecté (une erreur réseau ne casse rien).
async function lookupOnce() {
  try {
    const { data } = await api.get(`/patients/by-uuid/${props.localUuid}`);
    return data;
  } catch (err) {
    if (err?.response?.status === 404) return null;
    throw err;
  }
}

let polling = false;
async function startPolling() {
  if (polling || code.value) return;
  polling = true;
  timedOut.value = false;
  const found = await pollPatientCode(lookupOnce, { signal: controller.signal });
  polling = false;
  if (controller.signal.aborted) return;
  if (found) {
    code.value = found.code_patient;
    patientId.value = found.patient_id;
  } else {
    timedOut.value = true;
  }
}

// Le connecteur d'envoi met le patient en quarantaine (table locale sync_quarantine) quand le serveur le refuse
// definitivement : on le voit des que la ligne apparait, sans attendre le delai de recherche du code.
async function watchRejection() {
  try {
    for await (const result of db.watch(
      "SELECT error FROM sync_quarantine WHERE kind = 'patient' AND local_id = ?",
      [props.localUuid],
      { signal: controller.signal }
    )) {
      const row = result.rows?._array?.[0];
      if (row && !rejected.value) {
        rejected.value = true;
        rejectedReason.value = quarantineReason(row.error);
        controller.abort(); // plus rien a attendre : on arrete la recherche du code et cette surveillance
      }
    }
  } catch (err) {
    if (!controller.signal.aborted) console.error('Surveillance du refus du patient interrompue:', err);
  }
}

onMounted(() => {
  okButton.value?.$el?.focus();
  watchRejection();
  if (!offline.value) startPolling();
});
// Connexion rétablie pendant que la fenêtre est ouverte : on relance la recherche du code.
watch(offline, (isOffline) => {
  if (!isOffline) startPolling();
});
onBeforeUnmount(() => controller.abort());

async function copyCode() {
  try {
    await navigator.clipboard.writeText(code.value);
    copied.value = true;
    setTimeout(() => { copied.value = false; }, 2000);
  } catch {
    // presse-papiers indisponible : le code reste lisible à l'écran
  }
}

function confirm() {
  emit('ok', { code: code.value, patientId: patientId.value, rejected: rejected.value });
}

// Le patient refuse se resout depuis « Echecs de synchronisation » (rattachement a un patient existant).
function openFailures() {
  emit('ok', { code: '', patientId: null, rejected: true });
  router.push(props.failuresPath);
}
</script>

<template>
  <!-- Pas de fermeture au clic à côté ni par Échap : seul OK referme la fenêtre -->
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-ink/50 p-4" role="dialog" aria-modal="true" aria-labelledby="new-patient-title">
    <div class="app-refonte w-full max-w-md rounded-card border border-tone-neutral-border bg-white p-6 shadow-card">
      <h2 id="new-patient-title" class="text-xl font-bold text-ink">{{ dialogState === 'rejected' ? t('newPatient.title_rejected') : t('newPatient.title') }}</h2>
      <p v-if="fullName" class="mt-1 text-base text-ink-muted">{{ t('newPatient.patientLabel') }} : <span class="font-semibold text-ink">{{ fullName }}</span></p>

      <div v-if="dialogState === 'rejected'" role="alert" class="mt-5 grid gap-3 rounded-card border p-4" :class="toneClasses('danger')">
        <p class="text-base font-semibold">{{ t('newPatient.rejected', { reason: rejectedReason || t('newPatient.rejected_unknown') }) }}</p>
        <p class="text-base">{{ t('newPatient.rejected_help') }}</p>
        <AppButton v-if="failuresPath" variant="secondary" @click="openFailures">{{ t('newPatient.see_failures') }}</AppButton>
      </div>

      <div v-else class="mt-5 rounded-card border border-tone-neutral-border bg-tone-neutral-bg p-4 text-center" role="status" aria-live="polite">
        <p class="text-sm font-medium text-ink-muted">{{ t('newPatient.codeLabel') }}</p>

        <template v-if="dialogState === 'ready'">
          <p class="mt-1 select-all break-all text-4xl font-extrabold tracking-wide text-brand-700">{{ code }}</p>
          <AppButton variant="secondary" class="mt-3" @click="copyCode">
            {{ copied ? t('newPatient.copied') : t('newPatient.copy') }}
          </AppButton>
          <p class="mt-3 text-base text-ink">{{ t('newPatient.noteIt') }}</p>
        </template>

        <p v-else-if="dialogState === 'waiting'" class="mt-2 text-lg font-medium text-ink">{{ t('newPatient.waiting') }}</p>
        <p v-else-if="dialogState === 'offline'" class="mt-2 text-base text-ink">{{ t('newPatient.offline') }}</p>
        <p v-else class="mt-2 text-base text-ink">{{ t('newPatient.late') }}</p>
      </div>

      <AppButton ref="okButton" size="lg" class="mt-6 w-full" @click="confirm">{{ t('newPatient.ok') }}</AppButton>
    </div>
  </div>
</template>
