<template>
  <UiStatusBadge :tone="tone" :label="label" />
</template>

<script setup>
// Meme API qu'avant (prop `status`) : l'apparence passe par le badge commun de la refonte
// (point + texte, couleur selon le sens : vert = termine, rouge = annule, orange = en attente).
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { StatusBadge as UiStatusBadge } from '@/components/ui';

const { t } = useI18n();

const props = defineProps({
  status: {
    type: String,
    required: true,
  },
});

const tone = computed(() => {
  if (props.status === 'completed') return 'success';
  if (props.status === 'cancelled') return 'danger';
  return 'warning';
});

const label = computed(() => {
  if (props.status === 'completed') return t('appointments.status_completed');
  if (props.status === 'cancelled') return t('appointments.status_cancelled');
  return t('appointments.status_pending');
});
</script>
