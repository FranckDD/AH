<template>
  <div class="overflow-x-auto">
    <table class="min-w-full text-left border-collapse">
        <thead>
            <tr class="text-xs font-bold text-gray-500 uppercase border-b border-gray-200 bg-gray-50">
                <th class="px-4 py-3">{{ t('lab.patient_table.date') }}</th>
                <th class="px-4 py-3">{{ t('lab.patient_table.exam') }}</th>
                <th class="px-4 py-3">{{ t('lab.patient_table.lab_code') }}</th>
                <th class="px-4 py-3">{{ t('lab.patient_table.status') }}</th>
                <th class="px-4 py-3 text-right">{{ t('lab.patient_table.action') }}</th>
            </tr>
        </thead>
        <tbody class="divide-y divide-gray-100">
            <tr v-for="res in results" :key="res.result_id" class="hover:bg-gray-50">
                <td class="px-4 py-3 text-sm text-gray-600">{{ res.test_date }}</td>
                <td class="px-4 py-3 font-medium text-gray-900">{{ res.examen_name }}</td>
                <td class="px-4 py-3 text-sm font-mono text-gray-500">{{ res.code_lab }}</td>
                <td class="px-4 py-3">
                    <div class="flex items-center gap-2">
                        <span :class="getStatusClass(res.status)" class="px-2 py-0.5 rounded-sm text-xs font-bold uppercase">
                            {{ statusLabel(res.status) }}
                        </span>
                        <span v-if="res.nb_anormaux > 0"
                              class="bg-red-100 text-red-700 border border-red-200 px-2 py-0.5 rounded-full text-xs font-bold">
                            {{ t('lab.patient_table.abnormal_count', { n: res.nb_anormaux }, res.nb_anormaux) }}
                        </span>
                    </div>
                </td>
                <td class="px-4 py-3 text-right">
                    <button @click="openDetail(res)" class="text-blue-600 hover:text-blue-800 text-sm font-medium">
                        {{ t('lab.patient_table.view_results') }}
                    </button>
                </td>
            </tr>
            <tr v-if="results.length === 0">
                <td colspan="5" class="px-4 py-8 text-center text-gray-500">{{ t('lab.patient_table.empty') }}</td>
            </tr>
        </tbody>
    </table>

    <p v-if="detailError" class="mt-3 text-sm text-red-600">{{ detailError }}</p>

    <ResultDetailModal
        v-if="selectedResult"
        :result="selectedResult"
        @close="selectedResult = null"
        @print="downloadPdf"
    />
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { useLabStore } from '@/stores/labStore';
import ResultDetailModal from '@/components/lab/ResultDetailModal.vue';

defineProps({
    results: { type: Array, default: () => [] }
});

const { t } = useI18n();
const labStore = useLabStore();
const selectedResult = ref(null);
const detailError = ref('');

const getStatusClass = (status) => {
    switch(status) {
        case 'completed': return 'bg-green-100 text-green-700';
        case 'pending': return 'bg-yellow-100 text-yellow-700';
        default: return 'bg-gray-100 text-gray-600';
    }
};

const statusLabel = (status) => {
    const known = ['pending', 'partial', 'analyzed', 'completed', 'validated'];
    return known.includes(status) ? t(`lab.status.${status}`) : (status || '');
};

// Le detail (valeurs, flags, normes) est charge a la demande : la liste du
// dossier reste legere et n'embarque que le compteur d'anomalies.
const openDetail = async (res) => {
    detailError.value = '';
    const detail = await labStore.fetchResultDetail(res.result_id);
    if (detail) {
        selectedResult.value = detail;
    } else {
        detailError.value = t('lab.patient_table.detail_unavailable');
    }
};

const downloadPdf = async (item) => {
    await labStore.downloadPDF(item.result_id, `Resultat_${item.result_id}.pdf`);
};
</script>
