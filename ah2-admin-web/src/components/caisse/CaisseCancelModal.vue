<template>
  <FullScreenPanel :title="title || t('caisse.cancel_modal.title')" @close="$emit('close')">
    <form id="cancel-form" @submit.prevent="handleSubmit" class="space-y-4">
      <p class="text-base font-semibold text-ink">{{ label }}</p>
      <p class="text-base text-ink-muted">{{ help || t('caisseScreens.cancel_help') }}</p>

      <FormField id="cancel-justification" :label="t('caisse.cancel_modal.justification')" required v-slot="{ describedBy }">
        <textarea
          id="cancel-justification"
          v-model="justification"
          rows="3"
          required
          :aria-describedby="describedBy"
          :class="[fieldClass, 'py-2']"
          :placeholder="t('caisse.cancel_modal.justification_placeholder')"
        ></textarea>
      </FormField>

      <p v-if="errorMessage" role="alert" class="flex items-start gap-2 rounded-control border p-3 text-base" :class="toneClasses('danger')">
        <ExclamationCircleIcon class="mt-0.5 h-5 w-5 shrink-0" aria-hidden="true" />
        <span>{{ errorMessage }}</span>
      </p>
    </form>

    <template #footer>
      <ActionBar>
        <template #secondary>
          <AppButton variant="ghost" :disabled="isSaving" @click="$emit('close')">{{ t('caisse.cancel_modal.cancel') }}</AppButton>
        </template>
        <AppButton type="submit" form="cancel-form" variant="danger" :disabled="isSaving || !justification.trim()" :loading="isSaving">
          {{ isSaving ? t('caisse.cancel_modal.saving') : t('caisse.cancel_modal.confirm') }}
        </AppButton>
      </ActionBar>
    </template>
  </FullScreenPanel>
</template>

<script setup>
import { ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { ExclamationCircleIcon } from '@heroicons/vue/20/solid';
import { AppButton, FormField, ActionBar, FullScreenPanel } from '@/components/ui';
import { toneClasses } from '@/design/tones';

const props = defineProps({
  label: { type: String, default: '' },
  title: { type: String, default: '' },
  help: { type: String, default: '' },
  isSaving: { type: Boolean, default: false },
  errorMessage: { type: String, default: '' },
});
const emit = defineEmits(['close', 'confirm']);

const { t } = useI18n();
const justification = ref('');

// Style commun des champs : zone tactile >= 44 px, focus visible.
const fieldClass = 'block w-full min-h-11 rounded-control border border-tone-neutral-border bg-white px-3 text-base text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600';

const handleSubmit = () => {
  if (!justification.value.trim()) return;
  emit('confirm', justification.value.trim());
};
</script>
