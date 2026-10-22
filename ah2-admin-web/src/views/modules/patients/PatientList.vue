<template>
  <div class="grid w-full gap-6">

    <PageHeader :title="t('patients.title')" :subtitle="`Total : ${activeTabCount} patients`">
      <template #actions>
        <AppButton variant="secondary" @click="showExportModal = true">
          {{ t('export.confirm') }}
        </AppButton>
        <AppButton v-if="canManagePatients" :icon="PlusIcon" @click="openCreateModal">
          Ajouter un patient
        </AppButton>
      </template>
    </PageHeader>

    <div class="relative w-full md:max-w-md">
      <label for="patient-search" class="sr-only">{{ t('patients.search_placeholder') }}</label>
      <MagnifyingGlassIcon class="pointer-events-none absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-ink-muted" aria-hidden="true" />
      <input
        id="patient-search"
        v-model.lazy="searchQuery"
        @keyup.enter="patientStore.fetchPatients()"
        type="text"
        :placeholder="t('patients.search_placeholder')"
        class="block w-full min-h-11 rounded-control border border-tone-neutral-border bg-white pl-10 pr-3 text-base text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600"
      />
    </div>

    <div class="overflow-x-auto border-b border-tone-neutral-border">
      <div class="-mb-px flex gap-2" role="tablist" aria-label="Catégories de patients">
        <button
          v-for="tab in tabs"
          :key="tab.value"
          type="button"
          role="tab"
          :aria-selected="currentTab === tab.value"
          @click="currentTab = tab.value"
          :class="[
            currentTab === tab.value
              ? 'border-brand-600 text-brand-700'
              : 'border-transparent text-ink-muted hover:text-ink hover:border-tone-neutral-border',
            'flex min-h-11 items-center whitespace-nowrap border-b-2 px-3 text-base font-medium focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-brand-600'
          ]"
        >
          <component :is="tab.icon" class="mr-2 h-5 w-5" aria-hidden="true" />
          {{ t(tab.labelKey) }}
          <span class="ml-2 rounded-full bg-tone-neutral-bg px-2.5 py-0.5 text-sm font-bold text-tone-neutral-text">
            {{ tab.count }}
          </span>
        </button>
      </div>
    </div>

    <p v-if="patientStore.error" role="alert" class="rounded-card border p-4 text-base font-medium" :class="toneClasses('danger')">
      {{ patientStore.error }}
    </p>

    <ResponsiveTable
      v-else
      :columns="columns"
      :rows="patientStore.patients"
      row-key="id"
      :loading="patientStore.isLoading"
      empty-title="Aucun patient trouvé."
      :empty-message="' '"
    >
      <template #cell-patient="{ row: patient }">
        <div class="flex flex-col">
          <span class="text-sm font-bold uppercase tracking-wide text-ink-muted">{{ patient.code }}</span>
          <span class="text-base font-medium text-ink">{{ patient.firstName }} {{ patient.lastName }}</span>
          <span v-if="patient.is_staff" class="mt-1 self-start"><StatusBadge tone="success" :label="t('staffDiscount.badge')" /></span>
        </div>
      </template>
      <template #cell-type="{ row: patient }">
        <StatusBadge :tone="typeTone(patient.type)" :label="patient.type" />
      </template>
      <template #cell-phone="{ row: patient }">{{ patient.phone || 'N/A' }}</template>

      <template #actions="{ row: patient }">
        <AppButton
          v-if="!disableDetailLink"
          @click="viewPatientDossier(patient.id)"
        >
          Voir Dossier
        </AppButton>
        <AppButton
          v-if="canManagePatients"
          variant="secondary"
          :icon="PencilSquareIcon"
          @click="openEditModal(patient)"
          :disabled="patient.pending"
          :title="patient.pending ? 'En attente de synchronisation' : 'Modifier'"
        >
          Modifier
        </AppButton>
        <AppButton
          v-if="canManagePatients"
          variant="danger"
          :icon="TrashIcon"
          @click="confirmDelete(patient)"
          :disabled="patient.pending"
          :title="patient.pending ? 'En attente de synchronisation' : 'Supprimer'"
        >
          Supprimer
        </AppButton>
      </template>
    </ResponsiveTable>

    <div class="flex items-center justify-between gap-3 rounded-card border border-tone-neutral-border bg-white p-3">
      <AppButton
        variant="secondary"
        :icon="ChevronLeftIcon"
        @click="goToPage(patientStore.pagination.page - 1)"
        :disabled="patientStore.pagination.page === 1"
      >
        Précédent
      </AppButton>

      <span class="text-base font-medium text-ink">
        Page {{ patientStore.pagination.page }} sur {{ patientStore.pagination.total_pages }}
      </span>

      <AppButton
        variant="secondary"
        @click="goToPage(patientStore.pagination.page + 1)"
        :disabled="!patientStore.pagination.hasNext"
      >
        Suivant <ChevronRightIcon class="h-5 w-5" aria-hidden="true" />
      </AppButton>
    </div>

    <p v-if="deleteError" role="alert" class="rounded-card border p-4 text-base font-medium" :class="toneClasses('danger')">{{ deleteError }}</p>

    <PatientModal
        v-if="showModal"
        :patientToEdit="patientBeingEdited"
        :errorMessage="modalError"
        :isSaving="isSavingPatient"
        @close="closeModal"
        @save="handleSave"
    />

    <NewPatientCodeModal
        v-if="codeDialog"
        :localUuid="codeDialog.localUuid"
        :firstName="codeDialog.firstName"
        :lastName="codeDialog.lastName"
        @ok="onCodeOk"
    />

    <!-- Parametres du patient qui vient d'etre enregistre : a envoyer au medecin par defaut -->
    <MedicalRecordModal
        v-if="recordPrefill"
        :prefilledPatient="recordPrefill"
        :defaultNeedsDoctorReview="true"
        @close="recordPrefill = null"
        @save="handleRecordSave"
    />

    <ExportModal
      v-if="showExportModal"
      :title="t('export.confirm') + ' : ' + t('patients.title')"
      :formats="[{ value: 'pdf', label: 'PDF' }, { value: 'csv', label: 'CSV' }]"
      :onExport="exportPatients"
      @close="showExportModal = false"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import { usePatientStore } from '@/stores/patientStore';
import { useRouter, useRoute } from 'vue-router';
import { useI18n } from 'vue-i18n';
import {
    MagnifyingGlassIcon, UsersIcon, SparklesIcon,
    BeakerIcon, HeartIcon, ChevronLeftIcon, ChevronRightIcon,
    PlusIcon, PencilSquareIcon, TrashIcon
} from '@heroicons/vue/24/outline';
import PatientModal from '@/components/patients/PatientModal.vue';
import NewPatientCodeModal from '@/components/patients/NewPatientCodeModal.vue';
import MedicalRecordModal from '@/components/medical-records/MedicalRecordModal.vue';
import { useMedicalRecordStore } from '@/stores/medicalRecordStore';
import { useToastStore } from '@/stores/toastStore';
import { runsNewPatientFlow, patientPrefillFromCreated } from '@/utils/newPatientFlow';
import ExportModal from '@/components/common/ExportModal.vue';
import { AppButton, PageHeader, StatusBadge, ResponsiveTable } from '@/components/ui';
import { toneClasses } from '@/design/tones';
import { useAuthStore } from '@/stores/auth';
import api from '@/services/api';

const props = defineProps({ disableDetailLink: { type: Boolean, default: false } });

const { t } = useI18n();
const patientStore = usePatientStore();
const medicalRecordStore = useMedicalRecordStore();
const router = useRouter();
const route = useRoute();
const authStore = useAuthStore();

// Roles avec droit d'ECRITURE (POST/PUT/DELETE) sur /patients - depuis le
// chantier L4b-e, distinct des roles avec droit de LECTURE au niveau du
// routeur (qui inclut aussi assistant et ToxicoManager pour la recherche,
// voir patients_endpoints.py). Assistant est volontairement absent ici :
// il garde /patients en lecture/recherche seule (dette parquee au
// chantier 6, refermee au chantier L4b-e).
const canManagePatients = computed(() =>
    authStore.hasRole(['medecin', 'nurse', 'secretaire', 'admin', 'manager'])
);

// Colonnes du tableau (cartes empilees sous lg).
const columns = [
    { key: 'patient', label: 'Code / Patient' },
    { key: 'type', label: 'Type' },
    { key: 'phone', label: 'Téléphone' },
];

const showModal = ref(false);
const patientBeingEdited = ref(null);
const modalError = ref('');
const isSavingPatient = ref(false);
const deleteError = ref('');
const showExportModal = ref(false);

const exportPatients = async ({ format, dateFrom, dateTo }) => {
    const params = {
        format,
        type: patientStore.filters.type,
        search: patientStore.filters.search || undefined,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
    };
    const response = await api.get('/patients/export', {
        params,
        responseType: format === 'pdf' ? 'blob' : 'text',
    });
    const blob = format === 'pdf'
        ? new Blob([response.data], { type: 'application/pdf' })
        : new Blob([response.data], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `patients_export.${format}`;
    link.click();
    window.URL.revokeObjectURL(url);
};

const openCreateModal = () => {
    patientBeingEdited.value = null;
    modalError.value = '';
    showModal.value = true;
};

const openEditModal = async (patient) => {
    modalError.value = '';
    try {
        patientBeingEdited.value = await patientStore.getPatientById(patient.id);
        showModal.value = true;
    } catch (err) {
        deleteError.value = "Impossible de charger les détails du patient pour modification.";
    }
};

const closeModal = () => {
    showModal.value = false;
    patientBeingEdited.value = null;
    modalError.value = '';
};

const mapErrorToMessage = (err) => {
    if (err.response) {
        const status = err.response.status;
        const detail = err.response.data?.detail;
        if (status === 422) {
            const errors = Array.isArray(detail) ? detail : [];
            if (errors.length) {
                return `Erreurs de validation : ${errors.map(e => e.msg).join(', ')}`;
            }
            return "Données invalides.";
        }
        if (status === 400) return detail || "Requête invalide.";
        if (status === 401) return "Session expirée. Veuillez vous reconnecter.";
        if (status === 409) return detail || "Ce patient existe peut-être déjà (identifiant en conflit).";
        return `Erreur serveur (${status}) : ${detail || 'veuillez réessayer'}`;
    }
    if (err.request) return "Erreur réseau. Veuillez vérifier votre connexion.";
    return err.message || "Une erreur inattendue est survenue.";
};

const handleSave = async (payload) => {
    isSavingPatient.value = true;
    modalError.value = '';
    try {
        if (patientBeingEdited.value) {
            await patientStore.updatePatient(patientBeingEdited.value.patient_id, payload);
        } else {
            const created = await patientStore.addPatient(payload);
            closeModal();
            // Infirmiere : code a noter sur le carnet (fenetre qui attend OK), puis formulaire
            // des parametres du patient. Medecin/secretaire : comportement inchange ci-dessous.
            if (runsNewPatientFlow(authStore.userRole, created)) {
                codeDialog.value = {
                    localUuid: created.localUuid,
                    firstName: payload.firstName,
                    lastName: payload.lastName,
                };
                return;
            }
            // medecin/nurse : on enchaine directement sur la fiche du patient
            // cree (consultation/prescription possibles hors ligne, identifie
            // par son uuid tant qu'il n'a pas de code). Secretaire : pas de
            // fiche (disableDetailLink), il reste visible dans la liste.
            if (created?.localUuid && !props.disableDetailLink) {
                router.push(`${route.path}/${created.localUuid}`);
            }
            return;
        }
        closeModal();
    } catch (err) {
        modalError.value = mapErrorToMessage(err);
    } finally {
        isSavingPatient.value = false;
    }
};

// Parcours nouveau patient (infirmiere) : fenetre du code -> OK -> formulaire des parametres.
const codeDialog = ref(null);
const recordPrefill = ref(null);

const onCodeOk = ({ code, patientId }) => {
    const { localUuid, firstName, lastName } = codeDialog.value;
    recordPrefill.value = patientPrefillFromCreated({ localUuid, patientId, code, firstName, lastName });
    codeDialog.value = null;
};

const handleRecordSave = async (data) => {
    try {
        await medicalRecordStore.createMedicalRecord(data);
        recordPrefill.value = null;
        useToastStore().push(t('newPatient.saved'), 'success');
        patientStore.fetchPatients();
    } catch (err) {
        console.error('Erreur enregistrement des parametres:', err);
        alert('Erreur lors de l\'enregistrement : ' + (err.response?.data?.detail || err.message));
    }
};

const confirmDelete = async (patient) => {
    deleteError.value = '';
    if (confirm(`Voulez-vous vraiment supprimer ${patient.firstName} ${patient.lastName} ?`)) {
        try {
            await patientStore.deletePatient(patient.id);
        } catch (err) {
            deleteError.value = mapErrorToMessage(err);
        }
    }
};

// 🟢 Chargement initial
onMounted(() => {
    patientStore.fetchPatients();
    // 🟢 Charger les compteurs globaux au montage
    patientStore.fetchCounts();
});

// 🟢 Configuration des Onglets (MAINTENANT COMPUTED)
const tabs = computed(() => {
    const tousLesOnglets = [
        {
            value: 'ALL',
            labelKey: 'patients.tabs.all',
            icon: UsersIcon,
            count: patientStore.counts.ALL
        },
        {
            value: 'CLINIQUE',
            labelKey: 'patients.tabs.clinical',
            icon: HeartIcon,
            count: patientStore.counts.CLINIQUE
        },
        {
            value: 'TOXICO',
            labelKey: 'patients.tabs.toxico',
            icon: BeakerIcon,
            count: patientStore.counts.TOXICO
        },
        {
            value: 'SPIRITUEL',
            labelKey: 'patients.tabs.spiritual',
            icon: SparklesIcon,
            count: patientStore.counts.SPIRITUEL
        },
    ];
    // medecin/nurse : le backend refuse desormais /patients/toxicology et
    // /patients/spiritual/list (403) - sans ce filtre, ces deux onglets
    // restaient cliquables et menaient a un cul-de-sac affiche comme
    // "Erreur de connexion au serveur", masquant un refus de permission
    // volontaire derriere un message d'erreur technique trompeur.
    if (authStore.hasRole(['medecin', 'nurse'])) {
        return tousLesOnglets.filter((t) => t.value !== 'TOXICO' && t.value !== 'SPIRITUEL');
    }
    return tousLesOnglets;
});

// Helper pour afficher le total de l'onglet actif sous le titre
const activeTabCount = computed(() => {
    const active = tabs.value.find(t => t.value === currentTab.value);
    return active ? active.count : 0;
});

// 3. Créer la fonction de navigation
// Relatif a route.path (pas de nom de route en dur) : ce composant est
// monte a la fois sous /dashboard/patients (admin/ToxicoManager) et
// /medical/patients (medecin/nurse) - un nom fige pointerait toujours
// vers /dashboard/patients/:id, hors de portee des roles medicaux.
const viewPatientDossier = (patientId) => {
    router.push(`${route.path}/${patientId}`);
};

// Getter/Setter pour la recherche
const searchQuery = computed({
    get: () => patientStore.filters.search,
    set: (val) => patientStore.setFilters({ search: val })
});

// Getter/Setter pour les onglets
const currentTab = computed({
    get: () => patientStore.filters.type,
    set: (val) => patientStore.setFilters({ type: val })
});

const goToPage = (page) => {
    patientStore.setPage(page);
};

// Categorie du patient : le texte porte l'information, la couleur n'est qu'un repere.
const typeTone = (type) => {
    switch(type) {
        case 'CLINIQUE': return 'info';
        case 'TOXICO': return 'warning';
        default: return 'neutral';
    }
};
</script>