<template>
  <div class="app-refonte min-h-dvh bg-page md:grid md:grid-cols-[minmax(0,5fr)_minmax(0,6fr)]">

    <!-- Volet photo (PC et tablette) : photo du médecin, dégradé bleu nuit et message d'accueil -->
    <aside class="relative hidden md:flex flex-col justify-end overflow-hidden bg-nav-900 text-white">
      <img
        :src="heroPhoto"
        alt=""
        class="absolute inset-0 h-full w-full object-cover object-top"
        width="760"
        height="1028"
        fetchpriority="high"
      />
      <div class="absolute inset-0 bg-linear-to-t from-nav-900 via-nav-900/55 to-transparent" aria-hidden="true"></div>

      <div class="relative p-10 lg:p-14">
        <p class="max-w-sm text-3xl font-bold leading-snug">{{ $t('loginPage.heroTitle') }}</p>
        <div class="my-5 h-1 w-14 rounded-full bg-brand-500" aria-hidden="true"></div>
        <p class="text-lg font-semibold">{{ $t('loginPage.heroOrg') }}</p>
        <p class="text-base text-nav-text">{{ $t('loginPage.heroAddress') }}</p>
      </div>
    </aside>

    <main class="flex flex-col items-center justify-center gap-6 px-4 py-8 sm:px-8 md:px-10">
      <div class="w-full max-w-md">

        <div class="text-center">
          <img
            :src="logoSrc"
            alt="A.H2"
            class="mx-auto h-28 w-auto md:h-36"
            width="300"
            height="282"
          />
          <h1 class="mt-4 text-3xl font-bold text-nav-800">{{ $t('loginPage.title') }}</h1>
          <p class="mt-1 text-2xl font-medium text-brand-600">{{ orgName }}</p>
          <p class="mt-3 text-base text-ink-muted">{{ $t('loginPage.subtitle') }}</p>
        </div>

        <p
          v-if="error"
          role="alert"
          class="mt-6 flex items-start gap-2 rounded-control border p-3 text-base"
          :class="toneClasses('danger')"
        >
          <ExclamationCircleIcon class="mt-0.5 h-5 w-5 shrink-0" aria-hidden="true" />
          <span><span class="font-semibold">{{ $t('loginPage.errorPrefix') }}</span> {{ error }}</span>
        </p>

        <form class="mt-8 grid gap-5" @submit.prevent="handleLogin">

          <FormField id="username" :label="$t('loginPage.username')" required v-slot="{ describedBy }">
            <div class="relative">
              <UserIcon class="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-ink-muted" aria-hidden="true" />
              <input
                id="username"
                ref="usernameInput"
                v-model="username"
                type="text"
                required
                autocomplete="username"
                :aria-describedby="describedBy"
                :placeholder="$t('loginPage.usernamePlaceholder')"
                class="w-full min-h-12 pl-12 pr-4 py-2 text-base bg-white border border-tone-neutral-border rounded-card shadow-card placeholder:text-ink-muted focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600"
              />
            </div>
          </FormField>

          <FormField id="password" :label="$t('loginPage.password')" required v-slot="{ describedBy }">
            <div class="relative">
              <LockClosedIcon class="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-ink-muted" aria-hidden="true" />
              <input
                id="password"
                v-model="password"
                :type="showPassword ? 'text' : 'password'"
                required
                autocomplete="current-password"
                :aria-describedby="describedBy"
                :placeholder="$t('loginPage.passwordPlaceholder')"
                class="w-full min-h-12 pl-12 pr-14 py-2 text-base bg-white border border-tone-neutral-border rounded-card shadow-card placeholder:text-ink-muted focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600"
              />
              <button
                type="button"
                class="absolute inset-y-0 right-0 min-w-12 inline-flex items-center justify-center rounded-card text-ink-muted hover:text-ink focus-visible:outline-2 focus-visible:outline-brand-600"
                :aria-label="showPassword ? $t('loginPage.hidePassword') : $t('loginPage.showPassword')"
                :aria-pressed="showPassword"
                @click="showPassword = !showPassword"
              >
                <EyeSlashIcon v-if="showPassword" class="h-5 w-5" aria-hidden="true" />
                <EyeIcon v-else class="h-5 w-5" aria-hidden="true" />
              </button>
            </div>
          </FormField>

          <div class="-mt-2 flex justify-end">
            <a
              href="#"
              @click.prevent="showForgotPasswordModal = true"
              class="inline-flex min-h-11 items-center text-base font-medium text-brand-700 hover:underline focus-visible:outline-2 focus-visible:outline-brand-600"
            >
              {{ $t('loginPage.forgot') }}
            </a>
          </div>

          <AppButton type="submit" variant="brand" size="lg" class="w-full !rounded-card text-lg" :loading="isLoading">
            {{ isLoading ? $t('loginPage.submitting') : $t('loginPage.submit') }}
            <ArrowRightIcon v-if="!isLoading" class="h-5 w-5" aria-hidden="true" />
          </AppButton>
        </form>

        <p class="mt-8 flex items-center justify-center gap-2 text-sm text-ink-muted">
          <ShieldCheckIcon class="h-5 w-5 shrink-0 text-brand-600" aria-hidden="true" />
          {{ $t('loginPage.security') }}
        </p>
      </div>

      <p class="text-sm text-ink-muted">{{ $t('loginPage.copyright') }} {{ orgName }}</p>
    </main>

    <!-- Simple modale d'information (pas de flux de reinitialisation -
         demande explicite de l'utilisateur, texte exact impose) -->
    <div
      v-if="showForgotPasswordModal"
      class="fixed inset-0 z-50 flex items-center justify-center bg-ink/50 p-4"
      role="dialog"
      aria-modal="true"
      @click.self="showForgotPasswordModal = false"
    >
      <div class="w-full max-w-sm bg-white p-6 rounded-card shadow-card border border-tone-neutral-border">
        <p class="text-base text-ink text-center">
          {{ $t('loginPage.forgotMessage') }}
        </p>
        <AppButton class="mt-6 w-full" @click="showForgotPasswordModal = false">
          {{ $t('loginPage.close') }}
        </AppButton>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import {
  EyeIcon, EyeSlashIcon, LockClosedIcon, UserIcon, ShieldCheckIcon, ArrowRightIcon, ExclamationCircleIcon,
} from '@heroicons/vue/24/outline';
import { useAuthStore } from '@/stores/auth';
import { useConfigStore } from '@/stores/configStore';
import { resolveAssetUrl } from '@/services/api';
import { getPostLoginPath } from '@/utils/postLoginRoute';
import { toneClasses } from '@/design/tones';
import AppButton from '@/components/ui/AppButton.vue';
import FormField from '@/components/ui/FormField.vue';
import heroPhoto from '@/assets/login/medecin.webp';
import ahLogo from '@/assets/login/ah2-logo.webp';

const router = useRouter();
const authStore = useAuthStore();
// Logo et nom du centre : valeurs mises en cache par la session précédente, aucun appel réseau ajouté ici.
const configStore = useConfigStore();
const { t } = useI18n();

const logoSrc = computed(() =>
  configStore.structureInfo.logo_url ? resolveAssetUrl(configStore.structureInfo.logo_url) : ahLogo
);
const orgName = computed(() => configStore.structureInfo.name || 'A.H2 Medical Center');

const username = ref('');
const password = ref('');
const error = ref(null);
const isLoading = ref(false);
const showForgotPasswordModal = ref(false);
const showPassword = ref(false);
const usernameInput = ref(null);

onMounted(() => usernameInput.value?.focus());

// Page d'accueil de chaque role : voir src/utils/postLoginRoute.js
const getRedirectPath = getPostLoginPath;

const handleLogin = async () => {
  error.value = null;
  isLoading.value = true;

  try {
    // 1. Appel API pour login
    await authStore.login(username.value, password.value);

    // 2. Récupération du rôle (maintenant disponible dans le store)
    const role = authStore.userRole;

    // 3. Calcul de la route de destination
    const targetRoute = getRedirectPath(role);

    //console.log(`Connexion réussie. Rôle: ${role} -> Redirection vers: ${targetRoute}`);

    // 4. Redirection ciblée
    router.push(targetRoute);

  } catch (err) {
    console.error(err);
    if (err.response && err.response.status === 401) {
      error.value = t('loginPage.errorInvalid');
    } else {
      error.value = t('loginPage.errorGeneric');
    }
  } finally {
    isLoading.value = false;
  }
};
</script>
