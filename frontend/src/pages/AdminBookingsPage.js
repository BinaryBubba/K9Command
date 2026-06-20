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
  const [viewMode, setViewMode] = useState('list'); // list | calendar
  const [calendarDate, setCalendarDate] = useState(new Date());
  const [filter, setFilter] = useState('upcoming');

  const fetchBookings = useCallback(async () => {
    try {
      const now = new Date();
      const params = { limit: 100 };
      if (filter === 'upcoming') {
        params.start_date = now.toISOString();
        params.status = 'CONFIRMED';
      } else if (filter === 'past') {
        // check_out_date < now
        params.end_date = new Date(now.getTime() - 1).toISOString();
        params.status = 'CHECKED_OUT';
      } else if (filter === 'cancelled') {
        params.status = 'CANCELLED';
      } else if (filter === 'completed') {
        params.status = 'CHECKED_OUT';
      } else if (filter === 'all') {
        // no filter - show everything
      }
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
          <div className="flex gap-2">
            <Button size="sm" variant={viewMode === 'list' ? 'default' : 'outline'}
              onClick={() => setViewMode('list')}>List</Button>
            <Button size="sm" variant={viewMode === 'calendar' ? 'default' : 'outline'}
              onClick={() => setViewMode('calendar')}>Calendar</Button>
            <Button size="sm" onClick={() => setShowCreate(true)}>
              <PlusIcon size={16} className="mr-1" /> New
            </Button>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-6 space-y-4">
        {/* Filter tabs */}
        <div className="flex gap-2">
          {['upcoming', 'today', 'all', 'past', 'completed', 'cancelled'].map(f => (
            <button key={f} onClick={() => setFilter(f)}
              className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
                filter === f ? 'bg-primary text-primary-foreground' : 'bg-white border hover:bg-muted'
              }`}>
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>

        {viewMode === 'calendar' && (
          <BookingCalendar
            bookings={bookings}
            date={calendarDate}
            onDateChange={setCalendarDate}
            onBookingClick={b => navigate(`/admin/bookings/${b.id}`)}
          />
        )}
        {viewMode === 'list' && loading ? (
          <div className="flex justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-primary"></div>
          </div>
        ) : viewMode === 'list' && bookings.length === 0 ? (
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
                        <div className="flex items-center gap-1 mt-0.5">
                          <span className="text-xs font-medium text-muted-foreground">{b.household_name || 'Unknown'}</span>
                        </div>
                        <div className="flex items-center gap-2 mt-0.5">
                          <DogIcon size={12} className="text-muted-foreground" />
                          <span className="text-xs text-muted-foreground">
                            {b.dog_names?.length > 0 ? b.dog_names.join(', ') : `${b.dog_ids?.length || 0} dog${b.dog_ids?.length !== 1 ? 's' : ''}`}
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
  const [showNewCustomer, setShowNewCustomer] = useState(false);
  const [newCustForm, setNewCustForm] = useState({ display_name: '', first_name: '', last_name: '', email: '', phone: '' });
  const [creatingCustomer, setCreatingCustomer] = useState(false);
  const [newCustStep, setNewCustStep] = useState('info'); // info | dog | mag
  const [newHhId, setNewHhId] = useState(null);
  const [newHhName, setNewHhName] = useState('');
  const [newDogForm, setNewDogForm] = useState({ name: '', breed: '', age: '', weight: '' });
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
    if (householdId === '__new__') { setShowNewCustomer(true); return; }
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

  const handleCreateNewCustomer = async () => {
    if (!newCustForm.display_name.trim()) { toast.error('Household name required'); return; }
    if (!newCustForm.email.trim()) { toast.error('Email required'); return; }
    setCreatingCustomer(true);
    try {
      const hhRes = await api.post('/households', {
        display_name: newCustForm.display_name,
        primary_contact: {
          first_name: newCustForm.first_name,
          last_name: newCustForm.last_name,
          email: newCustForm.email,
          phone: newCustForm.phone,
          is_authorized_pickup: true,
          is_emergency_contact: false,
        },
      });
      const newHh = hhRes.data;
      setHouseholds(prev => [...prev, newHh]);
      setNewHhId(newHh.id);
      setNewHhName(newHh.display_name);
      setNewCustStep('dog');
      toast.success(`${newHh.display_name} created — add their dog`);
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed to create customer'); }
    finally { setCreatingCustomer(false); }
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
              <option value="__new__">➕ Create new customer...</option>
              {households.map(h => (
                <option key={h.id} value={h.id}>{h.display_name}</option>
              ))}
            </select>
          </div>

          <div>
            <Label>Dogs *</Label>
            {showNewCustomer && newCustStep === 'info' && (
              <div className="mt-2 p-3 border border-primary/30 rounded-lg bg-primary/5 space-y-2">
                <p className="text-xs font-medium text-primary">Step 1 of 3 — New Customer</p>
                <Input placeholder="Household/Family name *" value={newCustForm.display_name}
                  onChange={e => setNewCustForm(f=>({...f,display_name:e.target.value}))} />
                <div className="grid grid-cols-2 gap-2">
                  <Input placeholder="First name" value={newCustForm.first_name}
                    onChange={e => setNewCustForm(f=>({...f,first_name:e.target.value}))} />
                  <Input placeholder="Last name" value={newCustForm.last_name}
                    onChange={e => setNewCustForm(f=>({...f,last_name:e.target.value}))} />
                </div>
                <Input placeholder="Email *" type="email" value={newCustForm.email}
                  onChange={e => setNewCustForm(f=>({...f,email:e.target.value}))} />
                <Input placeholder="Phone" value={newCustForm.phone}
                  onChange={e => setNewCustForm(f=>({...f,phone:e.target.value}))} />
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" className="flex-1" onClick={() => setShowNewCustomer(false)}>Cancel</Button>
                  <Button size="sm" className="flex-1" onClick={handleCreateNewCustomer} disabled={creatingCustomer}>
                    {creatingCustomer ? 'Creating...' : 'Next: Add Dog →'}
                  </Button>
                </div>
              </div>
            )}
            {showNewCustomer && newCustStep === 'dog' && (
              <div className="mt-2 p-3 border border-green-200 rounded-lg bg-green-50 space-y-2">
                <p className="text-xs font-medium text-green-800">Step 2 of 3 — Add Dog for {newHhName}</p>
                <Input placeholder="Dog name *" value={newDogForm.name}
                  onChange={e => setNewDogForm(f=>({...f,name:e.target.value}))} />
                <div className="grid grid-cols-2 gap-2">
                  <Input placeholder="Breed" value={newDogForm.breed}
                    onChange={e => setNewDogForm(f=>({...f,breed:e.target.value}))} />
                  <Input placeholder="Age (yrs)" type="number" value={newDogForm.age}
                    onChange={e => setNewDogForm(f=>({...f,age:e.target.value}))} />
                </div>
                <Input placeholder="Weight (lbs)" type="number" value={newDogForm.weight}
                  onChange={e => setNewDogForm(f=>({...f,weight:e.target.value}))} />
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" className="flex-1"
                    onClick={async () => {
                      // Skip dog, go to M&G
                      await onHouseholdChange(newHhId);
                      setNewCustStep('mag');
                    }}>Skip</Button>
                  <Button size="sm" className="flex-1 bg-green-600 hover:bg-green-700"
                    onClick={async () => {
                      if (!newDogForm.name.trim()) { toast.error('Dog name required'); return; }
                      try {
                        await api.post('/dogs', {
                          name: newDogForm.name, breed: newDogForm.breed || undefined,
                          age: newDogForm.age ? parseInt(newDogForm.age) : undefined,
                          weight: newDogForm.weight ? parseFloat(newDogForm.weight) : undefined,
                          household_id: newHhId,
                        });
                        await onHouseholdChange(newHhId);
                        setNewCustStep('mag');
                        toast.success(`${newDogForm.name} added`);
                      } catch { toast.error('Failed to add dog'); }
                    }}>Add Dog & Continue →</Button>
                </div>
              </div>
            )}
            {showNewCustomer && newCustStep === 'mag' && (
              <div className="mt-2 p-3 border border-blue-200 rounded-lg bg-blue-50 space-y-2">
                <p className="text-xs font-medium text-blue-800">Step 3 of 3 — Meet & Greet for {newHhName}</p>
                <p className="text-xs text-blue-700">Dogs must complete a meet & greet before their first stay.</p>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" className="flex-1"
                    onClick={() => { setShowNewCustomer(false); setNewCustStep('info'); }}>
                    Skip for Now
                  </Button>
                  <Button size="sm" className="flex-1 bg-blue-600 hover:bg-blue-700"
                    onClick={() => {
                      setShowNewCustomer(false);
                      setNewCustStep('info');
                      navigate(`/admin/meet-and-greet?household_id=${newHhId}`);
                    }}>Schedule M&G →</Button>
                </div>
              </div>
            )}
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

const BookingCalendar = ({ bookings, date, onDateChange, onBookingClick }) => {
  const year = date.getFullYear();
  const month = date.getMonth();

  const firstDay = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const today = new Date();

  const monthNames = ['January','February','March','April','May','June',
    'July','August','September','October','November','December'];

  // Map bookings to days they overlap
  const getDayBookings = (day) => {
    const cellDate = new Date(year, month, day);
    return bookings.filter(b => {
      const checkIn = new Date(b.check_in_date);
      const checkOut = new Date(b.check_out_date);
      checkIn.setHours(0,0,0,0);
      checkOut.setHours(23,59,59,999);
      cellDate.setHours(12,0,0,0);
      return cellDate >= checkIn && cellDate <= checkOut;
    });
  };

  const STATUS_DOT = {
    confirmed: 'bg-blue-400',
    checked_in: 'bg-green-400',
    checked_out: 'bg-gray-400',
    cancelled: 'bg-red-400',
    pending: 'bg-amber-400',
  };

  return (
    <div className="bg-white rounded-xl border shadow-sm p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <button onClick={() => onDateChange(new Date(year, month - 1, 1))}
          className="p-1 rounded hover:bg-muted text-lg">‹</button>
        <h2 className="font-semibold">{monthNames[month]} {year}</h2>
        <button onClick={() => onDateChange(new Date(year, month + 1, 1))}
          className="p-1 rounded hover:bg-muted text-lg">›</button>
      </div>
      {/* Day names */}
      <div className="grid grid-cols-7 mb-1">
        {['Su','Mo','Tu','We','Th','Fr','Sa'].map(d => (
          <div key={d} className="text-center text-xs font-medium text-muted-foreground py-1">{d}</div>
        ))}
      </div>
      {/* Days grid */}
      <div className="grid grid-cols-7 gap-0.5">
        {Array.from({length: firstDay}).map((_, i) => <div key={`empty-${i}`} />)}
        {Array.from({length: daysInMonth}).map((_, i) => {
          const day = i + 1;
          const dayBookings = getDayBookings(day);
          const isToday = today.getFullYear() === year && today.getMonth() === month && today.getDate() === day;
          return (
            <div key={day} className={`min-h-14 p-1 rounded border text-xs ${
              isToday ? 'border-primary bg-primary/5' : 'border-transparent hover:border-border'
            }`}>
              <p className={`font-medium mb-0.5 ${isToday ? 'text-primary' : ''}`}>{day}</p>
              {dayBookings.slice(0,3).map(b => (
                <button key={b.id} type="button"
                  onClick={() => onBookingClick(b)}
                  className={`w-full text-left text-xs px-1 py-0.5 rounded mb-0.5 truncate flex items-center gap-1 hover:opacity-80 ${
                    b.status === 'checked_in' ? 'bg-green-100 text-green-800' :
                    b.status === 'confirmed' ? 'bg-blue-100 text-blue-800' :
                    b.status === 'cancelled' ? 'bg-red-100 text-red-700 line-through' :
                    'bg-gray-100 text-gray-600'
                  }`}>
                  <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${STATUS_DOT[b.status] || 'bg-gray-400'}`}></span>
                  <span className="truncate">{b.dog_names?.[0] || b.household_name || '—'}</span>
                </button>
              ))}
              {dayBookings.length > 3 && (
                <p className="text-muted-foreground text-xs">+{dayBookings.length - 3} more</p>
              )}
            </div>
          );
        })}
      </div>
      {/* Legend */}
      <div className="flex gap-4 mt-3 pt-3 border-t">
        {[['confirmed','bg-blue-400','Confirmed'],['checked_in','bg-green-400','Checked In'],['checked_out','bg-gray-400','Checked Out'],['cancelled','bg-red-400','Cancelled']].map(([s,c,l]) => (
          <div key={s} className="flex items-center gap-1 text-xs text-muted-foreground">
            <span className={`w-2 h-2 rounded-full ${c}`}></span>{l}
          </div>
        ))}
      </div>
    </div>
  );
};

export { CreateBookingModal };
