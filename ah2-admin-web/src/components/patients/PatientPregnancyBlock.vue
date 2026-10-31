<template>
  <AppCard :title="$t('pregnancy.block_title')" data-testid="pregnancy-block-file">
    <template v-if="canEditFile" #actions>
      <AppButton v-if="!editing" variant="secondary" :disabled="!online || !loaded" @click="startEdit">{{ $t('pregnancy.file_edit') }}</AppButton>
    </template>

    <p v-if="!loaded" class="text-base text-ink-muted" role="status">{{ $t('pregnancy.file_unavailable') }}</p>

    <template v-else>
      <dl v-if="!editing" class="grid gap-1 text-base text-ink">
        <div><dt class="inline font-medium">{{ $t('pregnancy.status_label') }} :</dt> <dd class="inline">{{ $t('pregnancy.status_' + status) }}</dd></div>
        <div><dt class="inline font-medium">{{ $t('pregnancy.dpa_short') }} :</dt> <dd class="inline">{{ dpaText || $t('pregnancy.file_not_set') }}</dd></div>
        <div><dt class="inline font-medium">{{ $t('pregnancy.program_label_short') }} :</dt> <dd class="inline">{{ patientFile.pregnancy_program_number || $t('pregnancy.file_not_set') }}</dd></div>
      </dl>

      <form v-else class="grid gap-4 md:grid-cols-2" @submit.prevent="save">
        <FormField id="file-preg-status" :label="$t('pregnancy.status_label')" v-slot="{ describedBy }">
          <select id="file-preg-status" v-model="form.pregnancy_status" :aria-describedby="describedBy" :class="fieldClass">
            <option v-for="st in PREGNANCY_STATUSES" :key="st" :value="st">{{ $t('pregnancy.status_' + st) }}</option>
          </select>
        </FormField>
        <FormField id="file-preg-dpa" :label="$t('pregnancy.dpa_label')" v-slot="{ describedBy }">
          <input id="file-preg-dpa" v-model="form.expected_delivery_date" type="date" :aria-describedby="describedBy" :class="fieldClass" />
        </FormField>
        <div class="md:col-span-2">
          <FormField id="file-preg-program" :label="$t('pregnancy.program_label')" v-slot="{ describedBy }">
            <input id="file-preg-program" v-model="form.pregnancy_program_number" type="text" maxlength="50" autocomplete="off" :aria-describedby="describedBy" :class="fieldClass" />
          </FormField>
        </div>
        <p v-if="errorText" role="alert" class="text-base font-medium text-tone-danger-text md:col-span-2">{{ errorText }}</p>
        <div class="flex flex-wrap gap-2 md:col-span-2">
          <AppButton type="submit" :disabled="saving || !online" :loading="saving">{{ $t('pregnancy.file_save') }}</AppButton>
          <AppButton variant="ghost" :disabled="saving" @click="editing = false">{{ $t('pregnancy.file_cancel') }}</AppButton>
        </div>
      </form>

      <p v-if="canEditFile && !online" class="mt-3 text-base font-medium text-ink-muted" role="status" data-testid="pregnancy-offline">{{ $t('pregnancy.file_offline') }}</p>
    </template>
  </AppCard>
</template>

<script setup>
// Bloc "Grossesse" de la fiche patient. Monte seulement pour un role autorise a le voir (le parent le garde par
// authStore.hasRole) ; la modification passe par PUT /patients/{id} en LIGNE seulement : les champs de grossesse ne
// sont dans aucun flux de synchronisation (voir le fichier de regles de sync), il n existe pas de copie locale.
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import api from '@/services/api';
import { useAuthStore } from '@/stores/auth';
import { AppButton, AppCard, FormField } from '@/components/ui';
import { notify } from '@/utils/notify';
import { describeServerError } from '@/utils/serverError';
import { PREGNANCY_STATUSES, canEditPregnancyOnPatientFile } from '@/utils/pregnancy';

const props = defineProps({
  patientId: { type: [Number, String], required: true },
  // Bloc patient du dossier (null hors ligne : rien de lisible)
  patientFile: { type: Object, default: null },
});
const emit = defineEmits(['saved']);

const { t } = useI18n();
const authStore = useAuthStore();
const fieldClass = 'block w-full min-h-11 rounded-control border border-tone-neutral-border bg-white px-3 text-base text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600';

const canEditFile = computed(() => canEditPregnancyOnPatientFile(authStore));
const loaded = computed(() => !!props.patientFile && props.patientFile.pregnancy_status !== undefined);
const status = computed(() => (PREGNANCY_STATUSES.includes(props.patientFile?.pregnancy_status) ? props.patientFile.pregnancy_status : 'inconnu'));
const dpaText = computed(() => {
  const d = props.patientFile?.expected_delivery_date;
  return d ? String(d).slice(0, 10).split('-').reverse().join('/') : '';
});

const online = ref(typeof navigator === 'undefined' ? true : navigator.onLine);
const setOnline = () => { online.value = navigator.onLine; };
onMounted(() => { window.addEventListener('online', setOnline); window.addEventListener('offline', setOnline); });
onBeforeUnmount(() => { window.removeEventListener('online', setOnline); window.removeEventListener('offline', setOnline); });

const editing = ref(false);
const saving = ref(false);
const errorText = ref('');
const form = reactive({ pregnancy_status: 'inconnu', expected_delivery_date: '', pregnancy_program_number: '' });

function startEdit() {
  const f = props.patientFile || {};
  form.pregnancy_status = status.value;
  form.expected_delivery_date = f.expected_delivery_date ? String(f.expected_delivery_date).slice(0, 10) : '';
  form.pregnancy_program_number = f.pregnancy_program_number || '';
  errorText.value = '';
  editing.value = true;
}

async function save() {
  if (!online.value) { errorText.value = t('pregnancy.file_offline'); return; }
  saving.value = true;
  errorText.value = '';
  try {
    const body = { pregnancy_status: form.pregnancy_status };
    if (form.expected_delivery_date) body.expected_delivery_date = form.expected_delivery_date;
    if (form.pregnancy_program_number.trim()) body.pregnancy_program_number = form.pregnancy_program_number.trim();
    const { data } = await api.put(`/patients/${props.patientId}`, body);
    editing.value = false;
    notify('pregnancy.file_saved', {}, 'success');
    emit('saved', {
      pregnancy_status: data.pregnancy_status ?? body.pregnancy_status,
      expected_delivery_date: data.expected_delivery_date ?? body.expected_delivery_date ?? null,
      pregnancy_program_number: data.pregnancy_program_number ?? body.pregnancy_program_number ?? null,
    });
  } catch (err) {
    errorText.value = describeServerError(err, t('pregnancy.file_save_failed'));
  } finally {
    saving.value = false;
  }
}
</script>
