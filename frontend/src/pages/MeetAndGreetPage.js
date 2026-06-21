import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import useAuthStore from '../store/authStore';
import api from '../utils/api';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { PlusIcon, DogIcon, CheckCircleIcon, XCircleIcon, AlertCircleIcon, ClockIcon } from 'lucide-react';
import { toast } from 'sonner';

const OUTCOME_COLORS = {
  pass: 'bg-green-100 text-green-700',
  fail: 'bg-red-100 text-red-700',
  conditional: 'bg-amber-100 text-amber-700',
  no_show: 'bg-gray-100 text-gray-600',
  rescheduled: 'bg-blue-100 text-blue-700',
};

const MAG_STATUS_COLORS = {
  required: 'text-amber-600',
  scheduled: 'text-blue-600',
  completed: 'text-green-600',
};

const MeetAndGreetPage = () => {
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const location = useLocation();
  const params = new URLSearchParams(location.search);
  const preselectedHouseholdId = params.get('household_id');
  const [dogs, setDogs] = useState([]);
  const [pendingRequests, setPendingRequests] = useState([]);
  const [mags, setMags] = useState({});
  const [loading, setLoading] = useState(true);
  const [showSchedule, setShowSchedule] = useState(!!new URLSearchParams(window.location.search).get('household_id'));
  const [selectedDog, setSelectedDog] = useState(null);

  const fetchData = useCallback(async () => {
    try {
      const dogsRes = await api.get('/dogs', { params: { limit: 200 } });
      const pending = dogsRes.data.filter(d =>
        d.meet_and_greet_status === 'required' || d.meet_and_greet_status === 'scheduled'
      );
      setDogs(pending);

      // Load pending customer M&G requests
      api.get('/meet-and-greets/upcoming').then(r => setPendingRequests(r.data || [])).catch(() => {});

      // Load MAG records for each pending dog
      const magData = {};
      await Promise.all(pending.slice(0, 20).map(async dog => {
        try {
          const res = await api.get(`/meet-and-greets/dog/${dog.id}`);
          magData[dog.id] = res.data;
        } catch {}
      }));
      setMags(magData);
    } catch {
      toast.error('Failed to load meet & greet data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!user) { navigate('/auth'); return; }
    fetchData();
  }, [user, navigate, fetchData]);

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-primary"></div>
    </div>
  );

  const required = dogs.filter(d => d.meet_and_greet_status === 'required');
  const scheduled = dogs.filter(d => d.meet_and_greet_status === 'scheduled');

  return (
    <div className="min-h-screen bg-[#F9F7F2]">
      <header className="bg-white border-b shadow-sm sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between">
          <h1 className="text-lg font-serif font-bold text-primary">Meet & Greet</h1>
          <Button size="sm" onClick={() => setShowSchedule(true)}>
            <PlusIcon size={16} className="mr-1" /> Schedule
          </Button>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-6">
        <Tabs defaultValue="requests">
          <TabsList className="w-full mb-6">
            <TabsTrigger value="requests" className="flex-1">
              Requests ({pendingRequests.length})
            </TabsTrigger>
            <TabsTrigger value="scheduled" className="flex-1">
              Scheduled ({scheduled.length})
            </TabsTrigger>
            <TabsTrigger value="required" className="flex-1">
              Needs M&G ({required.length})
            </TabsTrigger>
          </TabsList>

          <TabsContent value="requests">
            {pendingRequests.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground text-sm">No pending M&G requests</div>
            ) : pendingRequests.map(r => (
              <Card key={r.id} className="mb-3">
                <CardContent className="py-3 px-4">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="font-medium text-sm">{r.dog_name} <span className="text-muted-foreground font-normal">— {r.household_name}</span></p>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        {new Date(r.scheduled_at).toLocaleDateString([], {weekday:'long',month:'short',day:'numeric'})}
                        {' · '}
                        {r.slot === '10:00-10:30' ? '10:00–10:30 AM' :
                         r.slot === '10:30-11:00' ? '10:30–11:00 AM' :
                         r.slot === '11:00-11:30' ? '11:00–11:30 AM' :
                         r.slot === '11:30-12:00' ? '11:30 AM–12:00 PM' :
                         r.slot === '14:00-14:30' ? '2:00–2:30 PM' :
                         r.slot === '14:30-15:00' ? '2:30–3:00 PM' :
                         r.slot === '15:00-15:30' ? '3:00–3:30 PM' :
                         r.slot === '15:30-16:00' ? '3:30–4:00 PM' : r.slot}
                      </p>
                      {r.requested_stay_start && (
                        <p className="text-xs text-blue-600 mt-0.5">
                          Planned stay: {new Date(r.requested_stay_start+'T12:00:00').toLocaleDateString([], {month:'short',day:'numeric'})} – {new Date(r.requested_stay_end+'T12:00:00').toLocaleDateString([], {month:'short',day:'numeric',year:'numeric'})}
                        </p>
                      )}
                    </div>
                    <div className="flex flex-col gap-1 items-end">
                      <Badge className="text-xs bg-amber-100 text-amber-700">Pending</Badge>
                      <div className="flex gap-1 mt-1">
                        <Button size="sm" className="h-7 text-xs bg-green-600 hover:bg-green-700 text-white"
                          onClick={async () => {
                            try {
                              await api.patch(`/meet-and-greets/${r.id}/status`, { status: 'confirmed' });
                              toast.success('M&G confirmed');
                              setPendingRequests(prev => prev.filter(x => x.id !== r.id));
                            } catch { toast.error('Failed'); }
                          }}>Confirm</Button>
                        <Button size="sm" variant="outline" className="h-7 text-xs"
                          onClick={() => { setSelectedDog({ id: r.dog_id, household_id: r.household_id }); setShowSchedule(true); }}>
                          Edit
                        </Button>
                        <Button size="sm" variant="outline" className="h-7 text-xs text-red-500 border-red-200"
                          onClick={async () => {
                            if (!window.confirm('Cancel this M&G request?')) return;
                            try {
                              await api.patch(`/meet-and-greets/${r.id}/status`, { status: 'cancelled' });
                              toast.success('M&G cancelled');
                              setPendingRequests(prev => prev.filter(x => x.id !== r.id));
                            } catch { toast.error('Failed'); }
                          }}>Cancel</Button>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </TabsContent>

          <TabsContent value="scheduled">
            {scheduled.length === 0 ? (
              <Card><CardContent className="py-10 text-center text-muted-foreground">
                No scheduled meet & greets
              </CardContent></Card>
            ) : (
              <div className="space-y-3">
                {scheduled.map(dog => (
                  <MAGCard
                    key={dog.id}
                    dog={dog}
                    mags={mags[dog.id] || []}
                    onRecordOutcome={() => { setSelectedDog(dog); }}
                    onRefresh={fetchData}
                  />
                ))}
              </div>
            )}
          </TabsContent>

          <TabsContent value="required">
            {required.length === 0 ? (
              <Card><CardContent className="py-10 text-center text-muted-foreground">
                All dogs have completed meet & greets
              </CardContent></Card>
            ) : (
              <div className="space-y-3">
                {required.map(dog => (
                  <Card key={dog.id}>
                    <CardContent className="py-3 px-4">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <DogIcon size={16} className="text-muted-foreground" />
                          <div>
                            <p className="font-medium text-sm">{dog.name}</p>
                            <p className="text-xs text-muted-foreground">{dog.breed}</p>
                          </div>
                        </div>
                        <Button size="sm" variant="outline"
                          onClick={() => { setSelectedDog(dog); setShowSchedule(true); }}>
                          Schedule M&G
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </TabsContent>
        </Tabs>
      </main>

      {showSchedule && (
        <ScheduleMAGModal
          preselectedDog={selectedDog}
          preselectedHouseholdId={preselectedHouseholdId}
          onClose={() => { setShowSchedule(false); setSelectedDog(null); }}
          onSuccess={() => { setShowSchedule(false); setSelectedDog(null); fetchData(); }}
        />
      )}

      {selectedDog && !showSchedule && (
        <RecordOutcomeModal
          dog={selectedDog}
          mags={mags[selectedDog.id] || []}
          onClose={() => setSelectedDog(null)}
          onSuccess={() => { setSelectedDog(null); fetchData(); }}
        />
      )}
    </div>
  );
};

const MAGCard = ({ dog, mags, onRecordOutcome, onRefresh }) => {
  const latest = mags[0];
  return (
    <Card>
      <CardContent className="py-4 px-4">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-start gap-3">
            <DogIcon size={16} className="text-blue-500 mt-0.5" />
            <div>
              <p className="font-medium text-sm">{dog.name}</p>
              <p className="text-xs text-muted-foreground">{dog.breed}</p>
              {latest?.scheduled_at && (
                <p className="text-xs text-blue-600 flex items-center gap-1 mt-1">
                  <ClockIcon size={11} />
                  {new Date(latest.scheduled_at).toLocaleString()}
                </p>
              )}
            </div>
          </div>
          <Button size="sm" className="bg-green-600 hover:bg-green-700 text-white"
            onClick={onRecordOutcome}>
            Record Outcome
          </Button>
        </div>
      </CardContent>
    </Card>
  );
};

const MAG_SLOTS = [
  { id: '10:00-10:30', label: '10:00–10:30 AM', window: 'Morning' },
  { id: '10:30-11:00', label: '10:30–11:00 AM', window: 'Morning' },
  { id: '11:00-11:30', label: '11:00–11:30 AM', window: 'Morning' },
  { id: '11:30-12:00', label: '11:30 AM–12:00 PM', window: 'Morning' },
  { id: '14:00-14:30', label: '2:00–2:30 PM', window: 'Afternoon' },
  { id: '14:30-15:00', label: '2:30–3:00 PM', window: 'Afternoon' },
  { id: '15:00-15:30', label: '3:00–3:30 PM', window: 'Afternoon' },
  { id: '15:30-16:00', label: '3:30–4:00 PM', window: 'Afternoon' },
];
const MAG_DAYS = [0,1,3,5];
const MAG_DAY_NAMES = ['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'];

const ScheduleMAGModal = ({ preselectedDog, onClose, onSuccess }) => {
  const [dogs, setDogs] = useState([]);
  const [households, setHouseholds] = useState([]);
  const [form, setForm] = useState({
    dog_id: preselectedDog?.id || '',
    household_id: preselectedDog?.household_id || '',
    scheduled_date: '',
    slot: '',
    stay_start: '',
    stay_end: '',
  });
  const [availableSlots, setAvailableSlots] = useState(MAG_SLOTS.map(s => s.id));
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    Promise.all([
      api.get('/dogs', { params: { limit: 200 } }),
      api.get('/households', { params: { limit: 100 } }),
    ]).then(([dogsRes, hhRes]) => {
      setDogs((dogsRes.data?.dogs || dogsRes.data || []).filter(d => d.meet_and_greet_status !== 'completed'));
      setHouseholds(hhRes.data || []);
    });
  }, []);

  useEffect(() => {
    if (form.scheduled_date) {
      api.get('/meet-and-greets/available-slots', { params: { date: form.scheduled_date } })
        .then(r => { if (r.data.slots) setAvailableSlots(r.data.slots); })
        .catch(() => setAvailableSlots(MAG_SLOTS.map(s => s.id)));
    }
  }, [form.scheduled_date]);

  const availableDates = [];
  const today = new Date();
  for (let i = 0; i <= 90 && availableDates.length < 16; i++) {
    const d = new Date(today);
    d.setDate(today.getDate() + i);
    if (MAG_DAYS.includes(d.getDay())) {
      const str = d.toISOString().split('T')[0];
      availableDates.push({ str, label: `${MAG_DAY_NAMES[d.getDay()]} ${d.toLocaleDateString([], {month:'short',day:'numeric'})}` });
    }
  }

  const handleSubmit = async () => {
    if (!form.dog_id || !form.household_id) { toast.error('Dog and household required'); return; }
    if (!form.scheduled_date || !form.slot) { toast.error('Date and time slot required'); return; }
    setSubmitting(true);
    try {
      await api.post('/meet-and-greets/request', {
        dog_id: form.dog_id,
        household_id: form.household_id,
        scheduled_date: form.scheduled_date,
        slot: form.slot,
        stay_start: form.stay_start || undefined,
        stay_end: form.stay_end || undefined,
      });
      toast.success('M&G scheduled');
      onSuccess();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to schedule');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-end md:items-center justify-center p-4">
      <div className="bg-white rounded-t-2xl md:rounded-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="p-5 space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-lg font-bold">Schedule Meet & Greet</h2>
            <button onClick={onClose} className="text-muted-foreground text-xl">×</button>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label>Dog *</Label>
              <select className="w-full mt-1 border rounded-md px-3 py-2 text-sm bg-background"
                value={form.dog_id} onChange={e => setForm(f => ({...f, dog_id: e.target.value}))}>
                <option value="">Select dog...</option>
                {dogs.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
              </select>
            </div>
            <div>
              <Label>Household *</Label>
              <select className="w-full mt-1 border rounded-md px-3 py-2 text-sm bg-background"
                value={form.household_id} onChange={e => setForm(f => ({...f, household_id: e.target.value}))}>
                <option value="">Select household...</option>
                {households.map(h => <option key={h.id} value={h.id}>{h.display_name}</option>)}
              </select>
            </div>
          </div>
          <div>
            <Label>Date (Sun / Mon / Wed / Fri)</Label>
            <div className="grid grid-cols-2 gap-1.5 mt-1 max-h-40 overflow-y-auto pr-1">
              {availableDates.map(d => (
                <button key={d.str} type="button"
                  onClick={() => setForm(f => ({...f, scheduled_date: d.str, slot: ''}))}
                  className={`px-2 py-1.5 rounded-lg border text-xs text-left transition-colors ${
                    form.scheduled_date === d.str
                      ? 'bg-primary text-primary-foreground border-primary'
                      : 'border-border hover:bg-muted'
                  }`}>{d.label}</button>
              ))}
            </div>
          </div>
          {form.scheduled_date && (
            <div>
              <Label>Time Slot</Label>
              {['Morning','Afternoon'].map(win => (
                <div key={win} className="mt-2">
                  <p className="text-xs text-muted-foreground mb-1">{win}</p>
                  <div className="grid grid-cols-2 gap-1.5">
                    {MAG_SLOTS.filter(s => s.window === win).map(slot => {
                      const avail = availableSlots.includes(slot.id);
                      return (
                        <button key={slot.id} type="button" disabled={!avail}
                          onClick={() => avail && setForm(f => ({...f, slot: slot.id}))}
                          className={`px-2 py-1.5 rounded-lg border text-xs transition-colors ${
                            !avail ? 'opacity-40 cursor-not-allowed bg-gray-50' :
                            form.slot === slot.id ? 'bg-primary text-primary-foreground border-primary' :
                            'border-border hover:bg-muted'
                          }`}>{slot.label}{!avail && ' ✗'}</button>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          )}
          <div>
            <Label>Planned Stay Dates (Optional)</Label>
            <div className="grid grid-cols-2 gap-2 mt-1">
              <Input type="date" placeholder="Check-in" value={form.stay_start}
                onChange={e => setForm(f => ({...f, stay_start: e.target.value}))} />
              <Input type="date" placeholder="Check-out" value={form.stay_end}
                onChange={e => setForm(f => ({...f, stay_end: e.target.value}))} />
            </div>
          </div>
          <div className="flex gap-3 pt-1">
            <Button variant="outline" className="flex-1" onClick={onClose}>Cancel</Button>
            <Button className="flex-1" onClick={handleSubmit} disabled={submitting || !form.scheduled_date || !form.slot}>
              {submitting ? 'Scheduling...' : 'Schedule M&G'}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

const RecordOutcomeModal = ({ dog, mags, onClose, onSuccess }) => {
  const latestMag = mags[0];
  const [form, setForm] = useState({
    outcome: '',
    conditions: '',
    boarding_eligible_granted: false,
    daycare_eligible_granted: false,
    notes: '',
    dog_compatibility: '',
    handler_notes: '',
    dogs_to_avoid: '',
    playgroup_notes: '',
  });
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    if (!form.outcome) { toast.error('Outcome is required'); return; }
    if (!latestMag) { toast.error('No scheduled M&G found for this dog'); return; }
    if (form.outcome === 'CONDITIONAL' && !form.conditions) {
      toast.error('Conditions are required for conditional outcome'); return;
    }
    setSubmitting(true);
    try {
      await api.post(`/meet-and-greets/${latestMag.id}/outcome`, {
        outcome: form.outcome,
        conditions: form.conditions || undefined,
        boarding_eligible_granted: form.boarding_eligible_granted,
        daycare_eligible_granted: form.daycare_eligible_granted,
        notes: [
          form.notes,
          form.dog_compatibility ? `Dog compatibility: ${form.dog_compatibility}` : '',
          form.handler_notes ? `Handler notes: ${form.handler_notes}` : '',
          form.dogs_to_avoid ? `Dogs to avoid: ${form.dogs_to_avoid}` : '',
          form.playgroup_notes ? `Playgroup notes: ${form.playgroup_notes}` : '',
        ].filter(Boolean).join('\n') || undefined,
      });
      toast.success('Outcome recorded');
      onSuccess();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to record outcome');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-end md:items-center justify-center p-4">
      <div className="bg-white rounded-t-2xl md:rounded-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="p-6 space-y-4">
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-lg font-bold">Record M&G Outcome</h2>
              <p className="text-sm text-muted-foreground">{dog.name} · {dog.breed}</p>
            </div>
            <button onClick={onClose} className="text-muted-foreground text-xl">×</button>
          </div>

          <div>
            <Label>Outcome *</Label>
            <div className="grid grid-cols-3 gap-2 mt-2">
              {[
                { value: 'PASS', label: '✓ Pass', className: 'border-green-300 bg-green-50 text-green-700' },
                { value: 'CONDITIONAL', label: '~ Conditional', className: 'border-amber-300 bg-amber-50 text-amber-700' },
                { value: 'FAIL', label: '✗ Fail', className: 'border-red-300 bg-red-50 text-red-700' },
                { value: 'NO_SHOW', label: 'No Show', className: 'border-gray-300 bg-gray-50 text-gray-600' },
                { value: 'RESCHEDULED', label: 'Reschedule', className: 'border-blue-300 bg-blue-50 text-blue-700' },
              ].map(opt => (
                <button key={opt.value} type="button"
                  onClick={() => setForm(f => ({...f, outcome: opt.value}))}
                  className={`p-2 rounded-lg border text-xs font-medium transition-colors ${
                    form.outcome === opt.value ? opt.className + ' ring-2 ring-offset-1 ring-current' : 'border-border hover:bg-muted'
                  }`}>
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {form.outcome === 'PASS' && (
            <div className="flex gap-4">
              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <input type="checkbox" checked={form.boarding_eligible_granted}
                  onChange={e => setForm(f => ({...f, boarding_eligible_granted: e.target.checked}))} className="w-4 h-4" />
                Boarding eligible
              </label>
              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <input type="checkbox" checked={form.daycare_eligible_granted}
                  onChange={e => setForm(f => ({...f, daycare_eligible_granted: e.target.checked}))} className="w-4 h-4" />
                Daycare eligible
              </label>
            </div>
          )}

          {form.outcome === 'CONDITIONAL' && (
            <div>
              <Label>Conditions *</Label>
              <Textarea value={form.conditions}
                onChange={e => setForm(f => ({...f, conditions: e.target.value}))}
                className="mt-1" rows={2} placeholder="Describe the conditions..." />
            </div>
          )}

          <div>
            <Label>Dog Compatibility Notes</Label>
            <Textarea value={form.dog_compatibility}
              onChange={e => setForm(f => ({...f, dog_compatibility: e.target.value}))}
              className="mt-1" rows={2} placeholder="How did the dog interact with other dogs?" />
          </div>

          <div>
            <Label>Dogs to Avoid</Label>
            <Input value={form.dogs_to_avoid}
              onChange={e => setForm(f => ({...f, dogs_to_avoid: e.target.value}))}
              className="mt-1" placeholder="List any specific dogs to keep separate" />
          </div>

          <div>
            <Label>Handler Notes</Label>
            <Textarea value={form.handler_notes}
              onChange={e => setForm(f => ({...f, handler_notes: e.target.value}))}
              className="mt-1" rows={2} placeholder="Handling observations, triggers, special instructions..." />
          </div>

          <div>
            <Label>Playgroup Notes</Label>
            <Input value={form.playgroup_notes}
              onChange={e => setForm(f => ({...f, playgroup_notes: e.target.value}))}
              className="mt-1" placeholder="Approved playgroups or grouping notes" />
          </div>

          <div>
            <Label>General Notes</Label>
            <Textarea value={form.notes}
              onChange={e => setForm(f => ({...f, notes: e.target.value}))}
              className="mt-1" rows={2} placeholder="Any other observations..." />
          </div>

          <div className="flex gap-3 pt-2">
            <Button variant="outline" className="flex-1" onClick={onClose}>Cancel</Button>
            <Button className="flex-1" onClick={handleSubmit} disabled={submitting || !form.outcome}>
              {submitting ? 'Saving...' : 'Save Outcome'}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MeetAndGreetPage;
