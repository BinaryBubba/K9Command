import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import useAuthStore from '../store/authStore';
import api from '../utils/api';
import { Button } from '../components/ui/button';
import { Card, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { ArrowLeftIcon, PlusIcon, CalendarIcon, DogIcon, AlertCircleIcon } from 'lucide-react';
import { toast } from 'sonner';

const STATUS_COLORS = {
  confirmed: 'bg-blue-100 text-blue-700',
  checked_in: 'bg-green-100 text-green-700',
  checked_out: 'bg-gray-100 text-gray-600',
  cancelled: 'bg-red-100 text-red-600',
  pending: 'bg-amber-100 text-amber-700',
};

const AdminBookingsPage = () => {
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [filter, setFilter] = useState('upcoming');

  const fetchBookings = useCallback(async () => {
    try {
      const now = new Date();
      const params = { limit: 100 };
      if (filter === 'upcoming') params.start_date = now.toISOString();
      else if (filter === 'today') {
        params.start_date = new Date(now.setHours(0,0,0,0)).toISOString();
        params.end_date = new Date(now.setHours(23,59,59,999)).toISOString();
      }
      const res = await api.get('/bookings', { params });
      setBookings(res.data);
    } catch {
      toast.error('Failed to load bookings');
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => {
    if (!user) { navigate('/auth'); return; }
    fetchBookings();
  }, [user, navigate, fetchBookings]);

  return (
    <div className="min-h-screen bg-[#F9F7F2]">
      <header className="bg-white border-b shadow-sm sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="sm" onClick={() => navigate(-1)}>
              <ArrowLeftIcon size={18} />
            </Button>
            <h1 className="text-lg font-serif font-bold text-primary">Bookings</h1>
          </div>
          <Button size="sm" onClick={() => setShowCreate(true)}>
            <PlusIcon size={16} className="mr-1" /> New
          </Button>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-6 space-y-4">
        {/* Filter tabs */}
        <div className="flex gap-2">
          {['upcoming', 'today', 'all'].map(f => (
            <button key={f} onClick={() => setFilter(f)}
              className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
                filter === f ? 'bg-primary text-primary-foreground' : 'bg-white border hover:bg-muted'
              }`}>
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>

        {loading ? (
          <div className="flex justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-primary"></div>
          </div>
        ) : bookings.length === 0 ? (
          <Card><CardContent className="py-12 text-center text-muted-foreground">
            No bookings found
          </CardContent></Card>
        ) : (
          <div className="space-y-2">
            {bookings.map(b => (
              <Card key={b.id} className="cursor-pointer hover:shadow-md transition-shadow" onClick={() => navigate(`/admin/bookings/${b.id}`)}>
                <CardContent className="py-3 px-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-start gap-3">
                      <div className="bg-primary/10 p-2 rounded-full mt-0.5">
                        <CalendarIcon size={14} className="text-primary" />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <p className="font-medium text-sm">
                            {new Date(b.check_in_date).toLocaleDateString()} — {new Date(b.check_out_date).toLocaleDateString()}
                          </p>
                        </div>
                        <div className="flex items-center gap-2 mt-1">
                          <DogIcon size={12} className="text-muted-foreground" />
                          <span className="text-xs text-muted-foreground">
                            {b.dog_ids?.length} dog{b.dog_ids?.length !== 1 ? 's' : ''}
                          </span>
                          <span className="text-xs text-muted-foreground">·</span>
                          <span className="text-xs text-muted-foreground">
                            {Math.ceil((new Date(b.check_out_date) - new Date(b.check_in_date)) / (1000*60*60*24))} nights
                          </span>
                        </div>
                      </div>
                    </div>
                    <Badge className={`text-xs ${STATUS_COLORS[b.status] || 'bg-gray-100 text-gray-600'}`}>
                      {b.status?.replace('_', ' ')}
                    </Badge>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </main>

      {showCreate && (
        <CreateBookingModal
          onClose={() => setShowCreate(false)}
          onSuccess={() => { setShowCreate(false); fetchBookings(); }}
        />
      )}
    </div>
  );
};

const CreateBookingModal = ({ onClose, onSuccess }) => {
  const [households, setHouseholds] = useState([]);
  const [dogs, setDogs] = useState([]);
  const [form, setForm] = useState({
    household_id: '',
    dog_ids: [],
    check_in_date: '',
    check_out_date: '',
    notes: '',
  });
  const [conflicts, setConflicts] = useState([]);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    api.get('/households', { params: { limit: 100 } })
      .then(r => setHouseholds(r.data))
      .catch(() => {});
  }, []);

  const onHouseholdChange = async (householdId) => {
    setForm(f => ({...f, household_id: householdId, dog_ids: []}));
    if (householdId) {
      try {
        const res = await api.get('/dogs', { params: { household_id: householdId } });
        setDogs(res.data);
      } catch {}
    } else {
      setDogs([]);
    }
  };

  const checkConflicts = async () => {
    if (!form.check_in_date || !form.check_out_date || form.dog_ids.length === 0) return;
    try {
      const res = await api.post('/bookings/check-conflicts', {
        check_in_date: form.check_in_date,
        check_out_date: form.check_out_date,
        dog_ids: form.dog_ids,
      });
      setConflicts(res.data.conflicts || []);
    } catch {}
  };

  const [vaccinationWarnings, setVaccinationWarnings] = useState([]);
  const [showVaxWarning, setShowVaxWarning] = useState(false);

  const checkVaccinations = async (dogIds) => {
    const warnings = [];
    const today = new Date();
    const in30Days = new Date(today.getTime() + 30 * 24 * 60 * 60 * 1000);
    for (const dogId of dogIds) {
      try {
        const res = await api.get(`/vaccinations/dog/${dogId}`);
        const vax = res.data || [];
        const dog = dogs.find(d => d.id === dogId);
        const dogName = dog?.name || 'Unknown';
        const expired = vax.filter(v => v.expiry_date && new Date(v.expiry_date) < today);
        const expiring = vax.filter(v => v.expiry_date && new Date(v.expiry_date) >= today && new Date(v.expiry_date) <= in30Days);
        if (expired.length > 0) warnings.push({ dogName, type: 'expired', items: expired.map(v => v.vaccine_name) });
        if (expiring.length > 0) warnings.push({ dogName, type: 'expiring', items: expiring.map(v => v.vaccine_name) });
      } catch {}
    }
    return warnings;
  };

  const handleSubmit = async () => {
    if (!form.household_id) { toast.error('Select a household'); return; }
    if (form.dog_ids.length === 0) { toast.error('Select at least one dog'); return; }
    if (!form.check_in_date || !form.check_out_date) { toast.error('Set check-in and check-out dates'); return; }
    const blocking = conflicts.filter(c => c.severity === 'blocking');
    if (blocking.length > 0 && !window.confirm('There are blocking conflicts. Continue anyway?')) return;
    setSubmitting(true);
    try {
      await api.post('/bookings', {
        ...form,
        check_in_date: new Date(form.check_in_date).toISOString(),
        check_out_date: new Date(form.check_out_date).toISOString(),
      });
      toast.success('Booking created');
      onSuccess();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to create booking');
    } finally {
      setSubmitting(false);
    }
  };

  const toggleDog = (dogId) => {
    setForm(f => ({
      ...f,
      dog_ids: f.dog_ids.includes(dogId)
        ? f.dog_ids.filter(id => id !== dogId)
        : [...f.dog_ids, dogId]
    }));
  };

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-end md:items-center justify-center p-4">
      <div className="bg-white rounded-t-2xl md:rounded-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="p-6 space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-lg font-bold">New Booking</h2>
            <button onClick={onClose} className="text-muted-foreground text-xl">×</button>
          </div>

          <div>
            <Label>Household *</Label>
            <select
              className="w-full mt-1 border rounded-md px-3 py-2 text-sm bg-background"
              value={form.household_id}
              onChange={e => onHouseholdChange(e.target.value)}
            >
              <option value="">Select household...</option>
              {households.map(h => (
                <option key={h.id} value={h.id}>{h.display_name}</option>
              ))}
            </select>
          </div>

          <div>
            <Label>Dogs *</Label>
            {!form.household_id ? (
              <p className="text-xs text-muted-foreground mt-2 italic">Select a household above to see their dogs</p>
            ) : dogs.length === 0 ? (
              <p className="text-xs text-amber-600 mt-2">No dogs found for this household — add a dog to this household first</p>
            ) : (
              <div className="flex flex-wrap gap-2 mt-2">
                {dogs.map(dog => (
                  <button key={dog.id} type="button" onClick={() => toggleDog(dog.id)}
                    className={`px-3 py-1.5 rounded-full text-sm border transition-colors ${
                      form.dog_ids.includes(dog.id)
                        ? 'bg-primary text-primary-foreground border-primary'
                        : 'border-border hover:bg-muted'
                    }`}>
                    {dog.name}
                    {!dog.boarding_eligible && <span className="ml-1 text-xs opacity-60">(needs M&G)</span>}
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label>Check In *</Label>
              <Input type="datetime-local" value={form.check_in_date}
                onChange={e => setForm(f => ({...f, check_in_date: e.target.value}))}
                onBlur={checkConflicts} className="mt-1" />
            </div>
            <div>
              <Label>Check Out *</Label>
              <Input type="datetime-local" value={form.check_out_date}
                onChange={e => setForm(f => ({...f, check_out_date: e.target.value}))}
                onBlur={checkConflicts} className="mt-1" />
            </div>
          </div>

          {conflicts.length > 0 && (
            <div className="space-y-1">
              {conflicts.map((c, i) => (
                <div key={i} className={`flex items-center gap-2 p-2 rounded text-xs ${
                  c.severity === 'blocking' ? 'bg-red-50 text-red-700' : 'bg-amber-50 text-amber-700'
                }`}>
                  <AlertCircleIcon size={12} />
                  {c.message}
                </div>
              ))}
            </div>
          )}

          <div>
            <Label>Notes</Label>
            <Textarea value={form.notes}
              onChange={e => setForm(f => ({...f, notes: e.target.value}))}
              className="mt-1" rows={2} />
          </div>

          <div className="flex gap-3 pt-2">
            <Button variant="outline" className="flex-1" onClick={onClose}>Cancel</Button>
            <Button className="flex-1" onClick={handleSubmit} disabled={submitting}>
              {submitting ? 'Creating...' : 'Create Booking'}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminBookingsPage;

export { CreateBookingModal };
