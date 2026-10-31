<template>
  <div class="h-full overflow-y-auto p-4 text-sm md:p-6">
    <div class="mx-auto grid max-w-5xl gap-4">

      <PageHeader :title="t('lab.config.title')" :subtitle="t('lab.config.subtitle')">
        <template #actions>
          <AppButton v-if="canEdit" variant="lab" :icon="PlusIcon" :disabled="!online" @click="openNew">{{ t('lab.config.new_exam') }}</AppButton>
        </template>
      </PageHeader>

      <p role="note" class="flex items-start gap-2 rounded-card border p-3 text-sm" :class="toneClasses('info')" data-testid="snapshot-banner">
        <InformationCircleIcon class="mt-0.5 h-5 w-5 shrink-0" aria-hidden="true" />
        <span>{{ t('labCatalogue.snapshot_banner') }}</span>
      </p>
      <p v-if="!canEdit" role="status" class="rounded-card border p-3 text-sm" :class="toneClasses('neutral')" data-testid="readonly-banner">{{ t('labCatalogue.readonly_banner') }}</p>
      <p v-else-if="!online" role="alert" class="rounded-card border p-3 text-sm" :class="toneClasses('warning')" data-testid="offline-banner">{{ t('labCatalogue.offline_banner') }}</p>

      <div class="flex flex-wrap items-end gap-3">
        <div class="min-w-0 flex-1">
          <FormField id="cat-search" :label="t('labCatalogue.search')" v-slot="{ describedBy }">
            <input id="cat-search" v-model="query" type="search" autocomplete="off" :aria-describedby="describedBy" :class="fieldClass" />
          </FormField>
        </div>
        <label class="flex min-h-11 items-center gap-2 text-sm text-ink">
          <input id="cat-show-inactive" v-model="showInactive" type="checkbox" class="h-5 w-5 accent-brand-600" />
          {{ t('labCatalogue.show_inactive') }}
        </label>
      </div>

      <LoadErrorState v-if="loadFailed" :message="loadMessage" @retry="reload" />
      <p v-else-if="loading && !exams.length" class="text-ink-muted" role="status">{{ t('labCatalogue.loading') }}</p>
      <EmptyState v-else-if="!groups.length" :title="t('labCatalogue.empty')" />

      <section v-for="g in groups" :key="g.section || '_none'" class="rounded-card border border-tone-neutral-border bg-white shadow-card" :data-testid="`section-${g.section || 'none'}`">
        <h2 class="border-b border-tone-neutral-border px-4 py-3 text-lg font-semibold text-ink">{{ g.section || t('labCatalogue.no_section') }}</h2>
        <ul>
          <li v-for="(ex, i) in g.items" :key="ex.id" class="flex flex-wrap items-center justify-between gap-2 border-b border-tone-neutral-border px-4 py-2 last:border-b-0">
            <button type="button" class="min-h-11 min-w-0 flex-1 rounded-control text-left focus-visible:outline-2 focus-visible:outline-brand-600" :data-testid="`exam-${ex.code}`" @click="openExam(ex)">
              <span class="block font-medium text-ink">{{ ex.print_title || ex.nom }}</span>
              <span class="block text-sm text-ink-muted">
                <span class="font-mono">{{ ex.code }}</span> | {{ t('labCatalogue.exam.params_count', { n: (ex.parameters || []).length }) }}
                <StatusBadge v-if="ex.is_active === false" tone="neutral" :label="t('labCatalogue.inactive')" />
              </span>
            </button>
            <span v-if="canEdit && !query" class="flex gap-1">
              <AppButton size="sm" variant="ghost" :icon="ArrowUpIcon" :disabled="!online || busy || i === 0" :aria-label="t('labCatalogue.move_up')" @click="moveExam(ex, g, i, -1)" />
              <AppButton size="sm" variant="ghost" :icon="ArrowDownIcon" :disabled="!online || busy || i === g.items.length - 1" :aria-label="t('labCatalogue.move_down')" @click="moveExam(ex, g, i, 1)" />
            </span>
          </li>
        </ul>
      </section>
      <p v-if="listError" role="alert" class="rounded-control border p-3 text-sm" :class="toneClasses('danger')">{{ listError }}</p>
    </div>

    <FullScreenPanel v-if="panelOpen" wide maximizable :title="panelTitle" :subtitle="selected ? selected.code : ''" @close="closePanel">
      <div class="grid gap-4">
        <p v-if="!canEdit" role="status" class="rounded-control border p-3 text-sm" :class="toneClasses('neutral')">{{ t('labCatalogue.readonly_banner') }}</p>
        <p v-else-if="!online" role="alert" class="rounded-control border p-3 text-sm" :class="toneClasses('warning')">{{ t('labCatalogue.offline_draft') }}</p>

        <section class="rounded-card border border-tone-neutral-border bg-white p-4 shadow-card">
          <h3 class="mb-3 text-lg font-semibold text-ink">{{ t('labCatalogue.exam.section_title') }}</h3>
          <p v-if="inUse && inUse.kind === 'exam'" role="alert" class="mb-3 flex flex-wrap items-center gap-3 rounded-control border p-3 text-sm" :class="toneClasses('warning')">
            <span>{{ inUse.message }}</span>
            <AppButton size="sm" variant="secondary" :disabled="busy" @click="deactivateInstead('exam', selected)">{{ t('labCatalogue.deactivate_instead') }}</AppButton>
          </p>
          <CatalogueExamForm :exam="selected" :editable="editable" :saving="busy" :error="errors.exam" :sections="sections"
                             :can-see-price-link="isAdmin" @save="saveExam" @delete="deleteExam" />
        </section>

        <section v-if="selected" class="rounded-card border border-tone-neutral-border bg-white p-4 shadow-card">
          <h3 class="mb-3 text-lg font-semibold text-ink">{{ t('labCatalogue.param.section_title') }}</h3>
          <CatalogueParamTable :exam="selected" :editable="editable" :busy="busy" :error="errors.param" :range-error="errors.range"
                               :in-use="inUse && inUse.kind === 'param' ? inUse : null"
                               @save-param="saveParam" @move="moveParam" @toggle-active="toggleParam" @delete="deleteParam"
                               @deactivate-instead="(p) => deactivateInstead('param', p)" @save-range="saveRange" @delete-range="deleteRange" />
        </section>
      </div>
    </FullScreenPanel>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { ArrowDownIcon, ArrowUpIcon, InformationCircleIcon, PlusIcon } from '@heroicons/vue/24/outline';
import { AppButton, EmptyState, FormField, FullScreenPanel, LoadErrorState, PageHeader, StatusBadge } from '@/components/ui';
import { toneClasses } from '@/design/tones';
import { useAuthStore } from '@/stores/auth';
import { LabCatalogueGateway } from '@/services/LabCatalogueGateway';
import { catalogueErrorMessage, groupExams, isNetworkFailure, moveInList, serverCode } from '@/utils/labCatalogue';
import CatalogueExamForm from '@/components/labo/CatalogueExamForm.vue';
import CatalogueParamTable from '@/components/labo/CatalogueParamTable.vue';

const { t } = useI18n();
const authStore = useAuthStore();

const fieldClass = 'block w-full min-h-11 lg:min-h-10 rounded-control border border-tone-neutral-border bg-white px-3 text-sm text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600';

// Modifier le catalogue : admin, ou laborantin avec le drapeau cheffe du laboratoire. Les autres laborantins
// voient la meme liste en lecture seule. Le serveur reste juge (403 sur toute ecriture non autorisee).
const canEdit = computed(() => authStore.canEditLabCatalogue);
const isAdmin = computed(() => authStore.hasRole(['admin']));

// En ligne seulement : hors ligne, les commandes de modification sont desactivees et le brouillon reste dans les formulaires.
const online = ref(typeof navigator === 'undefined' ? true : navigator.onLine !== false);
const syncOnline = () => { online.value = typeof navigator === 'undefined' ? true : navigator.onLine !== false; };
const editable = computed(() => canEdit.value && online.value);

const exams = ref([]);
const loading = ref(false);
const loadFailed = ref(false);
const loadMessage = ref('');
const query = ref('');
const showInactive = ref(true);
const busy = ref(false);
const listError = ref('');
const errors = reactive({ exam: '', param: '', range: '' });
const inUse = ref(null);

const panelOpen = ref(false);
const selectedId = ref(null);
const selected = computed(() => exams.value.find((e) => e.id === selectedId.value) || null);
const panelTitle = computed(() => (selected.value ? (selected.value.print_title || selected.value.nom) : t('labCatalogue.exam.new_title')));

const groups = computed(() => groupExams(exams.value, query.value, showInactive.value));
const sections = computed(() => [...new Set(exams.value.map((e) => (e.section || '').trim()).filter(Boolean))]);

async function reload() {
  loading.value = true;
  loadFailed.value = false;
  try {
    exams.value = await LabCatalogueGateway.listExams(true);
  } catch (err) {
    loadFailed.value = true;
    loadMessage.value = isNetworkFailure(err) ? '' : catalogueErrorMessage(err, '');
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  window.addEventListener('online', syncOnline);
  window.addEventListener('offline', syncOnline);
  reload();
});
onBeforeUnmount(() => {
  window.removeEventListener('online', syncOnline);
  window.removeEventListener('offline', syncOnline);
});

function clearErrors() {
  errors.exam = ''; errors.param = ''; errors.range = ''; listError.value = ''; inUse.value = null;
}
function openNew() { clearErrors(); selectedId.value = null; panelOpen.value = true; }
function openExam(ex) { clearErrors(); selectedId.value = ex.id; panelOpen.value = true; }
function closePanel() { panelOpen.value = false; selectedId.value = null; clearErrors(); }

// Execute une ecriture puis recharge. scope = zone d'erreur ; kind/target servent au message "deja utilise" (409 in_use).
async function run(scope, fn, { kind = null, target = null } = {}) {
  if (!online.value) { errors[scope === 'list' ? 'exam' : scope] = t('labCatalogue.offline_save'); return false; }
  busy.value = true;
  if (scope === 'list') listError.value = ''; else errors[scope] = '';
  inUse.value = null;
  try {
    const res = await fn();
    await reload();
    return res ?? true;
  } catch (err) {
    let msg;
    if (isNetworkFailure(err)) msg = t('labCatalogue.offline_save');
    else msg = catalogueErrorMessage(err, t('labCatalogue.error_generic'));
    if (kind && err?.response?.status === 409 && serverCode(err) === 'in_use') {
      inUse.value = { kind, id: target?.id, message: msg };
    } else if (scope === 'list') listError.value = msg;
    else errors[scope] = msg;
    return false;
  } finally {
    busy.value = false;
  }
}

async function saveExam(payload) {
  if (selected.value) {
    await run('exam', () => LabCatalogueGateway.updateExam(selected.value.id, payload));
  } else {
    const res = await run('exam', () => LabCatalogueGateway.createExam(payload));
    if (res && res !== true) selectedId.value = res.data?.id ?? null;
  }
}

async function deleteExam() {
  const ex = selected.value;
  if (!ex || !window.confirm(t('labCatalogue.exam.delete_confirm', { name: ex.print_title || ex.nom }))) return;
  const ok = await run('exam', () => LabCatalogueGateway.deleteExam(ex.id), { kind: 'exam', target: ex });
  if (ok) closePanel();
}

async function moveExam(ex, group, indexInGroup, delta) {
  const neighbour = group.items[indexInGroup + delta];
  if (!neighbour) return;
  const ids = exams.value.map((e) => e.id);
  const position = ids.indexOf(neighbour.id) + 1;
  await run('list', () => LabCatalogueGateway.moveExam(ex.id, position));
}

async function saveParam({ id, payload, done }) {
  const ok = id
    ? await run('param', () => LabCatalogueGateway.updateParam(id, payload))
    : await run('param', () => LabCatalogueGateway.createParam({ ...payload, examen_id: selected.value.id }));
  if (ok && done) done();
}

async function moveParam(p, delta) {
  const ids = (selected.value?.parameters || []).map((x) => x.id);
  const next = moveInList(ids, ids.indexOf(p.id), delta);
  if (!next) return;
  await run('param', () => LabCatalogueGateway.orderParams(selected.value.id, next));
}

async function toggleParam(p) {
  await run('param', () => LabCatalogueGateway.updateParam(p.id, { is_active: p.is_active === false }));
}

async function deleteParam(p) {
  if (!window.confirm(t('labCatalogue.param.delete_confirm', { name: p.print_label || p.nom_parametre }))) return;
  await run('param', () => LabCatalogueGateway.deleteParam(p.id), { kind: 'param', target: p });
}

async function deactivateInstead(kind, target) {
  if (!target) return;
  if (kind === 'exam') await run('exam', () => LabCatalogueGateway.updateExam(target.id, { is_active: false }));
  else await run('param', () => LabCatalogueGateway.updateParam(target.id, { is_active: false }));
}

async function saveRange(p, { id, payload, done }) {
  const ok = id
    ? await run('range', () => LabCatalogueGateway.updateRange(id, payload))
    : await run('range', () => LabCatalogueGateway.createRange({ ...payload, parametre_id: p.id }));
  if (ok && done) done();
}

async function deleteRange(p, r) {
  if (!window.confirm(t('labCatalogue.range.delete_confirm'))) return;
  await run('range', () => LabCatalogueGateway.deleteRange(r.id));
}
</script>
