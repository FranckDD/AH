<template>
  <div class="overflow-x-auto">
    <table class="min-w-full text-left border-collapse">
        <thead>
            <tr class="text-xs font-bold text-gray-500 uppercase border-b border-gray-200 bg-gray-50">
                <th class="px-4 py-3">Date</th>
                <th class="px-4 py-3">Examen</th>
                <th class="px-4 py-3">Code Labo</th>
                <th class="px-4 py-3">Statut</th>
                <th class="px-4 py-3 text-right">Action</th>
            </tr>
        </thead>
        <tbody class="divide-y divide-gray-100">
            <tr v-for="res in results" :key="res.result_id" class="hover:bg-gray-50">
                <td class="px-4 py-3 text-sm text-gray-600">{{ res.test_date }}</td>
                <td class="px-4 py-3 font-medium text-gray-900">{{ res.examen_name }}</td>
                <td class="px-4 py-3 text-sm font-mono text-gray-500">{{ res.code_lab }}</td>
                <td class="px-4 py-3">
                    <span :class="getStatusClass(res.status)" class="px-2 py-0.5 rounded text-xs font-bold uppercase">
                        {{ res.status }}
                    </span>
                </td>
                <td class="px-4 py-3 text-right">
                    <button class="text-blue-600 hover:text-blue-800 text-sm font-medium">
                        Voir Résultats
                    </button>
                </td>
            </tr>
            <tr v-if="results.length === 0">
                <td colspan="5" class="px-4 py-8 text-center text-gray-500">Aucun examen réalisé.</td>
            </tr>
        </tbody>
    </table>
  </div>
</template>

<script setup>
defineProps({
    results: { type: Array, default: () => [] }
});

const getStatusClass = (status) => {
    switch(status) {
        case 'completed': return 'bg-green-100 text-green-700';
        case 'pending': return 'bg-yellow-100 text-yellow-700';
        default: return 'bg-gray-100 text-gray-600';
    }
};
</script>