import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { ArrowLeftIcon, ClockIcon, CalendarIcon, PlayIcon, StopCircleIcon } from 'lucide-react';
import { toast } from 'sonner';
import api from '../utils/api';
import useAuthStore from '../store/authStore';

const StaffTimesheetPage = () => {
  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);
  const [timeEntries, setTimeEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [clockedIn, setClockedIn] = useState(false);
  const [currentEntry, setCurrentEntry] = useState(null);
  const [clockingAction, setClockingAction] = useState(false);

  useEffect(() => {
    if (!user || user.role !== 'staff') {
      navigate('/auth');
      return;
    }
    fetchData();
  }, [user, navigate]);

  const fetchData = async () => {
    try {
      const [entriesRes, currentRes] = await Promise.all([
        api.get('/time-entries'),
        api.get('/time-entries/current'),
      ]);
      setTimeEntries(entriesRes.data);
      setClockedIn(currentRes.data.clocked_in);
      setCurrentEntry(currentRes.data.entry);
    } catch (error) {
      toast.error('Failed to load timesheet');
    } finally {
      setLoading(false);
    }
  };

  const handleClockIn = async () => {
    setClockingAction(true);
    try {
      await api.post('/time-entries/clock-in', {
        staff_id: user.id,
        location_id: user.location_id || 'default',
      });
      toast.success('Clocked in successfully!');
      fetchData();
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
      toast.success('Clocked out successfully!');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to clock out');
    } finally {
      setClockingAction(false);
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
    const now = new Date();
    const weekStart = new Date(now);
    weekStart.setDate(now.getDate() - now.getDay());
    weekStart.setHours(0, 0, 0, 0);
    
    const weeklyEntries = timeEntries.filter(entry => {
      const entryDate = new Date(entry.clock_in);
      return entryDate >= weekStart;
    });

    return weeklyEntries.reduce((total, entry) => {
      if (!entry.clock_out) return total;
      const diff = new Date(entry.clock_out) - new Date(entry.clock_in);
      return total + (diff / 1000 / 60 / 60);
    }, 0).toFixed(2);
  };

  const getCurrentDuration = () => {
    if (!currentEntry) return '0h 0m';
    const diff = new Date() - new Date(currentEntry.clock_in);
    const hours = Math.floor(diff / 1000 / 60 / 60);
    const minutes = Math.floor((diff / 1000 / 60) % 60);
    return `${hours}h ${minutes}m`;
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
          <Button
            variant="ghost"
            onClick={() => navigate('/staff/dashboard')}
            className="flex items-center gap-2 mb-2"
          >
            <ArrowLeftIcon size={18} />
            Back to Dashboard
          </Button>
          <h1 className="text-3xl font-serif font-bold text-primary">My Timesheet</h1>
          <p className="text-muted-foreground mt-1">Track your work hours</p>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 md:px-8 py-8">
        {/* Clock In/Out Card */}
        <Card className={`mb-6 rounded-2xl shadow-lg ${clockedIn ? 'bg-gradient-to-br from-green-500 to-green-600' : 'bg-gradient-to-br from-gray-600 to-gray-700'} text-white`}>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm opacity-90 uppercase tracking-wider mb-1">
                  {clockedIn ? 'Currently Working' : 'Not Clocked In'}
                </p>
                <p className="text-4xl font-serif font-bold">
                  {clockedIn ? getCurrentDuration() : '--:--'}
                </p>
                {clockedIn && currentEntry && (
                  <p className="text-sm opacity-75 mt-2">
                    Started at {new Date(currentEntry.clock_in).toLocaleTimeString()}
                  </p>
                )}
              </div>
              <Button
                data-testid={clockedIn ? 'clock-out-btn' : 'clock-in-btn'}
                onClick={clockedIn ? handleClockOut : handleClockIn}
                disabled={clockingAction}
                size="lg"
                className={`rounded-full px-8 ${clockedIn ? 'bg-white text-red-600 hover:bg-gray-100' : 'bg-white text-green-600 hover:bg-gray-100'}`}
              >
                {clockingAction ? (
                  'Processing...'
                ) : clockedIn ? (
                  <>
                    <StopCircleIcon size={20} className="mr-2" />
                    Clock Out
                  </>
                ) : (
                  <>
                    <PlayIcon size={20} className="mr-2" />
                    Clock In
                  </>
                )}
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Weekly Summary */}
        <Card className="mb-6 bg-gradient-to-br from-primary to-primary/80 text-white rounded-2xl shadow-lg">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm opacity-90 uppercase tracking-wider mb-1">This Week's Hours</p>
                <p className="text-4xl font-serif font-bold">{calculateWeeklyTotal()}h</p>
              </div>
              <div className="w-16 h-16 rounded-full bg-white/20 flex items-center justify-center">
                <ClockIcon size={32} />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Time Entries */}
        <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
          <CardHeader className="border-b border-border/40">
            <CardTitle className="text-2xl font-serif">Clock In/Out History</CardTitle>
          </CardHeader>
          <CardContent className="p-6">
            {timeEntries.length === 0 ? (
              <div className="text-center py-12">
                <ClockIcon size={48} className="mx-auto text-muted-foreground/50 mb-4" />
                <p className="text-muted-foreground">No time entries yet. Clock in to start tracking!</p>
              </div>
            ) : (
              <div className="space-y-3">
                {timeEntries.map((entry) => (
                  <div
                    key={entry.id}
                    data-testid={`time-entry-${entry.id}`}
                    className="p-4 rounded-xl bg-muted/30 border border-border"
                  >
                    <div className="flex justify-between items-start">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <CalendarIcon size={16} className="text-primary" />
                          <span className="font-semibold">
                            {new Date(entry.clock_in).toLocaleDateString()}
                          </span>
                          {!entry.clock_out && (
                            <Badge className="bg-green-100 text-green-800">Active</Badge>
                          )}
                        </div>
                        <div className="grid grid-cols-2 gap-4 text-sm">
                          <div>
                            <p className="text-muted-foreground">Clock In</p>
                            <p className="font-medium">{new Date(entry.clock_in).toLocaleTimeString()}</p>
                          </div>
                          <div>
                            <p className="text-muted-foreground">Clock Out</p>
                            <p className="font-medium">
                              {entry.clock_out ? new Date(entry.clock_out).toLocaleTimeString() : 'In Progress'}
                            </p>
                          </div>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="text-2xl font-serif font-bold text-primary">
                          {calculateHours(entry.clock_in, entry.clock_out)}
                        </p>
                      </div>
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

export default StaffTimesheetPage;
