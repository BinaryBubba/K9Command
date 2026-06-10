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
import {
  ArrowLeftIcon, PlusIcon, SettingsIcon,
  HomeIcon, CalendarIcon, AlertCircleIcon,
} from 'lucide-react';
import { toast } from 'sonner';

const AdminSettingsPage = () => {
  const { user } = useAuthStore();
  const navigate = useNavigate();

  useEffect(() => {
    if (!user || user.role !== 'admin') { navigate('/auth'); return; }
  }, [user, navigate]);

  return (
    <div className="min-h-screen bg-[#F9F7F2]">
      <header className="bg-white border-b shadow-sm sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={() => navigate(-1)}>
            <ArrowLeftIcon size={18} />
          </Button>
          <h1 className="text-lg font-serif font-bold text-primary">Settings</h1>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-6">
        <Tabs defaultValue="rooms">
          <TabsList className="w-full mb-6">
            <TabsTrigger value="rooms" className="flex-1">Rooms</TabsTrigger>
            <TabsTrigger value="closures" className="flex-1">Closures</TabsTrigger>
            <TabsTrigger value="org" className="flex-1">Organization</TabsTrigger>
          </TabsList>

          <TabsContent value="rooms"><RoomsTab /></TabsContent>
          <TabsContent value="closures"><ClosuresTab /></TabsContent>
          <TabsContent value="org"><OrgTab /></TabsContent>
        </Tabs>
      </main>
    </div>
  );
};

const RoomsTab = () => {
  const [rooms, setRooms] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get('/bookings/rooms/list')
      .then(r => setRooms(r.data))
      .catch(() => toast.error('Failed to load rooms'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="py-8 text-center text-muted-foreground">Loading...</div>;

  return (
    <div className="space-y-3">
      <div className="flex justify-between items-center">
        <p className="text-sm text-muted-foreground">{rooms.length} rooms configured</p>
      </div>
      {rooms.map(room => (
        <Card key={room.id}>
          <CardContent className="py-3 px-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="bg-blue-50 p-2 rounded-lg">
                  <HomeIcon size={16} className="text-blue-600" />
                </div>
                <div>
                  <p className="font-medium">{room.name}</p>
                  <p className="text-xs text-muted-foreground">
                    Max {room.max_dogs} dogs · Group {room.adjacency_group}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {room.is_out_of_service && (
                  <Badge variant="outline" className="text-xs text-red-600 border-red-200">Out of service</Badge>
                )}
                <Badge variant="outline" className="text-xs">
                  {room.is_active ? 'Active' : 'Inactive'}
                </Badge>
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
      <p className="text-xs text-muted-foreground text-center pt-2">
        Room configuration changes require server access. Contact your administrator.
      </p>
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
      const future = new Date(now.getTime() + 90 * 24 * 60 * 60 * 1000);
      const res = await api.get('/facility/status', {
        params: {
          start_date: now.toISOString(),
          end_date: future.toISOString(),
        }
      });
      setClosures(res.data.filter(c => c.status !== 'open'));
    } catch {
      toast.error('Failed to load closures');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchClosures(); }, [fetchClosures]);

  const handleAdd = async () => {
    if (!form.date) { toast.error('Date is required'); return; }
    if (!form.reason.trim()) { toast.error('Reason is required'); return; }
    setSubmitting(true);
    try {
      await api.post('/facility/status', {
        date: new Date(form.date).toISOString(),
        status: form.status,
        reason: form.reason,
        affects_bookings: form.affects_bookings,
      });
      toast.success('Closure added');
      setShowAdd(false);
      setForm({ date: '', status: 'CLOSED', reason: '', affects_bookings: true });
      fetchClosures();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to add closure');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Remove this closure date?')) return;
    try {
      await api.delete(`/facility/status/${id}`);
      toast.success('Closure removed');
      fetchClosures();
    } catch {
      toast.error('Failed to remove closure');
    }
  };

  const statusColors = {
    closed: 'bg-red-100 text-red-700',
    holiday: 'bg-blue-100 text-blue-700',
    limited: 'bg-amber-100 text-amber-700',
  };

  if (loading) return <div className="py-8 text-center text-muted-foreground">Loading...</div>;

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <p className="text-sm text-muted-foreground">Upcoming closures (next 90 days)</p>
        <Button size="sm" onClick={() => setShowAdd(!showAdd)}>
          <PlusIcon size={16} className="mr-1" /> Add Closure
        </Button>
      </div>

      {showAdd && (
        <Card className="border-primary/30">
          <CardContent className="pt-4 space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>Date *</Label>
                <Input type="date" value={form.date}
                  onChange={e => setForm(f => ({...f, date: e.target.value}))}
                  className="mt-1" />
              </div>
              <div>
                <Label>Type</Label>
                <select className="w-full mt-1 border rounded-md px-3 py-2 text-sm bg-background"
                  value={form.status} onChange={e => setForm(f => ({...f, status: e.target.value}))}>
                  <option value="CLOSED">Closed</option>
                  <option value="HOLIDAY">Holiday</option>
                  <option value="LIMITED">Limited capacity</option>
                </select>
              </div>
            </div>
            <div>
              <Label>Reason *</Label>
              <Input value={form.reason}
                onChange={e => setForm(f => ({...f, reason: e.target.value}))}
                placeholder="e.g. Independence Day" className="mt-1" />
            </div>
            <label className="flex items-center gap-2 cursor-pointer text-sm">
              <input type="checkbox" checked={form.affects_bookings}
                onChange={e => setForm(f => ({...f, affects_bookings: e.target.checked}))}
                className="w-4 h-4" />
              Block new bookings on this date
            </label>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={() => setShowAdd(false)}>Cancel</Button>
              <Button size="sm" onClick={handleAdd} disabled={submitting}>
                {submitting ? 'Adding...' : 'Add'}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {closures.length === 0 ? (
        <Card><CardContent className="py-8 text-center text-muted-foreground">
          No upcoming closures
        </CardContent></Card>
      ) : (
        closures.map(c => (
          <Card key={c.id}>
            <CardContent className="py-3 px-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="bg-gray-50 p-2 rounded-lg">
                    <CalendarIcon size={16} className="text-gray-600" />
                  </div>
                  <div>
                    <p className="font-medium">{new Date(c.date).toLocaleDateString(undefined, {weekday:'long', year:'numeric', month:'long', day:'numeric'})}</p>
                    <p className="text-xs text-muted-foreground">{c.reason}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Badge className={`text-xs ${statusColors[c.status] || 'bg-gray-100 text-gray-600'}`}>
                    {c.status}
                  </Badge>
                  <Button variant="ghost" size="sm" className="text-red-500 hover:text-red-700 h-7 px-2"
                    onClick={() => handleDelete(c.id)}>×</Button>
                </div>
              </div>
            </CardContent>
          </Card>
        ))
      )}
    </div>
  );
};

const OrgTab = () => (
  <Card>
    <CardHeader className="pb-2 pt-4">
      <CardTitle className="text-sm flex items-center gap-2">
        <SettingsIcon size={14} />
        Organization Info
      </CardTitle>
    </CardHeader>
    <CardContent className="space-y-3">
      <div>
        <Label>Organization Name</Label>
        <Input value="K9 Country Club" disabled className="mt-1 bg-muted" />
      </div>
      <div>
        <Label>Timezone</Label>
        <Input value="America/Chicago" disabled className="mt-1 bg-muted" />
      </div>
      <div>
        <Label>Owner Email</Label>
        <Input value="owners@k9countryclubkennel.com" disabled className="mt-1 bg-muted" />
      </div>
      <p className="text-xs text-muted-foreground pt-2 flex items-center gap-1">
        <AlertCircleIcon size={12} />
        Organization settings changes require server access.
      </p>
    </CardContent>
  </Card>
);

export default AdminSettingsPage;
