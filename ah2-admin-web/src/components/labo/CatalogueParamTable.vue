<template>
  <div class="grid gap-3">
    <p v-if="!params.length" class="text-sm text-ink-muted">{{ t('labCatalogue.param.none') }}</p>

    <ul class="grid gap-3">
      <li v-for="(p, i) in params" :key="p.id" :data-testid="`param-${p.id}`"
          class="rounded-card border border-tone-neutral-border bg-white p-3 shadow-card">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <div class="min-w-0">
            <p class="text-sm font-semibold text-ink">
              {{ p.print_label || p.nom_parametre }}
              <StatusBadge v-if="p.is_active === false" tone="neutral" :label="t('labCatalogue.inactive')" />
            </p>
            <p class="text-sm text-ink-muted">
              {{ t('labCatalogue.kinds.' + p.result_kind) }}<span v-if="p.unite"> | {{ p.unite }}</span>
              <span v-if="p.print_label && p.print_label !== p.nom_parametre"> | {{ p.nom_parametre }}</span>
              <span v-if="p.group_label" data-testid="param-group"> | {{ p.group_label }}</span>
              <span> | {{ t('labCatalogue.param.ranges_count', { n: (p.ranges || []).length }) }}</span>
            </p>
          </div>
          <div class="flex flex-wrap gap-2">
            <template v-if="editable">
              <AppButton size="sm" variant="ghost" :icon="ArrowUpIcon" :disabled="busy || i === 0" :aria-label="t('labCatalogue.move_up')" @click="$emit('move', p, -1)" />
              <AppButton size="sm" variant="ghost" :icon="ArrowDownIcon" :disabled="busy || i === params.length - 1" :aria-label="t('labCatalogue.move_down')" @click="$emit('move', p, 1)" />
              <AppButton size="sm" variant="secondary" :icon="PencilSquareIcon" :disabled="busy" @click="startEdit(p)">{{ t('labCatalogue.edit') }}</AppButton>
              <AppButton size="sm" variant="secondary" :disabled="busy" @click="$emit('toggle-active', p)">
                {{ p.is_active === false ? t('labCatalogue.activate') : t('labCatalogue.deactivate') }}
              </AppButton>
              <AppButton size="sm" variant="danger" :icon="TrashIcon" :disabled="busy" @click="$emit('delete', p)">{{ t('labCatalogue.delete') }}</AppButton>
            </template>
            <AppButton size="sm" variant="brandOutline" :aria-expanded="openRanges === p.id" @click="openRanges = openRanges === p.id ? null : p.id">
              {{ t('labCatalogue.param.norms') }}
            </AppButton>
          </div>
        </div>

        <p v-if="inUse && inUse.id === p.id" role="alert" class="mt-3 flex flex-wrap items-center gap-3 rounded-control border p-3 text-sm" :class="toneClasses('warning')">
          <span>{{ inUse.message }}</span>
          <AppButton size="sm" variant="secondary" :disabled="busy" @click="$emit('deactivate-instead', p)">{{ t('labCatalogue.deactivate_instead') }}</AppButton>
        </p>

        <div v-if="openRanges === p.id" class="mt-3 border-t border-tone-neutral-border pt-3">
          <CatalogueRangeEditor :param="p" :editable="editable" :busy="busy" :error="rangeError"
                                @save="(e) => $emit('save-range', p, e)" @delete="(r) => $emit('delete-range', p, r)" />
        </div>
      </li>
    </ul>

    <form v-if="editable" class="grid gap-3 rounded-card border border-tone-neutral-border bg-tone-neutral-bg p-3" novalidate @submit.prevent="submit">
      <h3 class="text-sm font-semibold text-ink">{{ editingId ? t('labCatalogue.param.edit_title') : t('labCatalogue.param.add_title') }}</h3>
      <div class="grid gap-3 md:grid-cols-2">
        <FormField id="pm-nom" :label="t('labCatalogue.param.label')" required :error="errText('nom_parametre')" v-slot="{ describedBy }">
          <input id="pm-nom" v-model="f.nom_parametre" type="text" maxlength="200" :aria-describedby="describedBy" :class="fieldClass" />
        </FormField>
        <FormField id="pm-print" :label="t('labCatalogue.param.print_label')" :help="t('labCatalogue.param.print_label_help')" :error="errText('print_label')" v-slot="{ describedBy }">
          <input id="pm-print" v-model="f.print_label" type="text" maxlength="200" :aria-describedby="describedBy" :class="fieldClass" />
        </FormField>
        <FormField id="pm-group" :label="t('labCatalogue.param.group_label')" :help="t('labCatalogue.param.group_label_help')" :error="errText('group_label')" v-slot="{ describedBy }">
          <input id="pm-group" v-model="f.group_label" type="text" maxlength="80" :aria-describedby="describedBy" :class="fieldClass" />
        </FormField>
        <FormField id="pm-unit" :label="t('labCatalogue.param.unit')" :error="errText('unite')" v-slot="{ describedBy }">
          <input id="pm-unit" v-model="f.unite" type="text" maxlength="40" :aria-describedby="describedBy" :class="fieldClass" />
        </FormField>
        <FormField id="pm-kind" :label="t('labCatalogue.param.kind')" required :error="errText('result_kind')" v-slot="{ describedBy }">
          <select id="pm-kind" v-model="f.result_kind" :aria-describedby="describedBy" :class="fieldClass">
            <option v-for="k in RESULT_KINDS" :key="k" :value="k">{{ t('labCatalogue.kinds.' + k) }}</option>
          </select>
        </FormField>
      </div>
      <FormField id="pm-norm-text" :label="t('labCatalogue.param.norm_text')" :help="t('labCatalogue.param.norm_text_help')" :error="errText('norm_text')" v-slot="{ describedBy }">
        <input id="pm-norm-text" v-model="f.norm_text" type="text" maxlength="200" :aria-describedby="describedBy" :class="[fieldClass, 'font-mono']" />
      </FormField>
      <FormField v-if="f.result_kind === 'choice'" id="pm-choices" :label="t('labCatalogue.param.choices')" :help="t('labCatalogue.param.choices_help')" :error="errText('choices')" v-slot="{ describedBy }">
        <textarea id="pm-choices" v-model="f.choices_text" rows="3" :aria-describedby="describedBy" :class="[fieldClass, 'py-2']"></textarea>
      </FormField>
      <label class="flex min-h-11 items-center gap-3 text-sm text-ink">
        <input id="pm-active" v-model="f.is_active" type="checkbox" class="h-5 w-5 accent-brand-600" />
        <span>{{ t('labCatalogue.param.active') }}</span>
      </label>
      <p v-if="error" role="alert" class="rounded-control border p-3 text-sm" :class="toneClasses('danger')">{{ error }}</p>
      <div class="flex flex-wrap gap-2">
        <AppButton type="submit" variant="lab" :loading="busy" :disabled="busy">{{ editingId ? t('labCatalogue.save') : t('labCatalogue.param.add') }}</AppButton>
        <AppButton v-if="editingId" variant="ghost" :disabled="busy" @click="reset">{{ t('labCatalogue.cancel') }}</AppButton>
      </div>
    </form>
  </div>
</template>

<script setup>
import { computed, reactive, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { ArrowDownIcon, ArrowUpIcon, PencilSquareIcon, TrashIcon } from '@heroicons/vue/24/outline';
import { AppButton, FormField, StatusBadge } from '@/components/ui';
import { toneClasses } from '@/design/tones';
import { RESULT_KINDS, validateParam, paramPayload } from '@/utils/labCatalogue';
import CatalogueRangeEditor from '@/components/labo/CatalogueRangeEditor.vue';

const props = defineProps({
  exam: { type: Object, required: true },
  editable: { type: Boolean, default: false },
  busy: { type: Boolean, default: false },
  error: { type: String, default: '' },
  rangeError: { type: String, default: '' },
  inUse: { type: Object, default: null },
});
const emit = defineEmits(['save-param', 'move', 'toggle-active', 'delete', 'deactivate-instead', 'save-range', 'delete-range']);
const { t } = useI18n();

const fieldClass = 'block w-full min-h-11 lg:min-h-10 rounded-control border border-tone-neutral-border bg-white px-3 text-sm text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600';

const params = computed(() => props.exam.parameters || []);
const openRanges = ref(null);
const editingId = ref(null);
const blank = () => ({ nom_parametre: '', print_label: '', group_label: '', norm_text: '', unite: '', result_kind: 'numeric', choices_text: '', is_active: true });
const f = reactive(blank());
const errors = ref({});
const errText = (k) => (errors.value[k] ? t(errors.value[k]) : '');

function reset() {
  Object.assign(f, blank());
  editingId.value = null;
  errors.value = {};
}

function startEdit(p) {
  editingId.value = p.id;
  errors.value = {};
  Object.assign(f, {
    nom_parametre: p.nom_parametre || '', print_label: p.print_label || '', group_label: p.group_label || '',
    norm_text: p.norm_text || '', unite: p.unite || '',
    result_kind: p.result_kind || 'numeric', choices_text: (p.choices || []).join('\n'), is_active: p.is_active !== false,
  });
}

function submit() {
  errors.value = validateParam(f);
  if (Object.keys(errors.value).length) return;
  emit('save-param', { id: editingId.value, payload: paramPayload(f), done: reset });
}
</script>
