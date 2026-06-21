import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import useAuthStore from '../store/authStore';
import api from '../utils/api';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { ArrowLeftIcon, CheckCircleIcon } from 'lucide-react';
import { toast } from 'sonner';

const CustomerAddDogPage = () => {
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: '', breed: '', age: '', weight: '', notes: '' });
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [newDog, setNewDog] = useState(null);
  const [newDog, setNewDog] = useState(null);

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

  if (submitted) return (
    <div className="min-h-screen bg-[#F9F7F2] flex items-center justify-center p-4">
      <div className="text-center space-y-4 max-w-sm">
        <CheckCircleIcon size={48} className="mx-auto text-green-500" />
        <h2 className="text-xl font-bold">{form.name || newDog?.name} Added!</h2>
        <p className="text-muted-foreground text-sm">
          All dogs need a Meet & Greet with our staff before their first stay. Would you like to schedule one now?
        </p>
        <Button className="w-full bg-primary" onClick={() => navigate(`/customer/mag-request?dog_id=${newDog?.id}&household_id=${newDog?.householdId}&dog_name=${encodeURIComponent(newDog?.name || '')}`)}>
          Schedule Meet & Greet →
        </Button>
        <div className="flex gap-2">
          <Button variant="outline" className="flex-1" onClick={() => { setSubmitted(false); setForm({ name:'',breed:'',age:'',weight:'',notes:'' }); setNewDog(null); }}>
            Add Another Dog
          </Button>
          <Button variant="ghost" className="flex-1" onClick={() => navigate('/customer/dashboard')}>
            Skip for Now
          </Button>
        </div>
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
