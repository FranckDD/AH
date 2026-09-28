// src/stores/configStore.js
import { defineStore } from 'pinia';
import { ref } from 'vue';
import api from '@/services/api'; // Import de votre instance Axios configurée

export const useConfigStore = defineStore('config', () => {
    
    // --- STATE ---
    const examens = ref([]);
    const prayerBookTypes = ref([]); 

    // Valeurs de secours (organisation reelle, communiquees 2026-09-28) -
    // utilisees UNIQUEMENT tant qu'aucune reponse de /config/structure n'a
    // encore ete recue (demarrage hors ligne avant toute synchronisation) ni
    // mise en cache localStorage d'un appel precedent (voir
    // readCachedStructureInfo ci-dessous). La source de verite reste la
    // configuration systeme geree par l'admin (SystemConfig.vue) - ces
    // valeurs ne sont PAS codees en dur dans le flux normal, seulement en
    // dernier recours pour que le ticket hors ligne ne soit jamais vide.
    const FALLBACK_STRUCTURE_INFO = {
        id: null,
        name: 'A Hand to Humanity (A.H2)',
        slogan: 'Transforming lives through holistic care.',
        logo_url: null,

        // Coordonnées
        address: '',
        city: '',
        po_box: '',
        phone: '(+237) 678 951 970',
        phone2: '694 682 198',
        email: '',
        website: 'ahandtohumanity-ngo.org',

        // Infos Légales
        niu: '',
        rccm: '',
        legal_info: ''
    };

    const STRUCTURE_INFO_STORAGE_KEY = 'structureInfoCache';

    // Meme motif que readCachedTicketPrintToken/writeCachedTicketPrintToken
    // plus bas : permet a une session hors ligne de reutiliser la derniere
    // configuration reellement recue du backend, plutot que de retomber sur
    // le FALLBACK_STRUCTURE_INFO statique des qu'un admin a deja modifie la
    // config au moins une fois en ligne.
    function readCachedStructureInfo() {
        try {
            const raw = localStorage.getItem(STRUCTURE_INFO_STORAGE_KEY);
            return raw ? { ...FALLBACK_STRUCTURE_INFO, ...JSON.parse(raw) } : { ...FALLBACK_STRUCTURE_INFO };
        } catch (err) {
            console.warn('Lecture localStorage des infos structure impossible:', err);
            return { ...FALLBACK_STRUCTURE_INFO };
        }
    }

    function writeCachedStructureInfo(info) {
        try {
            localStorage.setItem(STRUCTURE_INFO_STORAGE_KEY, JSON.stringify(info));
        } catch (err) {
            console.warn('Ecriture localStorage des infos structure impossible:', err);
        }
    }

    // 🟢 État : Infos de la structure COMPLÈTES
    // Mise à jour pour correspondre aux champs du formulaire "Impression Professionnelle"
    const structureInfo = ref(readCachedStructureInfo());

    const isLoading = ref(false);
    const error = ref(null);

    // null = tout va bien. Une chaine = l'appel a echoue, ce qui n'est PAS
    // la meme chose qu'un etablissement non configure : sans cette
    // distinction, un endpoint casse et une base vide sont indiscernables.
    const structureError = ref(null);

    const TICKET_PRINT_TOKEN_STORAGE_KEY = 'ticketPrintToken';

    // Valeur de secours lue depuis localStorage des la creation du store -
    // permet a une page qui monte hors ligne (secretaire sans reseau au
    // demarrage) d'avoir immediatement le dernier jeton connu, avant meme
    // que fetchTicketPrintToken() ait pu tenter (et echouer) son appel
    // reseau. Lecture protegee (try/catch) : le stockage navigateur peut
    // lever en contexte prive/restreint, jamais bloquant.
    function readCachedTicketPrintToken() {
        try {
            return localStorage.getItem(TICKET_PRINT_TOKEN_STORAGE_KEY) || null;
        } catch (err) {
            console.warn('Lecture localStorage du jeton d\'impression impossible:', err);
            return null;
        }
    }

    function writeCachedTicketPrintToken(token) {
        try {
            if (token) {
                localStorage.setItem(TICKET_PRINT_TOKEN_STORAGE_KEY, token);
            } else {
                localStorage.removeItem(TICKET_PRINT_TOKEN_STORAGE_KEY);
            }
        } catch (err) {
            console.warn('Ecriture localStorage du jeton d\'impression impossible:', err);
        }
    }

    const ticketPrintToken = ref(readCachedTicketPrintToken());

    // Logo monochrome du ticket, mis en cache en base64 (data URI) - permet
    // au ticket construit cote client (secretaire hors ligne, ou en ligne
    // mais pas encore synchronise, voir CaisseList.vue::buildLocalTicketData)
    // d'inclure quand meme le logo. Sans ca, ce chemin ne peut structurellement
    // jamais l'avoir : ticket_logo_path resolu cote backend est un chemin
    // fichier SERVEUR (voir get_ticket_header_context), jamais accessible
    // depuis le navigateur. Meme motif de cache que structureInfo/
    // ticketPrintToken ci-dessus.
    const TICKET_LOGO_STORAGE_KEY = 'ticketLogoDataUriCache';

    function readCachedTicketLogoDataUri() {
        try {
            return localStorage.getItem(TICKET_LOGO_STORAGE_KEY) || null;
        } catch (err) {
            console.warn('Lecture localStorage du logo ticket impossible:', err);
            return null;
        }
    }

    function writeCachedTicketLogoDataUri(dataUri) {
        try {
            if (dataUri) {
                localStorage.setItem(TICKET_LOGO_STORAGE_KEY, dataUri);
            } else {
                localStorage.removeItem(TICKET_LOGO_STORAGE_KEY);
            }
        } catch (err) {
            // Le plus probable : quota localStorage depasse (une image
            // encodee en base64 pese ~33% de plus que le fichier) - jamais
            // bloquant, le ticket local continuera simplement sans logo.
            console.warn('Ecriture localStorage du logo ticket impossible:', err);
        }
    }

    const ticketLogoDataUri = ref(readCachedTicketLogoDataUri());

    // Telecharge l'image du logo depuis /static (public, sans auth - voir
    // main.py) et la convertit en data URI. Best-effort total : un echec ne
    // doit jamais empecher fetchStructureInfo() de faire son travail
    // principal, le ticket local continue de fonctionner sans logo comme
    // avant.
    async function refreshTicketLogoCache(ticketLogoUrl) {
        if (!ticketLogoUrl) {
            return;
        }
        try {
            const response = await api.get(ticketLogoUrl, { responseType: 'blob' });
            const dataUri = await new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.onloadend = () => resolve(reader.result);
                reader.onerror = reject;
                reader.readAsDataURL(response.data);
            });
            ticketLogoDataUri.value = dataUri;
            writeCachedTicketLogoDataUri(dataUri);
        } catch (err) {
            console.warn('Impossible de mettre en cache le logo du ticket:', err);
        }
    }

    async function fetchTicketPrintToken() {
        try {
            const response = await api.get('/config/ticket-print-token');
            ticketPrintToken.value = response.data?.token || null;
            writeCachedTicketPrintToken(ticketPrintToken.value);
        } catch (err) {
            console.error('Echec du chargement du jeton d\'impression:', err);
        }
    }

    async function regenerateTicketPrintToken() {
        const response = await api.post('/config/generate-ticket-token');
        ticketPrintToken.value = response.data.token;
        writeCachedTicketPrintToken(ticketPrintToken.value);
        return ticketPrintToken.value;
    }

    // --- ACTIONS STRUCTURE ---

    // 1. Récupérer les infos structure
    async function fetchStructureInfo() {
        try {
            const response = await api.get('/config/structure');
            structureError.value = null;
            if (response.data) {
                structureInfo.value = { ...structureInfo.value, ...response.data };
                writeCachedStructureInfo(structureInfo.value);
                refreshTicketLogoCache(structureInfo.value.ticket_logo_url);
            }
        } catch (err) {
            structureError.value = "Impossible de charger les informations de l'établissement.";
            console.error('Echec du chargement des infos structure:', err);
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
            writeCachedStructureInfo(structureInfo.value);
            refreshTicketLogoCache(structureInfo.value.ticket_logo_url);
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
            // 🟢 CORRECTION : Ajout de "exams" à l'URL pour correspondre au backend
            const response = await api.get('/labo/exams'); 
            
            examens.value = response.data.map(ex => ({
                ...ex,
                prix: parseFloat(ex.prix)
            }));
        } catch (err) {
            console.error("Erreur fetchExamens:", err);
            error.value = "Impossible de charger les examens.";
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
        structureError,
        ticketPrintToken,
        ticketLogoDataUri,

        // Actions
        fetchExamens,
        saveExamen,
        deleteExamen,
        fetchPrayerBooks,
        fetchStructureInfo,
        saveStructureInfo,
        fetchTicketPrintToken,
        regenerateTicketPrintToken
    };
});