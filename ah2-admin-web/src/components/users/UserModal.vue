<template>
  <FullScreenPanel :title="isEditing ? t('users.modal.edit_title') : t('users.modal.new_title')" @close="$emit('close')">
    <form @submit.prevent="handleSubmit" id="userForm" class="grid gap-4">

      <FormSection compact :title="t('usersScreens.identity')">
        <FormField id="user-firstname" :label="t('users.modal.firstname')" required v-slot="{ describedBy }">
          <input id="user-firstname" v-model="form.firstName" type="text" required :aria-describedby="describedBy" :class="fieldClass" />
        </FormField>
        <FormField id="user-lastname" :label="t('users.modal.lastname')" required v-slot="{ describedBy }">
          <input id="user-lastname" v-model="form.lastName" type="text" required :aria-describedby="describedBy" :class="fieldClass" />
        </FormField>
        <FormField id="user-username" :label="t('usersScreens.username')" required v-slot="{ describedBy }">
          <input id="user-username" v-model="form.username" type="text" required autocomplete="off" :aria-describedby="describedBy" :class="fieldClass" />
        </FormField>
        <FormField id="user-email" :label="t('users.modal.email')" required v-slot="{ describedBy }">
          <input id="user-email" v-model="form.email" type="email" required :aria-describedby="describedBy" :class="fieldClass" />
        </FormField>
        <FormField id="user-phone" :label="t('users.modal.phone')" v-slot="{ describedBy }">
          <input id="user-phone" v-model="form.phone" type="tel" :aria-describedby="describedBy" :class="fieldClass" />
        </FormField>

        <div v-if="!isEditing">
          <FormField id="user-password" :label="t('usersScreens.password')" required v-slot="{ describedBy }">
            <div class="flex gap-2">
              <input id="user-password" v-model="form.password" :type="showPassword ? 'text' : 'password'" required autocomplete="new-password"
                     :aria-describedby="describedBy" :class="fieldClass" />
              <AppButton variant="secondary" :icon="showPassword ? EyeSlashIcon : EyeIcon"
                         :aria-label="showPassword ? t('usersScreens.hide_password') : t('usersScreens.show_password')" @click="showPassword = !showPassword" />
            </div>
          </FormField>
        </div>
        <div v-else>
          <FormField id="user-password" :label="t('usersScreens.new_password_optional')" v-slot="{ describedBy }">
            <div class="flex gap-2">
              <input id="user-password" v-model="form.password" :type="showPassword ? 'text' : 'password'" autocomplete="new-password"
                     :aria-describedby="describedBy" :class="fieldClass" />
              <AppButton variant="secondary" :icon="showPassword ? EyeSlashIcon : EyeIcon"
                         :aria-label="showPassword ? t('usersScreens.hide_password') : t('usersScreens.show_password')" @click="showPassword = !showPassword" />
            </div>
          </FormField>
        </div>
      </FormSection>

      <FormSection compact :title="t('usersScreens.permissions')">
        <FormField id="user-group" :label="t('users.groups.label')" required v-slot="{ describedBy }">
          <select id="user-group" v-model="form.postgres_role" @change="handlePostgresRoleChange" required :aria-describedby="describedBy" :class="fieldClass">
            <option value="app_admin">{{ t('users.groups.app_admin') }}</option>
            <option value="app_medical">{{ t('users.groups.app_medical') }}</option>
            <option value="app_secretaire">{{ t('users.groups.app_secretaire') }}</option>
            <option value="app_laborantin">{{ t('users.groups.app_laborantin') }}</option>
          </select>
        </FormField>

        <div v-if="availableRoles.length">
          <FormField id="user-role" :label="t('users.table.role')" required v-slot="{ describedBy }">
            <select id="user-role" v-model="form.role_id" @change="handleRoleChange" required :aria-describedby="describedBy" :class="fieldClass">
              <option :value="null" disabled>{{ t('usersScreens.select_role') }}</option>
              <option v-for="r in availableRoles" :key="r.id || r.role_id" :value="r.id || r.role_id">
                {{ prettyRole(r.role_name) }}
              </option>
            </select>
          </FormField>
        </div>

        <div v-if="showSpecialtyField">
          <FormField id="user-specialty" :label="t('users.specialty.label')" required v-slot="{ describedBy }">
            <select id="user-specialty" v-model="form.specialty_id" required :aria-describedby="describedBy" :class="fieldClass">
              <option :value="null" disabled>{{ t('users.specialty.placeholder') }}</option>
              <option v-for="s in medicalSpecialties" :key="s.specialty_id" :value="s.specialty_id">
                {{ s.name }}
              </option>
            </select>
          </FormField>
        </div>

        <label v-if="showHeadNurseField" class="flex min-h-11 items-center gap-3 text-base font-medium text-ink md:col-span-2">
          <input type="checkbox" v-model="form.is_head_nurse" class="h-5 w-5 accent-brand-600" />
          <span>{{ t('users.modal.is_head_nurse') }}</span>
        </label>

        <label class="flex min-h-11 items-center gap-3 text-base font-medium text-ink md:col-span-2">
          <input type="checkbox" v-model="form.is_active" class="h-5 w-5 accent-brand-600" />
          <span>{{ t('users.modal.is_active') }}</span>
        </label>
      </FormSection>

    </form>

    <template #footer>
      <ActionBar>
        <template #secondary>
          <AppButton variant="ghost" @click="$emit('close')">{{ t('users.modal.cancel') }}</AppButton>
        </template>
        <AppButton type="submit" form="userForm">{{ isEditing ? t('users.modal.update') : t('users.modal.create') }}</AppButton>
      </ActionBar>
    </template>
  </FullScreenPanel>
</template>

<script setup>
import { reactive, computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { EyeIcon, EyeSlashIcon } from '@heroicons/vue/24/outline'
import { AppButton, FormField, FormSection, ActionBar, FullScreenPanel } from '@/components/ui'

const { t } = useI18n()

// Style commun des champs : zone tactile >= 44 px, focus visible.
const fieldClass = 'block w-full min-h-11 lg:min-h-10 rounded-control border border-tone-neutral-border bg-white px-3 text-base text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600'

const props = defineProps({
  userToEdit: Object,
  applicationRoles: { type: Array, required: true },
  medicalSpecialties: { type: Array, required: true }
})

const emit = defineEmits(['close', 'save'])
const isEditing = computed(() => !!props.userToEdit)
const showPassword = ref(false)

const GROUP_MAPPING = {
  app_admin: ['admin', 'promoteur', 'Psychologist', 'SpiritualCounsellor', 'ToxicoManager', 'Assistant', 'StockController', 'ProductionManager'],
  app_medical: ['medecin', 'nurse'],
  app_secretaire: ['secretaire'],
  app_laborantin: ['laborantin']
}

const form = reactive({
  id: null,
  username: '',
  firstName: '',
  lastName: '',
  email: '',
  phone: '',
  password: '',
  postgres_role: 'app_medical',
  role_id: null,
  specialty_id: null,
  is_active: true,
  is_head_nurse: false
})

// --- LOGIQUE METIER CORRIGÉE ---

const availableRoles = computed(() => {
  const allowedNames = GROUP_MAPPING[form.postgres_role] || []
  return props.applicationRoles.filter(r => allowedNames.includes(r.role_name))
})

// 🟢 CORRECTION CRITIQUE POUR L'AFFICHAGE DE LA SPÉCIALITÉ
const showSpecialtyField = computed(() => {
  // 1. Doit être groupe médical
  if (form.postgres_role !== 'app_medical') return false
  
  // 2. Doit avoir un rôle sélectionné
  if (!form.role_id) return false
  
  // 3. On trouve l'objet Rôle complet
  // On compare de manière souple : (ID du rôle === ID du formulaire)
  const selectedRole = props.applicationRoles.find(r => 
    (r.id === form.role_id) || (r.role_id === form.role_id)
  )
  
  // DEBUG : Affiche ça dans la console si ça ne marche pas
  // console.log("Role selectionné:", selectedRole, "ID Form:", form.role_id);

  if (!selectedRole) return false;

  // 4. On vérifie si c'est 'medecin' (insensible à la casse)
  const name = (selectedRole.role_name || '').toLowerCase().trim();
  return name === 'medecin';
})

const showHeadNurseField = computed(() => {
  const selectedRole = props.applicationRoles.find(
    (r) => (r.id === form.role_id) || (r.role_id === form.role_id)
  )
  if (!selectedRole) return false
  return (selectedRole.role_name || '').toLowerCase().trim() === 'nurse'
})

// --- EVENEMENTS ---

const handlePostgresRoleChange = () => {
  form.role_id = null
  form.specialty_id = null
}

const handleRoleChange = () => {
  if (!showSpecialtyField.value) {
    form.specialty_id = null
  }
  if (!showHeadNurseField.value) {
    form.is_head_nurse = false
  }
}

const prettyRole = (name) => {
  const map = {
    admin: 'Administrateur',
    promoteur: 'Promoteur',
    medecin: 'Médecin',
    nurse: 'Infirmier(e)',
    secretaire: 'Secrétaire',
    laborantin: 'Laborantin',
    Psychologist: 'Psychologue',
    SpiritualCounsellor: 'Conseiller Spirituel',
    ToxicoManager: 'Resp. Toxicomanie',
    Assistant: 'Assistant',
    StockController: 'Contrôleur de stock',
    ProductionManager: 'Responsable de production'
  }
  return map[name] || name
}

// --- INITIALISATION ---

onMounted(() => {
  if (props.userToEdit) {
    const u = props.userToEdit
    Object.assign(form, {
      id: u.id,
      username: u.username,
      firstName: u.firstName,
      lastName: u.lastName,
      email: u.email,
      phone: u.phone,
      postgres_role: u.postgres_role,
      role_id: u.role_id,
      specialty_id: u.specialty_id,
      is_active: u.isActive,
      is_head_nurse: u.isHeadNurse || false
    })
  }
})

const handleSubmit = () => {
  const payload = { ...form }
  if (isEditing.value && !form.password) delete payload.password
  emit('save', payload)
}
</script>
