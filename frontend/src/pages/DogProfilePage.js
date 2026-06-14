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
            <Card>
              <CardHeader className="pb-2 pt-4"><CardTitle className="text-sm flex items-center gap-2"><ShieldIcon size={14} /> Behavior Profile</CardTitle></CardHeader>
              <CardContent>
                {dog.behavior_profile ? (
                  <div className="space-y-2">
                    {[
                      { label: '🦷 Bite history', value: dog.behavior_profile.bite_history },
                      { label: '🍖 Food guarding', value: dog.behavior_profile.food_guarding },
                      { label: '🎾 Toy guarding', value: dog.behavior_profile.toy_guarding },
                      { label: '🚧 Barrier reactivity', value: dog.behavior_profile.barrier_reactivity },
                      { label: '😷 Muzzle required', value: dog.behavior_profile.muzzle_required },
                      { label: '🏃 Escape risk', value: dog.escape_risk },
                      { label: '🏥 Medical alert', value: dog.medical_alert },
                    ].filter(f => f.value).length === 0 ? (
                      <p className="text-sm text-green-600">✓ No behavioral concerns on file</p>
                    ) : (
                      <div className="grid grid-cols-2 gap-2">
                        {[
                          { label: '🦷 Bite history', value: dog.behavior_profile.bite_history },
                          { label: '🍖 Food guarding', value: dog.behavior_profile.food_guarding },
                          { label: '🎾 Toy guarding', value: dog.behavior_profile.toy_guarding },
                          { label: '🚧 Barrier reactivity', value: dog.behavior_profile.barrier_reactivity },
                          { label: '😷 Muzzle required', value: dog.behavior_profile.muzzle_required },
                          { label: '🏃 Escape risk', value: dog.escape_risk },
                          { label: '🏥 Medical alert', value: dog.medical_alert },
                        ].filter(f => f.value).map(f => (
                          <div key={f.label} className="p-2 rounded border bg-red-50 border-red-200 text-xs font-medium text-red-700">
                            {f.label}
                          </div>
                        ))}
                      </div>
                    )}
                    {dog.behavior_profile.handling_restrictions && (
                      <div className="pt-2 border-t">
                        <p className="text-xs font-medium text-muted-foreground">Handling restrictions:</p>
                        <p className="text-sm mt-1">{dog.behavior_profile.handling_restrictions}</p>
                      </div>
                    )}
                    {dog.behavioral_notes && (
                      <div className="pt-2 border-t">
                        <p className="text-xs font-medium text-muted-foreground">Notes:</p>
                        <p className="text-sm mt-1">{dog.behavioral_notes}</p>
                      </div>
                    )}
                  </div>
                ) : <p className="text-sm text-muted-foreground">No behavior profile on file</p>}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="notes" className="mt-4">
            <DogNotesTab dogId={dogId} notes={notes} onRefresh={fetchDog} />
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
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

  return (
    <div className="space-y-3">
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
              <div><Label>Admin Date</Label><Input type="date" value={form.administration_date} onChange={e => setForm(f=>({...f,administration_date:e.target.value}))} className="mt-1" /></div>
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
                  <p className="font-medium text-sm">{v.vaccination_type}</p>
                  <p className="text-xs text-muted-foreground">
                    {v.expiration_date ? `Expires: ${new Date(v.expiration_date).toLocaleDateString()}` : 'No expiry'}
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

const InfoRow = ({ label, value }) => !value ? null : (
  <div><p className="text-xs text-muted-foreground">{label}</p><p className="text-sm font-medium capitalize">{value}</p></div>
);

const FlagRow = ({ label, value }) => (
  <div className={`p-2 rounded border text-xs font-medium flex items-center gap-1.5 ${value ? 'bg-red-50 border-red-200 text-red-700' : 'bg-muted/30 border-border text-muted-foreground'}`}>
    <span>{value ? '⚠️' : '✓'}</span> {label}
  </div>
);

export default DogProfilePage;
