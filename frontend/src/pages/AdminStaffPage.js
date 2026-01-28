import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { ArrowLeftIcon, UsersIcon, ClockIcon, CalendarIcon } from 'lucide-react';
import { toast } from 'sonner';
import api from '../utils/api';
import useAuthStore from '../store/authStore';

const AdminStaffPage = () => {
  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);
  const [timeEntries, setTimeEntries] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);

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
          <h1 className="text-3xl font-serif font-bold text-primary">Staff Management</h1>
          <p className="text-muted-foreground mt-1">View staff activity and schedules</p>
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
                  <ClockIcon className="text-green-600" size={24} />
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

        {/* Recent Tasks */}
        <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
          <CardHeader className="border-b border-border/40">
            <CardTitle className="text-2xl font-serif">Recent Tasks</CardTitle>
          </CardHeader>
          <CardContent className="p-6">
            {tasks.length === 0 ? (
              <p className="text-center text-muted-foreground py-8">No tasks found</p>
            ) : (
              <div className="space-y-3">
                {tasks.slice(0, 10).map((task) => (
                  <div
                    key={task.id}
                    className="p-4 rounded-xl bg-muted/30 border border-border"
                  >
                    <div className="flex justify-between items-start">
                      <div className="flex-1">
                        <h4 className="font-semibold">{task.title}</h4>
                        {task.description && (
                          <p className="text-sm text-muted-foreground mt-1">{task.description}</p>
                        )}
                      </div>
                      <Badge className={task.status === 'completed' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'}>
                        {task.status}
                      </Badge>
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

export default AdminStaffPage;
