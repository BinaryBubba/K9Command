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
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { AlertCircleIcon, CheckCircleIcon, ClockIcon, DogIcon, PlusIcon, UploadIcon } from 'lucide-react';
import { toast } from 'sonner';
import PinModal from '../components/PinModal';
import { useRef } from 'react';

const BELONGINGS_OPTIONS = [
  { key: 'leash', label: '🦮 Leash' },
  { key: 'collar', label: '🔔 Collar' },
  { key: 'bed_blanket', label: '🛏️ Bed/Blanket' },
  { key: 'food', label: '🍖 Food (owner-supplied)' },
  { key: 'medication', label: '💊 Medication' },
  { key: 'toys', label: '🎾 Toys' },
  { key: 'crate', label: '📦 Crate' },
];

const CheckInOutPage = () => {
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const [arrivals, setArrivals] = useState([]);
  const [departures, setDepartures] = useState([]);
  const [rooms, setRooms] = useState([]);
  const [loading, setLoading] = useState(true);
  const [pinModal, setPinModal] = useState(null); // { type, data, onSuccess }
  const [selectedArrival, setSelectedArrival] = useState(null);
  const [selectedDeparture, setSelectedDeparture] = useState(null);

  const fetchData = useCallback(async () => {
    try {
      const [arrivalsRes, departuresRes, roomsRes] = await Promise.all([
        api.get('/stays/arrivals/today'),
        api.get('/stays/departures/today'),
        api.get('/bookings/rooms/list'),
      ]);
      setArrivals(arrivalsRes.data);
      setDepartures(departuresRes.data);
      setRooms(roomsRes.data);
    } catch {
      toast.error('Failed to load check-in data');
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

  return (
    <>
    <div className="min-h-screen bg-[#F9F7F2]">
      <header className="bg-white border-b shadow-sm sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 py-3">
          <h1 className="text-lg font-serif font-bold text-primary">Check In / Out</h1>
          <p className="text-xs text-muted-foreground">{new Date().toLocaleDateString(undefined, { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}</p>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-6">
        <Tabs defaultValue="checkin">
          <TabsList className="w-full mb-6">
            <TabsTrigger value="checkin" className="flex-1">
              Arrivals ({arrivals.length})
            </TabsTrigger>
            <TabsTrigger value="checkout" className="flex-1">
              Departures ({departures.length})
            </TabsTrigger>
          </TabsList>

          <TabsContent value="checkin">
            {arrivals.length === 0 ? (
              <Card><CardContent className="py-12 text-center space-y-2">
                <CheckCircleIcon size={32} className="mx-auto text-green-400" />
                <p className="font-medium">No arrivals scheduled for today</p>
                <p className="text-sm text-muted-foreground">All caught up!</p>
              </CardContent></Card>
            ) : (
              <div className="space-y-3">
                {arrivals.map(arrival => (
                  <Card key={arrival.id}>
                    <CardContent className="py-4 px-4">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <DogIcon size={18} className="text-muted-foreground" />
                          <div>
                            <div className="flex items-center gap-2">
                              <p className="font-medium">{arrival.dog_name}</p>
                              {arrival.is_first_stay && <Badge className="text-xs bg-blue-100 text-blue-700">1st stay</Badge>}
                              {arrival.has_alert && <AlertCircleIcon size={14} className="text-red-500" />}
                            </div>
                            <p className="text-xs text-muted-foreground">{arrival.household_name}</p>
                            <p className="text-xs font-medium text-blue-600">
                              🕐 Scheduled: {new Date(arrival.check_in_date).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                              {' · '}{new Date(arrival.check_in_date).toLocaleDateString([], { month: 'short', day: 'numeric' })}
                            </p>
                          </div>
                        </div>
                        <Button size="sm" className="bg-green-600 hover:bg-green-700 text-white"
                          onClick={() => setSelectedArrival(arrival)}>
                          Check In
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </TabsContent>

          <TabsContent value="checkout">
            {departures.length === 0 ? (
              <Card><CardContent className="py-12 text-center space-y-2">
                <CheckCircleIcon size={32} className="mx-auto text-green-400" />
                <p className="font-medium">No departures scheduled for today</p>
                <p className="text-sm text-muted-foreground">All caught up!</p>
              </CardContent></Card>
            ) : (
              <div className="space-y-3">
                {departures.map(dep => (
                  <Card key={dep.id}>
                    <CardContent className="py-4 px-4">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <DogIcon size={18} className="text-muted-foreground" />
                          <div>
                            <p className="font-medium">{dep.dog_name}</p>
                            <p className="text-xs text-muted-foreground">{dep.household_name}</p>
                            <p className="text-xs font-medium text-orange-600">
                              🕐 Scheduled: {new Date(dep.check_out_date).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                              {' · '}{new Date(dep.check_out_date).toLocaleDateString([], { month: 'short', day: 'numeric' })}
                            </p>
                            {dep.room_name && <p className="text-xs text-muted-foreground">Room: {dep.room_name}</p>}
                          </div>
                        </div>
                        <Button size="sm" onClick={() => setSelectedDeparture(dep)}>Check Out</Button>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </TabsContent>
        </Tabs>
      </main>

      {selectedArrival && (
        <CheckInModal
          arrival={selectedArrival}
          rooms={rooms}
          onClose={() => setSelectedArrival(null)}
          onSuccess={() => { setSelectedArrival(null); fetchData(); toast.success(`${selectedArrival.dog_name} checked in!`); }}
        />
      )}
      {selectedDeparture && (
        <CheckOutModal
          departure={selectedDeparture}
          onClose={() => setSelectedDeparture(null)}
          onSuccess={() => { setSelectedDeparture(null); fetchData(); toast.success(`${selectedDeparture.dog_name} checked out!`); }}
        />
      )}
    </div>
  );
};

const CheckInModal = ({ arrival, rooms, onClose, onSuccess }) => {
  const [form, setForm] = useState({
    room_id: '',
    intake_condition_note: '',
    belongings_checked: {},
    belongings_other: '',
    feeding_override_detail: '',
    feeding_override_reason: '',
  });
  const [dogInfo, setDogInfo] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (arrival.dog_id) {
      api.get(`/dogs/${arrival.dog_id}`).then(r => setDogInfo(r.data)).catch(() => {});
    }
  }, [arrival.dog_id]);

  const toggleBelonging = (key) => {
    setForm(f => ({ ...f, belongings_checked: { ...f.belongings_checked, [key]: !f.belongings_checked[key] } }));
  };

  const buildBelongingsNote = () => {
    const checked = BELONGINGS_OPTIONS.filter(o => form.belongings_checked[o.key]).map(o => o.label.split(' ').slice(1).join(' '));
    if (form.belongings_other) checked.push(form.belongings_other);
    return checked.join(', ');
  };

  const handleSubmit = async () => {
    if (!form.room_id) { toast.error('Please select a room'); return; }
    setSubmitting(true);
    try {
      const payload = {
        booking_id: arrival.booking_id,
        dog_id: arrival.dog_id,
        room_id: form.room_id,
        intake_condition_note: form.intake_condition_note || undefined,
        belongings_note: buildBelongingsNote() || undefined,
      };
      if (form.feeding_override_detail) {
        payload.feeding_override = {
          type: 'instructions',
          detail: form.feeding_override_detail,
          reason: form.feeding_override_reason,
        };
      }
      await api.post('/stays/check-in', payload);
      onSuccess();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Check-in failed');
    } finally {
      setSubmitting(false);
    }
  };

  const rooms_only = rooms.filter(r => !r.room_type || r.room_type === 'room');
  const crates = rooms.filter(r => r.room_type && r.room_type !== 'room');

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-end md:items-center justify-center p-4">
      <div className="bg-white rounded-t-2xl md:rounded-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="p-6 space-y-5">
          <div className="flex justify-between items-start">
            <div>
              <h2 className="text-lg font-bold">Check In — {arrival.dog_name}</h2>
              {arrival.is_first_stay && <Badge className="mt-1 bg-blue-100 text-blue-700">⭐ First Stay</Badge>}
            </div>
            <button onClick={onClose} className="text-muted-foreground text-xl leading-none">×</button>
          </div>

          {dogInfo?.meet_and_greet_status !== 'completed' && (
            <div className="flex items-center gap-2 p-2 bg-amber-50 border border-amber-200 rounded text-xs text-amber-800">
              <AlertCircleIcon size={12} /> Meet & greet not completed
            </div>
          )}

          <div>
            <Label>Assign Room *</Label>
            <div className="grid grid-cols-4 gap-2 mt-2">
              {rooms_only.map(room => (
                <button key={room.id} type="button"
                  onClick={() => setForm(f => ({...f, room_id: room.id}))}
                  disabled={room.is_out_of_service}
                  className={`p-2 rounded-lg border text-xs font-medium transition-colors ${
                    form.room_id === room.id ? 'bg-primary text-primary-foreground border-primary' :
                    room.is_out_of_service ? 'bg-gray-100 text-gray-400 cursor-not-allowed' :
                    'border-border hover:bg-muted'
                  }`}>{room.name}</button>
              ))}
            </div>
            {crates.length > 0 && <>
              <p className="text-xs text-muted-foreground mt-3 mb-1">Crates</p>
              <div className="grid grid-cols-4 gap-2">
                {crates.map(crate => (
                  <button key={crate.id} type="button"
                    onClick={() => setForm(f => ({...f, room_id: crate.id}))}
                    disabled={crate.is_out_of_service}
                    className={`p-2 rounded-lg border text-xs font-medium transition-colors ${
                      form.room_id === crate.id ? 'bg-primary text-primary-foreground border-primary' :
                      crate.is_out_of_service ? 'bg-gray-100 text-gray-400 cursor-not-allowed' :
                      'border-border hover:bg-muted'
                    }`}>{crate.name}</button>
                ))}
              </div>
            </>}
          </div>

          <div>
            <Label>Belongings Left With Dog</Label>
            <div className="grid grid-cols-2 gap-2 mt-2">
              {BELONGINGS_OPTIONS.map(opt => (
                <label key={opt.key} className={`flex items-center gap-2 p-2 rounded-lg border cursor-pointer text-sm transition-colors ${
                  form.belongings_checked[opt.key] ? 'bg-primary/10 border-primary/30' : 'border-border hover:bg-muted'
                }`}>
                  <input type="checkbox" checked={!!form.belongings_checked[opt.key]} onChange={() => toggleBelonging(opt.key)} className="w-3.5 h-3.5" />
                  {opt.label}
                </label>
              ))}
            </div>
            <Input placeholder="Other items..." value={form.belongings_other}
              onChange={e => setForm(f => ({...f, belongings_other: e.target.value}))} className="mt-2" />
          </div>

          <div>
            <Label>Intake Condition Note</Label>
            <Textarea placeholder="Any observations at drop-off..." value={form.intake_condition_note}
              onChange={e => setForm(f => ({...f, intake_condition_note: e.target.value}))} className="mt-1" rows={2} />
          </div>

          <div>
            <Label>Feeding Override</Label>
            <Input placeholder="e.g. Only 1 cup per meal this stay" value={form.feeding_override_detail}
              onChange={e => setForm(f => ({...f, feeding_override_detail: e.target.value}))} className="mt-1" />
            {form.feeding_override_detail && (
              <Input placeholder="Reason..." value={form.feeding_override_reason}
                onChange={e => setForm(f => ({...f, feeding_override_reason: e.target.value}))} className="mt-2" />
            )}
          </div>

          <div className="flex gap-3 pt-2">
            <Button variant="outline" className="flex-1" onClick={onClose}>Cancel</Button>
            <Button className="flex-1 bg-green-600 hover:bg-green-700" onClick={handleSubmit} disabled={submitting}>
              {submitting ? 'Checking in...' : 'Confirm Check In'}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

const CheckOutModal = ({ departure, onClose, onSuccess }) => {
  const [form, setForm] = useState({
    pickup_person_name: '',
    relationship_to_household: '',
    is_authorized_pickup: false,
    id_verified: false,
    id_type: '',
    appetite_rating: '',
    dogs_played_well_with: '',
    medication_compliance: '',
    concerns: '',
    overall_notes: '',
  });
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    if (!form.pickup_person_name.trim()) { toast.error('Pickup person name is required'); return; }
    setSubmitting(true);
    try {
      const summary = [
        form.appetite_rating ? `Appetite: ${form.appetite_rating}` : '',
        form.dogs_played_well_with ? `Played well with: ${form.dogs_played_well_with}` : '',
        form.medication_compliance ? `Medication: ${form.medication_compliance}` : '',
        form.concerns ? `Concerns: ${form.concerns}` : '',
        form.overall_notes,
      ].filter(Boolean).join(' · ');

      await api.post(`/stays/${departure.id}/check-out`, {
        pickup_person_name: form.pickup_person_name,
        relationship_to_household: form.relationship_to_household,
        is_authorized_pickup: form.is_authorized_pickup,
        id_verified: form.id_verified,
        id_type: form.id_type,
        checkout_summary: summary || undefined,
      });
      onSuccess();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Check-out failed');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-end md:items-center justify-center p-4">
      <div className="bg-white rounded-t-2xl md:rounded-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="p-6 space-y-4">
          <div className="flex justify-between items-start">
            <h2 className="text-lg font-bold">Check Out — {departure.dog_name}</h2>
            <button onClick={onClose} className="text-muted-foreground text-xl leading-none">×</button>
          </div>

          <div className="space-y-3 border-b pb-4">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Pickup</p>
            <div>
              <Label>Pickup Person *</Label>
              <Input placeholder="Full name" value={form.pickup_person_name}
                onChange={e => setForm(f => ({...f, pickup_person_name: e.target.value}))} className="mt-1" />
            </div>
            <div>
              <Label>Relationship</Label>
              <Input placeholder="e.g. Owner, spouse, dog walker" value={form.relationship_to_household}
                onChange={e => setForm(f => ({...f, relationship_to_household: e.target.value}))} className="mt-1" />
            </div>
            <div className="flex gap-4">
              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <input type="checkbox" checked={form.is_authorized_pickup}
                  onChange={e => setForm(f => ({...f, is_authorized_pickup: e.target.checked}))} className="w-4 h-4" />
                Authorized pickup
              </label>
              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <input type="checkbox" checked={form.id_verified}
                  onChange={e => setForm(f => ({...f, id_verified: e.target.checked}))} className="w-4 h-4" />
                ID verified
              </label>
            </div>
            {!form.is_authorized_pickup && form.pickup_person_name && (
              <div className="bg-amber-50 border border-amber-200 rounded p-2 flex items-center gap-2">
                <AlertCircleIcon size={14} className="text-amber-600" />
                <span className="text-xs text-amber-800">Not an authorized pickup — owner acknowledgment required</span>
              </div>
            )}
          </div>

          <div className="space-y-3">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Stay Report</p>
            <div>
              <Label>Appetite</Label>
              <select className="w-full mt-1 border rounded-md px-3 py-2 text-sm bg-background"
                value={form.appetite_rating} onChange={e => setForm(f => ({...f, appetite_rating: e.target.value}))}>
                <option value="">Not recorded</option>
                <option value="Excellent">Excellent — ate everything</option>
                <option value="Good">Good — ate most meals</option>
                <option value="Fair">Fair — ate some meals</option>
                <option value="Poor">Poor — barely ate</option>
                <option value="Refused food">Refused food</option>
              </select>
            </div>
            <div>
              <Label>Played Well With</Label>
              <Input placeholder="Dog names or 'all'" value={form.dogs_played_well_with}
                onChange={e => setForm(f => ({...f, dogs_played_well_with: e.target.value}))} className="mt-1" />
            </div>
            <div>
              <Label>Medication Compliance</Label>
              <select className="w-full mt-1 border rounded-md px-3 py-2 text-sm bg-background"
                value={form.medication_compliance} onChange={e => setForm(f => ({...f, medication_compliance: e.target.value}))}>
                <option value="">N/A</option>
                <option value="All given as scheduled">All given as scheduled</option>
                <option value="Some refusals">Some refusals</option>
                <option value="Difficulty administering">Difficulty administering</option>
              </select>
            </div>
            <div>
              <Label>Concerns or Incidents</Label>
              <Textarea placeholder="Any health concerns, behavioral issues, or incidents..."
                value={form.concerns} onChange={e => setForm(f => ({...f, concerns: e.target.value}))} className="mt-1" rows={2} />
            </div>
            <div>
              <Label>Notes for Owner</Label>
              <Textarea placeholder="General summary..." value={form.overall_notes}
                onChange={e => setForm(f => ({...f, overall_notes: e.target.value}))} className="mt-1" rows={2} />
            </div>
          </div>

          <div className="flex gap-3 pt-2">
            <Button variant="outline" className="flex-1" onClick={onClose}>Cancel</Button>
            <Button className="flex-1" onClick={handleSubmit} disabled={submitting}>
              {submitting ? 'Checking out...' : 'Confirm Check Out'}
            </Button>
          </div>
        </div>
      </div>
    </div>
    {pinModal && (
      <PinModal
        title="Manager Override Required"
        message={pinModal.message || "Enter a manager PIN to continue"}
        onVerified={(name) => { pinModal.onSuccess(name); setPinModal(null); }}
        onCancel={() => setPinModal(null)}
      />
    )}
    </>
  );
};

export default CheckInOutPage;
