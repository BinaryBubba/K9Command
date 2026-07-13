import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import useAuthStore from '../store/authStore';
import api from '../utils/api';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { ArrowLeftIcon, CheckCircleIcon, AlertTriangleIcon } from 'lucide-react';
import { toast } from 'sonner';

const CustomerAddDogPage = () => {
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: '', breed: '', age: '', weight: '', notes: '' });
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [newDog, setNewDog] = useState(null);
  const [showSkipConfirm, setShowSkipConfirm] = useState(false);

  const [existingMag, setExistingMag] = useState(null);
  const [checkingExistingMag, setCheckingExistingMag] = useState(false);
  const [joiningExisting, setJoiningExisting] = useState(false);

  useEffect(() => {
    if (!submitted || !newDog?.householdId) return;
    setCheckingExistingMag(true);
    api.get('/meet-and-greets/upcoming', { params: { household_id: newDog.householdId } })
      .then(r => {
        // A freshly-created dog can't have its own M&G row yet, so any row
        // returned here is a genuinely pre-existing household appointment.
        const rows = r.data || [];
        if (rows.length > 0) setExistingMag(rows[0]);
      })
      .catch(() => {})
      .finally(() => setCheckingExistingMag(false));
  }, [submitted, newDog]);

  const handleSubmit = async () => {
    if (!form.name.trim()) { toast.error('Dog name is required'); return; }
    setSubmitting(true);
    try {
      const meRes = await api.get('/users/me');
      const householdId = meRes.data.household_id;
      if (!householdId) {
        toast.error('Your account is not linked to a household. Please contact us.');
        return;
      }
      const dogRes = await api.post('/dogs', {
        name: form.name,
        breed: form.breed || undefined,
        age: form.age ? parseInt(form.age) : undefined,
        weight: form.weight ? parseFloat(form.weight) : undefined,
        household_id: householdId,
        notes: form.notes || undefined,
      });
      setNewDog({ id: dogRes.data.id, name: form.name, householdId });
      setSubmitted(true);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to add dog');
    } finally {
      setSubmitting(false);
    }
  };

  const handleJoinExisting = async () => {
    if (!existingMag || !newDog) return;
    setJoiningExisting(true);
    try {
      await api.post('/meet-and-greets/join-existing', {
        dog_id: newDog.id,
        join_mag_id: existingMag.id,
      });
      toast.success(`${newDog.name} added to your upcoming Meet & Greet`);
      navigate('/customer/dashboard');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to join that appointment');
    } finally {
      setJoiningExisting(false);
    }
  };

  const handleSkipClick = () => setShowSkipConfirm(true);
  const handleSkipConfirmed = () => navigate('/customer/dashboard');

  if (submitted) return (
    <div className="min-h-screen bg-[#F9F7F2] flex items-center justify-center p-4">
      <div className="text-center space-y-4 max-w-sm">
        <CheckCircleIcon size={48} className="mx-auto text-green-500" />
        <h2 className="text-xl font-bold">{form.name || newDog?.name} Added!</h2>

        {!checkingExistingMag && existingMag ? (
          <>
            <p className="text-muted-foreground text-sm">
              Your household already has a Meet & Greet scheduled for{' '}
              {existingMag.scheduled_at
                ? new Date(existingMag.scheduled_at).toLocaleDateString([], { weekday: 'long', month: 'long', day: 'numeric' })
                : 'an upcoming date'}
              . Add {newDog?.name} to that same appointment instead of scheduling a separate visit.
            </p>
            <Button className="w-full bg-primary" onClick={handleJoinExisting} disabled={joiningExisting}>
              {joiningExisting ? 'Adding...' : `Add ${newDog?.name} to That Meet & Greet →`}
            </Button>
            <Button
              variant="outline"
              className="w-full"
              onClick={() => navigate(`/customer/mag-request?dog_id=${newDog?.id}&household_id=${newDog?.householdId}&dog_name=${encodeURIComponent(newDog?.name || '')}`)}
            >
              Schedule a Different Time Instead
            </Button>
          </>
        ) : (
          <>
            <p className="text-muted-foreground text-sm">
              All dogs need a Meet & Greet with our staff before their first stay. Would you like to schedule one now?
            </p>
            <Button className="w-full bg-primary" onClick={() => navigate(`/customer/mag-request?dog_id=${newDog?.id}&household_id=${newDog?.householdId}&dog_name=${encodeURIComponent(newDog?.name || '')}`)}>
              Schedule Meet & Greet →
            </Button>
          </>
        )}

        <div className="flex gap-2">
          <Button variant="outline" className="flex-1" onClick={() => { setSubmitted(false); setForm({ name:'',breed:'',age:'',weight:'',notes:'' }); setNewDog(null); setExistingMag(null); }}>
            Add Another Dog
          </Button>
          <Button variant="ghost" className="flex-1" onClick={handleSkipClick}>
            Skip for Now
          </Button>
        </div>

        {showSkipConfirm && (
          <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">
            <div className="bg-white rounded-xl p-5 max-w-sm w-full space-y-3 text-left">
              <div className="flex items-center gap-2 text-amber-600">
                <AlertTriangleIcon size={20} />
                <h3 className="font-bold text-base">Are you sure?</h3>
              </div>
              <p className="text-sm text-muted-foreground">
                Meet & Greets must be completed before a booking can be finalized. If you skip scheduling now,
                you'll need to come back and schedule one before {newDog?.name || 'this dog'} can stay with us.
              </p>
              <div className="flex gap-2 pt-1">
                <Button variant="outline" className="flex-1" onClick={() => setShowSkipConfirm(false)}>
                  Go Back
                </Button>
                <Button variant="ghost" className="flex-1 text-muted-foreground" onClick={handleSkipConfirmed}>
                  Skip Anyway
                </Button>
              </div>
            </div>
          </div>
        )}
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
          <h1 className="text-base font-serif font-bold text-primary">Add a Dog</h1>
        </div>
      </header>

      <main className="max-w-2xl mx-auto px-4 py-6 space-y-4">
        <Card>
          <CardHeader className="pb-2 pt-4"><CardTitle className="text-sm">Dog Information</CardTitle></CardHeader>
          <CardContent className="px-4 pb-4 space-y-3">
            <div>
              <Label>Dog's Name *</Label>
              <Input value={form.name} onChange={e => setForm(f=>({...f,name:e.target.value}))} className="mt-1" placeholder="Buddy" />
            </div>
            <div>
              <Label>Breed</Label>
              <Input value={form.breed} onChange={e => setForm(f=>({...f,breed:e.target.value}))} className="mt-1" placeholder="Golden Retriever" />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>Age (years)</Label>
                <Input type="number" value={form.age} onChange={e => setForm(f=>({...f,age:e.target.value}))} className="mt-1" placeholder="3" />
              </div>
              <div>
                <Label>Weight (lbs)</Label>
                <Input type="number" value={form.weight} onChange={e => setForm(f=>({...f,weight:e.target.value}))} className="mt-1" placeholder="65" />
              </div>
            </div>
            <div>
              <Label>Notes for Staff</Label>
              <Input value={form.notes} onChange={e => setForm(f=>({...f,notes:e.target.value}))} className="mt-1" placeholder="Allergies, behavioral notes, etc." />
            </div>
          </CardContent>
        </Card>

        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
          <p className="text-sm text-amber-800 font-medium">Meet & Greet Required</p>
          <p className="text-xs text-amber-700 mt-1">All dogs must complete a Meet & Greet with our staff before their first boarding stay. We'll be in touch to schedule one after you add your dog.</p>
        </div>

        <Button className="w-full" onClick={handleSubmit} disabled={submitting}>
          {submitting ? 'Adding...' : 'Add Dog'}
        </Button>
      </main>
    </div>
  );
};

export default CustomerAddDogPage;
