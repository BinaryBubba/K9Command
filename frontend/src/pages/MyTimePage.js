import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import ShiftStatusBanner from '../components/time/ShiftStatusBanner';
import {
  ArrowLeftIcon,
  ClockIcon,
  PlayIcon,
  StopCircleIcon,
  EditIcon,
  AlertCircleIcon,
  MapPinIcon
} from 'lucide-react';
import { toast } from 'sonner';
import api from '../utils/api';
import useAuthStore from '../store/authStore';

function shiftDate(value) {
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? null : d;
}

function getClockInValue(entry) {
  return entry?.clock_in || entry?.clockIn || null;
}

function getClockOutValue(entry) {
  return entry?.clock_out || entry?.clockOut || null;
}

function normalizeEntry(entry) {
  if (!entry || typeof entry !== 'object') return entry;
  const normalizedClockIn = entry.clock_in || entry.clockIn || null;
  const normalizedClockOut = entry.clock_out || entry.clockOut || null;
  return {
    ...entry,
    clock_in: normalizedClockIn,
    clock_out: normalizedClockOut,
    status: entry.status || (normalizedClockIn && !normalizedClockOut ? 'active' : entry.status),
  };
}

function isSameDay(a, b) {
  return a.toDateString() === b.toDateString();
}

function sortShifts(shifts = []) {
  return [...shifts].sort((a, b) => {
    const ad = shiftDate(a.start_time)?.getTime() || 0;
    const bd = shiftDate(b.start_time)?.getTime() || 0;
    return ad - bd;
  });
}

function getCurrentShift(shifts = [], now = new Date()) {
  return sortShifts(shifts).find((shift) => {
    const start = shiftDate(shift.start_time);
    const end = shiftDate(shift.end_time);
    return start && end && now >= start && now <= end;
  }) || null;
}

function getNextShift(shifts = [], now = new Date()) {
  const soonMs = 30 * 60 * 1000;
  return sortShifts(shifts).find((shift) => {
    const start = shiftDate(shift.start_time);
    return start && start > now && (start.getTime() - now.getTime()) <= soonMs;
  }) || null;
}

function entryOverlapsShift(entry, shift) {
  const entryStart = shiftDate(entry.clock_in);
  const entryEnd = entry.clock_out ? shiftDate(entry.clock_out) : new Date();
  const shiftStart = shiftDate(shift.start_time);
  const shiftEnd = shiftDate(shift.end_time);

  if (!entryStart || !entryEnd || !shiftStart || !shiftEnd) return false;
  return entryStart < shiftEnd && entryEnd > shiftStart;
}

function getMissedShift(shifts = [], entries = [], activeEntry, now = new Date()) {
  if (activeEntry) return null;

  const pastTodayShifts = sortShifts(shifts).filter((shift) => {
    const start = shiftDate(shift.start_time);
    const end = shiftDate(shift.end_time);
    return start && end && isSameDay(start, now) && now > end;
  });

  const missed = pastTodayShifts.filter((shift) => {
    const matchedEntry = entries.some((entry) => entryOverlapsShift(entry, shift));
    return !matchedEntry;
  });

  return missed.length > 0 ? missed[missed.length - 1] : null;
}

function classifyClockTiming(currentShift, now = new Date()) {
  if (!currentShift) return 'outside_shift';
  const start = shiftDate(currentShift.start_time);
  if (!start) return 'unknown';
  if (now < start) return 'early';
  if (now > start) return 'late';
  return 'on_time';
}

const MyTimePage = () => {
  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);

  const [timeEntries, setTimeEntries] = useState([]);
  const [modRequests, setModRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [clockedIn, setClockedIn] = useState(false);
  const [currentEntry, setCurrentEntry] = useState(null);
  const [clockingAction, setClockingAction] = useState(false);
  const [gpsPosition, setGpsPosition] = useState(null);
  const [gpsError, setGpsError] = useState(null);
  const [scheduleLoading, setScheduleLoading] = useState(false);
  const [scheduleWeekOffset, setScheduleWeekOffset] = useState(0);
  const [scheduleShifts, setScheduleShifts] = useState([]);
  const [swapRequests, setSwapRequests] = useState([]);

  const [modModalOpen, setModModalOpen] = useState(false);
  const [selectedEntry, setSelectedEntry] = useState(null);
  const [modForm, setModForm] = useState({
    requested_clock_in: '',
    requested_clock_out: '',
    reason: '',
  });

  const [liveNow, setLiveNow] = useState(Date.now());
  const [currentDuration, setCurrentDuration] = useState('--:--');

  useEffect(() => {
    const timer = setInterval(() => {
      setLiveNow(Date.now());
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    if (!user || user.role !== 'staff') {
      navigate('/auth');
      return;
    }
    fetchData();
    fetchScheduleData(0);
    getGPSPosition().catch(() => {});
  }, [user, navigate]);

  useEffect(() => {
    if (!user || user.role !== 'staff') return;

    const timer = setInterval(() => {
      syncCurrentTimeState();
    }, 5000);

    return () => clearInterval(timer);
  }, [user]);


  const now = useMemo(() => new Date(liveNow), [liveNow]);

  const activeEntry = useMemo(() => {
    if (getClockInValue(currentEntry)) return normalizeEntry(currentEntry);
    return (
      timeEntries.find((entry) => entry?.status === 'active') ||
      timeEntries.find((entry) => getClockInValue(entry) && !getClockOutValue(entry)) ||
      null
    );
  }, [currentEntry, timeEntries]);


  const fetchScheduleData = async (weekOffset = scheduleWeekOffset) => {
    setScheduleLoading(true);
    try {
      const base = new Date();
      base.setDate(base.getDate() + weekOffset * 7);

      const day = base.getDay();
      const diffToMonday = day === 0 ? -6 : 1 - day;

      const weekStart = new Date(base);
      weekStart.setDate(base.getDate() + diffToMonday);
      weekStart.setHours(0, 0, 0, 0);

      const weekEnd = new Date(weekStart);
      weekEnd.setDate(weekStart.getDate() + 6);
      weekEnd.setHours(23, 59, 59, 999);

      const [shiftsRes, swapsRes] = await Promise.all([
        api.get('/scheduling/shifts', {
          params: {
            start_date: weekStart.toISOString(),
            end_date: weekEnd.toISOString(),
          },
        }),
        api.get('/scheduling/swap-requests'),
      ]);

      setScheduleShifts(shiftsRes.data || []);
      setSwapRequests(swapsRes.data || []);
    } catch (error) {
      toast.error('Failed to load schedule data');
    } finally {
      setScheduleLoading(false);
    }
  };

  const syncCurrentTimeState = async () => {
    try {
      const currentRes = await api.get('/time-entries/current');
      const entriesRes = await api.get('/time-entries');

      const entries = (entriesRes.data || []).map(normalizeEntry);
      const normalizedCurrentEntry = normalizeEntry(currentRes.data?.entry);
      const fallbackActiveEntry =
        entries.find((entry) => entry?.status === 'active') ||
        entries.find((entry) => getClockInValue(entry) && !getClockOutValue(entry)) ||
        null;

      const resolvedCurrentEntry = normalizedCurrentEntry || fallbackActiveEntry || null;
      const resolvedClockedIn = Boolean(
        currentRes.data?.clocked_in ||
        resolvedCurrentEntry
      );

      setTimeEntries(entries);
      setClockedIn(resolvedClockedIn);
      setCurrentEntry(resolvedCurrentEntry);
    } catch (error) {
      console.error('Failed to sync current time state', error);
    }
  };

  const fetchData = async () => {
    try {
      const [entriesRes, currentRes, modRes] = await Promise.all([
        // debug: inspect active entry payload shape
        api.get('/time-entries'),
        api.get('/time-entries/current'),
        api.get('/time-entries/modification-requests'),
      ]);

      console.log('[MyTime fetchData]', {
        current_clocked_in: currentRes.data?.clocked_in,
        current_entry: currentRes.data?.entry,
        raw_current_response: currentRes.data,
      });

      const entries = (entriesRes.data || []).map(normalizeEntry);
      const normalizedCurrentEntry = normalizeEntry(currentRes.data?.entry);
      const fallbackActiveEntry =
        entries.find((entry) => entry?.status === 'active') ||
        entries.find((entry) => getClockInValue(entry) && !getClockOutValue(entry)) ||
        null;

      const resolvedCurrentEntry = normalizedCurrentEntry || fallbackActiveEntry || null;
      const resolvedClockedIn = Boolean(
        currentRes.data?.clocked_in ||
        resolvedCurrentEntry
      );

      setTimeEntries(entries);
      setClockedIn(resolvedClockedIn);
      setCurrentEntry(resolvedCurrentEntry);
      setModRequests(modRes.data || []);
    } catch (error) {
      toast.error('Failed to load time data');
    } finally {
      setLoading(false);
    }
  };

  const getGPSPosition = () => {
    return new Promise((resolve, reject) => {
      if (!navigator.geolocation) {
        reject(new Error('Geolocation not supported'));
        return;
      }

      navigator.geolocation.getCurrentPosition(
        (position) => {
          const pos = {
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
            accuracy: position.coords.accuracy,
          };
          setGpsPosition(pos);
          setGpsError(null);
          resolve(pos);
        },
        (error) => {
          setGpsError(error.message);
          reject(error);
        },
        { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 }
      );
    });
  };

  const todaysShifts = useMemo(() => {
    return sortShifts(scheduleShifts).filter((shift) => {
      const start = shiftDate(shift.start_time);
      return start && isSameDay(start, now);
    });
  }, [scheduleShifts, now]);

  const currentShift = useMemo(() => getCurrentShift(todaysShifts, now), [todaysShifts, now]);
  const nextShift = useMemo(() => getNextShift(todaysShifts, now), [todaysShifts, now]);
  const missedShift = useMemo(
    () => getMissedShift(todaysShifts, timeEntries, currentEntry, now),
    [todaysShifts, timeEntries, currentEntry, now]
  );

  const isOnShift = !!currentShift;
  const isLate = !!currentShift && !clockedIn && now > new Date(currentShift.start_time);
  const isEarly = !!currentShift && !clockedIn && now < new Date(currentShift.start_time);
  const clockedInOutsideShift = clockedIn && !currentShift;

  const clockButtonLabel = currentShift && !clockedIn
    ? 'Start Shift'
    : clockedIn && currentShift
      ? 'End Shift'
      : clockedIn
        ? 'Clock Out'
        : 'Clock In';

  const clockTimingClassification = classifyClockTiming(currentShift, now);


  const handleClockIn = async () => {
    setClockingAction(true);
    try {
      console.log('[PhaseA] Clock timing classification:', clockTimingClassification, currentShift);

      const response = await api.post('/time-entries/clock-in', {
        staff_id: user.id,
        ...(user?.location_id ? { location_id: user.location_id } : {}),
      });

      const responseEntry = response?.data?.entry || response?.data || null;
      const fallbackClockIn = new Date().toISOString();

      setClockedIn(true);
      setCurrentEntry((prev) => ({
        ...(prev || {}),
        ...(responseEntry && typeof responseEntry === 'object' ? responseEntry : {}),
        clock_in:
          responseEntry?.clock_in ||
          responseEntry?.clockIn ||
          prev?.clock_in ||
          fallbackClockIn,
        status:
          responseEntry?.status ||
          prev?.status ||
          'active',
      }));
      setLiveNow(Date.now());

      toast.success('Clocked in successfully');
      await syncCurrentTimeState();
      setTimeout(() => {
        syncCurrentTimeState();
      }, 1200);
      await fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to clock in');
    } finally {
      setClockingAction(false);
    }
  };

  const handleClockOut = async () => {
    setClockingAction(true);
    try {
      await api.post('/time-entries/clock-out');

      setClockedIn(false);
      setCurrentEntry(null);

      toast.success('Clocked out successfully');
      await syncCurrentTimeState();
      setTimeout(() => {
        syncCurrentTimeState();
      }, 1200);
      await fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to clock out');
    } finally {
      setClockingAction(false);
    }
  };

  const openModificationModal = (entry) => {
    setSelectedEntry(entry);
    setModForm({
      requested_clock_in: entry.clock_in ? entry.clock_in.slice(0, 16) : '',
      requested_clock_out: entry.clock_out ? entry.clock_out.slice(0, 16) : '',
      reason: '',
    });
    setModModalOpen(true);
  };

  const submitModificationRequest = async (e) => {
    e.preventDefault();

    if (!modForm.reason.trim()) {
      toast.error('Please provide a reason');
      return;
    }

    try {
      await api.post('/time-entries/modification-request', {
        time_entry_id: selectedEntry.id,
        requested_clock_in: new Date(modForm.requested_clock_in).toISOString(),
        requested_clock_out: modForm.requested_clock_out
          ? new Date(modForm.requested_clock_out).toISOString()
          : null,
        reason: modForm.reason,
      });
      toast.success('Modification request submitted');
      setModModalOpen(false);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to submit request');
    }
  };

  const calculateHours = (clockIn, clockOut) => {
    if (!clockOut) return 'In Progress';
    const diff = new Date(clockOut) - new Date(clockIn);
    const hours = Math.floor(diff / 1000 / 60 / 60);
    const minutes = Math.floor((diff / 1000 / 60) % 60);
    return `${hours}h ${minutes}m`;
  };

  const calculateWeeklyTotal = () => {
    const weekNow = new Date();
    const dayOfWeek = weekNow.getDay();
    const daysToMonday = dayOfWeek === 0 ? 6 : dayOfWeek - 1;
    const weekStart = new Date(weekNow);
    weekStart.setDate(weekNow.getDate() - daysToMonday);
    weekStart.setHours(0, 0, 0, 0);

    const weeklyEntries = timeEntries.filter((entry) => {
      const entryDate = new Date(entry.clock_in);
      return entryDate >= weekStart;
    });

    return weeklyEntries
      .reduce((total, entry) => {
        if (!entry.clock_out) return total;
        const diff = new Date(entry.clock_out) - new Date(entry.clock_in);
        return total + diff / 1000 / 60 / 60;
      }, 0)
      .toFixed(2);
  };

  useEffect(() => {
    const clockInValue = getClockInValue(activeEntry);
    if (!activeEntry || !clockInValue) {
      console.log('[DurationEffect] no active entry', { activeEntry, clockInValue, liveNow });
      setCurrentDuration('--:--');
      return;
    }

    const clockInMs = new Date(clockInValue).getTime();
    if (Number.isNaN(clockInMs)) {
      console.log('[DurationEffect] invalid clockInValue', { clockInValue, liveNow });
      setCurrentDuration('--:--');
      return;
    }

    const diffMs = Math.max(0, liveNow - clockInMs);
    const totalSeconds = Math.floor(diffMs / 1000);

    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;

    const nextDuration = `${hours}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;

    console.log('[DurationEffect] tick', {
      liveNow,
      clockInValue,
      clockInMs,
      diffMs,
      totalSeconds,
      nextDuration,
      activeEntry,
    });

    setCurrentDuration(nextDuration);
  }, [activeEntry, liveNow]);

  const todayDate = new Date().toDateString();
  const todayEntries = timeEntries.filter(
    (entry) => new Date(entry.clock_in).toDateString() === todayDate
  );

  const pendingRequests = modRequests.filter((r) => r.status === 'pending');

  const formatShiftTime = (value) =>
    new Date(value).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });

  const getWeekLabel = () => {
    if (scheduleWeekOffset === 0) return 'This Week';
    if (scheduleWeekOffset === 1) return 'Next Week';
    if (scheduleWeekOffset === -1) return 'Last Week';
    return scheduleWeekOffset > 1
      ? `${scheduleWeekOffset} Weeks Ahead`
      : `${Math.abs(scheduleWeekOffset)} Weeks Ago`;
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
        <div className="max-w-5xl mx-auto px-4 md:px-8 py-4">
          <Button variant="ghost" onClick={() => navigate('/staff/dashboard')} className="flex items-center gap-2 mb-2">
            <ArrowLeftIcon size={18} /> Back to Dashboard
          </Button>
          <h1 className="text-3xl font-serif font-bold text-primary">My Time</h1>
          <p className="text-muted-foreground mt-1">Clock in, review hours, and manage time records</p>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 md:px-8 py-8 space-y-6">
        <ShiftStatusBanner
          currentShift={currentShift}
          nextShift={nextShift}
          isLate={isLate}
          isOnShift={isOnShift}
          missedShift={missedShift}
          clockedIn={clockedIn}
          clockedInOutsideShift={clockedInOutsideShift}
        />

        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <MapPinIcon size={16} />
          {gpsPosition ? (
            <span>GPS active (±{Math.round(gpsPosition.accuracy)}m)</span>
          ) : gpsError ? (
            <span>{gpsError}</span>
          ) : (
            <span>Acquiring GPS...</span>
          )}
          <Button variant="ghost" size="sm" onClick={() => getGPSPosition().catch(() => {})}>
            Refresh
          </Button>
        </div>

        <Card className={`rounded-2xl shadow-lg ${clockedIn ? 'bg-gradient-to-br from-green-500 to-green-600' : 'bg-gradient-to-br from-gray-600 to-gray-700'} text-white`}>
          <CardContent className="p-6">
            <div className="flex items-center justify-between gap-4 flex-col md:flex-row">
              <div>
                <p className="text-sm opacity-90 uppercase tracking-wider mb-1">
                  {(clockedIn || activeEntry) ? 'Currently Working' : 'Not Clocked In'}
                </p>
                <p className="text-4xl font-serif font-bold">{(clockedIn || activeEntry) ? currentDuration : '--:--'}</p>
                <p className="text-xs opacity-70 mt-1">
                  debug liveNow={liveNow} clockIn={String(getClockInValue(activeEntry) || 'null')} currentDuration={currentDuration}
                </p>
                {clockedIn && activeEntry && (
                  <p className="text-sm opacity-80 mt-2">
                    Started at {getClockInValue(activeEntry) ? new Date(getClockInValue(activeEntry)).toLocaleTimeString() : '--:--'}
                  </p>
                )}
                {clockedInOutsideShift ? (
                  <p className="text-sm opacity-90 mt-2 text-yellow-100">
                    You are clocked in outside a scheduled shift
                  </p>
                ) : null}
                {!clockedIn && isEarly && currentShift ? (
                  <p className="text-sm opacity-90 mt-2">
                    You are early for your scheduled shift.
                  </p>
                ) : null}
              </div>

              <Button
                onClick={clockedIn ? handleClockOut : handleClockIn}
                disabled={clockingAction}
                size="lg"
                className={`rounded-full px-8 ${clockedIn ? 'bg-white text-red-600 hover:bg-gray-100' : 'bg-white text-green-600 hover:bg-gray-100'}`}
              >
                {clockingAction ? (
                  'Processing...'
                ) : clockedIn ? (
                  <>
                    <StopCircleIcon size={20} className="mr-2" /> {clockButtonLabel}
                  </>
                ) : (
                  <>
                    <PlayIcon size={20} className="mr-2" /> {clockButtonLabel}
                  </>
                )}
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card className="rounded-2xl shadow-sm">
          <CardHeader>
            <CardTitle>Today</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {todayEntries.length === 0 ? (
              <p className="text-muted-foreground">No entries today.</p>
            ) : (
              todayEntries.map((entry) => (
                <div key={entry.id} className="p-3 rounded-lg border bg-white flex items-center justify-between">
                  <div>
                    <p className="font-medium">
                      {new Date(entry.clock_in).toLocaleTimeString()} - {entry.clock_out ? new Date(entry.clock_out).toLocaleTimeString() : 'In Progress'}
                    </p>
                    <p className="text-sm text-muted-foreground">{calculateHours(entry.clock_in, entry.clock_out)}</p>
                  </div>
                  <Badge>{entry.status}</Badge>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-primary to-primary/80 text-white rounded-2xl shadow-lg">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm opacity-90 uppercase tracking-wider mb-1">This Week</p>
                <p className="text-4xl font-serif font-bold">{calculateWeeklyTotal()}h</p>
              </div>
              <ClockIcon size={32} className="opacity-50" />
            </div>
          </CardContent>
        </Card>

        <Card className="rounded-2xl shadow-sm">
          <CardHeader>
            <div className="flex items-center justify-between gap-3 flex-col md:flex-row">
              <CardTitle>My Schedule</CardTitle>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    const next = scheduleWeekOffset - 1;
                    setScheduleWeekOffset(next);
                    fetchScheduleData(next);
                  }}
                >
                  Previous
                </Button>
                <Badge variant="secondary">{getWeekLabel()}</Badge>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    const next = scheduleWeekOffset + 1;
                    setScheduleWeekOffset(next);
                    fetchScheduleData(next);
                  }}
                >
                  Next
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            {scheduleLoading ? (
              <p className="text-muted-foreground">Loading schedule...</p>
            ) : scheduleShifts.length === 0 ? (
              <p className="text-muted-foreground">No shifts scheduled for this week.</p>
            ) : (
              scheduleShifts.map((shift) => (
                <div key={shift.id} className="p-4 rounded-xl border bg-white flex flex-col md:flex-row md:items-center md:justify-between gap-3">
                  <div>
                    <p className="font-medium">
                      {new Date(shift.start_time).toLocaleDateString([], {
                        weekday: 'long',
                        month: 'short',
                        day: 'numeric',
                      })}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      {formatShiftTime(shift.start_time)} - {formatShiftTime(shift.end_time)}
                    </p>
                    {shift.notes ? (
                      <p className="text-sm text-muted-foreground">{shift.notes}</p>
                    ) : null}
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge>{shift.status || 'published'}</Badge>
                    {swapRequests.some((r) => r.shift_id === shift.id && r.status === 'pending') ? (
                      <Badge variant="secondary">Swap Pending</Badge>
                    ) : null}
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        {pendingRequests.length > 0 && (
          <Card className="bg-yellow-50 border-yellow-200 rounded-2xl shadow-sm">
            <CardHeader className="border-b border-yellow-200">
              <CardTitle className="text-lg font-serif flex items-center gap-2">
                <AlertCircleIcon className="text-yellow-600" size={20} />
                Pending Modification Requests
              </CardTitle>
            </CardHeader>
            <CardContent className="p-4">
              {pendingRequests.map((req) => (
                <div key={req.id} className="p-3 bg-white rounded-lg border border-yellow-200 mb-2">
                  <p className="font-medium">
                    Requested: {req.requested_clock_in ? new Date(req.requested_clock_in).toLocaleString() : 'N/A'}
                  </p>
                  <p className="text-sm text-muted-foreground">Reason: {req.reason}</p>
                  <Badge className="mt-2 bg-yellow-100 text-yellow-800">Awaiting Approval</Badge>
                </div>
              ))}
            </CardContent>
          </Card>
        )}

        <Card className="rounded-2xl shadow-sm">
          <CardHeader>
            <CardTitle>Time Entry History</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {timeEntries.map((entry) => (
              <div key={entry.id} className="p-4 rounded-xl border bg-white flex flex-col md:flex-row md:items-center md:justify-between gap-3">
                <div>
                  <p className="font-medium">{new Date(entry.clock_in).toLocaleDateString()}</p>
                  <p className="text-sm text-muted-foreground">
                    {new Date(entry.clock_in).toLocaleTimeString()} - {entry.clock_out ? new Date(entry.clock_out).toLocaleTimeString() : 'In Progress'}
                  </p>
                  <p className="text-sm text-muted-foreground">{calculateHours(entry.clock_in, entry.clock_out)}</p>
                </div>

                <div className="flex items-center gap-2">
                  <Badge variant={entry.status === 'active' ? 'default' : 'secondary'}>
                    {entry.status}
                  </Badge>
                  {entry.status !== 'active' && (
                    <Button variant="outline" size="sm" onClick={() => openModificationModal(entry)}>
                      <EditIcon size={16} className="mr-1" />
                      Request Edit
                    </Button>
                  )}
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        <Dialog open={modModalOpen} onOpenChange={setModModalOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Request Time Entry Modification</DialogTitle>
            </DialogHeader>

            <form onSubmit={submitModificationRequest} className="space-y-4">
              <div>
                <Label>Requested Clock In</Label>
                <Input
                  type="datetime-local"
                  value={modForm.requested_clock_in}
                  onChange={(e) => setModForm({ ...modForm, requested_clock_in: e.target.value })}
                />
              </div>

              <div>
                <Label>Requested Clock Out</Label>
                <Input
                  type="datetime-local"
                  value={modForm.requested_clock_out}
                  onChange={(e) => setModForm({ ...modForm, requested_clock_out: e.target.value })}
                />
              </div>

              <div>
                <Label>Reason</Label>
                <Input
                  value={modForm.reason}
                  onChange={(e) => setModForm({ ...modForm, reason: e.target.value })}
                />
              </div>

              <Button type="submit" className="w-full">Submit Request</Button>
            </form>
          </DialogContent>
        </Dialog>
      </main>
    </div>
  );
};

export default MyTimePage;
