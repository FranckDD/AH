import api from '@/services/api';
import { photoRequestUrl } from '@/utils/photoRequestUrl';

// Photos produit : image servie derriere authentification, donc recuperee
// en blob puis exposee en URL d'objet. Cache memoire + Cache API du
// navigateur, cle /pharmacy/{id}/photo?v={version}. Jamais d'exception
// vers l'UI pour la lecture : echec ou 404 -> null.
const CACHE_NAME = 'product-photos-v1';
const memory = new Map();

const keyOf = (id, version) => photoRequestUrl(id, version);

async function openCache() {
    try {
        return typeof caches !== 'undefined' ? await caches.open(CACHE_NAME) : null;
    } catch {
        return null;
    }
}

export const ProductPhotoGateway = {
    async getPhotoUrl(medicationId, version) {
        const key = keyOf(medicationId, version);
        if (memory.has(key)) return memory.get(key);
        try {
            const cache = await openCache();
            let blob = null;
            if (cache) {
                const hit = await cache.match(key);
                if (hit) blob = await hit.blob();
            }
            if (!blob) {
                const resp = await api.get(photoRequestUrl(medicationId, version), { responseType: 'blob' });
                blob = resp.data;
                if (cache) {
                    try { await cache.put(key, new Response(blob)); } catch { /* cache facultatif */ }
                }
            }
            const url = URL.createObjectURL(blob);
            memory.set(key, url);
            return url;
        } catch {
            return null;
        }
    },

    async uploadPhoto(medicationId, file) {
        const form = new FormData();
        form.append('file', file);
        const resp = await api.put(`/pharmacy/${medicationId}/photo`, form, {
            headers: { 'Content-Type': 'multipart/form-data' },
        });
        return resp.data;
    },

    async deletePhoto(medicationId) {
        const resp = await api.delete(`/pharmacy/${medicationId}/photo`);
        return resp.data;
    },
};
