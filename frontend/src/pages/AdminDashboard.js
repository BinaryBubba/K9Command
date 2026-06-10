import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import useAuthStore from '../store/authStore';
import api from '../utils/api';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import {
  DogIcon, CalendarIcon, AlertCircleIcon, LogOutIcon,
  ClockIcon, ActivityIcon, HomeIcon, UsersIcon, RefreshCwIcon,
} from 'lucide-react';
import { toast } from 'sonner';

const AdminDashboard = () => {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchDashboard = useCallback(async () => {
    try {
      const res = await api.get('/dashboard');
      setData(res.data);
    } catch {
      toast.error('Failed to load dashboard');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!user || user.role !== 'admin') { navigate('/auth'); return; }
    fetchDashboard();
    const interval = setInterval(fetchDashboard, 60000);
    return () => clearInterval(interval);
  }, [user, navigate, fetchDashboard]);

  const handleLogout = () => { logout(); navigate('/'); };

  if (loading || !data) return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <div className="inline-block animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div>
        <p className="mt-4 text-muted-foreground">Loading K9CMD...</p>
      </div>
    </div>
  );

  const pendingHandoff = data?.unacknowledged_handoffs?.length > 0 ?? false;

  return (
    <div className="min-h-screen bg-[#F9F7F2]">
      {/* Header */}
      <header className="bg-white border-b border-border/40 shadow-sm sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 md:px-8 py-3 flex justify-between items-center">
          <div>
            <h1 className="text-xl font-serif font-bold text-primary">K9 Command</h1>
            <p className="text-xs text-muted-foreground">Welcome back, {user?.full_name}</p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" onClick={fetchDashboard}>
              <RefreshCwIcon size={16} />
            </Button>
            <Button variant="ghost" size="sm" onClick={handleLogout}>
              <LogOutIcon size={16} className="mr-1" /> Logout
            </Button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 md:px-8 py-6 space-y-6">

        {/* Unacknowledged handoff banner */}
        {pendingHandoff && (
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 flex items-center justify-between">
            <div className="flex items-center gap-2 text-amber-800">
              <AlertCircleIcon size={18} />
              <span className="font-medium">Unacknowledged shift handoff requires review</span>
            </div>
            <Button size="sm" variant="outline" onClick={() => navigate('/admin/operations')}>
              Review
            </Button>
          </div>
        )}

        {/* Warning alerts */}
        {data?.warning_alerts?.length > 0 && (
          <div className="space-y-2">
            {data.warning_alerts.map(alert => (
              <div key={alert.id} className="bg-red-50 border border-red-200 rounded-lg p-3 flex items-center gap-3">
                <AlertCircleIcon size={18} className="text-red-600 flex-shrink-0" />
                <span className="text-red-800 text-sm font-medium">{alert.alert_message}</span>
                <Badge variant="destructive" className="ml-auto">Warning</Badge>
              </div>
            ))}
          </div>
        )}

        {/* Summary cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <SummaryCard icon={<DogIcon size={20} />} label="On Site" value={data?.on_site_count ?? 0} color="blue" onClick={() => navigate('/admin/kennels')} />
          <SummaryCard icon={<CalendarIcon size={20} />} label="Arriving Today" value={data?.arriving_today_count ?? 0} color="green" onClick={() => navigate('/admin/check-in-out')} />
          <SummaryCard icon={<ClockIcon size={20} />} label="Departing Today" value={data?.departing_today_count ?? 0} color="orange" onClick={() => navigate('/admin/check-in-out')} />
          <SummaryCard icon={<AlertCircleIcon size={20} />} label="Active Alerts" value={data?.active_alert_count ?? 0} color={data?.warning_alert_count > 0 ? 'red' : 'gray'} />
        </div>

        {/* Two-column layout */}
        <div className="grid md:grid-cols-2 gap-6">

          {/* Arriving soon */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <CalendarIcon size={16} className="text-green-600" />
                Arriving Soon
              </CardTitle>
            </CardHeader>
            <CardContent>
              {data?.arriving_soon?.length === 0 ? (
                <p className="text-sm text-muted-foreground">No arrivals in the next 2 hours</p>
              ) : (
                <div className="space-y-2">
                  {data.arriving_soon.map(b => (
                    <div key={b.booking_id} className="flex items-center justify-between py-2 border-b last:border-0">
                      <div>
                        <p className="text-sm font-medium">{b.dog_ids?.length} dog{b.dog_ids?.length !== 1 ? 's' : ''}</p>
                        <p className="text-xs text-muted-foreground">{new Date(b.check_in_date).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</p>
                      </div>
                      <Button size="sm" variant="outline" onClick={() => navigate('/admin/check-in-out')}>Check In</Button>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Departing soon */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <ClockIcon size={16} className="text-orange-600" />
                Departing Soon
              </CardTitle>
            </CardHeader>
            <CardContent>
              {data?.departing_soon?.length === 0 ? (
                <p className="text-sm text-muted-foreground">No departures in the next 2 hours</p>
              ) : (
                <div className="space-y-2">
                  {data.departing_soon.map(s => (
                    <div key={s.stay_id} className="flex items-center justify-between py-2 border-b last:border-0">
                      <p className="text-sm font-medium">Dog in {s.room_id ? 'Room' : 'unassigned'}</p>
                      <Button size="sm" variant="outline" onClick={() => navigate('/admin/check-in-out')}>Check Out</Button>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

        </div>

        {/* Room occupancy */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <HomeIcon size={16} className="text-blue-600" />
              Room Occupancy
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-4 md:grid-cols-8 gap-2">
              {data?.room_occupancy?.map(room => (
                <div
                  key={room.room_id}
                  onClick={() => navigate('/admin/kennels')}
                  className={`cursor-pointer rounded-lg p-2 text-center border transition-colors ${
                    room.is_out_of_service ? 'bg-gray-100 border-gray-200 opacity-50' :
                    room.current_dogs === 0 ? 'bg-green-50 border-green-200 hover:bg-green-100' :
                    room.current_dogs >= room.max_dogs ? 'bg-red-50 border-red-200' :
                    'bg-blue-50 border-blue-200 hover:bg-blue-100'
                  }`}
                >
                  <p className="text-xs font-medium truncate">{room.room_name}</p>
                  <p className="text-lg font-bold">{room.current_dogs}</p>
                  <p className="text-xs text-muted-foreground">/{room.max_dogs}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Quick actions */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <QuickAction label="Check In / Out" icon={<ActivityIcon size={18} />} onClick={() => navigate('/admin/check-in-out')} />
          <QuickAction label="Bookings" icon={<CalendarIcon size={18} />} onClick={() => navigate('/admin/bookings')} />
          <QuickAction label="Customers" icon={<UsersIcon size={18} />} onClick={() => navigate('/admin/customers')} />
          <QuickAction label="Kennels" icon={<HomeIcon size={18} />} onClick={() => navigate('/admin/kennels')} />
        </div>

      </main>
    </div>
  );
};

const SummaryCard = ({ icon, label, value, color, onClick }) => {
  const colors = {
    blue: 'text-blue-600 bg-blue-50',
    green: 'text-green-600 bg-green-50',
    orange: 'text-orange-600 bg-orange-50',
    red: 'text-red-600 bg-red-50',
    gray: 'text-gray-600 bg-gray-50',
  };
  return (
    <Card className={`cursor-pointer hover:shadow-md transition-shadow ${onClick ? '' : ''}`} onClick={onClick}>
      <CardContent className="pt-4 pb-4">
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-lg ${colors[color] || colors.gray}`}>{icon}</div>
          <div>
            <p className="text-2xl font-bold">{value}</p>
            <p className="text-xs text-muted-foreground">{label}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

const QuickAction = ({ label, icon, onClick }) => (
  <Button variant="outline" className="h-16 flex flex-col gap-1 text-xs" onClick={onClick}>
    {icon}
    {label}
  </Button>
);

export default AdminDashboard;
