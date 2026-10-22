<script setup>
// Guide de style : joignable uniquement en développement (/dev/styleguide).
// Toutes les données ci-dessous sont des EXEMPLES factices, jamais des données réelles.
import { ref } from 'vue';
import { PlusIcon, CheckIcon } from '@heroicons/vue/20/solid';
import {
    AppButton, AppCard, PageHeader, StatusBadge, EmptyState,
    FormField, FormSection, ActionBar, ResponsiveTable,
} from '@/components/ui';
import { TONES } from '@/design/tones';

const columns = [
    { key: 'name', label: 'Nom (exemple)' },
    { key: 'status', label: 'Statut' },
    { key: 'qty', label: 'Quantité', align: 'right' },
];
const rows = [
    { id: 1, name: 'Exemple A', status: 'success', qty: 12 },
    { id: 2, name: 'Exemple B', status: 'warning', qty: 3 },
    { id: 3, name: 'Exemple C', status: 'danger', qty: 0 },
];
const tableLoading = ref(false);
const emptyRows = ref(false);
const loadingBtn = ref(false);
const fieldError = ref('Ce champ est obligatoire.');
</script>

<template>
    <div class="app-refonte h-full overflow-auto bg-page p-4 md:p-8">
        <PageHeader title="Guide de style" subtitle="Exemple : données factices, visible en développement uniquement.">
            <template #actions>
                <AppButton variant="secondary">Action secondaire</AppButton>
                <AppButton :icon="PlusIcon">Action principale</AppButton>
            </template>
        </PageHeader>

        <div class="grid gap-6">
            <AppCard title="Boutons" subtitle="Hauteur minimale 44 px sous lg">
                <div class="flex flex-wrap gap-3">
                    <AppButton>Principal</AppButton>
                    <AppButton variant="secondary">Secondaire</AppButton>
                    <AppButton variant="danger">Danger</AppButton>
                    <AppButton variant="ghost">Discret</AppButton>
                    <AppButton size="lg" :icon="CheckIcon">Grand</AppButton>
                    <AppButton disabled>Désactivé</AppButton>
                    <AppButton :loading="loadingBtn" @click="loadingBtn = true; setTimeout(() => (loadingBtn = false), 1500)">Chargement (cliquer)</AppButton>
                </div>
            </AppCard>

            <AppCard title="Badges d'état" subtitle="Le point et le texte portent l'état, pas la couleur seule">
                <div class="flex flex-wrap gap-3">
                    <StatusBadge v-for="t in TONES" :key="t" :tone="t" :label="`Exemple ${t}`" />
                </div>
            </AppCard>

            <AppCard title="Formulaire en sections">
                <div class="grid gap-4">
                    <FormSection title="Motif" subtitle="Section non repliable">
                        <FormField id="sg-motif" label="Motif de la consultation" required help="Une phrase suffit." v-slot="{ describedBy }">
                            <input id="sg-motif" :aria-describedby="describedBy" class="min-h-11 rounded-control border border-tone-neutral-border px-3 text-base focus-visible:outline-2 focus-visible:outline-brand-600" />
                        </FormField>
                        <FormField id="sg-err" label="Champ en erreur" required :error="fieldError" v-slot="{ describedBy, invalid }">
                            <input id="sg-err" :aria-describedby="describedBy" :aria-invalid="invalid" class="min-h-11 rounded-control border border-tone-danger-border px-3 text-base focus-visible:outline-2 focus-visible:outline-brand-600" />
                        </FormField>
                    </FormSection>
                    <FormSection title="Notes (repliable)" collapsible :default-open="false">
                        <FormField id="sg-notes" label="Notes" v-slot="{ describedBy }">
                            <textarea id="sg-notes" :aria-describedby="describedBy" rows="3" class="rounded-control border border-tone-neutral-border px-3 py-2 text-base focus-visible:outline-2 focus-visible:outline-brand-600"></textarea>
                        </FormField>
                    </FormSection>
                </div>
                <template #footer>
                    <ActionBar>
                        <template #secondary><AppButton variant="ghost">Annuler</AppButton></template>
                        <AppButton>Enregistrer</AppButton>
                    </ActionBar>
                </template>
            </AppCard>

            <AppCard title="Tableau responsive" subtitle="Cartes sous lg, tableau à partir de lg">
                <template #actions>
                    <AppButton variant="ghost" @click="emptyRows = !emptyRows">Basculer vide</AppButton>
                    <AppButton variant="ghost" @click="tableLoading = !tableLoading">Basculer chargement</AppButton>
                </template>
                <ResponsiveTable :columns="columns" :rows="emptyRows ? [] : rows" :loading="tableLoading">
                    <template #cell-status="{ row }"><StatusBadge :tone="row.status" :label="`Exemple ${row.status}`" /></template>
                    <template #actions="{ row }"><AppButton variant="secondary" size="md">Voir {{ row.name }}</AppButton></template>
                </ResponsiveTable>
            </AppCard>

            <AppCard title="État vide">
                <EmptyState title="Rien à afficher (exemple)" message="Une phrase d'aide qui dit quoi faire ensuite.">
                    <template #action><AppButton :icon="PlusIcon">Créer</AppButton></template>
                </EmptyState>
            </AppCard>
        </div>
    </div>
</template>
