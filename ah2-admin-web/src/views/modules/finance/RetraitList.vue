<template>
  <div class="space-y-6 w-full">
    <div class="flex flex-col md:flex-row justify-between items-center bg-white p-6 rounded-2xl shadow-sm border border-gray-100 gap-4">
      <div>
        <h1 class="text-2xl font-extrabold text-gray-800 tracking-tight">{{ t('retrait.title') }}</h1>
        <p class="text-sm text-gray-500">{{ retraitStore.pagination.total }} retraits</p>
      </div>
      <button @click="showCreateModal = true"
              class="flex items-center px-6 py-2.5 bg-red-600 text-white rounded-xl hover:bg-red-700 shadow-md shadow-red-200 transition font-semibold">
        <PlusCircleIcon class="h-5 w-5 mr-2" />
        {{ t('retrait.new_retrait') }}
      </button>
    </div>

    <div class="bg-white p-4 rounded-2xl shadow-sm border border-gray-100 flex flex-wrap gap-4 items-end">
      <div class="flex-1 min-w-[200px]">
        <label class="text-xs font-bold text-gray-500 uppercase mb-1 block">Recherche</label>
        <input v-model="searchQuery" type="text" :placeholder="t('retrait.search_placeholder')"
               class="block w-full px-3 py-2 border border-gray-300 rounded-lg bg-gray-50 focus:ring-red-500 focus:border-red-500 sm:text-sm" />
      </div>
      <div class="w-full md:w-40">
        <label class="text-xs font-bold text-gray-500 uppercase mb-1 block">Du</label>
        <input v-model="startDate" type="date" class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-red-500 focus:border-red-500 sm:text-sm" />
      </div>
      <div class="w-full md:w-40">
        <label class="text-xs font-bold text-gray-500 uppercase mb-1 block">Au</label>
        <input v-model="endDate" type="date" class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-red-500 focus:border-red-500 sm:text-sm" />
      </div>
      <div class="w-full md:w-40">
        <label class="text-xs font-bold text-gray-500 uppercase mb-1 block">{{ t('retrait.table.status') }}</label>
        <select v-model="statusFilter" class="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-red-500 focus:border-red-500 sm:text-sm">
          <option value="">{{ t('caisse.status.all') }}</option>
          <option value="active">{{ t('caisse.status.active') }}</option>
          <option value="cancelled">{{ t('caisse.status.cancelled') }}</option>
        </select>
      </div>
    </div>

    <div class="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
      <div v-if="retraitStore.isLoading" class="p-10 text-center">
        <span class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-red-600"></span>
      </div>
      <div v-else-if="retraitStore.loadError" class="p-10 text-center text-red-500">Erreur de chargement</div>
      <div v-else class="overflow-x-auto">
        <table class="min-w-full text-left border-collapse">
          <thead>
            <tr class="bg-gray-50 text-gray-500 text-xs uppercase tracking-wider">
              <th class="px-6 py-4 font-semibold">{{ t('retrait.table.date') }}</th>
              <th class="px-6 py-4 font-semibold">{{ t('retrait.table.justification') }}</th>
              <th class="px-6 py-4 font-semibold">{{ t('retrait.table.category') }}</th>
              <th class="px-6 py-4 font-semibold">{{ t('retrait.table.method') }}</th>
              <th class="px-6 py-4 font-semibold text-right">{{ t('retrait.table.amount') }}</th>
              <th class="px-6 py-4 font-semibold">{{ t('retrait.table.status') }}</th>
              <th class="px-6 py-4 font-semibold text-right">{{ t('retrait.table.actions') }}</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-for="r in retraitStore.retraits" :key="r.retrait_id || r.id" class="hover:bg-gray-50 transition">
              <td class="px-6 py-4 text-sm text-gray-600 font-mono">{{ formatDate(r.retrait_at) }}</td>
              <td class="px-6 py-4 text-sm text-gray-900">{{ r.justification }}</td>
              <td class="px-6 py-4">
                <span class="inline-flex items-center px-2.5 py-0.5 rounded-lg text-xs font-medium bg-gray-100 text-gray-800 border border-gray-200">
                  {{ r.category }}
                </span>
              </td>
              <td class="px-6 py-4 text-sm text-gray-600">{{ r.payment_method }}</td>
              <td class="px-6 py-4 text-right font-bold text-sm text-red-600">- {{ formatCurrency(r.amount) }}</td>
              <td class="px-6 py-4">
                <span v-if="r.status === 'active'" class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">
                  {{ t('caisse.status.active') }}
                </span>
                <span v-else class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-200 text-gray-600">
                  {{ t('caisse.status.cancelled') }}
                </span>
              </td>
              <td class="px-6 py-4 text-right">
                <button v-if="r.status === 'active'" @click="openCancelModal(r)"
                        :disabled="!r.retrait_id"
                        class="p-2 bg-white border border-gray-200 rounded-lg text-red-500 hover:bg-red-50 hover:border-red-200 transition shadow-sm disabled:opacity-40 disabled:cursor-not-allowed"
                        :title="r.retrait_id ? t('caisse.actions.cancel') : 'En attente de synchronisation'">
                  <XCircleIcon class="h-4 w-4" />
                </button>
              </td>
            </tr>
            <tr v-if="retraitStore.retraits.length === 0">
              <td colspan="7" class="px-6 py-8 text-center text-gray-500 italic">Aucun retrait trouvé.</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="retraitStore.pagination.total_pages > 1" class="p-4 flex justify-between items-center border-t border-gray-100 bg-gray-50">
        <p class="text-sm text-gray-700">Page {{ retraitStore.pagination.page }} sur {{ retraitStore.pagination.total_pages }}</p>
        <div class="flex space-x-2">
          <button @click="goToPage(retraitStore.pagination.page - 1)" :disabled="retraitStore.pagination.page === 1" class="px-3 py-1 border rounded bg-white disabled:opacity-50">
            <ChevronLeftIcon class="h-5 w-5" />
          </button>
          <button @click="goToPage(retraitStore.pagination.page + 1)" :disabled="retraitStore.pagination.page === retraitStore.pagination.total_pages" class="px-3 py-1 border rounded bg-white disabled:opacity-50">
            <ChevronRightIcon class="h-5 w-5" />
          </button>
        </div>
      </div>
    </div>

    <RetraitModal v-if="showCreateModal" :isSaving="isSavingCreate" :errorMessage="createError"
                  @close="showCreateModal = false" @save="handleCreate" />

    <CaisseCancelModal v-if="cancellingRetrait" :isSaving="isCancelling" :errorMessage="cancelError"
                        :label="`Retrait de ${formatCurrency(cancellingRetrait.amount)} du ${formatDate(cancellingRetrait.retrait_at)}`"
                        @close="cancellingRetrait = null" @confirm="handleCancel" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRetraitStore } from '@/stores/retraitStore';
import RetraitModal from '@/components/caisse/RetraitModal.vue';
import CaisseCancelModal from '@/components/caisse/CaisseCancelModal.vue';
import {
  PlusCircleIcon, ChevronLeftIcon, ChevronRightIcon, XCircleIcon,
} from '@heroicons/vue/24/outline';

const { t } = useI18n();
const retraitStore = useRetraitStore();

onMounted(() => {
  retraitStore.fetchRetraits();
});

const searchQuery = computed({
  get: () => retraitStore.filters.searchQuery,
  set: (val) => retraitStore.setFilters({ searchQuery: val }),
});
const startDate = computed({
  get: () => retraitStore.filters.startDate,
  set: (val) => retraitStore.setFilters({ startDate: val }),
});
const endDate = computed({
  get: () => retraitStore.filters.endDate,
  set: (val) => retraitStore.setFilters({ endDate: val }),
});
const statusFilter = computed({
  get: () => retraitStore.filters.status,
  set: (val) => retraitStore.setFilters({ status: val }),
});

const goToPage = (page) => retraitStore.setPage(page);

const formatCurrency = (value) => new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'XAF' }).format(value).replace('XOF', 'FCFA');
const formatDate = (iso) => (iso ? String(iso).split('T')[0] : '');

const showCreateModal = ref(false);
const isSavingCreate = ref(false);
const createError = ref('');

const mapErrorToMessage = (err) => {
  if (err.response) {
    const status = err.response.status;
    const detail = err.response.data?.detail;
    if (status === 422) return "Données invalides.";
    if (status === 400) return detail || "Requête invalide.";
    return `Erreur serveur (${status}) : ${detail || 'veuillez réessayer'}`;
  }
  if (err.request) return "Erreur réseau. Veuillez vérifier votre connexion.";
  return err.message || "Une erreur inattendue est survenue.";
};

const handleCreate = async (payload) => {
  isSavingCreate.value = true;
  createError.value = '';
  try {
    await retraitStore.createRetrait(payload);
    showCreateModal.value = false;
  } catch (err) {
    createError.value = mapErrorToMessage(err);
  } finally {
    isSavingCreate.value = false;
  }
};

const cancellingRetrait = ref(null);
const isCancelling = ref(false);
const cancelError = ref('');

const openCancelModal = (r) => {
  cancellingRetrait.value = r;
  cancelError.value = '';
};

const handleCancel = async (justification) => {
  isCancelling.value = true;
  cancelError.value = '';
  try {
    await retraitStore.cancelRetrait(cancellingRetrait.value.retrait_id, justification);
    cancellingRetrait.value = null;
  } catch (err) {
    cancelError.value = mapErrorToMessage(err);
  } finally {
    isCancelling.value = false;
  }
};
</script>
