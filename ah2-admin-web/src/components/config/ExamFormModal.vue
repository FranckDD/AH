<template>
  <FullScreenPanel :title="isEditing ? t('config.edit') : t('config.add_exam')" @close="$emit('close')">
    <form id="exam-form" @submit.prevent="handleSave" class="grid gap-4">

      <FormField id="exam-nom" :label="t('config.table_name')" required v-slot="{ describedBy }">
        <input id="exam-nom" v-model="form.nom" type="text" required :aria-describedby="describedBy" :class="fieldClass" />
      </FormField>

      <div class="grid gap-4 md:grid-cols-2">
        <FormField id="exam-code" :label="t('config.table_code')" :help="isEditing ? t('configScreens.code_locked') : ''" required v-slot="{ describedBy }">
          <input id="exam-code" v-model="form.code" type="text" required :disabled="isEditing" :aria-describedby="describedBy" :class="[fieldClass, 'disabled:bg-tone-neutral-bg']" />
        </FormField>
        <FormField id="exam-categorie" :label="t('config.table_category')" required v-slot="{ describedBy }">
          <input id="exam-categorie" v-model="form.categorie" type="text" required :aria-describedby="describedBy" :class="fieldClass" />
        </FormField>
      </div>

      <FormField id="exam-prix" :label="t('config.table_price')" required v-slot="{ describedBy }">
        <div class="flex">
          <input id="exam-prix" v-model.number="form.prix" type="number" min="0" step="100" required inputmode="numeric"
                 :aria-describedby="describedBy" :class="[fieldClass, 'rounded-r-none text-right font-mono font-bold']" />
          <span class="flex min-h-11 items-center rounded-r-control border border-l-0 border-tone-neutral-border bg-tone-neutral-bg px-3 text-base text-ink-muted lg:min-h-10">FCFA</span>
        </div>
      </FormField>
    </form>

    <template #footer>
      <ActionBar>
        <template #secondary>
          <AppButton variant="ghost" @click="$emit('close')">{{ t('config.cancel') }}</AppButton>
        </template>
        <AppButton type="submit" form="exam-form" :icon="CheckCircleIcon" :disabled="configStore.isLoading" :loading="configStore.isLoading">{{ t('config.save') }}</AppButton>
      </ActionBar>
    </template>
  </FullScreenPanel>
</template>

<script setup>
import { reactive, computed, watch } from 'vue';
import { useConfigStore } from '@/stores/configStore';
import { useI18n } from 'vue-i18n';
import { CheckCircleIcon } from '@heroicons/vue/24/outline';
import { AppButton, FormField, ActionBar, FullScreenPanel } from '@/components/ui';

const props = defineProps({
  examen: { type: Object, default: null }
});

const emit = defineEmits(['close', 'saved']);
const { t } = useI18n();
const configStore = useConfigStore();

// Style commun des champs : zone tactile >= 44 px, focus visible.
const fieldClass = 'block w-full min-h-11 lg:min-h-10 rounded-control border border-tone-neutral-border bg-white px-3 text-base text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600';

// Initialisation du formulaire
const form = reactive({
  id: null,
  code: '',
  nom: '',
  categorie: '',
  prix: 0
});

const isEditing = computed(() => form.id !== null);

// Remplir le formulaire à l'ouverture ou au changement de la prop
watch(() => props.examen, (newVal) => {
  if (newVal) {
    // Copie pour éviter de modifier la prop directement
    Object.assign(form, newVal);
  } else {
    // Reset pour mode Ajout
    form.id = null;
    form.code = '';
    form.nom = '';
    form.categorie = '';
    form.prix = 0;
  }
}, { immediate: true });

const handleSave = async () => {
  try {
    await configStore.saveExamen({ ...form });
    emit('saved'); // Notifier le parent pour rafraîchir la liste si besoin
    emit('close');
  } catch (error) {
    // L'erreur est déjà loguée dans le store, mais on peut ajouter une alerte locale ici si nécessaire
    alert(error.message);
  }
};
</script>