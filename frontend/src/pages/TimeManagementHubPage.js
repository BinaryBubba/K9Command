import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { toast } from 'sonner';
import { ArrowLeftIcon } from 'lucide-react';
import api from '../utils/api';

export default function TimeManagementHubPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const currentTab = searchParams.get('tab') || 'overview';

  const [loading, setLoading] = useState(true);
  const [timeEntries, setTimeEntries] = useState([]);
  const [timeModRequests, setTimeModRequests] = useState([]);
  const [ptoRequests, setPtoRequests] = useState([]);
  const [ptoPolicies, setPtoPolicies] = useState([]);
  const [shifts, setShifts] = useState([]);
  const [staff, setStaff] = useState([]);
  const [swapRequests, setSwapRequests] = useState([]);
  const [locations, setLocations] = useState([]);

  const [searchTerm, setSearchTerm] = useState('');
  const [requestStatusFilter, setRequestStatusFilter] = useState('all');

  const [showTimeEntryModal, setShowTimeEntryModal] = useState(false);
  const [editingTimeEntry, setEditingTimeEntry] = useState(null);
  const [timeEntryForm, setTimeEntryForm] = useState({
    staff_id: '',
    clock_in: '',
    clock_out: '',
    location_id: '',
    notes: '',
  });

  const [showPtoModal, setShowPtoModal] = useState(false);
  const [editingPto, setEditingPto] = useState(null);
  const [ptoForm, setPtoForm] = useState({
    staff_id: '',
    start_date: '',
    end_date: '',
    reason: '',
    status: 'pending',
    review_notes: '',
  });

  const [showShiftModal, setShowShiftModal] = useState(false);
  const [editingShift, setEditingShift] = useState(null);
  const [shiftForm, setShiftForm] = useState({
    staff_id: '',
    location_id: '',
    start_time: '',
    end_time: '',
    notes: '',
  });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [entriesRes, modRes, ptoReqRes, ptoPolRes, shiftsRes, staffRes, swapRes, locationsRes] = await Promise.all([
        api.get('/time-entries').catch(() => ({ data: [] })),
        api.get('/time-entries/modification-requests').catch(() => ({ data: [] })),
        api.get('/hr/time-off-requests').catch(() => ({ data: [] })),
        api.get('/hr/time-off-policies').catch(() => ({ data: [] })),
        api.get('/scheduling/shifts').catch(() => ({ data: [] })),
        api.get('/admin/users?role=staff').catch(() => ({ data: [] })),
        api.get('/scheduling/swap-requests').catch(() => ({ data: [] })),
        api.get('/locations').catch(() => ({ data: [] })),
      ]);

      setTimeEntries(entriesRes.data || []);
      setTimeModRequests(modRes.data || []);
      setPtoRequests(ptoReqRes.data || []);
      setPtoPolicies(ptoPolRes.data || []);
      setShifts(shiftsRes.data || []);
      setStaff((staffRes.data || []).filter((s) => (s.role === 'staff' || s.role === 'admin') && s.is_active !== false));
      setSwapRequests(swapRes.data || []);
      setLocations(locationsRes.data || []);
    } catch (error) {
      console.error('Failed to load time management hub:', error);
      toast.error('Failed to load time management hub');
    } finally {
      setLoading(false);
    }
  };

  const summary = useMemo(() => {
    const clockedInNow = timeEntries.filter(e => e.clock_in && !e.clock_out).length;
    const pendingPto = ptoRequests.filter(r => String(r.status).toLowerCase() === 'pending').length;
    const pendingMods = timeModRequests.filter(r => String(r.status).toLowerCase() === 'pending').length;
    const pendingSwaps = swapRequests.filter(r => String(r.status).toLowerCase() === 'pending').length;

    return { clockedInNow, pendingPto, pendingMods, pendingSwaps };
  }, [timeEntries, ptoRequests, timeModRequests, swapRequests]);

  const filteredPtoRequests = useMemo(() => {
    return ptoRequests.filter((r) => {
      const person = String(r.staff_name || r.employee_name || r.user_name || r.staff_id || '').toLowerCase();
      const status = String(r.status || '').toLowerCase();
      const searchOk = !searchTerm || person.includes(searchTerm.toLowerCase());
      const statusOk = requestStatusFilter === 'all' || status === requestStatusFilter;
      return searchOk && statusOk;
    });
  }, [ptoRequests, searchTerm, requestStatusFilter]);

  const filteredTimeModRequests = useMemo(() => {
    return timeModRequests.filter((r) => {
      const person = String(r.staff_name || r.staff_id || '').toLowerCase();
      const status = String(r.status || '').toLowerCase();
      const searchOk = !searchTerm || person.includes(searchTerm.toLowerCase());
      const statusOk = requestStatusFilter === 'all' || status === requestStatusFilter;
      return searchOk && statusOk;
    });
  }, [timeModRequests, searchTerm, requestStatusFilter]);

  const filteredSwapRequests = useMemo(() => {
    return swapRequests.filter((r) => {
      const person = String(r.staff_name || r.requester_name || r.staff_id || '').toLowerCase();
      const status = String(r.status || '').toLowerCase();
      const searchOk = !searchTerm || person.includes(searchTerm.toLowerCase());
      const statusOk = requestStatusFilter === 'all' || status === requestStatusFilter;
      return searchOk && statusOk;
    });
  }, [swapRequests, searchTerm, requestStatusFilter]);

  const filteredTimeEntries = useMemo(() => {
    return timeEntries.filter((e) => {
      const person = String(e.staff_name || e.staff_id || '').toLowerCase();
      return !searchTerm || person.includes(searchTerm.toLowerCase());
    });
  }, [timeEntries, searchTerm]);

  const filteredShifts = useMemo(() => {
    return shifts.filter((s) => {
      const person = String(s.staff_name || s.staff_id || '').toLowerCase();
      return !searchTerm || person.includes(searchTerm.toLowerCase());
    });
  }, [shifts, searchTerm]);

  const staffOptions = useMemo(() => {
    return (staff || []).map((s) => ({
      id: s.id,
      label: s.full_name || s.name || s.email || 'Unknown Staff',
      name: s.full_name || s.name || s.email || 'Unknown Staff',
      full_name: s.full_name || s.name || '',
      email: s.email || '',
    }));
  }, [staff]);

  const openCreateTimeEntry = () => {
    setEditingTimeEntry(null);
    setTimeEntryForm({
      staff_id: staffOptions[0]?.id || '',
      clock_in: '',
      clock_out: '',
      location_id: '',
      notes: '',
    });
    setShowTimeEntryModal(true);
  };

  const openEditTimeEntry = (entry) => {
    const toLocal = (value) => {
      if (!value) return '';
      const d = new Date(value);
      const pad = (n) => String(n).padStart(2, '0');
      return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
    };

    setEditingTimeEntry(entry);
    setTimeEntryForm({
      staff_id: entry.staff_id || '',
      clock_in: toLocal(entry.clock_in),
      clock_out: toLocal(entry.clock_out),
      location_id: entry.location_id || '',
      notes: entry.notes || '',
    });
    setShowTimeEntryModal(true);
  };

  const handleSaveTimeEntry = async () => {
    try {
      const payload = {
        staff_id: timeEntryForm.staff_id,
        clock_in: timeEntryForm.clock_in ? new Date(timeEntryForm.clock_in).toISOString() : null,
        clock_out: timeEntryForm.clock_out ? new Date(timeEntryForm.clock_out).toISOString() : null,
        location_id: timeEntryForm.location_id || undefined,
        notes: timeEntryForm.notes || '',
      };

      if (!payload.staff_id || !payload.clock_in) {
        toast.error('Staff and clock-in are required');
        return;
      }

      if (editingTimeEntry?.id) {
        await api.patch(`/time-entries/${editingTimeEntry.id}`, payload);
        toast.success('Time entry updated');
      } else {
        await api.post('/time-entries', payload);
        toast.success('Time entry created');
      }

      setShowTimeEntryModal(false);
      setEditingTimeEntry(null);
      await loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save time entry');
    }
  };

  const handleDeleteTimeEntry = async (entry) => {
    try {
      await api.delete(`/time-entries/${entry.id}`);
      toast.success('Time entry deleted');
      await loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to delete time entry');
    }
  };

  const openCreatePtoRequest = () => {
    setEditingPto(null);
    setPtoForm({
      staff_id: staffOptions[0]?.id || '',
      start_date: '',
      end_date: '',
      reason: '',
      status: 'pending',
      review_notes: '',
    });
    setShowPtoModal(true);
  };

  const openEditPtoRequest = (req) => {
    setEditingPto(req);
    setPtoForm({
      staff_id: req.staff_id || '',
      start_date: req.start_date ? String(req.start_date).slice(0, 10) : '',
      end_date: req.end_date ? String(req.end_date).slice(0, 10) : '',
      reason: req.reason || '',
      status: req.status || 'pending',
      review_notes: req.review_notes || '',
    });
    setShowPtoModal(true);
  };

  const handleSavePtoRequest = async () => {
    try {
      if (!ptoForm.staff_id || !ptoForm.start_date || !ptoForm.end_date) {
        toast.error('Staff, start date, and end date are required');
        return;
      }

      const payload = {
        staff_id: ptoForm.staff_id,
        start_date: ptoForm.start_date,
        end_date: ptoForm.end_date,
        reason: ptoForm.reason || '',
        status: ptoForm.status || 'pending',
        review_notes: ptoForm.review_notes || '',
      };

      if (editingPto?.id) {
        await api.patch(`/hr/time-off-requests/${editingPto.id}`, payload);
        toast.success('PTO request updated');
      } else {
        await api.post('/hr/time-off-requests', payload);
        toast.success('PTO request created');
      }

      setShowPtoModal(false);
      setEditingPto(null);
      setPtoForm({
        staff_id: staffOptions[0]?.id || '',
        start_date: '',
        end_date: '',
        reason: '',
        status: 'pending',
        review_notes: '',
      });
      await loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save PTO request');
    }
  };

  const handleDeletePtoRequest = async (req) => {
    try {
      await api.delete(`/hr/time-off-requests/${req.id}`);
      toast.success('PTO request deleted');
      await loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to delete PTO request');
    }
  };

  const toLocalDateTime = (value) => {
    if (!value) return '';
    const d = new Date(value);
    const pad = (n) => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  };

  const openCreateShift = () => {
    setEditingShift(null);
    setShiftForm({
      staff_id: staffOptions[0]?.id || '',
      location_id: '',
      start_time: '',
      end_time: '',
      notes: '',
    });
    setShowShiftModal(true);
  };

  const openEditShift = (shift) => {
    setEditingShift(shift);
    setShiftForm({
      staff_id: shift.staff_id || '',
      location_id: shift.location_id || '',
      start_time: toLocalDateTime(shift.start_time || shift.start),
      end_time: toLocalDateTime(shift.end_time || shift.end),
      notes: shift.notes || '',
    });
    setShowShiftModal(true);
  };

  const handleSaveShift = async () => {
    try {
      if (!shiftForm.staff_id || !shiftForm.location_id || !shiftForm.start_time || !shiftForm.end_time) {
        toast.error('Staff, location, start time, and end time are required');
        return;
      }

      const payload = {
        staff_id: shiftForm.staff_id,
        location_id: shiftForm.location_id,
        start_time: new Date(shiftForm.start_time).toISOString(),
        end_time: new Date(shiftForm.end_time).toISOString(),
        notes: shiftForm.notes || '',
      };

      if (editingShift?.id) {
        await api.patch(`/scheduling/shifts/${editingShift.id}`, payload);
        toast.success('Shift updated');
      } else {
        await api.post('/scheduling/shifts', payload);
        toast.success('Shift created');
      }

      setShowShiftModal(false);
      setEditingShift(null);
      await loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save shift');
    }
  };

  const handleDeleteShift = async (shift) => {
    try {
      await api.delete(`/scheduling/shifts/${shift.id}`);
      toast.success('Shift deleted');
      await loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to delete shift');
    }
  };

  if (loading) {
    return (
      <div className="p-6 bg-slate-950 min-h-screen text-white">
        <div className="text-slate-400">Loading time management hub...</div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6 bg-slate-950 min-h-screen text-white">
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-3">
          <Button variant="outline" type="button" onClick={() => navigate('/admin/dashboard')}>
            <ArrowLeftIcon size={16} className="mr-2" />
            Back
          </Button>
          <div>
            <h1 className="text-2xl font-bold">Time Management</h1>
            <p className="text-slate-400">Scheduling, PTO, time entries, approvals</p>
          </div>
        </div>
        <div className="flex gap-2 flex-wrap w-full md:w-auto">
          <Button variant="outline" type="button" onClick={() => navigate('/admin/dashboard')}>
            Legacy Time Management
          </Button>
          <Button variant="outline" onClick={() => navigate('/admin/timesheet')}>
            Timesheets
          </Button>
          <Button variant="outline" onClick={() => navigate('/admin/schedule')}>
            Schedule
          </Button>
          <Button onClick={openCreateShift}>
            New Shift
          </Button>
          <Button onClick={openCreateTimeEntry}>
            New Time Entry
          </Button>
          <Button onClick={openCreatePtoRequest}>
            New PTO Request
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card><CardContent className="p-4"><div className="text-sm text-slate-400">Clocked In Now</div><div className="text-2xl font-bold">{summary.clockedInNow}</div></CardContent></Card>
        <Card><CardContent className="p-4"><div className="text-sm text-slate-400">Pending PTO</div><div className="text-2xl font-bold">{summary.pendingPto}</div></CardContent></Card>
        <Card><CardContent className="p-4"><div className="text-sm text-slate-400">Pending Time Mods</div><div className="text-2xl font-bold">{summary.pendingMods}</div></CardContent></Card>
        <Card><CardContent className="p-4"><div className="text-sm text-slate-400">Pending Swaps</div><div className="text-2xl font-bold">{summary.pendingSwaps}</div></CardContent></Card>
      </div>

      <Card>
        <CardContent className="p-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label>Search staff</Label>
              <Input
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search by name or staff id"
                className="mt-1"
              />
            </div>
            <div>
              <Label>Request status</Label>
              <Select value={requestStatusFilter} onValueChange={setRequestStatusFilter}>
                <SelectTrigger className="mt-1">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All statuses</SelectItem>
                  <SelectItem value="pending">Pending</SelectItem>
                  <SelectItem value="approved">Approved</SelectItem>
                  <SelectItem value="rejected">Rejected</SelectItem>
                  <SelectItem value="denied">Denied</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-4">
          <div className="flex gap-2 flex-wrap">
            <Button onClick={openCreateShift}>
              Create Shift
            </Button>
            <Button onClick={openCreateTimeEntry}>
              Create Time Entry
            </Button>
            <Button onClick={openCreatePtoRequest}>
              Create PTO Request
            </Button>
          </div>
        </CardContent>
      </Card>

      <Tabs value={currentTab} onValueChange={(tab) => setSearchParams({ tab })}>
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="scheduling">Scheduling</TabsTrigger>
          <TabsTrigger value="time-entries">Time Entries</TabsTrigger>
          <TabsTrigger value="time-off">Time Off</TabsTrigger>
          <TabsTrigger value="pay-periods">Pay Periods</TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
            <Card>
              <CardHeader><CardTitle>Active Clock-Ins</CardTitle></CardHeader>
              <CardContent className="space-y-3">
                {filteredTimeEntries
                  .filter(e => e.clock_in && !e.clock_out)
                  .slice(0, 10)
                  .map((entry) => (
                    <div key={entry.id} className="border border-slate-800 rounded-lg p-3">
                      <div className="font-medium">{entry.staff_name || entry.staff_id || 'Unknown staff'}</div>
                      <div className="text-sm text-slate-400">
                        Clocked in: {entry.clock_in ? new Date(entry.clock_in).toLocaleString() : 'Unknown'}
                      </div>
                    </div>
                  ))}
                {filteredTimeEntries.filter(e => e.clock_in && !e.clock_out).length === 0 && (
                  <div className="text-slate-400">Nobody is currently clocked in.</div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader><CardTitle>Pending PTO Requests</CardTitle></CardHeader>
              <CardContent className="space-y-3">
                {filteredPtoRequests
                  .filter(r => String(r.status).toLowerCase() === 'pending')
                  .slice(0, 10)
                  .map((req) => (
                    <div key={req.id} className="border border-slate-800 rounded-lg p-3">
                      <div className="font-medium">{req.staff_name || req.employee_name || req.user_name || req.staff_id || 'Unknown staff'}</div>
                      <div className="text-sm text-slate-400">
                        {req.start_date ? new Date(req.start_date).toLocaleDateString() : 'Unknown start'}
                        {req.end_date ? ` → ${new Date(req.end_date).toLocaleDateString()}` : ''}
                      </div>
                    </div>
                  ))}
                {filteredPtoRequests.filter(r => String(r.status).toLowerCase() === 'pending').length === 0 && (
                  <div className="text-slate-400">No pending PTO requests.</div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader><CardTitle>Pending Time Modifications</CardTitle></CardHeader>
              <CardContent className="space-y-3">
                {filteredTimeModRequests
                  .filter(r => String(r.status).toLowerCase() === 'pending')
                  .slice(0, 10)
                  .map((req) => (
                    <div key={req.id} className="border border-slate-800 rounded-lg p-3">
                      <div className="font-medium">{req.staff_name || req.staff_id || 'Unknown staff'}</div>
                      <div className="text-sm text-slate-400">
                        Requested: {req.requested_clock_in ? new Date(req.requested_clock_in).toLocaleString() : 'Unknown'}
                      </div>
                    </div>
                  ))}
                {filteredTimeModRequests.filter(r => String(r.status).toLowerCase() === 'pending').length === 0 && (
                  <div className="text-slate-400">No pending time modifications.</div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="scheduling">
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between gap-3 flex-wrap">
                  <CardTitle>Upcoming Shifts</CardTitle>
                  <div className="flex gap-2 flex-wrap">
                    <Button onClick={openCreateShift}>
                      Create Shift
                    </Button>
                    <Button variant="outline" onClick={() => navigate('/admin/schedule')}>
                      Legacy Schedule
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                {filteredShifts
                  .slice()
                  .sort((a, b) => new Date(a.start_time || a.start || 0) - new Date(b.start_time || b.start || 0))
                  .slice(0, 10)
                  .map((shift) => (
                    <div key={shift.id} className="border border-slate-800 rounded-lg p-3">
                      <div className="flex items-start justify-between gap-3 flex-wrap">
                        <div>
                          <div className="font-medium">{shift.staff_name || shift.staff_id || 'Unknown staff'}</div>
                          <div className="text-sm text-slate-400">
                            {shift.start_time || shift.start ? new Date(shift.start_time || shift.start).toLocaleString() : 'Unknown start'}
                            {shift.end_time ? ` • End: ${new Date(shift.end_time).toLocaleString()}` : ''}
                          </div>
                        </div>
                        <div className="flex gap-2">
                          <Button variant="outline" onClick={() => openEditShift(shift)}>
                            Edit
                          </Button>
                          <Button variant="outline" onClick={() => handleDeleteShift(shift)}>
                            Delete
                          </Button>
                        </div>
                      </div>
                    </div>
                  ))}
                {filteredShifts.length === 0 && (
                  <div className="text-slate-400">No shifts loaded.</div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader><CardTitle>Swap Requests</CardTitle></CardHeader>
              <CardContent className="space-y-3">
                {filteredSwapRequests
                  .slice(0, 10)
                  .map((swap) => (
                    <div key={swap.id} className="border border-slate-800 rounded-lg p-3">
                      <div className="font-medium">{swap.staff_name || swap.requester_name || swap.staff_id || 'Unknown staff'}</div>
                      <div className="text-sm text-slate-400">
                        Status: {swap.status || 'unknown'}
                      </div>
                    </div>
                  ))}
                {filteredSwapRequests.length === 0 && (
                  <div className="text-slate-400">No swap requests loaded.</div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="time-entries">
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between gap-3 flex-wrap">
                  <CardTitle>Recent Time Entries</CardTitle>
                  <Button onClick={openCreateTimeEntry}>
                    Create Time Entry
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                {filteredTimeEntries
                  .slice()
                  .sort((a, b) => new Date(b.clock_in || 0) - new Date(a.clock_in || 0))
                  .slice(0, 12)
                  .map((entry) => (
                    <div key={entry.id} className="border border-slate-800 rounded-lg p-3">
                      <div className="flex items-start justify-between gap-3 flex-wrap">
                        <div>
                          <div className="font-medium">{entry.staff_name || entry.staff_id || 'Unknown staff'}</div>
                          <div className="text-sm text-slate-400">
                            In: {entry.clock_in ? new Date(entry.clock_in).toLocaleString() : 'Unknown'}
                            {entry.clock_out ? ` • Out: ${new Date(entry.clock_out).toLocaleString()}` : ' • Still clocked in'}
                          </div>
                        </div>
                        <div className="flex gap-2">
                          <Button variant="outline" onClick={() => openEditTimeEntry(entry)}>
                            Edit
                          </Button>
                          <Button variant="outline" onClick={() => handleDeleteTimeEntry(entry)}>
                            Delete
                          </Button>
                        </div>
                      </div>
                    </div>
                  ))}
                {filteredTimeEntries.length === 0 && (
                  <div className="text-slate-400">No time entries loaded.</div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader><CardTitle>Modification Requests</CardTitle></CardHeader>
              <CardContent className="space-y-3">
                {filteredTimeModRequests
                  .slice()
                  .sort((a, b) => new Date(b.created_at || b.requested_at || 0) - new Date(a.created_at || a.requested_at || 0))
                  .slice(0, 12)
                  .map((req) => (
                    <div key={req.id} className="border border-slate-800 rounded-lg p-3">
                      <div className="font-medium">{req.staff_name || req.staff_id || 'Unknown staff'}</div>
                      <div className="text-sm text-slate-400">
                        Status: {req.status || 'unknown'}
                      </div>
                    </div>
                  ))}
                {filteredTimeModRequests.length === 0 && (
                  <div className="text-slate-400">No time modification requests loaded.</div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="time-off">
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between gap-3 flex-wrap">
                  <CardTitle>PTO Requests</CardTitle>
                  <Button onClick={openCreatePtoRequest}>
                    Create PTO Request
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                {filteredPtoRequests
                  .slice()
                  .sort((a, b) => new Date(b.created_at || b.requested_at || 0) - new Date(a.created_at || a.requested_at || 0))
                  .slice(0, 12)
                  .map((req) => (
                    <div key={req.id} className="border border-slate-800 rounded-lg p-3">
                      <div className="flex items-start justify-between gap-3 flex-wrap">
                        <div>
                          <div className="font-medium">{req.staff_name || req.employee_name || req.user_name || req.staff_id || 'Unknown staff'}</div>
                          <div className="text-sm text-slate-400">
                            Status: {req.status || 'unknown'}
                            {req.start_date ? ` • ${new Date(req.start_date).toLocaleDateString()}` : ''}
                            {req.end_date ? ` → ${new Date(req.end_date).toLocaleDateString()}` : ''}
                          </div>
                        </div>
                        <div className="flex gap-2">
                          <Button variant="outline" onClick={() => openEditPtoRequest(req)}>
                            Edit
                          </Button>
                          <Button variant="outline" onClick={() => handleDeletePtoRequest(req)}>
                            Delete
                          </Button>
                        </div>
                      </div>
                    </div>
                  ))}
                {filteredPtoRequests.length === 0 && (
                  <div className="text-slate-400">No PTO requests loaded.</div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader><CardTitle>PTO Policies</CardTitle></CardHeader>
              <CardContent className="space-y-3">
                {ptoPolicies.slice(0, 12).map((policy, idx) => (
                  <div key={policy.id || idx} className="border border-slate-800 rounded-lg p-3">
                    <div className="font-medium">{policy.name || policy.title || `Policy ${idx + 1}`}</div>
                    <div className="text-sm text-slate-400">
                      {policy.description || policy.policy_type || 'No description'}
                    </div>
                  </div>
                ))}
                {ptoPolicies.length === 0 && (
                  <div className="text-slate-400">No PTO policies loaded.</div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="pay-periods">
          <Card>
            <CardHeader><CardTitle>Pay Periods & Approvals</CardTitle></CardHeader>
            <CardContent>
              Placeholder for current pay period summary, approval state, and exceptions.
            </CardContent>
          </Card>
        </TabsContent>
      <Dialog open={showShiftModal} onOpenChange={setShowShiftModal}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>{editingShift ? 'Edit Shift' : 'Create Shift'}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>Staff</Label>
              <Select value={shiftForm.staff_id} onValueChange={(value) => setShiftForm({ ...shiftForm, staff_id: value })}>
                <SelectTrigger className="mt-1">
                  <SelectValue placeholder="Select staff" />
                </SelectTrigger>
                <SelectContent>
                  {staffOptions.map((staff) => (
                    <SelectItem key={staff.id} value={staff.id}>{staff.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Location</Label>
              <Select
                value={shiftForm.location_id || "__none__"}
                onValueChange={(value) => setShiftForm({ ...shiftForm, location_id: value === "__none__" ? "" : value })}
              >
                <SelectTrigger className="mt-1">
                  <SelectValue placeholder="Select location" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__none__">No location</SelectItem>
                  {locations.map((loc) => (
                    <SelectItem key={loc.id} value={loc.id}>
                      {loc.name || loc.id}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Start Time</Label>
              <Input
                type="datetime-local"
                value={shiftForm.start_time}
                onChange={(e) => setShiftForm({ ...shiftForm, start_time: e.target.value })}
                className="mt-1"
              />
            </div>
            <div>
              <Label>End Time</Label>
              <Input
                type="datetime-local"
                value={shiftForm.end_time}
                onChange={(e) => setShiftForm({ ...shiftForm, end_time: e.target.value })}
                className="mt-1"
              />
            </div>
            <div>
              <Label>Notes</Label>
              <Input
                value={shiftForm.notes}
                onChange={(e) => setShiftForm({ ...shiftForm, notes: e.target.value })}
                className="mt-1"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowShiftModal(false)}>Cancel</Button>
            <Button onClick={handleSaveShift}>{editingShift ? 'Save Changes' : 'Create Shift'}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={showTimeEntryModal} onOpenChange={setShowTimeEntryModal}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>{editingTimeEntry ? 'Edit Time Entry' : 'Create Time Entry'}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>Staff</Label>
              <Select value={timeEntryForm.staff_id} onValueChange={(value) => setTimeEntryForm({ ...timeEntryForm, staff_id: value })}>
                <SelectTrigger className="mt-1">
                  <SelectValue placeholder="Select staff" />
                </SelectTrigger>
                <SelectContent>
                  {staffOptions.map((staff) => (
                    <SelectItem key={staff.id} value={staff.id}>{staff.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Clock In</Label>
              <Input
                type="datetime-local"
                value={timeEntryForm.clock_in}
                onChange={(e) => setTimeEntryForm({ ...timeEntryForm, clock_in: e.target.value })}
                className="mt-1"
              />
            </div>
            <div>
              <Label>Clock Out</Label>
              <Input
                type="datetime-local"
                value={timeEntryForm.clock_out}
                onChange={(e) => setTimeEntryForm({ ...timeEntryForm, clock_out: e.target.value })}
                className="mt-1"
              />
            </div>
            <div>
              <Label>Location ID</Label>
              <Input
                value={timeEntryForm.location_id}
                onChange={(e) => setTimeEntryForm({ ...timeEntryForm, location_id: e.target.value })}
                className="mt-1"
              />
            </div>
            <div>
              <Label>Notes</Label>
              <Input
                value={timeEntryForm.notes}
                onChange={(e) => setTimeEntryForm({ ...timeEntryForm, notes: e.target.value })}
                className="mt-1"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowTimeEntryModal(false)}>Cancel</Button>
            <Button onClick={handleSaveTimeEntry}>{editingTimeEntry ? 'Save Changes' : 'Create Time Entry'}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={showPtoModal} onOpenChange={setShowPtoModal}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>{editingPto ? 'Edit PTO Request' : 'Create PTO Request'}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>Staff</Label>
              <Select value={ptoForm.staff_id} onValueChange={(value) => setPtoForm({ ...ptoForm, staff_id: value })}>
                <SelectTrigger className="mt-1">
                  <SelectValue placeholder="Select staff" />
                </SelectTrigger>
                <SelectContent>
                  {staffOptions.map((staff) => (
                    <SelectItem key={staff.id} value={staff.id}>{staff.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Start Date</Label>
              <Input
                type="date"
                value={ptoForm.start_date}
                onChange={(e) => setPtoForm({ ...ptoForm, start_date: e.target.value })}
                className="mt-1"
              />
            </div>
            <div>
              <Label>End Date</Label>
              <Input
                type="date"
                value={ptoForm.end_date}
                onChange={(e) => setPtoForm({ ...ptoForm, end_date: e.target.value })}
                className="mt-1"
              />
            </div>
            <div>
              <Label>Reason</Label>
              <Input
                value={ptoForm.reason}
                onChange={(e) => setPtoForm({ ...ptoForm, reason: e.target.value })}
                className="mt-1"
              />
            </div>
            <div>
              <Label>Status</Label>
              <Select value={ptoForm.status} onValueChange={(value) => setPtoForm({ ...ptoForm, status: value })}>
                <SelectTrigger className="mt-1">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="pending">Pending</SelectItem>
                  <SelectItem value="approved">Approved</SelectItem>
                  <SelectItem value="rejected">Rejected</SelectItem>
                  <SelectItem value="denied">Denied</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Review Notes</Label>
              <Input
                value={ptoForm.review_notes}
                onChange={(e) => setPtoForm({ ...ptoForm, review_notes: e.target.value })}
                className="mt-1"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowPtoModal(false)}>Cancel</Button>
            <Button onClick={handleSavePtoRequest}>{editingPto ? 'Save Changes' : 'Create PTO Request'}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      </Tabs>
    </div>
  );
}
