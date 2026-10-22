<!-- src/views/modules/caisse/StaffDiscountRules.vue -->
<template>
  <div class="grid w-full max-w-5xl gap-6">
    <PageHeader :title="$t('staffDiscount.title')" />

    <!-- Section 1 : regles par categorie -->
    <AppCard :title="$t('staffDiscount.rules_title')" :subtitle="$t('staffDiscount.rules_hint')">
      <div class="grid gap-3">
        <p v-if="rulesLoadError" role="alert" class="rounded-control border p-3 text-base" :class="toneClasses('danger')">
          {{ rulesLoadError }}
        </p>

        <ResponsiveTable :columns="ruleColumns" :rows="ruleRows" row-key="cat" striped>
          <template #cell-category="{ row: { cat } }"><span class="font-medium">{{ $t(`staffDiscount.categories.${cat}`) }}</span></template>
          <template #cell-min="{ row: { cat } }">
            <input v-model.number="rows[cat].min_invoice_amount" type="number" min="0" step="1" inputmode="numeric"
                   :aria-label="$t('staffDiscount.col_min_amount')" :class="[fieldClass, 'text-right lg:w-40']" />
          </template>
          <template #cell-rate="{ row: { cat } }">
            <input v-model.number="rows[cat].rate_percent" type="number" min="1" max="100" step="1" inputmode="numeric"
                   :aria-label="$t('staffDiscount.col_rate')" :class="[fieldClass, 'text-right lg:w-24']" />
          </template>
          <template #cell-active="{ row: { cat } }">
            <label class="inline-flex min-h-11 items-center gap-2 text-base text-ink">
              <input v-model="rows[cat].is_active" type="checkbox" class="h-5 w-5 accent-brand-600" />
              <span>{{ $t('staffDiscountScreens.rule_active_label') }}</span>
            </label>
          </template>
          <template #cell-action="{ row: { cat } }">
            <div class="grid gap-2">
              <AppButton @click="saveRule(cat)" :disabled="rows[cat].saving" :loading="rows[cat].saving">
                {{ rows[cat].saving ? $t('staffDiscount.saving') : $t('staffDiscount.save') }}
              </AppButton>
              <p v-if="rows[cat].message" :role="rows[cat].isError ? 'alert' : 'status'" class="text-base font-medium"
                 :class="rows[cat].isError ? 'text-tone-danger-text' : 'text-tone-success-text'">
                {{ rows[cat].message }}
              </p>
            </div>
          </template>
        </ResponsiveTable>
        <p class="text-base text-ink-muted">{{ $t('staffDiscount.matching_hint') }}</p>
      </div>
    </AppCard>

    <!-- Section 2 : membres du personnel (seul endroit ou le promoteur gere "Personnel") -->
    <AppCard :title="$t('staffDiscount.members_title')">
      <div class="grid gap-4">
        <p v-if="membersError" role="alert" class="rounded-control border p-3 text-base" :class="toneClasses('danger')">
          {{ membersError }}
        </p>

        <FormField id="staff-search" :label="$t('staffDiscountScreens.search_label')" v-slot="{ describedBy }">
          <input id="staff-search" v-model="searchQuery" @input="onSearchInput" type="search" autocomplete="off"
                 :placeholder="$t('staffDiscount.search_placeholder')" :aria-describedby="describedBy" :class="fieldClass" />
        </FormField>

        <ResponsiveTable v-if="searchQuery.trim().length >= 2" :columns="memberColumns" :rows="searchResults" row-key="patient_id"
                         :loading="isSearching" :empty-title="$t('staffDiscount.search_empty')" :empty-message="' '" striped>
          <template #cell-code="{ row: p }"><span class="font-mono">{{ p.code_patient }}</span></template>
          <template #cell-name="{ row: p }">{{ p.first_name }} {{ p.last_name }}</template>
          <template #cell-staff="{ row: p }"><StatusBadge v-if="p.is_staff" tone="success" :label="$t('staffDiscount.col_staff')" /></template>
          <template #actions="{ row: p }">
            <AppButton :variant="p.is_staff ? 'secondary' : 'primary'" @click="toggleStaff(p)" :disabled="togglingId === p.patient_id">
              {{ p.is_staff ? $t('staffDiscount.unmark_staff') : $t('staffDiscount.mark_staff') }}
            </AppButton>
          </template>
        </ResponsiveTable>

        <ResponsiveTable :columns="memberColumns" :rows="members" row-key="patient_id" :empty-title="$t('staffDiscount.members_empty')" :empty-message="' '" striped>
          <template #cell-code="{ row: p }"><span class="font-mono">{{ p.code_patient }}</span></template>
          <template #cell-name="{ row: p }">{{ p.first_name }} {{ p.last_name }}</template>
          <template #cell-staff="{ row: p }"><StatusBadge tone="success" :label="$t('staffDiscount.col_staff')" /></template>
          <template #actions="{ row: p }">
            <AppButton variant="secondary" @click="toggleStaff(p)" :disabled="togglingId === p.patient_id">{{ $t('staffDiscount.unmark_staff') }}</AppButton>
          </template>
        </ResponsiveTable>
      </div>
    </AppCard>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { StaffDiscountGateway } from '@/services/StaffDiscountGateway';
import { CATEGORIES } from '@/utils/staffDiscount';
import { AppButton, AppCard, PageHeader, FormField, StatusBadge, ResponsiveTable } from '@/components/ui';
import { toneClasses } from '@/design/tones';

const { t } = useI18n();

// Colonnes des tableaux (cartes empilees sous lg) et style commun des champs.
const ruleColumns = computed(() => [
  { key: 'category', label: t('staffDiscount.col_category') },
  { key: 'min', label: t('staffDiscount.col_min_amount') },
  { key: 'rate', label: t('staffDiscount.col_rate') },
  { key: 'active', label: t('staffDiscount.col_active') },
  { key: 'action', label: t('staffDiscount.col_action') },
]);
const ruleRows = CATEGORIES.map((cat) => ({ cat }));
const memberColumns = computed(() => [
  { key: 'code', label: t('staffDiscount.col_code') },
  { key: 'name', label: t('staffDiscount.col_name') },
  { key: 'staff', label: t('staffDiscount.col_staff') },
]);
const fieldClass = 'block w-full min-h-11 lg:min-h-10 rounded-control border border-tone-neutral-border bg-white px-3 text-base text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600';

// Message d'erreur visible, jamais avale : detail serveur (422 texte ou
// liste Pydantic), 403 explicite, sinon message generique.
const describeError = (err, fallbackKey) => {
  const status = err?.response?.status;
  const detail = err?.response?.data?.detail;
  if (status === 403) return t('staffDiscount.error_forbidden');
  if (typeof detail === 'string' && detail) return detail;
  if (Array.isArray(detail) && detail.length) return detail.map((d) => d.msg || String(d)).join(' ; ');
  return t(fallbackKey);
};

// --- Regles ---
const rows = reactive(Object.fromEntries(CATEGORIES.map((c) => [c, {
  min_invoice_amount: 0, rate_percent: null, is_active: false, saving: false, message: '', isError: false,
}])));
const rulesLoadError = ref('');

const loadRules = async () => {
  rulesLoadError.value = '';
  try {
    const list = await StaffDiscountGateway.list();
    for (const r of list || []) {
      if (!rows[r.category]) continue;
      rows[r.category].min_invoice_amount = Number(r.min_invoice_amount) || 0;
      rows[r.category].rate_percent = Number(r.rate_percent) || null;
      rows[r.category].is_active = Boolean(r.is_active);
    }
  } catch (err) {
    rulesLoadError.value = describeError(err, 'staffDiscount.error_load');
    console.error('Chargement des regles de reduction personnel echoue :', err);
  }
};

const saveRule = async (cat) => {
  const row = rows[cat];
  row.message = '';
  row.isError = false;
  const rate = Number(row.rate_percent);
  const min = Number(row.min_invoice_amount);
  if (!Number.isInteger(rate) || rate < 1 || rate > 100) {
    row.message = t('staffDiscount.invalid_rate');
    row.isError = true;
    return;
  }
  if (!Number.isFinite(min) || min < 0) {
    row.message = t('staffDiscount.invalid_min');
    row.isError = true;
    return;
  }
  row.saving = true;
  try {
    await StaffDiscountGateway.save(cat, { min_invoice_amount: min, rate_percent: rate, is_active: Boolean(row.is_active) });
    row.message = t('staffDiscount.saved');
  } catch (err) {
    row.message = describeError(err, 'staffDiscount.error_save');
    row.isError = true;
    console.error('Enregistrement de la regle echoue :', err);
  } finally {
    row.saving = false;
  }
};

// --- Membres du personnel ---
const members = ref([]);
const membersError = ref('');
const searchQuery = ref('');
const searchResults = ref([]);
const isSearching = ref(false);
const togglingId = ref(null);

const loadMembers = async () => {
  try {
    members.value = (await StaffDiscountGateway.lookupStaff({ onlyStaff: true })) || [];
  } catch (err) {
    membersError.value = describeError(err, 'staffDiscount.error_load');
    console.error('Chargement des membres du personnel echoue :', err);
  }
};

const runSearch = async () => {
  const q = searchQuery.value.trim();
  if (q.length < 2) {
    searchResults.value = [];
    return;
  }
  isSearching.value = true;
  try {
    searchResults.value = (await StaffDiscountGateway.lookupStaff({ q })) || [];
  } catch (err) {
    membersError.value = describeError(err, 'staffDiscount.error_load');
    console.error('Recherche de patients echouee :', err);
  } finally {
    isSearching.value = false;
  }
};

let searchTimeout = null;
const onSearchInput = () => {
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(runSearch, 300);
};

const toggleStaff = async (p) => {
  membersError.value = '';
  togglingId.value = p.patient_id;
  try {
    await StaffDiscountGateway.setStaff(p.patient_id, !p.is_staff);
    await Promise.all([loadMembers(), runSearch()]);
  } catch (err) {
    membersError.value = describeError(err, 'staffDiscount.error_toggle');
    console.error('Bascule Personnel echouee :', err);
  } finally {
    togglingId.value = null;
  }
};

onMounted(() => {
  loadRules();
  loadMembers();
});
</script>
