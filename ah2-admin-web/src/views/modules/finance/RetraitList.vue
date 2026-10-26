<template>
  <div class="grid w-full gap-6">
    <PageHeader :title="t('retrait.title')" :subtitle="t('retraitScreens.count', { n: retraitStore.pagination.total })">
      <template #actions>
        <AppButton variant="danger" :icon="PlusCircleIcon" @click="showCreateModal = true">{{ t('retrait.new_retrait') }}</AppButton>
      </template>
    </PageHeader>

    <section :aria-label="t('retrait.table.status')" class="grid gap-4 rounded-card border border-tone-neutral-border bg-white p-4 shadow-card md:grid-cols-2 lg:flex lg:flex-wrap lg:items-end">
      <div class="md:col-span-2 lg:min-w-64 lg:flex-1">
        <FormField id="retrait-search" :label="t('caisseScreens.search_label')" v-slot="{ describedBy }">
          <input id="retrait-search" v-model="searchQuery" type="search" :placeholder="t('retrait.search_placeholder')" :aria-describedby="describedBy" :class="fieldClass" />
        </FormField>
      </div>
      <div class="lg:w-44">
        <FormField id="retrait-from" :label="t('caisseScreens.from')" v-slot="{ describedBy }">
          <input id="retrait-from" v-model="startDate" type="date" :aria-describedby="describedBy" :class="fieldClass" />
        </FormField>
      </div>
      <div class="lg:w-44">
        <FormField id="retrait-to" :label="t('caisseScreens.to')" v-slot="{ describedBy }">
          <input id="retrait-to" v-model="endDate" type="date" :aria-describedby="describedBy" :class="fieldClass" />
        </FormField>
      </div>
      <div class="md:col-span-2 lg:w-52">
        <FormField id="retrait-status" :label="t('retrait.table.status')" v-slot="{ describedBy }">
          <select id="retrait-status" v-model="statusFilter" :aria-describedby="describedBy" :class="fieldClass">
            <option value="">{{ t('caisse.status.all') }}</option>
            <option value="active">{{ t('caisse.status.active') }}</option>
            <option value="cancelled">{{ t('caisse.status.cancelled') }}</option>
          </select>
        </FormField>
      </div>
    </section>

    <section class="grid gap-3">
      <p v-if="retraitStore.loadError" role="alert" class="rounded-card border p-4 text-center text-base font-medium" :class="toneClasses('danger')">
        {{ t('caisseScreens.load_error') }}
      </p>
      <ResponsiveTable
        v-else
        :columns="columns"
        :rows="retraitStore.retraits"
        row-key="retrait_id"
        :loading="retraitStore.isLoading"
        :empty-title="t('retraitScreens.empty')"
        :empty-message="' '"
        striped
      >
        <template #cell-date="{ row: r }"><span class="font-mono">{{ formatDate(r.retrait_at) }}</span></template>
        <template #cell-justification="{ row: r }">{{ r.justification }}</template>
        <template #cell-category="{ row: r }">{{ categoryLabel(r.category) }}</template>
        <template #cell-method="{ row: r }">{{ modeLabel(r.payment_method) }}</template>
        <template #cell-amount="{ row: r }">
          <span class="font-bold" :class="r.status === 'active' ? 'text-tone-danger-text' : 'text-ink-muted line-through'">- {{ formatCurrency(r.amount) }}</span>
        </template>
        <template #cell-status="{ row: r }">
          <StatusBadge v-if="r.status === 'active'" tone="success" :label="t('caisse.status.active')" />
          <StatusBadge v-else tone="neutral" :label="t('caisse.status.cancelled')" />
        </template>
        <template #actions="{ row: r }">
          <AppButton v-if="r.status === 'active'" variant="danger" :icon="XCircleIcon" @click="openCancelModal(r)" :disabled="!r.retrait_id"
                     :title="r.retrait_id ? t('caisse.actions.cancel') : t('caisseScreens.pending_sync')">
            <span class="lg:sr-only">{{ t('caisse.actions.cancel') }}</span>
          </AppButton>
        </template>
      </ResponsiveTable>

      <div v-if="retraitStore.pagination.total_pages > 1" class="flex items-center justify-between gap-3 rounded-card border border-tone-neutral-border bg-white p-3">
        <p class="text-base text-ink">{{ t('caisseScreens.page_label', { n: retraitStore.pagination.page, total: retraitStore.pagination.total_pages }) }}</p>
        <div class="flex gap-2">
          <AppButton variant="secondary" :icon="ChevronLeftIcon" :aria-label="t('caisseScreens.prev_page')" @click="goToPage(retraitStore.pagination.page - 1)" :disabled="retraitStore.pagination.page === 1" />
          <AppButton variant="secondary" :icon="ChevronRightIcon" :aria-label="t('caisseScreens.next_page')" @click="goToPage(retraitStore.pagination.page + 1)" :disabled="retraitStore.pagination.page === retraitStore.pagination.total_pages" />
        </div>
      </div>
    </section>

    <RetraitModal v-if="showCreateModal" :isSaving="isSavingCreate" :errorMessage="createError"
                  @close="showCreateModal = false" @save="handleCreate" />

    <CaisseCancelModal v-if="cancellingRetrait" :isSaving="isCancelling" :errorMessage="cancelError"
                        :title="t('retraitScreens.cancel_title')" :help="t('retraitScreens.cancel_help')"
                        :label="t('retraitScreens.cancel_label', { amount: formatCurrency(cancellingRetrait.amount), date: formatDate(cancellingRetrait.retrait_at) })"
                        @close="cancellingRetrait = null" @confirm="handleCancel" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRoute } from 'vue-router';
import { useRetraitStore } from '@/stores/retraitStore';
import RetraitModal from '@/components/caisse/RetraitModal.vue';
import CaisseCancelModal from '@/components/caisse/CaisseCancelModal.vue';
import {
  PlusCircleIcon, ChevronLeftIcon, ChevronRightIcon, XCircleIcon,
} from '@heroicons/vue/24/outline';
import { AppButton, PageHeader, FormField, StatusBadge, ResponsiveTable } from '@/components/ui';
import { toneClasses } from '@/design/tones';
import { modeLabel } from '@/utils/paymentModes';

const { t, te } = useI18n();
const retraitStore = useRetraitStore();
const route = useRoute();

// Colonnes du tableau (cartes empilees sous lg) et style commun des champs.
const columns = computed(() => [
  { key: 'date', label: t('retrait.table.date') },
  { key: 'justification', label: t('retrait.table.justification') },
  { key: 'category', label: t('retrait.table.category') },
  { key: 'method', label: t('retrait.table.method') },
  { key: 'amount', label: t('retrait.table.amount'), align: 'right' },
  { key: 'status', label: t('retrait.table.status') },
]);
const fieldClass = 'block w-full min-h-11 lg:min-h-10 rounded-control border border-tone-neutral-border bg-white px-3 text-base text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600';

onMounted(() => {
  // Action rapide de l'accueil du secretariat (?nouveau=1) : ouvre directement le formulaire. Le parametre est
  // retire de l'adresse SANS navigation (router.replace remonterait la page et fermerait le formulaire).
  if (route.query.nouveau === '1') {
    showCreateModal.value = true;
    window.history.replaceState(window.history.state, '', route.path);
  }
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
  if (err.code === 'OVER_CASH') return t('retraitScreens.over_cash');
  if (err.response) {
    const status = err.response.status;
    const detail = err.response.data?.detail;
    if (status === 422) return typeof detail === 'string' && detail ? detail : "Données invalides.";
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

// Les categories sont stockees en codes (SUPPLIES, BILLS...) : libelle traduit, ou le code tel quel s'il est inconnu.
const categoryLabel = (code) => {
  if (!code) return '-';
  const key = `finance.categories.${String(code).toLowerCase()}`;
  return te(key) ? t(key) : code;
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
