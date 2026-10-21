<template>
  <div class="fixed inset-0 z-50 bg-gray-900/60 backdrop-blur-xs flex items-end md:items-center justify-center md:p-4" @click.self="close">
    <div class="w-full md:max-w-lg bg-white shadow-2xl rounded-t-2xl md:rounded-2xl border border-gray-200 flex flex-col max-h-[92vh]">
      <div class="px-4 md:px-6 py-4 border-b border-gray-100 bg-red-50 rounded-t-2xl flex items-start justify-between gap-3">
        <div class="min-w-0">
          <h3 class="text-lg font-bold text-red-800">{{ t('toxico.stays.discharge_title') }}</h3>
          <p v-if="patientName" class="text-sm text-red-700 truncate">{{ patientName }}</p>
        </div>
        <button type="button" @click="close" :disabled="isSubmitting" :aria-label="t('toxico.stays.cancel')"
                class="min-h-[44px] min-w-[44px] lg:min-h-0 lg:min-w-0 lg:p-1 flex items-center justify-center text-red-400 hover:text-red-700 disabled:opacity-50">
          <span class="text-2xl font-bold leading-none">&times;</span>
        </button>
      </div>

      <form @submit.prevent="submit" class="p-4 md:p-6 space-y-4 overflow-y-auto">
        <fieldset :disabled="isSubmitting">
          <legend class="block text-sm font-medium text-gray-700 mb-2">
            {{ t('toxico.stays.reason_label') }} <span class="text-red-500">*</span>
          </legend>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
            <label v-for="r in DISCHARGE_REASONS" :key="r"
                   :class="['flex items-center gap-2 px-3 min-h-[44px] lg:min-h-[40px] rounded-lg border cursor-pointer text-sm',
                            reason === r ? 'border-red-500 bg-red-50 text-red-800 font-semibold' : 'border-gray-300 text-gray-700 hover:bg-gray-50']">
              <input type="radio" name="discharge-reason" :value="r" v-model="reason" class="text-red-600 focus:ring-red-500" />
              {{ t(dischargeReasonLabelKey(r)) }}
            </label>
          </div>
        </fieldset>

        <div>
          <label for="discharge-note" class="block text-sm font-medium text-gray-700 mb-1">
            {{ t('toxico.stays.note_label') }}
            <span v-if="reason === 'autre'" class="text-red-500">*</span>
            <span v-else class="text-gray-400 text-xs">{{ t('toxico.stays.optional') }}</span>
          </label>
          <textarea id="discharge-note" v-model="note" rows="3" :maxlength="NOTE_MAX_LENGTH" :disabled="isSubmitting"
                    :placeholder="t('toxico.stays.note_placeholder')"
                    class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-red-500 focus:border-red-500"></textarea>
        </div>

        <p class="text-xs text-gray-500">{{ t('toxico.stays.discharge_warning') }}</p>

        <div v-if="errorText" role="alert" class="bg-red-50 border-l-4 border-red-500 p-3 rounded-sm text-sm text-red-700">{{ errorText }}</div>

        <div class="flex flex-col-reverse sm:flex-row sm:justify-end gap-2 pt-2 border-t border-gray-100">
          <button type="button" @click="close" :disabled="isSubmitting"
                  class="min-h-[44px] lg:min-h-[40px] px-4 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 font-medium disabled:opacity-50">
            {{ t('toxico.stays.cancel') }}
          </button>
          <button type="submit" :disabled="isSubmitting"
                  class="min-h-[44px] lg:min-h-[40px] px-4 bg-red-600 text-white rounded-lg hover:bg-red-700 font-medium disabled:opacity-60 disabled:cursor-not-allowed">
            {{ isSubmitting ? t('toxico.stays.submitting') : t('toxico.stays.confirm') }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { useToxicoStore } from '@/stores/toxicoStore';
import { DISCHARGE_REASONS, NOTE_MAX_LENGTH, dischargeReasonLabelKey, validateDischarge, apiErrorMessage } from '@/utils/toxicoStays';

const props = defineProps({
  dossierId: { type: Number, required: true },
  patientName: { type: String, default: '' },
});
const emit = defineEmits(['close', 'discharged']);
const { t } = useI18n();
const toxicoStore = useToxicoStore();

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
