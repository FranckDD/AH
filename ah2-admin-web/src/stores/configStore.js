// src/stores/configStore.js
import { defineStore } from 'pinia';
import { ref } from 'vue';

// Mocks des données (simulent ce qui vient de la DB)
const mockExamens = [
    { id: 1, code: 'BH', nom: 'Bilan Hépatique', categorie: 'Biochimie', prix: 15000.00 },
    { id: 2, code: 'NFS', nom: 'Numération Formule Sanguine', categorie: 'Hématologie', prix: 8500.00 },
    { id: 3, code: 'ECBU', nom: 'Examen Cytobactériologique Urines', categorie: 'Microbiologie', prix: 5000.00 },
];

const mockPrayerBooks = [
    { type_code: 'CHR', label: 'Chrétien' },
    { type_code: 'MUS', label: 'Musulman' },
    { type_code: 'AUT', label: 'Autre / Général' },
];

const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));

export const useConfigStore = defineStore('config', () => {
    const examens = ref([]);
    const prayerBookTypes = ref([]);
    const isLoading = ref(false);

    // 🔬 Gestion des Examens
    async function fetchExamens() {
        isLoading.value = true;
        await delay(300);
        examens.value = JSON.parse(JSON.stringify(mockExamens));
        isLoading.value = false;
    }

    async function saveExamen(examen) {
        isLoading.value = true;
        await delay(500);

        if (examen.id) {
            // Mise à jour (Simulée)
            const index = examens.value.findIndex(e => e.id === examen.id);
            if (index !== -1) {
                examens.value[index] = { ...examen, prix: parseFloat(examen.prix) };
            }
        } else {
            // Ajout (Simulé)
            const newExamen = { 
                ...examen, 
                id: Date.now(), 
                prix: parseFloat(examen.prix) 
            };
            examens.value.unshift(newExamen);
        }
        isLoading.value = false;
    }

    // 🙏 Gestion des Livres de Prières
    async function fetchPrayerBooks() {
        isLoading.value = true;
        await delay(300);
        prayerBookTypes.value = JSON.parse(JSON.stringify(mockPrayerBooks));
        isLoading.value = false;
    }

    // NOTE: Nous n'implémentons pas savePrayerBook pour l'instant, 
    // car le focus est sur le dashboard. Nous pouvons l'ajouter si besoin.

    return { 
        examens, 
        prayerBookTypes, 
        isLoading, 
        fetchExamens, 
        saveExamen,
        fetchPrayerBooks
    };
});