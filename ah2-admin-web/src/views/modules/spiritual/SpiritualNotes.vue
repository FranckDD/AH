<!-- Notes du conseiller spirituel : liste (plus recente en premier), lecture pour promoteur et admin,
     ecriture pour le conseiller spirituel sur ses propres notes seulement (can_edit). -->
<template>
  <div class="grid w-full gap-6">
    <PageHeader :title="t('spiritualNotes.title')" :subtitle="t('spiritualNotes.subtitle')" />
    <div v-if="canWrite" class="flex">
      <AppButton @click="openNew">{{ t('spiritualNotes.new_button') }}</AppButton>
    </div>

    <p v-if="notice" role="status" class="rounded-card border p-3 text-base" :class="toneClasses('success')">{{ notice }}</p>
    <p v-if="pageError" role="alert" class="rounded-card border p-4 text-base" :class="toneClasses('danger')">{{ pageError }}</p>
    <p v-if="loading && !notes.length" role="status" class="p-10 text-center text-base text-ink-muted">{{ t('spiritualNotes.loading') }}</p>
    <p v-else-if="!loading && !pageError && !notes.length" class="p-10 text-center text-base text-ink-muted">{{ t('spiritualNotes.empty') }}</p>

    <ul v-if="notes.length" class="grid gap-4">
      <li v-for="(n, i) in notes" :key="n.id"
          class="grid gap-3 rounded-card border bg-white p-4 shadow-card"
          :class="isLast(i) ? 'border-2 border-brand-600' : 'border-tone-neutral-border'">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <div class="flex flex-wrap items-center gap-3">
            <span class="text-lg font-semibold text-ink">{{ formatDateDMY(n.meeting_date) }}</span>
            <span class="text-base text-ink-muted">{{ n.author_name }}</span>
            <span v-if="isLast(i)" class="rounded-full border px-3 py-0.5 text-sm font-semibold" :class="toneClasses('info')">{{ t('spiritualNotes.last_note') }}</span>
          </div>
          <div v-if="canWrite && n.can_edit" class="flex gap-2">
            <AppButton variant="secondary" @click="openEdit(n)">{{ t('spiritualNotes.edit') }}</AppButton>
            <AppButton variant="danger" @click="askDelete(n)">{{ t('spiritualNotes.delete') }}</AppButton>
          </div>
        </div>
        <ul v-if="chips(n).length || n.no_one_spoke" class="flex flex-wrap gap-2">
          <li v-for="c in chips(n)" :key="c" class="rounded-full border px-3 py-1 text-sm font-medium" :class="toneClasses('neutral')">{{ c }}</li>
          <li v-if="n.no_one_spoke" class="rounded-full border px-3 py-1 text-sm font-medium" :class="toneClasses('warning')">{{ t('spiritualNotes.no_one_spoke') }}</li>
        </ul>
        <p v-if="n.content" class="whitespace-pre-wrap break-words text-base text-ink">{{ n.content }}</p>
      </li>
    </ul>

    <div v-if="totalPages > 1" class="flex items-center justify-between gap-3 rounded-card border border-tone-neutral-border bg-white p-3">
      <p class="text-base text-ink">{{ t('common.page') }} {{ page }} / {{ totalPages }}</p>
      <div class="flex gap-2">
        <AppButton variant="secondary" :icon="ChevronLeftIcon" :aria-label="t('spiritualNotes.prev_page')" :disabled="page <= 1" @click="goTo(page - 1)" />
        <AppButton variant="secondary" :icon="ChevronRightIcon" :aria-label="t('spiritualNotes.next_page')" :disabled="page >= totalPages" @click="goTo(page + 1)" />
      </div>
    </div>

    <SpiritualNoteForm v-if="showForm" :note="editing" @close="closeForm" @saved="onSaved" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { ChevronLeftIcon, ChevronRightIcon } from '@heroicons/vue/24/outline';
import { AppButton, PageHeader } from '@/components/ui';
import SpiritualNoteForm from '@/components/spiritual/SpiritualNoteForm.vue';
import { toneClasses } from '@/design/tones';
import { useAuthStore } from '@/stores/auth';
import { formatDateDMY } from '@/utils/localDate';
import { describeServerError } from '@/utils/serverError';
import { isNetworkUploadError } from '@/utils/connectionStatus';
import { SpiritualNoteGateway } from '@/services/SpiritualNoteGateway';
import { CHECK_FIELDS } from '@/utils/spiritualNote';

const { t } = useI18n();
const authStore = useAuthStore();
// Seul le conseiller spirituel ecrit ; promoteur et admin lisent.
const canWrite = computed(() => authStore.hasRole(['SpiritualCounsellor']));

const notes = ref([]);
const page = ref(1);
const totalPages = ref(1);
const loading = ref(false);
const pageError = ref('');
const notice = ref('');
const deleting = ref(false);
const showForm = ref(false);
const editing = ref(null);

// La note la plus recente (premiere de la page 1, tri serveur par date decroissante) est mise en avant.
const isLast = (i) => page.value === 1 && i === 0;

function chips(n) {
  return CHECK_FIELDS.filter((f) => n[f]).map((f) => {
    const label = t('spiritualNotes.item_' + f);
    return f === 'verse_read' && n.verse_reference ? `${label} (${n.verse_reference})` : label;
  });
}

function readError(e, fallbackKey) {
  return isNetworkUploadError(e, typeof navigator !== 'undefined' ? navigator.onLine : undefined)
    ? t('spiritualNotes.err_network_read')
    : describeServerError(e, t(fallbackKey));
}

async function load() {
  loading.value = true;
  pageError.value = '';
  try {
    const r = await SpiritualNoteGateway.list({ page: page.value, perPage: 20 });
    notes.value = r?.data || [];
    totalPages.value = r?.total_pages || 1;
    // Page devenue vide (derniere note supprimee) : revenir a la derniere page existante.
    if (!notes.value.length && page.value > 1) {
      page.value = Math.max(1, totalPages.value);
      await load();
      return;
    }
  } catch (e) {
    pageError.value = readError(e, 'spiritualNotes.err_load');
  } finally {
    loading.value = false;
  }
}

function goTo(p) {
  if (p < 1 || p > totalPages.value) return;
  page.value = p;
  load();
}

function openNew() { if (!canWrite.value) return; editing.value = null; showForm.value = true; }
function openEdit(n) { if (!canWrite.value || !n.can_edit) return; editing.value = n; showForm.value = true; }
function closeForm() { showForm.value = false; editing.value = null; }

async function onSaved() {
  closeForm();
  notice.value = t('spiritualNotes.saved');
  await load();
}

async function askDelete(n) {
  if (deleting.value || !canWrite.value || !n.can_edit) return;
  if (!window.confirm(t('spiritualNotes.confirm_delete', { date: formatDateDMY(n.meeting_date) }))) return;
  deleting.value = true;
  notice.value = '';
  pageError.value = '';
  try {
    await SpiritualNoteGateway.remove(n.id);
    notice.value = t('spiritualNotes.deleted');
    await load();
  } catch (e) {
    notice.value = '';
    pageError.value = readError(e, 'spiritualNotes.err_delete');
  } finally {
    deleting.value = false;
  }
}

onMounted(load);
</script>
