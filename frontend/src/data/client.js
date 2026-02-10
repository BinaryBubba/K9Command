import api from '../utils/api';

// Data mode:
// - "api": use backend endpoints
// - "mock": use localStorage-backed fake data (default, unblocks UI)
const MODE = (process.env.REACT_APP_DATA_MODE || 'mock').toLowerCase();

// ========================
// LocalStorage Helpers
// ========================
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

// Storage keys
const KEYS = {
  BOOKINGS: 'k9_mock_bookings_v1',
  INVOICES: 'k9_mock_invoices_v1',
  DOGS: 'k9_mock_dogs_v1',
  EMAIL_OUTBOX: 'k9_mock_email_outbox_v1',
  EMAIL_TEMPLATES: 'k9_mock_email_templates_v1',
  STAFF_REQUESTS: 'k9_mock_staff_requests_v1',
  USERS: 'k9_mock_users_v1',
};

// ========================
// Utilities
// ========================
function uid(prefix = 'id') {
  return `${prefix}_${Math.random().toString(16).slice(2)}_${Date.now()}`;
}

export function toISODate(d) {
  if (!d) return null;
  const dt = new Date(d);
  if (isNaN(dt.getTime())) return null;
  const y = dt.getFullYear();
  const m = String(dt.getMonth() + 1).padStart(2, '0');
  const day = String(dt.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

function isDateInRange(dayISO, startISO, endISO) {
  return dayISO >= startISO && dayISO <= endISO;
}

// Get current user from localStorage (set by auth)
function getCurrentUser() {
  try {
    const raw = localStorage.getItem('user');
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

// Normalize booking to consistent format
function normalizeBooking(b) {
  return {
    ...b,
    id: b.id,
    startDate: toISODate(b.startDate || b.check_in_date || b.checkInDate),
    endDate: toISODate(b.endDate || b.check_out_date || b.checkOutDate),
    status: b.status || 'pending',
    dogs: b.dogs || b.dog_names || [],
    dogIds: b.dogIds || b.dog_ids || [],
    notes: b.notes || '',
    total: typeof b.total === 'number' ? b.total : (b.total_cents ? b.total_cents / 100 : 0),
    customerId: b.customerId || b.customer_id || b.user_id,
    createdAt: b.createdAt || b.created_at || new Date().toISOString(),
  };
}

// ========================
// Mock Implementation
// ========================
const mock = {
  // ---------- BOOKINGS ----------
  async listBookings() {
    const user = getCurrentUser();
    const bookings = ls.get(KEYS.BOOKINGS, []);
    // Customer scoping: only return bookings for logged-in customer
    const filtered = user?.role === 'customer' 
      ? bookings.filter(b => b.customerId === user.id || b.customer_id === user.id)
      : bookings;
    return filtered.map(normalizeBooking).sort((a, b) => (a.startDate > b.startDate ? 1 : -1));
  },

  async listBookingsForDay(day) {
    const dayISO = toISODate(day);
    const all = await mock.listBookings();
    return all.filter((b) => isDateInRange(dayISO, b.startDate, b.endDate));
  },

  async getBooking(bookingId) {
    const bookings = ls.get(KEYS.BOOKINGS, []);
    const booking = bookings.find(b => b.id === bookingId);
    return booking ? normalizeBooking(booking) : null;
  },

  async createBooking(payload) {
    const user = getCurrentUser();
    const bookings = ls.get(KEYS.BOOKINGS, []);
    const approvalMode = payload.approvalMode || 'request';

    // Get dog names for the booking
    const dogs = ls.get(KEYS.DOGS, []);
    const dogNames = (payload.dogIds || payload.dog_ids || []).map(id => {
      const dog = dogs.find(d => d.id === id);
      return dog?.name || 'Unknown';
    });

    const booking = {
      id: uid('booking'),
      customerId: user?.id,
      customer_id: user?.id,
      dogIds: payload.dogIds || payload.dog_ids || [],
      dogs: dogNames,
      startDate: toISODate(payload.startDate || payload.check_in_date),
      endDate: toISODate(payload.endDate || payload.check_out_date),
      notes: payload.notes || '',
      status: approvalMode === 'instant' ? 'confirmed' : 'pending',
      total: payload.total ?? 0,
      createdAt: new Date().toISOString(),
    };

    bookings.push(booking);
    ls.set(KEYS.BOOKINGS, bookings);

    // Create invoice
    const invoices = ls.get(KEYS.INVOICES, []);
    invoices.push({
      id: uid('inv'),
      bookingId: booking.id,
      amount: booking.total,
      currency: 'USD',
      status: 'unpaid',
      provider: 'square',
      createdAt: new Date().toISOString(),
    });
    ls.set(KEYS.INVOICES, invoices);

    // Send confirmation email (mock - write to outbox)
    await mock.sendBookingConfirmationEmail(booking);

    return normalizeBooking(booking);
  },

  async updateBooking(bookingId, updates) {
    const bookings = ls.get(KEYS.BOOKINGS, []);
    const idx = bookings.findIndex(b => b.id === bookingId);
    if (idx === -1) throw new Error('Booking not found');

    const booking = bookings[idx];
    const user = getCurrentUser();

    // Enforce rules: editable only if PENDING/CONFIRMED and check-in > 24h away
    const allowedStatuses = ['pending', 'confirmed'];
    if (!allowedStatuses.includes(booking.status)) {
      throw new Error('Booking cannot be modified in current status');
    }

    const checkInDate = new Date(booking.startDate);
    const now = new Date();
    const hoursUntilCheckIn = (checkInDate - now) / (1000 * 60 * 60);
    if (hoursUntilCheckIn < 24) {
      throw new Error('Booking cannot be modified within 24 hours of check-in');
    }

    // Customer can only modify their own bookings
    if (user?.role === 'customer' && booking.customerId !== user.id) {
      throw new Error('Not authorized to modify this booking');
    }

    // Get dog names if dogIds changed
    let dogNames = booking.dogs;
    if (updates.dogIds || updates.dog_ids) {
      const dogs = ls.get(KEYS.DOGS, []);
      dogNames = (updates.dogIds || updates.dog_ids).map(id => {
        const dog = dogs.find(d => d.id === id);
        return dog?.name || 'Unknown';
      });
    }

    const updated = {
      ...booking,
      ...updates,
      dogs: dogNames,
      startDate: updates.startDate ? toISODate(updates.startDate) : booking.startDate,
      endDate: updates.endDate ? toISODate(updates.endDate) : booking.endDate,
      updatedAt: new Date().toISOString(),
    };

    bookings[idx] = updated;
    ls.set(KEYS.BOOKINGS, bookings);

    return normalizeBooking(updated);
  },

  async cancelBooking(bookingId) {
    return mock.updateBooking(bookingId, { status: 'cancelled' });
  },

  // ---------- DOGS ----------
  async listDogs() {
    const user = getCurrentUser();
    const dogs = ls.get(KEYS.DOGS, []);
    // Customer scoping
    return user?.role === 'customer'
      ? dogs.filter(d => d.ownerId === user.id || d.owner_id === user.id)
      : dogs;
  },

  async getDog(dogId) {
    const dogs = ls.get(KEYS.DOGS, []);
    return dogs.find(d => d.id === dogId) || null;
  },

  async createDog(payload) {
    const user = getCurrentUser();
    const dogs = ls.get(KEYS.DOGS, []);

    const dog = {
      id: uid('dog'),
      ownerId: user?.id,
      owner_id: user?.id,
      name: payload.name,
      breed: payload.breed || '',
      age: payload.age || null,
      birthday: payload.birthday || null,
      weight: payload.weight || null,
      feedingInstructions: payload.feedingInstructions || payload.feeding_instructions || '',
      medications: payload.medications || '',
      behaviorNotes: payload.behaviorNotes || payload.behavior_notes || '',
      specialNeeds: payload.specialNeeds || payload.special_needs || '',
      photoUrl: payload.photoUrl || payload.photo_url || null,
      vaccinations: payload.vaccinations || [],
      createdAt: new Date().toISOString(),
    };

    dogs.push(dog);
    ls.set(KEYS.DOGS, dogs);
    return dog;
  },

  async updateDog(dogId, updates) {
    const dogs = ls.get(KEYS.DOGS, []);
    const idx = dogs.findIndex(d => d.id === dogId);
    if (idx === -1) throw new Error('Dog not found');

    const user = getCurrentUser();
    const dog = dogs[idx];

    // Customer can only modify their own dogs
    if (user?.role === 'customer' && dog.ownerId !== user.id && dog.owner_id !== user.id) {
      throw new Error('Not authorized to modify this dog');
    }

    const updated = {
      ...dog,
      ...updates,
      updatedAt: new Date().toISOString(),
    };

    dogs[idx] = updated;
    ls.set(KEYS.DOGS, dogs);
    return updated;
  },

  async deleteDog(dogId) {
    const dogs = ls.get(KEYS.DOGS, []);
    const idx = dogs.findIndex(d => d.id === dogId);
    if (idx === -1) throw new Error('Dog not found');

    dogs.splice(idx, 1);
    ls.set(KEYS.DOGS, dogs);
    return { success: true };
  },

  // ---------- INVOICES ----------
  async listInvoices() {
    const user = getCurrentUser();
    const invoices = ls.get(KEYS.INVOICES, []);
    const bookings = ls.get(KEYS.BOOKINGS, []);

    // Customer scoping
    if (user?.role === 'customer') {
      const customerBookingIds = bookings
        .filter(b => b.customerId === user.id || b.customer_id === user.id)
        .map(b => b.id);
      return invoices
        .filter(i => customerBookingIds.includes(i.bookingId))
        .sort((a, b) => (a.createdAt < b.createdAt ? 1 : -1));
    }
    return invoices.sort((a, b) => (a.createdAt < b.createdAt ? 1 : -1));
  },

  async payInvoice(invoiceId, { provider = 'square', method = 'card' } = {}) {
    const invoices = ls.get(KEYS.INVOICES, []);
    const idx = invoices.findIndex((i) => i.id === invoiceId);
    if (idx === -1) throw new Error('Invoice not found');

    invoices[idx] = {
      ...invoices[idx],
      status: 'paid',
      provider,
      method,
      paidAt: new Date().toISOString(),
      receiptId: uid('rcpt'),
    };
    ls.set(KEYS.INVOICES, invoices);
    return invoices[idx];
  },

  // ---------- EMAIL ----------
  async sendBookingConfirmationEmail(booking) {
    const templates = ls.get(KEYS.EMAIL_TEMPLATES, {});
    const template = templates.booking_confirmation || {
      subject: 'Booking Confirmation - K9Command',
      body: `Hello,\n\nYour booking has been ${booking.status === 'confirmed' ? 'confirmed' : 'received'}!\n\nDetails:\n- Check-in: {{startDate}}\n- Check-out: {{endDate}}\n- Dogs: {{dogs}}\n\nThank you for choosing K9Command!\n\nBest regards,\nThe K9Command Team`
    };

    const user = getCurrentUser();
    const email = {
      id: uid('email'),
      to: user?.email || 'customer@example.com',
      subject: template.subject.replace(/\{\{(\w+)\}\}/g, (_, key) => booking[key] || ''),
      body: template.body
        .replace(/\{\{startDate\}\}/g, booking.startDate)
        .replace(/\{\{endDate\}\}/g, booking.endDate)
        .replace(/\{\{dogs\}\}/g, (booking.dogs || []).join(', '))
        .replace(/\{\{status\}\}/g, booking.status)
        .replace(/\{\{(\w+)\}\}/g, (_, key) => booking[key] || ''),
      type: 'booking_confirmation',
      bookingId: booking.id,
      sentAt: new Date().toISOString(),
      status: 'sent',
    };

    const outbox = ls.get(KEYS.EMAIL_OUTBOX, []);
    outbox.push(email);
    ls.set(KEYS.EMAIL_OUTBOX, outbox);
    return email;
  },

  async getEmailOutbox() {
    return ls.get(KEYS.EMAIL_OUTBOX, []).sort((a, b) => (a.sentAt < b.sentAt ? 1 : -1));
  },

  async getEmailTemplates() {
    return ls.get(KEYS.EMAIL_TEMPLATES, {
      booking_confirmation: {
        subject: 'Booking Confirmation - K9Command',
        body: 'Hello,\n\nYour booking has been {{status}}!\n\nDetails:\n- Check-in: {{startDate}}\n- Check-out: {{endDate}}\n- Dogs: {{dogs}}\n\nThank you for choosing K9Command!\n\nBest regards,\nThe K9Command Team'
      }
    });
  },

  async updateEmailTemplate(templateName, { subject, body }) {
    const templates = ls.get(KEYS.EMAIL_TEMPLATES, {});
    templates[templateName] = { subject, body, updatedAt: new Date().toISOString() };
    ls.set(KEYS.EMAIL_TEMPLATES, templates);
    return templates[templateName];
  },

  async sendTestEmail(templateName, testEmail) {
    const templates = await mock.getEmailTemplates();
    const template = templates[templateName];
    if (!template) throw new Error('Template not found');

    const email = {
      id: uid('email'),
      to: testEmail,
      subject: `[TEST] ${template.subject}`,
      body: template.body,
      type: 'test',
      sentAt: new Date().toISOString(),
      status: 'sent',
    };

    const outbox = ls.get(KEYS.EMAIL_OUTBOX, []);
    outbox.push(email);
    ls.set(KEYS.EMAIL_OUTBOX, outbox);
    return email;
  },

  // ---------- STAFF REQUESTS & ACCOUNT GOVERNANCE ----------
  async requestStaffAccount(data) {
    const requests = ls.get(KEYS.STAFF_REQUESTS, []);
    const request = {
      id: uid('staff_req'),
      email: data.email,
      fullName: data.fullName || data.full_name,
      status: 'pending',
      createdAt: new Date().toISOString(),
    };
    requests.push(request);
    ls.set(KEYS.STAFF_REQUESTS, requests);
    return request;
  },

  async listStaffRequests() {
    return ls.get(KEYS.STAFF_REQUESTS, []).sort((a, b) => (a.createdAt < b.createdAt ? 1 : -1));
  },

  async approveStaffRequest(requestId) {
    const requests = ls.get(KEYS.STAFF_REQUESTS, []);
    const idx = requests.findIndex(r => r.id === requestId);
    if (idx === -1) throw new Error('Request not found');

    requests[idx] = { ...requests[idx], status: 'approved', approvedAt: new Date().toISOString() };
    ls.set(KEYS.STAFF_REQUESTS, requests);
    return requests[idx];
  },

  async rejectStaffRequest(requestId, reason) {
    const requests = ls.get(KEYS.STAFF_REQUESTS, []);
    const idx = requests.findIndex(r => r.id === requestId);
    if (idx === -1) throw new Error('Request not found');

    requests[idx] = { ...requests[idx], status: 'rejected', reason, rejectedAt: new Date().toISOString() };
    ls.set(KEYS.STAFF_REQUESTS, requests);
    return requests[idx];
  },

  async isOwner(userId) {
    // First admin is owner
    const users = ls.get(KEYS.USERS, []);
    const admins = users.filter(u => u.role === 'admin').sort((a, b) => 
      new Date(a.createdAt) - new Date(b.createdAt)
    );
    return admins.length > 0 && admins[0].id === userId;
  },

  async createAdminAccount(data) {
    const user = getCurrentUser();
    const isOwner = await mock.isOwner(user?.id);
    if (!isOwner) {
      throw new Error('Only the owner can create admin accounts');
    }

    const users = ls.get(KEYS.USERS, []);
    const newAdmin = {
      id: uid('user'),
      email: data.email,
      fullName: data.fullName || data.full_name,
      role: 'admin',
      createdAt: new Date().toISOString(),
      createdBy: user?.id,
    };
    users.push(newAdmin);
    ls.set(KEYS.USERS, users);
    return newAdmin;
  },

  // ---------- DASHBOARD STATS ----------
  async getDashboardStats() {
    const user = getCurrentUser();
    const dogs = await mock.listDogs();
    const bookings = await mock.listBookings();
    const now = new Date();

    const upcomingBookings = bookings.filter(b => {
      const checkIn = new Date(b.startDate);
      return checkIn >= now && ['pending', 'confirmed'].includes(b.status);
    });

    return {
      my_dogs: dogs.length,
      my_bookings: bookings.length,
      upcoming_bookings: upcomingBookings.length,
    };
  },

  // ---------- DAILY UPDATES ----------
  async getDailyUpdates() {
    // Mock returns empty for now
    return [];
  },
};

// ========================
// API Implementation
// ========================
const apiImpl = {
  async listBookings() {
    const res = await api.get('/bookings');
    const bookings = Array.isArray(res.data) ? res.data : (res.data.bookings || []);
    return bookings.map(normalizeBooking);
  },

  async listBookingsForDay(day) {
    const dayISO = toISODate(day);
    const all = await apiImpl.listBookings();
    return all.filter((b) => isDateInRange(dayISO, b.startDate, b.endDate));
  },

  async getBooking(bookingId) {
    const res = await api.get(`/bookings/${bookingId}`);
    return normalizeBooking(res.data);
  },

  async createBooking(payload) {
    const res = await api.post('/k9/bookings/smart', {
      dog_ids: payload.dogIds || payload.dog_ids,
      check_in_date: payload.startDate || payload.check_in_date,
      check_out_date: payload.endDate || payload.check_out_date,
      notes: payload.notes,
      add_ons: payload.addOns || payload.add_ons || [],
    });
    return normalizeBooking(res.data.booking || res.data);
  },

  async updateBooking(bookingId, updates) {
    const res = await api.patch(`/bookings/${bookingId}`, {
      check_in_date: updates.startDate,
      check_out_date: updates.endDate,
      dog_ids: updates.dogIds,
      notes: updates.notes,
    });
    return normalizeBooking(res.data);
  },

  async cancelBooking(bookingId) {
    const res = await api.patch(`/bookings/${bookingId}/status?status=cancelled`);
    return normalizeBooking(res.data);
  },

  async listDogs() {
    const res = await api.get('/dogs');
    return Array.isArray(res.data) ? res.data : (res.data.dogs || []);
  },

  async getDog(dogId) {
    const res = await api.get(`/dogs/${dogId}`);
    return res.data;
  },

  async createDog(payload) {
    const res = await api.post('/dogs', payload);
    return res.data;
  },

  async updateDog(dogId, updates) {
    const res = await api.patch(`/dogs/${dogId}`, updates);
    return res.data;
  },

  async deleteDog(dogId) {
    await api.delete(`/dogs/${dogId}`);
    return { success: true };
  },

  async listInvoices() {
    const res = await api.get('/k9/portal/invoices');
    return res.data.invoices || res.data || [];
  },

  async payInvoice(invoiceId, payload) {
    const res = await api.post(`/payments/invoices/${invoiceId}/pay`, payload);
    return res.data;
  },

  async getEmailOutbox() {
    const res = await api.get('/admin/email-outbox');
    return res.data.emails || [];
  },

  async getEmailTemplates() {
    const res = await api.get('/admin/email-templates');
    return res.data.templates || res.data || {};
  },

  async updateEmailTemplate(templateName, data) {
    const res = await api.put(`/admin/email-templates/${templateName}`, data);
    return res.data;
  },

  async sendTestEmail(templateName, testEmail) {
    const res = await api.post(`/admin/email-templates/${templateName}/test`, { email: testEmail });
    return res.data;
  },

  async sendBookingConfirmationEmail(booking) {
    // In API mode, this is handled server-side
    return { success: true };
  },

  async requestStaffAccount(data) {
    const res = await api.post('/auth/request-staff', data);
    return res.data;
  },

  async listStaffRequests() {
    const res = await api.get('/admin/staff-requests');
    return res.data.requests || res.data || [];
  },

  async approveStaffRequest(requestId) {
    const res = await api.post(`/admin/staff-requests/${requestId}/approve`);
    return res.data;
  },

  async rejectStaffRequest(requestId, reason) {
    const res = await api.post(`/admin/staff-requests/${requestId}/reject`, { reason });
    return res.data;
  },

  async isOwner(userId) {
    const res = await api.get(`/admin/is-owner/${userId}`);
    return res.data.isOwner;
  },

  async createAdminAccount(data) {
    const res = await api.post('/admin/create-admin', data);
    return res.data;
  },

  async getDashboardStats() {
    const res = await api.get('/dashboard/stats');
    return res.data;
  },

  async getDailyUpdates() {
    const res = await api.get('/daily-updates');
    return Array.isArray(res.data) ? res.data : [];
  },
};

// ========================
// Export
// ========================
export const dataClient = MODE === 'api' ? apiImpl : mock;
export const dataMode = MODE;
export { toISODate, normalizeBooking };
