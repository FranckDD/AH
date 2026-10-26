<!-- src/views/modules/caisse/DiscountReview.vue -->
<template>
  <div class="grid w-full max-w-3xl gap-4">
    <PageHeader :title="$t('discount_review.title')" />

    <p v-if="pending.length === 0" role="status" class="rounded-card border border-tone-neutral-border bg-white p-8 text-center text-base text-ink-muted">
      {{ $t('discount_review.empty') }}
    </p>

    <AppCard v-for="req in pending" :key="req.id" :title="formatCurrency(req.original_amount)" :subtitle="formatDate(req.created_at)">
      <div class="grid gap-4">
        <div>
          <p class="text-base text-ink">
            <span class="font-medium">{{ req.patient_label || $t('discount_review.unknown_patient') }}</span>
            <span v-if="req.items_summary" class="text-ink-muted"> : {{ req.items_summary }}</span>
          </p>
          <p class="text-base text-ink-muted">{{ $t('discount_review.requested_by', { name: req.requested_by_name || '?' }) }}</p>
        </div>

        <div class="grid gap-1.5">
          <span class="text-base font-medium text-ink">{{ $t('discountReviewScreens.percent_label') }}</span>
          <div class="grid grid-cols-2 gap-2 sm:grid-cols-4" role="group" :aria-label="$t('discountReviewScreens.percent_group')">
            <AppButton
              v-for="pct in [10, 20, 50, 100]"
              :key="pct"
              :variant="selectedPercent[req.id] === pct ? 'primary' : 'secondary'"
              :aria-pressed="selectedPercent[req.id] === pct"
              @click="selectedPercent[req.id] = pct"
            >{{ pct }}%</AppButton>
          </div>
        </div>

        <FormField :id="`review-deadline-${req.id}`" :label="$t('discount_review.echelonne_deadline')" v-slot="{ describedBy }">
          <input :id="`review-deadline-${req.id}`" type="date" v-model="selectedDeadline[req.id]" :aria-describedby="describedBy" :class="fieldClass" />
        </FormField>

        <FormField :id="`review-password-${req.id}`" :label="$t('discount_review.password_confirm')" :help="$t('discountReviewScreens.password_help')" v-slot="{ describedBy }">
          <input :id="`review-password-${req.id}`" type="password" autocomplete="current-password" v-model="passwordInput[req.id]" :aria-describedby="describedBy" :class="fieldClass" />
        </FormField>

        <p v-if="errorFor[req.id]" role="alert" class="rounded-control border p-3 text-base" :class="toneClasses('danger')">{{ errorFor[req.id] }}</p>

        <div class="grid gap-2 sm:grid-cols-2">
          <AppButton variant="success" @click="submitDecision(req, false)">{{ $t('discount_review.approve') }}</AppButton>
          <AppButton variant="danger" :disabled="hasApprovalChoice(req)" @click="submitDecision(req, true)">{{ $t('discount_review.refuse') }}</AppButton>
        </div>
        <div v-if="hasApprovalChoice(req)" class="flex flex-wrap items-center gap-3">
          <p class="text-base text-ink-muted">{{ $t('discountReviewScreens.refuse_needs_clear') }}</p>
          <AppButton variant="ghost" @click="clearChoice(req)">{{ $t('discountReviewScreens.clear_choice') }}</AppButton>
        </div>
      </div>
    </AppCard>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import api from '@/services/api';
import { AppButton, AppCard, PageHeader, FormField } from '@/components/ui';
import { toneClasses } from '@/design/tones';

// Style commun des champs : zone tactile >= 44 px, focus visible.
const fieldClass = 'block w-full min-h-11 lg:min-h-10 rounded-control border border-tone-neutral-border bg-white px-3 text-base text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600';

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

// Un refus n'accorde ni pourcentage ni echeance (le serveur refuse cette combinaison, 422) : on bloque le bouton
// plutot que d'ignorer en silence le choix fait a l'ecran.
const hasApprovalChoice = (req) => !!(selectedPercent[req.id] || selectedDeadline[req.id]);
const clearChoice = (req) => { selectedPercent[req.id] = null; selectedDeadline[req.id] = ''; };

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
    errorFor[req.id] = describeServerError(err, 'Erreur lors de la décision.');
  }
};

onMounted(fetchPending);
</script>
