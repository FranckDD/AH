// src/stores/configStore.js
import { defineStore } from 'pinia';
import { ref } from 'vue';
import api from '@/services/api'; // Import de votre instance Axios configurée

export const useConfigStore = defineStore('config', () => {
    
    // --- STATE ---
    const examens = ref([]);
    const prayerBookTypes = ref([]); 

    // 🟢 NOUVEL ÉTAT : Infos de la structure COMPLÈTES
    // Mise à jour pour correspondre aux champs du formulaire "Impression Professionnelle"
    const structureInfo = ref({
        id: null,
        name: 'AH2 DASHBOARD', 
        slogan: '',
        logo_url: null,       
        
        // Coordonnées
        address: '',
        city: '',       // Nouveau : Ville
        po_box: '',     // Nouveau : Boite Postale
        phone: '',
        phone2: '',     // Nouveau : Téléphone secondaire
        email: '',
        website: '',    // Nouveau : Site Web
        
        // Infos Légales
        niu: '',        // Nouveau : Numéro Identifiant Unique
        rccm: '',       // Nouveau : Registre de Commerce
        legal_info: ''  // On garde pour compatibilité ou infos supplémentaires
    });

    const isLoading = ref(false);
    const error = ref(null);

    // --- ACTIONS STRUCTURE ---

    // 1. Récupérer les infos structure
    async function fetchStructureInfo() {
        try {
            const response = await api.get('/config/structure');
            if (response.data) {
                // On fusionne avec les valeurs par défaut pour éviter les null sur les nouveaux champs
                structureInfo.value = { ...structureInfo.value, ...response.data };
            }
        } catch (err) {
            console.warn("Info structure non chargées, utilisation défaut.");
        }
    }

    // 2. Sauvegarder les infos (Avec gestion de fichier pour le logo)
    async function saveStructureInfo(formData) {
        isLoading.value = true;
        try {
            // Le backend devra gérer le multipart/form-data
            // Note: Vérifiez si votre backend attend un POST ou un PUT pour la mise à jour
            const response = await api.post('/config/structure', formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            });
            
            // Mise à jour immédiate avec la réponse du serveur
            structureInfo.value = response.data; 
        } catch (err) {
            console.error("Erreur saveStructureInfo:", err);
            throw err;
        } finally {
            isLoading.value = false;
        }
    }

    // --- ACTIONS EXAMENS (Inchangé) ---

    // 1. Récupérer la liste des examens
    async function fetchExamens() {
        isLoading.value = true;
        error.value = null;
        try {
            const response = await api.get('/labo/');
            
            // Conversion prix string -> float
            examens.value = response.data.map(ex => ({
                ...ex,
                prix: parseFloat(ex.prix)
            }));
        } catch (err) {
            console.error("Erreur fetchExamens:", err);
            error.value = "Impossible de charger la configuration des examens.";
        } finally {
            isLoading.value = false;
        }
    }

    // 2. Créer ou Mettre à jour un examen
    async function saveExamen(examen) {
        isLoading.value = true;
        error.value = null;
        try {
            const payload = {
                code: examen.code,
                nom: examen.nom,
                categorie: examen.categorie,
                prix: parseFloat(examen.prix)
            };

            if (examen.id) {
                // MISE À JOUR (PUT)
                await api.put(`/labo/exams/${examen.id}`, payload);
            } else {
                // CRÉATION (POST)
                await api.post('/labo/exams', payload);
            }

            // Rafraîchir la liste
            await fetchExamens();

        } catch (err) {
            console.error("Erreur saveExamen:", err);
            throw new Error(err.response?.data?.detail || "Erreur lors de la sauvegarde.");
        } finally {
            isLoading.value = false;
        }
    }

    // 3. Supprimer un examen
    async function deleteExamen(id) {
        // La confirmation est gérée dans la Vue maintenant, on exécute direct
        isLoading.value = true;
        try {
            await api.delete(`/labo/exams/${id}`);
            examens.value = examens.value.filter(e => e.id !== id);
        } catch (err) {
            console.error("Erreur deleteExamen:", err);
            alert("Erreur suppression: " + (err.response?.data?.detail || err.message));
        } finally {
            isLoading.value = false;
        }
    }

    // --- ACTIONS PRIERES (Inchangé) ---
    const mockPrayerBooks = [
        { type_code: 'CHR', label: 'Chrétien' },
        { type_code: 'MUS', label: 'Musulman' },
        { type_code: 'AUT', label: 'Autre / Général' },
    ];
    async function fetchPrayerBooks() {
        // Ici on pourrait appeler une API réelle si besoin
        prayerBookTypes.value = mockPrayerBooks;
    }

    return { 
        // State
        examens, 
        prayerBookTypes, 
        structureInfo,
        isLoading, 
        error,
        
        // Actions
        fetchExamens, 
        saveExamen,
        deleteExamen, 
        fetchPrayerBooks,
        fetchStructureInfo, 
        saveStructureInfo
    };
});