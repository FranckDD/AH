<template>
  <div class="grid gap-4">
    <LoadErrorState v-if="store.previousError" @retry="store.fetchPrevious()" />
    <template v-else>
      <ResponsiveTable :columns="columns" :rows="store.previous" row-key="dossier_id" :loading="store.previousLoading"
                       :empty-title="t('toxico.previous.empty')" :empty-message="' '" striped>
        <template #cell-patient="{ row }">
          <span class="block font-semibold">{{ row.patientName }}</span>
          <span class="block font-mono text-sm text-ink-muted">{{ row.code }}</span>
        </template>
        <template #cell-status="{ row }">
          <StatusBadge :tone="row.isActive ? 'success' : 'neutral'" :label="row.isActive ? t('toxico.discharged.tab_active') : t('toxico.discharged.tab_discharged')" />
        </template>
        <template #cell-psy="{ row }">{{ row.psychologist || '-' }}</template>
        <template #actions="{ row }">
          <AppButton variant="info" size="sm" @click="emit('view', row)">{{ t('toxico.discharged.view') }}</AppButton>
        </template>
      </ResponsiveTable>

      <nav v-if="!store.previousLoading && store.previousTotal > PER_PAGE"
           class="flex items-center justify-between gap-2 rounded-card border border-tone-neutral-border bg-white p-3 shadow-card" :aria-label="t('toxicoScreens.pagination_label')">
        <AppButton variant="secondary" :disabled="store.previousPage <= 1" @click="store.setPreviousPage(store.previousPage - 1)">{{ t('toxicoScreens.prev') }}</AppButton>
        <AppButton variant="secondary" :disabled="store.previousPage >= totalPages" @click="store.setPreviousPage(store.previousPage + 1)">{{ t('toxicoScreens.next') }}</AppButton>
      </nav>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { useToxicoStore } from '@/stores/toxicoStore';
import { AppButton, StatusBadge, ResponsiveTable, LoadErrorState } from '@/components/ui';

const emit = defineEmits(['view']);
const { t } = useI18n();
const store = useToxicoStore();
const PER_PAGE = 20;
const totalPages = computed(() => Math.max(1, Math.ceil(store.previousTotal / PER_PAGE)));

const columns = computed(() => [
    { key: 'patient', label: t('toxico.discharged.col.patient') },
    { key: 'status', label: t('toxico.previous.status') },
    { key: 'psy', label: t('toxico.previous.current_psy') },
]);

onMounted(() => { store.fetchPrevious(); });
</script>
