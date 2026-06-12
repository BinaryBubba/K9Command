import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import useAuthStore from '../store/authStore';
import api from '../utils/api';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { ArrowLeftIcon, PlusIcon, AlertCircleIcon, CheckCircleIcon, ShieldAlertIcon, UploadIcon } from 'lucide-react';
import { useRef } from 'react';
import { toast } from 'sonner';

const SEVERITY_COLORS = {
  info: 'bg-blue-100 text-blue-700',
  caution: 'bg-amber-100 text-amber-700',
  warning: 'bg-orange-100 text-orange-700',
  critical: 'bg-red-100 text-red-700',
};

const SEVERITY_ICONS = {
  info: '📋',
  caution: '⚠️',
  warning: '🚨',
  critical: '🔴',
};

const STATUS_COLORS = {
  open: 'bg-red-100 text-red-700',
  acknowledged: 'bg-amber-100 text-amber-700',
  resolved: 'bg-blue-100 text-blue-700',
  closed: 'bg-gray-100 text-gray-600',
};

const AdminIncidentsPage = () => {
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const [incidents, setIncidents] = useState([]);
  const [unacknowledged, setUnacknowledged] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);

  const fetchIncidents = useCallback(async () => {
    try {
      const [allRes, unackRes] = await Promise.all([
        api.get('/incidents'),
        api.get('/incidents/unacknowledged'),
      ]);
      setIncidents(allRes.data);
      setUnacknowledged(unackRes.data);
    } catch {
      toast.error('Failed to load incidents');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!user) { navigate('/auth'); return; }
    fetchIncidents();
  }, [user, navigate, fetchIncidents]);

  const acknowledge = async (id) => {
    try {
      await api.post(`/incidents/${id}/acknowledge`);
      toast.success('Incident acknowledged');
      fetchIncidents();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to acknowledge');
    }
  };

  const resolve = async (id) => {
    const notes = window.prompt('Resolution notes (optional):');
    if (notes === null) return;
    try {
      await api.post(`/incidents/${id}/resolve`, { resolution_notes: notes });
      toast.success('Incident resolved');
      fetchIncidents();
    } catch {
      toast.error('Failed to resolve incident');
    }
  };

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-primary"></div>
    </div>
  );

  return (
    <div className="min-h-screen bg-[#F9F7F2]">
      <header className="bg-white border-b shadow-sm sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="sm" onClick={() => navigate(-1)}>
              <ArrowLeftIcon size={18} />
            </Button>
            <h1 className="text-lg font-serif font-bold text-primary">Incidents</h1>
          </div>
          <Button size="sm" onClick={() => setShowCreate(true)}>
            <PlusIcon size={16} className="mr-1" /> Report
          </Button>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-6 space-y-5">

        {/* Unacknowledged banner */}
        {unacknowledged.length > 0 && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-sm font-semibold text-red-800 flex items-center gap-2 mb-3">
              <ShieldAlertIcon size={16} />
              {unacknowledged.length} incident{unacknowledged.length !== 1 ? 's' : ''} require owner acknowledgment
            </p>
            {unacknowledged.map(inc => (
              <div key={inc.id} className="flex items-center justify-between py-2 border-t border-red-100">
                <div>
                  <p className="text-sm font-medium text-red-800">{inc.title}</p>
                  <p className="text-xs text-red-600">{new Date(inc.occurred_at || inc.created_at).toLocaleString()}</p>
                </div>
                {user?.role === 'admin' && (
                  <Button size="sm" className="bg-red-600 hover:bg-red-700 text-white"
                    onClick={() => acknowledge(inc.id)}>
                    Acknowledge
                  </Button>
                )}
              </div>
            ))}
          </div>
        )}

        <Tabs defaultValue="open">
          <TabsList className="w-full mb-4">
            <TabsTrigger value="open" className="flex-1">
              Open ({incidents.filter(i => i.status === 'open' || i.status === 'acknowledged').length})
            </TabsTrigger>
            <TabsTrigger value="resolved" className="flex-1">
              Resolved ({incidents.filter(i => i.status === 'resolved' || i.status === 'closed').length})
            </TabsTrigger>
          </TabsList>

          <TabsContent value="open">
            <IncidentList
              incidents={incidents.filter(i => i.status === 'open' || i.status === 'acknowledged')}
              onAcknowledge={acknowledge}
              onResolve={resolve}
              isAdmin={user?.role === 'admin'}
            />
          </TabsContent>
          <TabsContent value="resolved">
            <IncidentList
              incidents={incidents.filter(i => i.status === 'resolved' || i.status === 'closed')}
              isAdmin={user?.role === 'admin'}
            />
          </TabsContent>
        </Tabs>
      </main>

      {showCreate && (
        <CreateIncidentModal
          onClose={() => setShowCreate(false)}
          onSuccess={() => { setShowCreate(false); fetchIncidents(); }}
        />
      )}
    </div>
  );
};

const IncidentList = ({ incidents, onAcknowledge, onResolve, isAdmin }) => {
  if (incidents.length === 0) return (
    <Card><CardContent className="py-10 text-center text-muted-foreground">No incidents</CardContent></Card>
  );
  return (
    <div className="space-y-3">
      {incidents.map(inc => (
        <Card key={inc.id} className={`cursor-pointer hover:shadow-md transition-shadow ${inc.severity === 'critical' ? 'border-red-300' : ''}`}
          onClick={() => navigate(`/admin/incidents/${inc.id}`)}>
          <CardContent className="py-4 px-4">
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1">
                <div className="flex items-center gap-2 flex-wrap mb-1">
                  <span>{SEVERITY_ICONS[inc.severity] || '📋'}</span>
                  <p className="font-medium text-sm">{inc.title}</p>
                  <Badge className={`text-xs ${SEVERITY_COLORS[inc.severity] || SEVERITY_COLORS.info}`}>
                    {inc.severity}
                  </Badge>
                  <Badge className={`text-xs ${STATUS_COLORS[inc.status] || STATUS_COLORS.open}`}>
                    {inc.status}
                  </Badge>
                  {inc.requires_acknowledgment && (
                    <Badge className="text-xs bg-red-100 text-red-700">Needs ack</Badge>
                  )}
                </div>
                <p className="text-xs text-muted-foreground">{inc.description}</p>
                {inc.immediate_action_taken && (
                  <p className="text-xs text-muted-foreground mt-1">
                    Action taken: {inc.immediate_action_taken}
                  </p>
                )}
                <p className="text-xs text-muted-foreground mt-1">
                  {inc.occurred_at ? new Date(inc.occurred_at).toLocaleString() : new Date(inc.created_at).toLocaleString()}
                </p>
              </div>
              <div className="flex flex-col gap-1.5 shrink-0">
                {inc.requires_acknowledgment && isAdmin && onAcknowledge && (
                  <Button size="sm" variant="outline" className="text-xs text-red-600 border-red-200"
                    onClick={() => onAcknowledge(inc.id)}>
                    Acknowledge
                  </Button>
                )}
                {inc.status !== 'resolved' && inc.status !== 'closed' && onResolve && (
                  <Button size="sm" variant="outline" className="text-xs"
                    onClick={() => onResolve(inc.id)}>
                    <CheckCircleIcon size={12} className="mr-1" /> Resolve
                  </Button>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
};

const CreateIncidentModal = ({ onClose, onSuccess }) => {
  const [form, setForm] = useState({
    title: '', description: '', severity: 'caution',
    immediate_action_taken: '', location_description: '',
    follow_up_required: false,
  });
  const [submitting, setSubmitting] = useState(false);
  const [photoKeys, setPhotoKeys] = useState([]);
  const [photoPreviews, setPhotoPreviews] = useState([]);
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef();

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
    } catch { toast.error('Upload failed'); setPhotoPreviews(prev => prev.slice(0,-1)); }
    finally { setUploading(false); }
  };

  const handleSubmit = async () => {
    if (!form.title.trim()) { toast.error('Title is required'); return; }
    if (!form.description.trim()) { toast.error('Description is required'); return; }
    setSubmitting(true);
    try {
      await api.post('/incidents', form);
      toast.success('Incident reported');
      onSuccess();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to report incident');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-end md:items-center justify-center p-4">
      <div className="bg-white rounded-t-2xl md:rounded-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="p-6 space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-lg font-bold">Report Incident</h2>
            <button onClick={onClose} className="text-muted-foreground text-xl">×</button>
          </div>
          <div>
            <Label>Title *</Label>
            <Input value={form.title} onChange={e => setForm(f=>({...f,title:e.target.value}))} className="mt-1" placeholder="Brief description of what happened" />
          </div>
          <div>
            <Label>Severity *</Label>
            <select className="w-full mt-1 border rounded-md px-3 py-2 text-sm bg-background"
              value={form.severity} onChange={e => setForm(f=>({...f,severity:e.target.value}))}>
              <option value="info">📋 Info — FYI only</option>
              <option value="caution">⚠️ Caution — monitor</option>
              <option value="warning">🚨 Warning — owner acknowledgment required</option>
              <option value="critical">🔴 Critical — immediate action required</option>
            </select>
          </div>
          <div>
            <Label>Full Description *</Label>
            <Textarea value={form.description} onChange={e => setForm(f=>({...f,description:e.target.value}))} className="mt-1" rows={3} placeholder="What happened, when, and who was involved" />
          </div>
          <div>
            <Label>Immediate Action Taken</Label>
            <Textarea value={form.immediate_action_taken} onChange={e => setForm(f=>({...f,immediate_action_taken:e.target.value}))} className="mt-1" rows={2} placeholder="What did you do right away?" />
          </div>
          <div>
            <Label>Location</Label>
            <Input value={form.location_description} onChange={e => setForm(f=>({...f,location_description:e.target.value}))} className="mt-1" placeholder="e.g. Outdoor play yard, Room 3" />
          </div>
          <label className="flex items-center gap-2 text-sm cursor-pointer">
            <input type="checkbox" checked={form.follow_up_required}
              onChange={e => setForm(f=>({...f,follow_up_required:e.target.checked}))} className="w-4 h-4" />
            Follow-up required
          </label>
          <div>
            <Label>Photos (optional)</Label>
            <div className="mt-1 space-y-2">
              <Button type="button" variant="outline" size="sm" onClick={() => fileRef.current?.click()} disabled={uploading}>
                <UploadIcon size={14} className="mr-1" /> {uploading ? 'Uploading...' : 'Add Photo'}
              </Button>
              <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={handlePhotoUpload} />
              {photoPreviews.length > 0 && (
                <div className="flex gap-2 flex-wrap">
                  {photoPreviews.map((url, i) => (
                    <img key={i} src={url} alt="preview" className="h-16 w-16 object-cover rounded border" />
                  ))}
                </div>
              )}
            </div>
          </div>
          {(form.severity === 'warning' || form.severity === 'critical') && (
            <div className="bg-amber-50 border border-amber-200 rounded p-3 text-xs text-amber-800">
              ⚠️ This incident will require owner acknowledgment before it can be closed.
            </div>
          )}
          <div className="flex gap-3 pt-2">
            <Button variant="outline" className="flex-1" onClick={onClose}>Cancel</Button>
            <Button className="flex-1" onClick={handleSubmit} disabled={submitting}>
              {submitting ? 'Reporting...' : 'Report Incident'}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminIncidentsPage;
