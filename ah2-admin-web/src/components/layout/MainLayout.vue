<template>
  <AppShell
    :menu-groups="menuGroups"
    :bell-roles="['admin', 'promoteur', 'secretaire', 'Assistant', 'StockController', 'laborantin', 'ToxicoManager']"
    brand-fallback="AH2 Dashboard"
    sidebar-id="dashboard-sidebar"
    :palette="paletteForRole(authStore.userRole)"
  />
</template>

<script setup>
// Cadre partage de l'admin, du promoteur, du laboratoire, de la toxicologie et du stock-control : ce fichier ne
// garde que la configuration (entrees de menu et roles) ; tout le gabarit (menu, barre du haut, tiroir, compte,
// langue, deconnexion, cloche) vit dans AppShell.vue. La couleur du menu depend du role (design/navPalettes.js).
import { onMounted, computed } from 'vue';
import { buildMenu, toShellGroups } from '@/utils/sidebarMenu';
import { paletteForRole } from '@/design/navPalettes';
import { useAuthStore } from '@/stores/auth';
import { useConfigStore } from '@/stores/configStore';
import AppShell from '@/components/layout/AppShell.vue';

import {
  HomeIcon, UsersIcon, ClipboardDocumentListIcon, BanknotesIcon,
  BeakerIcon, ChartBarIcon, CogIcon, ShieldCheckIcon, CubeIcon,
  ExclamationCircleIcon,
  CheckBadgeIcon, ClockIcon, ReceiptPercentIcon,
  ClipboardDocumentCheckIcon, ArrowsRightLeftIcon, AdjustmentsHorizontalIcon,
  ShoppingCartIcon
} from '@heroicons/vue/24/outline';

const authStore = useAuthStore();
const configStore = useConfigStore();

// --- 1. DÉFINITION DES RÔLES (Constantes) ---
const ROLES = {
  ADMIN: 'admin',
  PSYCHOLOGIST: 'Psychologist',
  SPIRITUAL: 'SpiritualCounsellor',
  TOXICO_MANAGER: 'ToxicoManager',
  ASSISTANT: 'Assistant',
  LABORANTIN: 'laborantin', // ✅ Ajout du rôle laborantin
  PROMOTEUR: 'promoteur',
  STOCK_CONTROLLER: 'StockController',
  PRODUCTION_MANAGER: 'ProductionManager'
};

// --- 2. STRUCTURE DU MENU (Data Driven) ---
const menuItems = [
  {
    path: '/dashboard/overview',
    labelKey: 'common.dashboard',
    icon: HomeIcon,
    roles: [ROLES.ADMIN] 
  },
  {
    path: '/dashboard/toxico-dashboard',
    labelKey: 'toxico.dashboard.title',
    icon: ChartBarIcon,
    roles: [ROLES.PSYCHOLOGIST, ROLES.SPIRITUAL, ROLES.TOXICO_MANAGER, ROLES.ASSISTANT]
  },
  {
    path: '/dashboard/toxico',
    labelKey: 'toxico.title',
    icon: ExclamationCircleIcon, // 🔄 Changement d'icône pour éviter doublon avec Labo
    // promoteur (2026-10-22) : lecture + validation de sortie uniquement
    roles: [ROLES.PSYCHOLOGIST, ROLES.SPIRITUAL, ROLES.TOXICO_MANAGER, ROLES.ASSISTANT, ROLES.PROMOTEUR]
  },
  // 🟢 AJOUT MODULE LABORATOIRE 🟢
  {
    path: '/dashboard/labo', // Pointe vers le layout ou la page par défaut du labo
    labelKey: 'lab.title',
    icon: BeakerIcon,        // L'icône "Tube à essai" convient parfaitement ici
    // Visible pour : Laborantin et ToxicoManager (en plus de l'Admin implicite)
    roles: [ROLES.LABORANTIN, ROLES.TOXICO_MANAGER]
  },
  {
    path: '/dashboard/finance',
    labelKey: 'finance.title',
    icon: BanknotesIcon,
    roles: [ROLES.ADMIN]
  },
  {
    path: '/dashboard/discount-review',
    labelKey: 'discount_review.title',
    icon: CheckBadgeIcon,
    roles: [ROLES.ADMIN, ROLES.PROMOTEUR]
  },
  {
    path: '/dashboard/discount-history',
    labelKey: 'discount_history.title',
    icon: ClockIcon,
    roles: [ROLES.ADMIN, ROLES.PROMOTEUR]
  },
  {
    path: '/dashboard/reductions-personnel',
    labelKey: 'staffDiscount.title',
    icon: ReceiptPercentIcon,
    roles: [ROLES.ADMIN, ROLES.PROMOTEUR]
  },
  {
    path: '/dashboard/users',
    labelKey: 'common.users',
    icon: UsersIcon,
    roles: [ROLES.TOXICO_MANAGER]
  },
  {
    path: '/dashboard/patients',
    labelKey: 'patients.title',
    icon: ClipboardDocumentListIcon,
    roles: [ROLES.TOXICO_MANAGER]
  },
  {
    path: '/dashboard/stock',
    group: 'stock',
    labelKey: 'stock.title',
    icon: CubeIcon,
    roles: [ROLES.TOXICO_MANAGER, ROLES.ASSISTANT]
  },
  {
    path: '/dashboard/stock-lots',
    group: 'stock',
    adminHidden: true,
    labelKey: 'stockOps.menu_lots',
    icon: BeakerIcon,
    roles: [ROLES.ADMIN, ROLES.ASSISTANT]
  },
  {
    path: '/dashboard/stock-receipts',
    group: 'stock',
    adminHidden: true,
    labelKey: 'stockOps.menu_receipts',
    icon: ClipboardDocumentListIcon,
    roles: [ROLES.ADMIN, ROLES.ASSISTANT]
  },
  {
    path: '/dashboard/stock-incidents',
    group: 'stock',
    adminHidden: true,
    labelKey: 'stockOps.menu_incidents',
    icon: ExclamationCircleIcon,
    roles: [ROLES.ADMIN, ROLES.ASSISTANT]
  },
  {
    path: '/dashboard/stock-control',
    group: 'stock',
    adminHidden: true,
    labelKey: 'stockControl.menu_control',
    icon: ClipboardDocumentCheckIcon,
    roles: [ROLES.STOCK_CONTROLLER, ROLES.ADMIN]
  },
  {
    path: '/dashboard/stock-movements',
    group: 'stock',
    labelKey: 'stockControl.menu_movements',
    icon: ArrowsRightLeftIcon,
    roles: [ROLES.STOCK_CONTROLLER, ROLES.ADMIN, ROLES.ASSISTANT]
  },
  {
    path: '/dashboard/stock-adjustment-requests',
    group: 'stock',
    labelKey: 'stockAdjust.menu_admin',
    icon: AdjustmentsHorizontalIcon,
    roles: [ROLES.ADMIN]
  },
  // Stock du laboratoire (admin voit tout via filteredMenu)
  {
    path: '/dashboard/lab-stock-products',
    group: 'labstock',
    labelKey: 'labStock.menu_products',
    icon: BeakerIcon,
    roles: [ROLES.LABORANTIN, ROLES.STOCK_CONTROLLER, ROLES.PROMOTEUR, ROLES.TOXICO_MANAGER]
  },
  {
    path: '/dashboard/lab-stock-requests',
    group: 'labstock',
    labelKey: 'labStock.menu_requests',
    icon: ShoppingCartIcon,
    roles: [ROLES.LABORANTIN, ROLES.STOCK_CONTROLLER, ROLES.PROMOTEUR, ROLES.TOXICO_MANAGER]
  },
  {
    path: '/dashboard/lab-stock-receipts',
    group: 'labstock',
    labelKey: 'labStock.menu_receipts',
    icon: ClipboardDocumentCheckIcon,
    roles: [ROLES.STOCK_CONTROLLER, ROLES.PROMOTEUR]
  },
  {
    path: '/dashboard/lab-stock-count',
    group: 'labstock',
    adminHidden: true,
    labelKey: 'labStock.menu_count',
    icon: AdjustmentsHorizontalIcon,
    roles: [ROLES.LABORANTIN]
  },
  {
    path: '/dashboard/lab-stock-alerts',
    group: 'labstock',
    labelKey: 'labStock.menu_alerts',
    icon: ExclamationCircleIcon,
    roles: [ROLES.LABORANTIN, ROLES.PROMOTEUR, ROLES.TOXICO_MANAGER]
  },
  {
    path: '/dashboard/lab-stock-movements',
    group: 'labstock',
    labelKey: 'labStock.menu_movements',
    icon: ArrowsRightLeftIcon,
    roles: [ROLES.STOCK_CONTROLLER, ROLES.PROMOTEUR, ROLES.TOXICO_MANAGER]
  },
  {
    path: '/dashboard/lab-stock-expenses',
    group: 'labstock',
    labelKey: 'labStock.menu_expenses',
    icon: BanknotesIcon,
    roles: [ROLES.PROMOTEUR, ROLES.TOXICO_MANAGER]
  },
  // Fabrication (admin voit tout via filteredMenu ; lecture seule pour promoteur et admin)
  {
    path: '/dashboard/fabrication-lots',
    group: 'fabrication',
    labelKey: 'fabrication.menu_lots',
    icon: BeakerIcon,
    roles: [ROLES.PRODUCTION_MANAGER, ROLES.PROMOTEUR]
  },
  {
    path: '/dashboard/fabrication-intrants',
    group: 'fabrication',
    labelKey: 'fabrication.menu_intrants',
    icon: CubeIcon,
    roles: [ROLES.PRODUCTION_MANAGER, ROLES.PROMOTEUR]
  },
  {
    path: '/dashboard/fabrication-suivi',
    group: 'fabrication',
    labelKey: 'fabrication.menu_suivi',
    icon: ChartBarIcon,
    roles: [ROLES.PRODUCTION_MANAGER, ROLES.PROMOTEUR]
  },
  {
    path: '/dashboard/logs',
    labelKey: 'tech.title',
    icon: ShieldCheckIcon,
    roles: [ROLES.TOXICO_MANAGER]
  },
  {
    path: '/dashboard/configuration',
    labelKey: 'config.title',
    icon: CogIcon,
    separator: true,
    roles: [ROLES.TOXICO_MANAGER]
  }
];

// --- 3. FILTRAGE + SOUS-MENUS (logique pure dans utils/sidebarMenu.js) ---
const MENU_GROUPS = {
  stock: { labelKey: 'stockOps.menu_group', icon: CubeIcon },
  labstock: { labelKey: 'labStock.menu_group', icon: BeakerIcon },
  fabrication: { labelKey: 'fabrication.menu_group', icon: BeakerIcon }
};

const menuEntries = computed(() => buildMenu(menuItems, {
    isAdmin: authStore.isAdmin || authStore.hasRole([ROLES.ADMIN]),
    hasRole: (roles) => authStore.hasRole(roles),
    groups: MENU_GROUPS
}));

// Format attendu par AppShell : un seul groupe sans intertitre, sous-menus repliables pour Stock et Stock du labo.
const menuGroups = computed(() => toShellGroups(menuEntries.value));

onMounted(() => {
    // Seuls admin/promoteur peuvent atteindre un ecran caisse/finance
    // depuis ce shell (voir router/index.js) - on evite un appel/403
    // inutile en console pour les autres roles (medecin, nurse,
    // laborantin, ...) qui ne declenchent jamais d'impression.
    if (authStore.hasRole([ROLES.ADMIN, ROLES.PROMOTEUR])) {
        configStore.fetchTicketPrintToken();
    }
});
</script>
