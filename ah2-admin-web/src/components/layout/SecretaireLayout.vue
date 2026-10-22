<template>
  <AppShell
    :menu-groups="menuGroups"
    :bell-roles="['admin', 'promoteur', 'secretaire']"
    brand-fallback="AH2 Secrétariat"
    sidebar-id="secretariat-sidebar"
    palette="forest"
  />
</template>

<script setup>
// Navigation propre a la fenetre secretariat (role secretaire uniquement) - pas de filtrage par role ici,
// contrairement a MainLayout.vue : ce cadre n'est jamais charge par un autre role (garde deja faite par le
// routeur, meta.roles). Tout le gabarit (menu, barre du haut, tiroir) vit dans AppShell.vue.
import { onMounted } from 'vue';
import AppShell from '@/components/layout/AppShell.vue';
import { useConfigStore } from '@/stores/configStore';
import {
  UserGroupIcon,
  CubeIcon,
  BanknotesIcon,
  ArrowUpTrayIcon,
  SparklesIcon,
  HomeIcon,
  ExclamationTriangleIcon,
  ClockIcon
} from '@heroicons/vue/24/outline';

const configStore = useConfigStore();

// Intertitres : le travail du jour (accueil, patients, caisse, retraits) puis le suivi.
// `exact` : l'accueil n'est actif que sur sa propre page.
const menuGroups = [
  {
    key: 'daily',
    labelKey: 'secretariatShell.sections.daily',
    items: [
      { path: '/secretariat/', labelKey: 'secretariat.nav.home', icon: HomeIcon, exact: true },
      { path: '/secretariat/patients', labelKey: 'secretariat.nav.patients', icon: UserGroupIcon },
      { path: '/secretariat/caisse', labelKey: 'secretariat.nav.caisse', icon: BanknotesIcon },
      { path: '/secretariat/retrait', labelKey: 'secretariat.nav.retrait', icon: ArrowUpTrayIcon },
    ],
  },
  {
    key: 'follow',
    labelKey: 'secretariatShell.sections.follow',
    items: [
      { path: '/secretariat/stock', labelKey: 'secretariat.nav.stock', icon: CubeIcon },
      { path: '/secretariat/discount-history', labelKey: 'secretariat.nav.discount_history', icon: ClockIcon },
      { path: '/secretariat/consultations', labelKey: 'secretariat.nav.consultations', icon: SparklesIcon },
      {
        path: '/secretariat/sync-failures',
        labelKey: 'secretariat.nav.sync_failures',
        icon: ExclamationTriangleIcon,
        onlyWhenQuarantine: true,
      },
    ],
  },
];

onMounted(() => {
  // La secretaire est le seul role qui declenche vraiment une impression
  // (facture caisse, reimpression) - sans ce chargement, le jeton
  // n'existe jamais pour elle (SystemConfig.vue n'est accessible qu'a
  // admin/promoteur) et toute impression echoue avec "Jeton d'impression
  // non configure".
  configStore.fetchTicketPrintToken();
});
</script>
