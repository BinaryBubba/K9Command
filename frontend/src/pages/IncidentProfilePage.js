import React, { useEffect, useState, useCallback, useRef } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import useAuthStore from '../store/authStore';
import api from '../utils/api';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Textarea } from '../components/ui/textarea';
import { Label } from '../components/ui/label';
import { AlertCircleIcon, CheckCircleIcon, ShieldAlertIcon, UploadIcon, PlusIcon } from 'lucide-react';
import { toast } from 'sonner';

const SEVERITY_COLORS = {
  info: 'bg-blue-100 text-blue-700',
  caution: 'bg-amber-100 text-amber-700',
  warning: 'bg-orange-100 text-orange-700',
  critical: 'bg-red-100 text-red-700',
};

const STATUS_COLORS = {
  open: 'bg-red-100 text-red-700',
  acknowledged: 'bg-amber-100 text-amber-700',
  resolved: 'bg-blue-100 text-blue-700',
  closed: 'bg-gray-100 text-gray-600',
};

const SEVERITY_ICONS = { info: '📋', caution: '⚠️', warning: '🚨', critical: '🔴' };

const IncidentProfilePage = () => {
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const { incidentId } = useParams();
  const [incident, setIncident] = useState(null);
  const [dog, setDog] = useState(null);
  const [notes, setNotes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAddNote, setShowAddNote] = useState(false);
  const [noteText, setNoteText] = useState('');
  const [photoKeys, setPhotoKeys] = useState([]);
  const [photoPreviews, setPhotoPreviews] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const fileRef = useRef();

  const fetchData = useCallback(async () => {
    try {
      const [res, notesRes] = await Promise.all([
        api.get(`/incidents/${incidentId}`),
        api.get(`/incidents/${incidentId}/notes`).catch(() => ({ data: [] })),
      ]);
      setIncident(res.data);
      setNotes(notesRes.data);
      if (res.data.dog_id) {
        api.get(`/dogs/${res.data.dog_id}`).then(r => setDog(r.data)).catch(() => {});
      }
    } catch { toast.error('Failed to load incident'); }
    finally { setLoading(false); }
  }, [incidentId]);

  useEffect(() => {
    if (!user) { navigate('/auth'); return; }
    fetchData();
  }, [user, navigate, fetchData]);

  const handlePhotoUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setPhotoPreviews(prev => [...prev, URL.createObjectURL(file)]);
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await api.post('/uploads/incident', formData, { headers: { 'Content-Type': 'multipart/form-data' } });
      setPhotoKeys(prev => [...prev, res.data.key]);
      toast.success('Photo uploaded');
    } catch { toast.error('Upload failed'); setPhotoPreviews(p => p.slice(0,-1)); }
    finally { setUploading(false); }
  };

  const handleAddNote = async () => {
    if (!noteText.trim()) { toast.error('Note text required'); return; }
    try {
      await api.post(`/incidents/${incidentId}/notes`, {
        note_text: noteText,
        photo_keys: photoKeys,
      });
      toast.success('Note added');
      setNoteText(''); setPhotoKeys([]); setPhotoPreviews([]); setShowAddNote(false);
      fetchData();
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed to add note'); }
  };

  const handleAcknowledge = async () => {
    try {
      await api.post(`/incidents/${incidentId}/acknowledge`);
      toast.success('Acknowledged');
      fetchData();
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed'); }
  };

  const handleResolve = async () => {
    const resNotes = window.prompt('Resolution notes (optional):');
    if (resNotes === null) return;
    try {
      await api.post(`/incidents/${incidentId}/resolve`, { resolution_notes: resNotes });
      toast.success('Resolved');
      fetchData();
    } catch { toast.error('Failed'); }
  };

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-primary"></div>
    </div>
  );

  if (!incident) return <div className="min-h-screen flex items-center justify-center"><p>Incident not found</p></div>;

  return (
    <div className="min-h-screen bg-[#F9F7F2]">
      <header className="bg-white border-b shadow-sm sticky top-0 z-10">
        <div className="max-w-3xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-xl">{SEVERITY_ICONS[incident.severity] || '📋'}</span>
            <div>
              <h1 className="text-base font-serif font-bold text-primary">{incident.title}</h1>
              <p className="text-xs text-muted-foreground">
                {incident.occurred_at ? new Date(incident.occurred_at).toLocaleString() : new Date(incident.created_at).toLocaleString()}
              </p>
            </div>
          </div>
          <div className="flex gap-1">
            <Badge className={`text-xs ${SEVERITY_COLORS[incident.severity] || SEVERITY_COLORS.info}`}>{incident.severity}</Badge>
            <Badge className={`text-xs ${STATUS_COLORS[incident.status] || STATUS_COLORS.open}`}>{incident.status}</Badge>
          </div>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 py-6 space-y-4">

        {/* Acknowledgment required banner */}
        {incident.requires_acknowledgment && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <ShieldAlertIcon size={16} className="text-red-600" />
              <p className="text-sm font-medium text-red-800">Owner acknowledgment required</p>
            </div>
            {user?.role === 'admin' && (
              <Button size="sm" className="bg-red-600 hover:bg-red-700 text-white" onClick={handleAcknowledge}>
                Acknowledge
              </Button>
            )}
          </div>
        )}

        {/* Main details */}
        <Card>
          <CardContent className="py-4 px-4 space-y-3">
            <div>
              <p className="text-xs font-medium text-muted-foreground">Description</p>
              <p className="text-sm mt-1">{incident.description}</p>
            </div>
            {incident.immediate_action_taken && (
              <div>
                <p className="text-xs font-medium text-muted-foreground">Immediate Action Taken</p>
                <p className="text-sm mt-1">{incident.immediate_action_taken}</p>
              </div>
            )}
            {incident.location_description && (
              <div>
                <p className="text-xs font-medium text-muted-foreground">Location</p>
                <p className="text-sm mt-1">{incident.location_description}</p>
              </div>
            )}
            {incident.witness_names && (
              <div>
                <p className="text-xs font-medium text-muted-foreground">Witnesses</p>
                <p className="text-sm mt-1">{incident.witness_names}</p>
              </div>
            )}
            {dog && (
              <div className="flex items-center gap-2 pt-2 border-t">
                <p className="text-xs font-medium text-muted-foreground">Dog involved:</p>
                <button className="text-sm text-primary hover:underline"
                  onClick={() => navigate(`/admin/dogs/${dog.id}`)}>
                  {dog.name} ({dog.breed})
                </button>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Resolution */}
        {incident.resolution_notes && (
          <Card className="border-green-200">
            <CardContent className="py-3 px-4">
              <p className="text-xs font-medium text-green-700 mb-1">✓ Resolution Notes</p>
              <p className="text-sm">{incident.resolution_notes}</p>
              {incident.resolved_at && (
                <p className="text-xs text-muted-foreground mt-1">Resolved {new Date(incident.resolved_at).toLocaleString()}</p>
              )}
            </CardContent>
          </Card>
        )}

        {/* Progress Notes */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-medium">Progress Notes ({notes.length})</h3>
            <Button size="sm" onClick={() => setShowAddNote(!showAddNote)}>
              <PlusIcon size={14} className="mr-1" /> Add Note
            </Button>
          </div>

          {showAddNote && (
            <Card className="border-primary/30 mb-3">
              <CardContent className="pt-4 space-y-3">
                <div>
                  <Label>Note</Label>
                  <Textarea value={noteText} onChange={e => setNoteText(e.target.value)}
                    className="mt-1" rows={3} placeholder="Update on incident progress..." />
                </div>
                <div className="flex items-center gap-2">
                  <Button type="button" variant="outline" size="sm"
                    onClick={() => fileRef.current?.click()} disabled={uploading}>
                    <UploadIcon size={14} className="mr-1" /> {uploading ? 'Uploading...' : 'Add Photo'}
                  </Button>
                  {photoKeys.length > 0 && <span className="text-xs text-green-600">✓ {photoKeys.length} photo{photoKeys.length !== 1 ? 's' : ''}</span>}
                  <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={handlePhotoUpload} />
                </div>
                {photoPreviews.length > 0 && (
                  <div className="flex gap-2 flex-wrap">
                    {photoPreviews.map((url, i) => (
                      <img key={i} src={url} alt="preview" className="h-16 w-16 object-cover rounded border" />
                    ))}
                  </div>
                )}
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={() => setShowAddNote(false)}>Cancel</Button>
                  <Button size="sm" onClick={handleAddNote}>Save Note</Button>
                </div>
              </CardContent>
            </Card>
          )}

          {notes.length === 0 ? (
            <Card><CardContent className="py-8 text-center text-muted-foreground text-sm">No progress notes yet</CardContent></Card>
          ) : notes.map(note => (
            <Card key={note.id} className="mb-2">
              <CardContent className="py-3 px-4">
                <p className="text-sm">{note.note_text}</p>
                {note.photo_urls?.filter(Boolean).length > 0 && (
                  <div className="flex gap-2 mt-2 flex-wrap">
                    {note.photo_urls.filter(Boolean).map((url, i) => (
                      <button key={i} onClick={() => window.open(url, '_blank')}>
                        <img src={url} alt="note" className="h-16 w-16 object-cover rounded border hover:opacity-80" />
                      </button>
                    ))}
                  </div>
                )}
                <p className="text-xs text-muted-foreground mt-1">
                  {note.created_by_name} · {new Date(note.created_at).toLocaleString()}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Actions */}
        {incident.status !== 'resolved' && incident.status !== 'closed' && (
          <div className="flex gap-3 pb-6">
            {incident.requires_acknowledgment && user?.role === 'admin' && (
              <Button variant="outline" className="flex-1 text-red-600 border-red-200" onClick={handleAcknowledge}>
                Acknowledge
              </Button>
            )}
            <Button className="flex-1" onClick={handleResolve}>
              <CheckCircleIcon size={14} className="mr-1" /> Mark Resolved
            </Button>
          </div>
        )}
      </main>
    </div>
  );
};

export default IncidentProfilePage;
