<script setup>
// Etat honnete d'un ecran qui n'a pas pu charger ses donnees (hors ligne ou serveur injoignable) :
// a la place d'un "0" ou d'un "Aucun ..." qui laisse croire que c'est vide. Un bouton relance le chargement.
import { ref, computed, onMounted, onBeforeUnmount } from 'vue';
import { useI18n } from 'vue-i18n';
import { ExclamationTriangleIcon } from '@heroicons/vue/24/outline';
import AppButton from './AppButton.vue';

const props = defineProps({
    // texte propre a l'ecran ; sinon le texte commun hors ligne / erreur
    message: { type: String, default: '' },
    compact: { type: Boolean, default: false },
});
defineEmits(['retry']);

const { t } = useI18n();
const online = ref(typeof navigator === 'undefined' ? true : navigator.onLine !== false);
const sync = () => { online.value = typeof navigator === 'undefined' ? true : navigator.onLine !== false; };
onMounted(() => { window.addEventListener('online', sync); window.addEventListener('offline', sync); });
onBeforeUnmount(() => { window.removeEventListener('online', sync); window.removeEventListener('offline', sync); });

const title = computed(() => props.message || (online.value ? t('loadError.server') : t('loadError.offline')));
</script>

<template>
    <div role="status" class="flex flex-col items-center gap-2 text-center"
         :class="compact ? 'px-3 py-4' : 'px-4 py-10'">
        <ExclamationTriangleIcon class="h-8 w-8 text-tone-warning-text" aria-hidden="true" />
        <p class="max-w-md text-base font-semibold text-ink">{{ title }}</p>
        <AppButton variant="secondary" @click="$emit('retry')">{{ t('loadError.retry') }}</AppButton>
    </div>
</template>
