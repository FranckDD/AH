<template>
  <div :class="['app-refonte flex w-full h-dvh bg-page', navPaletteClass(palette)]">

    <!-- Voile derrière le tiroir (téléphone) -->
    <div
      v-if="isDrawerOpen"
      class="fixed inset-0 z-30 bg-ink/50 md:hidden"
      aria-hidden="true"
      @click="closeDrawer"
    ></div>

    <aside
      :id="sidebarId"
      :aria-label="t('medicalShell.mainNav')"
      :class="[
        'bg-linear-to-br from-nav-900 to-nav-700 text-nav-text w-72 max-w-[85vw] shrink-0 flex flex-col',
        'fixed inset-y-0 left-0 z-40 transition-all duration-200 ease-in-out',
        'md:static md:z-20 md:translate-x-0',
        isSidebarOpen ? 'md:w-64' : 'md:w-20',
        isDrawerOpen ? 'translate-x-0' : '-translate-x-full'
      ]"
    >
      <div class="px-4 flex items-center justify-between gap-2 h-16 border-b border-white/10 shrink-0 overflow-hidden">
        <div :class="['flex items-center gap-3 min-w-0', isSidebarOpen ? '' : 'md:hidden']">
          <img
            v-if="configStore.structureInfo.logo_url"
            :src="resolveAssetUrl(configStore.structureInfo.logo_url)"
            class="h-9 w-9 object-contain bg-white rounded-full p-0.5 shrink-0"
            alt="Logo"
          />
          <div v-else class="h-9 w-9 rounded-full bg-brand-600 text-white flex items-center justify-center font-bold text-sm shrink-0">
            {{ (configStore.structureInfo.name || 'AH').substring(0,2).toUpperCase() }}
          </div>

          <h2 class="text-lg font-bold truncate">{{ configStore.structureInfo.name || brandFallback }}</h2>
        </div>

        <!-- Téléphone : fermer le tiroir -->
        <button
          type="button"
          class="md:hidden min-h-11 min-w-11 inline-flex items-center justify-center rounded-control hover:bg-nav-800 focus-visible:outline-2 focus-visible:outline-brand-500"
          :aria-label="t('medicalShell.closeMenu')"
          @click="closeDrawer"
        >
          <XMarkIcon class="h-6 w-6" aria-hidden="true" />
        </button>

        <!-- Tablette / PC : réduire le menu en icônes ou le déployer -->
        <button
          type="button"
          :class="[
            'hidden md:inline-flex min-h-11 min-w-11 items-center justify-center rounded-control text-nav-text hover:bg-nav-800 hover:text-white focus-visible:outline-2 focus-visible:outline-brand-500',
            isSidebarOpen ? 'ml-auto' : 'mx-auto'
          ]"
          :aria-label="isSidebarOpen ? t('medicalShell.collapseMenu') : t('medicalShell.expandMenu')"
          :title="isSidebarOpen ? t('medicalShell.collapseMenu') : t('medicalShell.expandMenu')"
          :aria-expanded="isSidebarOpen"
          :aria-controls="sidebarId"
          @click="toggleSidebar"
        >
          <Bars3CenterLeftIcon v-if="isSidebarOpen" class="h-6 w-6" aria-hidden="true" />
          <Bars3Icon v-else class="h-6 w-6" aria-hidden="true" />
        </button>
      </div>

      <nav class="flex-1 overflow-y-auto py-4 px-3 custom-scrollbar">
        <div v-for="group in visibleGroups" :key="group.key" class="mb-5">
          <p v-if="group.labelKey" :class="['px-3 mb-1 text-sm font-semibold uppercase tracking-wide text-brand-100', isSidebarOpen ? '' : 'md:hidden']">
            {{ t(group.labelKey) }}
          </p>
          <!-- Menu réduit : un trait remplace l'intertitre -->
          <hr v-if="group.labelKey && !isSidebarOpen" class="hidden md:block mx-3 mb-2 border-nav-800" />
          <ul class="space-y-1">
            <li v-for="item in group.items" :key="item.path || item.key">
              <hr v-if="item.separator" class="mx-3 mb-3 mt-6 border-nav-800" />

              <!-- Sous-menu repliable : ouvert d'office quand la page courante est un de ses enfants -->
              <template v-if="item.children">
                <button
                  type="button"
                  :aria-expanded="isGroupOpen(item)"
                  :aria-controls="`${sidebarId}-${item.key}`"
                  :title="!isSidebarOpen ? t(item.labelKey) : undefined"
                  :class="[
                    'relative flex w-full items-center gap-3 min-h-11 py-2 px-3 rounded-control border-l-4 border-transparent text-left transition-colors duration-150',
                    isSidebarOpen ? '' : 'md:justify-center',
                    'focus-visible:outline-2 focus-visible:outline-brand-500',
                    groupActive(item) ? 'font-semibold text-white' : 'text-nav-text hover:bg-nav-800 hover:text-white'
                  ]"
                  @click="onGroupClick(item)"
                >
                  <component :is="item.icon" class="h-6 w-6 shrink-0" aria-hidden="true" />
                  <span :class="['text-base flex-1', isSidebarOpen ? '' : 'md:sr-only']">{{ t(item.labelKey) }}</span>
                  <ChevronDownIcon v-if="isSidebarOpen" :class="['h-5 w-5 shrink-0 transition-transform', isGroupOpen(item) ? 'rotate-180' : '']" aria-hidden="true" />
                </button>
                <ul v-if="isSidebarOpen && isGroupOpen(item)" :id="`${sidebarId}-${item.key}`" class="mt-1 space-y-1 pl-4">
                  <li v-for="child in item.children" :key="child.path">
                    <router-link
                      :to="child.path"
                      :aria-current="isActive(child) ? 'page' : undefined"
                      :class="[
                        'flex items-center gap-3 min-h-11 py-2 px-3 rounded-control border-l-4 transition-colors duration-150',
                        'focus-visible:outline-2 focus-visible:outline-brand-500',
                        isActive(child)
                          ? 'bg-nav-800 border-brand-500 font-semibold text-white'
                          : 'border-transparent text-nav-text hover:bg-nav-800 hover:text-white'
                      ]"
                    >
                      <component :is="child.icon" class="h-5 w-5 shrink-0" aria-hidden="true" />
                      <span class="text-base">{{ t(child.labelKey) }}</span>
                    </router-link>
                  </li>
                </ul>
              </template>

              <router-link
                v-else
                :to="item.path"
                :aria-current="isActive(item) ? 'page' : undefined"
                :title="!isSidebarOpen ? t(item.labelKey) : undefined"
                :class="[
                  'relative flex items-center gap-3 min-h-11 py-2 px-3 rounded-control border-l-4 transition-colors duration-150',
                  isSidebarOpen ? '' : 'md:justify-center',
                  'focus-visible:outline-2 focus-visible:outline-brand-500',
                  isActive(item)
                    ? 'bg-nav-800 border-brand-500 font-semibold text-white'
                    : 'border-transparent text-nav-text hover:bg-nav-800 hover:text-white'
                ]"
              >
                <component :is="item.icon" class="h-6 w-6 shrink-0" aria-hidden="true" />
                <span :class="['text-base', isSidebarOpen ? '' : 'md:sr-only']">{{ t(item.labelKey) }}</span>
                <span v-if="item.onlyWhenQuarantine"
                      :class="[
                        'inline-flex items-center justify-center min-w-6 px-1.5 rounded-full text-sm font-bold bg-tone-danger-text text-white',
                        isSidebarOpen ? 'ml-auto' : 'ml-auto md:absolute md:top-0 md:right-0 md:ml-0'
                      ]">
                  {{ quarantineCount }}
                </span>
              </router-link>
            </li>
          </ul>
        </div>
      </nav>
    </aside>

    <div class="flex-1 flex flex-col overflow-hidden w-full min-w-0">

      <header class="bg-white shadow-card px-3 py-2 md:px-4 flex flex-wrap items-center justify-between gap-x-4 gap-y-2 z-10 relative">

        <div class="flex items-center gap-2 min-w-0">
          <button
            type="button"
            class="md:hidden min-h-11 min-w-11 inline-flex items-center justify-center rounded-control text-ink hover:bg-tone-neutral-bg focus-visible:outline-2 focus-visible:outline-brand-600"
            :aria-label="t('medicalShell.openMenu')"
            :aria-controls="sidebarId"
            :aria-expanded="isDrawerOpen"
            @click="isDrawerOpen = true"
          >
            <Bars3Icon class="h-6 w-6" aria-hidden="true" />
          </button>

          <div class="min-w-0">
            <h1 class="text-lg font-semibold text-ink truncate">
              {{ $t('common.welcome') }}, <span class="text-brand-700">{{ displayName }}</span>
              <span class="hidden sm:inline text-sm text-ink-muted ml-2 font-normal">({{ roleLine }})</span>
            </h1>
            <p class="hidden lg:block text-sm text-ink-muted capitalize">{{ todayLabel }}</p>
          </div>
        </div>

        <div class="flex flex-wrap items-center gap-2 md:gap-3">
          <ConnectionStatus />

          <div class="flex bg-tone-neutral-bg rounded-control p-1">
            <button
              type="button"
              @click="changeLanguage('fr')"
              :aria-pressed="locale === 'fr'"
              :class="locale === 'fr' ? 'bg-white shadow-card text-ink' : 'text-ink-muted hover:text-ink'"
              class="min-h-9 px-3 rounded-control text-sm font-medium transition-all duration-200 focus-visible:outline-2 focus-visible:outline-brand-600"
            >FR</button>
            <button
              type="button"
              @click="changeLanguage('en')"
              :aria-pressed="locale === 'en'"
              :class="locale === 'en' ? 'bg-white shadow-card text-ink' : 'text-ink-muted hover:text-ink'"
              class="min-h-9 px-3 rounded-control text-sm font-medium transition-all duration-200 focus-visible:outline-2 focus-visible:outline-brand-600"
            >EN</button>
          </div>

          <NotificationBell v-if="authStore.hasRole(bellRoles)" />

          <button
            type="button"
            @click="showAccountModal = true"
            class="min-h-11 min-w-11 inline-flex items-center justify-center rounded-control text-ink-muted hover:text-ink hover:bg-tone-neutral-bg transition focus-visible:outline-2 focus-visible:outline-brand-600"
            :title="$t('common.my_account')"
            :aria-label="$t('common.my_account')"
          >
            <UserCircleIcon class="h-7 w-7" aria-hidden="true" />
          </button>

          <!-- Discret mais visible : bordure + texte, pas de fond rouge plein -->
          <button
            type="button"
            @click="handleLogout"
            class="min-h-11 px-4 rounded-control border border-tone-danger-border text-tone-danger-text text-sm font-semibold hover:bg-tone-danger-bg transition duration-150 focus-visible:outline-2 focus-visible:outline-brand-600"
          >
            {{ $t('common.logout') }}
          </button>
        </div>
      </header>

      <main class="flex-1 overflow-x-hidden overflow-y-auto p-4 md:p-6 bg-page w-full">
        <slot>
          <router-view :key="route.fullPath" />
        </slot>
      </main>

      <AccountModal v-if="showAccountModal" @close="showAccountModal = false" />
    </div>
  </div>
</template>

<script setup>
// Cadre commun des espaces refondus (menu bleu nuit, barre du haut, tiroir sous 768 px, bouton de reduction
// en icones, nom complet, indicateur de connexion, langue, cloche, compte, deconnexion). Chaque espace ne fournit
// que sa configuration : groupes de menu, roles qui voient la cloche, nom de repli de la structure.
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue';
import { useAuthStore } from '@/stores/auth';
import { useRoute, useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { useConfigStore } from '@/stores/configStore';
import { resolveAssetUrl } from '@/services/api';
import AccountModal from '@/components/account/AccountModal.vue';
import NotificationBell from '@/components/notifications/NotificationBell.vue';
import ConnectionStatus from '@/components/ui/ConnectionStatus.vue';
import { navPaletteClass } from '@/design/navPalettes';
import { groupContainsPath } from '@/utils/sidebarMenu';
import { useSyncQuarantineCount } from '@/composables/useSyncQuarantineCount';
import {
  Bars3Icon,
  Bars3CenterLeftIcon,
  XMarkIcon,
  UserCircleIcon,
  ChevronDownIcon,
} from '@heroicons/vue/24/outline';

const props = defineProps({
  // [{ key, labelKey, items: [{ path, labelKey, icon, onlyWhenQuarantine?, exact? }] }]
  menuGroups: { type: Array, required: true },
  // Roles qui voient la cloche de notifications.
  bellRoles: { type: Array, default: () => [] },
  // Nom affiche quand la structure n'a pas encore de nom enregistre.
  brandFallback: { type: String, default: 'AH2' },
  sidebarId: { type: String, default: 'app-sidebar' },
  // Palette du menu de l'espace (cle de design/navPalettes.js) : night (defaut) ou forest.
  palette: { type: String, default: 'night' },
});

const authStore = useAuthStore();
const configStore = useConfigStore();
const route = useRoute();
const { locale, t } = useI18n();

// Tiroir du menu : utilisé sous md seulement.
const isDrawerOpen = ref(false);
// À partir de md : menu déployé (libellés) ou réduit en icônes, au choix de l'utilisateur.
const isSidebarOpen = ref(true);
const showAccountModal = ref(false);

const quarantineCount = useSyncQuarantineCount();

// Sous-menus repliables (item avec children) : ouvert d'office si la page courante est un enfant, sinon au clic.
const router = useRouter();
const openGroups = ref({});
const groupActive = (item) => groupContainsPath(item, route.path);
const isGroupOpen = (item) => groupActive(item) || !!openGroups.value[item.key];
const onGroupClick = (item) => {
  // Menu reduit (icones) : on va directement au premier enfant.
  if (!isSidebarOpen.value) {
    router.push(item.children[0].path);
    return;
  }
  // Un groupe ouvert d'office par la route reste ouvert (pas de fermeture).
  if (groupActive(item)) return;
  openGroups.value = { ...openGroups.value, [item.key]: !openGroups.value[item.key] };
};

// Une entree « echecs de synchronisation » n'apparait que s'il y a quelque chose a resoudre ;
// un intertitre sans entree visible n'est pas affiche.
const visibleGroups = computed(() =>
  props.menuGroups
    .map((g) => ({
      ...g,
      items: g.items.filter((item) => !item.onlyWhenQuarantine || quarantineCount.value > 0),
    }))
    .filter((g) => g.items.length)
);

// Nom complet (profil) en premier ; l'identifiant reste affiché à côté. Sessions anciennes sans
// full_name en cache : repli sur l'identifiant seul.
const displayName = computed(
  () => authStore.user?.full_name?.trim() || authStore.user?.username || 'Utilisateur'
);
const roleLine = computed(() => {
  const username = authStore.user?.username;
  const hasFullName = !!authStore.user?.full_name?.trim();
  return hasFullName && username ? `${username}, ${authStore.userRole}` : authStore.userRole;
});

const todayLabel = computed(() =>
  new Date().toLocaleDateString(locale.value === 'en' ? 'en-GB' : 'fr-FR', {
    weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
  })
);

const toggleSidebar = () => {
  isSidebarOpen.value = !isSidebarOpen.value;
};

const closeDrawer = () => {
  isDrawerOpen.value = false;
};

const changeLanguage = (lang) => {
  locale.value = lang;
  localStorage.setItem('lang', lang);
};

const handleLogout = async () => {
  // authStore.logout() nettoie deja l'etat ET redirige vers /login lui-meme
  // (fin de sa propre fonction). L'appeler sans attendre puis naviguer ici
  // en parallele creait une course : ce router.push('/login') s'executait
  // AVANT que logout() n'ait fini de vider authStore.user/token, et le
  // garde de navigation (router/index.js) voyait alors un utilisateur
  // encore "authentifie" naviguant vers /login -> le redirigeait vers
  // /dashboard (regle "deja connecte + va au login = redirection
  // intelligente"), route reservee a l'admin - d'ou un flash "403 Acces
  // Interdit" au moment meme de la deconnexion (bug reel constate en test
  // navigateur). Attendre logout() avant de naviguer (ou simplement ne pas
  // re-naviguer ici du tout) elimine la course.
  await authStore.logout();
};

// Entree « exact » (ex. l'accueil d'un espace) : active seulement sur sa propre page ;
// sinon par inclusion du chemin, comme le cadre medical d'origine.
const isActive = (item) => {
  if (item.exact) {
    return route.path === item.path || route.path === item.path.replace(/\/$/, '');
  }
  return route.path.includes(item.path);
};

// Le tiroir se referme après chaque navigation et par la touche Échap.
watch(() => route.fullPath, closeDrawer);
const onKeydown = (e) => {
  if (e.key === 'Escape') closeDrawer();
};

onMounted(() => {
  configStore.fetchStructureInfo();
  window.addEventListener('keydown', onKeydown);
});

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown);
});
</script>

<style scoped>
.custom-scrollbar::-webkit-scrollbar {
  width: 4px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: var(--color-nav-900);
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: var(--color-nav-800);
  border-radius: 2px;
}
</style>
