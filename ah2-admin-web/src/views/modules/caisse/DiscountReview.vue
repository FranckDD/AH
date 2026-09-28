<!-- src/views/modules/caisse/DiscountReview.vue -->
<template>
  <div class="max-w-3xl mx-auto p-6">
    <h2 class="text-xl font-bold text-gray-800 mb-4">{{ $t('discount_review.title') }}</h2>

    <div v-if="pending.length === 0" class="text-center text-gray-400 py-12">
      {{ $t('discount_review.empty') }}
    </div>

    <div v-for="req in pending" :key="req.id" class="bg-white rounded-xl shadow-sm border border-gray-200 p-5 mb-4">
      <div class="flex justify-between items-center mb-1">
        <span class="font-bold text-gray-800">{{ formatCurrency(req.original_amount) }}</span>
        <span class="text-xs text-gray-400">{{ formatDate(req.created_at) }}</span>
      </div>
      <div class="text-sm text-gray-600 mb-1">
        <span class="font-medium">{{ req.patient_label || $t('discount_review.unknown_patient') }}</span>
        <span v-if="req.items_summary" class="text-gray-400"> — {{ req.items_summary }}</span>
      </div>
      <div class="text-xs text-gray-500 mb-3">{{ $t('discount_review.requested_by', { name: req.requested_by_name || '?' }) }}</div>

      <div class="grid grid-cols-3 gap-2 mb-3">
        <button
          v-for="pct in [10, 20, 50, 100]"
          :key="pct"
          @click="selectedPercent[req.id] = pct"
          :class="selectedPercent[req.id] === pct ? 'bg-indigo-600 text-white' : 'bg-gray-100 text-gray-700'"
          class="py-2 rounded-lg text-sm font-medium"
        >{{ pct }}%</button>
      </div>

      <div class="mb-3">
        <label class="block text-xs text-gray-500 mb-1">{{ $t('discount_review.echelonne_deadline') }}</label>
        <input type="date" v-model="selectedDeadline[req.id]" class="border border-gray-300 rounded-lg px-3 py-1.5 text-sm" />
      </div>

      <div class="mb-3">
        <label class="block text-xs text-gray-500 mb-1">{{ $t('discount_review.password_confirm') }}</label>
        <input type="password" v-model="passwordInput[req.id]" class="border border-gray-300 rounded-lg px-3 py-1.5 text-sm w-full" />
      </div>

      <div v-if="errorFor[req.id]" class="text-xs text-red-600 mb-2">{{ errorFor[req.id] }}</div>

      <div class="flex gap-2">
        <button @click="submitDecision(req, false)" class="flex-1 bg-green-600 text-white rounded-lg py-2 font-medium hover:bg-green-700">
          {{ $t('discount_review.approve') }}
        </button>
        <button @click="submitDecision(req, true)" class="flex-1 bg-red-500 text-white rounded-lg py-2 font-medium hover:bg-red-600">
          {{ $t('discount_review.refuse') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import api from '@/services/api';

const pending = ref([]);
const selectedPercent = reactive({});
const selectedDeadline = reactive({});
const passwordInput = reactive({});
const errorFor = reactive({});

const formatCurrency = (v) => new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'XAF' }).format(v || 0).replace('XOF', 'FCFA');
const formatDate = (iso) => iso ? new Date(iso).toLocaleString('fr-FR') : '';

const fetchPending = async () => {
  const res = await api.get('/discount-requests/pending');
  pending.value = res.data || [];
};

const submitDecision = async (req, refuse) => {
  errorFor[req.id] = '';
  try {
    await api.post(`/discount-requests/${req.id}/decide`, {
      password: passwordInput[req.id] || '',
      refuse,
      decision_percent: refuse ? null : (selectedPercent[req.id] || null),
      decision_echelonne_deadline: refuse ? null : (selectedDeadline[req.id] || null),
    });
    pending.value = pending.value.filter((r) => r.id !== req.id);
  } catch (err) {
    errorFor[req.id] = err.response?.data?.detail || 'Erreur lors de la décision.';
  }
};

onMounted(fetchPending);
</script>
