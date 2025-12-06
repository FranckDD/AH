<template>
  <div class="space-y-6 w-full">
    
    <div class="flex flex-col md:flex-row justify-between items-center bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
      <div>
        <h1 class="text-2xl font-extrabold text-gray-800 tracking-tight">
          {{ t('tech.title') }}
        </h1>
        <p class="text-sm text-gray-500">{{ t('tech.subtitle') }}</p>
      </div>
      <div class="mt-4 md:mt-0">
          <input 
              type="date" 
              :placeholder="t('tech.filter.date_from')"
              :value="currentTab === 'ACCESS' ? auditStore.accessFilters.dateFrom : auditStore.actionFilters.dateFrom"
              @change="handleDateChange($event.target.value, 'dateFrom')"
              class="border border-gray-300 rounded-md p-2 text-sm focus:ring-indigo-500 focus:border-indigo-500"
          />
      </div>
    </div>

    <div class="border-b border-gray-200">
      <nav class="-mb-px flex space-x-8">
        <button 
          @click="currentTab = 'ACCESS'"
          :class="[
            currentTab === 'ACCESS'
              ? 'border-indigo-500 text-indigo-600'
              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
            'whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm flex items-center'
          ]"
        >
          <ShieldCheckIcon class="h-5 w-5 mr-2" />
          {{ t('tech.tabs.access') }} ({{ auditStore.accessPagination.total }})
        </button>

        <button 
          @click="currentTab = 'ACTIONS'"
          :class="[
            currentTab === 'ACTIONS'
              ? 'border-indigo-500 text-indigo-600'
              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
            'whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm flex items-center'
          ]"
        >
          <CommandLineIcon class="h-5 w-5 mr-2" />
          {{ t('tech.tabs.actions') }} ({{ auditStore.actionPagination.total }})
        </button>
      </nav>
    </div>

    <div class="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
        
        <div v-if="auditStore.isLoading" class="p-10 text-center text-gray-500">
            <span class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 mb-2"></span>
            <p>{{ t('common.loading') }}</p>
        </div>

        <div v-else-if="currentTab === 'ACCESS'">
            <div class="overflow-x-auto">
                <table class="min-w-full text-left border-collapse">
                    <thead>
                        <tr class="bg-gray-50 text-gray-500 text-xs uppercase tracking-wider">
                            <th class="px-6 py-3 font-semibold">{{ t('tech.table.date') }}</th>
                            <th class="px-6 py-3 font-semibold">{{ t('tech.table.user') }}</th>
                            <th class="px-6 py-3 font-semibold">{{ t('tech.table.action') }}</th>
                            <th class="px-6 py-3 font-semibold">{{ t('tech.table.ip') }}</th>
                            <th class="px-6 py-3 font-semibold">{{ t('tech.table.details') }}</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-gray-100">
                        <tr v-for="log in auditStore.accessLogs" :key="log.id" class="hover:bg-gray-50 transition">
                            <td class="px-6 py-4 text-sm text-gray-600 font-mono">{{ formatDate(log.timestamp) }}</td>
                            <td class="px-6 py-4 font-medium text-gray-900">{{ log.user_name || 'N/A' }}</td>
                            <td class="px-6 py-4">
                                <span :class="getAccessBadge(log.action_type)" class="px-2 py-1 text-xs font-bold rounded-md border">
                                    {{ log.action_type }}
                                </span>
                            </td>
                            <td class="px-6 py-4 text-sm text-gray-500">{{ log.ip_address }}</td>
                            <td class="px-6 py-4 text-sm text-gray-600">{{ log.details || '—' }}</td>
                        </tr>
                    </tbody>
                </table>
            </div>
            
            <Pagination 
                :pagination="auditStore.accessPagination"
                @page-change="(p) => auditStore.setAccessPage(p)"
            />
        </div>

        <div v-else>
            <div class="overflow-x-auto">
                <table class="min-w-full text-left border-collapse">
                    <thead>
                        <tr class="bg-gray-50 text-gray-500 text-xs uppercase tracking-wider">
                            <th class="px-6 py-3 font-semibold">{{ t('tech.table.date') }}</th>
                            <th class="px-6 py-3 font-semibold">{{ t('tech.table.user') }}</th>
                            <th class="px-6 py-3 font-semibold">{{ t('tech.table.resource') }}</th>
                            <th class="px-6 py-3 font-semibold">{{ t('tech.table.action') }}</th>
                            <th class="px-6 py-3 font-semibold">{{ t('tech.table.details') }}</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-gray-100">
                        <tr v-for="act in auditStore.actionLogs" :key="act.id" class="hover:bg-gray-50 transition">
                            <td class="px-6 py-4 text-sm text-gray-600 font-mono">{{ formatDate(act.timestamp) }}</td>
                            <td class="px-6 py-4 font-medium text-gray-900">{{ act.user_name || act.username || 'N/A' }}</td>
                            <td class="px-6 py-4">
                                <span class="bg-gray-100 text-gray-700 px-2 py-1 rounded text-xs font-bold">{{ act.resource_type }}</span>
                            </td>
                            <td class="px-6 py-4">
                                <span :class="getActionBadge(act.action_performed)" class="px-2 py-1 text-xs font-bold rounded-md border">
                                    {{ act.action_performed }}
                                </span>
                            </td>
                            <td class="px-6 py-4 text-sm text-gray-600 truncate max-w-xs" :title="act.new_values?.details || act.details">
                                {{ act.new_values?.details || act.details || '—' }}
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>

            <Pagination 
                :pagination="auditStore.actionPagination"
                @page-change="(p) => auditStore.setActionPage(p)"
            />
        </div>

    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue';
import { useAuditStore } from '@/stores/auditStore';
import { useI18n } from 'vue-i18n';
import { ShieldCheckIcon, CommandLineIcon } from '@heroicons/vue/24/outline';
import Pagination from '@/components/common/Pagination.vue'; 

const { t } = useI18n();
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
        return new Date(timestamp).toLocaleString();
    } catch { return timestamp; }
};

// Styles
const getAccessBadge = (type) => {
    switch(type) {
        case 'LOGIN': return 'bg-green-100 text-green-700 border-green-200';
        case 'LOGOUT': return 'bg-gray-100 text-gray-700 border-gray-200';
        case 'LOGIN_FAILED': return 'bg-red-100 text-red-700 border-red-200';
        default: return 'bg-gray-50 text-gray-600';
    }
};

const getActionBadge = (action) => {
    switch(action) {
        case 'CREATE': return 'bg-blue-100 text-blue-700 border-blue-200';
        case 'UPDATE': return 'bg-orange-100 text-orange-700 border-orange-200';
        case 'DELETE': return 'bg-red-100 text-red-700 border-red-200';
        default: return 'bg-gray-50 text-gray-600';
    }
};
</script>