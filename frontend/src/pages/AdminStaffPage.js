import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { ArrowLeftIcon, ClockIcon, CalendarIcon, PlusIcon, EditIcon, TrashIcon, CheckIcon, UserIcon } from 'lucide-react';
import { toast } from 'sonner';
import api from '../utils/api';
import useAuthStore from '../store/authStore';
import TaskModal from '../components/TaskModal';

const AdminStaffPage = () => {
  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);
  const [tasks, setTasks] = useState([]);
  const [shifts, setShifts] = useState([]);
  const [staff, setStaff] = useState([]);
  const [locations, setLocations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedTask, setSelectedTask] = useState(null);
  const [isRecurring, setIsRecurring] = useState(false);
  const [shiftModalOpen, setShiftModalOpen] = useState(false);
  const [selectedShift, setSelectedShift] = useState(null);
  const [shiftForm, setShiftForm] = useState({
    staff_id: '',
    location_id: '',
    start_time: '',
    end_time: '',
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
      const [tasksRes, shiftsRes, staffRes, locationsRes] = await Promise.all([
        api.get('/tasks'),
        api.get('/shifts'),
        api.get('/admin/users?role=staff'),
        api.get('/locations'),
      ]);
      setTasks(tasksRes.data);
      setShifts(shiftsRes.data);
      setStaff(staffRes.data);
      setLocations(locationsRes.data);
    } catch (error) {
      toast.error('Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const completedTasks = tasks.filter(t => t.status === 'completed').length;
  const pendingTasks = tasks.filter(t => t.status === 'pending').length;

  const handleCompleteTask = async (taskId) => {
    try {
      await api.patch(`/tasks/${taskId}/complete`);
      toast.success('Task marked as complete');
      fetchData();
    } catch (error) {
      toast.error('Failed to complete task');
    }
  };

  const handleDeleteTask = async (taskId) => {
    if (!window.confirm('Are you sure you want to delete this task?')) return;
    try {
      await api.delete(`/tasks/${taskId}`);
      toast.success('Task deleted');
      fetchData();
    } catch (error) {
      toast.error('Failed to delete task');
    }
  };

  const openCreateModal = (recurring = false) => {
    setSelectedTask(null);
    setIsRecurring(recurring);
    setModalOpen(true);
  };

  const openEditModal = (task) => {
    setSelectedTask(task);
    setIsRecurring(false);
    setModalOpen(true);
  };

  // Shift handlers
  const openShiftModal = (shift = null) => {
    if (shift) {
      setSelectedShift(shift);
      setShiftForm({
        staff_id: shift.staff_id,
        location_id: shift.location_id,
        start_time: shift.start_time.slice(0, 16),
        end_time: shift.end_time.slice(0, 16),
        notes: shift.notes || '',
      });
    } else {
      setSelectedShift(null);
      setShiftForm({
        staff_id: staff[0]?.id || '',
        location_id: locations[0]?.id || '',
        start_time: '',
        end_time: '',
        notes: '',
      });
    }
    setShiftModalOpen(true);
  };

  const handleShiftSubmit = async (e) => {
    e.preventDefault();
    try {
      if (selectedShift) {
        await api.patch(`/shifts/${selectedShift.id}`, {
          ...shiftForm,
          start_time: new Date(shiftForm.start_time).toISOString(),
          end_time: new Date(shiftForm.end_time).toISOString(),
        });
        toast.success('Shift updated');
      } else {
        await api.post('/shifts', {
          ...shiftForm,
          start_time: new Date(shiftForm.start_time).toISOString(),
          end_time: new Date(shiftForm.end_time).toISOString(),
        });
        toast.success('Shift created');
      }
      setShiftModalOpen(false);
      fetchData();
    } catch (error) {
      toast.error('Failed to save shift');
    }
  };

  const handleDeleteShift = async (shiftId) => {
    if (!window.confirm('Are you sure you want to delete this shift?')) return;
    try {
      await api.delete(`/shifts/${shiftId}`);
      toast.success('Shift deleted');
      fetchData();
    } catch (error) {
      toast.error('Failed to delete shift');
    }
  };

  // Group shifts by date
  const shiftsByDate = shifts.reduce((acc, shift) => {
    const date = new Date(shift.start_time).toLocaleDateString();
    if (!acc[date]) acc[date] = [];
    acc[date].push(shift);
    return acc;
  }, {});

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
          <h1 className="text-3xl font-serif font-bold text-primary">Staff & Task Management</h1>
          <p className="text-muted-foreground mt-1">Manage tasks, schedules, and staff assignments</p>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 md:px-8 py-8">
        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
            <CardContent className="p-6">
              <p className="text-sm text-muted-foreground uppercase tracking-wider mb-1">Total Tasks</p>
              <p className="text-3xl font-serif font-bold text-primary">{tasks.length}</p>
            </CardContent>
          </Card>
          <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
            <CardContent className="p-6">
              <p className="text-sm text-muted-foreground uppercase tracking-wider mb-1">Completed</p>
              <p className="text-3xl font-serif font-bold text-green-600">{completedTasks}</p>
            </CardContent>
          </Card>
          <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
            <CardContent className="p-6">
              <p className="text-sm text-muted-foreground uppercase tracking-wider mb-1">Pending</p>
              <p className="text-3xl font-serif font-bold text-yellow-600">{pendingTasks}</p>
            </CardContent>
          </Card>
          <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
            <CardContent className="p-6">
              <p className="text-sm text-muted-foreground uppercase tracking-wider mb-1">Scheduled Shifts</p>
              <p className="text-3xl font-serif font-bold text-blue-600">{shifts.length}</p>
            </CardContent>
          </Card>
        </div>

        <Tabs defaultValue="tasks" className="space-y-6">
          <TabsList className="bg-white rounded-full p-1 shadow-sm">
            <TabsTrigger value="tasks" className="rounded-full px-6">Tasks</TabsTrigger>
            <TabsTrigger value="schedule" className="rounded-full px-6">Shift Schedule</TabsTrigger>
          </TabsList>

          {/* Tasks Tab */}
          <TabsContent value="tasks">
            <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
              <CardHeader className="border-b border-border/40">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-2xl font-serif">All Tasks</CardTitle>
                  <div className="flex gap-2">
                    <Button onClick={() => openCreateModal(false)} className="rounded-full">
                      <PlusIcon size={18} className="mr-2" /> New Task
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="p-6">
                {tasks.length === 0 ? (
                  <div className="text-center py-12">
                    <CalendarIcon size={48} className="mx-auto text-muted-foreground/50 mb-4" />
                    <p className="text-muted-foreground mb-4">No tasks found</p>
                    <Button onClick={() => openCreateModal(false)}>Create First Task</Button>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {tasks.map((task) => (
                      <div key={task.id} className="p-4 rounded-xl bg-muted/30 border border-border hover:border-primary/30 transition-all">
                        <div className="flex justify-between items-start gap-4">
                          <div className="flex-1">
                            <h4 className="font-semibold">{task.title}</h4>
                            {task.description && <p className="text-sm text-muted-foreground mt-1">{task.description}</p>}
                            {task.due_date && (
                              <p className="text-xs text-muted-foreground mt-2">Due: {new Date(task.due_date).toLocaleDateString()}</p>
                            )}
                            {task.completed_by_name && (
                              <p className="text-xs text-green-600 mt-1">
                                <CheckIcon size={12} className="inline mr-1" />
                                Completed by {task.completed_by_name} at {task.completed_at ? new Date(task.completed_at).toLocaleString() : 'N/A'}
                              </p>
                            )}
                          </div>
                          <div className="flex items-center gap-2">
                            <Badge className={task.status === 'completed' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'}>
                              {task.status}
                            </Badge>
                            {task.status !== 'completed' && (
                              <Button variant="ghost" size="sm" onClick={() => handleCompleteTask(task.id)} className="text-green-600">
                                <CheckIcon size={16} />
                              </Button>
                            )}
                            <Button variant="ghost" size="sm" onClick={() => openEditModal(task)}>
                              <EditIcon size={16} />
                            </Button>
                            <Button variant="ghost" size="sm" className="text-red-600" onClick={() => handleDeleteTask(task.id)}>
                              <TrashIcon size={16} />
                            </Button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Schedule Tab */}
          <TabsContent value="schedule">
            <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
              <CardHeader className="border-b border-border/40">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-2xl font-serif">Shift Schedule</CardTitle>
                  <Button onClick={() => openShiftModal()} className="rounded-full">
                    <PlusIcon size={18} className="mr-2" /> Add Shift
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="p-6">
                {shifts.length === 0 ? (
                  <div className="text-center py-12">
                    <ClockIcon size={48} className="mx-auto text-muted-foreground/50 mb-4" />
                    <p className="text-muted-foreground mb-4">No shifts scheduled</p>
                    <Button onClick={() => openShiftModal()}>Schedule First Shift</Button>
                  </div>
                ) : (
                  <div className="space-y-6">
                    {Object.entries(shiftsByDate).sort((a, b) => new Date(a[0]) - new Date(b[0])).map(([date, dayShifts]) => (
                      <div key={date}>
                        <h3 className="font-semibold text-lg mb-3 flex items-center gap-2">
                          <CalendarIcon size={18} className="text-primary" />
                          {date}
                        </h3>
                        <div className="space-y-2 ml-6">
                          {dayShifts.map((shift) => (
                            <div key={shift.id} className="p-4 rounded-xl bg-blue-50 border border-blue-200 flex justify-between items-center">
                              <div className="flex items-center gap-4">
                                <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center">
                                  <UserIcon className="text-blue-600" size={18} />
                                </div>
                                <div>
                                  <p className="font-semibold">{shift.staff_name || 'Unknown Staff'}</p>
                                  <p className="text-sm text-muted-foreground">
                                    {new Date(shift.start_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} - 
                                    {new Date(shift.end_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                  </p>
                                  {shift.notes && <p className="text-xs text-muted-foreground">{shift.notes}</p>}
                                </div>
                              </div>
                              <div className="flex gap-2">
                                <Button size="sm" variant="ghost" onClick={() => openShiftModal(shift)}>
                                  <EditIcon size={14} />
                                </Button>
                                <Button size="sm" variant="ghost" className="text-red-600" onClick={() => handleDeleteShift(shift.id)}>
                                  <TrashIcon size={14} />
                                </Button>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </main>

      <TaskModal isOpen={modalOpen} onClose={() => setModalOpen(false)} task={selectedTask} onSuccess={fetchData} isRecurring={isRecurring} />

      {/* Shift Modal */}
      <Dialog open={shiftModalOpen} onOpenChange={setShiftModalOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>{selectedShift ? 'Edit Shift' : 'Schedule New Shift'}</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleShiftSubmit} className="space-y-4">
            <div>
              <Label>Staff Member</Label>
              <Select value={shiftForm.staff_id} onValueChange={(v) => setShiftForm({ ...shiftForm, staff_id: v })}>
                <SelectTrigger><SelectValue placeholder="Select staff" /></SelectTrigger>
                <SelectContent>
                  {staff.map((s) => (
                    <SelectItem key={s.id} value={s.id}>{s.full_name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Location</Label>
              <Select value={shiftForm.location_id} onValueChange={(v) => setShiftForm({ ...shiftForm, location_id: v })}>
                <SelectTrigger><SelectValue placeholder="Select location" /></SelectTrigger>
                <SelectContent>
                  {locations.map((l) => (
                    <SelectItem key={l.id} value={l.id}>{l.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Start Time</Label>
                <Input type="datetime-local" value={shiftForm.start_time} onChange={(e) => setShiftForm({ ...shiftForm, start_time: e.target.value })} required />
              </div>
              <div>
                <Label>End Time</Label>
                <Input type="datetime-local" value={shiftForm.end_time} onChange={(e) => setShiftForm({ ...shiftForm, end_time: e.target.value })} required />
              </div>
            </div>
            <div>
              <Label>Notes</Label>
              <textarea value={shiftForm.notes} onChange={(e) => setShiftForm({ ...shiftForm, notes: e.target.value })} className="w-full p-2 border rounded-lg" rows={2} />
            </div>
            <div className="flex gap-3 pt-4">
              <Button type="button" variant="outline" onClick={() => setShiftModalOpen(false)} className="flex-1">Cancel</Button>
              <Button type="submit" className="flex-1">{selectedShift ? 'Update' : 'Create'}</Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default AdminStaffPage;
