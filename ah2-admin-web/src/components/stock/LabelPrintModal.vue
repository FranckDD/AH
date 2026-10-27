<template>
  <FullScreenPanel :title="t('stockLabels.modal_title')" :subtitle="t('stockLabels.modal_subtitle')" wide maximizable @close="$emit('close')">
    <div class="grid gap-4">

      <FormSection :title="t('stockLabels.step_products')">
        <div class="grid gap-3 md:col-span-2">
          <div class="relative">
            <label for="label-search" class="sr-only">{{ t('stockLabels.search') }}</label>
            <MagnifyingGlassIcon class="pointer-events-none absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-ink-muted" aria-hidden="true" />
            <input id="label-search" v-model="searchInput" type="text" :placeholder="t('stockLabels.search')" :class="[fieldClass, 'pl-10']" @input="onSearchInput" />
          </div>

          <p v-if="loadError" role="alert" class="rounded-control border p-3 text-base font-medium" :class="toneClasses('danger')">{{ loadError }}</p>
          <p v-else-if="loading" role="status" class="text-base text-ink-muted">{{ t('stockLabels.loading') }}</p>
          <p v-else-if="products.length === 0" class="text-base text-ink-muted">{{ t('stockLabels.no_results') }}</p>

          <ul class="max-h-72 divide-y divide-tone-neutral-border overflow-auto rounded-control border border-tone-neutral-border bg-white">
            <li v-for="p in products" :key="p.id" class="flex min-h-11 flex-wrap items-center gap-3 px-3 py-2">
              <label class="flex min-w-0 flex-1 items-center gap-3 text-base text-ink" :class="p.barcode ? 'cursor-pointer' : 'opacity-60'">
                <input type="checkbox" class="h-5 w-5 shrink-0 accent-brand-600" :disabled="!p.barcode" :checked="isSelected(p.id)" @change="toggle(p, $event.target.checked)" />
                <span class="min-w-0 truncate font-medium">{{ p.name }}</span>
                <span class="shrink-0 font-mono text-sm text-ink-muted">{{ p.barcode || t('stockLabels.no_code') }}</span>
              </label>
              <div v-if="isSelected(p.id)" class="flex items-center gap-2">
                <label :for="`copies-${p.id}`" class="text-base text-ink">{{ t('stockLabels.copies') }}</label>
                <input :id="`copies-${p.id}`" type="number" min="1" :max="MAX_COPIES" step="1" inputmode="numeric" v-model.number="selected[p.id].copies" :class="[fieldClass, 'w-24 text-right font-mono']" />
              </div>
            </li>
          </ul>
          <p class="text-base text-ink-muted" role="status">{{ t('stockLabels.selected_count', { products: items.length, labels: totalLabels }) }}</p>
        </div>
      </FormSection>

      <FormSection :title="t('stockLabels.step_format')">
        <div class="grid gap-3 md:col-span-2">
          <fieldset class="grid gap-2">
            <legend class="text-base font-medium text-ink">{{ t('stockLabels.mode') }}</legend>
            <label class="flex min-h-11 items-center gap-3 text-base text-ink">
              <input type="radio" name="label-mode" value="roll" v-model="mode" class="h-5 w-5 accent-brand-600" />
              <span>{{ t('stockLabels.mode_roll') }}</span>
            </label>
            <label class="flex min-h-11 items-center gap-3 text-base text-ink">
              <input type="radio" name="label-mode" value="a4" v-model="mode" class="h-5 w-5 accent-brand-600" />
              <span>{{ t('stockLabels.mode_a4') }}</span>
            </label>
          </fieldset>
          <p class="text-base text-ink-muted">{{ t('stockLabels.size_info', { w: size.widthMm, h: size.heightMm }) }}</p>
        </div>
      </FormSection>

      <FormSection :title="t('stockLabels.step_preview')">
        <div class="grid gap-2 md:col-span-2">
          <p v-if="copiesInvalid" role="alert" class="rounded-control border p-3 text-base font-medium" :class="toneClasses('danger')">{{ t('stockLabels.copies_invalid', { max: MAX_COPIES }) }}</p>
          <p v-else-if="pages.length === 0" class="text-base text-ink-muted">{{ t('stockLabels.none_selected') }}</p>
          <template v-else>
            <p class="text-base text-ink-muted">{{ t('stockLabels.pages_count', { pages: pages.length }) }}</p>
            <component :is="'style'">{{ previewCss }}</component>
            <div class="flex flex-wrap gap-3 overflow-auto rounded-control border border-tone-neutral-border bg-tone-neutral-bg p-3" data-testid="label-preview">
              <div v-for="(page, i) in previewPages" :key="i" class="shrink-0 border border-tone-neutral-border bg-white shadow-card" :style="previewStyle(page)" v-html="pageMarkup(page)"></div>
            </div>
            <p v-if="pages.length > previewPages.length" class="text-sm text-ink-muted">{{ t('stockLabels.preview_more', { shown: previewPages.length, total: pages.length }) }}</p>
          </template>
        </div>
      </FormSection>

      <p v-if="printError" role="alert" class="rounded-control border p-3 text-base font-medium" :class="toneClasses('danger')">{{ printError }}</p>
    </div>

    <template #footer>
      <ActionBar>
        <template #secondary>
          <AppButton variant="ghost" @click="$emit('close')">{{ t('common.cancel') }}</AppButton>
        </template>
        <AppButton :icon="PrinterIcon" :disabled="!canPrint" @click="print">{{ t('stockLabels.print') }}</AppButton>
      </ActionBar>
    </template>
  </FullScreenPanel>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount } from 'vue';
import { useI18n } from 'vue-i18n';
import { MagnifyingGlassIcon, PrinterIcon } from '@heroicons/vue/24/outline';
import { AppButton, FormSection, ActionBar, FullScreenPanel } from '@/components/ui';
import { toneClasses } from '@/design/tones';
import api from '@/services/api';
import { useConfigStore } from '@/stores/configStore';
import { barcodeSvgMarkup } from '@/utils/barcodeSvg';
import { buildLabelPages, MAX_COPIES, MIN_LABEL_MM, MAX_LABEL_MM } from '@/utils/labelLayout';
import { labelPagesBody, labelPagesCss, labelPrintDocument } from '@/utils/labelPrintHtml';
import { describeServerError } from '@/utils/serverError';

// preselect : produit { id, name, barcode } deja coche a l'ouverture (raccourci de la ligne du stock).
const props = defineProps({ preselect: { type: Object, default: null } });
defineEmits(['close']);
const { t } = useI18n();
const configStore = useConfigStore();

const fieldClass = 'block w-full min-h-11 rounded-control border border-tone-neutral-border bg-white px-3 text-base text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600';

const searchInput = ref('');
const products = ref([]);
const loading = ref(false);
const loadError = ref('');
const printError = ref('');
const mode = ref('roll');
const selected = reactive({});

if (props.preselect && props.preselect.barcode) {
    selected[props.preselect.id] = { name: props.preselect.name, barcode: props.preselect.barcode, copies: 1 };
}

const inRange = (v) => typeof v === 'number' && Number.isFinite(v) && v >= MIN_LABEL_MM && v <= MAX_LABEL_MM;
// Taille lue de la configuration de la structure ; 50 x 30 mm si absente ou hors limites.
const size = computed(() => {
    const info = configStore.structureInfo || {};
    const w = Number(info.label_width_mm);
    const h = Number(info.label_height_mm);
    return { widthMm: inRange(w) ? w : 50, heightMm: inRange(h) ? h : 30 };
});

const isSelected = (id) => !!selected[id];
const toggle = (p, on) => {
    if (on) selected[p.id] = { name: p.name, barcode: p.barcode, copies: selected[p.id]?.copies || 1 };
    else delete selected[p.id];
};

const items = computed(() => Object.values(selected));
const copiesValid = (c) => Number.isInteger(c) && c >= 1 && c <= MAX_COPIES;
const copiesInvalid = computed(() => items.value.some((i) => !copiesValid(i.copies)));
const totalLabels = computed(() => items.value.reduce((n, i) => n + (copiesValid(i.copies) ? i.copies : 0), 0));

const pages = computed(() => {
    if (!items.value.length || copiesInvalid.value) return [];
    try {
        return buildLabelPages(items.value, size.value, mode.value);
    } catch {
        return [];
    }
});
const previewPages = computed(() => pages.value.slice(0, mode.value === 'a4' ? 2 : 6));
const canPrint = computed(() => pages.value.length > 0);

// Apercu : meme balisage que l'impression, a l'echelle de l'ecran (a4 reduit de moitie).
const barcodeCache = new Map();
const renderBarcode = (code) => {
    if (!barcodeCache.has(code)) barcodeCache.set(code, barcodeSvgMarkup(code));
    return barcodeCache.get(code);
};
const previewCss = computed(() => labelPagesCss(pages.value, { preview: true }));
const pageMarkup = (page) => labelPagesBody([page], renderBarcode);
const previewStyle = (page) => (page.mode === 'a4' ? 'zoom:0.5' : '');

let searchTimer = null;
const onSearchInput = () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(loadProducts, 300);
};

const loadProducts = async () => {
    loading.value = true;
    loadError.value = '';
    try {
        const params = { page: 1, per_page: 200 };
        if (searchInput.value.trim()) params.term = searchInput.value.trim();
        const resp = await api.get('/pharmacy/', { params });
        products.value = (resp.data?.data || []).map((p) => ({ id: p.medication_id, name: p.drug_name, barcode: p.barcode || '' }));
    } catch (err) {
        loadError.value = describeServerError(err, t('stockLabels.load_error'));
    } finally {
        loading.value = false;
    }
};

onMounted(() => {
    loadProducts();
    configStore.fetchStructureInfo();
});
onBeforeUnmount(() => clearTimeout(searchTimer));

// Impression : iframe cache contenant les pages et la regle @page, puis boite d'impression du navigateur.
const print = () => {
    printError.value = '';
    if (!canPrint.value) return;
    let frame = null;
    const cleanup = () => { if (frame && frame.parentNode) frame.parentNode.removeChild(frame); frame = null; };
    try {
        frame = document.createElement('iframe');
        frame.setAttribute('aria-hidden', 'true');
        frame.style.cssText = 'position:fixed;right:0;bottom:0;width:0;height:0;border:0;visibility:hidden';
        document.body.appendChild(frame);
        const doc = frame.contentWindow.document;
        doc.open();
        doc.write(labelPrintDocument(pages.value, renderBarcode));
        doc.close();
        frame.contentWindow.addEventListener('afterprint', cleanup);
        setTimeout(() => {
            try {
                frame.contentWindow.focus();
                frame.contentWindow.print();
            } catch {
                printError.value = t('stockLabels.print_failed');
                cleanup();
            }
        }, 100);
        // Filet de securite si afterprint ne se declenche pas.
        setTimeout(cleanup, 120000);
    } catch {
        printError.value = t('stockLabels.print_failed');
        cleanup();
    }
};
</script>
