import api from '@/services/api';

// Une fonction par route du routeur /spiritual-notes (ecritures en ligne seulement, pas de PowerSync).
// list renvoie { data, total, page, per_page, total_pages } ; les notes portent can_edit (ses propres notes).
export const SpiritualNoteGateway = {
    async list({ page = 1, perPage = 20 } = {}) {
        return (await api.get('/spiritual-notes/', { params: { page, per_page: perPage } })).data;
    },
    async create(body) { return (await api.post('/spiritual-notes/', body)).data; },
    async update(id, body) { return (await api.put(`/spiritual-notes/${id}`, body)).data; },
    async remove(id) { await api.delete(`/spiritual-notes/${id}`); },
};
