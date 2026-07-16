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
  const [editTask, setEditTask] = useState(null);
  const [staff, setStaff] = useState([]);
  const [completed, setCompleted] = useState([]);
  const [formModalTask, setFormModalTask] = useState(null);

  const fetchTasks = useCallback(async () => {
    try {
      const [allRes, myRes, staffRes, completedRes] = await Promise.all([
        api.get('/tasks'),
        api.get('/tasks/my'),
        api.get('/users', { params: { limit: 50 } }).catch(() => ({ data: [] })),
        api.get('/tasks/completed', { params: { limit: 50 } }).catch(() => ({ data: [] })),
      ]);
      setTasks(allRes.data);
      setMyTasks(myRes.data);
      setStaff(staffRes.data);
      setCompleted(completedRes.data);
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

  const claimTask = async (taskId) => {
    try {
      await api.patch(`/tasks/${taskId}`, { assigned_to: user.id });
      toast.success('Task claimed');
      fetchTasks();
    } catch { toast.error('Failed to claim task'); }
  };


  const completeTask = async (task) => {
    if (task.require_form_completion && task.form_template_id) {
      setFormModalTask(task);
      return;
    }
    try {
      await api.post(`/tasks/${task.id}/complete`);
      toast.success('Task completed');
      fetchTasks();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to complete task');
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
          {(user?.role === 'admin' || user?.role === 'manager') && (
            <Button size="sm" onClick={() => setShowCreate(true)}>
              <PlusIcon size={16} className="mr-1" /> New Task
            </Button>
          )}
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-6">
        <Tabs defaultValue={user?.role === 'admin' ? 'all' : 'mine'}>
          <TabsList className="w-full mb-6">
            <TabsTrigger value="mine" className="flex-1">My Tasks ({myTasks.length})</TabsTrigger>
            <TabsTrigger value="open" className="flex-1">All Tasks ({tasks.length})</TabsTrigger>
            {user?.role === 'admin' && (
              <TabsTrigger value="all" className="flex-1">Admin View</TabsTrigger>
            )}
            <TabsTrigger value="completed" className="flex-1">Completed</TabsTrigger>
          </TabsList>

          <TabsContent value="mine">
            <TaskList tasks={myTasks} onComplete={completeTask} onRefresh={fetchTasks} onEdit={setEditTask} />
          </TabsContent>
          <TabsContent value="open">
            <div className="mb-3 text-xs text-muted-foreground">All active tasks — tap an unassigned task to claim it</div>
            <TaskList tasks={tasks} onComplete={completeTask} onRefresh={fetchTasks} onEdit={setEditTask} onClaim={claimTask} showAssignee />
          </TabsContent>
          <TabsContent value="all">
            <TaskList tasks={tasks} onComplete={completeTask} onRefresh={fetchTasks} onEdit={setEditTask} showAssignee />
          </TabsContent>
          <TabsContent value="completed">
            <CompletedTaskList tasks={completed} />
          </TabsContent>
        </Tabs>
      </main>

      {editTask && (
        <EditTaskModal
          task={editTask}
          staff={staff}
          onClose={() => setEditTask(null)}
          onSuccess={() => { setEditTask(null); fetchTasks(); }}
        />
      )}
      {showCreate && (
        <CreateTaskModal
          staff={staff}
          onClose={() => setShowCreate(false)}
          onSuccess={() => { setShowCreate(false); fetchTasks(); }}
        />
      )}
      {formModalTask && (
        <TaskFormModal
          task={formModalTask}
          onClose={() => setFormModalTask(null)}
          onSuccess={() => { setFormModalTask(null); fetchTasks(); }}
        />
      )}
    </div>
  );
};

const TaskList = ({ tasks, onComplete, onRefresh, showAssignee, onEdit }) => {
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
              <div className="flex gap-1 shrink-0">
                {task.status !== 'completed' && task.status !== 'cancelled' && onEdit && (
                  <Button size="sm" variant="ghost" className="text-muted-foreground h-7 px-2"
                    onClick={() => onEdit(task)}>✏️</Button>
                )}
                {task.status !== 'completed' && task.status !== 'cancelled' && (
                  <Button size="sm" variant="outline" className="text-green-600 border-green-200 hover:bg-green-50"
                    onClick={() => onComplete(task)}>
                    <CheckCircleIcon size={14} className="mr-1" /> Done
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

const CreateTaskModal = ({ staff, onClose, onSuccess }) => {
  const { user } = useAuthStore();
  const [form, setForm] = useState({
    title: '', description: '', priority: 'medium',
    assigned_to: '', due_date: '', recurrence: '',
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
              <option value="">Unassigned (anyone can claim)</option>
              <optgroup label="── Staff ──">
                {staff.filter(s => ['admin','manager','staff'].includes(s.role?.toLowerCase())).map(s => (
                  <option key={s.id} value={s.id}>{s.full_name} ({s.role})</option>
                ))}
              </optgroup>
              <optgroup label="── Customers ──">
                {staff.filter(s => s.role?.toLowerCase() === 'customer').map(s => (
                  <option key={s.id} value={s.id}>{s.full_name}</option>
                ))}
              </optgroup>
            </select>
          </div>
          <div>
            <Label>Recurrence</Label>
            <select className="w-full mt-1 border rounded-md px-3 py-2 text-sm bg-background"
              value={form.recurrence} onChange={e => setForm(f=>({...f,recurrence:e.target.value}))}>
              <option value="">One-time</option>
              <option value="daily">Daily</option>
              <option value="weekdays">Weekdays only</option>
              <option value="weekly">Weekly</option>
              <option value="biweekly">Every 2 weeks</option>
              <option value="monthly">Monthly</option>
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

const CompletedTaskList = ({ tasks }) => {
  if (tasks.length === 0) return (
    <Card><CardContent className="py-12 text-center text-muted-foreground">No completed tasks</CardContent></Card>
  );
  return (
    <div className="space-y-2">
      {tasks.map(task => (
        <Card key={task.id} className="opacity-80">
          <CardContent className="py-3 px-4">
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <CheckCircleIcon size={14} className="text-green-500" />
                  <p className="font-medium text-sm">{task.title}</p>
                  <Badge className={`text-xs ${PRIORITY_COLORS[task.priority?.toLowerCase()] || PRIORITY_COLORS.medium}`}>
                    {task.priority?.toLowerCase()}
                  </Badge>
                </div>
                {task.description && <p className="text-xs text-muted-foreground mt-1">{task.description}</p>}
                <div className="flex gap-3 mt-1">
                  {task.completed_at && (
                    <span className="text-xs text-green-600">
                      ✓ Completed {new Date(task.completed_at).toLocaleString()}
                    </span>
                  )}
                  {task.completed_by_name && (
                    <span className="text-xs text-muted-foreground">by {task.completed_by_name}</span>
                  )}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
};

const EditTaskModal = ({ task, staff, onClose, onSuccess }) => {
  const [form, setForm] = useState({
    title: task.title || '',
    description: task.description || '',
    priority: task.priority?.toLowerCase() || 'medium',
    assigned_to: task.assigned_to || '',
    due_date: task.due_date ? new Date(task.due_date).toISOString().slice(0,16) : '',
    recurrence: task.recurrence || '',
  });
  const [submitting, setSubmitting] = useState(false);

  const handleSave = async () => {
    if (!form.title.trim()) { toast.error('Title required'); return; }
    setSubmitting(true);
    try {
      await api.patch(`/tasks/${task.id}`, {
        ...form,
        priority: form.priority.toUpperCase(),
        assigned_to: form.assigned_to || undefined,
        due_date: form.due_date ? new Date(form.due_date).toISOString() : undefined,
      });
      toast.success('Task updated');
      onSuccess();
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed'); }
    finally { setSubmitting(false); }
  };

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-end md:items-center justify-center p-4">
      <div className="bg-white rounded-t-2xl md:rounded-2xl w-full max-w-md max-h-[90vh] overflow-y-auto">
        <div className="p-6 space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-lg font-bold">Edit Task</h2>
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
          <div>
            <Label>Recurrence</Label>
            <select className="w-full mt-1 border rounded-md px-3 py-2 text-sm bg-background"
              value={form.recurrence} onChange={e => setForm(f=>({...f,recurrence:e.target.value}))}>
              <option value="">One-time</option>
              <option value="daily">Daily</option>
              <option value="weekdays">Weekdays only</option>
              <option value="weekly">Weekly</option>
              <option value="biweekly">Every 2 weeks</option>
              <option value="monthly">Monthly</option>
            </select>
          </div>
          <div className="flex gap-3 pt-2">
            <Button variant="outline" className="flex-1" onClick={onClose}>Cancel</Button>
            <Button className="flex-1" onClick={handleSave} disabled={submitting}>
              {submitting ? 'Saving...' : 'Save Changes'}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};



const TaskFormModal = ({ task, onClose, onSuccess }) => {
  const [template, setTemplate] = useState(null);
  const [values, setValues] = useState({});
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    api.get(`/task-forms/templates/${task.form_template_id}`)
      .then(res => setTemplate(res.data))
      .catch(() => toast.error('Failed to load form'))
      .finally(() => setLoading(false));
  }, [task.form_template_id]);

  const handleSubmit = async () => {
    const missing = (template?.fields || []).filter(f => f.required && !values[f.key]);
    if (missing.length > 0) {
      toast.error(`Please fill in: ${missing.map(f => f.label).join(', ')}`);
      return;
    }
    setSubmitting(true);
    try {
      await api.post('/task-forms/submissions', {
        template_id: task.form_template_id,
        values,
        related_type: 'task',
        related_id: task.id,
      });
      await api.post(`/tasks/${task.id}/complete`);
      toast.success('Form submitted and task completed!');
      onSuccess();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to submit form');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-xl p-5 max-w-md w-full max-h-[85vh] overflow-y-auto space-y-4">
        <div>
          <h3 className="font-bold text-base">Complete Required Form</h3>
          <p className="text-xs text-muted-foreground mt-1">
            This form must be submitted to complete "{task.title}".
          </p>
        </div>

        {loading ? (
          <p className="text-sm text-muted-foreground">Loading form...</p>
        ) : !template ? (
          <p className="text-sm text-red-600">Could not load the required form template.</p>
        ) : (
          <div className="space-y-3">
            {(template.fields || []).map(field => (
              <div key={field.key}>
                <Label>{field.label}{field.required && ' *'}</Label>
                {field.type === 'boolean' ? (
                  <label className="flex items-center gap-2 mt-1">
                    <input
                      type="checkbox"
                      checked={!!values[field.key]}
                      onChange={e => setValues(v => ({ ...v, [field.key]: e.target.checked }))}
                    />
                    <span className="text-sm">Yes</span>
                  </label>
                ) : field.type === 'select' ? (
                  <select
                    className="mt-1 w-full border border-border rounded-md h-9 px-2 text-sm"
                    value={values[field.key] || ''}
                    onChange={e => setValues(v => ({ ...v, [field.key]: e.target.value }))}
                  >
                    <option value="">Select...</option>
                    {(field.options || []).map(opt => (
                      <option key={opt} value={opt}>{opt}</option>
                    ))}
                  </select>
                ) : (
                  <Input
                    type={field.type === 'number' ? 'number' : 'text'}
                    value={values[field.key] || ''}
                    onChange={e => setValues(v => ({ ...v, [field.key]: e.target.value }))}
                    className="mt-1"
                  />
                )}
              </div>
            ))}
          </div>
        )}

        <div className="flex gap-2 pt-1">
          <Button variant="outline" className="flex-1" onClick={onClose}>Cancel</Button>
          <Button className="flex-1" onClick={handleSubmit} disabled={submitting || loading || !template}>
            {submitting ? 'Submitting...' : 'Submit & Complete'}
          </Button>
        </div>
      </div>
    </div>
  );
};


export default TaskDashboardPage;
