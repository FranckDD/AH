<template>
  <FullScreenPanel :title="t('labParams.title', { name: examen.nom })" wide @close="$emit('close')">
    <div class="grid gap-4">
      <p v-if="errorMessage" role="alert" class="rounded-control border border-tone-danger-border bg-tone-danger-bg p-3 text-base text-tone-danger-text">{{ errorMessage }}</p>

      <p v-if="!labStore.currentExamParams.length" class="text-base text-ink-muted">{{ t('labParams.empty') }}</p>

      <article v-for="(p, idx) in labStore.currentExamParams" :key="p.id" class="grid gap-3 rounded-card border border-tone-neutral-border bg-white p-4">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <div class="min-w-0">
            <p class="text-base font-semibold text-ink">{{ p.nom }}</p>
            <p class="text-sm text-ink-muted">{{ p.unite || '-' }} / {{ p.type === 'text' ? t('labParams.type_text') : t('labParams.type_numeric') }}</p>
          </div>
          <div class="flex flex-wrap gap-2">
            <template v-if="canReorder">
              <AppButton variant="ghost" :icon="ArrowUpIcon" :disabled="idx === 0 || reordering" :aria-label="t('labParams.move_up', { name: p.nom })" @click="move(idx, -1)" />
              <AppButton variant="ghost" :icon="ArrowDownIcon" :disabled="idx === labStore.currentExamParams.length - 1 || reordering" :aria-label="t('labParams.move_down', { name: p.nom })" @click="move(idx, 1)" />
            </template>
            <AppButton variant="secondary" :icon="PencilSquareIcon" @click="startEdit(p)">{{ t('labParams.edit') }}</AppButton>
            <AppButton v-if="canDelete" variant="danger" :icon="TrashIcon" @click="removeParam(p)">{{ t('labParams.delete') }}</AppButton>
          </div>
        </div>

        <div>
          <p class="text-sm font-semibold text-ink">{{ t('labParams.ranges') }}</p>
          <p v-if="!(p.ranges || []).length" class="text-sm text-ink-muted">{{ t('labParams.no_range') }}</p>
          <ul class="grid gap-1">
            <li v-for="r in p.ranges" :key="r.id" class="flex items-center justify-between gap-2 text-base text-ink">
              <span>{{ sexLabel(r.sexe) }}, {{ r.age_min }}-{{ r.age_max }} : {{ r.min }} - {{ r.max }}</span>
              <AppButton variant="ghost" :icon="TrashIcon" :aria-label="t('labParams.delete')" @click="removeRange(r)" />
            </li>
          </ul>
          <form class="mt-2 grid grid-cols-2 gap-2 md:grid-cols-6 md:items-end" @submit.prevent="addRange(p)">
            <FormField :id="`rg-sex-${p.id}`" :label="t('labParams.ranges')" v-slot="{ describedBy }">
              <select :id="`rg-sex-${p.id}`" v-model="rangeForm(p.id).sexe" :aria-describedby="describedBy" :class="fieldClass">
                <option value="X">{{ t('labParams.sex_x') }}</option>
                <option value="M">{{ t('labParams.sex_m') }}</option>
                <option value="F">{{ t('labParams.sex_f') }}</option>
              </select>
            </FormField>
            <FormField :id="`rg-amin-${p.id}`" :label="t('labParams.age_min')" v-slot="{ describedBy }">
              <input :id="`rg-amin-${p.id}`" v-model.number="rangeForm(p.id).age_min" type="number" min="0" :aria-describedby="describedBy" :class="fieldClass" />
            </FormField>
            <FormField :id="`rg-amax-${p.id}`" :label="t('labParams.age_max')" v-slot="{ describedBy }">
              <input :id="`rg-amax-${p.id}`" v-model.number="rangeForm(p.id).age_max" type="number" min="0" :aria-describedby="describedBy" :class="fieldClass" />
            </FormField>
            <FormField :id="`rg-vmin-${p.id}`" :label="t('labParams.value_min')" v-slot="{ describedBy }">
              <input :id="`rg-vmin-${p.id}`" v-model.number="rangeForm(p.id).valeur_min" type="number" step="any" required :aria-describedby="describedBy" :class="fieldClass" />
            </FormField>
            <FormField :id="`rg-vmax-${p.id}`" :label="t('labParams.value_max')" v-slot="{ describedBy }">
              <input :id="`rg-vmax-${p.id}`" v-model.number="rangeForm(p.id).valeur_max" type="number" step="any" required :aria-describedby="describedBy" :class="fieldClass" />
            </FormField>
            <AppButton type="submit" variant="secondary" :icon="PlusIcon">{{ t('labParams.add_range') }}</AppButton>
          </form>
        </div>
      </article>

      <form id="param-form" class="grid gap-3 rounded-card border border-tone-neutral-border bg-tone-neutral-bg p-4 md:grid-cols-3" @submit.prevent="saveParam">
        <p class="text-base font-semibold text-ink md:col-span-3">{{ editingId ? t('labParams.edit') : t('labParams.add') }}</p>
        <FormField id="param-name" :label="t('labParams.name')" required v-slot="{ describedBy }">
          <input id="param-name" v-model="form.nom_parametre" type="text" required :aria-describedby="describedBy" :class="fieldClass" />
        </FormField>
        <FormField id="param-unit" :label="t('labParams.unit')" v-slot="{ describedBy }">
          <input id="param-unit" v-model="form.unite" type="text" :aria-describedby="describedBy" :class="fieldClass" />
        </FormField>
        <FormField id="param-type" :label="t('labParams.type_label')" v-slot="{ describedBy }">
          <select id="param-type" v-model="form.type_valeur" :aria-describedby="describedBy" :class="fieldClass">
            <option value="numeric">{{ t('labParams.type_numeric') }}</option>
            <option value="text">{{ t('labParams.type_text') }}</option>
          </select>
        </FormField>
        <div class="md:col-span-3">
          <AppButton type="submit" :icon="CheckCircleIcon">{{ t('labParams.save') }}</AppButton>
        </div>
      </form>
    </div>

    <template #footer>
      <ActionBar>
        <AppButton variant="secondary" @click="$emit('close')">{{ t('labParams.close') }}</AppButton>
      </ActionBar>
    </template>
  </FullScreenPanel>
</template>

<script setup>
// Parametres d'un examen du catalogue : ajouter, modifier, supprimer, et leurs plages de reference
// (sexe, age, min/max). L'ordre d'affichage (parametres.ordre) se regle avec les fleches monter/descendre (admin).
import { reactive, ref, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { useLabStore } from '@/stores/labStore';
import { useAuthStore } from '@/stores/auth';
import { describeServerError } from '@/utils/serverError';
import { ArrowUpIcon, ArrowDownIcon, PencilSquareIcon, TrashIcon, PlusIcon, CheckCircleIcon } from '@heroicons/vue/24/outline';
import { AppButton, FormField, ActionBar, FullScreenPanel } from '@/components/ui';

const props = defineProps({ examen: { type: Object, required: true } });
defineEmits(['close']);

const { t } = useI18n();
const labStore = useLabStore();
const authStore = useAuthStore();
const fieldClass = 'block w-full min-h-11 lg:min-h-10 rounded-control border border-tone-neutral-border bg-white px-3 text-base text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600';

// Suppression d'un parametre : administrateur seul (meme regle que le serveur).
const canDelete = computed(() => authStore.hasRole(['admin']));
// Ordre des parametres : administrateur seul (meme regle que le serveur).
const canReorder = computed(() => authStore.hasRole(['admin']));
const reordering = ref(false);
const errorMessage = ref('');
const editingId = ref(null);
const form = reactive({ nom_parametre: '', unite: '', type_valeur: 'numeric' });
const rangeForms = reactive({});

const rangeForm = (id) => {
    if (!rangeForms[id]) rangeForms[id] = { sexe: 'X', age_min: 0, age_max: 150, valeur_min: null, valeur_max: null };
    return rangeForms[id];
};
const sexLabel = (s) => (s === 'M' ? t('labParams.sex_m') : s === 'F' ? t('labParams.sex_f') : t('labParams.sex_x'));

onMounted(() => { labStore.fetchExamParams(props.examen.id); });

const run = async (fn) => {
    errorMessage.value = '';
    try { await fn(); return true; } catch (err) {
        errorMessage.value = describeServerError(err, err?.message || '');
        return false;
    }
};

const startEdit = (p) => {
    editingId.value = p.id;
    form.nom_parametre = p.nom;
    form.unite = p.unite || '';
    form.type_valeur = p.type === 'text' ? 'text' : 'numeric';
};
const resetForm = () => { editingId.value = null; form.nom_parametre = ''; form.unite = ''; form.type_valeur = 'numeric'; };

const saveParam = async () => {
    const payload = { nom_parametre: form.nom_parametre, unite: form.unite, type_valeur: form.type_valeur, input_type: form.type_valeur };
    const ok = await run(() => editingId.value
        ? labStore.updateParam(editingId.value, props.examen.id, payload)
        : labStore.addParam(props.examen.id, payload));
    if (ok) resetForm();
};

const removeParam = async (p) => {
    if (!window.confirm(t('labParams.confirm_delete'))) return;
    await run(() => labStore.deleteParam(p.id, props.examen.id));
};

const addRange = async (p) => {
    const f = rangeForm(p.id);
    const ok = await run(() => labStore.addRange(p.id, props.examen.id, {
        sexe: f.sexe, age_min: f.age_min, age_max: f.age_max, valeur_min: f.valeur_min, valeur_max: f.valeur_max,
    }));
    if (ok) { f.valeur_min = null; f.valeur_max = null; }
};
const move = async (idx, delta) => {
    const ids = labStore.currentExamParams.map((x) => x.id);
    const to = idx + delta;
    if (to < 0 || to >= ids.length) return;
    [ids[idx], ids[to]] = [ids[to], ids[idx]];
    reordering.value = true;
    await run(() => labStore.reorderParams(props.examen.id, ids));
    reordering.value = false;
};
const removeRange = async (r) => { await run(() => labStore.deleteRange(r.id, props.examen.id)); };
</script>
