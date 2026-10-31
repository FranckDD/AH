<template>
  <form class="grid gap-4" novalidate @submit.prevent="submit">
    <div class="grid gap-4 md:grid-cols-2">
      <FormField id="cat-code" :label="t('labCatalogue.exam.code')" :required="isNew" :error="errText('code')" :help="isNew ? t('labCatalogue.exam.code_help') : t('labCatalogue.exam.code_locked')" v-slot="{ describedBy }">
        <input id="cat-code" v-model="form.code" type="text" :readonly="!isNew" :disabled="!editable" maxlength="20" autocomplete="off"
               :aria-describedby="describedBy" :class="[fieldClass, !isNew ? 'bg-tone-neutral-bg font-mono' : 'font-mono uppercase']" />
      </FormField>
      <FormField id="cat-nom" :label="t('labCatalogue.exam.name')" required :error="errText('nom')" v-slot="{ describedBy }">
        <input id="cat-nom" v-model="form.nom" type="text" :disabled="!editable" maxlength="200" :aria-describedby="describedBy" :class="fieldClass" />
      </FormField>
      <FormField id="cat-print-title" :label="t('labCatalogue.exam.print_title')" :help="t('labCatalogue.exam.print_title_help')" :error="errText('print_title')" v-slot="{ describedBy }">
        <input id="cat-print-title" v-model="form.print_title" type="text" :disabled="!editable" maxlength="200" :aria-describedby="describedBy" :class="fieldClass" />
      </FormField>
      <FormField id="cat-categorie" :label="t('labCatalogue.exam.category')" required :error="errText('categorie')" v-slot="{ describedBy }">
        <input id="cat-categorie" v-model="form.categorie" type="text" :disabled="!editable" maxlength="100" :aria-describedby="describedBy" :class="fieldClass" />
      </FormField>
      <FormField id="cat-section" :label="t('labCatalogue.exam.section')" :help="t('labCatalogue.exam.section_help')" :error="errText('section')" v-slot="{ describedBy }">
        <input id="cat-section" v-model="form.section" type="text" list="cat-section-list" :disabled="!editable" maxlength="120" :aria-describedby="describedBy" :class="fieldClass" />
        <datalist id="cat-section-list"><option v-for="s in sections" :key="s" :value="s" /></datalist>
      </FormField>
      <FormField id="cat-sort" :label="t('labCatalogue.exam.sort_order')" :help="t('labCatalogue.exam.sort_order_help')" :error="errText('sort_order')" v-slot="{ describedBy }">
        <input id="cat-sort" v-model="form.sort_order" type="number" min="0" step="1" :disabled="!editable" :aria-describedby="describedBy" :class="fieldClass" />
      </FormField>
    </div>

    <FormField id="cat-method" :label="t('labCatalogue.exam.method')" :help="t('labCatalogue.exam.method_help')" :error="errText('method')" v-slot="{ describedBy }">
      <textarea id="cat-method" v-model="form.method" rows="2" maxlength="1000" :disabled="!editable" :aria-describedby="describedBy" :class="[fieldClass, 'py-2']"></textarea>
    </FormField>

    <div class="grid gap-4 md:grid-cols-2">
      <FormField id="cat-family" :label="t('labCatalogue.exam.family')" required :error="errText('layout_family')" v-slot="{ describedBy }">
        <select id="cat-family" v-model="form.layout_family" :disabled="!editable" :aria-describedby="describedBy" :class="fieldClass">
          <option v-for="f in LAYOUT_FAMILIES" :key="f" :value="f">{{ t('labCatalogue.families.' + f) }}</option>
        </select>
        <p class="mt-1 text-sm text-ink-muted">{{ t('labCatalogue.families.' + form.layout_family + '_desc') }}</p>
      </FormField>
      <FormField id="cat-signature" :label="t('labCatalogue.exam.signature')" :help="t('labCatalogue.exam.signature_help')" :error="errText('signature_label')" v-slot="{ describedBy }">
        <input id="cat-signature" v-model="form.signature_label" type="text" :disabled="!editable" maxlength="200" :aria-describedby="describedBy" :class="fieldClass" />
      </FormField>
    </div>

    <CatalogueNotesEditor v-model="form.fixed_notes" :disabled="!editable" :show-errors="tried" />

    <div class="grid gap-4 md:grid-cols-2 md:items-start">
      <label class="flex min-h-11 items-center gap-3 text-sm text-ink">
        <input id="cat-active" v-model="form.is_active" type="checkbox" :disabled="!editable" class="h-5 w-5 accent-brand-600" />
        <span>{{ t('labCatalogue.exam.active') }}</span>
      </label>
      <div v-if="!isNew" class="rounded-control border border-tone-neutral-border bg-tone-neutral-bg p-3 text-sm" data-testid="cat-price">
        <p class="font-medium text-ink">{{ t('labCatalogue.exam.price') }} : <span class="font-mono">{{ priceText }}</span></p>
        <p class="mt-1 text-ink-muted">
          {{ t('labCatalogue.exam.price_readonly') }}
          <router-link v-if="canSeePriceLink" :to="{ name: 'system-config' }" class="font-medium text-brand-700 underline">{{ t('labCatalogue.exam.price_link') }}</router-link>
        </p>
      </div>
    </div>

    <p v-if="error" role="alert" class="rounded-control border p-3 text-sm" :class="toneClasses('danger')">{{ error }}</p>

    <ActionBar v-if="editable">
      <template v-if="!isNew" #secondary>
        <AppButton variant="danger" :icon="TrashIcon" :disabled="saving" @click="$emit('delete')">{{ t('labCatalogue.exam.delete') }}</AppButton>
      </template>
      <AppButton type="submit" variant="lab" :loading="saving" :disabled="saving">{{ isNew ? t('labCatalogue.exam.create') : t('labCatalogue.save') }}</AppButton>
    </ActionBar>
  </form>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { TrashIcon } from '@heroicons/vue/24/outline';
import { ActionBar, AppButton, FormField } from '@/components/ui';
import { toneClasses } from '@/design/tones';
import { LAYOUT_FAMILIES, validateExam, examPayload, notesFromExam } from '@/utils/labCatalogue';
import CatalogueNotesEditor from '@/components/labo/CatalogueNotesEditor.vue';

const props = defineProps({
  exam: { type: Object, default: null },
  editable: { type: Boolean, default: false },
  saving: { type: Boolean, default: false },
  error: { type: String, default: '' },
  sections: { type: Array, default: () => [] },
  canSeePriceLink: { type: Boolean, default: false },
});
const emit = defineEmits(['save', 'delete']);
const { t } = useI18n();

const fieldClass = 'block w-full min-h-11 lg:min-h-10 rounded-control border border-tone-neutral-border bg-white px-3 text-sm text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600 disabled:bg-tone-neutral-bg';

const isNew = computed(() => !props.exam);
const blank = () => ({ code: '', nom: '', print_title: '', categorie: '', section: '', method: '', layout_family: 'label_value', signature_label: '', sort_order: 0, is_active: true, fixed_notes: [] });
const fromExam = (e) => ({
  code: e.code || '', nom: e.nom || '', print_title: e.print_title || '', categorie: e.categorie || '', section: e.section || '',
  method: e.method || '', layout_family: e.layout_family || 'label_value', signature_label: e.signature_label || '',
  sort_order: e.sort_order ?? 0, is_active: e.is_active !== false, fixed_notes: notesFromExam(e),
});
const form = reactive(props.exam ? fromExam(props.exam) : blank());
const errors = ref({});
const tried = ref(false);

// Le brouillon survit aux rechargements de la liste : le formulaire n'est reinitialise que si les champs de
// l'examen changent cote serveur (ou si un autre examen est ouvert).
const signature = computed(() => (props.exam ? JSON.stringify(fromExam(props.exam)) + props.exam.id : 'new'));
watch(signature, () => {
  Object.assign(form, props.exam ? fromExam(props.exam) : blank());
  errors.value = {};
  tried.value = false;
});

const errText = (k) => (errors.value[k] ? t(errors.value[k]) : '');
const priceText = computed(() => `${new Intl.NumberFormat('fr-FR').format(Number(props.exam?.prix) || 0)} FCFA`);

function submit() {
  if (!props.editable) return;
  tried.value = true;
  errors.value = validateExam(form, { isNew: isNew.value });
  if (Object.keys(errors.value).length) return;
  emit('save', examPayload(form, { isNew: isNew.value }));
}
</script>
