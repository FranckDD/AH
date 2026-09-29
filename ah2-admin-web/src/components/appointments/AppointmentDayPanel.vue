<template>
  <div class="bg-white rounded-2xl shadow-xs border border-gray-100 overflow-hidden h-fit">
    <div class="p-4 border-b border-gray-100 flex items-center justify-between">
      <h3 class="text-sm font-bold text-gray-700">
        {{ t('appointments.calendar.day_panel_title') }} {{ formattedDate }}
      </h3>
      <button @click="$emit('close')" class="p-1 rounded-lg hover:bg-gray-100 transition">
        <XMarkIcon class="h-5 w-5 text-gray-400" />
      </button>
    </div>

    <div v-if="appointments.length === 0" class="p-6 text-sm text-gray-500 italic text-center">
      {{ t('appointments.calendar.day_panel_empty') }}
    </div>

    <div v-else class="divide-y divide-gray-100">
      <div v-for="appt in appointments" :key="appt.id" class="p-4 space-y-2">
        <div class="flex items-center justify-between">
          <div>
            <div class="text-sm font-semibold text-gray-900">{{ patientLabel(appt) }}</div>
            <div class="text-xs text-gray-500 font-mono">{{ (appt.appointment_time || '').substring(0, 5) }}</div>
          </div>
          <StatusBadge :status="appt.status" />
        </div>
        <div v-if="appt.reason" class="text-xs text-gray-600">{{ appt.reason }}</div>

        <div class="flex flex-wrap gap-2 pt-1">
          <button
            v-if="appt.status === 'pending'"
            @click="$emit('complete', appt)"
            :disabled="!appt.server_id"
            class="px-3 py-1.5 text-xs font-medium rounded-lg bg-emerald-50 text-emerald-700 hover:bg-emerald-100 transition disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {{ t('appointments.actions.complete') }}
          </button>
          <button
            v-if="appt.status === 'pending'"
            @click="$emit('cancel', appt)"
            :disabled="!appt.server_id"
            class="px-3 py-1.5 text-xs font-medium rounded-lg bg-red-50 text-red-700 hover:bg-red-100 transition disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {{ t('appointments.actions.cancel') }}
          </button>
          <button
            v-if="appt.status === 'pending'"
            @click="$emit('view-dossier', appt)"
            :disabled="!appt.patient_id"
            class="px-3 py-1.5 text-xs font-medium rounded-lg bg-blue-50 text-blue-700 hover:bg-blue-100 transition disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {{ t('appointments.actions.view_dossier') }}
          </button>
          <button
            v-if="appt.status === 'pending'"
            @click="$emit('start-consultation', appt)"
            :disabled="!appt.patient_id || !appt.server_id"
            class="px-3 py-1.5 text-xs font-medium rounded-lg bg-emerald-50 text-emerald-700 hover:bg-emerald-100 transition disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {{ t('appointments.actions.start_consultation') }}
          </button>
          <button
            @click="$emit('edit', appt)"
            class="px-3 py-1.5 text-xs font-medium rounded-lg bg-gray-100 text-gray-700 hover:bg-gray-200 transition"
          >
            {{ t('appointments.actions.edit') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import dayjs from 'dayjs';
import { XMarkIcon } from '@heroicons/vue/24/outline';
import StatusBadge from '@/components/appointments/StatusBadge.vue';

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
  return [appt.first_name, appt.last_name].filter(Boolean).join(' ') || '—';
}
</script>
