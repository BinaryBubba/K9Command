import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import useAuthStore from '../store/authStore';
import api from '../utils/api';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import {
  ArrowLeftIcon, CheckCircleIcon, AlertCircleIcon,
  DogIcon, ClockIcon, UserIcon,
} from 'lucide-react';
import { toast } from 'sonner';

const CheckInOutPage = () => {
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const [arrivals, setArrivals] = useState([]);
  const [departures, setDepartures] = useState([]);
  const [rooms, setRooms] = useState([]);
  const [loading, setLoading] = useState(true);
  const [checkingIn, setCheckingIn] = useState(null);
  const [checkingOut, setCheckingOut] = useState(null);

  const fetchData = useCallback(async () => {
    try {
      const [arrRes, depRes, roomRes] = await Promise.all([
        api.get('/stays/arrivals/today'),
        api.get('/stays/departures/today'),
        api.get('/bookings/rooms/list'),
      ]);
      setArrivals(arrRes.data);
      setDepartures(depRes.data);
      setRooms(roomRes.data);
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
    <div className="min-h-screen bg-[#F9F7F2]">
      <header className="bg-white border-b shadow-sm sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={() => navigate(-1)}>
            <ArrowLeftIcon size={18} />
          </Button>
          <h1 className="text-lg font-serif font-bold text-primary">Check In / Out</h1>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-6">
        <Tabs defaultValue="arrivals">
          <TabsList className="w-full mb-6">
            <TabsTrigger value="arrivals" className="flex-1">
              Arrivals ({arrivals.length})
            </TabsTrigger>
            <TabsTrigger value="departures" className="flex-1">
              Departures ({departures.length})
            </TabsTrigger>
          </TabsList>

          {/* ARRIVALS TAB */}
          <TabsContent value="arrivals">
            {arrivals.length === 0 ? (
              <Card><CardContent className="py-12 text-center text-muted-foreground">
                No arrivals scheduled for today
              </CardContent></Card>
            ) : (
              <div className="space-y-3">
                {arrivals.map((arrival, idx) => (
                  <ArrivalCard
                    key={`${arrival.booking_id}-${arrival.dog_id}`}
                    arrival={arrival}
                    rooms={rooms}
                    onCheckIn={() => setCheckingIn(arrival)}
                  />
                ))}
              </div>
            )}
          </TabsContent>

          {/* DEPARTURES TAB */}
          <TabsContent value="departures">
            {departures.length === 0 ? (
              <Card><CardContent className="py-12 text-center text-muted-foreground">
                No departures scheduled for today
              </CardContent></Card>
            ) : (
              <div className="space-y-3">
                {departures.map(dep => (
                  <DepartureCard
                    key={dep.id}
                    departure={dep}
                    onCheckOut={() => setCheckingOut(dep)}
                  />
                ))}
              </div>
            )}
          </TabsContent>
        </Tabs>
      </main>

      {/* Check-in modal */}
      {checkingIn && (
        <CheckInModal
          arrival={checkingIn}
          rooms={rooms}
          onClose={() => setCheckingIn(null)}
          onSuccess={() => { setCheckingIn(null); fetchData(); toast.success('Dog checked in'); }}
        />
      )}

      {/* Check-out modal */}
      {checkingOut && (
        <CheckOutModal
          departure={checkingOut}
          onClose={() => setCheckingOut(null)}
          onSuccess={() => { setCheckingOut(null); fetchData(); toast.success('Dog checked out'); }}
        />
      )}
    </div>
  );
};

const ArrivalCard = ({ arrival, rooms, onCheckIn }) => (
  <Card className={arrival.already_checked_in ? 'opacity-60' : ''}>
    <CardContent className="py-4">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="bg-green-100 p-2 rounded-full">
            <DogIcon size={18} className="text-green-700" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <p className="font-semibold">{arrival.dog_name}</p>
              {arrival.is_first_stay && (
                <Badge variant="secondary" className="text-xs">First Stay</Badge>
              )}
            </div>
            <p className="text-xs text-muted-foreground">
              In: {new Date(arrival.check_in_date).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'})} &nbsp;·&nbsp;
              Out: {new Date(arrival.check_out_date).toLocaleDateString()}
            </p>
          </div>
        </div>
        {arrival.already_checked_in ? (
          <Badge className="bg-green-100 text-green-700 border-green-200">Checked In</Badge>
        ) : (
          <Button size="sm" onClick={onCheckIn} className="bg-green-600 hover:bg-green-700 text-white">
            Check In
          </Button>
        )}
      </div>
    </CardContent>
  </Card>
);

const DepartureCard = ({ departure, onCheckOut }) => (
  <Card>
    <CardContent className="py-4">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="bg-orange-100 p-2 rounded-full">
            <DogIcon size={18} className="text-orange-700" />
          </div>
          <div>
            <p className="font-semibold">{departure.dog_name}</p>
            <p className="text-xs text-muted-foreground">
              Expected out: {new Date(departure.check_out_date).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'})}
            </p>
            {departure.active_alerts?.length > 0 && (
              <div className="flex items-center gap-1 mt-1">
                <AlertCircleIcon size={12} className="text-amber-500" />
                <span className="text-xs text-amber-600">{departure.active_alerts.length} active alert{departure.active_alerts.length !== 1 ? 's' : ''}</span>
              </div>
            )}
          </div>
        </div>
        <Button size="sm" onClick={onCheckOut} variant="outline">
          Check Out
        </Button>
      </div>
    </CardContent>
  </Card>
);

const CheckInModal = ({ arrival, rooms, onClose, onSuccess }) => {
  const [form, setForm] = useState({
    room_id: '',
    intake_condition_note: '',
    belongings_note: '',
    feeding_override_detail: '',
    feeding_override_reason: '',
  });
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    if (!form.room_id) { toast.error('Please select a room'); return; }
    setSubmitting(true);
    try {
      const payload = {
        booking_id: arrival.booking_id,
        dog_id: arrival.dog_id,
        room_id: form.room_id,
        intake_condition_note: form.intake_condition_note || undefined,
        belongings_note: form.belongings_note || undefined,
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

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-end md:items-center justify-center p-4">
      <div className="bg-white rounded-t-2xl md:rounded-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="p-6 space-y-5">
          <div className="flex justify-between items-start">
            <div>
              <h2 className="text-lg font-bold">Check In — {arrival.dog_name}</h2>
              {arrival.is_first_stay && (
                <Badge className="mt-1 bg-blue-100 text-blue-700">⭐ First Stay — allow extra time</Badge>
              )}
            </div>
            <button onClick={onClose} className="text-muted-foreground text-xl">×</button>
          </div>

          <div>
            <Label>Assign Room *</Label>
            <div className="grid grid-cols-4 gap-2 mt-2">
              {rooms.map(room => (
                <button
                  key={room.id}
                  onClick={() => setForm(f => ({...f, room_id: room.id}))}
                  className={`p-2 rounded-lg border text-sm font-medium transition-colors ${
                    form.room_id === room.id
                      ? 'bg-primary text-primary-foreground border-primary'
                      : room.is_out_of_service
                      ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                      : 'border-border hover:bg-muted'
                  }`}
                  disabled={room.is_out_of_service}
                >
                  {room.name}
                </button>
              ))}
            </div>
          </div>

          <div>
            <Label>Intake Condition Note</Label>
            <Textarea
              placeholder="Any observations at drop-off..."
              value={form.intake_condition_note}
              onChange={e => setForm(f => ({...f, intake_condition_note: e.target.value}))}
              className="mt-1"
              rows={2}
            />
          </div>

          <div>
            <Label>Belongings</Label>
            <Input
              placeholder="Food, medications, toys, blanket..."
              value={form.belongings_note}
              onChange={e => setForm(f => ({...f, belongings_note: e.target.value}))}
              className="mt-1"
            />
          </div>

          <div>
            <Label>Feeding Override (if owner gave instructions)</Label>
            <Input
              placeholder="e.g. Only 1 cup per meal this stay"
              value={form.feeding_override_detail}
              onChange={e => setForm(f => ({...f, feeding_override_detail: e.target.value}))}
              className="mt-1"
            />
            {form.feeding_override_detail && (
              <Input
                placeholder="Reason (e.g. recent vet visit)"
                value={form.feeding_override_reason}
                onChange={e => setForm(f => ({...f, feeding_override_reason: e.target.value}))}
                className="mt-2"
              />
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
    checkout_summary: '',
  });
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    if (!form.pickup_person_name.trim()) { toast.error('Pickup person name is required'); return; }
    setSubmitting(true);
    try {
      await api.post(`/stays/${departure.id}/check-out`, form);
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
        <div className="p-6 space-y-5">
          <div className="flex justify-between items-start">
            <h2 className="text-lg font-bold">Check Out — {departure.dog_name}</h2>
            <button onClick={onClose} className="text-muted-foreground text-xl">×</button>
          </div>

          <div>
            <Label>Pickup Person Name *</Label>
            <Input
              placeholder="Full name"
              value={form.pickup_person_name}
              onChange={e => setForm(f => ({...f, pickup_person_name: e.target.value}))}
              className="mt-1"
            />
          </div>

          <div>
            <Label>Relationship to Household</Label>
            <Input
              placeholder="e.g. Owner, spouse, dog walker"
              value={form.relationship_to_household}
              onChange={e => setForm(f => ({...f, relationship_to_household: e.target.value}))}
              className="mt-1"
            />
          </div>

          <div className="flex gap-6">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={form.is_authorized_pickup}
                onChange={e => setForm(f => ({...f, is_authorized_pickup: e.target.checked}))}
                className="w-4 h-4"
              />
              <span className="text-sm">Authorized pickup</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={form.id_verified}
                onChange={e => setForm(f => ({...f, id_verified: e.target.checked}))}
                className="w-4 h-4"
              />
              <span className="text-sm">ID verified</span>
            </label>
          </div>

          {!form.is_authorized_pickup && form.pickup_person_name && (
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 flex items-center gap-2">
              <AlertCircleIcon size={16} className="text-amber-600" />
              <span className="text-sm text-amber-800">This person is not marked as an authorized pickup — owner acknowledgment required</span>
            </div>
          )}

          <div>
            <Label>Checkout Summary</Label>
            <Textarea
              placeholder="How was the stay? Any notes for the customer..."
              value={form.checkout_summary}
              onChange={e => setForm(f => ({...f, checkout_summary: e.target.value}))}
              className="mt-1"
              rows={2}
            />
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
  );
};

export default CheckInOutPage;
