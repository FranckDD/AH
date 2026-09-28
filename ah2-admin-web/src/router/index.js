import { createRouter, createWebHistory } from 'vue-router';
import { useAuthStore } from '@/stores/auth'; 

// On garde uniquement les vues critiques en import statique pour que l'app se lance vite
import LoginView from '@/views/LoginView.vue';
import ForbiddenView from '@/views/errors/Forbidden.vue'; 


// 💡 ASTUCE CLEAN CODE : Définir les constantes de rôles ici aussi pour éviter les erreurs
const ROLES = {
  ADMIN: 'admin',
  PROMOTEUR: 'promoteur',
  PSYCHOLOGIST: 'Psychologist',
  SPIRITUAL: 'SpiritualCounsellor',
  TOXICO_MANAGER: 'ToxicoManager',
  ASSISTANT: 'Assistant',
  MEDECIN: 'medecin',
  NURSE: 'nurse',
  SECRETAIRE: 'secretaire'
};

const routes = [
  // --- ROUTES PUBLIQUES ---
  { path: '/login', component: LoginView },
  { path: '/forbidden', component: ForbiddenView }, 
  
  // --- ROUTE PARENT : /dashboard ---
  {
    path: '/dashboard', 
    // On utilise le Lazy Loading pour le Layout aussi
    component: () => import('@/components/layout/MainLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '', 
        // Redirection par défaut (sera interceptée par le login intelligent, mais utile au cas où)
        redirect: '/dashboard/overview' 
      },
      
      // 1. Vue d'ensemble (Admin Principal)
      {
        path: 'overview',
        name: 'dashboard-overview',
        // ✅ CORRECTION : Import Dynamique (Lazy Loading)
        component: () => import('@/views/dashboards/DashboardOverview.vue'),
        meta: {
            requiresAuth: true,
            roles: [ROLES.ADMIN, ROLES.PROMOTEUR] // Admin + promoteur voient le "Grand Dashboard"
        } 
      },
      
      // 2. Dashboard Toxico (Le cœur du métier pour ton équipe)
      {
        path: 'toxico-dashboard',
        name: 'toxico-dashboard',
        component: () => import('@/views/dashboards/ToxicoDashboard.vue'),
        meta: { 
            requiresAuth: true, 
            // Accessible à toute l'équipe soignante
            roles: [ROLES.ADMIN, ROLES.TOXICO_MANAGER, ROLES.PSYCHOLOGIST, ROLES.SPIRITUAL, ROLES.ASSISTANT] 
        }
      },

      // === DÉBUT DU BLOC LABO ===
      {
        path: 'labo',
        component: () => import('@/views/modules/labo/LabLayout.vue'), 
        redirect: { name: 'lab-dashboard' }, 
        
        children: [
            // 0. TABLEAU DE BORD
            {
                path: 'overviewlab',
                name: 'lab-dashboard',
                component: () => import('@/views/dashboards/LabDashboard.vue'),
                meta: { requiresAuth: true, roles: ['admin', 'laborantin', 'ToxicoManager'] }
            },

            // 1. RÉCEPTION
            {
                path: 'reception',
                name: 'lab-reception',
                component: () => import('@/views/modules/labo/LabReception.vue'),
                meta: { requiresAuth: true, roles: ['admin', 'laborantin', 'ToxicoManager', 'Assistant'] }
            },
            
            // 2. PAILLASSE
            {
                path: 'paillasse',
                name: 'lab-technician',
                component: () => import('@/views/modules/labo/LabTechnician.vue'),
                meta: { requiresAuth: true, roles: ['admin', 'laborantin', 'ToxicoManager'] }
            },

            // 3. HISTORIQUE
            {
                path: 'history',
                name: 'lab-history',
                component: () => import('@/views/modules/labo/LabHistory.vue'),
                meta: { requiresAuth: true, roles: ['admin', 'laborantin', 'ToxicoManager'] }
            },

            // 4. CONFIGURATION
            {
                path: 'config',
                name: 'lab-config',
                component: () => import('@/views/modules/labo/LabConfig.vue'),
                meta: { requiresAuth: true, roles: ['admin', 'ToxicoManager'] }
            },
            
            // 5. VALIDATION (ecran historique retire)
            // LabValidation.vue lisait une forme de reponse (`exams`) que le
            // backend ne renvoie jamais : formulaire toujours vide, mais
            // bouton "Valider & Cloturer" actif -> pouvait cloturer un
            // dossier sans aucune valeur. L'URL reste valide (favoris) mais
            // redirige vers la vraie paillasse + saisie (LabTechnician.vue).
            // Le fichier LabValidation.vue est conserve (nettoyage ulterieur).
            {
                path: 'validation/:id?',
                redirect: { name: 'lab-technician' }
            },

            // 6. ECHECS DE SYNCHRONISATION (quarantaine hors ligne)
            // Le laborantin produit des entrees de quarantaine
            // (lab_result / lab_result_detail, chantier 4 sous-projet 5) :
            // il doit pouvoir les consulter depuis son propre espace.
            {
                path: 'sync-failures',
                name: 'lab-sync-failures',
                component: () => import('@/views/modules/sync/SyncFailuresView.vue'),
                meta: { requiresAuth: true, roles: ['admin', 'laborantin', 'ToxicoManager'] }
            }
        ]
      },
      // === FIN DU BLOC LABO ===

      // 3. Suivi Toxicologique (Liste)
      {
        path: 'toxico',
        name: 'toxico',
        component: () => import('@/views/modules/toxico/ToxicoList.vue'),
        meta: { 
            requiresAuth: true, 
            roles: [ROLES.ADMIN, ROLES.TOXICO_MANAGER, ROLES.PSYCHOLOGIST, ROLES.SPIRITUAL, ROLES.ASSISTANT] 
        } 
      },

      // 4. Dossier Patients
      {
        path: 'patients',
        name: 'patients',
        component: () => import('@/views/modules/patients/PatientList.vue'),
        meta: { 
            requiresAuth: true, 
            // Manager uniquement (selon ta demande précédente)
            roles: [ROLES.ADMIN, ROLES.TOXICO_MANAGER] 
        }
      },
      {
        path: 'patients/:id', 
        name: 'PatientDetail', 
        component: () => import('@/views/modules/patients/PatientDetailView.vue'),
        props: true,
        meta: { 
            title: 'Dossier Patient',
            requiresAuth: true,
            roles: [ROLES.ADMIN, ROLES.TOXICO_MANAGER]
        }
      },
      
      // 5. Gestion des Utilisateurs
      {
        path: 'users',
        name: 'users',
        component: () => import('@/views/modules/users/UserManagement.vue'), 
        meta: { 
            requiresAuth: true, 
            roles: [ROLES.ADMIN, ROLES.TOXICO_MANAGER] 
        }, 
      },

      // 6. Gestion du Stock
      {
        path: 'stock',
        name: 'stock',
        component: () => import('@/views/modules/stock/StockList.vue'),
        meta: { 
            requiresAuth: true, 
            roles: [ROLES.ADMIN, ROLES.TOXICO_MANAGER, ROLES.ASSISTANT] 
        }
      },

      // 7. Finance
      {
        path: 'finance',
        name: 'finance',
        component: () => import('@/views/modules/finance/FinancialList.vue'),
        meta: {
            requiresAuth: true,
            roles: [ROLES.ADMIN]
        }
      },

      // 7b. Validation des demandes de remise (anti-fraude caisse)
      {
        path: 'discount-review',
        name: 'discount-review',
        component: () => import('@/views/modules/caisse/DiscountReview.vue'),
        meta: { requiresAuth: true, roles: [ROLES.ADMIN, ROLES.PROMOTEUR] }
      },

      // 7c. Historique + KPI des demandes de remise (lecture seule, ecran separe
      // de discount-review qui reste l'ecran de DECISION admin/promoteur)
      {
        path: 'discount-history',
        name: 'discount-history',
        component: () => import('@/views/modules/caisse/DiscountRequestsHistory.vue'),
        meta: { requiresAuth: true, roles: [ROLES.ADMIN, ROLES.PROMOTEUR] }
      },

      // 8. Configuration & Logs
      {
        path: 'configuration',
        name: 'system-config',
        component: () => import('@/views/SystemConfig.vue'),
        meta: {
            requiresAuth: true,
            roles: [ROLES.ADMIN, ROLES.TOXICO_MANAGER]
        }
      },
      {
        path: 'logs',
        name: 'system-logs',
        component: () => import('@/views/modules/tech/SystemLogs.vue'),
        meta: { 
            requiresAuth: true, 
            roles: [ROLES.ADMIN, ROLES.TOXICO_MANAGER] 
        }
      },
    ]
  },

  // --- ROUTE PARENT : /medical (fenetre medicale independante, medecin+nurse) ---
  {
    path: '/medical',
    component: () => import('@/components/layout/MedicalLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        redirect: '/medical/appointments'
      },
      {
        path: 'appointments',
        name: 'medical-appointments',
        component: () => import('@/views/modules/appointments/AppointmentsList.vue'),
        meta: {
          requiresAuth: true,
          roles: [ROLES.MEDECIN, ROLES.NURSE]
        }
      },
      {
        path: 'prescriptions',
        name: 'medical-prescriptions',
        component: () => import('@/views/modules/prescriptions/PrescriptionsList.vue'),
        meta: {
          requiresAuth: true,
          roles: [ROLES.MEDECIN, ROLES.NURSE]
        }
      },
      {
        path: 'medical-records',
        name: 'medical-medical-records',
        component: () => import('@/views/modules/medical-records/MedicalRecordsList.vue'),
        meta: {
          requiresAuth: true,
          roles: [ROLES.MEDECIN, ROLES.NURSE]
        }
      },
      {
        path: 'patients',
        name: 'medical-patients',
        // Reutilise les memes composants que /dashboard/patients (admin/ToxicoManager) -
        // aucune logique de role codee en dur dans PatientList.vue/PatientDetailView.vue.
        component: () => import('@/views/modules/patients/PatientList.vue'),
        meta: {
          requiresAuth: true,
          roles: [ROLES.MEDECIN, ROLES.NURSE]
        }
      },
      {
        path: 'patients/:id',
        name: 'medical-patient-detail',
        component: () => import('@/views/modules/patients/PatientDetailView.vue'),
        props: true,
        meta: {
          requiresAuth: true,
          roles: [ROLES.MEDECIN, ROLES.NURSE]
        }
      },
      {
        path: 'sync-failures',
        name: 'medical-sync-failures',
        component: () => import('@/views/modules/sync/SyncFailuresView.vue'),
        meta: {
          requiresAuth: true,
          roles: [ROLES.MEDECIN, ROLES.NURSE]
        }
      },
      {
        path: 'doctors',
        name: 'medical-doctors',
        component: () => import('@/views/modules/doctors/DoctorKpiView.vue'),
        meta: {
          requiresAuth: true,
          roles: [ROLES.MEDECIN, ROLES.NURSE]
        }
      },
      {
        path: 'lab-results',
        name: 'medical-lab-results',
        component: () => import('@/views/modules/labo/MedicalLabResults.vue'),
        meta: {
          requiresAuth: true,
          roles: [ROLES.MEDECIN, ROLES.NURSE]
        }
      }
    ]
  },

  // --- ROUTE PARENT : /secretariat (fenetre secretariat independante) ---
  {
    path: '/secretariat',
    component: () => import('@/components/layout/SecretaireLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        name: 'secretariat-home',
        component: () => import('@/views/modules/secretariat/SecretariatHomeView.vue'),
        meta: {
          requiresAuth: true,
          roles: [ROLES.SECRETAIRE]
        }
      },
      {
        path: 'patients',
        name: 'secretariat-patients',
        component: () => import('@/views/modules/patients/PatientList.vue'),
        props: { disableDetailLink: true },
        meta: {
          requiresAuth: true,
          roles: [ROLES.SECRETAIRE]
        }
      },
      {
        path: 'stock',
        name: 'secretariat-stock',
        component: () => import('@/views/modules/stock/StockList.vue'),
        meta: {
          requiresAuth: true,
          roles: [ROLES.SECRETAIRE]
        }
      },
      {
        path: 'caisse',
        name: 'secretariat-caisse',
        component: () => import('@/views/modules/finance/CaisseList.vue'),
        meta: {
          requiresAuth: true,
          roles: [ROLES.SECRETAIRE]
        }
      },
      {
        path: 'retrait',
        name: 'secretariat-retrait',
        component: () => import('@/views/modules/finance/RetraitList.vue'),
        meta: {
          requiresAuth: true,
          roles: [ROLES.SECRETAIRE]
        }
      },
      {
        path: 'consultations',
        name: 'secretariat-consultations',
        component: () => import('@/views/modules/consultations/ConsultationsList.vue'),
        meta: {
          requiresAuth: true,
          roles: [ROLES.SECRETAIRE]
        }
      },
      {
        path: 'sync-failures',
        name: 'secretariat-sync-failures',
        component: () => import('@/views/modules/sync/SyncFailuresView.vue'),
        meta: {
          requiresAuth: true,
          roles: [ROLES.SECRETAIRE]
        }
      },
      {
        path: 'discount-history',
        name: 'secretariat-discount-history',
        component: () => import('@/views/modules/caisse/DiscountRequestsHistory.vue'),
        meta: {
          requiresAuth: true,
          roles: [ROLES.SECRETAIRE]
        }
      },
    ]
  },

  // Routes de secours
  { path: '/', redirect: '/dashboard' },
  { path: '/:pathMatch(.*)*', redirect: '/dashboard' }
];

const router = createRouter({
  history: createWebHistory(),
  routes
});

// Apres un nouveau deploiement, les chunks de route (lazy-loading) changent de
// nom hashe et les anciens disparaissent du serveur. Un onglet reste ouvert
// avec l'ancien index.html (servi par le Service Worker depuis son cache)
// demande alors des fichiers qui n'existent plus : chaque navigation vers une
// vue lazy echoue en 404 et l'ecran ne s'affiche jamais. Recharger la page
// force la recuperation de l'index.html a jour, donc des bons noms de chunks.
// La garde sessionStorage evite toute boucle de rechargement si le 404 vient
// d'autre chose qu'un build perime.
const RELOAD_FLAG = 'ah2-chunk-reload';
router.onError((error, to) => {
  const isStaleChunk = /Failed to fetch dynamically imported module|Importing a module script failed/i.test(
    error?.message || ''
  );
  if (!isStaleChunk) {
    return;
  }
  if (sessionStorage.getItem(RELOAD_FLAG)) {
    console.error('Chunk introuvable apres rechargement - build incoherent cote serveur.', error);
    return;
  }
  sessionStorage.setItem(RELOAD_FLAG, '1');
  window.location.assign(to.fullPath);
});

router.afterEach(() => {
  sessionStorage.removeItem(RELOAD_FLAG);
});

// ------------------------------------------------
// 🛡️ GARDE DE NAVIGATION (Sécurité)
// ------------------------------------------------

router.beforeEach((to, from, next) => {
  const authStore = useAuthStore();
  
  // Force la récupération du statut (parfois Pinia n'est pas prêt à la microseconde près)
  const isAuthenticated = authStore.token && authStore.user; 
  const requiresAuth = to.matched.some(record => record.meta.requiresAuth);
  
  // 1. Vérification Authentification
  if (requiresAuth && !isAuthenticated) {
      return next('/login');
  }
  
  // Si on est déjà connecté et qu'on tente d'aller au login -> redirection intelligente
  if (to.path === '/login' && isAuthenticated) {
      return next('/dashboard');
  }

  // 2. Vérification Autorisation (RBAC)
  if (to.meta.roles && isAuthenticated) {
    const requiredRoles = to.meta.roles; 
    const userRole = authStore.userRole; 

    // Comparaison insensible à la casse : userRole vient de l'API (casse DB),
    // requiredRoles est ecrit a la main dans les meta de route.
    const normalizedUserRole = (userRole || '').toLowerCase();
    const normalizedRequired = requiredRoles.map((r) => r.toLowerCase());

    // Si le rôle de l'utilisateur N'EST PAS dans la liste autorisée
    if (!normalizedRequired.includes(normalizedUserRole)) {
      // Cas spécial : L'Admin a accès à tout, même si pas listé explicitement (Super User)
      if (normalizedUserRole === ROLES.ADMIN.toLowerCase()) {
          return next();
      }

      // Évite la boucle infinie si on est déjà sur forbidden
      if (to.path !== '/forbidden') {
        console.warn(`⛔ Accès refusé. Rôle: ${userRole} -> Vers: ${to.path}`);
        return next('/forbidden'); 
      }
    }
  }

  next();
});

export default router;