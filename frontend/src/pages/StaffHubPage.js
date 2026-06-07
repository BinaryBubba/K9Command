import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Label } from '../components/ui/label';
import { toast } from 'sonner';
import {
  ArrowLeftIcon,
  SearchIcon,
  UserIcon
} from 'lucide-react';
import api from '../utils/api';

export default function StaffHubPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const currentTab = searchParams.get('tab') || 'directory';

  const [loading, setLoading] = useState(true);
  const [staff, setStaff] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [timeEntries, setTimeEntries] = useState([]);
  const [timeModRequests, setTimeModRequests] = useState([]);
  const [ptoRequests, setPtoRequests] = useState([]);
  const [shifts, setShifts] = useState([]);
  const [swapRequests, setSwapRequests] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [locations, setLocations] = useState([]);

  const [searchTerm, setSearchTerm] = useState('');
  const [locationFilter, setLocationFilter] = useState('all');
  const [selectedStaff, setSelectedStaff] = useState(null);
  const [staffActionLoading, setStaffActionLoading] = useState(null);

  const [showStaffModal, setShowStaffModal] = useState(false);
  const [editingStaff, setEditingStaff] = useState(null);
  const [staffForm, setStaffForm] = useState({
    full_name: '',
    email: '',
    phone: '',
    location_id: '',
    password: '',
    is_active: true,
  });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [
        staffRes,
        tasksRes,
        timeEntriesRes,
        timeModReqRes,
        ptoReqRes,
        shiftsRes,
        swapReqRes,
        auditRes,
        locationsRes
      ] = await Promise.all([
        api.get('/admin/users?role=staff').catch(() => ({ data: [] })),
        api.get('/tasks').catch(() => ({ data: [] })),
        api.get('/time-entries').catch(() => ({ data: [] })),
        api.get('/time-entries/modification-requests').catch(() => ({ data: [] })),
        api.get('/hr/time-off-requests').catch(() => ({ data: [] })),
        api.get('/scheduling/shifts').catch(() => ({ data: [] })),
        api.get('/scheduling/swap-requests').catch(() => ({ data: [] })),
        api.get('/audit-logs').catch(() => ({ data: [] })),
        api.get('/locations').catch(() => ({ data: [] })),
      ]);

      setStaff(staffRes.data || []);
      setTasks(tasksRes.data || []);
      setTimeEntries(timeEntriesRes.data || []);
      setTimeModRequests(timeModReqRes.data || []);
      setPtoRequests(ptoReqRes.data || []);
      setShifts(shiftsRes.data || []);
      setSwapRequests(swapReqRes.data || []);
      setAuditLogs(auditRes.data || []);
      setLocations(locationsRes.data || []);
    } catch (error) {
      console.error('Failed to load staff hub data:', error);
      toast.error('Failed to load staff hub');
    } finally {
      setLoading(false);
    }
  };

  const locationOptions = useMemo(() => {
    const values = [...new Set(staff.map(s => s.location_id).filter(Boolean))];
    return values;
  }, [staff]);

  const staffRows = useMemo(() => {
    return staff.map((person) => {
      const personTasks = tasks.filter(t => t.assigned_to === person.id);
      const openTasks = personTasks.filter(t => t.status !== 'completed');
      const overdueTasks = openTasks.filter(t => t.due_date && new Date(t.due_date) < new Date());
      const pendingPto = ptoRequests.filter(r => r.staff_id === person.id && String(r.status).toLowerCase() === 'pending');
      const pendingTimeMods = timeModRequests.filter(r => r.staff_id === person.id && String(r.status).toLowerCase() === 'pending');

      const currentEntry = timeEntries.find(
        e => e.staff_id === person.id && e.clock_in && !e.clock_out
      );

      const recentAudit = auditLogs
        .filter(a => a.user_id === person.id || a.staff_id === person.id)
        .sort((a, b) => new Date(b.created_at || b.timestamp || 0) - new Date(a.created_at || a.timestamp || 0))[0];

      return {
        ...person,
        clocked_in_now: !!currentEntry,
        open_task_count: openTasks.length,
        overdue_task_count: overdueTasks.length,
        pending_pto_count: pendingPto.length,
        pending_time_mod_count: pendingTimeMods.length,
        recent_activity_at: recentAudit?.created_at || recentAudit?.timestamp || null,
      };
    });
  }, [staff, tasks, ptoRequests, timeModRequests, timeEntries, auditLogs]);

  const filteredStaff = useMemo(() => {
    return staffRows.filter((s) => {
      const matchesSearch =
        !searchTerm ||
        s.full_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        s.email?.toLowerCase().includes(searchTerm.toLowerCase());

      const matchesLocation =
        locationFilter === 'all' || s.location_id === locationFilter;

      return matchesSearch && matchesLocation;
    });
  }, [staffRows, searchTerm, locationFilter]);

  const summary = useMemo(() => {
    return {
      activeStaff: staffRows.filter(s => s.is_active !== false).length,
      clockedInNow: staffRows.filter(s => s.clocked_in_now).length,
      overdueTasks: staffRows.reduce((n, s) => n + s.overdue_task_count, 0),
      pendingPto: staffRows.reduce((n, s) => n + s.pending_pto_count, 0),
    };
  }, [staffRows]);

  const handleToggleStaffStatus = async (person) => {
    const nextStatus = person.is_active === false ? 'active' : 'inactive';
    try {
      setStaffActionLoading(person.id);
      await api.patch(`/admin/users/${person.id}/status?status=${nextStatus}`);
      toast.success(`Staff ${nextStatus === 'active' ? 'reactivated' : 'deactivated'}`);
      await loadData();
      setSelectedStaff((prev) => (
        prev?.id === person.id
          ? { ...prev, is_active: nextStatus === 'active' }
          : prev
      ));
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update staff status');
    } finally {
      setStaffActionLoading(null);
    }
  };

  const openCreateStaff = () => {
    setEditingStaff(null);
    setStaffForm({
      full_name: '',
      email: '',
      phone: '',
      location_id: '',
      password: '',
      is_active: true,
    });
    setShowStaffModal(true);
  };

  const openEditStaff = (person) => {
    setEditingStaff(person);
    setStaffForm({
      full_name: person.full_name || '',
      email: person.email || '',
      phone: person.phone || '',
      location_id: person.location_id || '',
      password: '',
      is_active: person.is_active !== false,
    });
    setShowStaffModal(true);
  };

  const handleSaveStaff = async () => {
    try {
      if (!staffForm.full_name.trim() || !staffForm.email.trim()) {
        toast.error('Full name and email are required');
        return;
      }

      if (!editingStaff && !staffForm.password) {
        toast.error('Password is required for new staff');
        return;
      }

      const payload = {
        full_name: staffForm.full_name,
        email: staffForm.email,
        phone: staffForm.phone || null,
        location_id: staffForm.location_id || null,
        is_active: !!staffForm.is_active,
      };

      if (staffForm.password) {
        payload.password = staffForm.password;
      }

      if (editingStaff?.id) {
        await api.patch(`/admin/users/${editingStaff.id}`, payload);
        toast.success('Staff updated');
      } else {
        await api.post('/admin/users/staff', payload);
        toast.success('Staff created');
      }

      setShowStaffModal(false);
      setEditingStaff(null);
      await loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save staff');
    }
  };

  const activityItems = useMemo(() => {
    const auditItems = (auditLogs || []).map((a) => ({
      id: `audit-${a.id || Math.random()}`,
      type: 'audit',
      staff_name: a.user_name || a.staff_name || 'Unknown',
      summary: a.action || a.event || 'Audit event',
      timestamp: a.created_at || a.timestamp,
    }));

    const ptoItems = (ptoRequests || []).map((r) => ({
      id: `pto-${r.id}`,
      type: 'pto',
      staff_name: r.staff_name || r.employee_name || r.user_name || 'Unknown',
      summary: `PTO request: ${r.status || 'unknown'}`,
      timestamp: r.created_at || r.requested_at,
    }));

    const timeModItems = (timeModRequests || []).map((r) => ({
      id: `timemod-${r.id}`,
      type: 'time_mod',
      staff_name: r.staff_name || 'Unknown',
      summary: `Time modification: ${r.status || 'unknown'}`,
      timestamp: r.created_at || r.requested_at,
    }));

    return [...auditItems, ...ptoItems, ...timeModItems]
      .filter(x => x.timestamp)
      .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
      .slice(0, 50);
  }, [auditLogs, ptoRequests, timeModRequests]);

  if (loading) {
    return (
      <div className="p-6 bg-slate-950 min-h-screen text-white">
        <div className="text-slate-400">Loading staff hub...</div>
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
            <h1 className="text-2xl font-bold">Staff Hub</h1>
            <p className="text-slate-400">Directory, assignments, and recent workforce activity</p>
          </div>
        </div>
        <div className="flex gap-2 flex-wrap w-full md:w-auto">
          <Button onClick={openCreateStaff}>
            New Staff
          </Button>
          <Button variant="outline" type="button" onClick={() => navigate('/admin/dashboard')}>
            Legacy Staff Page
          </Button>
          <Button variant="outline" onClick={() => navigate('/admin/staff-management')}>
            Staff Requests
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card><CardContent className="p-4"><div className="text-slate-400 text-sm">Active Staff</div><div className="text-2xl font-bold">{summary.activeStaff}</div></CardContent></Card>
        <Card><CardContent className="p-4"><div className="text-slate-400 text-sm">Clocked In Now</div><div className="text-2xl font-bold">{summary.clockedInNow}</div></CardContent></Card>
        <Card><CardContent className="p-4"><div className="text-slate-400 text-sm">Overdue Tasks</div><div className="text-2xl font-bold">{summary.overdueTasks}</div></CardContent></Card>
        <Card><CardContent className="p-4"><div className="text-slate-400 text-sm">Pending PTO</div><div className="text-2xl font-bold">{summary.pendingPto}</div></CardContent></Card>
      </div>

      <Tabs value={currentTab} onValueChange={(tab) => setSearchParams({ tab })}>
        <TabsList>
          <TabsTrigger value="directory">Directory</TabsTrigger>
          <TabsTrigger value="assignments">Assignments</TabsTrigger>
          <TabsTrigger value="activity">Activity</TabsTrigger>
        </TabsList>

        <TabsContent value="directory" className="space-y-4">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between gap-3 flex-wrap">
                <CardTitle>Staff Directory</CardTitle>
                <Button onClick={openCreateStaff}>
                  Create Staff
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex gap-3 flex-col md:flex-row">
                <div className="flex-1">
                  <Label>Search</Label>
                  <div className="relative">
                    <SearchIcon size={16} className="absolute left-3 top-3 text-slate-400" />
                    <Input
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      placeholder="Search name or email"
                      className="pl-9"
                    />
                  </div>
                </div>
                <div className="w-full md:w-64">
                  <Label>Location</Label>
                  <Select value={locationFilter} onValueChange={setLocationFilter}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All locations</SelectItem>
                      {locationOptions.map((loc) => (
                        <SelectItem key={loc} value={loc}>{loc}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="space-y-3">
                {filteredStaff.map((person) => (
                  <div key={person.id} className="border border-slate-800 rounded-lg p-4 flex flex-col lg:flex-row lg:items-center lg:justify-between gap-3">
                    <div>
                      <div className="font-semibold">{person.full_name || 'Unnamed staff'}</div>
                      <div className="text-sm text-slate-400">{person.email}</div>
                      <div className="text-xs text-slate-500 mt-1">
                        Role: {person.role || 'unknown'} • Location: {person.location_id || 'n/a'}
                      </div>
                    </div>

                    <div className="flex flex-wrap gap-2">
                      <Badge variant={person.clocked_in_now ? 'default' : 'secondary'}>
                        {person.clocked_in_now ? 'Clocked In' : 'Clocked Out'}
                      </Badge>
                      <Badge variant="secondary">Open Tasks: {person.open_task_count}</Badge>
                      <Badge variant={person.overdue_task_count > 0 ? 'destructive' : 'secondary'}>
                        Overdue: {person.overdue_task_count}
                      </Badge>
                      <Badge variant={person.pending_pto_count > 0 ? 'default' : 'secondary'}>
                        PTO Pending: {person.pending_pto_count}
                      </Badge>
                    </div>

                    <div className="flex gap-2 flex-wrap">
                      <Button variant="outline" onClick={() => setSelectedStaff(person)}>
                        <UserIcon size={14} className="mr-2" />
                        View
                      </Button>
                      <Button onClick={() => openEditStaff(person)}>
                        Edit
                      </Button>
                      <Button variant="outline" onClick={() => navigate('/tasks')}>
                        Tasks
                      </Button>
                      <Button
                        variant={person.is_active === false ? "default" : "destructive"}
                        disabled={staffActionLoading === person.id}
                        onClick={() => handleToggleStaffStatus(person)}
                      >
                        {person.is_active === false ? 'Reactivate' : 'Deactivate'}
                      </Button>
                    </div>
                  </div>
                ))}

                {!loading && filteredStaff.length === 0 && (
                  <div className="text-slate-400">No staff matched your filters.</div>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="assignments">
          <Card>
            <CardHeader><CardTitle>Assignments Snapshot</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              {staffRows
                .filter(s => s.open_task_count > 0 || s.overdue_task_count > 0)
                .sort((a, b) => b.overdue_task_count - a.overdue_task_count || b.open_task_count - a.open_task_count)
                .map((s) => (
                  <div key={s.id} className="border border-slate-800 rounded-lg p-4 flex items-center justify-between">
                    <div>
                      <div className="font-medium">{s.full_name}</div>
                      <div className="text-sm text-slate-400">Open: {s.open_task_count} • Overdue: {s.overdue_task_count}</div>
                    </div>
                    <Button variant="outline" onClick={() => setSelectedStaff(s)}>View Staff</Button>
                  </div>
                ))}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="activity">
          <Card>
            <CardHeader><CardTitle>Recent Activity</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              {activityItems.map((item) => (
                <div key={item.id} className="border border-slate-800 rounded-lg p-3">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <div className="font-medium">{item.staff_name}</div>
                      <div className="text-sm text-slate-400">{item.summary}</div>
                    </div>
                    <div className="text-xs text-slate-500">
                      {item.timestamp ? new Date(item.timestamp).toLocaleString() : 'Unknown'}
                    </div>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <Dialog open={!!selectedStaff} onOpenChange={() => setSelectedStaff(null)}>
        <DialogContent className="max-w-4xl">
          <DialogHeader>
            <DialogTitle>{selectedStaff?.full_name || 'Staff Details'}</DialogTitle>
          </DialogHeader>
          {selectedStaff && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Profile</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div>
                      <div className="text-sm text-slate-400">Email</div>
                      <div>{selectedStaff.email || 'n/a'}</div>
                    </div>
                    <div>
                      <div className="text-sm text-slate-400">Role / Location</div>
                      <div>{selectedStaff.role || 'unknown'} • {selectedStaff.location_id || 'n/a'}</div>
                    </div>
                    <div>
                      <div className="text-sm text-slate-400">Account Status</div>
                      <div>{selectedStaff.is_active === false ? 'Inactive' : 'Active'}</div>
                    </div>
                    <div>
                      <div className="text-sm text-slate-400">Current Status</div>
                      <div>{selectedStaff.clocked_in_now ? 'Clocked In' : 'Clocked Out'}</div>
                    </div>
                    <div>
                      <div className="text-sm text-slate-400">Recent Activity</div>
                      <div>
                        {selectedStaff.recent_activity_at
                          ? new Date(selectedStaff.recent_activity_at).toLocaleString()
                          : 'No recent activity found'}
                      </div>
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Work Summary</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div>
                      <div className="text-sm text-slate-400">Task Summary</div>
                      <div>Open: {selectedStaff.open_task_count} • Overdue: {selectedStaff.overdue_task_count}</div>
                    </div>
                    <div>
                      <div className="text-sm text-slate-400">Pending Requests</div>
                      <div>PTO: {selectedStaff.pending_pto_count} • Time Mods: {selectedStaff.pending_time_mod_count}</div>
                    </div>
                    <div className="flex gap-2 flex-wrap pt-2">
                      <Button
                        variant={selectedStaff.is_active === false ? "default" : "destructive"}
                        disabled={staffActionLoading === selectedStaff.id}
                        onClick={() => handleToggleStaffStatus(selectedStaff)}
                      >
                        {selectedStaff.is_active === false ? 'Reactivate Staff' : 'Deactivate Staff'}
                      </Button>
                      <Button onClick={() => openEditStaff(selectedStaff)}>
                        Edit Staff
                      </Button>
                      <Button variant="outline" type="button" onClick={() => navigate('/admin/dashboard')}>
                        Legacy Staff Manager
                      </Button>
                      <Button variant="outline" onClick={() => navigate('/admin/tasks')}>
                        Open Task Dashboard
                      </Button>
                      <Button variant="outline" onClick={() => navigate('/admin/time-management-hub')}>
                        Open Time Management Hub
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Assigned Tasks</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {tasks
                      .filter(t => t.assigned_to === selectedStaff.id)
                      .slice()
                      .sort((a, b) => {
                        const aOverdue = a.due_date && a.status !== 'completed' && new Date(a.due_date) < new Date() ? 1 : 0;
                        const bOverdue = b.due_date && b.status !== 'completed' && new Date(b.due_date) < new Date() ? 1 : 0;
                        if (bOverdue !== aOverdue) return bOverdue - aOverdue;

                        const ad = a.due_date ? new Date(a.due_date).getTime() : 0;
                        const bd = b.due_date ? new Date(b.due_date).getTime() : 0;
                        return ad - bd;
                      })
                      .slice(0, 8)
                      .map((task) => (
                        <div key={task.id} className="border border-slate-800 rounded-lg p-3">
                          <div className="font-medium">{task.title}</div>
                          <div className="text-sm text-slate-400">
                            Status: {task.status || 'unknown'}
                            {task.due_date ? ` • Due: ${new Date(task.due_date).toLocaleDateString()}` : ''}
                          </div>
                        </div>
                      ))}
                    {tasks.filter(t => t.assigned_to === selectedStaff.id).length === 0 && (
                      <div className="text-slate-400">No assigned tasks found.</div>
                    )}
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Recent Requests</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {[
                      ...ptoRequests
                        .filter(r => r.staff_id === selectedStaff.id)
                        .map(r => ({
                          id: `pto-${r.id}`,
                          label: `PTO • ${r.status || 'unknown'}`,
                          timestamp: r.created_at || r.requested_at || null,
                        })),
                      ...timeModRequests
                        .filter(r => r.staff_id === selectedStaff.id)
                        .map(r => ({
                          id: `timemod-${r.id}`,
                          label: `Time modification • ${r.status || 'unknown'}`,
                          timestamp: r.created_at || r.requested_at || null,
                        })),
                    ]
                      .sort((a, b) => new Date(b.timestamp || 0) - new Date(a.timestamp || 0))
                      .slice(0, 8)
                      .map((item) => (
                        <div key={item.id} className="border border-slate-800 rounded-lg p-3">
                          <div className="font-medium">{item.label}</div>
                          <div className="text-sm text-slate-400">
                            {item.timestamp ? new Date(item.timestamp).toLocaleString() : 'No timestamp'}
                          </div>
                        </div>
                      ))}
                    {[
                      ...ptoRequests.filter(r => r.staff_id === selectedStaff.id),
                      ...timeModRequests.filter(r => r.staff_id === selectedStaff.id),
                    ].length === 0 && (
                      <div className="text-slate-400">No recent requests found.</div>
                    )}
                  </CardContent>
                </Card>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      <Dialog open={showStaffModal} onOpenChange={setShowStaffModal}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>{editingStaff ? 'Edit Staff' : 'Create Staff'}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>Full Name</Label>
              <Input
                value={staffForm.full_name}
                onChange={(e) => setStaffForm({ ...staffForm, full_name: e.target.value })}
                className="mt-1"
              />
            </div>
            <div>
              <Label>Email</Label>
              <Input
                value={staffForm.email}
                onChange={(e) => setStaffForm({ ...staffForm, email: e.target.value })}
                className="mt-1"
              />
            </div>
            <div>
              <Label>Phone</Label>
              <Input
                value={staffForm.phone}
                onChange={(e) => setStaffForm({ ...staffForm, phone: e.target.value })}
                className="mt-1"
              />
            </div>
            <div>
              <Label>Location</Label>
              <select
                value={staffForm.location_id || "__none__"}
                onChange={(e) => setStaffForm({ ...staffForm, location_id: e.target.value === "__none__" ? "" : e.target.value })}
                className="mt-1 flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-white"
              >
                <option value="__none__">No location</option>
                {locations.map((loc) => (
                  <option key={loc.id} value={loc.id}>
                    {loc.name || loc.id}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <Label>{editingStaff ? 'Password (optional)' : 'Password'}</Label>
              <Input
                type="password"
                value={staffForm.password}
                onChange={(e) => setStaffForm({ ...staffForm, password: e.target.value })}
                className="mt-1"
              />
            </div>
            <div>
              <Label>Status</Label>
              <Select
                value={staffForm.is_active ? 'active' : 'inactive'}
                onValueChange={(value) => setStaffForm({ ...staffForm, is_active: value === 'active' })}
              >
                <SelectTrigger className="mt-1">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="active">Active</SelectItem>
                  <SelectItem value="inactive">Inactive</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowStaffModal(false)}>Cancel</Button>
            <Button onClick={handleSaveStaff}>{editingStaff ? 'Save Changes' : 'Create Staff'}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
