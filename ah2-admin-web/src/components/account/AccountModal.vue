<template>
  <div class="fixed inset-0 bg-gray-900 bg-opacity-60 overflow-y-auto h-full w-full z-50 flex items-center justify-center backdrop-blur-xs">
    <div class="relative mx-auto w-full max-w-md bg-white shadow-xl rounded-2xl border border-gray-200 flex flex-col max-h-[90vh]">
      <div class="px-6 py-4 border-b border-gray-100 bg-gray-700 rounded-t-2xl flex justify-between items-center shrink-0">
        <h3 class="text-lg font-bold text-white flex items-center">
          <UserCircleIcon class="h-6 w-6 mr-2" />
          {{ t('account.title') }}
        </h3>
        <button @click="$emit('close')" class="text-gray-200 hover:text-white transition">
          <span class="text-2xl font-bold">&times;</span>
        </button>
      </div>

      <div class="border-b border-gray-100 flex shrink-0">
        <button
          @click="activeTab = 'profile'"
          class="flex-1 py-3 text-sm font-semibold transition"
          :class="activeTab === 'profile' ? 'text-gray-800 border-b-2 border-gray-700' : 'text-gray-400 hover:text-gray-600'"
        >
          {{ t('account.tab_profile') }}
        </button>
        <button
          @click="activeTab = 'password'"
          class="flex-1 py-3 text-sm font-semibold transition"
          :class="activeTab === 'password' ? 'text-gray-800 border-b-2 border-gray-700' : 'text-gray-400 hover:text-gray-600'"
        >
          {{ t('account.tab_password') }}
        </button>
      </div>

      <div class="p-6 overflow-y-auto">
        <div v-if="activeTab === 'profile' && isLoadingProfile" class="text-center py-6 text-sm text-gray-400">
          {{ t('common.loading') }}
        </div>
        <form v-if="activeTab === 'profile' && !isLoadingProfile" @submit.prevent="handleProfileSubmit" class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('account.full_name') }}</label>
            <input v-model="profileForm.fullName" type="text" required
                   class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-gray-500 focus:border-gray-500" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('account.email') }}</label>
            <input v-model="profileForm.email" type="email"
                   class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-gray-500 focus:border-gray-500" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('account.contact') }}</label>
            <input v-model="profileForm.contact" type="tel"
                   class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-gray-500 focus:border-gray-500" />
          </div>

          <div v-if="profileError" class="bg-red-50 border-l-4 border-red-500 p-3 rounded-sm text-sm text-red-700">
            {{ profileError }}
          </div>
          <div v-if="profileSuccess" class="bg-green-50 border-l-4 border-green-500 p-3 rounded-sm text-sm text-green-700">
            {{ t('account.profile_saved') }}
          </div>

          <div class="flex justify-end pt-2">
            <button type="submit" :disabled="isSavingProfile"
                    class="px-6 py-2 bg-gray-800 text-white rounded-lg hover:bg-gray-900 font-medium shadow-xs transition disabled:opacity-50">
              {{ isSavingProfile ? t('account.saving') : t('account.save') }}
            </button>
          </div>
        </form>

        <form v-if="activeTab === 'password'" @submit.prevent="handlePasswordSubmit" class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('account.old_password') }}</label>
            <input v-model="passwordForm.oldPassword" type="password" required
                   class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-gray-500 focus:border-gray-500" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('account.new_password') }}</label>
            <input v-model="passwordForm.newPassword" type="password" required minlength="8"
                   class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-gray-500 focus:border-gray-500" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('account.confirm_password') }}</label>
            <input v-model="passwordForm.confirmPassword" type="password" required minlength="8"
                   class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-gray-500 focus:border-gray-500" />
          </div>

          <div v-if="passwordMismatch" class="bg-red-50 border-l-4 border-red-500 p-3 rounded-sm text-sm text-red-700">
            {{ t('account.password_mismatch') }}
          </div>
          <div v-if="passwordError" class="bg-red-50 border-l-4 border-red-500 p-3 rounded-sm text-sm text-red-700">
            {{ passwordError }}
          </div>
          <div v-if="passwordSuccess" class="bg-green-50 border-l-4 border-green-500 p-3 rounded-sm text-sm text-green-700">
            {{ t('account.password_saved') }}
          </div>

          <div class="flex justify-end pt-2">
            <button type="submit" :disabled="isSavingPassword"
                    class="px-6 py-2 bg-gray-800 text-white rounded-lg hover:bg-gray-900 font-medium shadow-xs transition disabled:opacity-50">
              {{ isSavingPassword ? t('account.saving') : t('account.save') }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { useAuthStore } from '@/stores/auth';
import { UserCircleIcon } from '@heroicons/vue/24/outline';

defineEmits(['close']);
const { t } = useI18n();
const authStore = useAuthStore();

const activeTab = ref('profile');

// --- Profil ---
// Pre-rempli depuis un GET /auth/me FRAIS, pas depuis authStore.user au
// montage : authStore.user n'est reellement rafraichi que dans login(),
// une session ouverte avant ce chantier (ou jamais re-authentifiee)
// aurait full_name/email/contact absents en cache localStorage - les
// pre-remplir depuis ce cache perime, puis soumettre le formulaire,
// effacerait silencieusement les vraies valeurs en base (trouve par la
// revue finale du chantier 7d, reproduit en reel).
const profileForm = reactive({
  fullName: '',
  email: '',
  contact: '',
});
const isLoadingProfile = ref(true);
const isSavingProfile = ref(false);
const profileError = ref('');
const profileSuccess = ref(false);

onMounted(async () => {
  try {
    const fresh = await authStore.fetchMe();
    profileForm.fullName = fresh.full_name || '';
    profileForm.email = fresh.email || '';
    profileForm.contact = fresh.contact || '';
  } catch (err) {
    profileError.value = mapErrorToMessage(err);
  } finally {
    isLoadingProfile.value = false;
  }
});

const mapErrorToMessage = (err) => {
  if (err.response) {
    const status = err.response.status;
    const detail = err.response.data?.detail;
    if (status === 422) return "Données invalides.";
    if (status === 400) return detail || "Requête invalide.";
    if (status === 409) return "Cette adresse email est déjà utilisée.";
    return `Erreur serveur (${status}) : ${detail || 'veuillez réessayer'}`;
  }
  if (err.request) return "Erreur réseau. Veuillez vérifier votre connexion.";
  return err.message || "Une erreur inattendue est survenue.";
};

const handleProfileSubmit = async () => {
  const trimmedFullName = profileForm.fullName.trim();
  if (!trimmedFullName) {
    profileError.value = "Le nom complet ne peut pas être vide.";
    return;
  }
  isSavingProfile.value = true;
  profileError.value = '';
  profileSuccess.value = false;
  try {
    await authStore.updateProfile({
      full_name: trimmedFullName,
      email: profileForm.email.trim() || null,
      contact: profileForm.contact.trim() || null,
    });
    profileSuccess.value = true;
  } catch (err) {
    profileError.value = mapErrorToMessage(err);
  } finally {
    isSavingProfile.value = false;
  }
};

// --- Mot de passe ---
const passwordForm = reactive({
  oldPassword: '',
  newPassword: '',
  confirmPassword: '',
});
const isSavingPassword = ref(false);
const passwordError = ref('');
const passwordSuccess = ref(false);

const passwordMismatch = computed(() =>
  passwordForm.newPassword.length > 0 &&
  passwordForm.confirmPassword.length > 0 &&
  passwordForm.newPassword !== passwordForm.confirmPassword
);

const handlePasswordSubmit = async () => {
  if (passwordMismatch.value) return;
  isSavingPassword.value = true;
  passwordError.value = '';
  passwordSuccess.value = false;
  try {
    await authStore.changePassword({
      old_password: passwordForm.oldPassword,
      new_password: passwordForm.newPassword,
      confirm_password: passwordForm.confirmPassword,
    });
    passwordSuccess.value = true;
    passwordForm.oldPassword = '';
    passwordForm.newPassword = '';
    passwordForm.confirmPassword = '';
    // PUT /auth/password revoque desormais TOUS les tokens de l'utilisateur,
    // y compris celui de cette session en cours (chantier 7d, decision du
    // 2026-09-22 : meme comportement que le bouton Deconnexion). Le prochain
    // appel API echouerait donc en 401 - on deconnecte nous-memes plutot que
    // de laisser l'utilisateur decouvrir un ecran casse. Delai court pour
    // laisser le message de succes visible avant la redirection.
    setTimeout(() => authStore.logout(), 2000);
  } catch (err) {
    passwordError.value = mapErrorToMessage(err);
  } finally {
    isSavingPassword.value = false;
  }
};
</script>
