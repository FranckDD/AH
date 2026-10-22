<template>
  <section class="h-fit overflow-hidden rounded-card border border-tone-neutral-border bg-white shadow-card">
    <div class="flex items-center justify-between gap-2 border-b border-tone-neutral-border px-4 py-3">
      <h3 class="text-lg font-semibold text-ink">
        {{ t('appointments.calendar.day_panel_title') }} {{ formattedDate }}
      </h3>
      <button
        type="button"
        @click="$emit('close')"
        class="inline-flex min-h-11 min-w-11 items-center justify-center rounded-control text-ink-muted hover:bg-tone-neutral-bg focus-visible:outline-2 focus-visible:outline-brand-600"
        :aria-label="t('ui.close')"
      >
        <XMarkIcon class="h-5 w-5" aria-hidden="true" />
      </button>
    </div>

    <EmptyState v-if="appointments.length === 0" :title="t('appointments.calendar.day_panel_empty')" />

    <ul v-else class="divide-y divide-tone-neutral-border">
      <li v-for="appt in appointments" :key="appt.id" class="space-y-3 p-4">
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0">
            <p class="text-base font-semibold text-ink">{{ patientLabel(appt) }}</p>
            <p class="font-mono text-sm text-ink-muted">{{ (appt.appointment_time || '').substring(0, 5) }}</p>
          </div>
          <StatusBadge :status="appt.status" />
        </div>
        <p v-if="appt.reason" class="text-base text-ink">{{ appt.reason }}</p>

        <div class="flex flex-col gap-2 sm:flex-row sm:flex-wrap">
          <AppButton
            v-if="appt.status === 'pending'"
            @click="$emit('start-consultation', appt)"
            :disabled="!appt.patient_id || !appt.server_id"
          >
            {{ t('appointments.actions.start_consultation') }}
          </AppButton>
          <AppButton
            v-if="appt.status === 'pending'"
            variant="secondary"
            @click="$emit('complete', appt)"
            :disabled="!appt.server_id"
          >
            {{ t('appointments.actions.complete') }}
          </AppButton>
          <AppButton
            v-if="appt.status === 'pending'"
            variant="secondary"
            @click="$emit('view-dossier', appt)"
            :disabled="!appt.patient_id"
          >
            {{ t('appointments.actions.view_dossier') }}
          </AppButton>
          <AppButton variant="ghost" @click="$emit('edit', appt)">
            {{ t('appointments.actions.edit') }}
          </AppButton>
          <AppButton
            v-if="appt.status === 'pending'"
            variant="danger"
            @click="$emit('cancel', appt)"
            :disabled="!appt.server_id"
          >
            {{ t('appointments.actions.cancel') }}
          </AppButton>
        </div>
      </li>
    </ul>
  </section>
</template>

<script setup>
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import dayjs from 'dayjs';
import { XMarkIcon } from '@heroicons/vue/24/outline';
import StatusBadge from '@/components/appointments/StatusBadge.vue';
import { AppButton, EmptyState } from '@/components/ui';

const { t } = useI18n();

const props = defineProps({
  date: {
    type: String,
    required: true,
  },
  appointments: {
    type: Array,
    default: () => [],
  },
});

defineEmits(['close', 'edit', 'cancel', 'complete', 'view-dossier', 'start-consultation']);

const formattedDate = computed(() => dayjs(props.date).format('DD/MM/YYYY'));

function patientLabel(appt) {
  return [appt.first_name, appt.last_name].filter(Boolean).join(' ') || '-';
}
</script>
