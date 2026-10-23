<template>
  <FullScreenPanel :title="t('toxico.stays.discharge_title')" :subtitle="patientName" tone="danger" @close="close">
    <form id="toxico-discharge-form" @submit.prevent="submit" class="grid gap-4">
      <fieldset :disabled="isSubmitting" class="grid gap-2">
        <legend class="mb-1 text-base font-medium text-ink">
          {{ t('toxico.stays.reason_label') }} <span class="text-tone-danger-text" aria-hidden="true">*</span>
        </legend>
        <div class="grid grid-cols-1 gap-2 sm:grid-cols-2">
          <label v-for="r in DISCHARGE_REASONS" :key="r"
                 :class="['flex min-h-11 cursor-pointer items-center gap-2 rounded-control border-2 px-3 text-base',
                          reason === r ? 'border-tone-danger-border bg-tone-danger-bg font-semibold text-tone-danger-text' : 'border-tone-neutral-border text-ink hover:bg-tone-neutral-bg']">
            <input type="radio" name="discharge-reason" :value="r" v-model="reason" class="h-5 w-5 accent-tone-danger-solid" />
            {{ t(dischargeReasonLabelKey(r)) }}
          </label>
        </div>
      </fieldset>

      <FormField id="discharge-note" :label="noteLabel" :required="reason === 'autre'" v-slot="{ describedBy }">
        <textarea id="discharge-note" v-model="note" rows="3" :maxlength="NOTE_MAX_LENGTH" :disabled="isSubmitting" :aria-describedby="describedBy"
                  :placeholder="t('toxico.stays.note_placeholder')" :class="[fieldClass, 'py-2']"></textarea>
      </FormField>

      <p class="rounded-card border p-3 text-base" :class="toneClasses('warning')">{{ t('toxico.stays.discharge_warning') }}</p>

      <p v-if="errorText" role="alert" class="rounded-card border p-3 text-base" :class="toneClasses('danger')">{{ errorText }}</p>
    </form>

    <template #footer>
      <ActionBar>
        <template #secondary>
          <AppButton variant="secondary" :disabled="isSubmitting" @click="close">{{ t('toxico.stays.cancel') }}</AppButton>
        </template>
        <AppButton type="submit" form="toxico-discharge-form" variant="danger" :disabled="isSubmitting" :loading="isSubmitting">
          {{ isSubmitting ? t('toxico.stays.submitting') : t('toxico.stays.confirm') }}
        </AppButton>
      </ActionBar>
    </template>
  </FullScreenPanel>
</template>

<script setup>
import { ref, computed, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { useToxicoStore } from '@/stores/toxicoStore';
import { DISCHARGE_REASONS, NOTE_MAX_LENGTH, dischargeReasonLabelKey, validateDischarge, apiErrorMessage } from '@/utils/toxicoStays';
import { AppButton, FormField, ActionBar, FullScreenPanel } from '@/components/ui';
import { toneClasses } from '@/design/tones';

const props = defineProps({
  dossierId: { type: Number, required: true },
  patientName: { type: String, default: '' },
});
const emit = defineEmits(['close', 'discharged']);
const { t } = useI18n();
const toxicoStore = useToxicoStore();

// Style commun des champs ; la note est obligatoire pour le motif « autre », facultative sinon.
const fieldClass = 'block w-full min-h-11 lg:min-h-10 rounded-control border border-tone-neutral-border bg-white px-3 text-base text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600';
const noteLabel = computed(() => (reason.value === 'autre' ? t('toxico.stays.note_label') : `${t('toxico.stays.note_label')} ${t('toxico.stays.optional')}`));

const reason = ref('');
const note = ref('');
const isSubmitting = ref(false);
const errorKey = ref('');
const serverError = ref('');
const errorText = computed(() => serverError.value || (errorKey.value ? t(errorKey.value) : ''));

watch([reason, note], () => { errorKey.value = ''; serverError.value = ''; });

function close() {
  if (!isSubmitting.value) emit('close');
}

async function submit() {
  if (isSubmitting.value) return;
  const errors = validateDischarge({ reason: reason.value, note: note.value });
  if (errors.length) { errorKey.value = errors[0]; return; }
  isSubmitting.value = true;
  serverError.value = '';
  try {
    await toxicoStore.dischargePatient(props.dossierId, { reason: reason.value, note: note.value });
    emit('discharged');
  } catch (e) {
    const status = e?.response?.status;
    const fallback = status === 409 ? t('toxico.stays.errors.conflict')
      : status === 422 ? t('toxico.stays.errors.invalid')
      : status === 403 ? t('toxico.stays.errors.forbidden')
      : t('toxico.stays.errors.generic');
    serverError.value = apiErrorMessage(e, fallback);
  } finally {
    isSubmitting.value = false;
  }
}
</script>
