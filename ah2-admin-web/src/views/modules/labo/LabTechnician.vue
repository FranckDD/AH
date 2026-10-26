<template>
  <div class="h-full overflow-y-auto p-4 md:p-6">
    <div class="mx-auto grid max-w-7xl items-start gap-6 lg:grid-cols-3">

      <!-- Dossiers en attente de saisie -->
      <AppCard class="lg:col-span-1" :title="t('lab.technician.title')" :subtitle="t('lab.technician.in_analysis', { n: labStore.paillasseList.length })">
        <template #actions>
          <AppButton variant="secondary" :icon="ArrowPathIcon" :loading="labStore.loading" @click="refreshList">{{ t('labScreens.refresh') }}</AppButton>
        </template>

        <p v-if="labStore.loading" role="status" class="sr-only">{{ t('ui.loading') }}</p>
        <EmptyState v-if="labStore.paillasseList.length === 0 && !labStore.loading" :icon="BeakerIcon" :title="t('lab.technician.nothing_to_enter')" />

        <div v-else class="grid max-h-[28rem] gap-3 overflow-y-auto lg:max-h-[65vh]">
          <LabPassageCard v-for="passage in passages" :key="passage.key" :passage="passage" :active-id="activeId" @open="openDossier" />
        </div>
      </AppCard>

      <!-- Dossier ouvert -->
      <div class="grid gap-4 lg:col-span-2">
        <section v-if="!activeDossier" class="rounded-card border border-tone-neutral-border bg-white shadow-card">
          <EmptyState :icon="BeakerIcon" :title="t('lab.technician.select_file')" />
        </section>

        <template v-else>
          <header class="grid gap-3 rounded-card bg-brand-700 p-4 text-white">
            <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div class="min-w-0">
              <h1 class="flex flex-wrap items-center gap-2 text-lg font-bold">
                {{ activeDossier.examen_nom }}
                <span class="rounded-control border border-white px-2 py-0.5 text-sm font-medium">#{{ activeDossier.code }}</span>
                <span v-if="activeDossier.corrected" class="rounded-control border border-white px-2 py-0.5 text-sm font-medium">{{ t('lab.technician.corrected_badge') }}</span>
              </h1>
              <p class="mt-1 flex items-center gap-2 text-sm">
                <UserIcon class="h-5 w-5 shrink-0" aria-hidden="true" />
                <span class="font-medium">{{ activeDossier.patient_info?.nom }}</span>
              </p>
            </div>
            <p class="text-sm font-medium">
              {{ t('labScreens.sex_age', { sex: activeDossier.patient_info?.sexe, age: activeDossier.patient_info?.age, years: t('lab.result_modal.years') }) }}
            </p>
            </div>
            <div v-if="activeDossier.details && activeDossier.details.length > 0">
              <p class="mb-1 text-sm">{{ t('labScreens.progress', { n: filledCount, total: activeDossier.details.length }) }}</p>
              <div class="h-2 overflow-hidden rounded-full bg-white/30" role="progressbar" :aria-valuenow="filledCount" aria-valuemin="0" :aria-valuemax="activeDossier.details.length"
                   :aria-label="t('labScreens.progress', { n: filledCount, total: activeDossier.details.length })">
                <div class="h-2 rounded-full bg-white transition-all duration-500" :style="{ width: (filledCount / activeDossier.details.length * 100) + '%' }"></div>
              </div>
            </div>
          </header>

          <div v-if="labStore.batchSiblings.length > 1" role="group" :aria-label="t('labScreens.batch_label')" class="flex gap-2 overflow-x-auto pb-1">
            <button v-for="sibling in labStore.batchSiblings" :key="sibling.result_id" type="button" @click="openDossier(sibling.result_id)"
                    :aria-pressed="sibling.result_id === activeDossier.result_id"
                    :class="sibling.result_id === activeDossier.result_id ? 'border-brand-600 bg-brand-50 font-semibold text-brand-700' : 'border-tone-neutral-border bg-white text-ink-muted hover:bg-tone-neutral-bg'"
                    class="flex min-h-11 shrink-0 items-center gap-2 rounded-control border-2 px-3 text-sm focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600">
              {{ sibling.exam_name }}
              <StatusBadge v-if="sibling.status === 'completed'" tone="success" :label="t('labScreens.done_badge')" />
            </button>
          </div>

          <p v-if="amendNotice" role="status" class="rounded-card border p-4 text-sm" :class="toneClasses('success')">{{ amendNotice }}</p>
          <p v-if="isLocked" role="status" class="flex items-start gap-2 rounded-card border p-4 text-sm" :class="toneClasses('info')">
            <LockClosedIcon class="mt-0.5 h-5 w-5 shrink-0" aria-hidden="true" />
            {{ t('lab.technician.locked_notice') }}
          </p>

          <p v-if="!activeDossier.details || activeDossier.details.length === 0" role="status" class="rounded-card border p-4 text-sm" :class="toneClasses('warning')">
            {{ t('lab.technician.no_params') }}
          </p>

          <ResponsiveTable v-else :columns="detailColumns" :rows="activeDossier.details" row-key="detail_id" striped>
            <template #cell-name="{ row: detail }"><span class="text-sm font-medium">{{ detail.nom }}</span></template>
            <template #cell-value="{ row: detail }">
              <div class="grid gap-2">
                <input v-if="detail.input_type === 'numeric'" v-model.number="formValues[detail.detail_id]" type="number" step="any" @wheel="$event.target.blur()" :disabled="isLocked"
                       :aria-label="t('labScreens.value_for', { name: detail.nom })" placeholder="-" :class="[fieldClass, 'text-center font-semibold lg:w-48']" />
                <input v-else v-model="formValues[detail.detail_id]" type="text" :disabled="isLocked"
                       :aria-label="t('labScreens.value_for', { name: detail.nom })" :placeholder="t('lab.technician.result_placeholder')" :class="[fieldClass, 'lg:w-48']" />

                <template v-if="hasValue(formValues[detail.detail_id])">
                  <div role="radiogroup" :aria-label="t('labScreens.flag_for', { name: detail.nom })" class="flex flex-wrap gap-2">
                    <label v-for="opt in flagOptions" :key="opt.value" class="cursor-pointer">
                      <input type="radio" class="peer sr-only" :name="`lab-flag-${detail.detail_id}`" :value="opt.value" v-model="formFlags[detail.detail_id]" :disabled="isLocked" />
                      <span :class="opt.checked"
                            class="inline-flex min-h-11 items-center gap-1.5 rounded-full border-2 border-tone-neutral-border bg-white px-3 text-sm font-medium text-ink-muted transition hover:bg-tone-neutral-bg peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-brand-600">
                        <component :is="opt.icon" class="h-5 w-5 shrink-0" aria-hidden="true" />
                        {{ opt.label }}
                      </span>
                    </label>
                  </div>
                  <input v-model="formInterpretations[detail.detail_id]" type="text" :disabled="isLocked" :aria-label="t('labScreens.note_for', { name: detail.nom })"
                         :placeholder="t('lab.technician.interp_placeholder')" :class="fieldClass" />
                </template>
              </div>
            </template>
            <template #cell-unit="{ row: detail }"><span class="text-sm">{{ detail.unite }}</span></template>
            <template #cell-range="{ row: detail }"><span class="text-sm">{{ getRangeForPatient(detail.ranges, activeDossier.patient_info?.sexe) }}</span></template>
          </ResponsiveTable>

          <section v-if="activeDossier.details && activeDossier.details.length > 0" class="rounded-card border border-tone-neutral-border bg-white p-4 shadow-card">
            <FormField id="lab-tech-note" :label="t('lab.technician.global_conclusion')" v-slot="{ describedBy }">
              <textarea id="lab-tech-note" v-model="formGlobalNote" rows="3" :disabled="isLocked" :aria-describedby="describedBy" :placeholder="t('lab.technician.conclusion_placeholder')"
                        :class="[fieldClass, 'py-2']"></textarea>
            </FormField>
          </section>

          <!-- Resultat valide : correction avec motif obligatoire (le medecin prescripteur est prevenu). -->
          <section v-if="activeDossier.details && activeDossier.details.length > 0 && activeDossier.status === 'completed'" class="grid gap-3 rounded-card border border-tone-neutral-border bg-white p-4 shadow-card">
            <template v-if="amending">
              <FormField id="lab-tech-amend-reason" :label="t('lab.technician.amend_reason_label')" :error="amendError" v-slot="{ describedBy }">
                <textarea id="lab-tech-amend-reason" v-model="amendReason" rows="3" :aria-describedby="describedBy"
                          :placeholder="t('lab.technician.amend_reason_placeholder')" :class="[fieldClass, 'py-2']"></textarea>
              </FormField>
              <p v-if="labStore.error" role="alert" class="rounded-control border p-3 text-sm" :class="toneClasses('danger')">{{ labStore.error }}</p>
            </template>
            <ActionBar>
              <template #secondary>
                <AppButton v-if="amending" variant="secondary" :disabled="labStore.loading" @click="cancelAmend">{{ t('lab.technician.amend_cancel') }}</AppButton>
              </template>
              <AppButton v-if="!amending" variant="lab" :icon="PencilSquareIcon" @click="startAmend">{{ t('lab.technician.amend_btn') }}</AppButton>
              <AppButton v-else variant="lab" :loading="labStore.loading" :disabled="labStore.loading" @click="submitAmend">{{ t('lab.technician.amend_save') }}</AppButton>
            </ActionBar>
          </section>

          <ActionBar v-if="!isLocked && !amending" class="rounded-card border">
            <template #secondary>
              <AppButton variant="secondary" :disabled="labStore.loading" @click="submit(false)">{{ t('lab.technician.save_draft') }}</AppButton>
            </template>
            <AppButton variant="success" :disabled="labStore.loading || !activeDossier.details.length || isFormEmpty" @click="submit(true, false)">
              {{ t('lab.technician.validate_close') }}
            </AppButton>
            <AppButton :icon="PrinterIcon" :loading="labStore.loading" :disabled="labStore.loading || !activeDossier.details.length || isFormEmpty" @click="submit(true, true)">
              {{ t('lab.technician.validate_print') }}
            </AppButton>
          </ActionBar>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
import { notifyText } from '@/utils/notify';
import { ref, computed, onMounted } from 'vue';
import { useLabStore } from '@/stores/labStore';
import dayjs from 'dayjs';
import { useI18n } from 'vue-i18n';
import { useRoute } from 'vue-router';
import { useToastStore } from '@/stores/toastStore';
import {
  ArrowPathIcon, BeakerIcon, UserIcon, PrinterIcon,
  ArrowUpIcon, ArrowDownIcon, CheckCircleIcon, ExclamationTriangleIcon, MinusCircleIcon, LockClosedIcon, PencilSquareIcon
} from '@heroicons/vue/24/outline';
import { AppButton, AppCard, FormField, StatusBadge, EmptyState, ResponsiveTable, ActionBar } from '@/components/ui';
import LabPassageCard from '@/components/lab/LabPassageCard.vue';
import { groupPaillasse } from '@/utils/labPassages';
import { rangeLabelForPatient } from '@/utils/labRanges';
import { toneClasses } from '@/design/tones';

const labStore = useLabStore();
const { t } = useI18n();
const route = useRoute();
const toast = useToastStore();
const activeId = ref(null);

// Un patient une seule fois, avec tous les examens de son passage (termines compris).
const passages = computed(() => groupPaillasse(labStore.paillasseList));

// Colonnes du tableau des parametres (cartes empilees sous lg).
const detailColumns = computed(() => [
  { key: 'name', label: t('lab.result_modal.param') },
  { key: 'value', label: t('lab.technician.value') },
  { key: 'unit', label: t('lab.result_modal.unit') },
  { key: 'range', label: t('lab.technician.reference'), align: 'right' },
]);

// Drapeaux proposes : H (haut), L (bas), N (normal), A (anormal), ou aucun. Chaque pastille porte
// son icone ET son texte ; la couleur de l'etat choisi suit le sens (jamais la couleur seule).
const flagOptions = computed(() => [
  { value: '', label: t('labScreens.flag_clear'), icon: MinusCircleIcon, checked: 'peer-checked:border-brand-600 peer-checked:bg-brand-50 peer-checked:text-brand-700' },
  { value: 'H', label: t('lab.result_modal.flag_high'), icon: ArrowUpIcon, checked: 'peer-checked:border-tone-warning-border peer-checked:bg-tone-warning-bg peer-checked:text-tone-warning-text' },
  { value: 'L', label: t('lab.result_modal.flag_low'), icon: ArrowDownIcon, checked: 'peer-checked:border-tone-info-border peer-checked:bg-tone-info-bg peer-checked:text-tone-info-text' },
  { value: 'N', label: t('lab.technician.flag_normal'), icon: CheckCircleIcon, checked: 'peer-checked:border-tone-success-border peer-checked:bg-tone-success-bg peer-checked:text-tone-success-text' },
  { value: 'A', label: t('lab.result_modal.abnormal'), icon: ExclamationTriangleIcon, checked: 'peer-checked:border-tone-danger-border peer-checked:bg-tone-danger-bg peer-checked:text-tone-danger-text' },
]);
const fieldClass = 'block w-full min-h-11 lg:min-h-10 rounded-control border border-tone-neutral-border bg-white px-3 text-sm text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600';

// Nouveaux états réactifs pour la structure séparée
const formValues = ref({}); 
const formFlags = ref({});
const formInterpretations = ref({});
const formGlobalNote = ref('');

// Récupère le dossier complet depuis le store
const activeDossier = computed(() => labStore.currentResult);

// Un résultat validé est en lecture seule : on ne le modifie que par la correction avec motif.
const amending = ref(false);
const amendReason = ref('');
const amendError = ref('');
const amendNotice = ref('');
const isLocked = computed(() => activeDossier.value?.status === 'completed' && !amending.value);

// Vérifie si aucune valeur n'a été saisie dans le formulaire principal
const isFormEmpty = computed(() => {
  if (Object.keys(formValues.value).length === 0) return true;
  return !Object.values(formValues.value).some(val => val !== '' && val !== null && val !== undefined);
});

// Affichage seulement : nombre de parametres deja saisis.
const filledCount = computed(() => (activeDossier.value?.details || []).filter((d) => hasValue(formValues.value[d.detail_id])).length);

// Helper pour afficher la sous-ligne
const hasValue = (val) => {
  return val !== '' && val !== null && val !== undefined;
};

onMounted(async () => {
  await refreshList();
  // Arrivee depuis le dashboard ("Saisir") : ouvrir directement le dossier
  // cible au lieu de laisser le technicien le rechercher dans la liste.
  const target = Number(route.query.open);
  if (target) {
    await openDossier(target);
    // Arrivee depuis l'historique ("Corriger ce resultat") : directement en mode correction.
    if (route.query.amend && activeDossier.value?.status === 'completed') startAmend();
  }
});

const refreshList = () => labStore.fetchPaillasseList();

// --- LOGIQUE MÉTIER ---

const flagFromDetail = (d) => {
  if (!(d.is_abnormal || d.flagged)) return '';
  const interp = (d.interpretation || '').toLowerCase();
  if (interp === 'haut') return 'H';
  if (interp === 'bas') return 'L';
  return 'A';
};

const openDossier = async (id) => {
  if (!id) return;

  activeId.value = id;
  labStore.clearMessages();
  amending.value = false;
  amendReason.value = '';
  amendError.value = '';
  amendNotice.value = '';
  
  // Reset complet
  formValues.value = {}; 
  formFlags.value = {};
  formInterpretations.value = {};
  formGlobalNote.value = '';
  
  // Appel API
  const data = await labStore.fetchResultDetail(id);
  
  // Remplissage du formulaire
  if (data) {
    // 🟢 Remplissage de la note globale depuis le champ "note" (si sauvegardé en brouillon)
    formGlobalNote.value = data.note || '';

    if (data.details) {
      data.details.forEach(d => {
        // Pour être sûr de rattraper les anciennes données
        const val = (d.valeur !== null && d.valeur !== undefined) ? d.valeur : '';
        formValues.value[d.detail_id] = val;
        
        // Le backend renvoie `is_abnormal` (pas `flagged`) : restaurer le flag
        // d'origine (Haut/Bas/Anormal) plutot que de le perdre a la reouverture.
        formFlags.value[d.detail_id] = flagFromDetail(d);
        formInterpretations.value[d.detail_id] = d.interpretation || '';
      });
    }
  }
};

const submit = async (isCompleted, shouldPrint) => {
  // Sécurité: On s'assure d'avoir un ID valide
  const targetId = activeId.value || activeDossier.value?.result_id;
  
  if (!targetId) {
      notifyText(t('lab.technician.no_file_selected'));
      return;
  }

  // 🟢 Construction du payload des valeurs au format attendu par le Controller
  const payloadValues = {};
  for (const detailId in formValues.value) {
      payloadValues[detailId] = {
          valeur: formValues.value[detailId],
          flag: formFlags.value[detailId] || '',
          interpretation: formInterpretations.value[detailId] || ''
      };
  }

  // 🟢 Construction du payload global
  const fullPayload = {
      values: payloadValues,
      completed: isCompleted,
      note: formGlobalNote.value
  };

  // ⚠️ ATTENTION : Assure-toi que ta fonction `labStore.saveValues`
  // transmette maintenant l'objet `fullPayload` complet à ton API.
  const success = await labStore.saveValues(targetId, fullPayload);
  
  if (success) {
      toast.push(isCompleted ? t('lab.technician.validated_ok') : t('lab.technician.draft_saved'), 'success');
      if (isCompleted && shouldPrint) {
          // Logique d'impression basique
          await labStore.downloadPDF(targetId, `Resultat_${targetId}.pdf`);
      }

      // Si c'est fini, on ferme
      if (isCompleted) {
          activeId.value = null;
          formValues.value = {};
          formFlags.value = {};
          formInterpretations.value = {};
          formGlobalNote.value = '';
      }
  }
};

// --- CORRECTION D'UN RESULTAT VALIDE ---

const startAmend = () => {
  amendNotice.value = '';
  amendError.value = '';
  amending.value = true;
};

const cancelAmend = async () => {
  // Remet les valeurs d'origine dans le formulaire.
  await openDossier(activeId.value || activeDossier.value?.result_id);
};

const submitAmend = async () => {
  const targetId = activeId.value || activeDossier.value?.result_id;
  if (!targetId) return;
  const reason = amendReason.value.trim();
  if (!reason) {
    amendError.value = t('lab.technician.amend_reason_required');
    return;
  }
  amendError.value = '';
  const payloadValues = {};
  for (const detailId in formValues.value) {
    payloadValues[detailId] = {
      valeur: formValues.value[detailId],
      flag: formFlags.value[detailId] || '',
      interpretation: formInterpretations.value[detailId] || ''
    };
  }
  const ok = await labStore.amendResult(targetId, { reason, values: payloadValues, note: formGlobalNote.value });
  if (ok) {
    await openDossier(targetId);
    amendNotice.value = t('lab.technician.amend_success');
  }
};

// --- HELPERS D'AFFICHAGE ---

// Trouve la bonne plage de référence selon le sexe (M/F)
// Plage du sexe du patient (a defaut la plage generique) ; jamais celle de l'autre sexe.
const getRangeForPatient = (ranges, sexePatient) => rangeLabelForPatient(ranges, sexePatient);
</script>
<style scoped>
input[type=number]::-webkit-inner-spin-button,
input[type=number]::-webkit-outer-spin-button {
  -webkit-appearance: none; margin: 0;
}
</style>
