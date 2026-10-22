<script setup>
// Panneau plein ecran (telephone et tablette) ou grande fenetre centree (PC) pour les formulaires longs.
// Se ferme par le bouton ou la touche Echap (meme evenement `close`) ; le focus reste dans le panneau
// (Tab boucle) et revient a l'element precedent a la fermeture. Aucun avertissement de saisie n'est ajoute :
// il n'en existait pas avant la refonte.
import { ref, onMounted, onBeforeUnmount, useId } from 'vue';
import { useI18n } from 'vue-i18n';
import { XMarkIcon } from '@heroicons/vue/24/outline';
import { nextFocusIndex } from '@/utils/ui';

defineProps({
    title: { type: String, required: true },
});
const emit = defineEmits(['close']);

const { t } = useI18n();
const titleId = `panel-title-${useId()}`;
const panel = ref(null);
const closeButton = ref(null);
let previouslyFocused = null;

const FOCUSABLE =
    'a[href], button:not([disabled]), input:not([disabled]):not([type="hidden"]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

// Seuls les elements visibles comptent (une section repliee est en display:none).
function focusables() {
    if (!panel.value) return [];
    return [...panel.value.querySelectorAll(FOCUSABLE)].filter((el) => el.offsetParent !== null);
}

function onKeydown(event) {
    if (event.key === 'Escape') {
        event.stopPropagation();
        emit('close');
        return;
    }
    if (event.key !== 'Tab') return;
    const items = focusables();
    if (!items.length) {
        event.preventDefault();
        return;
    }
    const next = nextFocusIndex(items.indexOf(document.activeElement), items.length, event.shiftKey);
    // On ne force le focus que pour boucler ou entrer dans le panneau ; sinon le navigateur suit l'ordre naturel.
    const current = items.indexOf(document.activeElement);
    const wraps = current === -1 || (!event.shiftKey && current === items.length - 1) || (event.shiftKey && current === 0);
    if (wraps) {
        event.preventDefault();
        items[next].focus();
    }
}

onMounted(() => {
    previouslyFocused = document.activeElement;
    // Premier champ de saisie du corps, sinon le bouton de fermeture.
    const first = focusables().find((el) => el !== closeButton.value?.$el && el !== closeButton.value) || closeButton.value;
    first?.focus?.();
});

onBeforeUnmount(() => {
    previouslyFocused?.focus?.();
});
</script>

<template>
    <div class="fixed inset-0 z-50 flex bg-ink/50 lg:items-center lg:justify-center lg:p-6" @keydown="onKeydown">
        <div
            ref="panel"
            role="dialog"
            aria-modal="true"
            :aria-labelledby="titleId"
            class="app-refonte flex h-full w-full flex-col bg-white lg:h-auto lg:max-h-[90dvh] lg:max-w-4xl lg:rounded-card lg:shadow-card"
        >
            <header class="flex shrink-0 items-center justify-between gap-3 border-b border-tone-neutral-border px-4 py-3 md:px-6">
                <h2 :id="titleId" class="text-xl font-bold text-ink">{{ title }}</h2>
                <button
                    ref="closeButton"
                    type="button"
                    class="inline-flex min-h-11 min-w-11 items-center justify-center rounded-control text-ink-muted hover:bg-tone-neutral-bg focus-visible:outline-2 focus-visible:outline-brand-600"
                    :aria-label="t('ui.close')"
                    @click="emit('close')"
                >
                    <XMarkIcon class="h-6 w-6" aria-hidden="true" />
                </button>
            </header>

            <div class="min-h-0 flex-1 overflow-y-auto px-4 py-4 md:px-6">
                <slot />
            </div>

            <footer v-if="$slots.footer" class="shrink-0">
                <slot name="footer" />
            </footer>
        </div>
    </div>
</template>
