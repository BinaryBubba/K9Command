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
  const [groups, setGroups] = useState([]);
  const [activeStaff, setActiveStaff] = useState([]);
  const [pendingRequests, setPendingRequests] = useState(0);
  const [upcomingMags, setUpcomingMags] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchDashboard = useCallback(async () => {
    try {
      const [res, groupsRes, shiftRes, pendingRes, magsRes] = await Promise.all([
        api.get('/dashboard'),
        api.get('/playgroups/today').catch(() => ({ data: [] })),
        api.get('/users/shift/active').catch(() => ({ data: [] })),
        api.get('/bookings', { params: { status: 'PENDING', limit: 100 } }).catch(() => ({ data: [] })),
        api.get('/meet-and-greets/upcoming').catch(() => ({ data: [] })),
      ]);
      setData(res.data);
      setGroups(groupsRes.data || []);
      setActiveStaff(shiftRes?.data || []);
      const pendingBookings = pendingRes?.data || [];
      if (pendingBookings.length > 0) setPendingRequests(pendingBookings.length);
      setUpcomingMags(magsRes?.data || []);
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
                        <p className="text-sm font-medium">{b.dog_names?.join(', ') || `${b.dog_ids?.length} dog${b.dog_ids?.length !== 1 ? 's' : ''}`}</p>
                        <p className="text-xs text-muted-foreground">{b.household_name} · {new Date(b.check_in_date).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</p>
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
                      <div>
                        <p className="text-sm font-medium">{s.dog_name || 'Unknown dog'}</p>
                        <p className="text-xs text-muted-foreground">{s.household_name}{s.room_name ? ` · ${s.room_name}` : ''} · {s.check_out_date ? new Date(s.check_out_date).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) : ''}</p>
                      </div>
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


        {/* Pending Booking Requests */}
        {pendingRequests > 0 && (
          <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-center justify-between cursor-pointer"
            onClick={() => navigate('/admin/bookings?filter=requests')}>
            <div>
              <p className="font-semibold text-amber-900">{pendingRequests} Pending Booking Request{pendingRequests !== 1 ? 's' : ''}</p>
              <p className="text-xs text-amber-700">Customer requests awaiting review</p>
            </div>
            <span className="text-amber-600 text-xl">→</span>
          </div>
        )}

        {/* Upcoming Meet & Greets */}
        {upcomingMags.length > 0 && (
          <div className="bg-white rounded-xl border shadow-sm p-4">
            <h2 className="font-serif font-semibold text-primary mb-3 text-sm flex items-center justify-between">
              Upcoming Meet & Greets
              <span className="text-xs bg-primary/10 text-primary px-2 py-0.5 rounded-full">{upcomingMags.length}</span>
            </h2>
            <div className="space-y-2">
              {upcomingMags.map(m => (
                <div key={m.id} className="flex items-center justify-between py-1.5 border-b last:border-0">
                  <div>
                    <p className="text-sm font-medium">{m.dog_name} <span className="text-muted-foreground font-normal">— {m.household_name}</span></p>
                    <p className="text-xs text-muted-foreground">
                      {new Date(m.scheduled_at).toLocaleDateString([], {weekday:'short',month:'short',day:'numeric'})} · {m.slot === '10:00-12:00' ? '10am–noon' : '2pm–4pm'}
                    </p>
                    {m.requested_stay_start && (
                      <p className="text-xs text-blue-600">
                        Stay: {new Date(m.requested_stay_start+'T12:00:00').toLocaleDateString([], {month:'short',day:'numeric'})} – {new Date(m.requested_stay_end+'T12:00:00').toLocaleDateString([], {month:'short',day:'numeric'})}
                      </p>
                    )}
                  </div>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${m.status === 'pending' ? 'bg-amber-100 text-amber-700' : 'bg-green-100 text-green-700'}`}>
                    {m.status}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Who's On Shift */}
        <div className="bg-white rounded-xl border shadow-sm p-4">
          <h2 className="font-serif font-semibold text-primary mb-3">Who's On Shift</h2>
          {activeStaff.length === 0 ? (
            <p className="text-sm text-muted-foreground">No staff currently clocked in</p>
          ) : (
            <div className="space-y-2">
              {activeStaff.map(s => (
                <div key={s.id} className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-green-500"></div>
                    <span className="text-sm font-medium">{s.full_name}</span>
                    <span className="text-xs text-muted-foreground capitalize">{s.role}</span>
                  </div>
                  {s.shift_started_at && (
                    <span className="text-xs text-muted-foreground">
                      since {new Date(s.shift_started_at).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'})}
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Today's Playgroups */}
        <div className="bg-white rounded-xl border shadow-sm p-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-serif font-semibold text-primary">Today's Groups</h2>
            <button className="text-xs text-primary hover:underline" onClick={() => navigate('/admin/playgroups')}>
              Manage →
            </button>
          </div>
          {groups.length === 0 ? (
            <div className="text-center py-3">
              <p className="text-sm text-muted-foreground">No groups set today</p>
              <Button size="sm" className="mt-2" onClick={() => navigate('/admin/playgroups')}>Set Up Groups</Button>
            </div>
          ) : (
            <div className="space-y-2">
              {groups.map((group, i) => (
                <div key={group.id} className={`p-2 rounded-lg border text-xs ${
                  group.is_individual ? 'bg-gray-50 border-gray-200' : 'bg-blue-50 border-blue-200'
                }`}>
                  <div className="flex items-center justify-between">
                    <span className="font-medium">{group.is_individual ? '👤' : `Group ${group.group_number}`} {group.label}</span>
                    <span className="text-muted-foreground">{group.dogs.length} dog{group.dogs.length !== 1 ? 's' : ''}</span>
                  </div>
                  <p className="text-muted-foreground mt-0.5">{group.dogs.map(d => d.dog_name).join(', ')}</p>
                </div>
              ))}
            </div>
          )}
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
