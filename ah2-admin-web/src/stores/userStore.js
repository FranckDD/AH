import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import api from '@/services/api';

export const useUserStore = defineStore('user', () => {
    
    const userData = ref({
        data: [],
        total: 0,
        page: 1,
        per_page: 50,
        total_pages: 1
    });
    
    const isLoading = ref(false);
    const error = ref(null);
    const filters = ref({ search: '', page: 1, per_page: 50 });

    // --- ACTIONS ---

    async function fetchUsers() {
        isLoading.value = true;
        error.value = null;

        try {
            const params = {
                page: filters.value.page,
                per_page: filters.value.per_page,
            };
            if (filters.value.search) params.search = filters.value.search;

            const response = await api.get('/users/', { params });
            
            // Gestion flexible de la réponse (liste directe ou objet paginé)
            const rawUsers = Array.isArray(response.data) ? response.data : (response.data.data || []);
            const totalCount = response.data.total || rawUsers.length; // Si pas de total renvoyé, on prend la longueur

            // MAPPING Backend -> Frontend
            const mappedUsers = rawUsers.map(u => {
                const names = (u.full_name || '').split(' ');
                const lastName = names.pop() || '';
                const firstName = names.join(' ');

                // Récupération sécurisée des objets liés
                const roleObj = u.application_role || {}; 
                const specObj = u.medical_speciality || {};

                return {
                    id: u.user_id,
                    firstName,
                    lastName,
                    username: u.username,
                    email: u.email,
                    phone: u.contact || '',
                    
                    // Pour l'affichage dans le tableau
                    roleName: roleObj.role_name || u.postgres_role || 'N/A',
                    specialtyName: specObj.name || '-',

                    // Pour le formulaire d'édition (IDs)
                    postgres_role: u.postgres_role,
                    role_id: u.role_id, 
                    specialty_id: u.specialty_id, 
                    
                    isActive: u.is_active,
                    originalData: u 
                };
            });

            userData.value.data = mappedUsers;
            userData.value.total = totalCount;
            userData.value.page = filters.value.page;
            userData.value.per_page = filters.value.per_page;
            userData.value.total_pages = Math.ceil(totalCount / filters.value.per_page) || 1;

        } catch (err) {
            console.error("Erreur chargement utilisateurs:", err);
            error.value = "Impossible de charger les utilisateurs.";
        } finally {
            isLoading.value = false;
        }
    }

    function setPage(newPage) {
        filters.value.page = newPage;
        fetchUsers();
    }

    function setFilters(newFilters) {
        filters.value = { ...filters.value, ...newFilters, page: 1 };
        fetchUsers();
    }

    // --- CRUD ---

    async function addUser(formData) {
        isLoading.value = true;
        try {
            // Mapping pour le Backend (Snake case)
            const payload = {
                username: formData.username || formData.email,
                password: formData.password || "123456", // MDP par défaut si admin crée
                full_name: `${formData.firstName} ${formData.lastName}`.trim(),
                email: formData.email,
                contact: formData.phone,
                
                postgres_role: formData.postgres_role,
                role_id: formData.role_id, 
                specialty_id: formData.specialty_id, // Peut être null
                
                is_active: formData.is_active
            };

            await api.post('/users/', payload);
            await fetchUsers(); // Recharger la liste
        } catch (err) {
            console.error("Erreur création:", err);
            throw err;
        } finally {
            isLoading.value = false;
        }
    }

    async function updateUser(formData) {
        isLoading.value = true;
        try {
            const payload = {
                full_name: `${formData.firstName} ${formData.lastName}`.trim(),
                email: formData.email,
                contact: formData.phone,
                postgres_role: formData.postgres_role,
                role_id: formData.role_id,
                specialty_id: formData.specialty_id,
                is_active: formData.is_active
            };
            
            // On n'envoie le mot de passe que s'il est renseigné
            if (formData.password && formData.password.trim() !== '') {
                payload.password = formData.password;
            }

            await api.put(`/users/${formData.id}`, payload);
            await fetchUsers();
        } catch (err) {
            console.error("Erreur mise à jour:", err);
            throw err;
        } finally {
            isLoading.value = false;
        }
    }

    async function deleteUser(id) {
        isLoading.value = true;
        try {
            await api.delete(`/users/${id}`);
            // Optimistic UI update
            userData.value.data = userData.value.data.filter(u => u.id !== id);
            userData.value.total--;
        } catch (err) {
            console.error("Erreur suppression:", err);
            throw err;
        } finally {
            isLoading.value = false;
        }
    }

    return { 
        users: computed(() => userData.value.data),
        pagination: computed(() => ({
            page: userData.value.page,
            per_page: userData.value.per_page,
            total: userData.value.total,
            total_pages: userData.value.total_pages
        })),
        isLoading, error, filters,
        fetchUsers, addUser, updateUser, deleteUser, setPage, setFilters
    };
});