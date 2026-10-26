// Remplace les alert() du navigateur : un bandeau (toast) dans la langue de l'interface.
import i18n from '@/i18n';
import { useToastStore } from '@/stores/toastStore';

// message deja traduit (ou venant du serveur)
export function notifyText(message, type = 'error') {
    if (!message) return;
    useToastStore().push(String(message), type);
}

// cle i18n + parametres
export function notify(key, params = {}, type = 'error') {
    notifyText(i18n.global.t(key, params), type);
}
