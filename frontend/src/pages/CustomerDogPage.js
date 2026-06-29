import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import useAuthStore from '../store/authStore';
import api from '../utils/api';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { ArrowLeftIcon, DogIcon, PlusIcon } from 'lucide-react';
import { toast } from 'sonner';

const CustomerDogPage = () => {
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const { dogId } = useParams();
  const [dog, setDog] = useState(null);
  const photoRef = React.useRef();
  const vaxRef = React.useRef();
  const [showVaxForm, setShowVaxForm] = useState(false);
  const [vaxForm, setVaxForm] = useState({ vaccination_type: '', administration_date: '', expiration_date: '', provider: '' });
  const [vaxUploading, setVaxUploading] = useState(false);
  const [vaxDocKey, setVaxDocKey] = useState('');

  const handleVaxFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setVaxUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await api.post('/uploads/vaccination', formData, { headers: { 'Content-Type': 'multipart/form-data' } });
      setVaxDocKey(res.data.key);
      toast.success('Document uploaded');
    } catch { toast.error('Upload failed'); }
    finally { setVaxUploading(false); }
  };

  const handleAddVax = async () => {
    if (!vaxForm.vaccination_type) { toast.error('Vaccine type required'); return; }
    try {
      await api.post(`/vaccinations/dog/${dogId}`, { ...vaxForm, document_path: vaxDocKey || undefined });
      toast.success('Vaccination record submitted for review');
      setShowVaxForm(false);
      setVaxForm({ vaccination_type: '', administration_date: '', expiration_date: '', provider: '' });
      setVaxDocKey('');
      fetchData();
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed'); }
  };
  const [vaccinations, setVaccinations] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    try {
      const [dogRes, vacRes] = await Promise.all([
        api.get(`/dogs/${dogId}`),
        api.get(`/vaccinations/dog/${dogId}`).catch(() => ({ data: [] })),
      ]);
      setDog(dogRes.data);
      setVaccinations(vacRes.data || []);
    } catch { toast.error('Failed to load dog profile'); }
    finally { setLoading(false); }
  }, [dogId]);

  useEffect(() => {
    if (!user) { navigate('/auth'); return; }
    fetchData();
  }, [user, navigate, fetchData]);

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-primary"></div>
    </div>
  );
  if (!dog) return <div className="p-4">Dog not found</div>;

  const today = new Date();
  const in30 = new Date(today.getTime() + 30*24*60*60*1000);

  const handlePhotoUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('dog_id', dogId);
      const res = await api.post('/uploads/dog-photo', formData, { headers: { 'Content-Type': 'multipart/form-data' } });
      await api.patch(`/dogs/${dogId}/photo`, { photo_url: res.data.url, avatar_key: res.data.key });
      toast.success('Photo saved!');
      fetchData().catch(() => {});
    } catch (err) {
      if (err.message !== 'canceled') {
        toast.error(err.response?.data?.detail || err.message || 'Upload failed');
      }
    }
  };

  return (
    <div className="min-h-screen bg-[#F9F7F2]">
      <header className="bg-white border-b shadow-sm sticky top-0 z-10">
        <div className="max-w-2xl mx-auto px-4 py-3 flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={() => navigate('/customer/dashboard')}>
            <ArrowLeftIcon size={18} />
          </Button>
          <h1 className="text-base font-serif font-bold text-primary">{dog.name}</h1>
        </div>
      </header>

      <main className="max-w-2xl mx-auto px-4 py-6 space-y-4">
        {/* Dog profile */}
        <Card>
          <CardContent className="py-4 px-4">
            <div className="flex items-center gap-4">
              {dog.photo_url ? (
                <img src={dog.photo_url} alt={dog.name} className="w-16 h-16 rounded-full object-cover" />
              ) : (
                <div className="bg-primary/10 w-16 h-16 rounded-full flex items-center justify-center">
                  <DogIcon size={28} className="text-primary" />
                </div>
              )}
              <div>
                <h2 className="text-lg font-bold">{dog.name}</h2>
                <p className="text-sm text-muted-foreground">
                  {[dog.breed, dog.age ? `${dog.age} yrs` : null, dog.weight ? `${dog.weight} lbs` : null, dog.color].filter(Boolean).join(' · ')}
                </p>
                <div className="flex gap-1 mt-1 flex-wrap">
                  {dog.meet_and_greet_status === 'completed' && <Badge className="text-xs bg-green-100 text-green-700">M&G ✓</Badge>}
                  {dog.spay_neuter_status && <Badge variant="outline" className="text-xs">{dog.spay_neuter_status}</Badge>}
                  {dog.boarding_eligible && <Badge className="text-xs bg-green-100 text-green-700">✓ Boarding</Badge>}
                  {dog.escape_risk && <Badge className="text-xs bg-red-100 text-red-700">⚠️ Escape Risk</Badge>}
                  {dog.medical_alert && <Badge className="text-xs bg-red-100 text-red-700">🏥 Medical Alert</Badge>}
                </div>
                <button type="button" className="text-xs text-primary hover:underline mt-1"
                  onClick={() => photoRef.current?.click()}>
                  {dog.photo_url ? '📷 Change Photo' : '📷 Add Photo'}
                </button>
                <input ref={photoRef} type="file" accept="image/*" className="hidden" onChange={handlePhotoUpload} />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Dog Details - Editable */}
        <DogDetailsEditor dog={dog} dogId={dogId} onSaved={fetchData} />

        {/* Vaccinations */}
        <Card>
          <CardHeader className="pb-2 pt-4 px-4">
            <CardTitle className="text-sm flex items-center justify-between">
              Vaccinations
              <Button size="sm" variant="outline" className="h-7 text-xs" onClick={() => setShowVaxForm(!showVaxForm)}>
                <PlusIcon size={12} className="mr-1" /> {showVaxForm ? 'Cancel' : 'Upload Record'}
              </Button>
            </CardTitle>
          </CardHeader>
          <CardContent className="px-4 pb-4">
            {showVaxForm && (
              <div className="mb-3 p-3 border border-primary/30 rounded-lg bg-primary/5 space-y-2">
                <select className="w-full border rounded-md px-3 py-2 text-sm bg-background"
                  value={vaxForm.vaccination_type} onChange={e => setVaxForm(f=>({...f,vaccination_type:e.target.value}))}>
                  <option value="">Select vaccine type...</option>
                  <option value="Rabies">Rabies</option>
                  <option value="Distemper">Distemper (DHPP)</option>
                  <option value="Bordetella">Bordetella</option>
                  <option value="Leptospirosis">Leptospirosis</option>
                  <option value="Lyme">Lyme</option>
                  <option value="Influenza">Influenza</option>
                  <option value="Other">Other</option>
                </select>
                <div className="grid grid-cols-2 gap-2">
                  <Input type="date" placeholder="Date given" value={vaxForm.administration_date}
                    onChange={e => setVaxForm(f=>({...f,administration_date:e.target.value}))} />
                  <Input type="date" placeholder="Expiry date" value={vaxForm.expiration_date}
                    onChange={e => setVaxForm(f=>({...f,expiration_date:e.target.value}))} />
                </div>
                <Input placeholder="Veterinarian/Provider" value={vaxForm.provider}
                  onChange={e => setVaxForm(f=>({...f,provider:e.target.value}))} />
                <div className="flex items-center gap-2">
                  <Button variant="outline" size="sm" onClick={() => vaxRef.current?.click()} disabled={vaxUploading}>
                    {vaxUploading ? 'Uploading...' : vaxDocKey ? '✓ Doc uploaded' : 'Attach Document'}
                  </Button>
                  <input ref={vaxRef} type="file" accept=".pdf,image/*" className="hidden" onChange={handleVaxFileUpload} />
                </div>
                <Button size="sm" className="w-full" onClick={handleAddVax}>Submit Record</Button>
              </div>
            )}
            {vaccinations.length === 0 ? (
              <p className="text-sm text-amber-600">No vaccination records on file</p>
            ) : vaccinations.map(v => {
              const expiry = (v.expiration_date || v.expiry_date) ? new Date(v.expiration_date || v.expiry_date) : null;
              const isExpiring = expiry && expiry > today && expiry <= in30;
              const isExpired = expiry && expiry < today;
              return (
                <div key={v.id} className="py-2 border-b last:border-0">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="text-sm font-medium">{v.vaccination_type || v.vaccine_type}</p>
                      {expiry && (
                        <p className={`text-xs ${isExpired ? 'text-red-600' : isExpiring ? 'text-amber-600' : 'text-muted-foreground'}`}>
                          {isExpired ? '⚠️ Expired' : isExpiring ? '⚠️ Expiring soon' : 'Expires'} {expiry.toLocaleDateString()}
                        </p>
                      )}
                      {v.document_url && (
                        <a href={v.document_url} target="_blank" rel="noopener noreferrer"
                          className="text-xs text-blue-600 hover:underline mt-0.5 block">
                          📄 View document
                        </a>
                      )}
                    </div>
                    <Badge className={`text-xs ${
                      (v.verification_status || v.status) === 'verified' ? 'bg-green-100 text-green-700' :
                      (v.verification_status || v.status) === 'rejected' ? 'bg-red-100 text-red-700' :
                      'bg-amber-100 text-amber-700'}`}>{v.verification_status || v.status}</Badge>
                  </div>
                </div>
              );
            })}
          </CardContent>
        </Card>

        {/* Photos */}
        {dog.photo_url && (
          <Card>
            <CardHeader className="pb-2 pt-4 px-4">
              <CardTitle className="text-sm">Photos</CardTitle>
            </CardHeader>
            <CardContent className="px-4 pb-4">
              <div className="grid grid-cols-3 gap-2">
                <div className="rounded-lg overflow-hidden aspect-square bg-muted">
                  <img src={dog.photo_url} alt={dog.name} className="w-full h-full object-cover" />
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </main>
    </div>
  );
};

const DogDetailsEditor = ({ dog, dogId, onSaved }) => {
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({});
  const [saving, setSaving] = useState(false);

  React.useEffect(() => {
    const bp = dog.behavior_profile || {};
    setForm({
      gender: dog.gender || '',
      color: dog.color || '',
      microchip_number: dog.microchip_number || '',
      meal_routine: dog.meal_routine || '',
      allergies: dog.allergies || '',
      medication_requirements: dog.medication_requirements || '',
      behavioral_notes: dog.behavioral_notes || '',
      energy_level: bp.energy_level || 3,
      anxiety_level: bp.anxiety_level || 1,
      play_style: bp.play_style || '',
      known_triggers: bp.known_triggers || '',
    });
  }, [dog]);

  const handleSave = async () => {
    setSaving(true);
    try {
      await api.patch(`/dogs/${dogId}`, {
        gender: form.gender,
        color: form.color,
        microchip_number: form.microchip_number,
        meal_routine: form.meal_routine,
        allergies: form.allergies,
        medication_requirements: form.medication_requirements,
        behavioral_notes: form.behavioral_notes,
      });
      // Save behavior profile separately
      await api.patch(`/dogs/${dogId}/behavior`, {
        energy_level: form.energy_level,
        anxiety_level: form.anxiety_level,
        play_style: form.play_style,
        known_triggers: form.known_triggers,
      }).catch(() => {});
      toast.success('Details updated');
      setEditing(false);
      onSaved();
    } catch { toast.error('Failed to save'); }
    finally { setSaving(false); }
  };

  return (
    <Card>
      <CardHeader className="pb-2 pt-4 px-4">
        <CardTitle className="text-sm flex items-center justify-between">
          Details
          {editing ? (
            <div className="flex gap-2">
              <Button size="sm" variant="outline" className="h-7 text-xs" onClick={() => setEditing(false)}>Cancel</Button>
              <Button size="sm" className="h-7 text-xs" onClick={handleSave} disabled={saving}>
                {saving ? 'Saving...' : 'Save'}
              </Button>
            </div>
          ) : (
            <Button size="sm" variant="outline" className="h-7 text-xs" onClick={() => setEditing(true)}>Edit</Button>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="px-4 pb-4 space-y-3">
        {editing ? (
          <>
            <div className="grid grid-cols-2 gap-2">
              <div><Label className="text-xs">Gender</Label>
                <select className="w-full mt-0.5 border rounded px-2 py-1.5 text-sm bg-background"
                  value={form.gender} onChange={e => setForm(f=>({...f,gender:e.target.value}))}>
                  <option value="">Select...</option>
                  <option value="male">Male</option>
                  <option value="female">Female</option>
                </select>
              </div>
              <div><Label className="text-xs">Color</Label>
                <Input value={form.color} onChange={e => setForm(f=>({...f,color:e.target.value}))} className="mt-0.5 h-8 text-sm" />
              </div>
            </div>
            <div><Label className="text-xs">Microchip Number</Label>
              <Input value={form.microchip_number} onChange={e => setForm(f=>({...f,microchip_number:e.target.value}))} className="mt-0.5 h-8 text-sm" placeholder="Leave blank if unknown" />
            </div>
            <div><Label className="text-xs">Feeding Routine</Label>
              <textarea className="w-full mt-0.5 border rounded px-2 py-1.5 text-sm bg-background resize-none" rows={2}
                value={form.meal_routine} onChange={e => setForm(f=>({...f,meal_routine:e.target.value}))}
                placeholder="e.g. 1 cup morning and evening" />
            </div>
            <div><Label className="text-xs">Allergies</Label>
              <Input value={form.allergies} onChange={e => setForm(f=>({...f,allergies:e.target.value}))} className="mt-0.5 h-8 text-sm" placeholder="Food, environmental, medications..." />
            </div>
            <div><Label className="text-xs">Medication Notes</Label>
              <textarea className="w-full mt-0.5 border rounded px-2 py-1.5 text-sm bg-background resize-none" rows={2}
                value={form.medication_requirements} onChange={e => setForm(f=>({...f,medication_requirements:e.target.value}))}
                placeholder="Any medications or medical needs..." />
            </div>
            <div><Label className="text-xs">Behavioral Notes</Label>
              <textarea className="w-full mt-0.5 border rounded px-2 py-1.5 text-sm bg-background resize-none" rows={2}
                value={form.behavioral_notes} onChange={e => setForm(f=>({...f,behavioral_notes:e.target.value}))}
                placeholder="Temperament, triggers, things we should know..." />
            </div>
            <div>
              <Label className="text-xs">Energy Level: {'⚡'.repeat(form.energy_level)} ({form.energy_level}/5)</Label>
              <input type="range" min="1" max="5" value={form.energy_level}
                onChange={e => setForm(f=>({...f,energy_level:parseInt(e.target.value)}))} className="w-full mt-1" />
            </div>
            <div>
              <Label className="text-xs">Anxiety Level: {'😰'.repeat(form.anxiety_level)} ({form.anxiety_level}/5)</Label>
              <input type="range" min="1" max="5" value={form.anxiety_level}
                onChange={e => setForm(f=>({...f,anxiety_level:parseInt(e.target.value)}))} className="w-full mt-1" />
            </div>
            <div><Label className="text-xs">Play Style</Label>
              <Input value={form.play_style} onChange={e => setForm(f=>({...f,play_style:e.target.value}))} className="mt-0.5 h-8 text-sm" placeholder="e.g. Fetch, wrestling, independent..." />
            </div>
            <div><Label className="text-xs">Known Triggers</Label>
              <Input value={form.known_triggers} onChange={e => setForm(f=>({...f,known_triggers:e.target.value}))} className="mt-0.5 h-8 text-sm" placeholder="e.g. Bikes, skateboards, intact dogs..." />
            </div>
          </>
        ) : (
          <div className="space-y-2 text-sm">
            {form.gender && <div className="flex justify-between"><span className="text-muted-foreground">Gender</span><span className="capitalize">{form.gender}</span></div>}
            {form.color && <div className="flex justify-between"><span className="text-muted-foreground">Color</span><span>{form.color}</span></div>}
            {form.microchip_number && <div className="flex justify-between"><span className="text-muted-foreground">Microchip</span><span>{form.microchip_number}</span></div>}
            {form.meal_routine && <div><p className="text-muted-foreground text-xs">Feeding Routine</p><p className="mt-0.5">{form.meal_routine}</p></div>}
            {form.allergies && <div className="p-2 bg-amber-50 rounded border border-amber-100"><p className="text-xs font-medium text-amber-800">⚠️ Allergies</p><p className="text-xs text-amber-700 mt-0.5">{form.allergies}</p></div>}
            {form.medication_requirements && <div><p className="text-muted-foreground text-xs">Medication Notes</p><p className="mt-0.5">{form.medication_requirements}</p></div>}
            {form.behavioral_notes && <div><p className="text-muted-foreground text-xs">Behavioral Notes</p><p className="mt-0.5">{form.behavioral_notes}</p></div>}
            {form.energy_level && <div className="flex justify-between"><span className="text-muted-foreground">Energy</span><span>{'⚡'.repeat(form.energy_level)} {form.energy_level}/5</span></div>}
            {form.anxiety_level && <div className="flex justify-between"><span className="text-muted-foreground">Anxiety</span><span>{'😰'.repeat(form.anxiety_level)} {form.anxiety_level}/5</span></div>}
            {form.play_style && <div><p className="text-muted-foreground text-xs">Play Style</p><p className="mt-0.5">{form.play_style}</p></div>}
            {form.known_triggers && <div><p className="text-muted-foreground text-xs">Known Triggers</p><p className="mt-0.5">{form.known_triggers}</p></div>}
            {!form.gender && !form.color && !form.microchip_number && !form.meal_routine && !form.allergies && !form.medication_requirements && !form.behavioral_notes && (
              <p className="text-muted-foreground text-xs">Click Edit to add details about your dog</p>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default CustomerDogPage;
