<template>
  <AppShell
    :menu-groups="menuGroups"
    :bell-roles="['medecin', 'nurse']"
    brand-fallback="AH2 Médical"
    sidebar-id="medical-sidebar"
    :palette="paletteForRole(authStore.userRole)"
  />
</template>

<script setup>
// Navigation propre a la fenetre medicale (medecin + nurse partagent le meme cadre) - pas de filtrage par
// role ici, contrairement a MainLayout.vue : ce cadre n'est jamais charge par un autre role (garde deja faite
// par le routeur, meta.roles). Tout le gabarit (menu, barre du haut, tiroir) vit dans AppShell.vue.
import AppShell from '@/components/layout/AppShell.vue';
import { useAuthStore } from '@/stores/auth';
import { paletteForRole } from '@/design/navPalettes';
import {
  CalendarIcon,
  CalendarDaysIcon,
  TagIcon,
  HeartIcon,
  UserGroupIcon,
  ChartBarIcon,
  BeakerIcon,
  ExclamationTriangleIcon,
  BuildingOffice2Icon
} from '@heroicons/vue/24/outline';

const authStore = useAuthStore();

// Intertitres de la refonte UX : activity / medical / followup.
const menuGroups = [
  {
    key: 'activity',
    labelKey: 'medicalShell.sections.activity',
    items: [
      { path: '/medical/appointments', labelKey: 'appointments.title', icon: CalendarIcon },
      { path: '/medical/patients', labelKey: 'patients.title', icon: UserGroupIcon },
      { path: '/medical/hospitalizations', labelKey: 'hospitalization.title', icon: BuildingOffice2Icon },
      { path: '/medical/nurse-shifts', labelKey: 'nurseShift.title', icon: CalendarDaysIcon },
    ],
  },
  {
    key: 'medical',
    labelKey: 'medicalShell.sections.medical',
    items: [
      { path: '/medical/prescriptions', labelKey: 'prescriptions.title', icon: TagIcon },
      { path: '/medical/medical-records', labelKey: 'medicalRecords.title', icon: HeartIcon },
      { path: '/medical/lab-results', labelKey: 'lab.nav.medical_results', icon: BeakerIcon },
    ],
  },
  {
    key: 'followup',
    labelKey: 'medicalShell.sections.followup',
    items: [
      { path: '/medical/doctors', labelKey: 'doctorKpi.title', icon: ChartBarIcon },
      {
        path: '/medical/sync-failures',
        labelKey: 'secretariat.nav.sync_failures',
        icon: ExclamationTriangleIcon,
        onlyWhenQuarantine: true,
      },
    ],
  },
];
</script>
