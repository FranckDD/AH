// src/router/index.js

import { createRouter, createWebHistory } from 'vue-router';
import { useAuthStore } from '@/stores/auth'; 

// Vues de Base
import LoginView from '@/views/LoginView.vue';
import MainLayout from '@/components/layout/MainLayout.vue';
import ForbiddenView from '@/views/errors/Forbidden.vue'; 

// Vues Modules (Importations mises à jour)
import DashboardOverview from '@/views/dashboards/DashboardOverview.vue';
import PatientList from '@/views/modules/patients/PatientList.vue'; 
import FinancialList from '@/views/modules/finance/FinancialList.vue';
import UserManagement from '@/views/modules/users/UserManagement.vue'; 
import ToxicoList from '@/views/modules/toxico/ToxicoList.vue'; // 🟢 NOUVEL IMPORT
import ToxicoDashboard from '@/views/dashboards/ToxicoDashboard.vue';
import SystemConfig from '@/views/SystemConfig.vue';
import SystemLogs from '@/views/modules/tech/SystemLogs.vue';
import StockList from '@/views/modules/stock/StockList.vue';


const routes = [
  // Route de connexion et Forbidden
  { path: '/login', component: LoginView },
  { path: '/forbidden', component: ForbiddenView }, 
  
  // 1. 🟢 ROUTE PARENT : /dashboard
  {
    path: '/dashboard', 
    component: MainLayout,
    meta: { requiresAuth: true },
    children: [
      {
        path: '', 
        redirect: '/dashboard/overview' 
      },
      
      // 1. Vue d'ensemble (Dashboard Holistique)
      {
        path: 'overview',
        name: 'dashboard-overview',
        component: DashboardOverview,
        // RÔLES BDD: ADMIN, MEDECIN (pour la prise de décision)
        meta: { requiresAuth: true, roles: ['admin', 'medecin','manager'] } 
      },
      
      // 2. Gestion des Utilisateurs
      {
        path: 'users',
        name: 'users',
        component: UserManagement, 
        // RÔLES BDD: ADMIN SEUL
        meta: { requiresAuth: true, roles: ['admin','manager'] }, 
      },
      
      // 3. Gestion des Patients
      {
        path: 'patients',
        name: 'patients',
        component: PatientList,
        // RÔLES BDD: SOIGNANTS + SECRETAIRE
        meta: { requiresAuth: true, roles: ['admin', 'medecin', 'nurse', 'secretaire','manager'] }
      },

      {
        // Le ":id" est crucial, c'est lui qui récupère le "80" ou "79" de votre erreur
        path: '/patients/:id', 
        name: 'PatientDetail', 
        // Assurez-vous que le chemin vers le fichier est correct
        component: () => import('@/views/modules/patients/PatientDetailView.vue'),
        props: true, // Permet de passer l'ID comme une prop au composant
        meta: { title: 'Dossier Patient' }
      },
      
      // 4. Gestion Financière
      {
        path: 'finance',
        name: 'finance',
        component: FinancialList,
        // RÔLES BDD: FINANCE
        meta: { requiresAuth: true, roles: ['admin'] } // Utilisons 'Assistant' pour la caisse
      },

      // 5. 🟢 Gestion Toxicologique
      {
        path: 'toxico',
        name: 'toxico',
        component: ToxicoList,
        // RÔLES BDD: MANAGER TOXICO + PSYCHOLOGUE
        meta: { requiresAuth: true, roles: ['admin', 'ToxicoManager', 'Psychologist','manager'] } 
      },
      {
        path: 'toxico-dashboard',
        name: 'toxico-dashboard',
        component: ToxicoDashboard,
        meta: { requiresAuth: true, roles: ['admin', 'ToxicoManager','manager'] }
    },
    {
        path: 'configuration',
        name: 'system-config',
        component: SystemConfig,
        meta: { requiresAuth: true, roles: ['admin', 'manager'] }
    },
    {
        path: 'logs',
        name: 'system-logs',
        component: SystemLogs,
        meta: { requiresAuth: true, roles: ['admin', 'Admin Système'] }
    },
    {
        path: 'stock',
        name: 'stock',
        component: StockList,
        meta: { requiresAuth: true, roles: ['admin', 'manager'] }
    },
      
    ]
  },
  
  // 2. Redirection de la racine (/)
  {
    path: '/',
    redirect: '/dashboard'
  },
  
  // 3. Route Catch-all 404
  { path: '/:pathMatch(.*)*', redirect: '/dashboard' }
];

const router = createRouter({
  history: createWebHistory(),
  routes
});



// ------------------------------------------------
// 🛡️ GARDE DE NAVIGATION (Laissé intact car il est correct)
// ------------------------------------------------

router.beforeEach((to, from, next) => {
  const authStore = useAuthStore();
  const isAuthenticated = authStore.isAuthenticated;
  const requiresAuth = to.matched.some(record => record.meta.requiresAuth);
  
  // 1. Authentification
  if (requiresAuth && !isAuthenticated) return next('/login');
  if (to.path === '/login' && isAuthenticated) return next('/');

  // 2. Autorisation (RBAC)
  if (to.meta.roles && isAuthenticated) {
    const requiredRoles = to.meta.roles; 
    const userRole = authStore.userRole; 

    if (!requiredRoles.includes(userRole)) {
      if (to.path !== '/forbidden') {
        console.warn(`Accès refusé pour ${userRole} vers ${to.path}`);
        return next('/forbidden'); 
      }
    }
  }

  next();
});

export default router;