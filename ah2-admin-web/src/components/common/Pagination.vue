<template>
  <div class="px-6 py-4 flex items-center justify-between border-t border-gray-100 bg-gray-50">
    
    <div class="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
      <div>
        <p class="text-sm text-gray-700">
          Affichage de la page
          <span class="font-medium">{{ pagination.page }}</span>
          sur
          <span class="font-medium">{{ pagination.total_pages }}</span>
          <span v-if="pagination.total" class="text-gray-500 ml-1">
            (Total : {{ pagination.total }} entrées)
          </span>
        </p>
      </div>
      
      <div>
        <nav class="relative z-0 inline-flex rounded-md shadow-sm -space-x-px" aria-label="Pagination">
          
          <button
            @click="changePage(pagination.page - 1)"
            :disabled="pagination.page <= 1"
            class="relative inline-flex items-center px-2 py-2 rounded-l-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <span class="sr-only">Précédent</span>
            <ChevronLeftIcon class="h-5 w-5" aria-hidden="true" />
          </button>

          <button
            @click="changePage(pagination.page + 1)"
            :disabled="pagination.page >= pagination.total_pages"
            class="relative inline-flex items-center px-2 py-2 rounded-r-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <span class="sr-only">Suivant</span>
            <ChevronRightIcon class="h-5 w-5" aria-hidden="true" />
          </button>
          
        </nav>
      </div>
    </div>

    <div class="flex items-center justify-between sm:hidden w-full">
       <button
          @click="changePage(pagination.page - 1)"
          :disabled="pagination.page <= 1"
          class="relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
        >
          Préc.
        </button>
        <span class="text-sm text-gray-700">Page {{ pagination.page }}</span>
        <button
          @click="changePage(pagination.page + 1)"
          :disabled="pagination.page >= pagination.total_pages"
          class="relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
        >
          Suiv.
        </button>
    </div>

  </div>
</template>

<script setup>
import { ChevronLeftIcon, ChevronRightIcon } from '@heroicons/vue/24/solid';

const props = defineProps({
  pagination: {
    type: Object,
    required: true,
    // Structure attendue : { page: 1, per_page: 20, total: 100, total_pages: 5 }
    default: () => ({ page: 1, total_pages: 1, total: 0 })
  }
});

const emit = defineEmits(['page-change']);

const changePage = (newPage) => {
  if (newPage >= 1 && newPage <= props.pagination.total_pages) {
    emit('page-change', newPage);
  }
};
</script>