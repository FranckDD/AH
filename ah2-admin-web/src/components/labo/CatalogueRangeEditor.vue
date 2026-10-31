<template>
  <div class="grid gap-3" :data-testid="`ranges-${param.id}`">
    <p v-if="!ranges.length" class="text-sm text-ink-muted">{{ t('labCatalogue.range.none') }}</p>
    <ul v-else class="grid gap-2">
      <li v-for="r in ranges" :key="r.id"
          class="flex flex-wrap items-center justify-between gap-2 rounded-control border border-tone-neutral-border bg-white p-3 text-sm">
        <span class="text-ink">
          <span class="font-semibold">{{ sexLabel(r.sexe) }}</span>
          <span class="text-ink-muted"> | {{ ageText(r) }}</span>
          <span v-if="gaText(r)" class="text-ink-muted"> | {{ gaText(r) }}</span>
          <span class="font-mono"> | {{ r.valeur_min }} - {{ r.valeur_max }}</span>
          <span v-if="r.display_text" class="font-mono text-ink-muted" data-testid="range-display"> | {{ t('labCatalogue.range.display_text') }} : {{ r.display_text }}</span>
        </span>
        <span v-if="editable" class="flex flex-wrap gap-2">
          <AppButton size="sm" variant="secondary" :icon="PencilSquareIcon" :disabled="busy" @click="edit(r)">{{ t('labCatalogue.edit') }}</AppButton>
          <AppButton size="sm" variant="danger" :icon="TrashIcon" :disabled="busy" @click="$emit('delete', r)">{{ t('labCatalogue.delete') }}</AppButton>
        </span>
      </li>
    </ul>

    <form v-if="editable" class="grid gap-3 rounded-control border border-tone-neutral-border bg-tone-neutral-bg p-3" novalidate @submit.prevent="submit">
      <h4 class="text-sm font-semibold text-ink">{{ editingId ? t('labCatalogue.range.edit_title') : t('labCatalogue.range.add_title') }}</h4>
      <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <FormField :id="`rg-sex-${param.id}`" :label="t('labCatalogue.range.sex')" v-slot="{ describedBy }">
          <select :id="`rg-sex-${param.id}`" v-model="f.sexe" :aria-describedby="describedBy" :class="fieldClass">
            <option v-for="s in SEXES" :key="s" :value="s">{{ sexLabel(s) }}</option>
          </select>
        </FormField>
        <FormField :id="`rg-min-${param.id}`" :label="t('labCatalogue.range.min')" required v-slot="{ describedBy }">
          <input :id="`rg-min-${param.id}`" v-model="f.valeur_min" type="text" inputmode="decimal" :aria-describedby="describedBy" :class="fieldClass" />
        </FormField>
        <FormField :id="`rg-max-${param.id}`" :label="t('labCatalogue.range.max')" required v-slot="{ describedBy }">
          <input :id="`rg-max-${param.id}`" v-model="f.valeur_max" type="text" inputmode="decimal" :aria-describedby="describedBy" :class="fieldClass" />
        </FormField>
      </div>

      <FormField :id="`rg-display-${param.id}`" :label="t('labCatalogue.range.display_text')" :help="t('labCatalogue.range.display_text_help')" v-slot="{ describedBy }">
        <input :id="`rg-display-${param.id}`" v-model="f.display_text" type="text" maxlength="60" :aria-describedby="describedBy" :class="[fieldClass, 'font-mono']" />
      </FormField>

      <div class="grid gap-3 sm:grid-cols-2">
        <fieldset class="grid gap-2">
          <legend class="text-sm font-medium text-ink">{{ t('labCatalogue.range.age') }}</legend>
          <div class="grid grid-cols-[1fr_1fr] items-start gap-2">
            <input :id="`rg-agemin-${param.id}`" v-model="f.ageMin" type="text" inputmode="numeric" :aria-label="t('labCatalogue.range.age_min')"
                   :placeholder="t('labCatalogue.range.age_min')" :class="fieldClass" />
            <input :id="`rg-agemax-${param.id}`" v-model="f.ageMax" type="text" inputmode="numeric" :aria-label="t('labCatalogue.range.age_max')"
                   :placeholder="t('labCatalogue.range.age_max')" :class="fieldClass" />
          </div>
          <label class="grid gap-1 text-sm text-ink-muted">
            {{ t('labCatalogue.range.age_unit') }}
            <select :id="`rg-unit-${param.id}`" v-model="f.unit" :class="fieldClass">
              <option v-for="u in AGE_UNITS" :key="u" :value="u">{{ t('labCatalogue.units.' + u) }}</option>
            </select>
          </label>
          <p class="text-sm text-ink-muted">{{ t('labCatalogue.range.age_help') }}</p>
          <p v-if="agePreview" class="text-sm text-ink-muted" data-testid="age-preview">{{ agePreview }}</p>
        </fieldset>

        <fieldset class="grid gap-2">
          <legend class="text-sm font-medium text-ink">{{ t('labCatalogue.range.ga') }}</legend>
          <div class="grid grid-cols-[1fr_1fr] items-start gap-2">
            <input :id="`rg-gamin-${param.id}`" v-model="f.gaMin" type="text" inputmode="numeric" :aria-label="t('labCatalogue.range.ga_min')"
                   :placeholder="t('labCatalogue.range.ga_min')" :class="fieldClass" />
            <input :id="`rg-gamax-${param.id}`" v-model="f.gaMax" type="text" inputmode="numeric" :aria-label="t('labCatalogue.range.ga_max')"
                   :placeholder="t('labCatalogue.range.ga_max')" :class="fieldClass" />
          </div>
          <p class="text-sm text-ink-muted">{{ t('labCatalogue.range.ga_help') }}</p>
        </fieldset>
      </div>

      <ul v-if="shownErrors.length" role="alert" class="grid gap-1 rounded-control border p-3 text-sm" :class="toneClasses('danger')">
        <li v-for="k in shownErrors" :key="k">{{ t(k) }}</li>
      </ul>
      <ul v-if="warnings.length" role="status" class="grid gap-1 rounded-control border p-3 text-sm" :class="toneClasses('warning')" data-testid="range-warning">
        <li v-for="k in warnings" :key="k">{{ t(k) }}</li>
      </ul>
      <p v-if="error" role="alert" class="rounded-control border p-3 text-sm" :class="toneClasses('danger')">{{ error }}</p>

      <div class="flex flex-wrap gap-2">
        <AppButton type="submit" variant="lab" :loading="busy" :disabled="busy">{{ editingId ? t('labCatalogue.save') : t('labCatalogue.range.add') }}</AppButton>
        <AppButton v-if="editingId" variant="ghost" :disabled="busy" @click="reset">{{ t('labCatalogue.cancel') }}</AppButton>
      </div>
    </form>
  </div>
</template>

<script setup>
import { computed, reactive, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { PencilSquareIcon, TrashIcon } from '@heroicons/vue/24/outline';
import { AppButton, FormField } from '@/components/ui';
import { toneClasses } from '@/design/tones';
import { AGE_UNITS, SEXES, ageBoundLabel, toDays, validateRange, rangePayload } from '@/utils/labCatalogue';

const props = defineProps({
  param: { type: Object, required: true },
  editable: { type: Boolean, default: false },
  busy: { type: Boolean, default: false },
  error: { type: String, default: '' },
});
const emit = defineEmits(['save', 'delete']);
const { t } = useI18n();

const fieldClass = 'block w-full min-h-11 lg:min-h-10 rounded-control border border-tone-neutral-border bg-white px-3 text-sm text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600';

const ranges = computed(() => props.param.ranges || []);
const blank = () => ({ sexe: 'X', valeur_min: '', valeur_max: '', display_text: '', ageMin: '', ageMax: '', unit: 'jours', gaMin: '', gaMax: '' });
const f = reactive(blank());
const editingId = ref(null);
const tried = ref(false);

const sexLabel = (s) => t('labCatalogue.range.sex_' + s);
const ageText = (r) => {
  const lo = r.age_min_days; const hi = r.age_max_days;
  if ((lo === null || lo === undefined) && (hi === null || hi === undefined)) return t('labCatalogue.range.all_ages');
  const a = lo === null || lo === undefined ? '0' : ageBoundLabel(lo, t);
  const b = hi === null || hi === undefined ? t('labCatalogue.range.no_limit') : ageBoundLabel(hi, t);
  return `${a} - ${b}`;
};
const gaText = (r) => {
  const lo = r.ga_min_weeks; const hi = r.ga_max_weeks;
  if ((lo === null || lo === undefined) && (hi === null || hi === undefined)) return '';
  return `${t('labCatalogue.range.ga_short')} ${lo ?? 0} - ${hi ?? t('labCatalogue.range.no_limit')}`;
};

// Valeurs saisies -> plage (ages convertis en jours avec l'unite choisie, memes regles que le serveur).
const draft = computed(() => {
  const empty = (v) => v === '' || v === null || v === undefined;
  const lo = empty(f.ageMin) ? null : toDays(f.ageMin, f.unit);
  const hi = empty(f.ageMax) ? null : toDays(f.ageMax, f.unit);
  const intOrNaN = (v) => (empty(v) ? null : (Number.isInteger(Number(v)) ? Number(v) : NaN));
  return {
    sexe: f.sexe,
    age_min_days: empty(f.ageMin) ? null : (lo === null ? NaN : lo),
    age_max_days: empty(f.ageMax) ? null : (hi === null ? NaN : hi),
    ga_min_weeks: intOrNaN(f.gaMin),
    ga_max_weeks: intOrNaN(f.gaMax),
    valeur_min: f.valeur_min,
    valeur_max: f.valeur_max,
    display_text: f.display_text,
  };
});
const others = computed(() => ranges.value.filter((r) => r.id !== editingId.value));
const verdict = computed(() => validateRange(draft.value, others.value));
const warnings = computed(() => verdict.value.warnings);
// Les erreurs n'apparaissent qu'apres une tentative d'enregistrement (pas pendant la frappe).
const shownErrors = computed(() => (tried.value ? verdict.value.errors : []));
const agePreview = computed(() => {
  const d = draft.value;
  const lo = Number.isInteger(d.age_min_days) ? d.age_min_days : null;
  const hi = Number.isInteger(d.age_max_days) ? d.age_max_days : null;
  if (lo === null && hi === null) return '';
  return t('labCatalogue.range.age_days_preview', { min: lo ?? '-', max: hi ?? '-' });
});

function reset() {
  Object.assign(f, blank());
  editingId.value = null;
  tried.value = false;
}

// Valeur exacte d'un nombre de jours dans une unite (null si l'unite ne redonne pas exactement ce nombre).
function exactIn(days, unit) {
  if (unit === 'jours') return days;
  const factor = unit === 'ans' ? 365.25 : unit === 'mois' ? 30.4375 : 7;
  for (const v of [Math.round(days / factor), Math.round(days / factor) - 1, Math.round(days / factor) + 1]) {
    if (v >= 0 && toDays(v, unit) === days) return v;
  }
  return null;
}

function edit(r) {
  editingId.value = r.id;
  tried.value = false;
  const lo = r.age_min_days ?? null;
  const hi = r.age_max_days ?? null;
  // Une seule unite pour les deux bornes : la plus grande qui redonne exactement les nombres de jours.
  let unit = 'jours';
  if (lo !== null || hi !== null) {
    for (const u of ['ans', 'mois', 'semaines']) {
      if ((lo === null || exactIn(lo, u) !== null) && (hi === null || exactIn(hi, u) !== null)) { unit = u; break; }
    }
  }
  Object.assign(f, {
    sexe: r.sexe, valeur_min: String(r.valeur_min), valeur_max: String(r.valeur_max), display_text: r.display_text || '',
    ageMin: lo === null ? '' : String(exactIn(lo, unit)), ageMax: hi === null ? '' : String(exactIn(hi, unit)),
    unit, gaMin: r.ga_min_weeks ?? '', gaMax: r.ga_max_weeks ?? '',
  });
}

function submit() {
  tried.value = true;
  if (verdict.value.errors.length) return;
  emit('save', { id: editingId.value, payload: rangePayload(draft.value), done: reset });
}
</script>
