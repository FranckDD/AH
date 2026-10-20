<template>
  <div class="space-y-6 w-full animate-fade-in-up p-2 md:p-6 bg-gray-50 min-h-screen">
    
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-2">
      <div>
        <h1 class="text-2xl font-black text-gray-800 tracking-tight">{{ t('lab.dashboard.title') }}</h1>
        <p class="text-sm text-gray-500">{{ t('lab.dashboard.subtitle') }}</p>
      </div>
      
      <div class="flex bg-white p-1 rounded-xl shadow-xs border border-gray-200">
        <button 
          v-for="p in ['day', 'month', 'year']" :key="p"
          @click="changePeriod(p)"
          :class="currentPeriod === p ? 'bg-indigo-600 text-white shadow-md' : 'text-gray-500 hover:bg-gray-50'"
          class="px-4 py-1.5 rounded-lg text-xs font-bold transition-all duration-200 capitalize"
        >
          {{ t(`lab.dashboard.period_${p}`) }}
        </button>
      </div>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div @click="$router.push({name: 'lab-technician'})" class="card-stat border-l-4 border-l-yellow-400 cursor-pointer hover:scale-105 transition-transform">
            <div class="flex justify-between">
                <div>
                    <p class="stat-label">{{ t('lab.dashboard.pending') }}</p>
                    <h3 class="stat-value">{{ stats?.pending ?? 0 }}</h3>
                </div>
                <div class="stat-icon bg-yellow-50"><ClockIcon class="text-yellow-600 h-6 w-6" /></div>
            </div>
            <p class="mt-4 text-xs text-gray-400 font-medium">{{ t('lab.dashboard.pending_hint') }}</p>
        </div>

        <div class="card-stat border-l-4 border-l-green-500">
            <div class="flex justify-between">
                <div>
                    <p class="stat-label">{{ t('lab.dashboard.completed') }}</p>
                    <h3 class="stat-value">{{ stats?.completed_today ?? 0 }}</h3>
                </div>
                <div class="stat-icon bg-green-50"><CheckBadgeIcon class="text-green-600 h-6 w-6" /></div>
            </div>
            <p class="mt-4 text-xs text-gray-400 font-medium">{{ t('lab.dashboard.completed_hint') }}</p>
        </div>

        <div @click="$router.push({name: 'lab-history', query: { abnormal: '1', period: currentPeriod }})" class="card-stat border-l-4 border-l-red-500 cursor-pointer hover:scale-105 transition-transform">
            <div class="flex justify-between">
                <div>
                    <p class="stat-label">{{ t('lab.dashboard.critical') }}</p>
                    <h3 class="stat-value text-red-600">{{ stats?.critical ?? 0 }}</h3>
                </div>
                <div class="stat-icon bg-red-50"><ExclamationTriangleIcon class="text-red-600 h-6 w-6" /></div>
            </div>
            <p class="mt-4 text-xs text-red-400 font-medium">{{ t('lab.dashboard.critical_hint') }}</p>
        </div>

        <div class="card-stat border-l-4 border-l-blue-500">
            <div class="flex justify-between">
                <div>
                    <p class="stat-label">{{ t('lab.dashboard.total') }}</p>
                    <h3 class="stat-value">{{ stats?.total_month ?? 0 }}</h3>
                </div>
                <div class="stat-icon bg-blue-50"><ClipboardDocumentListIcon class="text-blue-600 h-6 w-6" /></div>
            </div>
             <p class="mt-4 text-xs text-gray-400 font-medium">{{ t('lab.dashboard.total_hint') }}</p>
        </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        <div class="bg-white rounded-2xl shadow-xs border border-gray-100 lg:col-span-2 flex flex-col overflow-hidden">
            <div class="p-5 border-b border-gray-100 flex justify-between items-center bg-white">
                <h3 class="text-lg font-bold text-gray-800 flex items-center gap-2">
                    <ClockIcon class="w-5 h-5 text-indigo-500"/>
                    {{ t('lab.dashboard.recent') }}
                </h3>
                <button @click="$router.push({name: 'lab-technician'})" class="text-xs text-indigo-600 font-bold hover:text-indigo-800 transition">
                    {{ t('lab.dashboard.see_bench') }} &rarr;
                </button>
            </div>
            
            <div class="overflow-x-auto">
                <table class="w-full text-sm text-left">
                    <thead class="bg-gray-50/50 text-gray-500 text-xs uppercase tracking-wider">
                        <tr>
                            <th class="px-5 py-4 font-semibold">{{ t('lab.dashboard.col_patient') }}</th>
                            <th class="px-5 py-4 font-semibold">{{ t('lab.dashboard.col_exam') }}</th>
                            <th class="px-5 py-4 font-semibold text-right">{{ t('lab.dashboard.col_action') }}</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-gray-100">
                        <tr v-if="!stats?.recent_pending?.length">
                            <td colspan="3" class="px-5 py-8 text-center text-gray-400 italic">
                                {{ t('lab.dashboard.no_pending') }}
                            </td>
                        </tr>
                        <tr v-for="item in stats.recent_pending" :key="item.id" class="hover:bg-indigo-50/30 transition group">
                            <td class="px-5 py-3">
                                <div class="flex items-center gap-3">
                                    <div class="h-8 w-8 rounded-full bg-gray-100 flex items-center justify-center text-xs font-bold text-gray-600 group-hover:bg-indigo-100 group-hover:text-indigo-600 transition">
                                        {{ item.patient_name?.charAt(0) || '?' }}
                                    </div>
                                    <div>
                                        <div class="font-bold text-gray-900">{{ item.patient_name || t('lab.dashboard.unknown_patient') }}</div>
                                        <div class="text-[10px] uppercase tracking-widest text-gray-400">{{ item.code_patient || 'N/A' }}</div>
                                    </div>
                                </div>
                            </td>
                            <td class="px-5 py-3">
                                <span class="badge-exam">{{ item.test_type || t('lab.dashboard.col_exam') }}</span>
                            </td>
                            <td class="px-5 py-3 text-right">
                                <button @click="goToTechnician(item)" class="btn-saisir">{{ t('lab.dashboard.enter') }}</button>
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>

        <div class="bg-white p-6 rounded-2xl shadow-xs border border-gray-100 flex flex-col">
            <h3 class="text-lg font-bold text-gray-800 mb-6 flex items-center gap-2">
                <ArrowTrendingUpIcon class="w-5 h-5 text-indigo-500" />
                {{ t('lab.dashboard.top_exams') }}
            </h3>
            
            <div v-if="!stats?.top_exams || Object.keys(stats.top_exams).length === 0" class="text-sm text-gray-400 italic text-center py-4">
                {{ t('lab.dashboard.no_data') }}
            </div>

            <div v-else class="space-y-5 flex-1">
                <div v-for="(count, name) in stats.top_exams" :key="name" class="relative">
                    <div class="flex justify-between text-sm mb-1.5">
                        <span class="text-gray-700 font-medium">{{ name }}</span>
                        <span class="font-bold text-indigo-600">{{ count }}</span>
                    </div>
                    <div class="w-full bg-gray-100 rounded-full h-2 overflow-hidden">
                        <div class="bg-linear-to-r from-indigo-400 to-indigo-600 h-2 rounded-full transition-all duration-1000 ease-out" 
                             :style="{ width: (count / (stats.max_exam_count || 1) * 100) + '%' }">
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue';
import { useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { useLabStore } from '@/stores/labStore'; 
import { 
    ClockIcon, CheckBadgeIcon, ExclamationTriangleIcon, 
    ArrowTrendingUpIcon, ClipboardDocumentListIcon 
} from '@heroicons/vue/24/outline';

const router = useRouter();
const { t } = useI18n();
const labStore = useLabStore();

const currentPeriod = ref('month');
let refreshInterval = null;

/**
 * Calcul sécurisé des statistiques. 
 * Garantit que le template a toujours une structure d'objet valide même si l'API échoue.
 */
const stats = computed(() => {
    return labStore.stats || {
        pending: 0,
        completed_today: 0,
        critical: 0,
        total_month: 0,
        recent_pending: [],
        top_exams: {},
        max_exam_count: 1
    };
});

/**
 * Charge les données depuis le store
 */
const loadData = async () => {
    try {
        await labStore.fetchDashboardStats(currentPeriod.value);
    } catch (error) {
        console.error("Erreur UI Dashboard:", error);
    }
};

/**
 * Change la période de filtrage
 */
const changePeriod = async (period) => {
    currentPeriod.value = period;
    await loadData();
};

onMounted(() => {
    loadData();
    // Rafraîchissement automatique toutes les 5 minutes
    refreshInterval = setInterval(loadData, 300000);
});

onUnmounted(() => {
    if (refreshInterval) {
        clearInterval(refreshInterval);
        refreshInterval = null;
    }
});

/**
 * Navigation vers la paillasse avec filtre auto
 */
const goToTechnician = (item) => {
    if (item?.id) {
        router.push({ name: 'lab-technician', query: { open: String(item.id) } });
    }
};
</script>

<style scoped>
/* Tailwind v4 : @apply dans un bloc <style> scope necessite une reference
   explicite au theme (plus d'injection implicite comme en v3). */
@reference "../../style.css";

/* Animations d'entrée */
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
.animate-fade-in-up {
  animation: fadeInUp 0.4s ease-out forwards;
}

/* Classes utilitaires Tailwind (via @apply pour la lisibilité) */
.card-stat {
  @apply bg-white p-5 rounded-2xl shadow-xs border border-gray-100;
}
.stat-label {
  @apply text-sm font-semibold text-gray-500 mb-1;
}
.stat-value {
  @apply text-3xl font-black text-gray-800;
}
.stat-icon {
  @apply h-12 w-12 rounded-xl flex items-center justify-center;
}
.badge-exam {
  @apply px-2.5 py-1 rounded-md bg-white border border-gray-200 text-xs font-semibold text-gray-700 shadow-xs whitespace-nowrap;
}
.btn-saisir {
  @apply inline-flex items-center justify-center px-4 py-1.5 bg-indigo-50 text-indigo-700 hover:bg-indigo-600 hover:text-white text-xs font-bold rounded-lg transition-colors duration-200;
}
</style>