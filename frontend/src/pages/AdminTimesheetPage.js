import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Badge } from '../components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { ArrowLeftIcon, ClockIcon, SearchIcon, DownloadIcon, UserIcon, PlusIcon, EditIcon, TrashIcon, CheckIcon, XIcon } from 'lucide-react';
import { toast } from 'sonner';
import api from '../utils/api';
import useAuthStore from '../store/authStore';

const AdminTimesheetPage = () => {
  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);
  const [timeEntries, setTimeEntries] = useState([]);
  const [modRequests, setModRequests] = useState([]);
  const [staff, setStaff] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedStaff, setSelectedStaff] = useState('all');
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editMode, setEditMode] = useState(false);
  const [selectedEntry, setSelectedEntry] = useState(null);
  const [formData, setFormData] = useState({
    staff_id: '',
    clock_in: '',
    clock_out: '',
    notes: '',
  });

  useEffect(() => {
    if (!user || user.role !== 'admin') {
      navigate('/auth');
      return;
    }
    fetchData();
  }, [user, navigate]);

  const fetchData = async () => {
    try {
      const [entriesRes, staffRes, modRes] = await Promise.all([
        api.get('/time-entries'),
        api.get('/admin/users?role=staff'),
        api.get('/time-entries/modification-requests'),
      ]);
      setTimeEntries(entriesRes.data);
      setStaff(staffRes.data);
      setModRequests(modRes.data.filter(r => r.status === 'pending'));
    } catch (error) {
      toast.error('Failed to load timesheets');
    } finally {
      setLoading(false);
    }
  };

  const calculateHours = (clockIn, clockOut) => {
    if (!clockOut) return 'In Progress';
    const diff = new Date(clockOut) - new Date(clockIn);
    const hours = Math.floor(diff / 1000 / 60 / 60);
    const minutes = Math.floor((diff / 1000 / 60) % 60);
    return `${hours}h ${minutes}m`;
  };

  const getWeekRange = () => {
    const now = new Date();
    const dayOfWeek = now.getDay();
    const daysToMonday = dayOfWeek === 0 ? 6 : dayOfWeek - 1;
    const monday = new Date(now);
    monday.setDate(now.getDate() - daysToMonday);
    monday.setHours(0, 0, 0, 0);
    
    const sunday = new Date(monday);
    sunday.setDate(monday.getDate() + 6);
    sunday.setHours(23, 59, 59, 999);
    
    return { start: monday, end: sunday };
  };

  const calculateWeeklyTotal = (staffId) => {
    const { start, end } = getWeekRange();
    
    const weeklyEntries = timeEntries.filter(entry => {
      const entryDate = new Date(entry.clock_in);
      return entry.staff_id === staffId && entryDate >= start && entryDate <= end;
    });

    return weeklyEntries.reduce((total, entry) => {
      if (!entry.clock_out) return total;
      const diff = new Date(entry.clock_out) - new Date(entry.clock_in);
      return total + (diff / 1000 / 60 / 60);
    }, 0).toFixed(2);
  };

  const exportToCSV = () => {
    const { start, end } = getWeekRange();
    const headers = ['Staff Name', 'Date', 'Clock In', 'Clock Out', 'Hours', 'Notes'];
    const rows = timeEntries.map(entry => {
      const staffMember = staff.find(s => s.id === entry.staff_id);
      return [
        staffMember?.full_name || entry.staff_id,
        new Date(entry.clock_in).toLocaleDateString(),
        new Date(entry.clock_in).toLocaleTimeString(),
        entry.clock_out ? new Date(entry.clock_out).toLocaleTimeString() : 'In Progress',
        calculateHours(entry.clock_in, entry.clock_out),
        entry.notes || '',
      ];
    });

    const csv = [headers, ...rows].map(row => row.join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `timesheets_${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    toast.success('Timesheet exported!');
  };

  const openCreateModal = () => {
    setEditMode(false);
    setFormData({ staff_id: staff[0]?.id || '', clock_in: '', clock_out: '', notes: '' });
    setModalOpen(true);
  };

  const openEditModal = (entry) => {
    setEditMode(true);
    setSelectedEntry(entry);
    setFormData({
      staff_id: entry.staff_id,
      clock_in: entry.clock_in.slice(0, 16),
      clock_out: entry.clock_out ? entry.clock_out.slice(0, 16) : '',
      notes: entry.notes || '',
    });
    setModalOpen(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editMode) {
        await api.patch(`/time-entries/${selectedEntry.id}`, {
          clock_in: new Date(formData.clock_in).toISOString(),
          clock_out: formData.clock_out ? new Date(formData.clock_out).toISOString() : null,
          notes: formData.notes,
        });
        toast.success('Time entry updated');
      } else {
        await api.post('/time-entries', {
          staff_id: formData.staff_id,
          clock_in: new Date(formData.clock_in).toISOString(),
          clock_out: formData.clock_out ? new Date(formData.clock_out).toISOString() : null,
          notes: formData.notes,
        });
        toast.success('Time entry created');
      }
      setModalOpen(false);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save');
    }
  };

  const handleDelete = async (entryId) => {
    if (!window.confirm('Are you sure you want to delete this time entry?')) return;
    try {
      await api.delete(`/time-entries/${entryId}`);
      toast.success('Time entry deleted');
      fetchData();
    } catch (error) {
      toast.error('Failed to delete');
    }
  };

  const handleModRequest = async (requestId, action) => {
    try {
      await api.patch(`/time-entries/modification-requests/${requestId}?action=${action}`);
      toast.success(`Request ${action}d`);
      fetchData();
    } catch (error) {
      toast.error('Failed to process request');
    }
  };

  // Filter entries
  let filteredEntries = timeEntries;
  if (selectedStaff !== 'all') {
    filteredEntries = filteredEntries.filter(e => e.staff_id === selectedStaff);
  }
  if (searchQuery) {
    filteredEntries = filteredEntries.filter(entry => {
      const staffMember = staff.find(s => s.id === entry.staff_id);
      return staffMember?.full_name?.toLowerCase().includes(searchQuery.toLowerCase());
    });
  }

  // Group by staff
  const entriesByStaff = filteredEntries.reduce((acc, entry) => {
    if (!acc[entry.staff_id]) acc[entry.staff_id] = [];
    acc[entry.staff_id].push(entry);
    return acc;
  }, {});

  const totalHours = timeEntries.reduce((sum, entry) => {
    if (!entry.clock_out) return sum;
    const diff = new Date(entry.clock_out) - new Date(entry.clock_in);
    return sum + (diff / 1000 / 60 / 60);
  }, 0);

  const { start: weekStart, end: weekEnd } = getWeekRange();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="inline-block animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#F9F7F2]">
      <header className="bg-white border-b border-border/40 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 md:px-8 py-4">
          <Button variant="ghost" onClick={() => navigate('/admin/dashboard')} className="flex items-center gap-2 mb-2">
            <ArrowLeftIcon size={18} /> Back to Dashboard
          </Button>
          <div className="flex justify-between items-start">
            <div>
              <h1 className="text-3xl font-serif font-bold text-primary">Staff Timesheets</h1>
              <p className="text-muted-foreground mt-1">
                Week: {weekStart.toLocaleDateString()} - {weekEnd.toLocaleDateString()}
              </p>
            </div>
            <div className="flex gap-2">
              <Button onClick={openCreateModal} className="rounded-full">
                <PlusIcon size={18} className="mr-2" /> Add Entry
              </Button>
              <Button onClick={exportToCSV} variant="outline" className="rounded-full">
                <DownloadIcon size={18} className="mr-2" /> Export CSV
              </Button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 md:px-8 py-8">
        {/* Modification Requests */}
        {modRequests.length > 0 && (
          <Card className="mb-6 bg-yellow-50 border-yellow-200 rounded-2xl shadow-sm">
            <CardHeader className="border-b border-yellow-200">
              <CardTitle className="text-lg font-serif">Pending Modification Requests ({modRequests.length})</CardTitle>
            </CardHeader>
            <CardContent className="p-4 space-y-3">
              {modRequests.map((req) => (
                <div key={req.id} className="p-4 bg-white rounded-lg border border-yellow-200">
                  <div className="flex justify-between items-start">
                    <div>
                      <p className="font-semibold">{req.staff_name}</p>
                      <p className="text-sm text-muted-foreground">
                        Original: {new Date(req.original_clock_in).toLocaleString()} - {req.original_clock_out ? new Date(req.original_clock_out).toLocaleString() : 'N/A'}
                      </p>
                      <p className="text-sm text-blue-600">
                        Requested: {new Date(req.requested_clock_in).toLocaleString()} - {req.requested_clock_out ? new Date(req.requested_clock_out).toLocaleString() : 'N/A'}
                      </p>
                      <p className="text-sm mt-2"><strong>Reason:</strong> {req.reason}</p>
                    </div>
                    <div className="flex gap-2">
                      <Button size="sm" onClick={() => handleModRequest(req.id, 'approve')} className="bg-green-600 hover:bg-green-700">
                        <CheckIcon size={14} className="mr-1" /> Approve
                      </Button>
                      <Button size="sm" variant="destructive" onClick={() => handleModRequest(req.id, 'reject')}>
                        <XIcon size={14} className="mr-1" /> Reject
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        )}

        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <Card className="bg-gradient-to-br from-primary to-primary/80 text-white rounded-2xl shadow-lg">
            <CardContent className="p-6">
              <p className="text-sm opacity-90 uppercase tracking-wider mb-1">Total Hours (All Time)</p>
              <p className="text-3xl font-serif font-bold">{totalHours.toFixed(1)}h</p>
            </CardContent>
          </Card>
          <Card className="bg-gradient-to-br from-green-500 to-green-600 text-white rounded-2xl shadow-lg">
            <CardContent className="p-6">
              <p className="text-sm opacity-90 uppercase tracking-wider mb-1">Currently Working</p>
              <p className="text-3xl font-serif font-bold">{timeEntries.filter(e => !e.clock_out).length}</p>
            </CardContent>
          </Card>
          <Card className="bg-gradient-to-br from-blue-500 to-blue-600 text-white rounded-2xl shadow-lg">
            <CardContent className="p-6">
              <p className="text-sm opacity-90 uppercase tracking-wider mb-1">Total Staff</p>
              <p className="text-3xl font-serif font-bold">{staff.length}</p>
            </CardContent>
          </Card>
        </div>

        {/* Filters */}
        <Card className="mb-6 bg-white rounded-2xl border border-border/50 shadow-sm">
          <CardContent className="p-6">
            <div className="flex flex-col md:flex-row gap-4">
              <div className="flex-1 relative">
                <SearchIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground" size={20} />
                <Input placeholder="Search by staff name..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} className="pl-10" />
              </div>
              <Select value={selectedStaff} onValueChange={setSelectedStaff}>
                <SelectTrigger className="w-[200px]"><SelectValue placeholder="Filter by staff" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Staff</SelectItem>
                  {staff.map((s) => (
                    <SelectItem key={s.id} value={s.id}>{s.full_name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        {/* Time Entries by Staff */}
        {Object.keys(entriesByStaff).length === 0 ? (
          <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
            <CardContent className="p-12 text-center">
              <ClockIcon size={48} className="mx-auto text-muted-foreground/50 mb-4" />
              <p className="text-muted-foreground">No timesheet entries found</p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-6">
            {Object.entries(entriesByStaff).map(([staffId, entries]) => {
              const staffMember = staff.find(s => s.id === staffId);
              const weeklyHours = calculateWeeklyTotal(staffId);
              const isWorking = entries.some(e => !e.clock_out);

              return (
                <Card key={staffId} className="bg-white rounded-2xl border border-border/50 shadow-sm">
                  <CardHeader className="border-b border-border/40">
                    <div className="flex justify-between items-center">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
                          <UserIcon className="text-primary" size={20} />
                        </div>
                        <div>
                          <CardTitle className="text-xl font-serif">{staffMember?.full_name || 'Unknown'}</CardTitle>
                          <p className="text-sm text-muted-foreground">{staffMember?.email}</p>
                        </div>
                        {isWorking && <Badge className="bg-green-100 text-green-800">Working Now</Badge>}
                      </div>
                      <div className="text-right">
                        <p className="text-sm text-muted-foreground">This Week (Mon-Sun)</p>
                        <p className="text-2xl font-serif font-bold text-primary">{weeklyHours}h</p>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent className="p-6">
                    <div className="space-y-3">
                      {entries.slice(0, 10).map((entry) => (
                        <div key={entry.id} className={`p-4 rounded-xl border flex justify-between items-center ${!entry.clock_out ? 'bg-green-50 border-green-200' : 'bg-muted/30 border-border'}`}>
                          <div>
                            <p className="font-semibold mb-1">{new Date(entry.clock_in).toLocaleDateString()}</p>
                            <div className="grid grid-cols-2 gap-4 text-sm text-muted-foreground">
                              <span>In: {new Date(entry.clock_in).toLocaleTimeString()}</span>
                              <span>Out: {entry.clock_out ? new Date(entry.clock_out).toLocaleTimeString() : 'In Progress'}</span>
                            </div>
                            {entry.notes && <p className="text-xs text-muted-foreground mt-1">Note: {entry.notes}</p>}
                          </div>
                          <div className="flex items-center gap-3">
                            <p className={`text-xl font-serif font-bold ${!entry.clock_out ? 'text-green-600' : ''}`}>
                              {calculateHours(entry.clock_in, entry.clock_out)}
                            </p>
                            <Button size="sm" variant="ghost" onClick={() => openEditModal(entry)}>
                              <EditIcon size={14} />
                            </Button>
                            <Button size="sm" variant="ghost" className="text-red-600" onClick={() => handleDelete(entry.id)}>
                              <TrashIcon size={14} />
                            </Button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
      </main>

      {/* Create/Edit Modal */}
      <Dialog open={modalOpen} onOpenChange={setModalOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>{editMode ? 'Edit Time Entry' : 'Create Time Entry'}</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="space-y-4">
            {!editMode && (
              <div>
                <Label>Staff Member</Label>
                <Select value={formData.staff_id} onValueChange={(v) => setFormData({ ...formData, staff_id: v })}>
                  <SelectTrigger><SelectValue placeholder="Select staff" /></SelectTrigger>
                  <SelectContent>
                    {staff.map((s) => (
                      <SelectItem key={s.id} value={s.id}>{s.full_name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}
            <div>
              <Label>Clock In</Label>
              <Input type="datetime-local" value={formData.clock_in} onChange={(e) => setFormData({ ...formData, clock_in: e.target.value })} required />
            </div>
            <div>
              <Label>Clock Out</Label>
              <Input type="datetime-local" value={formData.clock_out} onChange={(e) => setFormData({ ...formData, clock_out: e.target.value })} />
            </div>
            <div>
              <Label>Notes</Label>
              <textarea value={formData.notes} onChange={(e) => setFormData({ ...formData, notes: e.target.value })} className="w-full p-2 border rounded-lg" rows={2} />
            </div>
            <div className="flex gap-3 pt-4">
              <Button type="button" variant="outline" onClick={() => setModalOpen(false)} className="flex-1">Cancel</Button>
              <Button type="submit" className="flex-1">{editMode ? 'Update' : 'Create'}</Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default AdminTimesheetPage;
