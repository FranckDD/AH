<!-- src/views/modules/stock/StockCount.vue -->
<!-- Comptage physique du stock de la pharmacie, A L'AVEUGLE. Zone Comptage (StockController seul) : le
     compteur saisit ce qu'il voit sans jamais voir la quantite du systeme ; le serveur ne revele le systeme et les
     ecarts qu'apres la validation (StockCountReveal). Zones Frequence et Historique : lecture pour tous les roles
     autorises (le reglage de la frequence reste a l'admin). L'admin ne compte pas : l'auteur d'une demande
     ne peut pas l'approuver, son comptage serait inapprouvable. -->
<template>
  <div class="grid w-full gap-6">
    <PageHeader :title="t('stockCount.title')" :subtitle="t('stockCount.subtitle')" />

    <div role="tablist" :aria-label="t('stockCount.tabs_label')" class="flex flex-col gap-1 border-b border-tone-neutral-border sm:flex-row sm:gap-2">
      <button v-for="tb in tabs" :key="tb" type="button" role="tab" :aria-selected="tab === tb" @click="tab = tb"
              :class="[
                tab === tb ? 'border-brand-600 text-brand-700 font-semibold' : 'border-transparent text-ink-muted hover:border-tone-neutral-border hover:text-ink',
                'flex min-h-11 items-center border-b-4 px-3 text-base focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600'
              ]">
        {{ t(`stockCount.tab_${tb}`) }}
      </button>
    </div>

    <!-- COMPTAGE (v-show : la saisie en cours survit a un changement d'onglet) -->
    <section v-if="canCount" v-show="tab === 'count'" class="grid gap-4" :aria-label="t('stockCount.tab_count')">
      <p v-if="pageError" role="alert" class="rounded-card border p-4 text-base" :class="toneClasses('danger')">{{ pageError }}</p>
      <p v-if="info" role="status" class="rounded-card border p-4 text-base" :class="toneClasses('warning')">{{ info }}</p>

      <AppCard v-if="!store.open && !store.result" :title="t('stockCount.start_title')">
        <p class="mb-4 text-base text-ink-muted">{{ t('stockCount.start_help') }}</p>
        <div class="flex flex-col gap-3 sm:flex-row sm:items-end">
          <FormField id="count-scope" :label="t('stockCount.scope_label')" v-slot="{ describedBy }">
            <select id="count-scope" v-model="scope" :aria-describedby="describedBy" :class="fieldClass">
              <option value="tous">{{ t('stockCount.scope_tous') }}</option>
              <option value="selection">{{ t('stockCount.scope_selection') }}</option>
            </select>
          </FormField>
          <AppButton variant="primary" :disabled="starting" :loading="starting" @click="handleStart">{{ t('stockCount.start') }}</AppButton>
        </div>
      </AppCard>

      <AppCard v-if="store.open" :title="t('stockCount.open_title', { id: store.open.id })"
               :subtitle="t('stockCount.open_subtitle', { date: formatLocalDateTime(store.open.started_at, locale) })">
        <template #actions>
          <AppButton variant="danger" :disabled="abandoning || submitting" :loading="abandoning" @click="handleAbandon">{{ t('stockCount.abandon') }}</AppButton>
        </template>
        <p class="mb-3 text-base text-ink-muted">{{ t('stockCount.count_help') }}</p>
        <FormField id="count-search" :label="t('stockCount.search_label')" v-slot="{ describedBy }">
          <input id="count-search" v-model="search" type="search" autocomplete="off" :aria-describedby="describedBy" :class="fieldClass" />
        </FormField>

        <form id="count-form" class="mt-4 grid gap-3" @submit.prevent="handleSubmit">
          <p v-if="!visibleProducts.length" class="text-base text-ink-muted">{{ t('stockCount.no_product') }}</p>
          <div v-for="p in visibleProducts" :key="p.id" class="grid gap-2 rounded-control border border-tone-neutral-border p-3">
            <div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <label :for="`qty-${p.id}`" class="text-base font-medium text-ink">{{ p.name }}</label>
              <div class="flex items-center gap-2">
                <input :id="`qty-${p.id}`" v-model="form[p.id].qty" @change="commitQty(p.id)" type="text" inputmode="numeric" autocomplete="off"
                       :placeholder="t('stockCount.qty_placeholder')" :aria-invalid="lineInvalid(p.id) ? 'true' : 'false'"
                       :aria-describedby="lineInvalid(p.id) ? `qty-${p.id}-error` : undefined" :class="[fieldClass, 'w-32 text-right']" />
                <AppButton variant="ghost" :aria-expanded="form[p.id].showObs ? 'true' : 'false'" :aria-controls="`obs-${p.id}`"
                           @click="form[p.id].showObs = !form[p.id].showObs">{{ t('stockCount.observation_toggle') }}</AppButton>
              </div>
            </div>
            <p v-if="lineInvalid(p.id)" :id="`qty-${p.id}-error`" role="alert" class="text-base text-tone-danger-text">{{ t('stockCount.qty_invalid') }}</p>
            <textarea v-if="form[p.id].showObs" :id="`obs-${p.id}`" v-model="form[p.id].observation" rows="2" maxlength="1000"
                      :aria-label="t('stockCount.observation_label', { name: p.name })" :class="[fieldClass, 'py-2']"></textarea>
          </div>

          <p role="status" class="text-base text-ink-muted">
            {{ lines === null ? t('stockCount.blocked_invalid') : t('stockCount.lines_typed', { n: lines.length, total: store.open.products.length }) }}
          </p>
          <div class="flex justify-end">
            <AppButton type="submit" variant="success" :disabled="!canSubmit" :loading="submitting">
              {{ submitting ? t('stockCount.submitting') : t('stockCount.submit') }}
            </AppButton>
          </div>
        </form>
      </AppCard>

      <template v-if="store.result">
        <p role="status" class="rounded-card border p-4 text-base" :class="toneClasses('success')">{{ t('stockCount.success', { id: store.result.id }) }}</p>
        <AppCard :title="t('stockCount.reveal_title')">
          <StockCountReveal v-if="store.result" :count="store.result" />
        </AppCard>
        <div class="flex justify-end">
          <AppButton variant="secondary" @click="store.clearResult()">{{ t('stockCount.new_count') }}</AppButton>
        </div>
      </template>
    </section>

    <StockCountFrequency v-if="tab === 'frequency'" />
    <StockCountHistory v-if="tab === 'history'" />
  </div>
</template>

<script setup>
import { reactive, ref, computed, watch, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { AppButton, AppCard, FormField, PageHeader } from '@/components/ui';
import StockCountReveal from '@/components/stock/StockCountReveal.vue';
import StockCountFrequency from '@/components/stock/StockCountFrequency.vue';
import StockCountHistory from '@/components/stock/StockCountHistory.vue';
import { toneClasses } from '@/design/tones';
import { useAuthStore } from '@/stores/auth';
import { useStockCountStore } from '@/stores/stockCountStore';
import { parseCount, buildLines, formatLocalDateTime, instantISO } from '@/utils/stockCount';
import { describeServerError } from '@/utils/serverError';

const { t, locale } = useI18n();
const authStore = useAuthStore();
const store = useStockCountStore();

const fieldClass = 'block w-full min-h-11 rounded-control border border-tone-neutral-border bg-white px-3 text-base text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600';

const canCount = computed(() => authStore.hasRole(['StockController']));
const tabs = computed(() => (canCount.value ? ['count', 'frequency', 'history'] : ['frequency', 'history']));
const tab = ref(canCount.value ? 'count' : 'frequency');
const myId = computed(() => authStore.user?.id ?? null);

const scope = ref('tous');
const search = ref('');
const pageError = ref('');
const info = ref('');
const starting = ref(false);
const submitting = ref(false);
const abandoning = ref(false);

// Saisie par produit : { [id]: { qty, observation, showObs, countedAt } }. Vide = produit non compte.
const form = reactive({});
watch(() => store.open?.id, () => {
  for (const k of Object.keys(form)) delete form[k];
  for (const p of store.open?.products || []) form[p.id] = { qty: '', observation: '', showObs: false, countedAt: null };
  search.value = '';
}, { immediate: true });

const visibleProducts = computed(() => {
  const q = search.value.trim().toLowerCase();
  return (store.open?.products || []).filter((p) => form[p.id] && (!q || (p.name || '').toLowerCase().includes(q)));
});
// Heure de comptage du produit : relevee quand la saisie est validee (sortie du champ ou Entree), mise a jour si
// la valeur est corrigee, effacee si le champ est vide. Le serveur calcule l'ecart a cet instant.
function commitQty(id) {
  const entry = form[id];
  if (!entry) return;
  const parsed = parseCount(entry.qty);
  entry.countedAt = parsed.blank || parsed.error ? null : instantISO();
}
const lineInvalid = (id) => !!parseCount(form[id]?.qty).error;
const lines = computed(() => buildLines(store.open?.products, form));
const canSubmit = computed(() => !submitting.value && lines.value !== null && lines.value.length > 0);

const errorText = (err, fallback) => (err?.response ? (describeServerError(err, '') || t(fallback)) : t('stockCount.network_error'));

// Reprise d'un comptage deja ouvert par cet utilisateur. Renvoie vrai si un comptage a ete repris.
async function resumeOpen() {
  try {
    return !!(await store.findOpen());
  } catch (err) {
    console.error('Reprise du comptage en cours impossible:', err);
    return false;
  }
}

async function handleStart() {
  if (starting.value) return;
  starting.value = true;
  pageError.value = '';
  info.value = '';
  try {
    await store.start(scope.value);
  } catch (err) {
    if (err?.response?.status === 409 && await resumeOpen()) {
      info.value = t('stockCount.resumed', { detail: describeServerError(err, '') });
    } else {
      pageError.value = errorText(err, 'stockCount.start_error');
    }
  } finally {
    starting.value = false;
  }
}

async function handleSubmit() {
  if (submitting.value) return;
  if (!canSubmit.value) return;
  submitting.value = true;
  pageError.value = '';
  info.value = '';
  try {
    await store.submit(lines.value);
  } catch (err) {
    pageError.value = errorText(err, 'stockCount.submit_error');
    if (err?.response?.status === 409) await recoverFromConflict();
  } finally {
    submitting.value = false;
  }
}

async function handleAbandon() {
  if (abandoning.value) return;
  if (!window.confirm(t('stockCount.abandon_confirm'))) return;
  abandoning.value = true;
  pageError.value = '';
  info.value = '';
  try {
    await store.abandon();
    info.value = t('stockCount.abandoned');
  } catch (err) {
    pageError.value = errorText(err, 'stockCount.abandon_error');
    if (err?.response?.status === 409) await recoverFromConflict();
  } finally {
    abandoning.value = false;
  }
}

// 409 a la validation ou a l'abandon : le comptage affiche n'est plus en cours. On l'oublie (le message du
// serveur reste affiche) et on reprend un eventuel autre comptage ouvert, sans recharger la page.
async function recoverFromConflict() {
  store.forgetOpen();
  await resumeOpen();
}

// Poste partage : l'etat du store appartient a un utilisateur ; tout est jete si l'utilisateur change.
function syncOwner() {
  store.ensureOwner(myId.value);
  if (!canCount.value && tab.value === 'count') tab.value = 'frequency';
  pageError.value = '';
  info.value = '';
  store.loadFrequency();
  if (canCount.value && !store.open) resumeOpen();
}
watch(myId, syncOwner);
onMounted(syncOwner);
</script>
