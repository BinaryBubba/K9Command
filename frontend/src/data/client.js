import api from '../utils/api';

// Data mode:
// - "api": use backend endpoints
// - "mock": use localStorage-backed fake data (default, unblocks UI)
const MODE = (process.env.REACT_APP_DATA_MODE || 'mock').toLowerCase();

const ls = {
  get(key, fallback) {
    try {
      const raw = localStorage.getItem(key);
      return raw ? JSON.parse(raw) : fallback;
    } catch {
      return fallback;
    }
  },
  set(key, value) {
    localStorage.setItem(key, JSON.stringify(value));
  },
};

const KEY_BOOKINGS = 'k9_mock_bookings_v1';
const KEY_INVOICES = 'k9_mock_invoices_v1';

function uid(prefix = 'id') {
  return `${prefix}_${Math.random().toString(16).slice(2)}_${Date.now()}`;
}

function toISODate(d) {
  // store dates as YYYY-MM-DD for stable comparisons
  const dt = new Date(d);
  const y = dt.getFullYear();
  const m = String(dt.getMonth() + 1).padStart(2, '0');
  const day = String(dt.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

function isDateInRange(dayISO, startISO, endISO) {
  return dayISO >= startISO && dayISO <= endISO;
}

// --------------------------
// Mock implementation
// --------------------------
const mock = {
  async listBookings() {
    const bookings = ls.get(KEY_BOOKINGS, []);
    return bookings.sort((a, b) => (a.startDate > b.startDate ? 1 : -1));
  },

  async listBookingsForDay(day) {
    const dayISO = toISODate(day);
    const all = await mock.listBookings();
    return all.filter((b) => isDateInRange(dayISO, b.startDate, b.endDate));
  },

  async createBooking(payload) {
    // payload: { dogs: [], startDate, endDate, notes, approvalMode }
    const bookings = ls.get(KEY_BOOKINGS, []);
    const approvalMode = payload.approvalMode || 'request'; // 'request' | 'instant'

    const booking = {
      id: uid('booking'),
      dogs: payload.dogs || [],
      startDate: toISODate(payload.startDate),
      endDate: toISODate(payload.endDate),
      notes: payload.notes || '',
      status: approvalMode === 'instant' ? 'confirmed' : 'pending',
      total: payload.total ?? 0,
      createdAt: new Date().toISOString(),
    };

    bookings.push(booking);
    ls.set(KEY_BOOKINGS, bookings);

    // Create invoice (paid only if instant + paymentSuccess is passed by caller)
    const invoices = ls.get(KEY_INVOICES, []);
    invoices.push({
      id: uid('inv'),
      bookingId: booking.id,
      amount: booking.total,
      currency: 'USD',
      status: 'unpaid',
      provider: 'square',
      createdAt: new Date().toISOString(),
    });
    ls.set(KEY_INVOICES, invoices);

    return booking;
  },

  async listInvoices() {
    const invoices = ls.get(KEY_INVOICES, []);
    return invoices.sort((a, b) => (a.createdAt < b.createdAt ? 1 : -1));
  },

  async payInvoice(invoiceId, { provider = 'square', method = 'card' } = {}) {
    const invoices = ls.get(KEY_INVOICES, []);
    const idx = invoices.findIndex((i) => i.id === invoiceId);
    if (idx === -1) throw new Error('Invoice not found');

    const inv = invoices[idx];
    invoices[idx] = {
      ...inv,
      status: 'paid',
      provider,
      method,
      paidAt: new Date().toISOString(),
      receiptId: uid('rcpt'),
    };
    ls.set(KEY_INVOICES, invoices);
    return invoices[idx];
  },
};

// --------------------------
// API implementation (thin wrappers)
// --------------------------
const apiImpl = {
  async listBookings() {
    const res = await api.get('/bookings');
    return res.data;
  },

  async listBookingsForDay(day) {
    // If backend doesn't support day filtering yet, caller can filter client-side
    const dayISO = toISODate(day);
    const all = await apiImpl.listBookings();
    return (all || []).filter((b) => isDateInRange(dayISO, b.startDate, b.endDate));
  },

  async createBooking(payload) {
    const res = await api.post('/bookings', payload);
    return res.data;
  },

  async listInvoices() {
    const res = await api.get('/payments/invoices');
    return res.data;
  },

  async payInvoice(invoiceId, payload) {
    const res = await api.post(`/payments/invoices/${invoiceId}/pay`, payload);
    return res.data;
  },
};

export const dataClient = MODE === 'api' ? apiImpl : mock;
export const dataMode = MODE;
