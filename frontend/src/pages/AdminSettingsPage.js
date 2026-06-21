import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import useAuthStore from '../store/authStore';
import api from '../utils/api';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { PlusIcon, PencilIcon, HomeIcon, CalendarIcon, AlertCircleIcon, CheckIcon, XIcon } from 'lucide-react';
import { toast } from 'sonner';

const ROOM_TYPE_LABELS = {
  room: 'Room', crate_xl: 'Crate XL', crate_medium: 'Crate M', crate_small: 'Crate S',
};

const AdminSettingsPage = () => {
  const [orgSettings, setOrgSettings] = useState({ contact_phone: '', contact_email: '', contact_address: '' });
  const [orgSaving, setOrgSaving] = useState(false);

  useEffect(() => {
    api.get('/users/org/settings').then(r => setOrgSettings(r.data)).catch(() => {});
  }, []);

  const handleSaveOrg = async () => {
    setOrgSaving(true);
    try {
      await api.patch('/users/org/settings', orgSettings);
      toast.success('Settings saved');
    } catch { toast.error('Failed'); }
    finally { setOrgSaving(false); }
  };
  useEffect(() => {
  }, []);

  const { user } = useAuthStore();
  const navigate = useNavigate();
  useEffect(() => { if (!user || user.role !== 'admin') navigate('/auth'); }, [user, navigate]);

  return (
    <div className="min-h-screen bg-[#F9F7F2]">
      <header className="bg-white border-b shadow-sm sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 py-3">
          <h1 className="text-lg font-serif font-bold text-primary">Settings</h1>
        </div>
      </header>
      <main className="max-w-4xl mx-auto px-4 py-6">
        <Tabs defaultValue="rooms">
          <TabsList className="w-full mb-6">
            <TabsTrigger value="import" className="flex-1">Import</TabsTrigger>
            <TabsTrigger value="rooms" className="flex-1">Rooms & Crates</TabsTrigger>
            <TabsTrigger value="closures" className="flex-1">Closures</TabsTrigger>
            <TabsTrigger value="org" className="flex-1">Organization</TabsTrigger>
          </TabsList>
          <TabsContent value="import"><ImportTab /></TabsContent>
          <TabsContent value="rooms"><RoomsTab /></TabsContent>
          <TabsContent value="closures"><ClosuresTab /></TabsContent>
          <TabsContent value="org"><OrgTab orgSettings={orgSettings} setOrgSettings={setOrgSettings} handleSaveOrg={handleSaveOrg} orgSaving={orgSaving} /></TabsContent>
        </Tabs>
        <ExportsSection />
      </main>
    </div>
  );
};

const RoomsTab = () => {
  const [rooms, setRooms] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(null);
  const [showCreate, setShowCreate] = useState(false);

  const fetchRooms = useCallback(async () => {
    try {
      const res = await api.get('/facility/rooms');
      setRooms(res.data);
    } catch { toast.error('Failed to load rooms'); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchRooms(); }, [fetchRooms]);

  const saveRoom = async (room, updates) => {
    try {
      await api.patch(`/facility/rooms/${room.id}`, updates);
      toast.success('Room updated');
      setEditing(null);
      fetchRooms();
    } catch { toast.error('Failed to update room'); }
  };

  const rooms_list = rooms.filter(r => !r.room_type || r.room_type === 'room');
  const crates_list = rooms.filter(r => r.room_type && r.room_type !== 'room');

  if (loading) return <div className="py-8 text-center text-muted-foreground">Loading...</div>;

  return (
    <div className="space-y-6">
      <div>
        <div className="flex justify-between items-center mb-3">
          <h3 className="font-medium">Rooms ({rooms_list.length})</h3>
          <Button size="sm" variant="outline" onClick={() => setShowCreate('room')}>
            <PlusIcon size={14} className="mr-1" /> Add Room
          </Button>
        </div>
        <div className="space-y-2">
          {rooms_list.map(room => (
            <RoomRow key={room.id} room={room} editing={editing === room.id}
              onEdit={() => setEditing(room.id)}
              onSave={(updates) => saveRoom(room, updates)}
              onCancel={() => setEditing(null)} />
          ))}
        </div>
      </div>

      <div>
        <div className="flex justify-between items-center mb-3">
          <h3 className="font-medium">Crates ({crates_list.length})</h3>
          <Button size="sm" variant="outline" onClick={() => setShowCreate('crate')}>
            <PlusIcon size={14} className="mr-1" /> Add Crate
          </Button>
        </div>
        <div className="space-y-2">
          {crates_list.map(room => (
            <RoomRow key={room.id} room={room} editing={editing === room.id}
              onEdit={() => setEditing(room.id)}
              onSave={(updates) => saveRoom(room, updates)}
              onCancel={() => setEditing(null)} />
          ))}
        </div>
      </div>

      {showCreate && (
        <CreateRoomModal
          type={showCreate}
          onClose={() => setShowCreate(false)}
          onSuccess={() => { setShowCreate(false); fetchRooms(); }}
        />
      )}
    </div>
  );
};

const RoomRow = ({ room, editing, onEdit, onSave, onCancel }) => {
  const [form, setForm] = useState({
    name: room.name,
    max_dogs: room.max_dogs,
    adjacency_group: room.adjacency_group || '',
    is_out_of_service: room.is_out_of_service,
    out_of_service_reason: room.out_of_service_reason || '',
  });

  if (editing) return (
    <Card className="border-primary/30">
      <CardContent className="py-3 px-4 space-y-3">
        <div className="grid grid-cols-3 gap-3">
          <div>
            <Label className="text-xs">Name</Label>
            <Input value={form.name} onChange={e => setForm(f=>({...f,name:e.target.value}))} className="mt-1 h-8 text-sm" />
          </div>
          <div>
            <Label className="text-xs">Max Dogs</Label>
            <Input type="number" min="1" max="10" value={form.max_dogs}
              onChange={e => setForm(f=>({...f,max_dogs:parseInt(e.target.value)}))} className="mt-1 h-8 text-sm" />
          </div>
          <div>
            <Label className="text-xs">Group</Label>
            <Input value={form.adjacency_group}
              onChange={e => setForm(f=>({...f,adjacency_group:e.target.value}))} className="mt-1 h-8 text-sm" />
          </div>
        </div>
        <label className="flex items-center gap-2 text-sm cursor-pointer">
          <input type="checkbox" checked={form.is_out_of_service}
            onChange={e => setForm(f=>({...f,is_out_of_service:e.target.checked}))} className="w-4 h-4" />
          Out of service
        </label>
        {form.is_out_of_service && (
          <Input placeholder="Reason" value={form.out_of_service_reason}
            onChange={e => setForm(f=>({...f,out_of_service_reason:e.target.value}))} className="h-8 text-sm" />
        )}
        <div className="flex gap-2">
          <Button size="sm" onClick={() => onSave(form)} className="h-7">
            <CheckIcon size={12} className="mr-1" /> Save
          </Button>
          <Button size="sm" variant="outline" onClick={onCancel} className="h-7">
            <XIcon size={12} className="mr-1" /> Cancel
          </Button>
        </div>
      </CardContent>
    </Card>
  );

  return (
    <Card className={room.is_out_of_service ? 'opacity-60' : ''}>
      <CardContent className="py-3 px-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <HomeIcon size={16} className="text-muted-foreground" />
            <div>
              <div className="flex items-center gap-2">
                <p className="font-medium text-sm">{room.name}</p>
                {room.room_type && room.room_type !== 'room' && (
                  <Badge variant="secondary" className="text-xs">{ROOM_TYPE_LABELS[room.room_type] || room.room_type}</Badge>
                )}
                {room.is_out_of_service && <Badge variant="outline" className="text-xs text-red-600 border-red-200">OOS</Badge>}
              </div>
              <p className="text-xs text-muted-foreground">
                Max {room.max_dogs} · Group {room.adjacency_group || '—'}
              </p>
            </div>
          </div>
          <Button size="sm" variant="ghost" className="h-7 px-2" onClick={onEdit}>
            <PencilIcon size={14} />
          </Button>
        </div>
      </CardContent>
    </Card>
  );
};

const CreateRoomModal = ({ type, onClose, onSuccess }) => {
  const [form, setForm] = useState({
    name: '', max_dogs: type === 'crate' ? 1 : 3,
    adjacency_group: type === 'crate' ? 'C' : 'A',
    room_type: type === 'crate' ? 'crate_xl' : 'room',
  });
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    if (!form.name.trim()) { toast.error('Name is required'); return; }
    setSubmitting(true);
    try {
      await api.post('/facility/rooms', form);
      toast.success(`${type === 'crate' ? 'Crate' : 'Room'} created`);
      onSuccess();
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed to create'); }
    finally { setSubmitting(false); }
  };

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-end md:items-center justify-center p-4">
      <div className="bg-white rounded-t-2xl md:rounded-2xl w-full max-w-md">
        <div className="p-6 space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-lg font-bold">Add {type === 'crate' ? 'Crate' : 'Room'}</h2>
            <button onClick={onClose} className="text-muted-foreground text-xl">×</button>
          </div>
          <div>
            <Label>Name *</Label>
            <Input value={form.name} onChange={e => setForm(f=>({...f,name:e.target.value}))} className="mt-1" placeholder={type === 'crate' ? 'e.g. Crate XL-5' : 'e.g. Room 9'} />
          </div>
          {type === 'crate' && (
            <div>
              <Label>Crate Size</Label>
              <select className="w-full mt-1 border rounded-md px-3 py-2 text-sm bg-background"
                value={form.room_type} onChange={e => setForm(f=>({...f,room_type:e.target.value}))}>
                <option value="crate_xl">XL</option>
                <option value="crate_medium">Medium</option>
                <option value="crate_small">Small</option>
              </select>
            </div>
          )}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label>Max Dogs</Label>
              <Input type="number" min="1" max="10" value={form.max_dogs}
                onChange={e => setForm(f=>({...f,max_dogs:parseInt(e.target.value)}))} className="mt-1" />
            </div>
            <div>
              <Label>Adjacency Group</Label>
              <Input value={form.adjacency_group}
                onChange={e => setForm(f=>({...f,adjacency_group:e.target.value}))} className="mt-1" />
            </div>
          </div>
          <div className="flex gap-3 pt-2">
            <Button variant="outline" className="flex-1" onClick={onClose}>Cancel</Button>
            <Button className="flex-1" onClick={handleSubmit} disabled={submitting}>
              {submitting ? 'Creating...' : 'Create'}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

const ClosuresTab = () => {
  const [closures, setClosures] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState({ date: '', status: 'CLOSED', reason: '', affects_bookings: true });
  const [submitting, setSubmitting] = useState(false);

  const fetchClosures = useCallback(async () => {
    try {
      const now = new Date();
      const future = new Date(now.getTime() + 90*24*60*60*1000);
      const res = await api.get('/facility/status', { params: { start_date: now.toISOString(), end_date: future.toISOString() } });
      setClosures(res.data.filter(c => c.status !== 'open'));
    } catch { toast.error('Failed to load closures'); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchClosures(); }, [fetchClosures]);

  const handleAdd = async () => {
    if (!form.date || !form.reason.trim()) { toast.error('Date and reason required'); return; }
    setSubmitting(true);
    try {
      await api.post('/facility/status', { date: new Date(form.date).toISOString(), status: form.status, reason: form.reason, affects_bookings: form.affects_bookings });
      toast.success('Closure added'); setShowAdd(false);
      setForm({ date: '', status: 'CLOSED', reason: '', affects_bookings: true });
      fetchClosures();
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed'); }
    finally { setSubmitting(false); }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Remove this closure?')) return;
    try { await api.delete(`/facility/status/${id}`); fetchClosures(); } catch { toast.error('Failed'); }
  };

  if (loading) return <div className="py-8 text-center text-muted-foreground">Loading...</div>;

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <p className="text-sm text-muted-foreground">Upcoming closures (next 90 days)</p>
        <Button size="sm" onClick={() => setShowAdd(!showAdd)}><PlusIcon size={16} className="mr-1" /> Add</Button>
      </div>
      {showAdd && (
        <Card className="border-primary/30">
          <CardContent className="pt-4 space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div><Label>Date *</Label><Input type="date" value={form.date} onChange={e => setForm(f=>({...f,date:e.target.value}))} className="mt-1" /></div>
              <div><Label>Type</Label>
                <select className="w-full mt-1 border rounded-md px-3 py-2 text-sm bg-background" value={form.status} onChange={e => setForm(f=>({...f,status:e.target.value}))}>
                  <option value="CLOSED">Closed</option><option value="HOLIDAY">Holiday</option><option value="LIMITED">Limited</option>
                </select>
              </div>
            </div>
            <div><Label>Reason *</Label><Input value={form.reason} onChange={e => setForm(f=>({...f,reason:e.target.value}))} className="mt-1" /></div>
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input type="checkbox" checked={form.affects_bookings} onChange={e => setForm(f=>({...f,affects_bookings:e.target.checked}))} className="w-4 h-4" />
              Block new bookings
            </label>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={() => setShowAdd(false)}>Cancel</Button>
              <Button size="sm" onClick={handleAdd} disabled={submitting}>{submitting ? 'Adding...' : 'Add'}</Button>
            </div>
          </CardContent>
        </Card>
      )}
      {closures.length === 0 ? (
        <Card><CardContent className="py-8 text-center text-muted-foreground">No upcoming closures</CardContent></Card>
      ) : closures.map(c => (
        <Card key={c.id}><CardContent className="py-3 px-4">
          <div className="flex items-center justify-between">
            <div><p className="font-medium text-sm">{new Date(c.date).toLocaleDateString(undefined,{weekday:'long',year:'numeric',month:'long',day:'numeric'})}</p>
              <p className="text-xs text-muted-foreground">{c.reason}</p></div>
            <div className="flex items-center gap-2">
              <Badge className="text-xs bg-red-100 text-red-700">{c.status}</Badge>
              <Button variant="ghost" size="sm" className="text-red-500 h-7 px-2" onClick={() => handleDelete(c.id)}>×</Button>
            </div>
          </div>
        </CardContent></Card>
      ))}
    </div>
  );
};

const OrgTab = ({ orgSettings, setOrgSettings, handleSaveOrg, orgSaving }) => (
  <Card><CardContent className="py-6 space-y-4">
    <div>
      <Label>Contact Phone</Label>
      <Input value={orgSettings.contact_phone || ''} className="mt-1"
        placeholder="(763) 000-0000"
        onChange={e => setOrgSettings(s => ({...s, contact_phone: e.target.value}))} />
    </div>
    <div>
      <Label>Contact Email</Label>
      <Input value={orgSettings.contact_email || ''} className="mt-1"
        placeholder="info@k9countryclubkennel.com"
        onChange={e => setOrgSettings(s => ({...s, contact_email: e.target.value}))} />
    </div>
    <div>
      <Label>Address</Label>
      <Input value={orgSettings.contact_address || ''} className="mt-1"
        placeholder="123 Main St, Elk River MN 55330"
        onChange={e => setOrgSettings(s => ({...s, contact_address: e.target.value}))} />
    </div>
    <Button onClick={handleSaveOrg} disabled={orgSaving}>
      {orgSaving ? 'Saving...' : 'Save Contact Info'}
    </Button>
  </CardContent></Card>
);

const ImportTab = () => {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState([]);
  const [importing, setImporting] = useState(false);
  const [results, setResults] = useState(null);
  const fileRef = React.useRef();

  const handleFile = (e) => {
    const f = e.target.files[0];
    if (!f) return;
    setFile(f);
    const reader = new FileReader();
    reader.onload = (ev) => {
      const lines = ev.target.result.split('\n').filter(Boolean);
      const headers = lines[0].split(',').map(h => h.trim().replace(/"/g,''));
      const rows = lines.slice(1, 6).map(l => {
        const vals = l.split(',').map(v => v.trim().replace(/"/g,''));
        return Object.fromEntries(headers.map((h, i) => [h, vals[i] || '']));
      });
      setPreview(rows);
    };
    reader.readAsText(f);
  };

  const handleImport = async () => {
    if (!file) return;
    setImporting(true);
    const formData = new FormData();
    formData.append('file', file);
    try {
      const res = await api.post('/households/import-csv', formData, { headers: { 'Content-Type': 'multipart/form-data' } });
      setResults(res.data);
      toast.success(`Imported ${res.data.created} customers`);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Import failed');
    } finally {
      setImporting(false);
    }
  };

  return (
    <div className="space-y-4">
      <Card>
        <CardContent className="py-4 px-4 space-y-3">
          <h3 className="font-medium text-sm">Customer CSV Import</h3>
          <p className="text-xs text-muted-foreground">
            Upload a CSV with columns in this order:
          </p>
          <code className="text-xs bg-muted px-2 py-1 rounded block">display_name, first_name, last_name, email, phone, dogs</code>
          <p className="text-xs text-muted-foreground">
            The <strong>dogs</strong> column is optional. Use semicolons to separate multiple dogs (e.g. <code className="bg-muted px-1 rounded">Buddy;Max</code>).
          </p>
          <div className="flex items-center gap-3">
            <Button variant="outline" size="sm" onClick={() => fileRef.current?.click()}>
              Choose CSV File
            </Button>
            {file && <span className="text-xs text-green-600">✓ {file.name}</span>}
            <input ref={fileRef} type="file" accept=".csv" className="hidden" onChange={handleFile} />
          </div>
          {preview.length > 0 && (
            <div className="overflow-x-auto">
              <p className="text-xs text-muted-foreground mb-1">Preview (first 5 rows):</p>
              <table className="text-xs w-full border-collapse">
                <thead>
                  <tr>{Object.keys(preview[0]).map(h => <th key={h} className="border px-2 py-1 text-left bg-muted">{h}</th>)}</tr>
                </thead>
                <tbody>
                  {preview.map((row, i) => (
                    <tr key={i}>{Object.values(row).map((v, j) => <td key={j} className="border px-2 py-1">{v}</td>)}</tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {file && (
            <Button onClick={handleImport} disabled={importing}>
              {importing ? 'Importing...' : 'Import Customers'}
            </Button>
          )}
          {results && (
            <div className="p-3 bg-green-50 border border-green-200 rounded-lg text-sm">
              <p className="font-medium text-green-800">Import Complete</p>
              <p className="text-xs text-green-700 mt-1">
                Created: {results.created} · Skipped: {results.skipped} · Errors: {results.errors}
              </p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

const ExportsSection = () => {
  const downloadCSV = async (endpoint, filename) => {
    try {
      const token = JSON.parse(localStorage.getItem('auth-storage') || '{}')?.state?.token;
      const res = await fetch(`/api/dashboard/${endpoint}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = filename; a.click();
      URL.revokeObjectURL(url);
    } catch { alert('Export failed'); }
  };

  return (
    <div className="bg-white rounded-xl border shadow-sm p-5 space-y-3">
      <h2 className="font-serif font-semibold text-primary">Data Exports</h2>
      <p className="text-xs text-muted-foreground">Download CSV exports for reporting and record-keeping.</p>
      <div className="grid grid-cols-2 gap-3">
        <button onClick={() => downloadCSV('export/bookings', 'bookings.csv')}
          className="p-3 rounded-lg border hover:bg-muted text-left">
          <p className="text-sm font-medium">📅 Bookings</p>
          <p className="text-xs text-muted-foreground">All bookings with dates and dogs</p>
        </button>
        <button onClick={() => downloadCSV('export/customers', 'customers.csv')}
          className="p-3 rounded-lg border hover:bg-muted text-left">
          <p className="text-sm font-medium">👥 Customers</p>
          <p className="text-xs text-muted-foreground">All households and contact info</p>
        </button>
        <button onClick={() => downloadCSV('export/dogs', 'dogs.csv')}
          className="p-3 rounded-lg border hover:bg-muted text-left">
          <p className="text-sm font-medium">🐾 Dogs</p>
          <p className="text-xs text-muted-foreground">All dogs with behavior flags</p>
        </button>
        <button onClick={() => downloadCSV('export/incidents', 'incidents.csv')}
          className="p-3 rounded-lg border hover:bg-muted text-left">
          <p className="text-sm font-medium">⚠️ Incidents</p>
          <p className="text-xs text-muted-foreground">All incident reports</p>
        </button>
      </div>
    </div>
  );
};

export default AdminSettingsPage;
