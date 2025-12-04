<template>
  <div class="space-y-6 w-full">
    
    <div class="flex items-center justify-between bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
        <div>
            <h1 class="text-2xl font-extrabold text-gray-800 tracking-tight">
                {{ t('toxico.dashboard.title') }}
            </h1>
            <p class="text-sm text-gray-500">{{ t('toxico.dashboard.subtitle') }}</p>
        </div>
        <div class="flex space-x-2">
            <span class="px-3 py-1 bg-green-100 text-green-700 text-sm font-medium rounded-full flex items-center">
                <div class="w-2 h-2 bg-green-500 rounded-full mr-2 animate-pulse"></div>
                Service Opérationnel
            </span>
        </div>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div class="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 flex flex-col justify-between">
            <div class="flex justify-between items-start">
                <div>
                    <p class="text-sm font-medium text-gray-500 uppercase">{{ t('toxico.dashboard.active_patients') }}</p>
                    <h3 class="text-3xl font-bold text-gray-900 mt-2">{{ toxicoStore.totalActive }}</h3>
                </div>
                <div class="p-2 bg-indigo-50 rounded-lg">
                    <UserGroupIcon class="h-6 w-6 text-indigo-600" />
                </div>
            </div>
            <div class="mt-4 text-xs text-green-600 flex items-center font-medium">
                <ArrowTrendingUpIcon class="h-3 w-3 mr-1" /> +2 cette semaine
            </div>
        </div>

        <div class="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 flex flex-col justify-between">
            <div class="flex justify-between items-start">
                <div>
                    <p class="text-sm font-medium text-gray-500 uppercase">{{ t('toxico.dashboard.relapse_rate') }}</p>
                    <h3 class="text-3xl font-bold text-gray-900 mt-2">{{ toxicoStore.relapseRate }}%</h3>
                </div>
                <div class="p-2 bg-red-50 rounded-lg">
                    <ExclamationTriangleIcon class="h-6 w-6 text-red-600" />
                </div>
            </div>
            <div class="w-full bg-gray-200 rounded-full h-1.5 mt-4">
                <div class="bg-red-500 h-1.5 rounded-full" :style="{ width: toxicoStore.relapseRate + '%' }"></div>
            </div>
        </div>

        <div class="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 flex flex-col justify-between">
            <div class="flex justify-between items-start">
                <div>
                    <p class="text-sm font-medium text-gray-500 uppercase">En Sevrage (Phase 1)</p>
                    <h3 class="text-3xl font-bold text-gray-900 mt-2">{{ toxicoStore.statsByPhase[1] || 0 }}</h3>
                </div>
                <div class="p-2 bg-orange-50 rounded-lg">
                    <FireIcon class="h-6 w-6 text-orange-600" />
                </div>
            </div>
            <p class="text-xs text-gray-400 mt-4">Nécessitent une surveillance accrue</p>
        </div>

        <div class="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 flex flex-col justify-between">
        <div class="flex justify-between items-start">
            <div>
                <p class="text-sm font-medium text-gray-500 uppercase">{{ t('toxico.dashboard.new_this_month') }}</p>
                <h3 class="text-3xl font-bold text-gray-900 mt-2">{{ toxicoStore.currentMonthAdmissions }}</h3>
            </div>
            <div class="p-2 bg-green-50 rounded-lg">
                <CalendarIcon class="h-6 w-6 text-green-600" />
            </div>
        </div>
    </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        <div class="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 lg:col-span-2">
            <h3 class="text-lg font-bold text-gray-800 mb-6">{{ t('toxico.dashboard.phase_dist') }}</h3>
            
            <div class="space-y-5">
                <div v-for="phase in [1, 2, 3, 4]" :key="phase" class="group">
                    <div class="flex justify-between items-center mb-1">
                        <span class="text-sm font-medium text-gray-700">{{ t(`toxico.phases.${phase}`) }}</span>
                        <span class="text-sm font-bold text-gray-900">{{ toxicoStore.statsByPhase[phase] || 0 }} patients</span>
                    </div>
                    <div class="w-full bg-gray-100 rounded-full h-3">
                        <div 
                            class="h-3 rounded-full transition-all duration-1000 ease-out"
                            :class="getPhaseColor(phase)"
                            :style="{ width: getPercentage(toxicoStore.statsByPhase[phase]) + '%' }"
                        ></div>
                    </div>
                </div>
            </div>
        </div>

        <div class="bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
            <h3 class="text-lg font-bold text-gray-800 mb-6">{{ t('toxico.dashboard.substance_dist') }}</h3>
            
            <div class="space-y-4">
                <div v-for="(count, substance) in toxicoStore.statsBySubstance" :key="substance" class="flex items-center justify-between p-3 bg-gray-50 rounded-xl">
                    <div class="flex items-center">
                        <div class="w-2 h-8 rounded-l bg-indigo-500 mr-3"></div>
                        <span class="font-medium text-gray-700">{{ substance }}</span>
                    </div>
                    <span class="font-bold text-gray-900 bg-white px-3 py-1 rounded-lg shadow-sm border border-gray-100">{{ count }}</span>
                </div>
            </div>
        </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        <div class="bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
            <h3 class="text-lg font-bold text-gray-800 mb-4">{{ t('toxico.dashboard.psy_workload') }}</h3>
            <div class="overflow-x-auto">
                <table class="w-full text-sm text-left">
                    <thead class="bg-gray-50 text-gray-500">
                        <tr>
                            <th class="px-4 py-2 rounded-l-lg">Psychologue</th>
                            <th class="px-4 py-2 rounded-r-lg text-right">Patients suivis</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-gray-100">
                        <tr v-for="psy in toxicoStore.statsByPsy" :key="psy.name">
                            <td class="px-4 py-3 font-medium text-gray-900">{{ psy.name }}</td>
                            <td class="px-4 py-3 text-right">
                                <span class="bg-indigo-100 text-indigo-800 py-1 px-3 rounded-full text-xs font-bold">
                                    {{ psy.count }}
                                </span>
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>

        <div class="bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
            <h3 class="text-lg font-bold text-gray-800 mb-4">{{ t('toxico.dashboard.alerts') }}</h3>
            <div class="space-y-3">
                
                <div v-if="toxicoStore.generatedAlerts.length === 0" class="text-gray-500 text-sm italic text-center py-4">
                    Aucune alerte à signaler pour l'instant.
                </div>

                <div v-for="alert in toxicoStore.generatedAlerts" :key="alert.id" 
                    class="flex items-start p-3 rounded-xl border"
                    :class="alert.type === 'critical' ? 'bg-red-50 border-red-100' : 'bg-yellow-50 border-yellow-100'">
                    
                    <ExclamationCircleIcon v-if="alert.type === 'critical'" class="h-5 w-5 text-red-600 mr-3 mt-0.5" />
                    <ClockIcon v-else class="h-5 w-5 text-yellow-600 mr-3 mt-0.5" />
                    
                    <div>
                        <p class="text-sm font-bold" 
                        :class="alert.type === 'critical' ? 'text-red-800' : 'text-yellow-800'">
                        {{ alert.title }}
                        </p>
                        <p class="text-xs mt-1" 
                        :class="alert.type === 'critical' ? 'text-red-600' : 'text-yellow-600'">
                        {{ alert.message }}
                        </p>
                    </div>
                </div>
            </div>
        </div>

    </div>

  </div>
</template>

<script setup>
import { onMounted } from 'vue';
import { useToxicoStore } from '@/stores/toxicoStore';
import { useI18n } from 'vue-i18n';
import { 
    UserGroupIcon, 
    ArrowTrendingUpIcon, 
    ExclamationTriangleIcon, 
    FireIcon, 
    CalendarIcon,
    ExclamationCircleIcon,
    ClockIcon
} from '@heroicons/vue/24/outline';

const { t } = useI18n();
const toxicoStore = useToxicoStore();

onMounted(() => {
    toxicoStore.fetchToxicoPatients();
});

// Helpers
const getPercentage = (count) => {
    if (!count || toxicoStore.totalActive === 0) return 0;
    return (count / toxicoStore.totalActive) * 100;
};

const getPhaseColor = (phase) => {
    switch(phase) {
        case 1: return 'bg-red-500';
        case 2: return 'bg-orange-500';
        case 3: return 'bg-blue-500';
        case 4: return 'bg-green-500';
        default: return 'bg-gray-500';
    }
};
</script>