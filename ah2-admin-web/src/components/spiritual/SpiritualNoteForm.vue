<!-- Formulaire de note du conseiller spirituel (creation et modification). Seule la date est obligatoire.
     Ecriture en ligne : en cas de panne reseau le brouillon reste ouvert avec un message clair. -->
<template>
  <FullScreenPanel :title="note ? t('spiritualNotes.edit_title') : t('spiritualNotes.new_title')" @close="$emit('close')">
    <form id="spiritual-note-form" class="grid gap-4 p-4" novalidate @submit.prevent="submit">
      <p v-if="serverError" role="alert" class="rounded-control border p-3 text-base" :class="toneClasses('danger')">{{ serverError }}</p>

      <FormField id="sn-date" :label="t('spiritualNotes.field_date')" required :error="errorText('meeting_date')" v-slot="{ describedBy, invalid }">
        <input id="sn-date" v-model="form.meeting_date" type="date" :max="today" :aria-describedby="describedBy" :aria-invalid="invalid" :class="fieldClass" />
      </FormField>

      <fieldset class="grid gap-1">
        <legend class="mb-1 text-base font-medium text-ink">{{ t('spiritualNotes.field_items') }}</legend>
        <label v-for="f in CHECK_FIELDS" :key="f" class="flex min-h-11 cursor-pointer items-center gap-3 text-base text-ink">
          <input v-model="form[f]" type="checkbox" class="h-5 w-5 shrink-0" />
          {{ t('spiritualNotes.item_' + f) }}
        </label>
      </fieldset>

      <FormField id="sn-verse" :label="t('spiritualNotes.field_verse')" :error="errorText('verse_reference')" v-slot="{ describedBy, invalid }">
        <input id="sn-verse" v-model="form.verse_reference" type="text" maxlength="120" :aria-describedby="describedBy" :aria-invalid="invalid" :class="fieldClass" />
      </FormField>

      <label class="flex min-h-11 cursor-pointer items-center gap-3 text-base text-ink">
        <input v-model="form.no_one_spoke" type="checkbox" class="h-5 w-5 shrink-0" />
        {{ t('spiritualNotes.no_one_spoke') }}
      </label>

      <FormField id="sn-content" :label="t('spiritualNotes.field_content')" :error="errorText('content')" v-slot="{ describedBy, invalid }">
        <textarea id="sn-content" v-model="form.content" rows="6" maxlength="5000" :aria-describedby="describedBy" :aria-invalid="invalid" :class="fieldClass + ' py-2'"></textarea>
      </FormField>
    </form>
    <template #footer>
      <div class="flex flex-wrap justify-end gap-3 border-t border-tone-neutral-border bg-white p-4">
        <AppButton variant="secondary" @click="$emit('close')">{{ t('spiritualNotes.cancel') }}</AppButton>
        <AppButton type="submit" form="spiritual-note-form" :loading="saving">{{ t('spiritualNotes.save') }}</AppButton>
      </div>
    </template>
  </FullScreenPanel>
</template>

<script setup>
import { reactive, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { AppButton, FormField, FullScreenPanel } from '@/components/ui';
import { toneClasses } from '@/design/tones';
import { todayLocalISO } from '@/utils/localDate';
import { describeServerError } from '@/utils/serverError';
import { isNetworkUploadError } from '@/utils/connectionStatus';
import { SpiritualNoteGateway } from '@/services/SpiritualNoteGateway';
import { CHECK_FIELDS, emptyNote, validateNote } from '@/utils/spiritualNote';

const props = defineProps({ note: { type: Object, default: null } });
const emit = defineEmits(['close', 'saved']);
const { t } = useI18n();

const today = todayLocalISO();
const blank = emptyNote(today);
const form = reactive(props.note
  ? Object.fromEntries(Object.keys(blank).map((k) => [k, props.note[k] ?? blank[k]]))
  : blank);
const errors = ref({});
const serverError = ref('');
const saving = ref(false);
const fieldClass = 'block w-full min-h-11 rounded-control border border-tone-neutral-border bg-white px-3 text-base text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600';
const errorText = (k) => (errors.value[k] ? t(errors.value[k]) : '');

async function submit() {
  if (saving.value) return;
  serverError.value = '';
  const r = validateNote(form, today, props.note?.meeting_date);
  errors.value = r.errors;
  if (!r.ok) return;
  saving.value = true;
  try {
    const body = { ...form };
    // Date inchangee en modification : ne pas l'envoyer (une ancienne note reste modifiable).
    if (props.note && body.meeting_date === props.note.meeting_date) delete body.meeting_date;
    const saved = props.note
      ? await SpiritualNoteGateway.update(props.note.id, body)
      : await SpiritualNoteGateway.create(body);
    emit('saved', saved);
  } catch (e) {
    // Panne reseau : le formulaire reste ouvert avec le brouillon.
    serverError.value = isNetworkUploadError(e, typeof navigator !== 'undefined' ? navigator.onLine : undefined)
      ? t('spiritualNotes.err_network')
      : describeServerError(e, t('spiritualNotes.err_save'));
  } finally {
    saving.value = false;
  }
}
</script>
