<!-- Tableau "Total vendu par produit" : periode de la page, recherche differee (300 ms), type, categorie, tri,
     pages de 50. Les reponses perimees sont ignorees par le magasin (compteur tableSeq). -->
<script setup>
import { ref, computed, watch, onBeforeUnmount } from 'vue';
import { useI18n } from 'vue-i18n';
import { AppButton, AppCard, FormField } from '@/components/ui';
import { useReportsStore } from '@/stores/reportsStore';
import { formatMoney, formatCount, pageRange, PAGE_SIZE } from '@/utils/reports';

const props = defineProps({
    period: { type: Object, required: true },
});
const { t, te } = useI18n();
const store = useReportsStore();

const ITEM_TYPES = ['Medicament', 'Examen', 'Consultation', 'Service'];
const SORTS = ['amount_desc', 'amount_asc', 'quantity_desc', 'quantity_asc', 'name_asc'];
const fieldClass = 'block w-full min-h-11 rounded-control border border-tone-neutral-border bg-white px-3 text-base text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600';

const search = ref('');
const q = ref('');
const itemType = ref('Medicament');
const categoryInput = ref('');
const category = ref('');
const sort = ref('amount_desc');
const offset = ref(0);

let timer = null;
function debounce(fn) {
    clearTimeout(timer);
    timer = setTimeout(fn, 300);
}
watch(search, (v) => debounce(() => { q.value = v.trim(); offset.value = 0; }));
watch(categoryInput, (v) => debounce(() => { category.value = v.trim(); offset.value = 0; }));
watch([itemType, sort], () => { offset.value = 0; });
onBeforeUnmount(() => clearTimeout(timer));

function load() {
    if (!props.period?.from || !props.period?.to) return;
    store.loadTable(props.period, {
        q: q.value, itemType: itemType.value, category: category.value, sort: sort.value, offset: offset.value,
    });
}
watch(() => [props.period.from, props.period.to], () => {
    if (offset.value !== 0) offset.value = 0; else load();
});
watch([q, itemType, category, sort, offset], load, { immediate: true });

const data = computed(() => store.table);
const range = computed(() => pageRange(data.value.offset || 0, data.value.items.length, data.value.total));
const tk = (k) => (k && te(k) ? t(k) : '');
const canPrev = computed(() => offset.value > 0 && !store.tableLoading);
const canNext = computed(() => offset.value + PAGE_SIZE < (data.value.total || 0) && !store.tableLoading);
</script>

<template>
    <AppCard :title="t('reports.table.title')" :subtitle="tk(data.amount_basis) || t('reports.table.amount_before_discount')">
        <div class="mb-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <FormField id="rp-search" :label="t('reports.table.search')" v-slot="{ describedBy }">
                <input id="rp-search" v-model="search" type="search" maxlength="100" autocomplete="off" :aria-describedby="describedBy" :class="fieldClass" />
            </FormField>
            <FormField id="rp-type" :label="t('reports.table.type')" v-slot="{ describedBy }">
                <select id="rp-type" v-model="itemType" :aria-describedby="describedBy" :class="fieldClass">
                    <option v-for="it in ITEM_TYPES" :key="it" :value="it">{{ t(`reports.table.type_${it}`) }}</option>
                </select>
            </FormField>
            <FormField id="rp-category" :label="t('reports.table.category')" v-slot="{ describedBy }">
                <input id="rp-category" v-model="categoryInput" type="text" maxlength="100" autocomplete="off" :aria-describedby="describedBy" :class="fieldClass" />
            </FormField>
            <FormField id="rp-sort" :label="t('reports.table.sort')" v-slot="{ describedBy }">
                <select id="rp-sort" v-model="sort" :aria-describedby="describedBy" :class="fieldClass">
                    <option v-for="s in SORTS" :key="s" :value="s">{{ t(`reports.table.sort_${s}`) }}</option>
                </select>
            </FormField>
        </div>

        <p v-if="store.tableLoading" role="status" class="text-base text-ink-muted">{{ t('reports.states.loading') }}</p>
        <div v-else-if="store.tableError" role="alert" class="flex flex-wrap items-center gap-3 text-base text-tone-danger-text">
            <span>{{ store.tableError === 'error' ? t('reports.states.error') : store.tableError }}</span>
            <AppButton variant="secondary" size="sm" @click="load">{{ t('reports.states.retry') }}</AppButton>
        </div>
        <p v-else-if="!data.items.length" class="text-base text-ink-muted">{{ t('reports.table.empty') }}</p>
        <div v-else class="overflow-x-auto">
            <table class="w-full text-left text-base">
                <thead class="text-sm text-ink-muted">
                    <tr>
                        <th scope="col" class="py-2 pr-3">{{ t('reports.table.col_name') }}</th>
                        <th scope="col" class="py-2 pr-3">{{ t('reports.table.col_category') }}</th>
                        <th scope="col" class="py-2 pr-3 text-right">{{ t('reports.table.col_quantity') }}</th>
                        <th scope="col" class="py-2 text-right">{{ t('reports.table.col_amount') }}</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="(r, i) in data.items" :key="`${r.product_id}-${i}`" class="border-t border-tone-neutral-border">
                        <td class="py-2 pr-3">{{ r.name }}</td>
                        <td class="py-2 pr-3 text-ink-muted">{{ r.category || '' }}</td>
                        <td class="py-2 pr-3 text-right">{{ formatCount(r.quantity) }}</td>
                        <td class="py-2 text-right">{{ formatMoney(r.amount) }}</td>
                    </tr>
                </tbody>
            </table>
        </div>

        <template #footer>
            <div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <p class="text-sm text-ink-muted">{{ tk(data.note_key) || t('reports.table.note_differs_from_cash') }}</p>
                <div class="flex flex-wrap items-center gap-2">
                    <span class="text-sm text-ink-muted" role="status">{{ t('reports.table.range', range) }}</span>
                    <AppButton variant="secondary" size="sm" :disabled="!canPrev" @click="offset = Math.max(0, offset - PAGE_SIZE)">{{ t('reports.table.prev') }}</AppButton>
                    <AppButton variant="secondary" size="sm" :disabled="!canNext" @click="offset = offset + PAGE_SIZE">{{ t('reports.table.next') }}</AppButton>
                </div>
            </div>
        </template>
    </AppCard>
</template>
