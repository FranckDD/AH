<!-- src/views/modules/caisse/StaffDiscountRules.vue -->
<template>
  <div class="max-w-4xl mx-auto p-6 space-y-8">
    <h2 class="text-xl font-bold text-gray-800">{{ $t('staffDiscount.title') }}</h2>

    <!-- Section 1 : regles par categorie -->
    <section class="bg-white rounded-xl shadow-xs border border-gray-200 p-5">
      <h3 class="text-lg font-semibold text-gray-800 mb-1">{{ $t('staffDiscount.rules_title') }}</h3>
      <p class="text-xs text-gray-500 mb-4">{{ $t('staffDiscount.rules_hint') }}</p>

      <div v-if="rulesLoadError" class="bg-red-50 border-l-4 border-red-500 p-3 rounded-sm text-sm text-red-700 mb-3">
        {{ rulesLoadError }}
      </div>

      <table class="w-full text-sm">
        <thead>
          <tr class="text-left text-xs text-gray-500 uppercase border-b">
            <th class="py-2">{{ $t('staffDiscount.col_category') }}</th>
            <th class="py-2">{{ $t('staffDiscount.col_min_amount') }}</th>
            <th class="py-2">{{ $t('staffDiscount.col_rate') }}</th>
            <th class="py-2">{{ $t('staffDiscount.col_active') }}</th>
            <th class="py-2">{{ $t('staffDiscount.col_action') }}</th>
          </tr>
        </thead>
        <tbody>
          <template v-for="cat in CATEGORIES" :key="cat">
            <tr class="border-b last:border-0">
              <td class="py-2 font-medium text-gray-800">{{ $t(`staffDiscount.categories.${cat}`) }}</td>
              <td class="py-2 pr-2">
                <input v-model.number="rows[cat].min_invoice_amount" type="number" min="0" step="1"
                       class="w-36 px-2 py-1 border border-gray-300 rounded-sm" />
              </td>
              <td class="py-2 pr-2">
                <input v-model.number="rows[cat].rate_percent" type="number" min="1" max="100" step="1"
                       class="w-20 px-2 py-1 border border-gray-300 rounded-sm" />
              </td>
              <td class="py-2">
                <input v-model="rows[cat].is_active" type="checkbox" class="h-4 w-4" />
              </td>
              <td class="py-2">
                <button type="button" @click="saveRule(cat)" :disabled="rows[cat].saving"
                        class="px-3 py-1 bg-green-600 text-white rounded-lg text-xs font-medium hover:bg-green-700 disabled:opacity-50">
                  {{ rows[cat].saving ? $t('staffDiscount.saving') : $t('staffDiscount.save') }}
                </button>
              </td>
            </tr>
            <tr v-if="rows[cat].message">
              <td colspan="5" class="pb-2 text-xs" :class="rows[cat].isError ? 'text-red-700' : 'text-green-700'">
                {{ rows[cat].message }}
              </td>
            </tr>
          </template>
        </tbody>
      </table>
      <p class="text-xs text-gray-500 mt-3">{{ $t('staffDiscount.matching_hint') }}</p>
    </section>

    <!-- Section 2 : membres du personnel (seul endroit ou le promoteur gere "Personnel") -->
    <section class="bg-white rounded-xl shadow-xs border border-gray-200 p-5">
      <h3 class="text-lg font-semibold text-gray-800 mb-4">{{ $t('staffDiscount.members_title') }}</h3>

      <div v-if="membersError" class="bg-red-50 border-l-4 border-red-500 p-3 rounded-sm text-sm text-red-700 mb-3">
        {{ membersError }}
      </div>

      <input v-model="searchQuery" @input="onSearchInput" type="text"
             :placeholder="$t('staffDiscount.search_placeholder')"
             class="block w-full px-3 py-2 border border-gray-300 rounded-lg text-sm mb-3" />

      <div v-if="searchQuery.trim().length >= 2" class="mb-6">
        <div v-if="searchResults.length === 0 && !isSearching" class="text-sm text-gray-400">{{ $t('staffDiscount.search_empty') }}</div>
        <table v-else class="w-full text-sm">
          <tbody>
            <tr v-for="p in searchResults" :key="p.patient_id" class="border-b last:border-0">
              <td class="py-2 font-mono text-gray-600">{{ p.code_patient }}</td>
              <td class="py-2">{{ p.first_name }} {{ p.last_name }}</td>
              <td class="py-2 text-right">
                <button type="button" @click="toggleStaff(p)" :disabled="togglingId === p.patient_id"
                        :class="p.is_staff ? 'bg-gray-200 text-gray-700' : 'bg-emerald-600 text-white'"
                        class="px-3 py-1 rounded-lg text-xs font-medium disabled:opacity-50">
                  {{ p.is_staff ? $t('staffDiscount.unmark_staff') : $t('staffDiscount.mark_staff') }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="members.length === 0" class="text-sm text-gray-400">{{ $t('staffDiscount.members_empty') }}</div>
      <table v-else class="w-full text-sm">
        <thead>
          <tr class="text-left text-xs text-gray-500 uppercase border-b">
            <th class="py-2">{{ $t('staffDiscount.col_code') }}</th>
            <th class="py-2">{{ $t('staffDiscount.col_name') }}</th>
            <th class="py-2 text-right">{{ $t('staffDiscount.col_staff') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="p in members" :key="p.patient_id" class="border-b last:border-0">
            <td class="py-2 font-mono text-gray-600">{{ p.code_patient }}</td>
            <td class="py-2">{{ p.first_name }} {{ p.last_name }}</td>
            <td class="py-2 text-right">
              <button type="button" @click="toggleStaff(p)" :disabled="togglingId === p.patient_id"
                      class="px-3 py-1 bg-gray-200 text-gray-700 rounded-lg text-xs font-medium disabled:opacity-50">
                {{ $t('staffDiscount.unmark_staff') }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </section>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { StaffDiscountGateway } from '@/services/StaffDiscountGateway';
import { CATEGORIES } from '@/utils/staffDiscount';

const { t } = useI18n();

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
