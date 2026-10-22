<!-- ah2-admin-web/src/components/nurseshift/NurseShiftDayPanel.vue -->
<template>
  <section class="h-fit overflow-hidden rounded-card border border-tone-neutral-border bg-white shadow-card">
    <div class="flex items-center justify-between gap-2 border-b border-tone-neutral-border px-4 py-3">
      <h3 class="text-lg font-semibold text-ink">{{ t('nurseShift.day_panel_title') }} {{ formattedDate }}</h3>
      <button
        type="button"
        @click="$emit('close')"
        class="inline-flex min-h-11 min-w-11 items-center justify-center rounded-control text-ink-muted hover:bg-tone-neutral-bg focus-visible:outline-2 focus-visible:outline-brand-600"
        :aria-label="t('ui.close')"
      >
        <XMarkIcon class="h-5 w-5" aria-hidden="true" />
      </button>
    </div>

    <p v-if="!canManage" class="px-4 pt-3 text-base text-ink-muted">{{ t('nurseShift.read_only_note') }}</p>

    <div class="space-y-5 p-4">
      <div v-for="st in SHIFT_TYPES" :key="st">
        <h4 class="mb-2 text-base font-semibold text-ink">{{ t(`nurseShift.shift.${st}`) }}</h4>

        <p v-if="shiftsFor(st).length === 0" class="mb-2 text-base text-ink-muted">
          {{ t('nurseShift.no_assignment') }}
        </p>
        <div v-for="s in shiftsFor(st)" :key="s.id" class="flex items-center justify-between gap-2 py-1 text-base text-ink">
          <span>{{ s.nurse_name }}</span>
          <AppButton v-if="canManage" variant="ghost" @click="$emit('remove', s.id)">
            {{ t('nurseShift.remove') }}
          </AppButton>
        </div>

        <div v-if="canManage" class="mt-2 flex flex-col gap-2 sm:flex-row">
          <select
            v-model="selectedNurseByShift[st]"
            :aria-label="t('nurseShift.select_nurse')"
            class="block min-h-11 w-full flex-1 rounded-control border border-tone-neutral-border bg-white px-3 text-base text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600"
          >
            <option value="" disabled>{{ t('nurseShift.select_nurse') }}</option>
            <option v-for="n in unassignedNursesFor(st)" :key="n.user_id" :value="n.user_id">
              {{ n.full_name }}{{ n.is_head_nurse ? ` (${t('nurseShift.head_nurse_badge')})` : '' }}
            </option>
          </select>
          <AppButton
            @click="handleAdd(st)"
            :disabled="!selectedNurseByShift[st]"
          >
            {{ t('nurseShift.add_nurse') }}
          </AppButton>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { reactive, computed } from 'vue';
import { useI18n } from 'vue-i18n';
import dayjs from 'dayjs';
import { XMarkIcon } from '@heroicons/vue/24/outline';
import { SHIFT_TYPES } from '@/stores/nurseShiftStore';
import { AppButton } from '@/components/ui';

const { t } = useI18n();

const props = defineProps({
  date: {
    type: String,
    required: true,
  },
  shifts: {
    type: Array,
    default: () => [],
  },
  availableNurses: {
    type: Array,
    default: () => [],
  },
  canManage: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(['close', 'add', 'remove']);

const selectedNurseByShift = reactive({ MATIN: '', APRES_MIDI: '', NUIT: '' });

const formattedDate = computed(() => dayjs(props.date).format('DD/MM/YYYY'));

function shiftsFor(shiftType) {
  return props.shifts.filter((s) => s.shift_type === shiftType);
}

function unassignedNursesFor(shiftType) {
  const assignedIds = new Set(shiftsFor(shiftType).map((s) => s.nurse_id));
  return props.availableNurses.filter((n) => !assignedIds.has(n.user_id));
}

function handleAdd(shiftType) {
  const nurseId = selectedNurseByShift[shiftType];
  emit('add', { shiftType, nurseId });
  // Reset optimiste : le parent recharge props.shifts apres l'ajout, la
  // liste sera re-filtree au prochain rendu (voir unassignedNursesFor).
  selectedNurseByShift[shiftType] = '';
}
</script>
