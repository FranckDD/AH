<!-- src/views/modules/labstock/LabStockCount.vue -->
<!-- Comptage hebdomadaire. Breakpoints : < md = une carte par produit (360 px), md = cartes
     sur 2 colonnes, lg = tableau. Acces : laborantin, admin. Les produits en conflit gardent
     leur saisie pour recomptage ; les autres sont vides apres l'envoi. -->
<template>
  <div class="space-y-6 w-full">
    <div class="flex flex-col md:flex-row justify-between md:items-center bg-white p-4 md:p-6 rounded-2xl shadow-xs border border-gray-100 gap-4">
      <div>
        <h1 class="text-xl md:text-2xl font-extrabold text-gray-800 tracking-tight">{{ t('labStock.count_title') }}</h1>
        <p class="text-sm text-gray-500">{{ t('labStock.count_subtitle') }}</p>
      </div>
      <p class="text-sm text-gray-500">{{ t('labStock.count_last', { date: lastCountText }) }}</p>
    </div>

    <div v-if="reminderDue" class="bg-amber-50 border-l-4 border-amber-500 p-3 rounded-sm text-sm text-amber-800">
      {{ daysSince == null ? t('labStock.count_reminder_never') : t('labStock.count_reminder', { days: daysSince }) }}
    </div>
    <div v-if="pageError" class="bg-red-50 border-l-4 border-red-500 p-3 rounded-sm text-sm text-red-700">{{ pageError }}</div>
    <div v-if="pageMessage" class="bg-green-50 border-l-4 border-green-500 p-3 rounded-sm text-sm text-green-700">{{ pageMessage }}</div>

    <div v-if="conflicts.length" class="bg-orange-50 border-2 border-orange-300 p-4 rounded-xl text-sm text-orange-900 space-y-2">
      <p class="font-bold">{{ t('labStock.count_conflicts_title') }}</p>
      <ul class="list-disc pl-5 space-y-1">
        <li v-for="c in conflicts" :key="c.product_id">{{ t('labStock.count_conflict_line', { name: c.name, expected: c.expected, actual: c.actual }) }}</li>
      </ul>
    </div>

    <div class="bg-white rounded-2xl shadow-xs border border-gray-100 p-4 flex flex-col sm:flex-row gap-3 sm:items-center sm:justify-between">
      <div class="relative w-full sm:w-72">
        <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
          <MagnifyingGlassIcon class="h-5 w-5 text-gray-400" />
        </div>
        <input v-model="search" type="text" :placeholder="t('common.search_placeholder')"
               class="block w-full pl-10 pr-3 py-2 min-h-[44px] lg:min-h-0 border border-gray-300 rounded-lg bg-gray-50 sm:text-sm" />
      </div>
      <span class="text-sm text-gray-500">{{ t('labStock.count_filled', { n: filledCount, total: products.length }) }}</span>
    </div>

    <div v-if="isLoading" class="p-10 text-center text-gray-500">{{ t('stockOps.loading') }}</div>
    <div v-else-if="filtered.length === 0" class="bg-white rounded-2xl border border-gray-100 p-8 text-center text-gray-500 italic">{{ t('labStock.no_products') }}</div>

    <template v-else>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-3 lg:hidden">
        <article v-for="p in filtered" :key="p.id" class="bg-white rounded-2xl shadow-xs border p-4 space-y-3"
                 :class="isConflict(p.id) ? 'border-orange-300' : invalid(p.id) ? 'border-red-300' : 'border-gray-100'">
          <div class="flex items-start justify-between gap-3">
            <div class="min-w-0">
              <h3 class="font-semibold text-gray-900 break-words">{{ p.name }}</h3>
              <p v-if="p.packaging" class="text-xs text-gray-500">{{ p.packaging }}</p>
            </div>
            <div class="text-right shrink-0">
              <div class="text-xs text-gray-500">{{ t('labStock.last_stock') }}</div>
              <div class="text-2xl font-bold leading-none text-gray-900">{{ num(p.quantity) }}</div>
            </div>
          </div>
          <label class="block text-sm text-gray-700">{{ t('labStock.counted_qty') }}
            <input v-model="entered[p.id]" type="number" inputmode="numeric" pattern="[0-9]*" min="0" step="1"
                   class="mt-1 block w-full px-3 py-2 min-h-[44px] text-lg border rounded-lg"
                   :class="invalid(p.id) ? 'border-red-400' : 'border-gray-300'" />
          </label>
        </article>
      </div>

      <div class="hidden lg:block bg-white rounded-2xl shadow-xs border border-gray-100 overflow-x-auto">
        <table class="min-w-full text-left border-collapse">
          <thead>
            <tr class="bg-gray-50 text-gray-500 text-xs uppercase tracking-wider">
              <th class="px-6 py-3 font-semibold">{{ t('labStock.col_product') }}</th>
              <th class="px-6 py-3 font-semibold">{{ t('labStock.col_packaging') }}</th>
              <th class="px-6 py-3 font-semibold text-right">{{ t('labStock.last_stock') }}</th>
              <th class="px-6 py-3 font-semibold">{{ t('labStock.col_last_count') }}</th>
              <th class="px-6 py-3 font-semibold text-right">{{ t('labStock.counted_qty') }}</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-for="p in filtered" :key="p.id" :class="isConflict(p.id) ? 'bg-orange-50' : ''">
              <td class="px-6 py-3 font-medium text-gray-900">{{ p.name }}</td>
              <td class="px-6 py-3 text-sm text-gray-600">{{ p.packaging || '—' }}</td>
              <td class="px-6 py-3 text-right font-bold text-gray-900">{{ num(p.quantity) }}</td>
              <td class="px-6 py-3 text-sm text-gray-500">{{ formatDate(p.last_counted_at) || t('labStock.never') }}</td>
              <td class="px-6 py-3 text-right">
                <input v-model="entered[p.id]" type="number" inputmode="numeric" min="0" step="1"
                       class="w-28 px-2 py-1 border rounded-sm text-right" :class="invalid(p.id) ? 'border-red-400' : 'border-gray-300'" />
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>

    <div class="sticky bottom-0 z-30 lg:static bg-white border border-gray-200 rounded-2xl shadow-lg lg:shadow-xs p-3 md:p-4 flex flex-col md:flex-row md:items-center md:justify-end gap-2">
      <p v-if="hasInvalid" class="text-xs text-red-600 md:mr-auto">{{ t('labStock.count_err_invalid') }}</p>
      <button type="button" @click="submit" :disabled="busy || !filledCount || hasInvalid"
              class="w-full md:w-auto px-6 py-3 lg:py-2 min-h-[44px] bg-emerald-600 text-white rounded-xl font-semibold hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed">
        {{ busy ? t('labStock.submitting') : t('labStock.submit_count') }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount } from 'vue';
import { useI18n } from 'vue-i18n';
import { MagnifyingGlassIcon } from '@heroicons/vue/24/outline';
import { LabStockGateway, describeLabStockError } from '@/services/LabStockGateway';
import { buildCountPayload, describeConflicts, isValidCount } from '@/utils/labCount';

const { t } = useI18n();
const products = ref([]);
const entered = reactive({});
const status = ref(null);
const conflicts = ref([]);
const search = ref('');
const isLoading = ref(false);
const busy = ref(false);
const pageError = ref('');
const pageMessage = ref('');

const num = (v) => Number(v ?? 0);
const formatDate = (v) => (v ? new Date(v).toLocaleDateString() : '');
const blank = (v) => v === undefined || v === null || String(v).trim() === '';
const invalid = (id) => !blank(entered[id]) && !isValidCount(entered[id]);
const isConflict = (id) => conflicts.value.some((c) => c.product_id === id);

const st = computed(() => status.value?.count_status ?? status.value ?? {});
const reminderDue = computed(() => !!st.value.reminder_due);
const daysSince = computed(() => st.value.days_since ?? null);
const lastCountText = computed(() => formatDate(st.value.last_counted_at) || t('labStock.never'));

const filtered = computed(() => {
  const q = search.value.trim().toLowerCase();
  if (!q) return products.value;
  return products.value.filter((p) => [p.name, p.packaging].some((v) => (v || '').toLowerCase().includes(q)));
});
const filledCount = computed(() => products.value.filter((p) => !blank(entered[p.id])).length);
const hasInvalid = computed(() => products.value.some((p) => invalid(p.id)));

let msgTimer = null;
const flash = (msg) => {
  pageMessage.value = msg;
  clearTimeout(msgTimer);
  msgTimer = setTimeout(() => { pageMessage.value = ''; }, 6000);
};
onBeforeUnmount(() => clearTimeout(msgTimer));

const loadProducts = async () => {
  products.value = await LabStockGateway.listProducts();
};
const loadStatus = async () => {
  try { status.value = await LabStockGateway.countStatus(); } catch (err) { console.error('Statut de comptage indisponible :', err); }
};
const load = async () => {
  isLoading.value = true;
  pageError.value = '';
  try {
    await loadProducts();
  } catch (err) {
    pageError.value = describeLabStockError(err, t('stockOps.error_load'));
    console.error('Chargement des produits du labo echoue :', err);
  } finally {
    isLoading.value = false;
  }
  loadStatus();
};

// Ne garde que la saisie des produits en conflit (a recompter).
const keepOnly = (ids) => {
  for (const k of Object.keys(entered)) if (!ids.has(Number(k))) delete entered[k];
};

const submit = async () => {
  if (busy.value || hasInvalid.value) return;
  const lines = buildCountPayload(products.value, entered);
  if (!lines.length) return;
  busy.value = true;
  pageError.value = '';
  conflicts.value = [];
  try {
    const resp = await LabStockGateway.submitCount(lines);
    conflicts.value = describeConflicts(resp);
    keepOnly(new Set(conflicts.value.map((c) => c.product_id)));
    flash(t('labStock.count_saved', { n: (resp?.applied || []).length }));
  } catch (err) {
    const c = err?.response?.status === 409 ? describeConflicts(err) : [];
    if (c.length) {
      conflicts.value = c;
      keepOnly(new Set(c.map((x) => x.product_id)));
    } else {
      pageError.value = describeLabStockError(err, t('stockOps.error_save'));
    }
    console.error('Envoi du comptage echoue :', err);
  } finally {
    busy.value = false;
  }
  try { await loadProducts(); } catch (err) { console.error('Rechargement des produits echoue :', err); }
  loadStatus();
};

onMounted(load);
</script>
