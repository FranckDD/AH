<script setup>
import { computed } from 'vue';
import { normalizeColumns, alignClass } from '@/utils/ui';
import EmptyState from './EmptyState.vue';

const props = defineProps({
    columns: { type: Array, default: () => [] },
    rows: { type: Array, default: () => [] },
    rowKey: { type: String, default: 'id' },
    loading: { type: Boolean, default: false },
    emptyTitle: { type: String, default: '' },
    emptyMessage: { type: String, default: '' },
});

const cols = computed(() => normalizeColumns(props.columns));
const keyOf = (row, i) => row?.[props.rowKey] ?? i;
</script>

<template>
    <div class="rounded-card border border-tone-neutral-border bg-white">
        <p v-if="loading" class="px-4 py-8 text-center text-base text-ink-muted" role="status">{{ $t('ui.loading') }}</p>

        <EmptyState
            v-else-if="!rows.length"
            :title="emptyTitle || $t('ui.noResults')"
            :message="emptyMessage || $t('ui.noResultsHelp')"
        />

        <template v-else>
            <!-- PC (lg et plus) : vrai tableau, en-tête collant -->
            <div class="hidden max-h-[70vh] overflow-auto lg:block">
                <table class="w-full border-collapse text-base">
                    <thead>
                        <tr>
                            <th
                                v-for="c in cols"
                                :key="c.key"
                                scope="col"
                                :class="['sticky top-0 border-b border-tone-neutral-border bg-tone-neutral-bg px-4 py-3 text-sm font-semibold text-tone-neutral-text', alignClass(c.align), c.class]"
                            >{{ c.label }}</th>
                            <th v-if="$slots.actions" scope="col" class="sticky top-0 border-b border-tone-neutral-border bg-tone-neutral-bg px-4 py-3"><span class="sr-only">{{ $t('ui.actions') }}</span></th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr v-for="(row, i) in rows" :key="keyOf(row, i)" class="border-b border-tone-neutral-border last:border-b-0 hover:bg-brand-50">
                            <td v-for="c in cols" :key="c.key" :class="['px-4 py-3 text-ink', alignClass(c.align), c.class]">
                                <slot :name="`cell-${c.key}`" :row="row">{{ row[c.key] }}</slot>
                            </td>
                            <td v-if="$slots.actions" class="px-4 py-3 text-right"><div class="flex justify-end gap-2"><slot name="actions" :row="row" /></div></td>
                        </tr>
                    </tbody>
                </table>
            </div>

            <!-- Téléphone et tablette : cartes empilées (2 colonnes dès md) -->
            <ul class="grid gap-3 p-3 md:grid-cols-2 lg:hidden">
                <li v-for="(row, i) in rows" :key="keyOf(row, i)" class="rounded-card border border-tone-neutral-border p-4">
                    <slot name="card" :row="row">
                        <dl class="grid gap-2">
                            <div v-for="c in cols" :key="c.key" class="flex flex-col">
                                <dt class="text-sm text-ink-muted">{{ c.label }}</dt>
                                <dd class="text-base text-ink"><slot :name="`cell-${c.key}`" :row="row">{{ row[c.key] }}</slot></dd>
                            </div>
                        </dl>
                    </slot>
                    <div v-if="$slots.actions" class="mt-3 flex flex-col gap-2 [&>*]:w-full"><slot name="actions" :row="row" /></div>
                </li>
            </ul>
        </template>
    </div>
</template>
