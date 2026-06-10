import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import useAuthStore from '../store/authStore';
import api from '../utils/api';
import { Button } from '../components/ui/button';
import { Card, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { ArrowLeftIcon, PlusIcon, CheckCircleIcon, ClockIcon, AlertCircleIcon } from 'lucide-react';
import { toast } from 'sonner';

const PRIORITY_COLORS = {
  urgent: 'bg-red-100 text-red-700',
  high: 'bg-orange-100 text-orange-700',
  medium: 'bg-blue-100 text-blue-700',
  low: 'bg-gray-100 text-gray-600',
};

const STATUS_COLORS = {
  pending: 'bg-amber-100 text-amber-700',
  in_progress: 'bg-blue-100 text-blue-700',
  completed: 'bg-green-100 text-green-700',
  cancelled: 'bg-gray-100 text-gray-500',
  overdue: 'bg-red-100 text-red-700',
};

const TaskDashboardPage = () => {
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const [tasks, setTasks] = useState([]);
  const [myTasks, setMyTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [staff, setStaff] = useState([]);

  const fetchTasks = useCallback(async () => {
    try {
      const [allRes, myRes, staffRes] = await Promise.all([
        api.get('/tasks'),
        api.get('/tasks/my'),
        api.get('/users', { params: { limit: 50 } }).catch(() => ({ data: [] })),
      ]);
      setTasks(allRes.data);
      setMyTasks(myRes.data);
      setStaff(staffRes.data);
    } catch {
      toast.error('Failed to load tasks');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!user) { navigate('/auth'); return; }
    fetchTasks();
  }, [user, navigate, fetchTasks]);

  const completeTask = async (taskId) => {
    try {
      await api.post(`/tasks/${taskId}/complete`);
      toast.success('Task completed');
      fetchTasks();
    } catch {
      toast.error('Failed to complete task');
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
            <h1 className="text-lg font-serif font-bold text-primary">Tasks</h1>
          </div>
          <Button size="sm" onClick={() => setShowCreate(true)}>
            <PlusIcon size={16} className="mr-1" /> New Task
          </Button>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-6">
        <Tabs defaultValue={user?.role === 'admin' ? 'all' : 'mine'}>
          <TabsList className="w-full mb-6">
            <TabsTrigger value="mine" className="flex-1">My Tasks ({myTasks.length})</TabsTrigger>
            {user?.role === 'admin' && (
              <TabsTrigger value="all" className="flex-1">All Tasks ({tasks.length})</TabsTrigger>
            )}
          </TabsList>

          <TabsContent value="mine">
            <TaskList tasks={myTasks} onComplete={completeTask} onRefresh={fetchTasks} />
          </TabsContent>
          <TabsContent value="all">
            <TaskList tasks={tasks} onComplete={completeTask} onRefresh={fetchTasks} showAssignee />
          </TabsContent>
        </Tabs>
      </main>

      {showCreate && (
        <CreateTaskModal
          staff={staff}
          onClose={() => setShowCreate(false)}
          onSuccess={() => { setShowCreate(false); fetchTasks(); }}
        />
      )}
    </div>
  );
};

const TaskList = ({ tasks, onComplete, onRefresh, showAssignee }) => {
  if (tasks.length === 0) return (
    <Card><CardContent className="py-12 text-center text-muted-foreground">
      No active tasks
    </CardContent></Card>
  );

  return (
    <div className="space-y-2">
      {tasks.map(task => (
        <Card key={task.id} className={task.status === 'overdue' ? 'border-red-200' : ''}>
          <CardContent className="py-3 px-4">
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <p className="font-medium text-sm">{task.title}</p>
                  <Badge className={`text-xs ${PRIORITY_COLORS[task.priority?.toLowerCase()] || PRIORITY_COLORS.medium}`}>
                    {task.priority?.toLowerCase()}
                  </Badge>
                  <Badge className={`text-xs ${STATUS_COLORS[task.status?.toLowerCase()] || STATUS_COLORS.pending}`}>
                    {task.status?.replace('_', ' ')}
                  </Badge>
                </div>
                {task.description && (
                  <p className="text-xs text-muted-foreground mt-1">{task.description}</p>
                )}
                <div className="flex gap-3 mt-1.5">
                  {task.due_date && (
                    <span className="flex items-center gap-1 text-xs text-muted-foreground">
                      <ClockIcon size={11} />
                      Due: {new Date(task.due_date).toLocaleDateString()}
                    </span>
                  )}
                  {showAssignee && task.assigned_to && (
                    <span className="text-xs text-muted-foreground">→ {task.assigned_to.slice(0,8)}...</span>
                  )}
                </div>
                {task.checklist?.length > 0 && (
                  <p className="text-xs text-muted-foreground mt-1">
                    {task.checklist.filter(i => i.completed).length}/{task.checklist.length} checklist items
                  </p>
                )}
              </div>
              {task.status !== 'completed' && task.status !== 'cancelled' && (
                <Button size="sm" variant="outline" className="shrink-0 text-green-600 border-green-200 hover:bg-green-50"
                  onClick={() => onComplete(task.id)}>
                  <CheckCircleIcon size={14} className="mr-1" /> Done
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
};

const CreateTaskModal = ({ staff, onClose, onSuccess }) => {
  const { user } = useAuthStore();
  const [form, setForm] = useState({
    title: '', description: '', priority: 'medium',
    assigned_to: '', due_date: '',
  });
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    if (!form.title.trim()) { toast.error('Title is required'); return; }
    setSubmitting(true);
    try {
      await api.post('/tasks', {
        ...form,
        priority: form.priority.toUpperCase(),
        assigned_to: form.assigned_to || undefined,
        due_date: form.due_date ? new Date(form.due_date).toISOString() : undefined,
      });
      toast.success('Task created');
      onSuccess();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to create task');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-end md:items-center justify-center p-4">
      <div className="bg-white rounded-t-2xl md:rounded-2xl w-full max-w-md max-h-[90vh] overflow-y-auto">
        <div className="p-6 space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-lg font-bold">New Task</h2>
            <button onClick={onClose} className="text-muted-foreground text-xl">×</button>
          </div>
          <div>
            <Label>Title *</Label>
            <Input value={form.title} onChange={e => setForm(f=>({...f,title:e.target.value}))} className="mt-1" />
          </div>
          <div>
            <Label>Description</Label>
            <Textarea value={form.description} onChange={e => setForm(f=>({...f,description:e.target.value}))} className="mt-1" rows={2} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label>Priority</Label>
              <select className="w-full mt-1 border rounded-md px-3 py-2 text-sm bg-background"
                value={form.priority} onChange={e => setForm(f=>({...f,priority:e.target.value}))}>
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="urgent">Urgent</option>
              </select>
            </div>
            <div>
              <Label>Due Date</Label>
              <Input type="datetime-local" value={form.due_date}
                onChange={e => setForm(f=>({...f,due_date:e.target.value}))} className="mt-1" />
            </div>
          </div>
          <div>
            <Label>Assign To</Label>
            <select className="w-full mt-1 border rounded-md px-3 py-2 text-sm bg-background"
              value={form.assigned_to} onChange={e => setForm(f=>({...f,assigned_to:e.target.value}))}>
              <option value="">Unassigned</option>
              {staff.map(s => <option key={s.id} value={s.id}>{s.full_name}</option>)}
            </select>
          </div>
          <div className="flex gap-3 pt-2">
            <Button variant="outline" className="flex-1" onClick={onClose}>Cancel</Button>
            <Button className="flex-1" onClick={handleSubmit} disabled={submitting}>
              {submitting ? 'Creating...' : 'Create Task'}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TaskDashboardPage;
