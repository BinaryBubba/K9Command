import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Checkbox } from '../components/ui/checkbox';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { toast } from 'sonner';
import { 
  PlusIcon, 
  SearchIcon, 
  CheckCircleIcon, 
  ClockIcon, 
  AlertTriangleIcon,
  PlayIcon,
  ArrowLeftIcon,
  FilterIcon,
  CalendarIcon,
  UserIcon,
  MoreVerticalIcon,
  ListTodoIcon,
  FlagIcon,
  XIcon
} from 'lucide-react';
import api from '../utils/api';
import useAuthStore from '../store/authStore';

export default function TaskDashboardPage() {
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const isAdmin = user?.role === 'admin';
  
  const [tasks, setTasks] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [priorityFilter, setPriorityFilter] = useState('all');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showTaskDetail, setShowTaskDetail] = useState(null);
  const [analytics, setAnalytics] = useState(null);

  // Create task form
  const [newTask, setNewTask] = useState({
    title: '',
    description: '',
    priority: 'medium',
    due_date: '',
    assigned_to: ''
  });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [tasksRes, templatesRes, analyticsRes] = await Promise.all([
        api.get('/tasks'),
        api.get('/forms/task-templates').catch(() => ({ data: [] })),
        api.get('/forms/analytics/tasks').catch(() => ({ data: {} }))
      ]);
      setTasks(tasksRes.data || []);
      setTemplates(templatesRes.data || []);
      setAnalytics(analyticsRes.data);
    } catch (error) {
      console.error('Failed to load tasks:', error);
      toast.error('Failed to load tasks');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateTask = async () => {
    if (!newTask.title.trim()) {
      toast.error('Please enter a task title');
      return;
    }

    try {
      await api.post('/tasks', {
        ...newTask,
        status: 'pending'
      });
      toast.success('Task created');
      setShowCreateModal(false);
      setNewTask({ title: '', description: '', priority: 'medium', due_date: '', assigned_to: '' });
      loadData();
    } catch (error) {
      toast.error('Failed to create task');
    }
  };

  const handleUpdateStatus = async (taskId, newStatus) => {
    try {
      await api.patch(`/api/tasks/${taskId}`, { status: newStatus });
      toast.success(`Task ${newStatus === 'completed' ? 'completed' : 'updated'}`);
      loadData();
    } catch (error) {
      toast.error('Failed to update task');
    }
  };

  const handleChecklistToggle = async (taskId, itemIndex) => {
    const task = tasks.find(t => t.id === taskId);
    if (!task) return;

    const checklist = [...(task.checklist_items || [])];
    checklist[itemIndex] = {
      ...checklist[itemIndex],
      completed: !checklist[itemIndex].completed
    };

    try {
      await api.patch(`/api/tasks/${taskId}`, { checklist_items: checklist });
      loadData();
    } catch (error) {
      toast.error('Failed to update checklist');
    }
  };

  const filteredTasks = tasks.filter(t => {
    const matchesSearch = t.title?.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         t.description?.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = statusFilter === 'all' || t.status === statusFilter;
    const matchesPriority = priorityFilter === 'all' || t.priority === priorityFilter;
    return matchesSearch && matchesStatus && matchesPriority;
  });

  const getPriorityColor = (priority) => {
    switch (priority) {
      case 'high': return 'bg-red-500/20 text-red-400 border-red-500/30';
      case 'medium': return 'bg-amber-500/20 text-amber-400 border-amber-500/30';
      case 'low': return 'bg-green-500/20 text-green-400 border-green-500/30';
      default: return 'bg-slate-500/20 text-slate-400 border-slate-500/30';
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed': return 'bg-green-500/20 text-green-400 border-green-500/30';
      case 'in_progress': return 'bg-blue-500/20 text-blue-400 border-blue-500/30';
      case 'pending': return 'bg-slate-500/20 text-slate-400 border-slate-500/30';
      default: return 'bg-slate-500/20 text-slate-400 border-slate-500/30';
    }
  };

  const isOverdue = (task) => {
    if (!task.due_date || task.status === 'completed') return false;
    return new Date(task.due_date) < new Date();
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="animate-spin h-8 w-8 border-2 border-blue-500 border-t-transparent rounded-full"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950" data-testid="task-dashboard-page">
      {/* Header */}
      <header className="bg-slate-900 border-b border-slate-700 px-6 py-4">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => navigate(isAdmin ? '/admin' : '/staff')}
                className="text-slate-400 hover:text-white"
              >
                <ArrowLeftIcon size={20} />
              </Button>
              <div>
                <h1 className="text-2xl font-bold text-white">Tasks</h1>
                <p className="text-slate-400 text-sm">Manage and track your tasks</p>
              </div>
            </div>
            <Button
              onClick={() => setShowCreateModal(true)}
              className="bg-blue-600 hover:bg-blue-700 text-white"
              data-testid="create-task-btn"
            >
              <PlusIcon size={18} className="mr-2" />
              New Task
            </Button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-8">
          <Card className="bg-gradient-to-br from-slate-700 to-slate-800 border-none">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-white/10 flex items-center justify-center">
                  <ListTodoIcon className="text-white" size={20} />
                </div>
                <div>
                  <p className="text-slate-300 text-sm">Total</p>
                  <p className="text-2xl font-bold text-white">{analytics?.total_tasks || tasks.length}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-amber-600 to-amber-700 border-none">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-white/20 flex items-center justify-center">
                  <ClockIcon className="text-white" size={20} />
                </div>
                <div>
                  <p className="text-amber-100 text-sm">Pending</p>
                  <p className="text-2xl font-bold text-white">{analytics?.pending || 0}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-blue-600 to-blue-700 border-none">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-white/20 flex items-center justify-center">
                  <PlayIcon className="text-white" size={20} />
                </div>
                <div>
                  <p className="text-blue-100 text-sm">In Progress</p>
                  <p className="text-2xl font-bold text-white">{analytics?.in_progress || 0}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-green-600 to-green-700 border-none">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-white/20 flex items-center justify-center">
                  <CheckCircleIcon className="text-white" size={20} />
                </div>
                <div>
                  <p className="text-green-100 text-sm">Completed</p>
                  <p className="text-2xl font-bold text-white">{analytics?.completed || 0}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-red-600 to-red-700 border-none">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-white/20 flex items-center justify-center">
                  <AlertTriangleIcon className="text-white" size={20} />
                </div>
                <div>
                  <p className="text-red-100 text-sm">Overdue</p>
                  <p className="text-2xl font-bold text-white">{analytics?.overdue || 0}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-3 mb-6">
          <div className="relative flex-1 max-w-md">
            <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
            <Input
              placeholder="Search tasks..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-9 bg-slate-800 border-slate-700 text-white"
            />
          </div>
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-40 bg-slate-800 border-slate-700 text-white">
              <FilterIcon size={14} className="mr-2" />
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Status</SelectItem>
              <SelectItem value="pending">Pending</SelectItem>
              <SelectItem value="in_progress">In Progress</SelectItem>
              <SelectItem value="completed">Completed</SelectItem>
            </SelectContent>
          </Select>
          <Select value={priorityFilter} onValueChange={setPriorityFilter}>
            <SelectTrigger className="w-40 bg-slate-800 border-slate-700 text-white">
              <FlagIcon size={14} className="mr-2" />
              <SelectValue placeholder="Priority" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Priority</SelectItem>
              <SelectItem value="high">High</SelectItem>
              <SelectItem value="medium">Medium</SelectItem>
              <SelectItem value="low">Low</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Tasks List */}
        {filteredTasks.length === 0 ? (
          <Card className="bg-slate-900 border-slate-700">
            <CardContent className="py-12 text-center">
              <ListTodoIcon className="mx-auto text-slate-600 mb-4" size={48} />
              <h3 className="text-lg font-semibold text-slate-400 mb-2">No tasks found</h3>
              <p className="text-slate-500 mb-4">Create your first task to get started</p>
              <Button onClick={() => setShowCreateModal(true)} className="bg-blue-600 hover:bg-blue-700">
                <PlusIcon size={16} className="mr-2" />
                Create Task
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-3">
            {filteredTasks.map(task => (
              <Card 
                key={task.id} 
                className={`bg-slate-900 border-slate-700 hover:border-slate-600 transition-all cursor-pointer ${
                  isOverdue(task) ? 'border-l-4 border-l-red-500' : ''
                }`}
                onClick={() => setShowTaskDetail(task)}
                data-testid={`task-card-${task.id}`}
              >
                <CardContent className="p-4">
                  <div className="flex items-start gap-4">
                    {/* Status Checkbox */}
                    <div className="pt-1" onClick={(e) => e.stopPropagation()}>
                      <Checkbox
                        checked={task.status === 'completed'}
                        onCheckedChange={(checked) => 
                          handleUpdateStatus(task.id, checked ? 'completed' : 'pending')
                        }
                        className="h-5 w-5"
                      />
                    </div>

                    {/* Task Content */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className={`font-medium ${task.status === 'completed' ? 'text-slate-500 line-through' : 'text-white'}`}>
                          {task.title}
                        </h3>
                        {isOverdue(task) && (
                          <Badge className="bg-red-500/20 text-red-400 border-red-500/30 text-xs">
                            Overdue
                          </Badge>
                        )}
                      </div>
                      {task.description && (
                        <p className="text-slate-400 text-sm line-clamp-1">{task.description}</p>
                      )}
                      <div className="flex items-center gap-4 mt-2 text-sm">
                        {task.due_date && (
                          <span className={`flex items-center gap-1 ${isOverdue(task) ? 'text-red-400' : 'text-slate-400'}`}>
                            <CalendarIcon size={14} />
                            {new Date(task.due_date).toLocaleDateString()}
                          </span>
                        )}
                        {task.assigned_to_name && (
                          <span className="flex items-center gap-1 text-slate-400">
                            <UserIcon size={14} />
                            {task.assigned_to_name}
                          </span>
                        )}
                        {task.checklist_items?.length > 0 && (
                          <span className="text-slate-400">
                            {task.checklist_items.filter(i => i.completed).length}/{task.checklist_items.length} items
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Badges */}
                    <div className="flex items-center gap-2">
                      <Badge className={getPriorityColor(task.priority)}>
                        {task.priority}
                      </Badge>
                      <Badge className={getStatusColor(task.status)}>
                        {task.status?.replace('_', ' ')}
                      </Badge>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </main>

      {/* Create Task Modal */}
      <Dialog open={showCreateModal} onOpenChange={setShowCreateModal}>
        <DialogContent className="bg-slate-900 border-slate-700">
          <DialogHeader>
            <DialogTitle className="text-white">Create New Task</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <Label className="text-slate-300">Title</Label>
              <Input
                value={newTask.title}
                onChange={(e) => setNewTask({ ...newTask, title: e.target.value })}
                placeholder="Task title"
                className="mt-1 bg-slate-800 border-slate-600 text-white"
              />
            </div>
            <div>
              <Label className="text-slate-300">Description</Label>
              <Textarea
                value={newTask.description}
                onChange={(e) => setNewTask({ ...newTask, description: e.target.value })}
                placeholder="Task description (optional)"
                className="mt-1 bg-slate-800 border-slate-600 text-white"
                rows={3}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label className="text-slate-300">Priority</Label>
                <Select value={newTask.priority} onValueChange={(v) => setNewTask({ ...newTask, priority: v })}>
                  <SelectTrigger className="mt-1 bg-slate-800 border-slate-600 text-white">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="low">Low</SelectItem>
                    <SelectItem value="medium">Medium</SelectItem>
                    <SelectItem value="high">High</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label className="text-slate-300">Due Date</Label>
                <Input
                  type="date"
                  value={newTask.due_date}
                  onChange={(e) => setNewTask({ ...newTask, due_date: e.target.value })}
                  className="mt-1 bg-slate-800 border-slate-600 text-white"
                />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCreateModal(false)} className="border-slate-600 text-slate-300">
              Cancel
            </Button>
            <Button onClick={handleCreateTask} className="bg-blue-600 hover:bg-blue-700">
              Create Task
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Task Detail Modal */}
      {showTaskDetail && (
        <Dialog open={!!showTaskDetail} onOpenChange={() => setShowTaskDetail(null)}>
          <DialogContent className="bg-slate-900 border-slate-700 max-w-lg">
            <DialogHeader>
              <div className="flex items-center justify-between">
                <DialogTitle className="text-white">{showTaskDetail.title}</DialogTitle>
                <Badge className={getPriorityColor(showTaskDetail.priority)}>
                  {showTaskDetail.priority}
                </Badge>
              </div>
            </DialogHeader>
            <div className="space-y-4 py-4">
              {showTaskDetail.description && (
                <div>
                  <Label className="text-slate-400 text-xs">Description</Label>
                  <p className="text-slate-300 mt-1">{showTaskDetail.description}</p>
                </div>
              )}
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="text-slate-400 text-xs">Status</Label>
                  <Select 
                    value={showTaskDetail.status} 
                    onValueChange={(v) => handleUpdateStatus(showTaskDetail.id, v)}
                  >
                    <SelectTrigger className="mt-1 bg-slate-800 border-slate-600 text-white">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="pending">Pending</SelectItem>
                      <SelectItem value="in_progress">In Progress</SelectItem>
                      <SelectItem value="completed">Completed</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                {showTaskDetail.due_date && (
                  <div>
                    <Label className="text-slate-400 text-xs">Due Date</Label>
                    <p className={`mt-1 flex items-center gap-1 ${isOverdue(showTaskDetail) ? 'text-red-400' : 'text-slate-300'}`}>
                      <CalendarIcon size={14} />
                      {new Date(showTaskDetail.due_date).toLocaleDateString()}
                    </p>
                  </div>
                )}
              </div>

              {showTaskDetail.assigned_to_name && (
                <div>
                  <Label className="text-slate-400 text-xs">Assigned To</Label>
                  <p className="text-slate-300 mt-1 flex items-center gap-1">
                    <UserIcon size={14} />
                    {showTaskDetail.assigned_to_name}
                  </p>
                </div>
              )}

              {/* Checklist */}
              {showTaskDetail.checklist_items?.length > 0 && (
                <div>
                  <Label className="text-slate-400 text-xs">Checklist</Label>
                  <div className="mt-2 space-y-2">
                    {showTaskDetail.checklist_items.map((item, index) => (
                      <label key={index} className="flex items-center gap-2 text-slate-300">
                        <Checkbox
                          checked={item.completed}
                          onCheckedChange={() => handleChecklistToggle(showTaskDetail.id, index)}
                        />
                        <span className={item.completed ? 'line-through text-slate-500' : ''}>
                          {item.title || item.text || `Item ${index + 1}`}
                        </span>
                      </label>
                    ))}
                  </div>
                </div>
              )}
            </div>
            <DialogFooter>
              <Button 
                onClick={() => setShowTaskDetail(null)} 
                className="bg-blue-600 hover:bg-blue-700"
              >
                Close
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}
