<template>
  <div class="fixed inset-0 bg-gray-900 bg-opacity-60 flex items-center justify-center z-50" @click.self="$emit('close')">
    <div class="bg-white rounded-2xl shadow-xl w-full max-w-md p-6 space-y-5">
      <div class="flex justify-between items-center">
        <h3 class="text-lg font-bold text-gray-800">{{ title }}</h3>
        <button @click="$emit('close')" class="text-gray-400 hover:text-gray-600">
          <span class="text-2xl">&times;</span>
        </button>
      </div>

      <div>
        <label class="block text-sm font-medium text-gray-700 mb-2">{{ t('export.format_label') }}</label>
        <div class="flex gap-2">
          <button v-for="f in formats" :key="f.value" @click="format = f.value"
                  :class="format === f.value ? 'bg-teal-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'"
                  class="px-4 py-2 rounded-lg text-sm font-medium transition">
            {{ f.label }}
          </button>
        </div>
      </div>

      <div>
        <label class="block text-sm font-medium text-gray-700 mb-2">{{ t('export.period_label') }}</label>
        <div class="flex gap-2 mb-3">
          <button v-for="p in presets" :key="p.value" @click="applyPreset(p.value)"
                  :class="activePreset === p.value ? 'bg-teal-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'"
                  class="px-3 py-1.5 rounded-lg text-xs font-bold transition">
            {{ p.label }}
          </button>
        </div>
        <div class="flex gap-2">
          <input type="date" v-model="dateFrom" @input="activePreset = null" class="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm" />
          <input type="date" v-model="dateTo" @input="activePreset = null" class="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm" />
        </div>
      </div>

      <div v-if="errorMessage" class="text-sm text-red-600">{{ errorMessage }}</div>

      <div class="flex justify-end gap-3 pt-2">
        <button @click="$emit('close')" class="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg text-sm">{{ t('export.cancel') }}</button>
        <button @click="handleExport" :disabled="isExporting"
                class="px-4 py-2 bg-teal-600 text-white rounded-lg text-sm font-medium hover:bg-teal-700 disabled:opacity-50">
          {{ isExporting ? t('export.exporting') : t('export.confirm') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useI18n } from 'vue-i18n';

const props = defineProps({
  title: { type: String, required: true },
  formats: { type: Array, required: true },
  onExport: { type: Function, required: true },
});
const emit = defineEmits(['close']);
const { t } = useI18n();

const format = ref(props.formats[0]?.value);
const dateFrom = ref('');
const dateTo = ref('');
const activePreset = ref(null);
const isExporting = ref(false);
const errorMessage = ref('');

const today = () => new Date().toISOString().slice(0, 10);
const daysAgo = (n) => {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return d.toISOString().slice(0, 10);
};

const presets = [
  { value: 'day', label: t('export.preset_day') },
  { value: 'week', label: t('export.preset_week') },
  { value: 'month', label: t('export.preset_month') },
];

const applyPreset = (preset) => {
  activePreset.value = preset;
  dateTo.value = today();
  if (preset === 'day') dateFrom.value = today();
  else if (preset === 'week') dateFrom.value = daysAgo(7);
  else if (preset === 'month') dateFrom.value = daysAgo(30);
};

const handleExport = async () => {
  isExporting.value = true;
  errorMessage.value = '';
  try {
    await props.onExport({ format: format.value, dateFrom: dateFrom.value || null, dateTo: dateTo.value || null });
    emit('close');
  } catch (err) {
    errorMessage.value = t('export.error');
  } finally {
    isExporting.value = false;
  }
};
</script>
