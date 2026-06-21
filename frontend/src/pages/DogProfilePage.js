import React, { useEffect, useState, useCallback, useRef } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
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
  AlertCircleIcon, DogIcon, ShieldIcon, UtensilsIcon,
  PillIcon, ClipboardListIcon, PlusIcon, SyringeIcon,
  FileTextIcon, UploadIcon, TrashIcon,
} from 'lucide-react';
import { toast } from 'sonner';

const DogProfilePage = () => {
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const { dogId } = useParams();
  const [dog, setDog] = useState(null);
  const [notes, setNotes] = useState([]);
  const [vaccinations, setVaccinations] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchDog = useCallback(async () => {
    try {
      const [dogRes, notesRes, vaxRes, medsRes] = await Promise.all([
        api.get(`/dogs/${dogId}`),
        api.get(`/dogs/${dogId}/notes`).catch(() => ({ data: [] })),
        api.get(`/vaccinations/dog/${dogId}`).catch(() => ({ data: [] })),
        api.get(`/care/medications/dog/${dogId}`).catch(() => ({ data: [] })),
      ]);
      setDog({ ...dogRes.data, medications: medsRes.data });
      setNotes(notesRes.data);
      setVaccinations(vaxRes.data);
    } catch {
      toast.error('Failed to load dog profile');
    } finally {
      setLoading(false);
    }
  }, [dogId]);

  useEffect(() => {
    if (!user) { navigate('/auth'); return; }
    fetchDog();
  }, [user, navigate, fetchDog]);

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-primary"></div>
    </div>
  );

  if (!dog) return <div className="min-h-screen flex items-center justify-center"><p className="text-muted-foreground">Dog not found</p></div>;

  const hasWarnings = dog.escape_risk || dog.medical_alert ||
    dog.behavior_profile?.bite_history || dog.behavior_profile?.active_safety_alert;

  return (
    <div className="min-h-screen bg-[#F9F7F2]">
      <header className="bg-white border-b shadow-sm sticky top-0 z-10">
        <div className="max-w-3xl mx-auto px-4 py-3 flex items-center gap-3">
          <div className="flex items-center gap-2">
            <h1 className="text-lg font-serif font-bold text-primary">{dog.name}</h1>
            {hasWarnings && <AlertCircleIcon size={16} className="text-red-500" />}
          </div>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 py-6 space-y-4">
        {hasWarnings && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 space-y-1">
            <p className="text-sm font-semibold text-red-800 flex items-center gap-2"><AlertCircleIcon size={16} /> Safety Flags</p>
            {dog.escape_risk && <p className="text-xs text-red-700">⚠️ Escape risk</p>}
            {dog.medical_alert && <p className="text-xs text-red-700">🏥 Medical alert</p>}
            {dog.behavior_profile?.bite_history && <p className="text-xs text-red-700">🦷 Bite history</p>}
            {dog.behavior_profile?.muzzle_required && <p className="text-xs text-red-700">😷 Muzzle required</p>}
            {dog.behavior_profile?.active_safety_alert && <p className="text-xs text-red-700 font-medium">🚨 {dog.behavior_profile.safety_alert_detail || 'Active safety alert'}</p>}
          </div>
        )}

        <Card>
          <CardContent className="py-4 px-4">
            <div className="flex items-start gap-4">
              <div className="bg-primary/10 p-3 rounded-full"><DogIcon size={24} className="text-primary" /></div>
              <div className="flex-1 grid grid-cols-2 gap-x-6 gap-y-1">
                {dog.breed && <InfoRow label="Breed" value={dog.breed} />}
                {dog.age && <InfoRow label="Age" value={`${dog.age} yr${dog.age !== 1 ? 's' : ''}`} />}
                {dog.weight && <InfoRow label="Weight" value={`${dog.weight} lbs`} />}
                {dog.gender && <InfoRow label="Gender" value={dog.gender} />}
                {dog.color && <InfoRow label="Color" value={dog.color} />}
                {dog.spay_neuter_status && <InfoRow label="Spay/Neuter" value={dog.spay_neuter_status} />}
              </div>
            </div>
            <div className="flex gap-2 mt-4 flex-wrap">
              <Badge className={dog.boarding_eligible ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}>
                {dog.boarding_eligible ? '✓ Boarding' : '✗ Boarding'}
              </Badge>
              <Badge className={dog.daycare_eligible ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}>
                {dog.daycare_eligible ? '✓ Daycare' : '✗ Daycare'}
              </Badge>
              <Badge variant="outline" className="text-xs">M&G: {dog.meet_and_greet_status}</Badge>
            </div>
          </CardContent>
        </Card>

        <Tabs defaultValue="care">
          <TabsList className="w-full">
            <TabsTrigger value="care" className="flex-1">Care</TabsTrigger>
            <TabsTrigger value="vaccinations" className="flex-1">
              Vaccines {vaccinations.some(v => v.verification_status !== 'verified') ? '⚠️' : '✓'}
            </TabsTrigger>
            <TabsTrigger value="behavior" className="flex-1">Behavior</TabsTrigger>
            <TabsTrigger value="notes" className="flex-1">
              Notes {notes.some(n => n.is_alert) ? '🚨' : ''}
            </TabsTrigger>
          </TabsList>

          <TabsContent value="care" className="space-y-4 mt-4">
            <Card>
              <CardHeader className="pb-2 pt-4"><CardTitle className="text-sm flex items-center gap-2"><UtensilsIcon size={14} /> Feeding</CardTitle></CardHeader>
              <CardContent>
                {dog.meal_routine ? <p className="text-sm">{dog.meal_routine}</p> : <p className="text-sm text-muted-foreground">No feeding routine on file</p>}
                {dog.allergies && <div className="mt-3 p-2 bg-amber-50 rounded border border-amber-100"><p className="text-xs font-medium text-amber-800">Allergies:</p><p className="text-xs text-amber-700 mt-0.5">{dog.allergies}</p></div>}
              </CardContent>
            </Card>
            {dog.medications?.length > 0 && (
              <Card>
                <CardHeader className="pb-2 pt-4"><CardTitle className="text-sm flex items-center gap-2"><PillIcon size={14} /> Medications</CardTitle></CardHeader>
                <CardContent className="space-y-2">
                  {dog.medications.map(med => (
                    <div key={med.id} className="p-3 bg-muted/30 rounded-lg border">
                      <p className="font-medium text-sm">{med.name}</p>
                      <p className="text-xs text-muted-foreground">{med.dose} · {med.frequency}</p>
                      {med.administration_instructions && <p className="text-xs text-muted-foreground mt-1">{med.administration_instructions}</p>}
                    </div>
                  ))}
                </CardContent>
              </Card>
            )}
          </TabsContent>

          <TabsContent value="vaccinations" className="mt-4">
            <VaccinationsTab dogId={dogId} vaccinations={vaccinations} onRefresh={fetchDog} isStaff={user?.role !== 'customer'} />
          </TabsContent>

          <TabsContent value="behavior" className="space-y-4 mt-4">
            <BehaviorTab dog={dog} dogId={dogId} onRefresh={fetchDog} isStaff={user?.role !== 'customer'} />
          </TabsContent>

          <TabsContent value="notes" className="mt-4">
            <DogNotesTab dogId={dogId} notes={notes} onRefresh={fetchDog} />
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
};

const REQUIRED_VAXES = ['Rabies', 'Distemper', 'Bordetella'];

const getRequiredVaxStatus = (vaccinations) => {
  const today = new Date();
  return REQUIRED_VAXES.map(vax => {
    const records = vaccinations.filter(v => v.vaccination_type === vax);
    const valid = records.find(v => {
      if (v.verification_status === 'rejected') return false;
      if (!v.expiration_date) return v.verification_status === 'verified';
      return new Date(v.expiration_date) > today && v.verification_status === 'verified';
    });
    return { vax, status: valid ? 'ok' : records.length > 0 ? 'pending' : 'missing' };
  });
};

const getVaxStatus = (v) => {
  if (v.verification_status === 'rejected') return 'rejected';
  if (!v.expiration_date) return v.verification_status;
  const today = new Date();
  const expiry = new Date(v.expiration_date);
  const daysUntilExpiry = Math.ceil((expiry - today) / (1000*60*60*24));
  if (daysUntilExpiry < 0) return 'expired';
  if (daysUntilExpiry <= 30) return 'expiring_soon';
  return v.verification_status;
};

const VAX_STATUS_STYLES = {
  verified: 'bg-green-100 text-green-700',
  pending: 'bg-amber-100 text-amber-700',
  rejected: 'bg-red-100 text-red-700',
  expired: 'bg-red-100 text-red-700',
  expiring_soon: 'bg-orange-100 text-orange-700',
};

const VAX_STATUS_LABELS = {
  verified: 'Verified',
  pending: 'Pending Review',
  rejected: 'Rejected',
  expired: 'Expired',
  expiring_soon: 'Expiring Soon',
};

// Common vax intervals in days
const VAX_INTERVALS = {
  'Rabies': 365,
  'Distemper': 365,
  'Bordetella': 180,
  'Leptospirosis': 365,
  'Lyme': 365,
  'Influenza': 365,
};

const VaccinationsTab = ({ dogId, vaccinations, onRefresh, isStaff }) => {
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState({ vaccination_type: '', administration_date: '', expiration_date: '', provider: '', auto_verify: false });
  const [uploading, setUploading] = useState(false);
  const [docKey, setDocKey] = useState('');
  const fileRef = useRef();

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await api.post('/uploads/vaccination', formData, { headers: { 'Content-Type': 'multipart/form-data' } });
      setDocKey(res.data.key);
      toast.success('Document uploaded');
    } catch { toast.error('Upload failed'); }
    finally { setUploading(false); }
  };

  const handleAdd = async () => {
    if (!form.vaccination_type.trim()) { toast.error('Vaccination type required'); return; }
    try {
      await api.post(`/vaccinations/dog/${dogId}`, { ...form, document_path: docKey || undefined });
      toast.success('Vaccination record added');
      setShowAdd(false); setDocKey('');
      setForm({ vaccination_type: '', administration_date: '', expiration_date: '', provider: '', auto_verify: false });
      onRefresh();
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed'); }
  };

  const handleVerify = async (id) => {
    try { await api.post(`/vaccinations/${id}/verify`); toast.success('Verified'); onRefresh(); }
    catch { toast.error('Failed to verify'); }
  };

  const handleReject = async (id) => {
    const reason = window.prompt('Rejection reason:');
    if (!reason) return;
    try { await api.post(`/vaccinations/${id}/reject`, { reason }); toast.success('Rejected'); onRefresh(); }
    catch { toast.error('Failed to reject'); }
  };

  const requiredStatus = getRequiredVaxStatus(vaccinations);
  const [editingId, setEditingId] = useState(null);
  const [editForm, setEditForm] = useState({});

  const handleEdit = (v) => {
    setEditingId(v.id);
    setEditForm({
      vaccination_type: v.vaccination_type,
      administration_date: v.administration_date ? v.administration_date.split('T')[0] : '',
      expiration_date: v.expiration_date ? v.expiration_date.split('T')[0] : '',
      provider: v.provider || '',
    });
  };

  const handleSaveEdit = async () => {
    try {
      await api.patch(`/vaccinations/${editingId}`, editForm);
      toast.success('Updated');
      setEditingId(null);
      onRefresh();
    } catch { toast.error('Failed to update'); }
  };

  return (
    <div className="space-y-3">
      {/* Required vaccines status */}
      <div className="flex gap-2 flex-wrap">
        {requiredStatus.map(r => (
          <span key={r.vax} className={`text-xs px-2 py-1 rounded-full font-medium ${
            r.status === 'ok' ? 'bg-green-100 text-green-700' :
            r.status === 'pending' ? 'bg-amber-100 text-amber-700' :
            'bg-red-100 text-red-700'
          }`}>
            {r.vax}: {r.status === 'ok' ? '✓' : r.status === 'pending' ? 'Pending' : 'Missing'}
          </span>
        ))}
      </div>

      {isStaff && (
        <div className="flex justify-end">
          <Button size="sm" onClick={() => setShowAdd(!showAdd)}>
            <PlusIcon size={14} className="mr-1" /> Add Record
          </Button>
        </div>
      )}

      {showAdd && (
        <Card className="border-primary/30">
          <CardContent className="pt-4 space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div><Label>Type *</Label>
                <select className="w-full mt-1 border rounded-md px-3 py-2 text-sm bg-background"
                  value={form.vaccination_type} onChange={e => setForm(f=>({...f,vaccination_type:e.target.value}))}>
                  <option value="">Select...</option>
                  <option value="Rabies">Rabies</option>
                  <option value="Distemper">Distemper (DHPP)</option>
                  <option value="Bordetella">Bordetella</option>
                  <option value="Leptospirosis">Leptospirosis</option>
                  <option value="Lyme">Lyme</option>
                  <option value="Influenza">Influenza</option>
                  <option value="Other">Other</option>
                </select>
              </div>
              <div><Label>Provider</Label><Input value={form.provider} onChange={e => setForm(f=>({...f,provider:e.target.value}))} className="mt-1" /></div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div><Label>Admin Date</Label><Input type="date" value={form.administration_date}
                onChange={e => {
                  const val = e.target.value;
                  const interval = VAX_INTERVALS[form.vaccination_type];
                  let expiry = form.expiration_date;
                  if (val && interval && !form.expiration_date) {
                    const d = new Date(val);
                    d.setDate(d.getDate() + interval);
                    expiry = d.toISOString().split('T')[0];
                  }
                  setForm(f=>({...f, administration_date:val, expiration_date: expiry}));
                }} className="mt-1" /></div>
              <div><Label>Expiry Date</Label><Input type="date" value={form.expiration_date} onChange={e => setForm(f=>({...f,expiration_date:e.target.value}))} className="mt-1" /></div>
            </div>
            <div>
              <Label>Document (PDF or image)</Label>
              <div className="mt-1 flex items-center gap-2">
                <Button type="button" variant="outline" size="sm" onClick={() => fileRef.current?.click()} disabled={uploading}>
                  <UploadIcon size={14} className="mr-1" /> {uploading ? 'Uploading...' : docKey ? 'Replace' : 'Upload'}
                </Button>
                {docKey && <span className="text-xs text-green-600">✓ Document uploaded</span>}
                <input ref={fileRef} type="file" accept=".pdf,image/*" className="hidden" onChange={handleFileUpload} />
              </div>
            </div>
            {isStaff && (
              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <input type="checkbox" checked={form.auto_verify} onChange={e => setForm(f=>({...f,auto_verify:e.target.checked}))} className="w-4 h-4" />
                Mark as verified (staff submission)
              </label>
            )}
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={() => setShowAdd(false)}>Cancel</Button>
              <Button size="sm" onClick={handleAdd}>Add Record</Button>
            </div>
          </CardContent>
        </Card>
      )}

      {vaccinations.length === 0 ? (
        <Card><CardContent className="py-8 text-center text-muted-foreground text-sm">No vaccination records on file</CardContent></Card>
      ) : vaccinations.map(v => (
        <Card key={v.id}>
          <CardContent className="py-3 px-4">
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-start gap-2">
                <SyringeIcon size={14} className="mt-0.5 text-muted-foreground" />
                <div>
                  <div className="flex items-center gap-2">
                    <p className="font-medium text-sm">{v.vaccination_type}</p>
                    <span className={`text-xs px-1.5 py-0.5 rounded-full ${VAX_STATUS_STYLES[getVaxStatus(v)] || 'bg-gray-100 text-gray-600'}`}>
                      {VAX_STATUS_LABELS[getVaxStatus(v)] || v.verification_status}
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {v.administration_date && `Given: ${new Date(v.administration_date).toLocaleDateString()} · `}
                    {v.expiration_date ? (
                      (() => {
                        const days = Math.ceil((new Date(v.expiration_date) - new Date()) / (1000*60*60*24));
                        if (days < 0) return <span className="text-red-600">Expired {Math.abs(days)} days ago</span>;
                        if (days <= 30) return <span className="text-orange-600">Expires in {days} days</span>;
                        return `Expires: ${new Date(v.expiration_date).toLocaleDateString()}`;
                      })()
                    ) : 'No expiry'}
                    {v.provider && ` · ${v.provider}`}
                  </p>
                  {v.document_url && (
                    <a href={v.document_url} target="_blank" rel="noopener noreferrer"
                      className="text-xs text-blue-600 flex items-center gap-1 mt-1 hover:underline"
                      onClick={e => e.stopPropagation()}>
                      <FileTextIcon size={11} /> View document
                    </a>
                  )}
                </div>
              </div>
              <div className="flex flex-col items-end gap-1">
                <Badge className={
                  v.verification_status === 'verified' ? 'bg-green-100 text-green-700' :
                  v.verification_status === 'rejected' ? 'bg-red-100 text-red-700' :
                  'bg-amber-100 text-amber-700'
                }>{v.verification_status}</Badge>
                {isStaff && v.verification_status === 'pending' && (
                  <div className="flex gap-1">
                    <Button size="sm" variant="outline" className="h-6 px-2 text-xs text-green-600" onClick={() => handleVerify(v.id)}>Verify</Button>
                    <Button size="sm" variant="outline" className="h-6 px-2 text-xs text-red-600" onClick={() => handleReject(v.id)}>Reject</Button>
                  </div>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
};

const DogNotesTab = ({ dogId, notes, onRefresh }) => {
  const { user } = useAuthStore();
  const [showAdd, setShowAdd] = useState(false);
  const [noteText, setNoteText] = useState('');
  const [isAlert, setIsAlert] = useState(false);
  const [imageKeys, setImageKeys] = useState([]);
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef();

  const [imagePreviews, setImagePreviews] = useState([]);

  const handleImageUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    // Show local preview immediately
    const localUrl = URL.createObjectURL(file);
    setImagePreviews(prev => [...prev, localUrl]);
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await api.post('/uploads/dog-photo', formData, { headers: { 'Content-Type': 'multipart/form-data' } });
      setImageKeys(prev => [...prev, res.data.key]);
      toast.success('Image uploaded');
    } catch {
      toast.error('Upload failed');
      setImagePreviews(prev => prev.slice(0, -1));
    }
    finally { setUploading(false); }
  };

  const handleAdd = async () => {
    if (!noteText.trim()) { toast.error('Note text required'); return; }
    try {
      await api.post(`/dogs/${dogId}/notes`, { note_text: noteText, is_alert: isAlert, image_keys: imageKeys });
      toast.success('Note added');
      setNoteText(''); setIsAlert(false); setImageKeys([]); setImagePreviews([]); setShowAdd(false);
      onRefresh();
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed'); }
  };

  const handleDelete = async (noteId) => {
    if (!window.confirm('Delete this note?')) return;
    try { await api.delete(`/dogs/${dogId}/notes/${noteId}`); onRefresh(); }
    catch { toast.error('Failed to delete'); }
  };

  const alertNotes = notes.filter(n => n.is_alert);
  const regularNotes = notes.filter(n => !n.is_alert);

  return (
    <div className="space-y-3">
      <div className="flex justify-end">
        <Button size="sm" onClick={() => setShowAdd(!showAdd)}>
          <PlusIcon size={14} className="mr-1" /> Add Note
        </Button>
      </div>

      {showAdd && (
        <Card className="border-primary/30">
          <CardContent className="pt-4 space-y-3">
            <div>
              <Label>Note ({noteText.length}/500)</Label>
              <Textarea value={noteText} onChange={e => setNoteText(e.target.value.slice(0,500))}
                className="mt-1" rows={3} placeholder="Describe the observation or incident..." />
            </div>
            <div className="flex items-center justify-between">
              <label className={`flex items-center gap-2 text-sm cursor-pointer p-2 rounded-lg border transition-colors ${isAlert ? 'bg-red-50 border-red-200 text-red-700' : 'border-border'}`}>
                <input type="checkbox" checked={isAlert} onChange={e => setIsAlert(e.target.checked)} className="w-4 h-4" />
                🚨 Mark as aggressive behavior alert
              </label>
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <Button type="button" variant="outline" size="sm" onClick={() => fileRef.current?.click()} disabled={uploading}>
                    <UploadIcon size={14} className="mr-1" /> {uploading ? 'Uploading...' : 'Add Photo'}
                  </Button>
                  {imageKeys.length > 0 && <span className="text-xs text-green-600">✓ {imageKeys.length} photo{imageKeys.length !== 1 ? 's' : ''} ready</span>}
                  <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={handleImageUpload} />
                </div>
                {imagePreviews.length > 0 && (
                  <div className="flex gap-2 flex-wrap">
                    {imagePreviews.map((url, i) => (
                      <img key={i} src={url} alt="preview" className="h-16 w-16 object-cover rounded border" />
                    ))}
                  </div>
                )}
              </div>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={() => setShowAdd(false)}>Cancel</Button>
              <Button size="sm" onClick={handleAdd}>Save Note</Button>
            </div>
          </CardContent>
        </Card>
      )}

      {alertNotes.length > 0 && (
        <div>
          <p className="text-xs font-medium text-red-600 mb-2">🚨 Alert Notes</p>
          {alertNotes.map(note => <NoteCard key={note.id} note={note} onDelete={handleDelete} canDelete={user?.role !== 'customer'} />)}
        </div>
      )}

      {regularNotes.length > 0 && (
        <div>
          {alertNotes.length > 0 && <p className="text-xs font-medium text-muted-foreground mb-2 mt-4">Regular Notes</p>}
          {regularNotes.map(note => <NoteCard key={note.id} note={note} onDelete={handleDelete} canDelete={user?.role !== 'customer'} />)}
        </div>
      )}

      {notes.length === 0 && !showAdd && (
        <Card><CardContent className="py-8 text-center text-muted-foreground text-sm">No notes on file</CardContent></Card>
      )}
    </div>
  );
};

const NoteCard = ({ note, onDelete, canDelete }) => (
  <Card className={`mb-2 ${note.is_alert ? 'border-red-200 bg-red-50/30' : ''}`}>
    <CardContent className="py-3 px-4">
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1">
          {note.is_alert && <p className="text-xs font-medium text-red-600 mb-1">🚨 Alert</p>}
          <p className="text-sm">{note.note_text}</p>
          {note.image_urls?.filter(Boolean).length > 0 && (
            <div className="flex gap-2 mt-2 flex-wrap">
              {note.image_urls.filter(Boolean).map((url, i) => (
                <button key={i} type="button"
                  onClick={e => { e.stopPropagation(); window.open(url, '_blank', 'noopener,noreferrer'); }}>
                  <img src={url} alt="Note attachment"
                    className="h-16 w-16 object-cover rounded border hover:opacity-80 transition-opacity"
                    onError={e => { e.target.style.display='none'; }} />
                </button>
              ))}
            </div>
          )}
          <p className="text-xs text-muted-foreground mt-1">{new Date(note.created_at).toLocaleString()}</p>
        </div>
        {canDelete && (
          <Button variant="ghost" size="sm" className="text-red-400 hover:text-red-600 h-7 px-1 shrink-0" onClick={() => onDelete(note.id)}>
            <TrashIcon size={14} />
          </Button>
        )}
      </div>
    </CardContent>
  </Card>
);

const BehaviorTab = ({ dog, dogId, onRefresh, isStaff }) => {
  const [editing, setEditing] = useState(false);
  const bp = dog.behavior_profile || {};
  const [form, setForm] = useState({
    bite_history: bp.bite_history || false,
    food_guarding: bp.food_guarding || false,
    toy_guarding: bp.toy_guarding || false,
    barrier_reactivity: bp.barrier_reactivity || false,
    muzzle_required: bp.muzzle_required || false,
    active_safety_alert: bp.active_safety_alert || false,
    safety_alert_detail: bp.safety_alert_detail || '',
    is_humper: bp.is_humper || false,
    is_wrestler: bp.is_wrestler || false,
    energy_level: bp.energy_level || 3,
    anxiety_level: bp.anxiety_level || 1,
    play_style: bp.play_style || '',
    handling_restrictions: bp.handling_restrictions || '',
    known_triggers: bp.known_triggers || '',
    dog_compatibility: bp.dog_compatibility || '',
    approved_playgroups: bp.approved_playgroups || '',
  });
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    try {
      await api.patch(`/dogs/${dogId}/behavior`, form);
      toast.success('Behavior profile updated');
      setEditing(false);
      onRefresh();
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed'); }
    finally { setSaving(false); }
  };

  const flags = [
    { key: 'bite_history', label: '🦷 Bite history' },
    { key: 'food_guarding', label: '🍖 Food guarding' },
    { key: 'toy_guarding', label: '🎾 Toy guarding' },
    { key: 'barrier_reactivity', label: '🚧 Barrier reactivity' },
    { key: 'muzzle_required', label: '😷 Muzzle required' },
    { key: 'is_humper', label: '🐾 Humper' },
    { key: 'is_wrestler', label: '💪 Wrestler' },
    { key: 'active_safety_alert', label: '🚨 Active safety alert' },
  ];

  const activeFlags = flags.filter(f => bp[f.key] || (f.key === 'escape_risk' && dog.escape_risk));

  return (
    <Card>
      <CardHeader className="pb-2 pt-4">
        <CardTitle className="text-sm flex items-center justify-between">
          <span className="flex items-center gap-2"><ShieldIcon size={14} /> Behavior Profile</span>
          {isStaff && (
            <Button size="sm" variant="ghost" className="h-7 text-xs" onClick={() => setEditing(!editing)}>
              {editing ? 'Cancel' : '✏️ Edit'}
            </Button>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {!editing ? (
          <div className="space-y-3">
            {activeFlags.length === 0 && !dog.escape_risk && !dog.medical_alert ? (
              <p className="text-sm text-green-600">✓ No behavioral concerns on file</p>
            ) : (
              <div className="grid grid-cols-2 gap-2">
                {activeFlags.map(f => (
                  <div key={f.key} className="p-2 rounded border bg-red-50 border-red-200 text-xs font-medium text-red-700">{f.label}</div>
                ))}
                {dog.escape_risk && <div className="p-2 rounded border bg-red-50 border-red-200 text-xs font-medium text-red-700">🏃 Escape risk</div>}
                {dog.medical_alert && <div className="p-2 rounded border bg-red-50 border-red-200 text-xs font-medium text-red-700">🏥 Medical alert</div>}
              </div>
            )}
            {bp.active_safety_alert && bp.safety_alert_detail && (
              <p className="text-xs text-red-700 bg-red-50 border border-red-200 rounded p-2">🚨 {bp.safety_alert_detail}</p>
            )}
            <div className="grid grid-cols-2 gap-3 pt-2 border-t">
              {bp.energy_level && <div><p className="text-xs text-muted-foreground">Energy level</p><p className="text-sm">{'⚡'.repeat(bp.energy_level)} ({bp.energy_level}/5)</p></div>}
              {bp.anxiety_level && <div><p className="text-xs text-muted-foreground">Anxiety level</p><p className="text-sm">{'😰'.repeat(bp.anxiety_level)} ({bp.anxiety_level}/5)</p></div>}
              {bp.play_style && <div><p className="text-xs text-muted-foreground">Play style</p><p className="text-sm capitalize">{bp.play_style}</p></div>}
              {bp.dog_compatibility && <div><p className="text-xs text-muted-foreground">Dog compatibility</p><p className="text-sm">{bp.dog_compatibility}</p></div>}
            </div>
            {bp.handling_restrictions && <div className="pt-2 border-t"><p className="text-xs text-muted-foreground">Handling restrictions</p><p className="text-sm mt-1">{bp.handling_restrictions}</p></div>}
            {bp.known_triggers && <div><p className="text-xs text-muted-foreground">Known triggers</p><p className="text-sm mt-1">{bp.known_triggers}</p></div>}
            {bp.approved_playgroups && <div><p className="text-xs text-muted-foreground">Approved playgroups</p><p className="text-sm mt-1">{bp.approved_playgroups}</p></div>}
          </div>
        ) : (
          <div className="space-y-4">
            <div>
              <p className="text-xs font-medium text-muted-foreground mb-2">Behavior Flags</p>
              <div className="grid grid-cols-2 gap-2">
                {flags.map(f => (
                  <label key={f.key} className={`flex items-center gap-2 p-2 rounded-lg border cursor-pointer text-sm transition-colors ${
                    form[f.key] ? 'bg-red-50 border-red-200 text-red-700' : 'border-border hover:bg-muted'
                  }`}>
                    <input type="checkbox" checked={!!form[f.key]} onChange={e => setForm(fv=>({...fv,[f.key]:e.target.checked}))} className="w-4 h-4" />
                    {f.label}
                  </label>
                ))}
              </div>
            </div>
            {form.active_safety_alert && (
              <div><Label>Safety Alert Detail</Label>
                <Input value={form.safety_alert_detail} onChange={e => setForm(f=>({...f,safety_alert_detail:e.target.value}))} className="mt-1" placeholder="Describe the safety concern..." /></div>
            )}
            <div className="grid grid-cols-2 gap-3">
              <div><Label>Energy Level (1-5)</Label>
                <input type="range" min="1" max="5" value={form.energy_level}
                  onChange={e => setForm(f=>({...f,energy_level:parseInt(e.target.value)}))} className="w-full mt-1" />
                <p className="text-xs text-muted-foreground text-center">{'⚡'.repeat(form.energy_level)} {form.energy_level}/5</p>
              </div>
              <div><Label>Anxiety Level (1-5)</Label>
                <input type="range" min="1" max="5" value={form.anxiety_level}
                  onChange={e => setForm(f=>({...f,anxiety_level:parseInt(e.target.value)}))} className="w-full mt-1" />
                <p className="text-xs text-muted-foreground text-center">{'😰'.repeat(form.anxiety_level)} {form.anxiety_level}/5</p>
              </div>
            </div>
            <div><Label>Play Style</Label>
              <select className="w-full mt-1 border rounded-md px-3 py-2 text-sm bg-background"
                value={form.play_style} onChange={e => setForm(f=>({...f,play_style:e.target.value}))}>
                <option value="">Not assessed</option>
                <option value="gentle">Gentle</option>
                <option value="moderate">Moderate</option>
                <option value="rough">Rough</option>
                <option value="varies">Varies</option>
              </select>
            </div>
            <div><Label>Dog Compatibility Notes</Label>
              <Textarea value={form.dog_compatibility} onChange={e => setForm(f=>({...f,dog_compatibility:e.target.value}))} className="mt-1" rows={2} placeholder="How does this dog do with others?" /></div>
            <div><Label>Handling Restrictions</Label>
              <Textarea value={form.handling_restrictions} onChange={e => setForm(f=>({...f,handling_restrictions:e.target.value}))} className="mt-1" rows={2} /></div>
            <div><Label>Known Triggers</Label>
              <Input value={form.known_triggers} onChange={e => setForm(f=>({...f,known_triggers:e.target.value}))} className="mt-1" placeholder="e.g. skateboards, umbrellas" /></div>
            <div><Label>Approved Playgroup Notes</Label>
              <Input value={form.approved_playgroups} onChange={e => setForm(f=>({...f,approved_playgroups:e.target.value}))} className="mt-1" placeholder="e.g. plays well with Group A regulars" /></div>
            <div className="flex gap-3 pt-2">
              <Button variant="outline" className="flex-1" onClick={() => setEditing(false)}>Cancel</Button>
              <Button className="flex-1" onClick={handleSave} disabled={saving}>{saving ? 'Saving...' : 'Save'}</Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

const InfoRow = ({ label, value }) => !value ? null : (
  <div><p className="text-xs text-muted-foreground">{label}</p><p className="text-sm font-medium capitalize">{value}</p></div>
);

const FlagRow = ({ label, value }) => (
  <div className={`p-2 rounded border text-xs font-medium flex items-center gap-1.5 ${value ? 'bg-red-50 border-red-200 text-red-700' : 'bg-muted/30 border-border text-muted-foreground'}`}>
    <span>{value ? '⚠️' : '✓'}</span> {label}
  </div>
);

export default DogProfilePage;
