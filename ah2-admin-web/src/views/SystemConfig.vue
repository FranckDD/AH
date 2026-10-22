<template>
  <div class="grid w-full max-w-7xl gap-6 pb-12">

    <PageHeader :title="t('config.title')" :subtitle="t('config.subtitle')" />

    <!-- Identite de la structure et en-tete des documents -->
    <section class="rounded-card border border-tone-neutral-border bg-white shadow-card">
      <h2>
        <button type="button" :aria-expanded="openSections.structure" aria-controls="cfg-structure"
                :class="accordionButtonClass" @click="openSections.structure = !openSections.structure">
          <span class="flex min-w-0 items-center gap-3">
            <BuildingOfficeIcon class="h-6 w-6 shrink-0 text-brand-700" aria-hidden="true" />
            <span class="min-w-0">
              <span class="block text-lg font-semibold text-ink">{{ t('configScreens.structure_title') }}</span>
              <span class="block text-base font-normal text-ink-muted">{{ t('configScreens.structure_help') }}</span>
            </span>
          </span>
          <ChevronDownIcon :class="['h-6 w-6 shrink-0 text-ink-muted transition-transform', openSections.structure ? 'rotate-180' : '']" aria-hidden="true" />
        </button>
      </h2>

      <div v-show="openSections.structure" id="cfg-structure" class="border-t border-tone-neutral-border p-4 md:p-5">
        <form @submit.prevent="saveStructureConfig" class="grid gap-6">
          <div class="grid gap-6 lg:grid-cols-[18rem_1fr]">

            <div class="grid content-start gap-4">
              <div class="grid gap-2 rounded-card border border-dashed border-tone-neutral-border bg-tone-neutral-bg p-4">
                <img
                  :src="previewLogo || resolveAssetUrl(configStore.structureInfo.logo_url) || '/placeholder-logo.png'"
                  class="mx-auto h-36 w-36 rounded-control border border-tone-neutral-border bg-white object-contain p-2"
                  :alt="t('configScreens.logo_label')"
                />
                <FormField id="cfg-logo" :label="t('configScreens.logo_label')" :help="t('configScreens.logo_help')" v-slot="{ describedBy }">
                  <input id="cfg-logo" type="file" accept="image/*" @change="handleLogoUpload" :aria-describedby="describedBy" :class="fileClass" />
                </FormField>
              </div>

              <div class="grid gap-2 rounded-card border border-dashed border-tone-neutral-border bg-tone-neutral-bg p-4">
                <img
                  :src="previewTicketLogo || resolveAssetUrl(configStore.structureInfo.ticket_logo_url) || '/placeholder-logo.png'"
                  class="mx-auto h-36 w-36 rounded-control border border-tone-neutral-border bg-white object-contain p-2"
                  :alt="t('configScreens.ticket_logo_label')"
                />
                <FormField id="cfg-ticket-logo" :label="t('configScreens.ticket_logo_label')" :help="t('configScreens.ticket_logo_help')" v-slot="{ describedBy }">
                  <input id="cfg-ticket-logo" type="file" accept="image/*" @change="handleTicketLogoUpload" :aria-describedby="describedBy" :class="fileClass" />
                </FormField>
              </div>
            </div>

            <div class="grid content-start gap-4">
              <div class="grid gap-3 rounded-card border border-tone-neutral-border bg-tone-neutral-bg p-4">
                <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <div class="min-w-0">
                    <p class="text-base font-medium text-ink">{{ t('configScreens.token_label') }}</p>
                    <p class="break-all font-mono text-base text-ink-muted">{{ configStore.ticketPrintToken || 'Non généré' }}</p>
                  </div>
                  <AppButton variant="secondary" :disabled="!confirmRegenerate" @click="handleRegenerateToken">{{ t('configScreens.token_regenerate') }}</AppButton>
                </div>
                <p class="rounded-control border p-3 text-base" :class="toneClasses('warning')">{{ t('configScreens.token_warning') }}</p>
                <label class="flex min-h-11 items-center gap-3 text-base font-medium text-ink">
                  <input type="checkbox" v-model="confirmRegenerate" class="h-5 w-5 shrink-0 accent-brand-600" />
                  <span>{{ t('configScreens.token_confirm_check') }}</span>
                </label>
              </div>

              <div class="grid gap-4 md:grid-cols-2">
                <div class="md:col-span-2">
                  <FormField id="cfg-name" :label="t('configScreens.name')" required v-slot="{ describedBy }">
                    <input id="cfg-name" v-model="formStructure.name" type="text" :placeholder="t('configScreens.name_placeholder')" required :aria-describedby="describedBy" :class="fieldClass" />
                  </FormField>
                </div>
                <div class="md:col-span-2">
                  <FormField id="cfg-slogan" :label="t('configScreens.slogan')" v-slot="{ describedBy }">
                    <input id="cfg-slogan" v-model="formStructure.slogan" type="text" :placeholder="t('configScreens.slogan_placeholder')" :aria-describedby="describedBy" :class="fieldClass" />
                  </FormField>
                </div>
                <FormField id="cfg-phone" :label="t('configScreens.phone')" v-slot="{ describedBy }">
                  <input id="cfg-phone" v-model="formStructure.phone" type="tel" :aria-describedby="describedBy" :class="fieldClass" />
                </FormField>
                <FormField id="cfg-phone2" :label="t('configScreens.phone2')" v-slot="{ describedBy }">
                  <input id="cfg-phone2" v-model="formStructure.phone2" type="tel" :aria-describedby="describedBy" :class="fieldClass" />
                </FormField>
                <FormField id="cfg-email" :label="t('configScreens.email')" v-slot="{ describedBy }">
                  <input id="cfg-email" v-model="formStructure.email" type="email" :aria-describedby="describedBy" :class="fieldClass" />
                </FormField>
                <FormField id="cfg-website" :label="t('configScreens.website')" v-slot="{ describedBy }">
                  <input id="cfg-website" v-model="formStructure.website" type="text" :placeholder="t('configScreens.website_placeholder')" :aria-describedby="describedBy" :class="fieldClass" />
                </FormField>
                <div class="md:col-span-2">
                  <FormField id="cfg-address" :label="t('configScreens.address')" v-slot="{ describedBy }">
                    <input id="cfg-address" v-model="formStructure.address" type="text" :placeholder="t('configScreens.address_placeholder')" :aria-describedby="describedBy" :class="fieldClass" />
                  </FormField>
                </div>
                <FormField id="cfg-city" :label="t('configScreens.city')" v-slot="{ describedBy }">
                  <input id="cfg-city" v-model="formStructure.city" type="text" :aria-describedby="describedBy" :class="fieldClass" />
                </FormField>
                <FormField id="cfg-pobox" :label="t('configScreens.po_box')" v-slot="{ describedBy }">
                  <input id="cfg-pobox" v-model="formStructure.po_box" type="text" :aria-describedby="describedBy" :class="fieldClass" />
                </FormField>

                <h3 class="border-t border-tone-neutral-border pt-4 text-base font-semibold text-ink md:col-span-2">{{ t('configScreens.legal_title') }}</h3>

                <FormField id="cfg-niu" :label="t('configScreens.niu')" v-slot="{ describedBy }">
                  <input id="cfg-niu" v-model="formStructure.niu" type="text" :aria-describedby="describedBy" :class="fieldClass" />
                </FormField>
                <FormField id="cfg-rccm" :label="t('configScreens.rccm')" v-slot="{ describedBy }">
                  <input id="cfg-rccm" v-model="formStructure.rccm" type="text" :aria-describedby="describedBy" :class="fieldClass" />
                </FormField>
              </div>
            </div>
          </div>

          <div class="flex justify-end border-t border-tone-neutral-border pt-4">
            <AppButton type="submit" :icon="CheckCircleIcon" :disabled="isSaving" :loading="isSaving">
              {{ isSaving ? t('configScreens.saving') : t('configScreens.save_structure') }}
            </AppButton>
          </div>
        </form>
      </div>
    </section>

    <!-- Tarification des examens -->
    <section class="rounded-card border border-tone-neutral-border bg-white shadow-card">
      <h2>
        <button type="button" :aria-expanded="openSections.exams" aria-controls="cfg-exams"
                :class="accordionButtonClass" @click="openSections.exams = !openSections.exams">
          <span class="text-lg font-semibold text-ink">{{ t('config.exams_title') }}</span>
          <ChevronDownIcon :class="['h-6 w-6 shrink-0 text-ink-muted transition-transform', openSections.exams ? 'rotate-180' : '']" aria-hidden="true" />
        </button>
      </h2>

      <div v-show="openSections.exams" id="cfg-exams" class="grid gap-4 border-t border-tone-neutral-border p-4 md:p-5">
        <div class="grid gap-3 sm:grid-cols-[1fr_auto] sm:items-end">
          <FormField id="cfg-exam-search" :label="t('configScreens.search_label')" v-slot="{ describedBy }">
            <input id="cfg-exam-search" v-model="searchQuery" type="search" autocomplete="off"
                   :placeholder="t('common.search_placeholder') || 'Rechercher...'" :aria-describedby="describedBy" :class="fieldClass" />
          </FormField>
          <AppButton :icon="PlusCircleIcon" @click="openExamModal(null)">{{ t('config.add_exam') }}</AppButton>
        </div>

        <ResponsiveTable
          :columns="examColumns"
          :rows="filteredExamens"
          row-key="id"
          :loading="configStore.isLoading && configStore.examens.length === 0"
          :empty-title="`${t('users.table.no_results')} &quot;${searchQuery}&quot;`"
          :empty-message="' '"
          striped
        >
          <template #cell-code="{ row: exam }"><span class="font-mono">{{ exam.code }}</span></template>
          <template #cell-name="{ row: exam }"><span class="font-medium">{{ exam.nom }}</span></template>
          <template #cell-category="{ row: exam }"><StatusBadge tone="info" :label="String(exam.categorie ?? '-')" /></template>
          <template #cell-price="{ row: exam }"><span class="font-bold text-tone-success-text">{{ formatPrice(exam.prix) }}</span></template>
          <template #actions="{ row: exam }">
            <AppButton variant="secondary" :icon="PencilSquareIcon" @click="openExamModal(exam)">{{ t('config.edit') }}</AppButton>
            <AppButton variant="danger" :icon="TrashIcon" @click="handleDeleteExam(exam.id)">{{ t('common.delete') }}</AppButton>
          </template>
        </ResponsiveTable>
      </div>
    </section>

    <div class="grid items-start gap-6 md:grid-cols-2">

      <!-- Types de livres de prieres -->
      <section class="rounded-card border border-tone-neutral-border bg-white shadow-card">
        <h2>
          <button type="button" :aria-expanded="openSections.prayers" aria-controls="cfg-prayers"
                  :class="accordionButtonClass" @click="openSections.prayers = !openSections.prayers">
            <span class="min-w-0">
              <span class="block text-lg font-semibold text-ink">{{ t('config.prayers_title') }}</span>
              <span class="block text-base font-normal text-ink-muted">{{ t('config.prayers_subtitle') }}</span>
            </span>
            <ChevronDownIcon :class="['h-6 w-6 shrink-0 text-ink-muted transition-transform', openSections.prayers ? 'rotate-180' : '']" aria-hidden="true" />
          </button>
        </h2>
        <div v-show="openSections.prayers" id="cfg-prayers" class="border-t border-tone-neutral-border p-4">
          <ResponsiveTable :columns="prayerColumns" :rows="configStore.prayerBookTypes" row-key="type_code" :empty-title="t('configScreens.no_results')" :empty-message="' '" striped>
            <template #cell-type_code="{ row: type }"><span class="font-mono">{{ type.type_code }}</span></template>
            <template #cell-label="{ row: type }"><span class="font-medium">{{ type.label }}</span></template>
          </ResponsiveTable>
        </div>
      </section>

      <!-- Parametres generaux et maintenance -->
      <section class="rounded-card border border-tone-neutral-border bg-white shadow-card">
        <h2>
          <button type="button" :aria-expanded="openSections.general" aria-controls="cfg-general"
                  :class="accordionButtonClass" @click="openSections.general = !openSections.general">
            <span class="min-w-0">
              <span class="block text-lg font-semibold text-ink">{{ t('config.general_title') }}</span>
              <span class="block text-base font-normal text-ink-muted">{{ t('config.general_subtitle') }}</span>
            </span>
            <ChevronDownIcon :class="['h-6 w-6 shrink-0 text-ink-muted transition-transform', openSections.general ? 'rotate-180' : '']" aria-hidden="true" />
          </button>
        </h2>

        <div v-show="openSections.general" id="cfg-general" class="grid gap-4 border-t border-tone-neutral-border p-4">
          <div class="grid gap-3 rounded-card border border-tone-neutral-border p-4 sm:grid-cols-[1fr_auto] sm:items-center">
            <div class="min-w-0">
              <h3 class="flex items-center gap-2 text-base font-semibold text-ink">
                <ArrowDownTrayIcon class="h-5 w-5 shrink-0 text-brand-700" aria-hidden="true" />
                {{ t('config.db_backup') }}
              </h3>
              <p class="text-base text-ink-muted">{{ t('config.db_backup_subtitle') }}</p>
            </div>
            <AppButton @click="handleBackup" :disabled="isBackupRunning" :loading="isBackupRunning">
              {{ isBackupRunning ? t('common.loading') : t('config.launch_backup') }}
            </AppButton>
          </div>

          <div class="grid gap-3 rounded-card border border-tone-neutral-border p-4 sm:grid-cols-[1fr_auto] sm:items-center">
            <div class="min-w-0">
              <h3 class="flex flex-wrap items-center gap-2 text-base font-semibold text-ink">
                <WrenchScrewdriverIcon class="h-5 w-5 shrink-0 text-brand-700" aria-hidden="true" />
                {{ t('config.maintenance_mode') }}
                <StatusBadge :tone="isMaintenanceMode ? 'danger' : 'success'" :label="isMaintenanceMode ? t('configScreens.maintenance_state_on') : t('configScreens.maintenance_state_off')" />
              </h3>
              <p class="text-base" :class="isMaintenanceMode ? 'font-bold text-tone-danger-text' : 'text-ink-muted'">
                {{ isMaintenanceMode ? t('config.maintenance_active') : t('config.maintenance_mode_subtitle') }}
              </p>
            </div>
            <AppButton :variant="isMaintenanceMode ? 'danger' : 'primary'" @click="toggleMaintenanceMode">
              {{ isMaintenanceMode ? t('config.deactivate') : t('config.activate') }}
            </AppButton>
          </div>
        </div>
      </section>
    </div>

    <ExamFormModal
      v-if="showExamModal"
      :examen="selectedExam"
      @close="showExamModal = false"
      @saved="onExamSaved"
    />

  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, reactive } from 'vue';
import { useConfigStore } from '@/stores/configStore';
import { resolveAssetUrl } from '@/services/api';
import { useI18n } from 'vue-i18n';
import { 
  PlusCircleIcon, 
  PencilSquareIcon, 
  MagnifyingGlassIcon,
  WrenchScrewdriverIcon, 
  ArrowDownTrayIcon,
  TrashIcon,
  BuildingOfficeIcon,
  PhotoIcon,
  CheckCircleIcon,
  ChevronDownIcon // 🟢 Ajout de l'icône Chevron
} from '@heroicons/vue/24/outline';

import ExamFormModal from '@/components/config/ExamFormModal.vue';
import { AppButton, PageHeader, FormField, StatusBadge, ResponsiveTable } from '@/components/ui';
import { toneClasses } from '@/design/tones';

const { t } = useI18n();
const configStore = useConfigStore();

// Colonnes des tableaux (cartes empilees sous lg) et classes communes des champs et des sections repliables.
const examColumns = computed(() => [
    { key: 'code', label: t('config.table_code') },
    { key: 'name', label: t('config.table_name') },
    { key: 'category', label: t('config.table_category') },
    { key: 'price', label: t('config.table_price'), align: 'right' },
]);
const prayerColumns = computed(() => [
    { key: 'type_code', label: t('config.table_type_code') },
    { key: 'label', label: t('config.table_label') },
]);
const fieldClass = 'block w-full min-h-11 lg:min-h-10 rounded-control border border-tone-neutral-border bg-white px-3 text-base text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600';
const fileClass = 'block w-full text-base text-ink file:mr-3 file:min-h-11 file:cursor-pointer file:rounded-control file:border file:border-brand-600 file:bg-white file:px-4 file:text-base file:font-medium file:text-brand-700 hover:file:bg-brand-50 lg:file:min-h-10';
const accordionButtonClass = 'flex w-full min-h-11 items-center justify-between gap-3 rounded-card px-4 py-3 text-left hover:bg-tone-neutral-bg focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600 md:px-5';

// --- 🟢 ÉTAT POUR LES ACCORDÉONS ---
// Par défaut, la structure et les examens sont ouverts, le reste fermé pour alléger.
const openSections = reactive({
    structure: true,
    exams: true,
    prayers: false,
    general: false
});


// --- ETAT CONFIGURATION STRUCTURE ---
const formStructure = ref({
    name: '', slogan: '', phone: '', phone2: '', email: '', website: '',
    address: '', city: '', po_box: '', niu: '', rccm: ''
});
const logoFile = ref(null);
const previewLogo = ref(null);
const isSaving = ref(false);
const ticketLogoFile = ref(null);
const previewTicketLogo = ref(null);

// --- ETATS CONFIGURATION GENERALE ---
const showExamModal = ref(false);
const selectedExam = ref(null);
const searchQuery = ref('');
const isMaintenanceMode = ref(false);
const isBackupRunning = ref(false);


// --- CYCLE DE VIE ---
onMounted(async () => {
    await configStore.fetchStructureInfo();
    await configStore.fetchTicketPrintToken();
    configStore.fetchExamens();
    configStore.fetchPrayerBooks();
});

watch(() => configStore.structureInfo, (info) => {
    if (info) { formStructure.value = { ...formStructure.value, ...info }; }
}, { deep: true });


// --- LOGIQUE STRUCTURE & LOGO ---
const handleLogoUpload = (event) => {
    const file = event.target.files[0];
    if (file) {
        logoFile.value = file;
        previewLogo.value = URL.createObjectURL(file);
    }
};

const handleTicketLogoUpload = (event) => {
    const file = event.target.files[0];
    if (file) {
        ticketLogoFile.value = file;
        previewTicketLogo.value = URL.createObjectURL(file);
    }
};

// Le jeton n'est regenere qu'une fois (a l'installation) : la case doit etre cochee, et elle se decoche apres chaque regeneration.
const confirmRegenerate = ref(false);
const handleRegenerateToken = async () => {
    if (!confirm("Régénérer le jeton invalidera l'ancien pour tous les services pont locaux déjà configurés. Continuer ?")) return;
    await configStore.regenerateTicketPrintToken();
    confirmRegenerate.value = false;
};

const saveStructureConfig = async () => {
    isSaving.value = true;
    try {
        const formData = new FormData();
        Object.keys(formStructure.value).forEach(key => {
            formData.append(key, formStructure.value[key] || '');
        });
        if (logoFile.value) {
            formData.append('logo', logoFile.value);
        }
        if (ticketLogoFile.value) {
            formData.append('ticket_logo', ticketLogoFile.value);
        }
        await configStore.saveStructureInfo(formData);
        alert("Configuration de la structure enregistrée avec succès !");
    } catch (error) {
        console.error("Erreur save:", error);
        alert("Erreur lors de l'enregistrement: " + error.message);
    } finally {
        isSaving.value = false;
    }
};


// --- LOGIQUE EXAMENS ---
const filteredExamens = computed(() => {
  if (!searchQuery.value) return configStore.examens;
  const query = searchQuery.value.toLowerCase();
  return configStore.examens.filter(exam => 
    exam.nom.toLowerCase().includes(query) ||
    exam.code.toLowerCase().includes(query) ||
    exam.categorie.toLowerCase().includes(query)
  );
});

const openExamModal = (exam) => {
  selectedExam.value = exam;
  showExamModal.value = true;
};

const onExamSaved = () => {
  showExamModal.value = false;
  configStore.fetchExamens();
};

const handleDeleteExam = async (id) => {
    if(confirm(t('config.delete_confirmation') || "Supprimer cet élément ?")) {
        await configStore.deleteExamen(id);
    }
};

// --- LOGIQUE SYSTEME ---
const handleBackup = async () => {
  if (isBackupRunning.value) return;
  isBackupRunning.value = true;
  await new Promise(resolve => setTimeout(resolve, 3000)); 
  isBackupRunning.value = false;
  alert(t('config.db_backup') + " terminée.");
};

const toggleMaintenanceMode = async () => {
  isMaintenanceMode.value = !isMaintenanceMode.value;
};

const formatPrice = (price) => {
  return new Intl.NumberFormat('fr-FR', {
    style: 'currency', currency: 'XOF', minimumFractionDigits: 0
  }).format(price).replace('XOF', 'FCFA'); 
};
</script>