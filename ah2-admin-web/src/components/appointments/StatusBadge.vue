<template>
  <span v-if="status === 'completed'" class="inline-flex items-center px-2 py-0.5 rounded-sm text-xs font-medium bg-emerald-100 text-emerald-800">
    <CheckCircleIcon class="h-3 w-3 mr-1" /> {{ t('appointments.status_completed') }}
  </span>
  <span v-else-if="status === 'cancelled'" class="inline-flex items-center px-2 py-0.5 rounded-sm text-xs font-medium bg-red-100 text-red-800">
    <XCircleIcon class="h-3 w-3 mr-1" /> {{ t('appointments.status_cancelled') }}
  </span>
  <span v-else class="inline-flex items-center px-2 py-0.5 rounded-sm text-xs font-medium bg-yellow-100 text-yellow-800">
    <ClockIcon class="h-3 w-3 mr-1" /> {{ t('appointments.status_pending') }}
  </span>
</template>

<script setup>
import { useI18n } from 'vue-i18n';
import { CheckCircleIcon, XCircleIcon, ClockIcon } from '@heroicons/vue/24/outline';

const { t } = useI18n();

defineProps({
  status: {
    type: String,
    required: true,
  },
});
</script>
