import api from '@/services/api';

export const NurseShiftGateway = {
    async fetchShifts(start, end) {
        return api.get('/nurse-shifts/', { params: { start, end } });
    },

    async fetchActiveNurses() {
        return api.get('/nurse-shifts/nurses');
    },

    async createShift(shiftDate, shiftType, nurseId) {
        return api.post('/nurse-shifts/', {
            shift_date: shiftDate,
            shift_type: shiftType,
            nurse_id: nurseId,
        });
    },

    async deleteShift(shiftId) {
        return api.delete(`/nurse-shifts/${shiftId}`);
    },
};
