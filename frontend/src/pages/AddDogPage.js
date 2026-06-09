import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import useAuthStore from '../store/authStore';
import api from '../utils/api';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { ArrowLeftIcon, AlertCircleIcon } from 'lucide-react';
import { toast } from 'sonner';

const AddDogPage = () => {
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const prefillHouseholdId = searchParams.get('household_id');

  const [households, setHouseholds] = useState([]);
  const [form, setForm] = useState({
    household_id: prefillHouseholdId || '',
    name: '',
    breed: '',
    age: '',
    weight: '',
    gender: '',
    color: '',
    spay_neuter_status: '',
    microchip_number: '',
    meal_routine: '',
    allergies: '',
    behavioral_notes: '',
    escape_risk: false,
    medical_alert: false,
    bite_history: false,
    food_guarding: false,
  });
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!user) { navigate('/auth'); return; }
    api.get('/households', { params: { limit: 100 } })
      .then(r => setHouseholds(r.data))
      .catch(() => {});
  }, [user, navigate]);

  const f = (field) => (e) => {
    const val = e.target.type === 'checkbox' ? e.target.checked : e.target.value;
    setForm(prev => ({...prev, [field]: val}));
  };

  const handleSubmit = async () => {
    if (!form.household_id) { toast.error('Select a household'); return; }
    if (!form.name.trim()) { toast.error('Dog name is required'); return; }
    if (!form.breed.trim()) { toast.error('Breed is required'); return; }
    setSubmitting(true);
    try {
      const payload = {
        ...form,
        age: form.age ? parseInt(form.age) : undefined,
        weight: form.weight ? parseFloat(form.weight) : undefined,
      };
      const res = await api.post('/dogs', payload);
      toast.success(`${form.name} added successfully`);
      navigate(`/admin/customers`);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to add dog');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#F9F7F2]">
      <header className="bg-white border-b shadow-sm sticky top-0 z-10">
        <div className="max-w-2xl mx-auto px-4 py-3 flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={() => navigate(-1)}>
            <ArrowLeftIcon size={18} />
          </Button>
          <h1 className="text-lg font-serif font-bold text-primary">Add Dog</h1>
        </div>
      </header>

      <main className="max-w-2xl mx-auto px-4 py-6 space-y-5">

        {/* Household */}
        <Card>
          <CardHeader className="pb-2 pt-4">
            <CardTitle className="text-sm">Household *</CardTitle>
          </CardHeader>
          <CardContent>
            <select
              className="w-full border rounded-md px-3 py-2 text-sm bg-background"
              value={form.household_id}
              onChange={f('household_id')}
            >
              <option value="">Select household...</option>
              {households.map(h => (
                <option key={h.id} value={h.id}>{h.display_name}</option>
              ))}
            </select>
          </CardContent>
        </Card>

        {/* Basic info */}
        <Card>
          <CardHeader className="pb-2 pt-4">
            <CardTitle className="text-sm">Basic Info</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>Name *</Label>
                <Input value={form.name} onChange={f('name')} className="mt-1" placeholder="Dog's name" />
              </div>
              <div>
                <Label>Breed *</Label>
                <Input value={form.breed} onChange={f('breed')} className="mt-1" placeholder="e.g. Golden Retriever" />
              </div>
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div>
                <Label>Age (years)</Label>
                <Input type="number" value={form.age} onChange={f('age')} className="mt-1" min="0" max="30" />
              </div>
              <div>
                <Label>Weight (lbs)</Label>
                <Input type="number" value={form.weight} onChange={f('weight')} className="mt-1" />
              </div>
              <div>
                <Label>Gender</Label>
                <select className="w-full mt-1 border rounded-md px-3 py-2 text-sm bg-background"
                  value={form.gender} onChange={f('gender')}>
                  <option value="">--</option>
                  <option value="male">Male</option>
                  <option value="female">Female</option>
                </select>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>Color / Markings</Label>
                <Input value={form.color} onChange={f('color')} className="mt-1" />
              </div>
              <div>
                <Label>Spay / Neuter</Label>
                <select className="w-full mt-1 border rounded-md px-3 py-2 text-sm bg-background"
                  value={form.spay_neuter_status} onChange={f('spay_neuter_status')}>
                  <option value="">Unknown</option>
                  <option value="neutered">Neutered</option>
                  <option value="spayed">Spayed</option>
                  <option value="intact">Intact</option>
                </select>
              </div>
            </div>
            <div>
              <Label>Microchip Number</Label>
              <Input value={form.microchip_number} onChange={f('microchip_number')} className="mt-1" />
            </div>
          </CardContent>
        </Card>

        {/* Safety flags */}
        <Card>
          <CardHeader className="pb-2 pt-4">
            <CardTitle className="text-sm flex items-center gap-2">
              <AlertCircleIcon size={14} className="text-red-500" />
              Safety Flags
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              {[
                { field: 'escape_risk', label: '⚠️ Escape Risk' },
                { field: 'medical_alert', label: '🏥 Medical Alert' },
                { field: 'bite_history', label: '🦷 Bite History' },
                { field: 'food_guarding', label: '🍖 Food Guarding' },
              ].map(({ field, label }) => (
                <label key={field} className={`flex items-center gap-2 p-3 rounded-lg border cursor-pointer transition-colors ${
                  form[field] ? 'bg-red-50 border-red-200' : 'border-border hover:bg-muted'
                }`}>
                  <input type="checkbox" checked={form[field]} onChange={f(field)} className="w-4 h-4" />
                  <span className="text-sm font-medium">{label}</span>
                </label>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Care info */}
        <Card>
          <CardHeader className="pb-2 pt-4">
            <CardTitle className="text-sm">Care Information</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div>
              <Label>Feeding Routine</Label>
              <Textarea value={form.meal_routine} onChange={f('meal_routine')}
                placeholder="e.g. 2 cups twice daily, morning and evening" className="mt-1" rows={2} />
            </div>
            <div>
              <Label>Allergies</Label>
              <Input value={form.allergies} onChange={f('allergies')} className="mt-1"
                placeholder="e.g. chicken, grain-free required" />
            </div>
            <div>
              <Label>Behavioral Notes</Label>
              <Textarea value={form.behavioral_notes} onChange={f('behavioral_notes')}
                placeholder="General notes about temperament, handling preferences..." className="mt-1" rows={3} />
            </div>
          </CardContent>
        </Card>

        <div className="flex gap-3 pb-6">
          <Button variant="outline" className="flex-1" onClick={() => navigate(-1)}>Cancel</Button>
          <Button className="flex-1" onClick={handleSubmit} disabled={submitting}>
            {submitting ? 'Adding...' : 'Add Dog'}
          </Button>
        </div>

      </main>
    </div>
  );
};

export default AddDogPage;
