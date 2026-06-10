import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import useAuthStore from '../store/authStore';
import api from '../utils/api';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import {
  DogIcon, CalendarIcon, AlertCircleIcon, LogOutIcon,
  HomeIcon, ActivityIcon, ClipboardListIcon, RefreshCwIcon,
} from 'lucide-react';
import { toast } from 'sonner';

const StaffDashboard = () => {
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
    if (!user) { navigate('/auth'); return; }
    fetchDashboard();
    const interval = setInterval(fetchDashboard, 60000);
    return () => clearInterval(interval);
  }, [user, navigate, fetchDashboard]);

  const handleLogout = () => { logout(); navigate('/'); };

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-primary"></div>
    </div>
  );

  return (
    <div className="min-h-screen bg-[#F9F7F2]">
      <header className="bg-white border-b shadow-sm sticky top-0 z-10">
        <div className="max-w-2xl mx-auto px-4 py-3 flex justify-between items-center">
          <div>
            <h1 className="text-lg font-serif font-bold text-primary">K9 Command</h1>
            <p className="text-xs text-muted-foreground">Hi {user?.full_name?.split(' ')[0]}</p>
          </div>
          <div className="flex items-center gap-1">
            <Button variant="ghost" size="sm" onClick={fetchDashboard}>
              <RefreshCwIcon size={16} />
            </Button>
            <Button variant="ghost" size="sm" onClick={handleLogout}>
              <LogOutIcon size={16} />
            </Button>
          </div>
        </div>
      </header>

      <main className="max-w-2xl mx-auto px-4 py-5 space-y-5">

        {/* Warning alerts — always at top */}
        {data?.warning_alerts?.length > 0 && (
          <div className="space-y-2">
            {data.warning_alerts.map(alert => (
              <div key={alert.id} className="bg-red-50 border border-red-200 rounded-lg p-3 flex items-start gap-2">
                <AlertCircleIcon size={16} className="text-red-600 mt-0.5 flex-shrink-0" />
                <div>
                  <p className="text-sm font-medium text-red-800">{alert.alert_message}</p>
                  <p className="text-xs text-red-600 mt-0.5">Severity: Warning</p>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Summary row */}
        <div className="grid grid-cols-2 gap-3">
          <StatPill icon={<DogIcon size={16} />} value={data?.on_site_count ?? 0} label="On Site" color="blue" />
          <StatPill icon={<CalendarIcon size={16} />} value={data?.arriving_today_count ?? 0} label="Arriving" color="green" />
          <StatPill icon={<ClockIcon size={16} />} value={data?.departing_today_count ?? 0} label="Departing" color="orange" />
          <StatPill icon={<AlertCircleIcon size={16} />} value={data?.active_alert_count ?? 0} label="Alerts"
            color={data?.warning_alert_count > 0 ? 'red' : 'gray'} />
        </div>

        {/* Quick actions — big tap targets for phone */}
        <div className="grid grid-cols-2 gap-3">
          <ActionCard
            icon={<ActivityIcon size={22} />}
            label="Check In / Out"
            sublabel={`${data?.arriving_today_count ?? 0} arriving · ${data?.departing_today_count ?? 0} departing`}
            onClick={() => navigate('/staff/check-in-out')}
            highlight={data?.arriving_today_count > 0 || data?.departing_today_count > 0}
          />
          <ActionCard
            icon={<HomeIcon size={22} />}
            label="Occupancy Board"
            sublabel={`${data?.on_site_count ?? 0} dogs on site`}
            onClick={() => navigate('/admin/kennels')}
          />
          <ActionCard
            icon={<ClipboardListIcon size={22} />}
            label="My Tasks"
            sublabel="View assigned tasks"
            onClick={() => navigate('/staff/tasks')}
          />
          <ActionCard
            icon={<CalendarIcon size={22} />}
            label="Bookings"
            sublabel="View schedule"
            onClick={() => navigate('/staff/bookings')}
          />
        </div>

        {/* Caution alerts */}
        {data?.caution_alerts?.length > 0 && (
          <Card>
            <CardHeader className="pb-2 pt-4">
              <CardTitle className="text-sm flex items-center gap-2">
                <AlertCircleIcon size={14} className="text-amber-500" />
                Active Alerts
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {data.caution_alerts.slice(0, 5).map(alert => (
                <div key={alert.id} className="flex items-start gap-2 p-2 bg-amber-50 rounded border border-amber-100">
                  <AlertCircleIcon size={14} className="text-amber-500 mt-0.5 flex-shrink-0" />
                  <p className="text-xs text-amber-800">{alert.alert_message}</p>
                </div>
              ))}
            </CardContent>
          </Card>
        )}

        {/* Room occupancy compact */}
        <Card>
          <CardHeader className="pb-2 pt-4">
            <CardTitle className="text-sm flex items-center gap-2">
              <HomeIcon size={14} className="text-blue-500" />
              Rooms
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-8 gap-1">
              {data?.room_occupancy?.map(room => (
                <div key={room.room_id} className="text-center">
                  <div className={`h-8 w-full rounded flex items-center justify-center text-xs font-bold ${
                    room.is_out_of_service ? 'bg-gray-200 text-gray-400' :
                    room.current_dogs === 0 ? 'bg-green-100 text-green-700' :
                    room.current_dogs >= room.max_dogs ? 'bg-red-100 text-red-700' :
                    'bg-blue-100 text-blue-700'
                  }`}>
                    {room.current_dogs}
                  </div>
                  <p className="text-xs text-muted-foreground mt-0.5 truncate">{room.room_name.replace('Room ', '')}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

      </main>
    </div>
  );
};

const StatPill = ({ icon, value, label, color }) => {
  const colors = {
    blue: 'bg-blue-50 text-blue-700',
    green: 'bg-green-50 text-green-700',
    red: 'bg-red-50 text-red-700',
    orange: 'bg-orange-50 text-orange-700',
    gray: 'bg-gray-50 text-gray-600',
  };
  return (
    <div className={`rounded-xl p-3 text-center ${colors[color] || colors.gray}`}>
      <div className="flex justify-center mb-1">{icon}</div>
      <p className="text-xl font-bold">{value}</p>
      <p className="text-xs">{label}</p>
    </div>
  );
};

const ActionCard = ({ icon, label, sublabel, onClick, highlight }) => (
  <button
    onClick={onClick}
    className={`w-full text-left p-4 rounded-xl border transition-all active:scale-95 ${
      highlight
        ? 'bg-primary text-primary-foreground border-primary shadow-sm'
        : 'bg-white border-border hover:shadow-md'
    }`}
  >
    <div className="mb-2">{icon}</div>
    <p className="font-semibold text-sm">{label}</p>
    <p className={`text-xs mt-0.5 ${highlight ? 'text-primary-foreground/80' : 'text-muted-foreground'}`}>
      {sublabel}
    </p>
  </button>
);

export default StaffDashboard;
