import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import useAuthStore from '../store/authStore';
import api from '../utils/api';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import {
  DogIcon, CalendarIcon, AlertCircleIcon, LogOutIcon,
  HomeIcon, ActivityIcon, ClipboardListIcon, RefreshCwIcon, ClockIcon, CameraIcon} from 'lucide-react';
import { toast } from 'sonner';

const StaffDashboard = () => {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();

  const handleClockIn = async () => {
    setShiftLoading(true);
    try {
      await api.post('/users/shift/clock-in');
      setOnShift(true);
      toast.success('Clocked in — have a great shift!');
    } catch { toast.error('Failed to clock in'); }
    finally { setShiftLoading(false); }
  };

  const handleClockOut = () => {
    // Navigate to handoff page which handles clock-out
    navigate('/staff/handoff');
  };
  const [data, setData] = useState(null);
  const [groups, setGroups] = useState([]);
  const [onShift, setOnShift] = useState(false);
  const [shiftLoading, setShiftLoading] = useState(false);
  const [handoffPrompt, setHandoffPrompt] = useState(null);
  const [careSummary, setCareSummary] = useState([]);

  useEffect(() => {
    if (!user?.id) return;
    const load = () => api.get('/care/on-site-summary')
      .then(res => setCareSummary(res.data || []))
      .catch(() => {});
    load();
    const timer = setInterval(load, 60000);
    return () => clearInterval(timer);
  }, [user?.id]);

  useEffect(() => {
    if (!user?.id) return;
    api.get('/care/handoffs', { params: { limit: 10 } })
      .then(res => {
        const latestFromOthers = (res.data || []).find(h => h.staff_id !== user.id);
        if (latestFromOthers && !latestFromOthers.acknowledged_at) {
          setHandoffPrompt(latestFromOthers);
        }
      })
      .catch(() => {});
  }, [user?.id]);
  const [loading, setLoading] = useState(true);

  const fetchDashboard = useCallback(async () => {
    try {
      const [dashRes, groupsRes] = await Promise.all([
        api.get('/dashboard'),
        api.get('/playgroups/today').catch(() => ({ data: [] })),
      ]);
      setData(dashRes.data);
      setGroups(groupsRes.data || []);
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

  if (loading || !data) return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-primary"></div>
    </div>
  );

  return (
    <div className="min-h-screen bg-[#F9F7F2]">
      {handoffPrompt && (
        <HandoffPromptModal
          handoff={handoffPrompt}
          onClose={() => setHandoffPrompt(null)}
          onAcknowledged={() => setHandoffPrompt(null)}
          onViewAll={() => navigate('/staff/handoff')}
        />
      )}
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
          <ActionCard
            icon={<CameraIcon size={22} />}
            label="Daily Update"
            sublabel="Send a photo/note update"
            onClick={() => navigate('/staff/daily-update')}
          />
        </div>

        {careSummary.length > 0 && <OnSiteCareCard summary={careSummary} />}
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

        {/* Today's Groups */}
        {groups.length > 0 && (
          <div className="bg-white rounded-xl border shadow-sm p-4">
            <h2 className="font-serif font-semibold text-primary mb-3 text-sm">Today's Groups</h2>
            <div className="space-y-2">
              {groups.map(g => (
                <div key={g.group_number} className="flex items-center gap-2 flex-wrap">
                  <span className="text-xs font-medium bg-primary/10 text-primary px-2 py-0.5 rounded-full">
                    {g.label || `Group ${g.group_number}`}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {g.dogs?.map(m => m.dog_name).join(', ')}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
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

const OnSiteCareCard = ({ summary }) => (
  <Card>
    <CardHeader className="pb-2 pt-4">
      <CardTitle className="text-sm">Feeding & Medications ({summary.length} on site)</CardTitle>
    </CardHeader>
    <CardContent className="px-4 pb-4 space-y-3">
      {summary.map(d => {
        const hasFeeding = d.feeding_plans.length > 0 || d.meal_routine;
        const hasMeds = d.medications.length > 0 || d.medication_requirements;
        return (
          <div key={d.dog_id} className="border-b last:border-0 pb-2 last:pb-0">
            <div className="flex items-center gap-2 flex-wrap">
              <p className="text-sm font-medium">{d.dog_name}</p>
              {d.allergies && (
                <Badge className="text-xs bg-red-100 text-red-700">Allergies: {d.allergies}</Badge>
              )}
            </div>
            {!hasFeeding && !hasMeds && (
              <p className="text-xs text-muted-foreground mt-0.5">No feeding or medication info on file</p>
            )}
            {d.feeding_plans.map((p, i) => (
              <p key={i} className="text-xs mt-0.5">
                🍽 {p.food_name}, {p.amount}, {p.frequency}
                {p.food_supplied_by_owner ? ' (owner supplied)' : ''}
                {p.preparation_instructions ? ` — ${p.preparation_instructions}` : ''}
              </p>
            ))}
            {d.feeding_plans.length === 0 && d.meal_routine && (
              <p className="text-xs mt-0.5">🍽 {d.meal_routine}</p>
            )}
            {d.medications.map((m, i) => (
              <p key={i} className="text-xs mt-0.5 text-amber-800">
                💊 {m.name} {m.dose}, {m.frequency}{m.as_needed ? ' (as needed)' : ''}
                {m.instructions ? ` — ${m.instructions}` : ''}
              </p>
            ))}
            {d.medications.length === 0 && d.medication_requirements && (
              <p className="text-xs mt-0.5 text-amber-800">💊 {d.medication_requirements}</p>
            )}
          </div>
        );
      })}
    </CardContent>
  </Card>
);

const HandoffPromptModal = ({ handoff, onClose, onAcknowledged, onViewAll }) => {
  const [acknowledging, setAcknowledging] = useState(false);

  const itemText = (x) => {
    if (x == null) return '';
    if (typeof x === 'string') return x;
    return x.title || x.description || x.text || x.note || x.item || x.summary || JSON.stringify(x);
  };

  const handleAcknowledge = async () => {
    setAcknowledging(true);
    try {
      await api.post(`/care/handoffs/${handoff.id}/acknowledge`);
      toast.success('Handoff acknowledged');
      onAcknowledged();
    } catch {
      toast.error('Failed to acknowledge handoff');
    } finally {
      setAcknowledging(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-end md:items-center justify-center p-4">
      <div className="bg-white rounded-t-2xl md:rounded-2xl w-full max-w-md max-h-[90vh] overflow-y-auto">
        <div className="p-5 space-y-4">
          <div>
            <h2 className="text-lg font-bold">Previous Shift Handoff</h2>
            <p className="text-xs text-muted-foreground mt-1">
              From {handoff.staff_name}
              {handoff.submitted_at ? ` · ${new Date(handoff.submitted_at).toLocaleString()}` : ''}
            </p>
          </div>

          {handoff.staff_notes && (
            <div>
              <p className="text-xs font-medium text-muted-foreground mb-1">Notes</p>
              <p className="text-sm whitespace-pre-wrap">{handoff.staff_notes}</p>
            </div>
          )}

          {handoff.dogs_on_site_snapshot?.length > 0 && (
            <div>
              <p className="text-xs font-medium text-muted-foreground mb-1">Dogs on site ({handoff.dogs_on_site_snapshot.length})</p>
              <div className="flex flex-wrap gap-1">
                {handoff.dogs_on_site_snapshot.map((d, i) => (
                  <Badge key={i} variant="outline" className="text-xs">{d.name}{d.room ? ` · ${d.room}` : ''}</Badge>
                ))}
              </div>
            </div>
          )}

          {handoff.active_medications?.length > 0 && (
            <div>
              <p className="text-xs font-medium text-amber-700 mb-1">Medications</p>
              {handoff.active_medications.map((m, i) => (
                <p key={i} className="text-xs">{m.dog}: {m.medication} {m.dosage} — {m.frequency}</p>
              ))}
            </div>
          )}

          {handoff.active_alerts?.length > 0 && (
            <div>
              <p className="text-xs font-medium text-red-700 mb-1">Active Alerts</p>
              {handoff.active_alerts.map((a, i) => (
                <p key={i} className="text-xs">{a.dog}: {a.alert}</p>
              ))}
            </div>
          )}

          {handoff.open_incidents?.length > 0 && (
            <div>
              <p className="text-xs font-medium text-orange-700 mb-1">Open Incidents</p>
              {handoff.open_incidents.map((inc, i) => (
                <p key={i} className="text-xs">{itemText(inc)}</p>
              ))}
            </div>
          )}

          {handoff.outstanding_care?.length > 0 && (
            <div>
              <p className="text-xs font-medium text-muted-foreground mb-1">Outstanding Care</p>
              {handoff.outstanding_care.map((c, i) => (
                <p key={i} className="text-xs">{itemText(c)}</p>
              ))}
            </div>
          )}

          {handoff.follow_up_items?.length > 0 && (
            <div>
              <p className="text-xs font-medium text-muted-foreground mb-1">Follow-ups</p>
              {handoff.follow_up_items.map((f, i) => (
                <p key={i} className="text-xs">{itemText(f)}</p>
              ))}
            </div>
          )}

          <div className="space-y-2 pt-1">
            <Button className="w-full" onClick={handleAcknowledge} disabled={acknowledging}>
              {acknowledging ? 'Saving...' : 'Acknowledge Handoff'}
            </Button>
            <div className="flex gap-2">
              <Button variant="outline" className="flex-1 text-xs" onClick={onViewAll}>View Full Handoff</Button>
              <Button variant="ghost" className="flex-1 text-xs text-muted-foreground" onClick={onClose}>Not Now</Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default StaffDashboard;
