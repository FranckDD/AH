<template>
  <div class="grid w-full gap-6">

    <PageHeader :title="t('users.title')" :subtitle="t('usersScreens.count', { n: userStore.pagination.total })">
      <template #actions>
        <AppButton :icon="PlusIcon" @click="openAddModal">{{ t('users.add_new') }}</AppButton>
      </template>
    </PageHeader>

    <section :aria-label="t('usersScreens.search_label')" class="rounded-card border border-tone-neutral-border bg-white p-4 shadow-card">
      <div class="max-w-xl">
        <FormField id="user-search" :label="t('usersScreens.search_label')" v-slot="{ describedBy }">
          <input id="user-search" v-model="searchQuery" type="search" autocomplete="off"
                 :placeholder="t('users.search_placeholder')" :aria-describedby="describedBy" :class="fieldClass" />
        </FormField>
      </div>
    </section>

    <section class="grid gap-3">
      <ResponsiveTable
        :columns="columns"
        :rows="userStore.users"
        row-key="id"
        :loading="userStore.isLoading"
        :empty-title="t('usersScreens.empty')"
        :empty-message="t('usersScreens.empty_help')"
        striped
      >
        <template #cell-employee="{ row: user }">
          <div class="flex items-center gap-3">
            <span class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-brand-100 bg-brand-50 text-base font-bold text-brand-700" aria-hidden="true">
              {{ user.firstName.charAt(0) }}{{ user.lastName.charAt(0) }}
            </span>
            <span class="min-w-0">
              <span class="block font-bold text-ink">{{ user.firstName }} {{ user.lastName }}</span>
              <span class="block text-sm text-ink-muted">@{{ user.username }}</span>
            </span>
          </div>
        </template>

        <template #cell-role="{ row: user }">
          <StatusBadge :tone="getRoleColor(user.roleName)" :label="String(user.roleName ?? '-')" />
          <p v-if="user.specialtyName && user.specialtyName !== '-'" class="mt-1.5 text-sm text-ink-muted">{{ user.specialtyName }}</p>
          <p v-else class="mt-1.5 text-sm uppercase text-ink-muted">{{ user.postgres_role }}</p>
        </template>

        <template #cell-contact="{ row: user }">
          <span class="block font-medium text-ink">{{ user.email }}</span>
          <span class="block text-sm text-ink-muted">{{ user.phone }}</span>
        </template>

        <template #cell-status="{ row: user }">
          <StatusBadge v-if="user.isActive" tone="success" :label="t('usersScreens.active')" />
          <StatusBadge v-else tone="neutral" :label="t('usersScreens.inactive')" />
        </template>

        <template #actions="{ row: user }">
          <AppButton variant="secondary" :icon="PencilSquareIcon" :title="t('users.modal.edit_title')" @click="openEditModal(user)">
            <span class="lg:sr-only">{{ t('usersScreens.edit') }}</span>
          </AppButton>
          <AppButton variant="danger" :icon="TrashIcon" :title="t('common.delete')" @click="confirmDelete(user)">
            <span class="lg:sr-only">{{ t('usersScreens.delete_user') }}</span>
          </AppButton>
        </template>
      </ResponsiveTable>

      <div v-if="userStore.pagination.total_pages > 1" class="flex items-center justify-between gap-3 rounded-card border border-tone-neutral-border bg-white p-3">
        <p class="text-base text-ink">{{ t('usersScreens.page_label', { n: userStore.pagination.page, total: userStore.pagination.total_pages }) }}</p>
        <div class="flex gap-2">
          <AppButton variant="secondary" :icon="ChevronLeftIcon" :aria-label="t('usersScreens.prev_page')" @click="goToPage(userStore.pagination.page - 1)" :disabled="userStore.pagination.page === 1" />
          <AppButton variant="secondary" :icon="ChevronRightIcon" :aria-label="t('usersScreens.next_page')" @click="goToPage(userStore.pagination.page + 1)" :disabled="userStore.pagination.page === userStore.pagination.total_pages" />
        </div>
      </div>
    </section>

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
import { AppButton, PageHeader, FormField, StatusBadge, ResponsiveTable } from '@/components/ui';
import { 
    PlusIcon, PencilSquareIcon, TrashIcon, MagnifyingGlassIcon, ChevronLeftIcon, ChevronRightIcon 
} from '@heroicons/vue/24/outline';

const userStore = useUserStore();
const { t } = useI18n();

// Colonnes du tableau (cartes empilees sous lg) et style commun des champs.
const columns = computed(() => [
  { key: 'employee', label: t('users.table.employee') },
  { key: 'role', label: t('users.table.role') },
  { key: 'contact', label: t('users.table.contact') },
  { key: 'status', label: t('users.table.status') },
]);
const fieldClass = 'block w-full min-h-11 lg:min-h-10 rounded-control border border-tone-neutral-border bg-white px-3 text-base text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600';

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
    if (r.includes('admin') || r.includes('directeur')) return 'info';
    
    // Médical (Docteur)
    if (r.includes('medecin') || r.includes('médecin') || r.includes('doctor')) return 'success';
    
    // Soins infirmiers
    if (r.includes('nurse') || r.includes('infirmier')) return 'success';
    
    // Secrétariat / Accueil
    if (r.includes('secretaire') || r.includes('secrétaire')) return 'warning';
    
    // Laboratoire
    if (r.includes('laborantin') || r.includes('bio')) return 'warning';
    
    // Psy / Toxico
    if (r.includes('psy') || r.includes('toxico')) return 'neutral';

    // Par défaut
    return 'neutral';
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