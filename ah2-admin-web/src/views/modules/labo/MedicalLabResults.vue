<template>
  <div class="max-w-7xl mx-auto p-6 space-y-6 animate-fade-in-up h-full flex flex-col">

    <div class="bg-white p-4 rounded-2xl shadow-sm border border-gray-100 flex flex-col md:flex-row gap-4 items-center justify-between">
      <div class="relative flex-1 max-w-md">
          <MagnifyingGlassIcon class="w-5 h-5 text-gray-400 absolute left-3 top-3"/>
          <input
              v-model="filters.query"
              @input="handleSearch"
              type="text"
              placeholder="Rechercher un patient ou un code..."
              class="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-xl focus:ring-indigo-500 focus:border-indigo-500 transition"
          >
      </div>

      <button @click="refresh" class="p-2 text-gray-500 hover:bg-gray-100 rounded-full transition" title="Actualiser">
        <ArrowPathIcon class="w-5 h-5" :class="{'animate-spin': store.loading}"/>
      </button>
    </div>

    <div class="bg-white rounded-2xl shadow-sm border border-gray-100 flex-1 overflow-hidden flex flex-col">
      <div class="overflow-y-auto flex-1">
        <table class="w-full text-sm text-left">
            <thead class="bg-gray-50 text-gray-500 uppercase font-bold text-xs border-b border-gray-100 sticky top-0 z-10">
            <tr>
                <th class="px-6 py-4">Date & ID</th>
                <th class="px-6 py-4">Patient</th>
                <th class="px-6 py-4">Examen</th>
                <th class="px-6 py-4 text-center">Actions</th>
            </tr>
            </thead>
            <tbody class="divide-y divide-gray-100">
            <tr v-for="res in store.paginatedHistory.items" :key="res.result_id" class="hover:bg-gray-50 transition group">
                <td class="px-6 py-4 whitespace-nowrap">
                    <div class="text-gray-900 font-medium">{{ formatDate(res.test_date) }}</div>
                    <div class="text-[10px] text-gray-400 font-mono">#{{ res.result_id }} <span v-if="res.code">| {{ res.code }}</span></div>
                </td>

                <td class="px-6 py-4">
                    <div class="font-bold text-gray-800">{{ res.patient_name }}</div>
                    <div class="flex gap-2 mt-1">
                        <span class="text-[10px] text-gray-500">{{ res.patient_age }} • {{ res.patient_sexe }}</span>
                        <span v-if="res.is_external" class="text-[9px] bg-orange-50 text-orange-600 px-1.5 py-0.5 rounded font-black uppercase">Externe</span>
                    </div>
                </td>

                <td class="px-6 py-4 text-gray-600 font-medium">
                    {{ res.examen_nom }}
                </td>

                <td class="px-6 py-4">
                    <div class="flex items-center justify-center gap-2">
                        <button
                            @click="openView(res)"
                            class="p-2 text-gray-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition border border-transparent hover:border-indigo-100"
                            title="Voir les détails"
                        >
                            <EyeIcon class="w-5 h-5"/>
                        </button>

                        <button
                            @click="downloadPdf(res)"
                            class="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition border border-transparent hover:border-red-100"
                            title="Télécharger PDF"
                        >
                            <PrinterIcon class="w-5 h-5"/>
                        </button>
                    </div>
                </td>
            </tr>
            </tbody>
        </table>

        <div v-if="store.paginatedHistory.items.length === 0 && !store.loading" class="flex flex-col items-center justify-center h-64 text-gray-400">
            <DocumentMagnifyingGlassIcon class="w-16 h-16 mb-2 opacity-20"/>
            <p class="font-medium">Aucun examen complet trouvé.</p>
            <p class="text-xs">Les examens en cours restent visibles uniquement par le laboratoire.</p>
        </div>
      </div>

      <div v-if="store.paginatedHistory.total_pages > 0" class="border-t border-gray-100 bg-gray-50 px-6 py-3 flex items-center justify-between">
          <div class="text-sm text-gray-500">
              Affichage de <span class="font-medium">{{ store.paginatedHistory.items.length }}</span> sur <span class="font-medium">{{ store.paginatedHistory.total_items }}</span> résultats
          </div>
          <div class="flex items-center space-x-2 text-sm">
              <button
                  @click="prevPage"
                  :disabled="filters.page === 1"
                  class="px-3 py-1 rounded-lg border border-gray-200 bg-white text-gray-600 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed transition"
              >
                  Précédent
              </button>
              <span class="px-3 py-1 text-gray-600 font-medium">
                  Page {{ store.paginatedHistory.current_page }} / {{ store.paginatedHistory.total_pages }}
              </span>
              <button
                  @click="nextPage"
                  :disabled="filters.page >= store.paginatedHistory.total_pages"
                  class="px-3 py-1 rounded-lg border border-gray-200 bg-white text-gray-600 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed transition"
              >
                  Suivant
              </button>
          </div>
      </div>
    </div>

    <ResultDetailModal
        v-if="selectedResult"
        :result="selectedResult"
        @close="selectedResult = null"
        @print="downloadPdf"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useLabStore } from '@/stores/labStore';
import ResultDetailModal from '@/components/lab/ResultDetailModal.vue';
import dayjs from 'dayjs';
import debounce from 'lodash/debounce';
import {
    MagnifyingGlassIcon, ArrowPathIcon, PrinterIcon,
    DocumentMagnifyingGlassIcon, EyeIcon
} from '@heroicons/vue/24/outline';

// Vue dediee medecin/nurse (chantier perimetre medical, 2026-09-22) - pas
// de selecteur de statut : le backend (controller/lab_controller.py,
// Tache 3 de ce meme plan) force deja "completed" pour ce role, quel que
// soit le parametre envoye. L'afficher laisserait croire qu'on peut choisir
// "en attente" pour ne jamais rien voir.
const store = useLabStore();
const selectedResult = ref(null);

const filters = ref({
    query: '',
    page: 1,
    limit: 15
});

const fetchData = async () => {
    const q = filters.value.query;
    if (q.length === 1) return;

    await store.fetchPaginatedHistory({
        page: filters.value.page,
        limit: filters.value.limit,
        search: q.length >= 2 ? q : null,
    });
};

const handleSearch = debounce(() => {
    filters.value.page = 1;
    fetchData();
}, 400);

const nextPage = () => {
    if (filters.value.page < store.paginatedHistory.total_pages) {
        filters.value.page++;
        fetchData();
    }
};

const prevPage = () => {
    if (filters.value.page > 1) {
        filters.value.page--;
        fetchData();
    }
};

const refresh = () => {
    filters.value.query = '';
    filters.value.page = 1;
    fetchData();
};

const openView = async (item) => {
    const detail = await store.fetchResultDetail(item.result_id);
    if (detail) {
        selectedResult.value = detail;
    }
};

const downloadPdf = async (item) => {
    const filename = `Resultat_${item.result_id}.pdf`;
    await store.downloadPDF(item.result_id, filename);
};

const formatDate = (d) => {
    if (!d) return 'N/A';
    return dayjs(d).format('DD/MM/YYYY HH:mm');
};

onMounted(() => {
    fetchData();
});
</script>

<style scoped>
.animate-fade-in-up {
  animation: fadeInUp 0.4s ease-out;
}

@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
