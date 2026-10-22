<template>
  <div class="grid w-full gap-6">

    <PageHeader :title="t('tech.title')" :subtitle="t('tech.subtitle')">
      <template #actions>
        <div class="md:w-52">
          <FormField id="logs-from" :label="t('techScreens.date_from')" v-slot="{ describedBy }">
            <input id="logs-from" type="date"
                   :value="currentTab === 'ACCESS' ? auditStore.accessFilters.dateFrom : auditStore.actionFilters.dateFrom"
                   @change="handleDateChange($event.target.value, 'dateFrom')"
                   :aria-describedby="describedBy" :class="fieldClass" />
          </FormField>
        </div>
      </template>
    </PageHeader>

    <div role="tablist" :aria-label="t('techScreens.tabs_label')" class="flex flex-col gap-1 border-b border-tone-neutral-border sm:flex-row sm:gap-2">
      <button
        type="button" role="tab" id="logs-tab-access" aria-controls="logs-panel-access"
        :aria-selected="currentTab === 'ACCESS'"
        @click="currentTab = 'ACCESS'"
        :class="[
          currentTab === 'ACCESS' ? 'border-brand-600 text-brand-700 font-semibold' : 'border-transparent text-ink-muted hover:border-tone-neutral-border hover:text-ink',
          'flex min-h-11 items-center gap-2 border-b-4 px-3 text-base focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600'
        ]"
      >
        <ShieldCheckIcon class="h-5 w-5 shrink-0" aria-hidden="true" />
        {{ t('tech.tabs.access') }} ({{ auditStore.accessPagination.total }})
      </button>

      <button
        type="button" role="tab" id="logs-tab-actions" aria-controls="logs-panel-actions"
        :aria-selected="currentTab === 'ACTIONS'"
        @click="currentTab = 'ACTIONS'"
        :class="[
          currentTab === 'ACTIONS' ? 'border-brand-600 text-brand-700 font-semibold' : 'border-transparent text-ink-muted hover:border-tone-neutral-border hover:text-ink',
          'flex min-h-11 items-center gap-2 border-b-4 px-3 text-base focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600'
        ]"
      >
        <CommandLineIcon class="h-5 w-5 shrink-0" aria-hidden="true" />
        {{ t('tech.tabs.actions') }} ({{ auditStore.actionPagination.total }})
      </button>
    </div>

    <section v-if="currentTab === 'ACCESS'" id="logs-panel-access" role="tabpanel" aria-labelledby="logs-tab-access" class="grid gap-3">
      <ResponsiveTable
        :columns="accessColumns"
        :rows="auditStore.accessLogs"
        row-key="id"
        :loading="auditStore.isLoading"
        :empty-title="t('techScreens.empty')"
        :empty-message="' '"
        striped
      >
        <template #cell-date="{ row: log }"><span class="font-mono">{{ formatDate(log.timestamp) }}</span></template>
        <template #cell-user="{ row: log }"><span class="font-medium">{{ log.user_name || 'N/A' }}</span></template>
        <template #cell-action="{ row: log }"><StatusBadge :tone="getAccessBadge(log.action_type)" :label="String(log.action_type ?? '-')" /></template>
        <template #cell-ip="{ row: log }">{{ log.ip_address }}</template>
        <template #cell-details="{ row: log }">{{ log.details || '-' }}</template>
      </ResponsiveTable>

      <div v-if="auditStore.accessPagination.total_pages > 1" class="flex items-center justify-between gap-3 rounded-card border border-tone-neutral-border bg-white p-3">
        <p class="text-base text-ink">{{ t('techScreens.page_label', { n: auditStore.accessPagination.page, total: auditStore.accessPagination.total_pages, count: auditStore.accessPagination.total }) }}</p>
        <div class="flex gap-2">
          <AppButton variant="secondary" :icon="ChevronLeftIcon" :aria-label="t('techScreens.prev_page')" @click="auditStore.setAccessPage(auditStore.accessPagination.page - 1)" :disabled="auditStore.accessPagination.page <= 1" />
          <AppButton variant="secondary" :icon="ChevronRightIcon" :aria-label="t('techScreens.next_page')" @click="auditStore.setAccessPage(auditStore.accessPagination.page + 1)" :disabled="auditStore.accessPagination.page >= auditStore.accessPagination.total_pages" />
        </div>
      </div>
    </section>

    <section v-else id="logs-panel-actions" role="tabpanel" aria-labelledby="logs-tab-actions" class="grid gap-3">
      <ResponsiveTable
        :columns="actionColumns"
        :rows="auditStore.actionLogs"
        row-key="id"
        :loading="auditStore.isLoading"
        :empty-title="t('techScreens.empty')"
        :empty-message="' '"
        striped
      >
        <template #cell-date="{ row: act }"><span class="font-mono">{{ formatDate(act.timestamp) }}</span></template>
        <template #cell-user="{ row: act }"><span class="font-medium">{{ act.user_name || act.username || 'N/A' }}</span></template>
        <template #cell-resource="{ row: act }"><StatusBadge tone="neutral" :label="String(act.resource_type ?? '-')" /></template>
        <template #cell-action="{ row: act }"><StatusBadge :tone="getActionBadge(act.action_performed)" :label="String(act.action_performed ?? '-')" /></template>
        <template #cell-details="{ row: act }">
          <span class="block max-w-xs truncate" :title="act.new_values?.details || act.details">{{ act.new_values?.details || act.details || '-' }}</span>
        </template>
      </ResponsiveTable>

      <div v-if="auditStore.actionPagination.total_pages > 1" class="flex items-center justify-between gap-3 rounded-card border border-tone-neutral-border bg-white p-3">
        <p class="text-base text-ink">{{ t('techScreens.page_label', { n: auditStore.actionPagination.page, total: auditStore.actionPagination.total_pages, count: auditStore.actionPagination.total }) }}</p>
        <div class="flex gap-2">
          <AppButton variant="secondary" :icon="ChevronLeftIcon" :aria-label="t('techScreens.prev_page')" @click="auditStore.setActionPage(auditStore.actionPagination.page - 1)" :disabled="auditStore.actionPagination.page <= 1" />
          <AppButton variant="secondary" :icon="ChevronRightIcon" :aria-label="t('techScreens.next_page')" @click="auditStore.setActionPage(auditStore.actionPagination.page + 1)" :disabled="auditStore.actionPagination.page >= auditStore.actionPagination.total_pages" />
        </div>
      </div>
    </section>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue';
import { useAuditStore } from '@/stores/auditStore';
import { useI18n } from 'vue-i18n';
import { ShieldCheckIcon, CommandLineIcon, ChevronLeftIcon, ChevronRightIcon } from '@heroicons/vue/24/outline';
import { AppButton, PageHeader, FormField, StatusBadge, ResponsiveTable } from '@/components/ui';

const { t, locale } = useI18n();

// Colonnes de chaque onglet (cartes empilees sous lg) et style commun des champs.
const accessColumns = computed(() => [
    { key: 'date', label: t('tech.table.date') },
    { key: 'user', label: t('tech.table.user') },
    { key: 'action', label: t('tech.table.action') },
    { key: 'ip', label: t('tech.table.ip') },
    { key: 'details', label: t('tech.table.details') },
]);
const actionColumns = computed(() => [
    { key: 'date', label: t('tech.table.date') },
    { key: 'user', label: t('tech.table.user') },
    { key: 'resource', label: t('tech.table.resource') },
    { key: 'action', label: t('tech.table.action') },
    { key: 'details', label: t('tech.table.details') },
]);
const fieldClass = 'block w-full min-h-11 lg:min-h-10 rounded-control border border-tone-neutral-border bg-white px-3 text-base text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600';
const auditStore = useAuditStore();
const currentTab = ref('ACCESS');

onMounted(() => {
    // Appel initial pour charger la page 1
    auditStore.fetchAccessLogs();
    auditStore.fetchActionLogs();
});

// Re-fetch intelligent lors du changement d'onglet si vide
watch(currentTab, (newTab) => {
    if (newTab === 'ACCESS' && auditStore.accessLogs.length === 0) {
        auditStore.fetchAccessLogs();
    } else if (newTab === 'ACTIONS' && auditStore.actionLogs.length === 0) {
        auditStore.fetchActionLogs();
    }
});

// Gestion date
const handleDateChange = (value, filterKey) => {
    const filters = { [filterKey]: value };
    if (currentTab.value === 'ACCESS') {
        auditStore.setAccessFilters(filters);
    } else {
        auditStore.setActionFilters(filters);
    }
};

const formatDate = (timestamp) => {
    if (!timestamp) return 'N/A';
    try {
        return new Date(timestamp).toLocaleString(locale.value === 'en' ? 'en-GB' : 'fr-FR');
    } catch { return timestamp; }
};

// Styles
const getAccessBadge = (type) => {
    switch(type) {
        case 'LOGIN': return 'success';
        case 'LOGOUT': return 'neutral';
        case 'LOGIN_FAILED': return 'danger';
        default: return 'neutral';
    }
};

const getActionBadge = (action) => {
    switch(action) {
        case 'CREATE': return 'info';
        case 'UPDATE': return 'warning';
        case 'DELETE': return 'danger';
        default: return 'neutral';
    }
};
</script>