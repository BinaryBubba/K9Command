import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import useAuthStore from '../store/authStore';
import api from '../utils/api';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { ArrowLeftIcon, CheckCircleIcon, CalendarIcon, ClockIcon, DogIcon } from 'lucide-react';
import { toast } from 'sonner';

const ALLOWED_DAYS = [0, 1, 3, 5]; // Sun=0, Mon=1, Wed=3, Fri=5 (JS getDay())
const DAY_NAMES = ['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'];
const SLOTS = [
  { id: '10:00-10:30', label: '10:00 – 10:30 AM', window: 'Morning' },
  { id: '10:30-11:00', label: '10:30 – 11:00 AM', window: 'Morning' },
  { id: '11:00-11:30', label: '11:00 – 11:30 AM', window: 'Morning' },
  { id: '11:30-12:00', label: '11:30 AM – 12:00 PM', window: 'Morning' },
  { id: '14:00-14:30', label: '2:00 – 2:30 PM', window: 'Afternoon' },
  { id: '14:30-15:00', label: '2:30 – 3:00 PM', window: 'Afternoon' },
  { id: '15:00-15:30', label: '3:00 – 3:30 PM', window: 'Afternoon' },
  { id: '15:30-16:00', label: '3:30 – 4:00 PM', window: 'Afternoon' },
];

const CustomerMagRequestPage = () => {
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const dogId = searchParams.get('dog_id');
  const householdId = searchParams.get('household_id');
  const dogName = searchParams.get('dog_name') || 'your dog';

  const [step, setStep] = useState('datetime'); // datetime | stay | confirm
  const [selectedDate, setSelectedDate] = useState('');
  const [selectedSlot, setSelectedSlot] = useState('');
  const [availableSlots, setAvailableSlots] = useState(SLOTS.map(s => s.id));
  const [stayStart, setStayStart] = useState('');
  const [stayEnd, setStayEnd] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [dogCount, setDogCount] = useState(1);

  // Other household dogs that could join this same appointment slot.
  const [otherDogs, setOtherDogs] = useState([]);
  const [selectedOtherDogIds, setSelectedOtherDogIds] = useState([]);
  const [loadingOtherDogs, setLoadingOtherDogs] = useState(true);

  const isAllowedDay = (dateStr) => {
    if (!dateStr) return false;
    const d = new Date(dateStr + 'T12:00:00');
    return ALLOWED_DAYS.includes(d.getDay());
  };

  useEffect(() => {
    if (selectedDate && isAllowedDay(selectedDate)) {
      api.get('/meet-and-greets/available-slots', { params: { date: selectedDate } })
        .then(r => {
          if (r.data.slots) setAvailableSlots(r.data.slots);
        }).catch(() => {});
    }
  }, [selectedDate]);

  // Load other dogs in the household that haven't been cleared yet, so the
  // customer can bring them to the same appointment instead of scheduling
  // a separate visit for each dog.
  useEffect(() => {
    if (!householdId) { setLoadingOtherDogs(false); return; }
    api.get('/dogs', { params: { household_id: householdId, limit: 50 } })
      .then(r => {
        const list = r.data?.dogs || r.data || [];
        const others = list.filter(d =>
          d.id !== dogId &&
          d.meet_and_greet_status !== 'completed' &&
          d.meet_and_greet_status !== 'waived'
        );
        setOtherDogs(others);
        setSelectedOtherDogIds(others.map(d => d.id));
      })
      .catch(() => {})
      .finally(() => setLoadingOtherDogs(false));
  }, [householdId, dogId]);

  const toggleOtherDog = (id) => {
    setSelectedOtherDogIds(prev =>
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    );
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      const allDogIds = [dogId, ...selectedOtherDogIds].filter(Boolean);
      const res = await api.post('/meet-and-greets/request', {
        dog_ids: allDogIds,
        household_id: householdId,
        scheduled_date: selectedDate,
        slot: selectedSlot,
        stay_start: stayStart || undefined,
        stay_end: stayEnd || undefined,
      });
      setDogCount(res.data?.dog_count || allDogIds.length);
      setSubmitted(true);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to submit request');
    } finally {
      setSubmitting(false);
    }
  };

  // Generate next 30 days, only allowed days
  const availableDates = [];
  const today = new Date();
  for (let i = 1; i <= 60; i++) {
    const d = new Date(today);
    d.setDate(today.getDate() + i);
    if (ALLOWED_DAYS.includes(d.getDay())) {
      const str = d.toISOString().split('T')[0];
      availableDates.push({ str, label: `${DAY_NAMES[d.getDay()]}, ${d.toLocaleDateString([], {month:'short',day:'numeric'})}` });
    }
    if (availableDates.length >= 12) break;
  }

  if (submitted) return (
    <div className="min-h-screen bg-[#F9F7F2] flex items-center justify-center p-4">
      <div className="text-center space-y-4 max-w-sm">
        <CheckCircleIcon size={48} className="mx-auto text-green-500" />
        <h2 className="text-xl font-bold">Request Submitted!</h2>
        <p className="text-sm text-muted-foreground">
          {dogCount > 1
            ? `Your Meet & Greet request for ${dogCount} dogs has been sent.`
            : `Your Meet & Greet request for ${dogName} has been sent.`}
          {' '}Our staff will confirm your appointment shortly.
          {stayStart && ` Your stay request has also been submitted.`}
        </p>
        <Button className="w-full" onClick={() => navigate('/customer/dashboard')}>Back to Dashboard</Button>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-[#F9F7F2]">
      <header className="bg-white border-b shadow-sm sticky top-0 z-10">
        <div className="max-w-2xl mx-auto px-4 py-3 flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={() => navigate('/customer/dashboard')}>
            <ArrowLeftIcon size={18} />
          </Button>
          <div>
            <h1 className="text-base font-serif font-bold text-primary">Schedule Meet & Greet</h1>
            <p className="text-xs text-muted-foreground">For {dogName}</p>
          </div>
        </div>
      </header>

      <main className="max-w-2xl mx-auto px-4 py-6 space-y-4">
        {!loadingOtherDogs && otherDogs.length > 0 && (
          <Card>
            <CardHeader className="pb-2 pt-4">
              <CardTitle className="text-sm flex items-center gap-2">
                <DogIcon size={14} /> Bring Other Dogs Too?
              </CardTitle>
            </CardHeader>
            <CardContent className="px-4 pb-4 space-y-2">
              <p className="text-xs text-muted-foreground mb-2">
                These dogs in your household haven't been cleared yet — add them to this same appointment instead of scheduling separately.
              </p>
              {otherDogs.map(dog => (
                <label key={dog.id} className="flex items-center gap-2 p-2 rounded-lg border border-border cursor-pointer hover:bg-muted">
                  <input
                    type="checkbox"
                    checked={selectedOtherDogIds.includes(dog.id)}
                    onChange={() => toggleOtherDog(dog.id)}
                  />
                  <span className="text-sm">{dog.name}</span>
                </label>
              ))}
            </CardContent>
          </Card>
        )}

        <Card>
          <CardHeader className="pb-2 pt-4">
            <CardTitle className="text-sm flex items-center gap-2">
              <CalendarIcon size={14} /> Select a Date
            </CardTitle>
          </CardHeader>
          <CardContent className="px-4 pb-4">
            <p className="text-xs text-muted-foreground mb-3">
              Meet & Greets are available Sunday, Monday, Wednesday, and Friday
            </p>
            <div className="grid grid-cols-2 gap-2">
              {availableDates.map(d => (
                <button key={d.str} type="button"
                  onClick={() => { setSelectedDate(d.str); setSelectedSlot(''); }}
                  className={`p-3 rounded-lg border text-left text-sm transition-colors ${
                    selectedDate === d.str
                      ? 'bg-primary text-primary-foreground border-primary'
                      : 'border-border hover:bg-muted'
                  }`}>
                  {d.label}
                </button>
              ))}
            </div>
          </CardContent>
        </Card>

        {selectedDate && (
          <Card>
            <CardHeader className="pb-2 pt-4">
              <CardTitle className="text-sm flex items-center gap-2">
                <ClockIcon size={14} /> Select a Time Slot
              </CardTitle>
            </CardHeader>
            <CardContent className="px-4 pb-4 space-y-2">
              {['Morning', 'Afternoon'].map(window => (
                <div key={window}>
                  <p className="text-xs font-medium text-muted-foreground mb-1 mt-2">{window}</p>
                  <div className="grid grid-cols-2 gap-2">
                    {SLOTS.filter(s => s.window === window).map(slot => {
                      const available = availableSlots.includes(slot.id);
                      return (
                        <button key={slot.id} type="button"
                          disabled={!available}
                          onClick={() => available && setSelectedSlot(slot.id)}
                          className={`p-2.5 rounded-lg border text-sm transition-colors ${
                            !available ? 'opacity-40 cursor-not-allowed bg-gray-50 text-gray-400' :
                            selectedSlot === slot.id
                              ? 'bg-primary text-primary-foreground border-primary'
                              : 'border-border hover:bg-muted'
                          }`}>
                          {slot.label}
                          {!available && <span className="block text-xs">Unavailable</span>}
                        </button>
                      );
                    })}
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        )}

        {selectedDate && selectedSlot && (
          <Card>
            <CardHeader className="pb-2 pt-4">
              <CardTitle className="text-sm">Planned Stay Dates (Optional)</CardTitle>
            </CardHeader>
            <CardContent className="px-4 pb-4 space-y-3">
              <p className="text-xs text-muted-foreground">
                Let us know when you're planning to board — we'll create a pending reservation for you.
              </p>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label>Check-In Date</Label>
                  <Input type="date" value={stayStart}
                    min={new Date().toISOString().split('T')[0]}
                    onChange={e => setStayStart(e.target.value)} className="mt-1" />
                </div>
                <div>
                  <Label>Check-Out Date</Label>
                  <Input type="date" value={stayEnd}
                    min={stayStart || new Date().toISOString().split('T')[0]}
                    onChange={e => setStayEnd(e.target.value)} className="mt-1" />
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {selectedDate && selectedSlot && (
          <div className="bg-primary/5 border border-primary/20 rounded-xl p-4 space-y-1">
            <p className="text-sm font-medium">Your Request Summary</p>
            <p className="text-xs text-muted-foreground">
              Dog{selectedOtherDogIds.length > 0 ? 's' : ''}: {[dogName, ...otherDogs.filter(d => selectedOtherDogIds.includes(d.id)).map(d => d.name)].join(', ')}
            </p>
            <p className="text-xs text-muted-foreground">
              Date: {new Date(selectedDate + 'T12:00:00').toLocaleDateString([], {weekday:'long',month:'long',day:'numeric'})}
            </p>
            <p className="text-xs text-muted-foreground">
              Time: {SLOTS.find(s => s.id === selectedSlot)?.label || selectedSlot}
            </p>
            {stayStart && stayEnd && (
              <p className="text-xs text-muted-foreground">
                Stay: {new Date(stayStart+'T12:00:00').toLocaleDateString([], {month:'short',day:'numeric'})} – {new Date(stayEnd+'T12:00:00').toLocaleDateString([], {month:'short',day:'numeric',year:'numeric'})}
              </p>
            )}
          </div>
        )}

        <Button className="w-full" disabled={!selectedDate || !selectedSlot || submitting}
          onClick={handleSubmit}>
          {submitting ? 'Submitting...' : 'Submit M&G Request'}
        </Button>
      </main>
    </div>
  );
};

export default CustomerMagRequestPage;
