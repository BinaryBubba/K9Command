import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { ArrowLeftIcon, UsersIcon, ClockIcon, CalendarIcon, PlusIcon, EditIcon, TrashIcon, CheckIcon } from 'lucide-react';
import { toast } from 'sonner';
import api from '../utils/api';
import useAuthStore from '../store/authStore';
import TaskModal from '../components/TaskModal';

const AdminStaffPage = () => {
  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedTask, setSelectedTask] = useState(null);
  const [isRecurring, setIsRecurring] = useState(false);

  useEffect(() => {
    if (!user || user.role !== 'admin') {
      navigate('/auth');
      return;
    }
    fetchData();
  }, [user, navigate]);

  const fetchData = async () => {
    try {
      const [tasksRes] = await Promise.all([
        api.get('/tasks'),
      ]);
      setTasks(tasksRes.data);
    } catch (error) {
      toast.error('Failed to load staff data');
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
          <Button
            variant="ghost"
            onClick={() => navigate('/admin/dashboard')}
            className="flex items-center gap-2 mb-2"
          >
            <ArrowLeftIcon size={18} />
            Back to Dashboard
          </Button>
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-serif font-bold text-primary">Staff & Task Management</h1>
              <p className="text-muted-foreground mt-1">Manage tasks and staff schedules</p>
            </div>
            <div className="flex gap-2">
              <Button
                data-testid="create-task-btn"
                onClick={() => openCreateModal(false)}
                className="flex items-center gap-2 rounded-full"
              >
                <PlusIcon size={18} />
                New Task
              </Button>
              <Button
                data-testid="create-recurring-task-btn"
                onClick={() => openCreateModal(true)}
                variant="outline"
                className="flex items-center gap-2 rounded-full"
              >
                <CalendarIcon size={18} />
                Recurring Tasks
              </Button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 md:px-8 py-8">
        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground uppercase tracking-wider mb-1">Total Tasks</p>
                  <p className="text-3xl font-serif font-bold text-primary">{tasks.length}</p>
                </div>
                <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center">
                  <CalendarIcon className="text-primary" size={24} />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground uppercase tracking-wider mb-1">Completed</p>
                  <p className="text-3xl font-serif font-bold text-green-600">{completedTasks}</p>
                </div>
                <div className="w-12 h-12 rounded-full bg-green-100 flex items-center justify-center">
                  <CheckIcon className="text-green-600" size={24} />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground uppercase tracking-wider mb-1">Pending</p>
                  <p className="text-3xl font-serif font-bold text-yellow-600">{pendingTasks}</p>
                </div>
                <div className="w-12 h-12 rounded-full bg-yellow-100 flex items-center justify-center">
                  <ClockIcon className="text-yellow-600" size={24} />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Tasks List */}
        <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
          <CardHeader className="border-b border-border/40">
            <CardTitle className="text-2xl font-serif">All Tasks</CardTitle>
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
                  <div
                    key={task.id}
                    data-testid={`task-${task.id}`}
                    className="p-4 rounded-xl bg-muted/30 border border-border hover:border-primary/30 transition-all"
                  >
                    <div className="flex justify-between items-start gap-4">
                      <div className="flex-1">
                        <h4 className="font-semibold">{task.title}</h4>
                        {task.description && (
                          <p className="text-sm text-muted-foreground mt-1">{task.description}</p>
                        )}
                        {task.due_date && (
                          <p className="text-xs text-muted-foreground mt-2">
                            Due: {new Date(task.due_date).toLocaleDateString()}
                          </p>
                        )}
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge className={task.status === 'completed' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'}>
                          {task.status}
                        </Badge>
                        {task.status !== 'completed' && (
                          <Button
                            data-testid={`complete-task-${task.id}`}
                            variant="ghost"
                            size="sm"
                            onClick={() => handleCompleteTask(task.id)}
                            className="text-green-600 hover:text-green-700 hover:bg-green-50"
                          >
                            <CheckIcon size={16} />
                          </Button>
                        )}
                        <Button
                          data-testid={`edit-task-${task.id}`}
                          variant="ghost"
                          size="sm"
                          onClick={() => openEditModal(task)}
                        >
                          <EditIcon size={16} />
                        </Button>
                        <Button
                          data-testid={`delete-task-${task.id}`}
                          variant="ghost"
                          size="sm"
                          className="text-red-600 hover:text-red-700 hover:bg-red-50"
                          onClick={() => handleDeleteTask(task.id)}
                        >
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
      </main>

      <TaskModal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        task={selectedTask}
        onSuccess={fetchData}
        isRecurring={isRecurring}
      />
    </div>
  );
};

export default AdminStaffPage;
