<!-- Reglages du controle quotidien (admin seul : la page ne monte ce composant que pour l'admin). -->
<script setup>
import { reactive, ref, watch, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { AppButton, AppCard, FormField } from '@/components/ui';
import { toneClasses } from '@/design/tones';
import { useReportsStore } from '@/stores/reportsStore';
import { settingsErrors } from '@/utils/reports';
import { describeServerError } from '@/utils/serverError';

const { t } = useI18n();
const store = useReportsStore();
const fieldClass = 'block w-full min-h-11 rounded-control border border-tone-neutral-border bg-white px-3 text-base text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-600';

const form = reactive({ cancelled_sales_threshold: '', adjustment_pending_days: '' });
const errors = ref({});
const saving = ref(false);
const message = ref('');
const failure = ref('');

function fill(s) {
    if (!s) return;
    form.cancelled_sales_threshold = String(s.cancelled_sales_threshold ?? '');
    form.adjustment_pending_days = String(s.adjustment_pending_days ?? '');
}
watch(() => store.settings, fill, { immediate: true });
onMounted(() => store.loadSettings());

async function save() {
    if (saving.value) return;
    message.value = '';
    failure.value = '';
    errors.value = settingsErrors(form);
    if (Object.keys(errors.value).length) return;
    saving.value = true;
    try {
        await store.saveSettings({
            cancelledSalesThreshold: Number(form.cancelled_sales_threshold),
            adjustmentPendingDays: Number(form.adjustment_pending_days),
        });
        message.value = t('reports.settings.saved');
    } catch (e) {
        failure.value = describeServerError(e, t('reports.settings.save_error'));
    } finally {
        saving.value = false;
    }
}
</script>

<template>
    <AppCard :title="t('reports.settings.title')" :subtitle="t('reports.settings.subtitle')">
        <div v-if="store.settingsError" role="alert" class="mb-3 flex flex-wrap items-center gap-3 text-base text-tone-danger-text">
            <span>{{ store.settingsError === 'error' ? t('reports.states.error') : store.settingsError }}</span>
            <AppButton variant="secondary" size="sm" @click="store.loadSettings()">{{ t('reports.states.retry') }}</AppButton>
        </div>
        <form class="grid gap-3 sm:grid-cols-2" novalidate @submit.prevent="save">
            <FormField id="rs-threshold" :label="t('reports.settings.cancelled_sales_threshold')" :help="t('reports.settings.help_threshold')"
                       :error="errors.cancelled_sales_threshold ? t(errors.cancelled_sales_threshold) : ''" v-slot="{ describedBy }">
                <input id="rs-threshold" v-model="form.cancelled_sales_threshold" type="text" inputmode="numeric" autocomplete="off"
                       :aria-invalid="errors.cancelled_sales_threshold ? 'true' : 'false'" :aria-describedby="describedBy" :class="fieldClass" />
            </FormField>
            <FormField id="rs-pending" :label="t('reports.settings.adjustment_pending_days')" :help="t('reports.settings.help_pending')"
                       :error="errors.adjustment_pending_days ? t(errors.adjustment_pending_days) : ''" v-slot="{ describedBy }">
                <input id="rs-pending" v-model="form.adjustment_pending_days" type="text" inputmode="numeric" autocomplete="off"
                       :aria-invalid="errors.adjustment_pending_days ? 'true' : 'false'" :aria-describedby="describedBy" :class="fieldClass" />
            </FormField>
            <div class="flex flex-wrap items-center gap-3 sm:col-span-2">
                <AppButton type="submit" variant="primary" :loading="saving">{{ t('reports.settings.save') }}</AppButton>
                <p v-if="message" role="status" class="rounded-control border px-3 py-2 text-base" :class="toneClasses('success')">{{ message }}</p>
                <p v-if="failure" role="alert" class="rounded-control border px-3 py-2 text-base" :class="toneClasses('danger')">{{ failure }}</p>
            </div>
        </form>
    </AppCard>
</template>
