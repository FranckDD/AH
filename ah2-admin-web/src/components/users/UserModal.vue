<template>
  <div class="fixed inset-0 bg-gray-900 bg-opacity-50 overflow-y-auto h-full w-full z-50 flex items-center justify-center backdrop-blur-sm">
    <div class="relative mx-auto w-full max-w-2xl bg-white shadow-2xl rounded-2xl flex flex-col max-h-[90vh]">

      <div class="flex justify-between items-center p-6 border-b border-gray-100">
        <h3 class="text-xl font-bold text-gray-800">
          {{ isEditing ? t('users.modal.edit_title') : t('users.modal.new_title') }}
        </h3>
        <button @click="$emit('close')" class="text-gray-400 hover:text-gray-600 transition p-2 rounded-full hover:bg-gray-100">
          <span class="text-2xl leading-none">&times;</span>
        </button>
      </div>

      <div class="p-6 overflow-y-auto custom-scrollbar">
        <form @submit.prevent="handleSubmit" id="userForm" class="space-y-6">

          <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div>
              <label class="block text-sm font-semibold text-gray-700 mb-1.5">{{ t('users.modal.firstname') }}</label>
              <input v-model="form.firstName" type="text" required class="w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-green-500 transition" />
            </div>
            <div>
              <label class="block text-sm font-semibold text-gray-700 mb-1.5">{{ t('users.modal.lastname') }}</label>
              <input v-model="form.lastName" type="text" required class="w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-green-500 transition" />
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div>
               <label class="block text-sm font-semibold text-gray-700 mb-1.5">Username</label>
               <input v-model="form.username" type="text" required class="w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-green-500 transition" />
            </div>
            <div>
               <label class="block text-sm font-semibold text-gray-700 mb-1.5">{{ t('users.modal.email') }}</label>
               <input v-model="form.email" type="email" required class="w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-green-500 transition" />
            </div>
          </div>

          <div>
             <label class="block text-sm font-semibold text-gray-700 mb-1.5">{{ t('users.modal.phone') }}</label>
             <input v-model="form.phone" type="tel" class="w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-green-500 transition" />
          </div>

          <div v-if="!isEditing">
            <label class="block text-sm font-semibold text-gray-700 mb-1.5">Mot de passe</label>
            <div class="relative">
                <input 
                    v-model="form.password" 
                    :type="showPassword ? 'text' : 'password'" 
                    required 
                    class="w-full px-4 py-2.5 pr-10 border border-gray-300 rounded-xl focus:ring-2 focus:ring-green-500 transition"
                />
                <button type="button" @click="showPassword = !showPassword" class="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600 focus:outline-none">
                    <EyeIcon v-if="!showPassword" class="h-5 w-5" />
                    <EyeSlashIcon v-else class="h-5 w-5" />
                </button>
            </div>
          </div>
          <div v-else>
             <label class="block text-sm font-semibold text-gray-700 mb-1.5">Nouveau mot de passe (optionnel)</label>
             <div class="relative">
                 <input 
                    v-model="form.password" 
                    :type="showPassword ? 'text' : 'password'" 
                    class="w-full px-4 py-2.5 pr-10 border border-gray-300 rounded-xl focus:ring-2 focus:ring-green-500 bg-gray-50 transition" 
                    placeholder="••••••••" 
                 />
                 <button type="button" @click="showPassword = !showPassword" class="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600 focus:outline-none">
                    <EyeIcon v-if="!showPassword" class="h-5 w-5" />
                    <EyeSlashIcon v-else class="h-5 w-5" />
                </button>
             </div>
          </div>

          <div class="bg-gray-50 p-5 rounded-xl border border-gray-200 space-y-4">
              <h4 class="text-sm font-bold text-gray-900 uppercase tracking-wide border-b border-gray-200 pb-2 mb-2">
                Habilitations
              </h4>
              
              <div>
                <label class="block text-sm font-semibold text-gray-700 mb-1.5">{{ t('users.groups.label') }}</label>
                <select v-model="form.postgres_role" @change="handlePostgresRoleChange" required class="w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-green-500 bg-white">
                    <option value="app_admin">{{ t('users.groups.app_admin') }}</option>
                    <option value="app_medical">{{ t('users.groups.app_medical') }}</option>
                    <option value="app_secretaire">{{ t('users.groups.app_secretaire') }}</option>
                    <option value="app_laborantin">{{ t('users.groups.app_laborantin') }}</option>
                </select>
              </div>

              <div v-if="availableRoles.length">
                <label class="block text-sm font-semibold text-gray-700 mb-1.5">{{ t('users.table.role') }}</label>
                <select v-model="form.role_id" @change="handleRoleChange" required class="w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-green-500 bg-white">
                    <option :value="null" disabled>— Sélectionner un rôle —</option>
                    <option v-for="r in availableRoles" :key="r.id || r.role_id" :value="r.id || r.role_id">
                        {{ prettyRole(r.role_name) }}
                    </option>
                </select>
              </div>

              <div v-if="showSpecialtyField" class="animate-fade-in-down">
                <label class="block text-sm font-semibold text-gray-700 mb-1.5">{{ t('users.specialty.label') }}</label>
                <select v-model="form.specialty_id" required class="w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-green-500 bg-white">
                    <option :value="null" disabled>{{ t('users.specialty.placeholder') }}</option>
                    <option v-for="s in medicalSpecialties" :key="s.specialty_id" :value="s.specialty_id">
                        {{ s.name }}
                    </option>
                </select>
              </div>
          </div>

          <div class="flex items-center">
             <label class="inline-flex items-center cursor-pointer">
                <input type="checkbox" v-model="form.is_active" class="sr-only peer">
                <div class="relative w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-green-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-green-600"></div>
                <span class="ms-3 text-sm font-medium text-gray-900">{{ t('users.modal.is_active') }}</span>
            </label>
          </div>

        </form>
      </div>

      <div class="p-6 border-t border-gray-100 flex justify-end gap-3 bg-gray-50 rounded-b-2xl">
        <button type="button" @click="$emit('close')" class="px-5 py-2.5 bg-white border border-gray-300 text-gray-700 rounded-xl hover:bg-gray-50 font-medium transition shadow-sm">
          {{ t('users.modal.cancel') }}
        </button>
        <button type="submit" form="userForm" class="px-5 py-2.5 bg-green-600 text-white rounded-xl hover:bg-green-700 font-medium shadow-lg shadow-green-200 transition transform active:scale-95">
          {{ isEditing ? t('users.modal.update') : t('users.modal.create') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { EyeIcon, EyeSlashIcon } from '@heroicons/vue/24/outline'

const { t } = useI18n()

const props = defineProps({
  userToEdit: Object,
  applicationRoles: { type: Array, required: true },
  medicalSpecialties: { type: Array, required: true }
})

const emit = defineEmits(['close', 'save'])
const isEditing = computed(() => !!props.userToEdit)
const showPassword = ref(false)

const GROUP_MAPPING = {
  app_admin: ['admin', 'Psychologist', 'SpiritualCounsellor', 'ToxicoManager', 'Assistant'],
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
  is_active: true
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

// --- EVENEMENTS ---

const handlePostgresRoleChange = () => {
  form.role_id = null
  form.specialty_id = null
}

const handleRoleChange = () => {
  if (!showSpecialtyField.value) {
    form.specialty_id = null
  }
}

const prettyRole = (name) => {
  const map = {
    admin: 'Administrateur',
    medecin: 'Médecin',
    nurse: 'Infirmier(e)',
    secretaire: 'Secrétaire',
    laborantin: 'Laborantin',
    Psychologist: 'Psychologue',
    SpiritualCounsellor: 'Conseiller Spirituel',
    ToxicoManager: 'Resp. Toxicomanie',
    Assistant: 'Assistant'
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
      is_active: u.isActive
    })
  }
})

const handleSubmit = () => {
  const payload = { ...form }
  if (isEditing.value && !form.password) delete payload.password
  emit('save', payload)
}
</script>

<style scoped>
.animate-fade-in-down {
  animation: fadeInDown 0.3s ease-out;
}
@keyframes fadeInDown {
  from { opacity: 0; transform: translateY(-10px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>