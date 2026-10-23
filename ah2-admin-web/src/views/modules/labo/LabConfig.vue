<template>
  <div class="h-full overflow-y-auto p-4 text-sm md:p-6 [&_table]:text-sm [&_dd]:text-sm">
    <div class="mx-auto grid max-w-7xl gap-6">

      <PageHeader :title="t('lab.config.title')" :subtitle="t('lab.config.subtitle')">
        <template #actions>
          <AppButton v-if="isAdmin" :icon="PlusIcon" @click="openModal()">{{ t('lab.config.new_exam') }}</AppButton>
        </template>
      </PageHeader>

      <ResponsiveTable :columns="columns" :rows="labStore.exams" row-key="id" striped>
        <template #cell-code="{ row: exam }"><span class="font-medium">{{ exam.code }}</span></template>
        <template #cell-name="{ row: exam }"><span class="font-medium">{{ exam.nom }}</span></template>
        <template #cell-category="{ row: exam }"><StatusBadge tone="info" :label="String(exam.categorie)" /></template>
        <template v-if="isAdmin" #actions="{ row: exam }">
          <AppButton variant="danger" :icon="TrashIcon" @click="removeExam(exam)">{{ t('labScreens.delete_exam') }}</AppButton>
        </template>
      </ResponsiveTable>
    </div>

    <ExamFormModal v-if="showExamModal" :examen="selectedExam" @close="showExamModal = false" @saved="onExamSaved" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { useLabStore } from '@/stores/labStore';
import { useAuthStore } from '@/stores/auth';
import { useConfigStore } from '@/stores/configStore';
import ExamFormModal from '@/components/config/ExamFormModal.vue';
import { PlusIcon, TrashIcon } from '@heroicons/vue/24/outline';
import { AppButton, PageHeader, StatusBadge, ResponsiveTable } from '@/components/ui';

const labStore = useLabStore();
const authStore = useAuthStore();
const configStore = useConfigStore();
const { t } = useI18n();

// Colonnes du tableau (cartes empilees sous lg).
const columns = computed(() => [
    { key: 'code', label: t('lab.config.col_code') },
    { key: 'name', label: t('lab.config.col_name') },
    { key: 'category', label: t('lab.config.col_category') },
]);

// Vérification du rôle pour l'affichage conditionnel
const isAdmin = computed(() => {
    return authStore.hasRole(['admin', 'manager']);
});

onMounted(() => {
    labStore.fetchExams();
});

// Creation d'un examen : meme fenetre que la configuration systeme (code, nom, categorie, prix).
const showExamModal = ref(false);
const selectedExam = ref(null);

const openModal = (exam = null) => {
    selectedExam.value = exam;
    showExamModal.value = true;
};

const onExamSaved = async () => {
    showExamModal.value = false;
    await labStore.fetchExams();
};

// Suppression (admin seul cote serveur) : confirmation avec le nom de l'examen, puis liste rechargee.
const removeExam = async (exam) => {
    if (!window.confirm(t('labScreens.delete_exam_confirm', { name: exam.nom }))) return;
    await configStore.deleteExamen(exam.id);
    await labStore.fetchExams();
};
</script>
