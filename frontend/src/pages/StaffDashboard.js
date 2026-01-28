import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import useAuthStore from '../store/authStore';
import api from '../utils/api';
import { Button } from '../components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/card';
import { Checkbox } from '../components/ui/checkbox';
import { CheckCircleIcon, ClockIcon, ListTodoIcon, LogOutIcon, ImageIcon, UploadIcon } from 'lucide-react';
import { toast } from 'sonner';

const StaffDashboard = () => {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const [stats, setStats] = useState({});
  const [tasks, setTasks] = useState([]);
  const [clockedIn, setClockedIn] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user || user.role !== 'staff') {
      navigate('/auth');
      return;
    }
    fetchData();
  }, [user, navigate]);

  const fetchData = async () => {
    try {
      const [statsRes, tasksRes] = await Promise.all([
        api.get('/dashboard/stats'),
        api.get('/tasks'),
      ]);
      setStats(statsRes.data);
      setTasks(tasksRes.data.filter(t => t.status !== 'completed'));
    } catch (error) {
      toast.error('Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  const handleClockIn = async () => {
    try {
      await api.post('/time-entries/clock-in', {
        staff_id: user.id,
        location_id: user.location_id || 'default-location',
      });
      setClockedIn(true);
      toast.success('Clocked in successfully!');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to clock in');
    }
  };

  const handleClockOut = async () => {
    try {
      await api.post('/time-entries/clock-out');
      setClockedIn(false);
      toast.success('Clocked out successfully!');
    } catch (error) {
      toast.error('Failed to clock out');
    }
  };

  const handleCompleteTask = async (taskId) => {
    try {
      await api.patch(`/tasks/${taskId}/complete`);
      setTasks(tasks.filter(t => t.id !== taskId));
      toast.success('Task completed!');
    } catch (error) {
      toast.error('Failed to complete task');
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div>
          <p className="mt-4 text-muted-foreground">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#F9F7F2]">
      {/* Header */}
      <header className="bg-white border-b border-border/40 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 md:px-8 py-4">
          <div className="flex justify-between items-center mb-4">
            <div>
              <h1 className="text-2xl font-serif font-bold text-primary">Staff Dashboard</h1>
              <p className="text-sm text-muted-foreground">Welcome back, {user?.full_name}</p>
            </div>
            <Button
              data-testid="staff-logout-button"
              onClick={handleLogout}
              variant="ghost"
              className="flex items-center gap-2"
            >
              <LogOutIcon size={18} />
              Logout
            </Button>
          </div>
          
          {/* Time Clock */}
          <div className="flex gap-4">
            {!clockedIn ? (
              <Button
                data-testid="clock-in-button"
                onClick={handleClockIn}
                className="rounded-full bg-primary hover:bg-primary/90 flex items-center gap-2"
              >
                <ClockIcon size={18} />
                Clock In
              </Button>
            ) : (
              <Button
                data-testid="clock-out-button"
                onClick={handleClockOut}
                variant="destructive"
                className="rounded-full flex items-center gap-2"
              >
                <ClockIcon size={18} />
                Clock Out
              </Button>
            )}
            {clockedIn && (
              <span className="flex items-center gap-2 text-sm text-green-600 font-medium">
                <div className="w-2 h-2 rounded-full bg-green-600 animate-pulse"></div>
                Currently Clocked In
              </span>
            )}
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 md:px-8 py-8">
        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          <Card data-testid="stat-tasks" className="bg-white rounded-2xl border border-border/50 shadow-sm">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground uppercase tracking-wider">Today's Tasks</p>
                  <p className="text-3xl font-serif font-bold text-primary mt-2">{stats.todays_tasks || 0}</p>
                </div>
                <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center">
                  <ListTodoIcon className="text-primary" size={24} />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card data-testid="stat-active-dogs" className="bg-white rounded-2xl border border-border/50 shadow-sm">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground uppercase tracking-wider">Active Dogs</p>
                  <p className="text-3xl font-serif font-bold text-secondary-foreground mt-2">{stats.active_bookings || 0}</p>
                </div>
                <div className="w-12 h-12 rounded-full bg-secondary/20 flex items-center justify-center">
                  <CheckCircleIcon className="text-secondary-foreground" size={24} />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Quick Actions */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          <Card data-testid="action-upload-photos" className="bg-gradient-to-br from-primary to-primary/80 text-white rounded-2xl shadow-lg cursor-pointer hover:shadow-xl hover:-translate-y-1 transition-all duration-300" onClick={() => navigate('/staff/upload')}>
            <CardContent className="p-8">
              <div className="flex items-center gap-4">
                <div className="w-16 h-16 rounded-full bg-white/20 backdrop-blur-sm flex items-center justify-center">
                  <UploadIcon size={32} />
                </div>
                <div>
                  <h3 className="text-2xl font-serif font-bold">Upload Photos</h3>
                  <p className="opacity-90">Add today's updates</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card data-testid="action-view-bookings" className="bg-gradient-to-br from-secondary to-secondary/80 text-secondary-foreground rounded-2xl shadow-lg cursor-pointer hover:shadow-xl hover:-translate-y-1 transition-all duration-300" onClick={() => navigate('/staff/bookings')}>
            <CardContent className="p-8">
              <div className="flex items-center gap-4">
                <div className="w-16 h-16 rounded-full bg-white/30 backdrop-blur-sm flex items-center justify-center">
                  <ImageIcon size={32} />
                </div>
                <div>
                  <h3 className="text-2xl font-serif font-bold">View Bookings</h3>
                  <p className="opacity-90">Check today's guests</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Task List */}
        <Card data-testid="task-list" className="bg-white rounded-2xl border border-border/50 shadow-sm">
          <CardHeader className="border-b border-border/40">
            <CardTitle className="text-2xl font-serif flex items-center gap-2">
              <ListTodoIcon className="text-primary" />
              Today's Tasks
            </CardTitle>
          </CardHeader>
          <CardContent className="p-6">
            {tasks.length === 0 ? (
              <div className="text-center py-12">
                <CheckCircleIcon size={48} className="mx-auto text-green-500 mb-4" />
                <p className="text-muted-foreground">All tasks completed! Great work!</p>
              </div>
            ) : (
              <div className="space-y-4">
                {tasks.map((task) => (
                  <div
                    key={task.id}
                    data-testid={`task-item-${task.id}`}
                    className="flex items-start gap-4 p-4 bg-[#F9F7F2] rounded-xl border border-border/30 hover:border-primary/30 transition-all"
                  >
                    <Checkbox
                      data-testid={`task-checkbox-${task.id}`}
                      checked={false}
                      onCheckedChange={() => handleCompleteTask(task.id)}
                      className="mt-1"
                    />
                    <div className="flex-1">
                      <h4 className="font-semibold text-lg">{task.title}</h4>
                      {task.description && (
                        <p className="text-sm text-muted-foreground mt-1">{task.description}</p>
                      )}
                      {task.due_date && (
                        <p className="text-xs text-muted-foreground mt-2">
                          Due: {new Date(task.due_date).toLocaleString()}
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </main>
    </div>
  );
};

export default StaffDashboard;
