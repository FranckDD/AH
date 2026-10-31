<template>
  <section class="grid gap-3 rounded-card border border-tone-neutral-border bg-white p-3" data-testid="notes-editor" aria-labelledby="cat-notes-title">
    <div class="flex flex-wrap items-center justify-between gap-2">
      <div class="min-w-0">
        <h3 id="cat-notes-title" class="text-base font-semibold text-ink">{{ t('labCatalogue.notes.title') }}</h3>
        <p class="text-sm text-ink-muted">{{ t('labCatalogue.notes.help') }}</p>
      </div>
      <p class="text-sm text-ink-muted" data-testid="notes-count">{{ t('labCatalogue.notes.count', { n: notes.length, max: MAX_NOTES }) }}</p>
    </div>

    <p v-if="!notes.length" class="text-sm text-ink-muted">{{ t('labCatalogue.notes.none') }}</p>

    <ul v-else class="grid gap-3">
      <li v-for="(n, i) in notes" :key="i" :data-testid="`note-${i}`"
          class="grid gap-3 rounded-control border border-tone-neutral-border bg-tone-neutral-bg p-3">
        <div class="flex flex-wrap items-end justify-between gap-2">
          <p class="text-sm font-semibold text-ink">{{ t('labCatalogue.notes.item', { n: i + 1 }) }}</p>
          <div v-if="!disabled" class="flex flex-wrap gap-2">
            <AppButton size="sm" variant="ghost" :icon="ArrowUpIcon" :disabled="i === 0" :aria-label="t('labCatalogue.move_up')" @click="move(i, -1)" />
            <AppButton size="sm" variant="ghost" :icon="ArrowDownIcon" :disabled="i === notes.length - 1" :aria-label="t('labCatalogue.move_down')" @click="move(i, 1)" />
            <AppButton size="sm" variant="danger" :icon="TrashIcon" :aria-label="t('labCatalogue.notes.remove')" @click="remove(i)" />
          </div>
        </div>
        <div class="grid gap-3 sm:grid-cols-2">
          <FormField :id="`note-pos-${i}`" :label="t('labCatalogue.notes.position')" v-slot="{ describedBy }">
            <select :id="`note-pos-${i}`" :value="n.position" :disabled="disabled" :aria-describedby="describedBy" :class="fieldClass" @change="set(i, 'position', $event.target.value)">
              <option v-for="p in NOTE_POSITIONS" :key="p" :value="p">{{ t('labCatalogue.positions.' + p) }}</option>
            </select>
          </FormField>
          <FormField :id="`note-style-${i}`" :label="t('labCatalogue.notes.style')" v-slot="{ describedBy }">
            <select :id="`note-style-${i}`" :value="n.style" :disabled="disabled" :aria-describedby="describedBy" :class="fieldClass" @change="set(i, 'style', $event.target.value)">
              <option v-for="s in NOTE_STYLES" :key="s" :value="s">{{ t('labCatalogue.styles.' + s) }}</option>
            </select>
          </FormField>
        </div>
        <FormField :id="`note-text-${i}`" :label="t('labCatalogue.notes.text')" required :error="itemError(i)" v-slot="{ describedBy }">
          <textarea :id="`note-text-${i}`" :value="n.text" rows="3" :maxlength="NOTE_MAX" :disabled="disabled" :aria-describedby="describedBy"
                    :class="[fieldClass, 'py-2']" @input="set(i, 'text', $event.target.value)"></textarea>
          <p class="mt-1 text-sm text-ink-muted">{{ t('labCatalogue.notes.text_counter', { n: (n.text || '').length, max: NOTE_MAX }) }}</p>
        </FormField>
      </li>
    </ul>

    <p v-if="listError" role="alert" class="rounded-control border p-3 text-sm" :class="toneClasses('danger')">{{ t(listError) }}</p>

    <div v-if="!disabled">
      <AppButton variant="secondary" :icon="PlusIcon" :disabled="notes.length >= MAX_NOTES" @click="add">{{ t('labCatalogue.notes.add') }}</AppButton>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { ArrowDownIcon, ArrowUpIcon, PlusIcon, TrashIcon } from '@heroicons/vue/24/outline';
import { AppButton, FormField } from '@/components/ui';
import { toneClasses } from '@/design/tones';
import { CATALOGUE_LIMITS, NOTE_POSITIONS, NOTE_STYLES, blankNote, moveInList, validateNotes } from '@/utils/labCatalogue';

const props = defineProps({
  modelValue: { type: Array, default: () => [] },
  disabled: { type: Boolean, default: false },
  // Les erreurs par note n'apparaissent qu'apres une tentative d'enregistrement.
  showErrors: { type: Boolean, default: false },
});
const emit = defineEmits(['update:modelValue']);
const { t } = useI18n();

const MAX_NOTES = CATALOGUE_LIMITS.notes;
const NOTE_MAX = CATALOGUE_LIMITS.note_text;
const fieldClass = 'block w-full min-h-11 lg:min-h-10 rounded-control border border-tone-neutral-border bg-white px-3 text-sm text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600 disabled:bg-tone-neutral-bg';

const notes = computed(() => props.modelValue || []);
const verdict = computed(() => validateNotes(notes.value));
const itemError = (i) => (props.showErrors && verdict.value.items[i] ? t(verdict.value.items[i]) : '');
const listError = computed(() => (props.showErrors ? verdict.value.list : null));

const commit = (list) => emit('update:modelValue', list);
const set = (i, key, value) => commit(notes.value.map((n, j) => (j === i ? { ...n, [key]: value } : n)));
const add = () => { if (notes.value.length < MAX_NOTES) commit([...notes.value, blankNote()]); };
const remove = (i) => commit(notes.value.filter((_, j) => j !== i));
const move = (i, delta) => {
  const order = moveInList(notes.value.map((_, j) => j), i, delta);
  if (order) commit(order.map((j) => notes.value[j]));
};
</script>
