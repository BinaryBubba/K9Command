import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import useAuthStore from '../store/authStore';
import api from '../utils/api';
import { Button } from '../components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/card';
import { UsersIcon, DogIcon, CalendarIcon, AlertCircleIcon, LogOutIcon, BarChartIcon, ClockIcon, MessageCircleIcon, ClipboardListIcon, ShieldCheckIcon, CalendarDaysIcon } from 'lucide-react';
import { toast } from 'sonner';

const AdminDashboard = () => {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const [stats, setStats] = useState({});
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
      const statsRes = await api.get('/dashboard/stats');
      setStats(statsRes.data);
    } catch (error) {
      toast.error('Failed to load dashboard data');
    } finally {
      setLoading(false);
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
        <div className="max-w-7xl mx-auto px-4 md:px-8 py-4 flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-serif font-bold text-primary">Admin Dashboard</h1>
            <p className="text-sm text-muted-foreground">Welcome back, {user?.full_name}</p>
          </div>
          <Button
            data-testid="admin-logout-button"
            onClick={handleLogout}
            variant="ghost"
            className="flex items-center gap-2"
          >
            <LogOutIcon size={18} />
            Logout
          </Button>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 md:px-8 py-8">
        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6 mb-8">
          <Card data-testid="stat-customers" className="bg-white rounded-2xl border border-border/50 shadow-sm">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Customers</p>
                  <p className="text-2xl font-serif font-bold text-primary mt-2">{stats.total_customers || 0}</p>
                </div>
                <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
                  <UsersIcon className="text-primary" size={20} />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card data-testid="stat-dogs" className="bg-white rounded-2xl border border-border/50 shadow-sm">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Dogs</p>
                  <p className="text-2xl font-serif font-bold text-primary mt-2">{stats.total_dogs || 0}</p>
                </div>
                <div className="w-10 h-10 rounded-full bg-secondary/20 flex items-center justify-center">
                  <DogIcon className="text-secondary-foreground" size={20} />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card data-testid="stat-bookings" className="bg-white rounded-2xl border border-border/50 shadow-sm">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Bookings</p>
                  <p className="text-2xl font-serif font-bold text-primary mt-2">{stats.total_bookings || 0}</p>
                </div>
                <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
                  <CalendarIcon className="text-primary" size={20} />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card data-testid="stat-active" className="bg-white rounded-2xl border border-border/50 shadow-sm">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Active Now</p>
                  <p className="text-2xl font-serif font-bold text-green-600 mt-2">{stats.active_bookings || 0}</p>
                </div>
                <div className="w-10 h-10 rounded-full bg-green-100 flex items-center justify-center">
                  <AlertCircleIcon className="text-green-600" size={20} />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card data-testid="stat-staff" className="bg-white rounded-2xl border border-border/50 shadow-sm">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Staff</p>
                  <p className="text-2xl font-serif font-bold text-primary mt-2">{stats.total_staff || 0}</p>
                </div>
                <div className="w-10 h-10 rounded-full bg-secondary/20 flex items-center justify-center">
                  <UsersIcon className="text-secondary-foreground" size={20} />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Management Sections */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <Card data-testid="admin-nav-bookings" className="bg-white rounded-2xl border border-border/50 shadow-sm cursor-pointer hover:shadow-lg hover:-translate-y-1 transition-all duration-300" onClick={() => navigate('/admin/bookings')}>
            <CardContent className="p-8">
              <div className="w-16 h-16 rounded-full bg-primary/10 mx-auto mb-4 flex items-center justify-center">
                <CalendarIcon className="text-primary" size={32} />
              </div>
              <h3 className="text-xl font-serif font-semibold text-center mb-2">Manage Bookings</h3>
              <p className="text-sm text-muted-foreground text-center">View and manage all reservations</p>
            </CardContent>
          </Card>

          <Card data-testid="admin-nav-staff" className="bg-white rounded-2xl border border-border/50 shadow-sm cursor-pointer hover:shadow-lg hover:-translate-y-1 transition-all duration-300" onClick={() => navigate('/admin/staff')}>
            <CardContent className="p-8">
              <div className="w-16 h-16 rounded-full bg-secondary/20 mx-auto mb-4 flex items-center justify-center">
                <UsersIcon className="text-secondary-foreground" size={32} />
              </div>
              <h3 className="text-xl font-serif font-semibold text-center mb-2">Staff Management</h3>
              <p className="text-sm text-muted-foreground text-center">Schedule and track staff</p>
            </CardContent>
          </Card>

          <Card data-testid="admin-nav-reports" className="bg-white rounded-2xl border border-border/50 shadow-sm cursor-pointer hover:shadow-lg hover:-translate-y-1 transition-all duration-300" onClick={() => navigate('/admin/reports')}>
            <CardContent className="p-8">
              <div className="w-16 h-16 rounded-full bg-primary/10 mx-auto mb-4 flex items-center justify-center">
                <BarChartIcon className="text-primary" size={32} />
              </div>
              <h3 className="text-xl font-serif font-semibold text-center mb-2">Reports & Analytics</h3>
              <p className="text-sm text-muted-foreground text-center">View business insights</p>
            </CardContent>
          </Card>

          <Card data-testid="admin-nav-customers" className="bg-white rounded-2xl border border-border/50 shadow-sm cursor-pointer hover:shadow-lg hover:-translate-y-1 transition-all duration-300" onClick={() => navigate('/admin/customers')}>
            <CardContent className="p-8">
              <div className="w-16 h-16 rounded-full bg-secondary/20 mx-auto mb-4 flex items-center justify-center">
                <UsersIcon className="text-secondary-foreground" size={32} />
              </div>
              <h3 className="text-xl font-serif font-semibold text-center mb-2">Customer Management</h3>
              <p className="text-sm text-muted-foreground text-center">View all customers and dogs</p>
            </CardContent>
          </Card>

          <Card data-testid="admin-nav-incidents" className="bg-white rounded-2xl border border-border/50 shadow-sm cursor-pointer hover:shadow-lg hover:-translate-y-1 transition-all duration-300" onClick={() => navigate('/admin/incidents')}>
            <CardContent className="p-8">
              <div className="w-16 h-16 rounded-full bg-red-100 mx-auto mb-4 flex items-center justify-center">
                <AlertCircleIcon className="text-red-600" size={32} />
              </div>
              <h3 className="text-xl font-serif font-semibold text-center mb-2">Incidents</h3>
              <p className="text-sm text-muted-foreground text-center">Review and manage incidents</p>
            </CardContent>
          </Card>

          <Card data-testid="admin-nav-audit" className="bg-white rounded-2xl border border-border/50 shadow-sm cursor-pointer hover:shadow-lg hover:-translate-y-1 transition-all duration-300" onClick={() => navigate('/admin/audit')}>
            <CardContent className="p-8">
              <div className="w-16 h-16 rounded-full bg-primary/10 mx-auto mb-4 flex items-center justify-center">
                <ShieldCheckIcon className="text-primary" size={32} />
              </div>
              <h3 className="text-xl font-serif font-semibold text-center mb-2">Audit Logs</h3>
              <p className="text-sm text-muted-foreground text-center">View system activity logs</p>
            </CardContent>
          </Card>

          <Card data-testid="admin-nav-timesheet" className="bg-white rounded-2xl border border-border/50 shadow-sm cursor-pointer hover:shadow-lg hover:-translate-y-1 transition-all duration-300" onClick={() => navigate('/admin/timesheet')}>
            <CardContent className="p-8">
              <div className="w-16 h-16 rounded-full bg-blue-100 mx-auto mb-4 flex items-center justify-center">
                <ClockIcon className="text-blue-600" size={32} />
              </div>
              <h3 className="text-xl font-serif font-semibold text-center mb-2">Staff Timesheets</h3>
              <p className="text-sm text-muted-foreground text-center">View employee work hours</p>
            </CardContent>
          </Card>

          <Card data-testid="admin-nav-time-management" className="bg-white rounded-2xl border border-border/50 shadow-sm cursor-pointer hover:shadow-lg hover:-translate-y-1 transition-all duration-300" onClick={() => navigate('/admin/time-management')}>
            <CardContent className="p-8">
              <div className="w-16 h-16 rounded-full bg-green-100 mx-auto mb-4 flex items-center justify-center">
                <ClockIcon className="text-green-600" size={32} />
              </div>
              <h3 className="text-xl font-serif font-semibold text-center mb-2">Time Management</h3>
              <p className="text-sm text-muted-foreground text-center">Pay periods & approvals</p>
            </CardContent>
          </Card>

          <Card data-testid="admin-nav-schedule" className="bg-white rounded-2xl border border-border/50 shadow-sm cursor-pointer hover:shadow-lg hover:-translate-y-1 transition-all duration-300" onClick={() => navigate('/admin/schedule')}>
            <CardContent className="p-8">
              <div className="w-16 h-16 rounded-full bg-indigo-100 mx-auto mb-4 flex items-center justify-center">
                <CalendarDaysIcon className="text-indigo-600" size={32} />
              </div>
              <h3 className="text-xl font-serif font-semibold text-center mb-2">Staff Schedule</h3>
              <p className="text-sm text-muted-foreground text-center">Shifts & swap requests</p>
            </CardContent>
          </Card>

          <Card data-testid="admin-nav-chat" className="bg-white rounded-2xl border border-border/50 shadow-sm cursor-pointer hover:shadow-lg hover:-translate-y-1 transition-all duration-300" onClick={() => navigate('/admin/chat')}>
            <CardContent className="p-8">
              <div className="w-16 h-16 rounded-full bg-purple-100 mx-auto mb-4 flex items-center justify-center">
                <MessageCircleIcon className="text-purple-600" size={32} />
              </div>
              <h3 className="text-xl font-serif font-semibold text-center mb-2">Messages</h3>
              <p className="text-sm text-muted-foreground text-center">Chat with staff & customers</p>
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  );
};

export default AdminDashboard;
