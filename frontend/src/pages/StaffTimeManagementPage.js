import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Calendar } from '../components/ui/calendar';
import { 
  ArrowLeftIcon, CalendarIcon, ClockIcon, PlayIcon, StopCircleIcon,
  PlusIcon, CoffeeIcon, CheckIcon
} from 'lucide-react';
import { toast } from 'sonner';
import api from '../utils/api';
import useAuthStore from '../store/authStore';

const StaffTimeManagementPage = () => {
  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);
  const [activeTab, setActiveTab] = useState('timeclock');
  const [loading, setLoading] = useState(true);
  const [viewMode, setViewMode] = useState('list');
  
  // Data
  const [timeEntries, setTimeEntries] = useState([]);
  const [currentEntry, setCurrentEntry] = useState(null);
  const [timeOffRequests, setTimeOffRequests] = useState([]);
  const [schedules, setSchedules] = useState([]);
  const [timeOffBalances, setTimeOffBalances] = useState({});
  
  // Clock state
  const [isClockedIn, setIsClockedIn] = useState(false);
  const [isOnBreak, setIsOnBreak] = useState(false);
  const [clockTime, setClockTime] = useState('');
  
  // Calendar
  const [selectedDate, setSelectedDate] = useState(new Date());
  
  // Time Off Modal
  const [timeOffModalOpen, setTimeOffModalOpen] = useState(false);
  const [timeOffForm, setTimeOffForm] = useState({
    leave_type: 'vacation',
    start_date: '',
    end_date: '',
    reason: ''
  });

  useEffect(() => {
    if (!user || user.role !== 'staff') {
      navigate('/auth');
      return;
    }
    fetchAllData();
    
    // Update clock every minute
    const interval = setInterval(() => {
      setClockTime(new Date().toLocaleTimeString());
    }, 1000);
    setClockTime(new Date().toLocaleTimeString());
    
    return () => clearInterval(interval);
  }, [user, navigate]);

  const fetchAllData = async () => {
    setLoading(true);
    try {
      const [entriesRes, timeOffRes, schedulesRes, balancesRes] = await Promise.all([
        api.get('/time-entries'),
        api.get('/time-off/my-requests'),
        api.get('/schedules/my-schedule'),
        api.get('/time-off/balances').catch(() => ({ data: {} })),
      ]);
      
      const entries = entriesRes.data || [];
      setTimeEntries(entries);
      setTimeOffRequests(timeOffRes.data || []);
      setSchedules(schedulesRes.data || []);
      setTimeOffBalances(balancesRes.data || {});
      
      // Check if currently clocked in
      const activeEntry = entries.find(e => !e.clock_out);
      if (activeEntry) {
        setCurrentEntry(activeEntry);
        setIsClockedIn(true);
        setIsOnBreak(activeEntry.on_break || false);
      } else {
        setIsClockedIn(false);
        setIsOnBreak(false);
        setCurrentEntry(null);
      }
    } catch (error) {
      console.error('Failed to load data:', error);
      toast.error('Failed to load time data');
    } finally {
      setLoading(false);
    }
  };

  const handleClockIn = async () => {
    try {
      const res = await api.post('/timeclock/clock-in');
      toast.success('Clocked in successfully!');
      setIsClockedIn(true);
      setCurrentEntry(res.data);
      fetchAllData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to clock in');
    }
  };

  const handleClockOut = async () => {
    try {
      await api.post('/timeclock/clock-out');
      toast.success('Clocked out successfully!');
      setIsClockedIn(false);
      setCurrentEntry(null);
      fetchAllData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to clock out');
    }
  };

  const handleStartBreak = async () => {
    try {
      await api.post('/timeclock/break/start');
      toast.success('Break started');
      setIsOnBreak(true);
      fetchAllData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to start break');
    }
  };

  const handleEndBreak = async () => {
    try {
      await api.post('/timeclock/break/end');
      toast.success('Break ended');
      setIsOnBreak(false);
      fetchAllData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to end break');
    }
  };

  const handleSubmitTimeOff = async (e) => {
    e.preventDefault();
    try {
      await api.post('/time-off/requests', timeOffForm);
      toast.success('Time off request submitted');
      setTimeOffModalOpen(false);
      setTimeOffForm({ leave_type: 'vacation', start_date: '', end_date: '', reason: '' });
      fetchAllData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to submit request');
    }
  };

  const formatDuration = (minutes) => {
    if (!minutes) return '0h 0m';
    const h = Math.floor(minutes / 60);
    const m = minutes % 60;
    return `${h}h ${m}m`;
  };

  const getElapsedTime = () => {
    if (!currentEntry?.clock_in) return '0h 0m';
    const start = new Date(currentEntry.clock_in);
    const now = new Date();
    const diff = Math.floor((now - start) / 60000);
    return formatDuration(diff);
  };

  // Calendar view helpers
  const getEventsForDate = (date) => {
    const dateStr = date.toISOString().split('T')[0];
    const events = [];
    
    timeEntries.forEach(e => {
      if (e.clock_in?.startsWith(dateStr)) {
        events.push({ type: 'timeEntry', data: e });
      }
    });
    
    timeOffRequests.forEach(r => {
      if (r.start_date <= dateStr && r.end_date >= dateStr) {
        events.push({ type: 'timeOff', data: r });
      }
    });
    
    schedules.forEach(s => {
      if (s.date === dateStr || (s.recurring && s.day_of_week === date.getDay())) {
        events.push({ type: 'schedule', data: s });
      }
    });
    
    return events;
  };

  // Stats
  const totalHoursThisWeek = timeEntries
    .filter(e => {
      const entryDate = new Date(e.clock_in);
      const now = new Date();
      const weekAgo = new Date(now.setDate(now.getDate() - 7));
      return entryDate >= weekAgo;
    })
    .reduce((acc, e) => acc + (e.total_minutes || 0), 0);

  const pendingRequests = timeOffRequests.filter(r => r.status === 'pending').length;

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#F9F7F2]">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#F9F7F2]">
      <header className="bg-white border-b border-border/40 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 md:px-8 py-4">
          <Button variant="ghost" onClick={() => navigate('/staff/dashboard')} className="flex items-center gap-2 mb-2">
            <ArrowLeftIcon size={18} /> Back to Dashboard
          </Button>
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-serif font-bold text-primary">My Time</h1>
              <p className="text-muted-foreground mt-1">Timeclock, schedule, and time off</p>
            </div>
            <Button 
              variant={viewMode === 'calendar' ? 'default' : 'outline'} 
              onClick={() => setViewMode(viewMode === 'list' ? 'calendar' : 'list')}
            >
              <CalendarIcon size={16} className="mr-2" /> {viewMode === 'list' ? 'Calendar View' : 'List View'}
            </Button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 md:px-8 py-8">
        {/* Time Clock Card */}
        <Card className="mb-6 bg-white rounded-2xl border border-border/50 shadow-sm">
          <CardContent className="p-6">
            <div className="flex flex-col md:flex-row items-center justify-between gap-6">
              <div className="text-center md:text-left">
                <p className="text-4xl font-mono font-bold text-primary">{clockTime}</p>
                <p className="text-muted-foreground">{new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' })}</p>
              </div>
              
              <div className="flex flex-col items-center gap-2">
                {isClockedIn ? (
                  <>
                    <Badge className="bg-green-100 text-green-800 text-lg px-4 py-1">
                      {isOnBreak ? 'On Break' : 'Clocked In'}
                    </Badge>
                    <p className="text-sm text-muted-foreground">Elapsed: {getElapsedTime()}</p>
                  </>
                ) : (
                  <Badge className="bg-gray-100 text-gray-800 text-lg px-4 py-1">Clocked Out</Badge>
                )}
              </div>
              
              <div className="flex gap-3">
                {!isClockedIn ? (
                  <Button size="lg" className="bg-green-600 hover:bg-green-700" onClick={handleClockIn}>
                    <PlayIcon size={20} className="mr-2" /> Clock In
                  </Button>
                ) : (
                  <>
                    {!isOnBreak ? (
                      <Button size="lg" variant="outline" onClick={handleStartBreak}>
                        <CoffeeIcon size={20} className="mr-2" /> Start Break
                      </Button>
                    ) : (
                      <Button size="lg" variant="outline" onClick={handleEndBreak}>
                        <CheckIcon size={20} className="mr-2" /> End Break
                      </Button>
                    )}
                    <Button size="lg" className="bg-red-600 hover:bg-red-700" onClick={handleClockOut}>
                      <StopCircleIcon size={20} className="mr-2" /> Clock Out
                    </Button>
                  </>
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
            <CardContent className="p-5">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-100 rounded-lg">
                  <ClockIcon className="text-blue-600" size={20} />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Hours This Week</p>
                  <p className="text-2xl font-bold">{formatDuration(totalHoursThisWeek)}</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
            <CardContent className="p-5">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-green-100 rounded-lg">
                  <CalendarIcon className="text-green-600" size={20} />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">PTO Balance</p>
                  <p className="text-2xl font-bold">{timeOffBalances.vacation || 0} days</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
            <CardContent className="p-5">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-yellow-100 rounded-lg">
                  <PlusIcon className="text-yellow-600" size={20} />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Pending Requests</p>
                  <p className="text-2xl font-bold">{pendingRequests}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {viewMode === 'calendar' ? (
          /* Calendar View */
          <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
            <CardContent className="p-6">
              <div className="flex gap-6">
                <div className="flex-shrink-0">
                  <Calendar
                    mode="single"
                    selected={selectedDate}
                    onSelect={(date) => date && setSelectedDate(date)}
                    className="rounded-md border"
                  />
                </div>
                <div className="flex-1">
                  <h3 className="text-lg font-semibold mb-4">
                    Events for {selectedDate.toLocaleDateString()}
                  </h3>
                  <div className="space-y-3 max-h-[400px] overflow-y-auto">
                    {getEventsForDate(selectedDate).length === 0 ? (
                      <p className="text-muted-foreground text-center py-8">No events for this date</p>
                    ) : (
                      getEventsForDate(selectedDate).map((event, idx) => (
                        <div key={idx} className="p-3 bg-muted/30 rounded-lg">
                          {event.type === 'timeEntry' && (
                            <div className="flex items-center justify-between">
                              <div>
                                <Badge className="bg-blue-100 text-blue-800 mb-1">Time Entry</Badge>
                                <p className="text-sm text-muted-foreground">
                                  {new Date(event.data.clock_in).toLocaleTimeString()} - {event.data.clock_out ? new Date(event.data.clock_out).toLocaleTimeString() : 'Active'}
                                </p>
                              </div>
                              <span className="font-medium">{formatDuration(event.data.total_minutes)}</span>
                            </div>
                          )}
                          {event.type === 'timeOff' && (
                            <div>
                              <Badge className="bg-orange-100 text-orange-800 mb-1">Time Off</Badge>
                              <p className="text-sm">{event.data.leave_type}</p>
                              <Badge className={event.data.status === 'approved' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'}>
                                {event.data.status}
                              </Badge>
                            </div>
                          )}
                          {event.type === 'schedule' && (
                            <div>
                              <Badge className="bg-green-100 text-green-800 mb-1">Scheduled Shift</Badge>
                              <p className="text-sm text-muted-foreground">
                                {event.data.start_time} - {event.data.end_time}
                              </p>
                            </div>
                          )}
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        ) : (
          /* List View with Tabs */
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="mb-4">
              <TabsTrigger value="timeclock">
                <ClockIcon size={16} className="mr-2" /> My Timesheet
              </TabsTrigger>
              <TabsTrigger value="time-off">
                <CalendarIcon size={16} className="mr-2" /> Time Off
              </TabsTrigger>
              <TabsTrigger value="schedule">
                <CalendarIcon size={16} className="mr-2" /> My Schedule
              </TabsTrigger>
            </TabsList>

            {/* Timesheet Tab */}
            <TabsContent value="timeclock">
              <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
                <CardContent className="p-0">
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead className="bg-muted/30">
                        <tr>
                          <th className="text-left p-4 font-medium">Date</th>
                          <th className="text-left p-4 font-medium">Clock In</th>
                          <th className="text-left p-4 font-medium">Clock Out</th>
                          <th className="text-left p-4 font-medium">Break</th>
                          <th className="text-left p-4 font-medium">Total</th>
                          <th className="text-left p-4 font-medium">Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {timeEntries.length === 0 ? (
                          <tr>
                            <td colSpan={6} className="p-8 text-center text-muted-foreground">No time entries yet</td>
                          </tr>
                        ) : (
                          timeEntries.slice(0, 20).map(entry => (
                            <tr key={entry.id} className="border-t hover:bg-muted/20">
                              <td className="p-4">{new Date(entry.clock_in).toLocaleDateString()}</td>
                              <td className="p-4">{new Date(entry.clock_in).toLocaleTimeString()}</td>
                              <td className="p-4">{entry.clock_out ? new Date(entry.clock_out).toLocaleTimeString() : <Badge className="bg-green-100 text-green-800">Active</Badge>}</td>
                              <td className="p-4">{formatDuration(entry.break_minutes || 0)}</td>
                              <td className="p-4 font-medium">{formatDuration(entry.total_minutes)}</td>
                              <td className="p-4">
                                <Badge className={entry.status === 'approved' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}>
                                  {entry.status || 'Pending'}
                                </Badge>
                              </td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            {/* Time Off Tab */}
            <TabsContent value="time-off">
              <div className="flex justify-end mb-4">
                <Button onClick={() => setTimeOffModalOpen(true)}>
                  <PlusIcon size={16} className="mr-2" /> Request Time Off
                </Button>
              </div>
              <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
                <CardContent className="p-0">
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead className="bg-muted/30">
                        <tr>
                          <th className="text-left p-4 font-medium">Type</th>
                          <th className="text-left p-4 font-medium">Start Date</th>
                          <th className="text-left p-4 font-medium">End Date</th>
                          <th className="text-left p-4 font-medium">Reason</th>
                          <th className="text-left p-4 font-medium">Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {timeOffRequests.length === 0 ? (
                          <tr>
                            <td colSpan={5} className="p-8 text-center text-muted-foreground">No time off requests</td>
                          </tr>
                        ) : (
                          timeOffRequests.map(request => (
                            <tr key={request.id} className="border-t hover:bg-muted/20">
                              <td className="p-4 capitalize">{request.leave_type}</td>
                              <td className="p-4">{request.start_date}</td>
                              <td className="p-4">{request.end_date}</td>
                              <td className="p-4 max-w-48 truncate">{request.reason || '-'}</td>
                              <td className="p-4">
                                <Badge className={
                                  request.status === 'approved' ? 'bg-green-100 text-green-800' :
                                  request.status === 'rejected' ? 'bg-red-100 text-red-800' :
                                  'bg-yellow-100 text-yellow-800'
                                }>
                                  {request.status}
                                </Badge>
                              </td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            {/* Schedule Tab */}
            <TabsContent value="schedule">
              <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
                <CardContent className="p-6">
                  {schedules.length === 0 ? (
                    <p className="text-center text-muted-foreground py-8">No schedule assigned yet</p>
                  ) : (
                    <div className="space-y-4">
                      {schedules.map(s => (
                        <div key={s.id} className="flex justify-between items-center p-4 bg-muted/20 rounded-lg">
                          <div>
                            <p className="font-medium">{s.date || s.day_of_week}</p>
                            {s.recurring && <Badge variant="outline">Recurring</Badge>}
                          </div>
                          <div className="text-right">
                            <p className="font-medium">{s.start_time} - {s.end_time}</p>
                            {s.location_name && <p className="text-sm text-muted-foreground">{s.location_name}</p>}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        )}
      </main>

      {/* Time Off Request Modal */}
      <Dialog open={timeOffModalOpen} onOpenChange={setTimeOffModalOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Request Time Off</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmitTimeOff} className="space-y-4">
            <div>
              <Label>Leave Type</Label>
              <Select value={timeOffForm.leave_type} onValueChange={(v) => setTimeOffForm({ ...timeOffForm, leave_type: v })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="vacation">Vacation</SelectItem>
                  <SelectItem value="sick">Sick Leave</SelectItem>
                  <SelectItem value="personal">Personal</SelectItem>
                  <SelectItem value="bereavement">Bereavement</SelectItem>
                  <SelectItem value="other">Other</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Start Date</Label>
                <Input
                  type="date"
                  value={timeOffForm.start_date}
                  onChange={(e) => setTimeOffForm({ ...timeOffForm, start_date: e.target.value })}
                  required
                />
              </div>
              <div>
                <Label>End Date</Label>
                <Input
                  type="date"
                  value={timeOffForm.end_date}
                  onChange={(e) => setTimeOffForm({ ...timeOffForm, end_date: e.target.value })}
                  required
                />
              </div>
            </div>
            <div>
              <Label>Reason (optional)</Label>
              <Input
                value={timeOffForm.reason}
                onChange={(e) => setTimeOffForm({ ...timeOffForm, reason: e.target.value })}
                placeholder="Brief description"
              />
            </div>
            <div className="flex gap-3 pt-4">
              <Button type="button" variant="outline" onClick={() => setTimeOffModalOpen(false)} className="flex-1">Cancel</Button>
              <Button type="submit" className="flex-1">Submit Request</Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default StaffTimeManagementPage;
