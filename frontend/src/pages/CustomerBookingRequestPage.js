import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import useAuthStore from '../store/authStore';
import api from '../utils/api';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { ArrowLeftIcon, CheckCircleIcon } from 'lucide-react';
import { toast } from 'sonner';

const CustomerBookingRequestPage = () => {
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const [dogs, setDogs] = useState([]);
  const [orgSettings, setOrgSettings] = useState(null);
  const [form, setForm] = useState({
    check_in_date: '',
    check_out_date: '',
    dog_ids: [],
    special_request: '',
    notes: '',
  });
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  useEffect(() => {
    if (!user) { navigate('/auth'); return; }
    const fetchData = async () => {
      try {
        const meRes = await api.get('/users/me');
        const householdId = meRes.data.household_id;
        if (householdId) {
          const dogsRes = await api.get('/dogs', { params: { household_id: householdId } });
          setDogs(dogsRes.data?.dogs || dogsRes.data || []);
        }
        const orgRes = await api.get('/users/org/settings').catch(() => ({ data: {} }));
        setOrgSettings(orgRes.data);
      } catch {}
    };
    fetchData();
  }, [user, navigate]);

  const toggleDog = (dogId) => {
    setForm(f => ({
      ...f,
      dog_ids: f.dog_ids.includes(dogId)
        ? f.dog_ids.filter(id => id !== dogId)
        : [...f.dog_ids, dogId]
    }));
  };

  const handleSubmit = async () => {
    if (!form.check_in_date || !form.check_out_date) {
      toast.error('Please select check-in and check-out dates');
      return;
    }
    if (form.dog_ids.length === 0) {
      toast.error('Please select at least one dog');
      return;
    }
    if (new Date(form.check_out_date) <= new Date(form.check_in_date)) {
      toast.error('Check-out must be after check-in');
      return;
    }
    setSubmitting(true);
    try {
      // Get household_id
      const meRes = await api.get('/users/me');
      const householdId = meRes.data.household_id;
      if (!householdId) {
        toast.error('Your account is not linked to a household. Please contact us.');
        return;
      }
      await api.post('/bookings', {
        household_id: householdId,
        dog_ids: form.dog_ids,
        check_in_date: new Date(form.check_in_date).toISOString(),
        check_out_date: new Date(form.check_out_date).toISOString(),
        status: 'PENDING',
        special_request: form.special_request || undefined,
        notes: form.notes || undefined,
        service_type: 'Boarding',
      });
      setSubmitted(true);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to submit request');
    } finally {
      setSubmitting(false);
    }
  };

  if (submitted) return (
    <div className="min-h-screen bg-[#F9F7F2] flex items-center justify-center p-4">
      <div className="text-center space-y-4 max-w-sm">
        <CheckCircleIcon size={48} className="mx-auto text-green-500" />
        <h2 className="text-xl font-bold">Request Submitted!</h2>
        <p className="text-muted-foreground text-sm">
          We've received your booking request and will confirm it shortly.
          {orgSettings?.contact_phone && ` Questions? Call us at ${orgSettings.contact_phone}.`}
        </p>
        <Button onClick={() => navigate('/customer/dashboard')} className="w-full">
          Back to Dashboard
        </Button>
      </div>
    </div>
  );

  const nights = form.check_in_date && form.check_out_date
    ? Math.ceil((new Date(form.check_out_date) - new Date(form.check_in_date)) / (1000*60*60*24))
    : 0;

  return (
    <div className="min-h-screen bg-[#F9F7F2]">
      <header className="bg-white border-b shadow-sm sticky top-0 z-10">
        <div className="max-w-2xl mx-auto px-4 py-3 flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={() => navigate('/customer/dashboard')}>
            <ArrowLeftIcon size={18} />
          </Button>
          <h1 className="text-base font-serif font-bold text-primary">Request a Stay</h1>
        </div>
      </header>

      <main className="max-w-2xl mx-auto px-4 py-6 space-y-4">
        <Card>
          <CardHeader className="pb-2 pt-4"><CardTitle className="text-sm">Stay Dates</CardTitle></CardHeader>
          <CardContent className="px-4 pb-4 space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>Check-In Date *</Label>
                <Input type="date" value={form.check_in_date}
                  min={new Date().toISOString().split('T')[0]}
                  onChange={e => setForm(f=>({...f,check_in_date:e.target.value}))} className="mt-1" />
              </div>
              <div>
                <Label>Check-Out Date *</Label>
                <Input type="date" value={form.check_out_date}
                  min={form.check_in_date || new Date().toISOString().split('T')[0]}
                  onChange={e => setForm(f=>({...f,check_out_date:e.target.value}))} className="mt-1" />
              </div>
            </div>
            {nights > 0 && (
              <p className="text-xs text-muted-foreground">{nights} night{nights !== 1 ? 's' : ''}</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2 pt-4"><CardTitle className="text-sm">Select Dogs *</CardTitle></CardHeader>
          <CardContent className="px-4 pb-4">
            {dogs.length === 0 ? (
              <p className="text-sm text-amber-600">No dogs on your account. Please contact us to add your dog.</p>
            ) : dogs.map(dog => (
              <button key={dog.id} type="button"
                onClick={() => toggleDog(dog.id)}
                className={`w-full text-left p-3 rounded-lg border mb-2 transition-colors ${
                  form.dog_ids.includes(dog.id)
                    ? 'bg-primary/10 border-primary'
                    : 'border-border hover:bg-muted'
                }`}>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-sm">{dog.name}</p>
                    <p className="text-xs text-muted-foreground">{dog.breed}</p>
                  </div>
                  {form.dog_ids.includes(dog.id) && (
                    <CheckCircleIcon size={18} className="text-primary" />
                  )}
                </div>
              </button>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2 pt-4"><CardTitle className="text-sm">Special Requests</CardTitle></CardHeader>
          <CardContent className="px-4 pb-4 space-y-3">
            <Textarea value={form.special_request}
              onChange={e => setForm(f=>({...f,special_request:e.target.value}))}
              rows={3} placeholder="Feeding schedule, medications, preferences, or anything else we should know..." />
          </CardContent>
        </Card>

        {orgSettings?.contact_phone && (
          <p className="text-xs text-center text-muted-foreground">
            Questions? Call us at {orgSettings.contact_phone} or email {orgSettings.contact_email}
          </p>
        )}

        <Button className="w-full" onClick={handleSubmit} disabled={submitting}>
          {submitting ? 'Submitting...' : 'Submit Booking Request'}
        </Button>
        <p className="text-xs text-center text-muted-foreground pb-4">
          Requests are subject to availability and staff confirmation.
        </p>
      </main>
    </div>
  );
};

export default CustomerBookingRequestPage;
