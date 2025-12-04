<template>
  <div class="space-y-6 w-full animate-fade-in">
    
    <div class="flex flex-col lg:flex-row justify-between items-center bg-white p-6 rounded-2xl shadow-sm border border-gray-100 gap-6">
      
      <div class="w-full lg:w-auto text-center lg:text-left">
        <h1 class="text-2xl font-extrabold text-gray-800 tracking-tight flex items-center gap-3 justify-center lg:justify-start">
          <span class="bg-green-100 p-2 rounded-lg text-green-700">
             <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" /></svg>
          </span>
          {{ t('users.title') }}
        </h1>
        <p class="text-sm text-gray-500 mt-1 ml-1">{{ userStore.pagination.total }} utilisateurs enregistrés</p>
      </div>

      <div class="flex flex-col sm:flex-row gap-4 w-full lg:w-auto">
          <div class="relative w-full sm:w-80">
            <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <MagnifyingGlassIcon class="h-5 w-5 text-gray-400" />
            </div>
            <input 
              v-model="searchQuery"
              type="text"
              :placeholder="t('users.search_placeholder')"
              class="block w-full pl-10 pr-3 py-2.5 border border-gray-300 rounded-xl leading-5 bg-gray-50 placeholder-gray-400 focus:outline-none focus:bg-white focus:ring-2 focus:ring-green-500 focus:border-green-500 transition duration-150"
            />
          </div>
          
          <button 
            @click="openAddModal"
            class="w-full sm:w-auto flex items-center justify-center px-6 py-2.5 bg-green-600 text-white rounded-xl hover:bg-green-700 shadow-lg shadow-green-200 transition font-semibold transform hover:-translate-y-0.5"
          >
            <PlusIcon class="h-5 w-5 mr-2" />
            {{ t('users.add_new') }}
          </button>
      </div>
    </div>

    <div class="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
      
      <div v-if="userStore.isLoading" class="p-12 text-center text-gray-500 flex flex-col items-center">
         <div class="animate-spin rounded-full h-10 w-10 border-b-2 border-green-600 mb-3"></div>
         <p class="font-medium">{{ t('common.loading') || 'Chargement des données...' }}</p>
      </div>

      <div v-else class="overflow-x-auto">
        <table class="min-w-full text-left border-collapse">
          <thead>
            <tr class="bg-gray-50/50 text-gray-500 text-xs uppercase tracking-wider border-b border-gray-100">
              <th class="px-6 py-4 font-semibold pl-8">{{ t('users.table.employee') }}</th>
              <th class="px-6 py-4 font-semibold">{{ t('users.table.role') }}</th>
              <th class="px-6 py-4 font-semibold">{{ t('users.table.contact') }}</th>
              <th class="px-6 py-4 font-semibold text-center">{{ t('users.table.status') }}</th>
              <th class="px-6 py-4 font-semibold text-right pr-8">{{ t('users.table.actions') }}</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-for="user in userStore.users" :key="user.id" class="hover:bg-green-50/30 transition duration-150 group">
              
              <td class="px-6 py-4 pl-8">
                <div class="flex items-center">
                  <div class="h-10 w-10 flex-shrink-0 bg-gradient-to-br from-green-100 to-green-200 rounded-full flex items-center justify-center text-green-700 font-bold text-sm shadow-sm">
                    {{ user.firstName.charAt(0) }}{{ user.lastName.charAt(0) }}
                  </div>
                  <div class="ml-4">
                    <div class="text-sm font-bold text-gray-900">{{ user.firstName }} {{ user.lastName }}</div>
                    <div class="text-xs text-gray-500">@{{ user.username }}</div>
                  </div>
                </div>
              </td>

              <td class="px-6 py-4 text-sm">
                <span :class="['px-3 py-1 text-xs font-bold rounded-full border', getRoleColor(user.roleName)]">
                  {{ user.roleName }}
                </span>
                
                <div v-if="user.specialtyName && user.specialtyName !== '-'" class="mt-1.5 flex items-center text-xs text-gray-600">
                   <span class="w-1.5 h-1.5 rounded-full bg-blue-400 mr-1.5"></span>
                   {{ user.specialtyName }}
                </div>
                <div v-else class="text-[10px] text-gray-400 mt-1 uppercase">
                   {{ user.postgres_role }}
                </div>
              </td>

              <td class="px-6 py-4 text-gray-600 text-sm">
                  <div class="flex flex-col">
                    <span class="font-medium text-gray-900">{{ user.email }}</span>
                    <span class="text-xs text-gray-400 mt-0.5">{{ user.phone }}</span>
                  </div>
              </td>

              <td class="px-6 py-4 text-center">
                <span v-if="user.isActive" class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800 border border-green-200">
                  Actif
                </span>
                <span v-else class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600 border border-gray-200">
                  Inactif
                </span>
              </td>

              <td class="px-6 py-4 text-right space-x-2 pr-8">
                <button @click="openEditModal(user)" class="p-2 bg-white border border-gray-200 rounded-lg text-indigo-600 hover:bg-indigo-50 hover:border-indigo-200 transition shadow-sm" :title="t('users.modal.edit_title')">
                  <PencilSquareIcon class="h-4 w-4" />
                </button>
                <button @click="confirmDelete(user)" class="p-2 bg-white border border-gray-200 rounded-lg text-red-500 hover:bg-red-50 hover:border-red-200 transition shadow-sm" :title="t('common.delete')">
                  <TrashIcon class="h-4 w-4" />
                </button>
              </td>
            </tr>
          </tbody>
        </table>

        <div v-if="userStore.users.length === 0 && !userStore.isLoading" class="p-12 text-center">
            <div class="inline-flex items-center justify-center w-16 h-16 rounded-full bg-gray-100 mb-4">
                <MagnifyingGlassIcon class="h-8 w-8 text-gray-400" />
            </div>
            <h3 class="text-lg font-medium text-gray-900">Aucun utilisateur trouvé</h3>
            <p class="mt-1 text-gray-500">Ajoutez un nouvel utilisateur pour commencer.</p>
        </div>
      </div>

      <div v-if="userStore.pagination.total_pages > 1" class="px-6 py-4 flex justify-between items-center border-t border-gray-100 bg-gray-50/50">
        <p class="text-sm text-gray-600">
            Page <span class="font-semibold text-gray-900">{{ userStore.pagination.page }}</span> sur {{ userStore.pagination.total_pages }}
        </p>
        <div class="flex space-x-2">
            <button @click="goToPage(userStore.pagination.page - 1)" :disabled="userStore.pagination.page === 1" class="px-3 py-1.5 border border-gray-300 rounded-lg bg-white text-gray-600 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition shadow-sm">
                <ChevronLeftIcon class="h-4 w-4" />
            </button>
            <button @click="goToPage(userStore.pagination.page + 1)" :disabled="userStore.pagination.page === userStore.pagination.total_pages" class="px-3 py-1.5 border border-gray-300 rounded-lg bg-white text-gray-600 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition shadow-sm">
                <ChevronRightIcon class="h-4 w-4" />
            </button>
        </div>
      </div>

    </div>

    <UserModal 
      v-if="showModal"
      :userToEdit="selectedUser"
      :application-roles="applicationRoles"
      :medical-specialties="medicalSpecialties"
      @close="closeModal"
      @save="handleSaveUser"
    />
    
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useUserStore } from '@/stores/userStore';
import api from '@/services/api'; 
import UserModal from '@/components/users/UserModal.vue'; 
import { useI18n } from 'vue-i18n'; 
import { 
    PlusIcon, PencilSquareIcon, TrashIcon, MagnifyingGlassIcon, ChevronLeftIcon, ChevronRightIcon 
} from '@heroicons/vue/24/outline';

const userStore = useUserStore();
const { t } = useI18n(); 

const showModal = ref(false);
const selectedUser = ref(null);
const applicationRoles = ref([])
const medicalSpecialties = ref([])

onMounted(async () => {
  try {
      // 1. Charger les utilisateurs
      userStore.fetchUsers();

      // 2. Charger les listes de références pour le formulaire
      // (INDISPENSABLE pour que la cascade fonctionne dans le modal)
      const rolesRes = await api.get('/users/roles'); 
      applicationRoles.value = Array.isArray(rolesRes.data) ? rolesRes.data : rolesRes.data.data || rolesRes.data;

      const specsRes = await api.get('/users/specialties');
      medicalSpecialties.value = Array.isArray(specsRes.data) ? specsRes.data : specsRes.data.data || specsRes.data;
      
  } catch (e) {
      console.error("Erreur chargement refs", e);
  }
});

// Computed pour Search
const searchQuery = computed({
    get: () => userStore.filters.search,
    set: (val) => userStore.setFilters({ search: val })
});

const goToPage = (page) => userStore.setPage(page);

// --- COULEURS RÔLES (Mise à jour pour correspondre aux noms de la BD) ---
const getRoleColor = (roleName) => {
    // On met en minuscule pour éviter les erreurs de casse
    const r = (roleName || '').toLowerCase();
    
    // Admin / Direction
    if (r.includes('admin') || r.includes('directeur')) return 'bg-purple-50 text-purple-700 border-purple-200';
    
    // Médical (Docteur)
    if (r.includes('medecin') || r.includes('médecin') || r.includes('doctor')) return 'bg-blue-50 text-blue-700 border-blue-200';
    
    // Soins infirmiers
    if (r.includes('nurse') || r.includes('infirmier')) return 'bg-sky-50 text-sky-700 border-sky-200';
    
    // Secrétariat / Accueil
    if (r.includes('secretaire') || r.includes('secrétaire')) return 'bg-pink-50 text-pink-700 border-pink-200';
    
    // Laboratoire
    if (r.includes('laborantin') || r.includes('bio')) return 'bg-yellow-50 text-yellow-700 border-yellow-200';
    
    // Psy / Toxico
    if (r.includes('psy') || r.includes('toxico')) return 'bg-teal-50 text-teal-700 border-teal-200';

    // Par défaut
    return 'bg-gray-50 text-gray-700 border-gray-200';
}

// --- LOGIQUE CRUD ---
const openAddModal = () => {
    selectedUser.value = null;
    showModal.value = true;
};

const openEditModal = (user) => {
    selectedUser.value = { ...user };
    showModal.value = true;
};

const closeModal = () => {
    showModal.value = false;
    selectedUser.value = null;
};

const handleSaveUser = async (userData) => {
    try {
        if (userData.id) {
            await userStore.updateUser(userData);
        } else {
            await userStore.addUser(userData);
        }
        closeModal();
    } catch(error) {
       // Erreur déjà gérée dans le store
    }
};

const confirmDelete = async (user) => {
    if (confirm(`Voulez-vous vraiment supprimer ${user.firstName} ${user.lastName} ?`)) {
        await userStore.deleteUser(user.id);
    }
};
</script>