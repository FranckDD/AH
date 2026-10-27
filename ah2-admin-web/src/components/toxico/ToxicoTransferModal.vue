<template>
  <FullScreenPanel :title="t('toxico.transfer.title')" :subtitle="patientName" @close="close">
    <form id="toxico-transfer-form" @submit.prevent="submit" class="grid gap-4">
      <p class="rounded-card border p-3 text-base" :class="toneClasses('neutral')">
        {{ t('toxico.transfer.current', { name: currentPsychologistName || t('toxico.transfer.no_referent') }) }}
      </p>

      <FormField id="transfer-target" :label="t('toxico.transfer.target_label')" required v-slot="{ describedBy }">
        <select id="transfer-target" v-model="targetId" :disabled="isSubmitting" :aria-describedby="describedBy" :class="fieldClass">
          <option :value="null" disabled>{{ t('toxico.transfer.target_placeholder') }}</option>
          <option v-for="psy in candidates" :key="psy.id" :value="psy.id">{{ psy.name }}</option>
        </select>
      </FormField>

      <FormField id="transfer-reason" :label="t('toxico.transfer.reason_label')" required v-slot="{ describedBy }">
        <textarea id="transfer-reason" v-model="reason" rows="4" :maxlength="TRANSFER_REASON_MAX_LENGTH" :disabled="isSubmitting" :aria-describedby="describedBy"
                  :placeholder="t('toxico.transfer.reason_placeholder')" :class="[fieldClass, 'py-2']"></textarea>
      </FormField>

      <p v-if="errorText" role="alert" class="rounded-card border p-3 text-base" :class="toneClasses('danger')">{{ errorText }}</p>
    </form>

    <template #footer>
      <ActionBar>
        <template #secondary>
          <AppButton variant="secondary" :disabled="isSubmitting" @click="close">{{ t('toxico.transfer.cancel') }}</AppButton>
        </template>
        <AppButton type="submit" form="toxico-transfer-form" variant="spirit" :disabled="isSubmitting" :loading="isSubmitting">
          {{ isSubmitting ? t('toxico.transfer.submitting') : t('toxico.transfer.submit') }}
        </AppButton>
      </ActionBar>
    </template>
  </FullScreenPanel>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { useToxicoStore } from '@/stores/toxicoStore';
import { TRANSFER_REASON_MAX_LENGTH, validateTransfer, apiErrorMessage } from '@/utils/toxicoStays';
import { AppButton, FormField, ActionBar, FullScreenPanel } from '@/components/ui';
import { toneClasses } from '@/design/tones';

const props = defineProps({
  dossierId: { type: Number, required: true },
  patientName: { type: String, default: '' },
  currentPsychologistId: { type: Number, default: null },
  currentPsychologistName: { type: String, default: '' },
});
const emit = defineEmits(['close', 'transferred']);
const { t } = useI18n();
const toxicoStore = useToxicoStore();

const fieldClass = 'block w-full min-h-11 lg:min-h-10 rounded-control border border-tone-neutral-border bg-white px-3 text-base text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600';

// Le referent actuel n'est pas proposable : on ne transfere pas vers soi-meme.
const candidates = computed(() => (toxicoStore.psychologists || []).filter((p) => p.id !== props.currentPsychologistId));

const targetId = ref(null);
const reason = ref('');
const isSubmitting = ref(false);
const errorKey = ref('');
const serverError = ref('');
const errorText = computed(() => serverError.value || (errorKey.value ? t(errorKey.value) : ''));

onMounted(() => { toxicoStore.fetchPsychologists().catch(() => {}); });
watch([targetId, reason], () => { errorKey.value = ''; serverError.value = ''; });

function close() {
  if (!isSubmitting.value) emit('close');
}

async function submit() {
  if (isSubmitting.value) return;
  const errors = validateTransfer({ toPsychologistId: targetId.value, currentPsychologistId: props.currentPsychologistId, reason: reason.value });
  if (errors.length) { errorKey.value = errors[0]; return; }
  isSubmitting.value = true;
  serverError.value = '';
  try {
    await toxicoStore.transferDossier(props.dossierId, { toPsychologistId: targetId.value, reason: reason.value });
    const target = candidates.value.find((p) => p.id === targetId.value);
    emit('transferred', { name: target?.name || '' });
  } catch (e) {
    const status = e?.response?.status;
    const fallback = status === 403 ? t('toxico.stays.errors.forbidden')
      : status === 422 ? t('toxico.stays.errors.invalid')
      : t('toxico.stays.errors.generic');
    serverError.value = apiErrorMessage(e, fallback);
  } finally {
    isSubmitting.value = false;
  }
}
</script>
