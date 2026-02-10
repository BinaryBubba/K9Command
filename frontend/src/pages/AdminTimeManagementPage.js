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
  ArrowLeftIcon, CalendarIcon, ClockIcon, UserIcon, CheckIcon, XIcon,
  PlusIcon, PlayIcon, PauseIcon, DownloadIcon, FilterIcon
} from 'lucide-react';
import { toast } from 'sonner';
import api from '../utils/api';
import useAuthStore from '../store/authStore';

const AdminTimeManagementPage = () => {
  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);
  const [activeTab, setActiveTab] = useState('timesheets');
  const [loading, setLoading] = useState(true);
  const [viewMode, setViewMode] = useState('list'); // 'list' or 'calendar'
  
  // Data
  const [staff, setStaff] = useState([]);
  const [timeEntries, setTimeEntries] = useState([]);
  const [timeOffRequests, setTimeOffRequests] = useState([]);
  const [schedules, setSchedules] = useState([]);
  
  // Filters
  const [selectedStaff, setSelectedStaff] = useState('all');
  const [dateRange, setDateRange] = useState({ start: '', end: '' });
  const [statusFilter, setStatusFilter] = useState('all');
  
  // Calendar
  const [selectedDate, setSelectedDate] = useState(new Date());
  
  // Modal
  const [modalOpen, setModalOpen] = useState(false);
  const [modalType, setModalType] = useState(''); // 'timeEntry', 'timeOff', 'schedule'
  const [selectedItem, setSelectedItem] = useState(null);

  useEffect(() => {
    if (!user || user.role !== 'admin') {
      navigate('/auth');
      return;
    }
    fetchAllData();
  }, [user, navigate]);

  const fetchAllData = async () => {
    setLoading(true);
    try {
      const [staffRes, entriesRes, timeOffRes, schedulesRes] = await Promise.all([
        api.get('/admin/users?role=staff'),
        api.get('/time-entries'),
        api.get('/time-off/requests'),
        api.get('/schedules'),
      ]);
      setStaff(staffRes.data || []);
      setTimeEntries(entriesRes.data || []);
      setTimeOffRequests(timeOffRes.data || []);
      setSchedules(schedulesRes.data || []);
    } catch (error) {
      console.error('Failed to load data:', error);
      toast.error('Failed to load time management data');
    } finally {
      setLoading(false);
    }
  };

  const getStaffName = (staffId) => {
    const s = staff.find(st => st.id === staffId);
    return s?.full_name || 'Unknown';
  };

  const formatDuration = (minutes) => {
    if (!minutes) return '0h 0m';
    const h = Math.floor(minutes / 60);
    const m = minutes % 60;
    return `${h}h ${m}m`;
  };

  const handleApproveTimeOff = async (requestId) => {
    try {
      await api.post(`/time-off/requests/${requestId}/approve`);
      toast.success('Time off request approved');
      fetchAllData();
    } catch (error) {
      toast.error('Failed to approve request');
    }
  };

  const handleRejectTimeOff = async (requestId) => {
    const reason = window.prompt('Reason for rejection (optional):');
    try {
      await api.post(`/time-off/requests/${requestId}/reject`, { reason });
      toast.success('Time off request rejected');
      fetchAllData();
    } catch (error) {
      toast.error('Failed to reject request');
    }
  };

  const exportCSV = () => {
    // Filter based on current view
    let data = [];
    let filename = '';
    
    if (activeTab === 'timesheets') {
      data = filteredEntries.map(e => ({
        Staff: getStaffName(e.staff_id),
        Date: new Date(e.clock_in).toLocaleDateString(),
        'Clock In': new Date(e.clock_in).toLocaleTimeString(),
        'Clock Out': e.clock_out ? new Date(e.clock_out).toLocaleTimeString() : 'Active',
        'Total Hours': formatDuration(e.total_minutes),
        Status: e.status
      }));
      filename = 'timesheets.csv';
    } else if (activeTab === 'time-off') {
      data = filteredTimeOff.map(r => ({
        Staff: getStaffName(r.staff_id),
        Type: r.leave_type,
        'Start Date': r.start_date,
        'End Date': r.end_date,
        Status: r.status,
        Reason: r.reason || ''
      }));
      filename = 'time-off-requests.csv';
    }
    
    if (data.length === 0) {
      toast.error('No data to export');
      return;
    }
    
    const headers = Object.keys(data[0]).join(',');
    const rows = data.map(row => Object.values(row).map(v => `"${v}"`).join(',')).join('\n');
    const csv = headers + '\n' + rows;
    
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
    
    toast.success('CSV exported successfully');
  };

  // Filtered data
  const filteredEntries = timeEntries.filter(e => {
    if (selectedStaff !== 'all' && e.staff_id !== selectedStaff) return false;
    return true;
  });

  const filteredTimeOff = timeOffRequests.filter(r => {
    if (selectedStaff !== 'all' && r.staff_id !== selectedStaff) return false;
    if (statusFilter !== 'all' && r.status !== statusFilter) return false;
    return true;
  });

  const filteredSchedules = schedules.filter(s => {
    if (selectedStaff !== 'all' && s.staff_id !== selectedStaff) return false;
    return true;
  });

  // Calendar view helpers
  const getEventsForDate = (date) => {
    const dateStr = date.toISOString().split('T')[0];
    const events = [];
    
    // Time entries
    timeEntries.forEach(e => {
      if (e.clock_in?.startsWith(dateStr)) {
        events.push({ type: 'timeEntry', data: e });
      }
    });
    
    // Time off
    timeOffRequests.forEach(r => {
      if (r.start_date <= dateStr && r.end_date >= dateStr) {
        events.push({ type: 'timeOff', data: r });
      }
    });
    
    // Schedules
    schedules.forEach(s => {
      if (s.date === dateStr || (s.recurring && s.day_of_week === date.getDay())) {
        events.push({ type: 'schedule', data: s });
      }
    });
    
    return events;
  };

  // Stats
  const pendingTimeOff = timeOffRequests.filter(r => r.status === 'pending').length;
  const activeClockIns = timeEntries.filter(e => !e.clock_out).length;
  const totalHoursThisWeek = filteredEntries.reduce((acc, e) => acc + (e.total_minutes || 0), 0);

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
          <Button variant="ghost" onClick={() => navigate('/admin/dashboard')} className="flex items-center gap-2 mb-2">
            <ArrowLeftIcon size={18} /> Back to Dashboard
          </Button>
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-serif font-bold text-primary">Time Management</h1>
              <p className="text-muted-foreground mt-1">Staff timesheets, schedules, and time off requests</p>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" onClick={exportCSV}>
                <DownloadIcon size={16} className="mr-2" /> Export CSV
              </Button>
              <Button 
                variant={viewMode === 'calendar' ? 'default' : 'outline'} 
                onClick={() => setViewMode(viewMode === 'list' ? 'calendar' : 'list')}
              >
                <CalendarIcon size={16} className="mr-2" /> {viewMode === 'list' ? 'Calendar View' : 'List View'}
              </Button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 md:px-8 py-8">
        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
            <CardContent className="p-5">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-100 rounded-lg">
                  <UserIcon className="text-blue-600" size={20} />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Total Staff</p>
                  <p className="text-2xl font-bold">{staff.length}</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
            <CardContent className="p-5">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-green-100 rounded-lg">
                  <PlayIcon className="text-green-600" size={20} />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Currently Clocked In</p>
                  <p className="text-2xl font-bold">{activeClockIns}</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
            <CardContent className="p-5">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-orange-100 rounded-lg">
                  <ClockIcon className="text-orange-600" size={20} />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Total Hours (filtered)</p>
                  <p className="text-2xl font-bold">{formatDuration(totalHoursThisWeek)}</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
            <CardContent className="p-5">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-yellow-100 rounded-lg">
                  <PauseIcon className="text-yellow-600" size={20} />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Pending Time Off</p>
                  <p className="text-2xl font-bold">{pendingTimeOff}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Filters */}
        <Card className="mb-6 bg-white rounded-2xl border border-border/50 shadow-sm">
          <CardContent className="p-4">
            <div className="flex flex-wrap gap-4 items-center">
              <div className="flex items-center gap-2">
                <FilterIcon size={16} className="text-muted-foreground" />
                <span className="text-sm font-medium">Filters:</span>
              </div>
              <Select value={selectedStaff} onValueChange={setSelectedStaff}>
                <SelectTrigger className="w-48">
                  <SelectValue placeholder="All Staff" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Staff</SelectItem>
                  {staff.map(s => (
                    <SelectItem key={s.id} value={s.id}>{s.full_name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="w-40">
                  <SelectValue placeholder="All Statuses" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Statuses</SelectItem>
                  <SelectItem value="pending">Pending</SelectItem>
                  <SelectItem value="approved">Approved</SelectItem>
                  <SelectItem value="rejected">Rejected</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

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
                                <p className="font-medium">{getStaffName(event.data.staff_id)}</p>
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
                              <p className="font-medium">{getStaffName(event.data.staff_id)}</p>
                              <p className="text-sm text-muted-foreground">{event.data.leave_type} - {event.data.status}</p>
                            </div>
                          )}
                          {event.type === 'schedule' && (
                            <div>
                              <Badge className="bg-green-100 text-green-800 mb-1">Schedule</Badge>
                              <p className="font-medium">{getStaffName(event.data.staff_id)}</p>
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
              <TabsTrigger value="timesheets">
                <ClockIcon size={16} className="mr-2" /> Timesheets
              </TabsTrigger>
              <TabsTrigger value="time-off">
                <CalendarIcon size={16} className="mr-2" /> Time Off Requests
                {pendingTimeOff > 0 && (
                  <Badge className="ml-2 bg-yellow-500">{pendingTimeOff}</Badge>
                )}
              </TabsTrigger>
              <TabsTrigger value="schedules">
                <UserIcon size={16} className="mr-2" /> Staff Schedules
              </TabsTrigger>
            </TabsList>

            {/* Timesheets Tab */}
            <TabsContent value="timesheets">
              <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
                <CardContent className="p-0">
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead className="bg-muted/30">
                        <tr>
                          <th className="text-left p-4 font-medium">Staff</th>
                          <th className="text-left p-4 font-medium">Date</th>
                          <th className="text-left p-4 font-medium">Clock In</th>
                          <th className="text-left p-4 font-medium">Clock Out</th>
                          <th className="text-left p-4 font-medium">Break Time</th>
                          <th className="text-left p-4 font-medium">Total</th>
                          <th className="text-left p-4 font-medium">Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {filteredEntries.length === 0 ? (
                          <tr>
                            <td colSpan={7} className="p-8 text-center text-muted-foreground">No time entries found</td>
                          </tr>
                        ) : (
                          filteredEntries.map(entry => (
                            <tr key={entry.id} className="border-t hover:bg-muted/20">
                              <td className="p-4">{getStaffName(entry.staff_id)}</td>
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
              <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
                <CardContent className="p-0">
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead className="bg-muted/30">
                        <tr>
                          <th className="text-left p-4 font-medium">Staff</th>
                          <th className="text-left p-4 font-medium">Type</th>
                          <th className="text-left p-4 font-medium">Start Date</th>
                          <th className="text-left p-4 font-medium">End Date</th>
                          <th className="text-left p-4 font-medium">Reason</th>
                          <th className="text-left p-4 font-medium">Status</th>
                          <th className="text-left p-4 font-medium">Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {filteredTimeOff.length === 0 ? (
                          <tr>
                            <td colSpan={7} className="p-8 text-center text-muted-foreground">No time off requests found</td>
                          </tr>
                        ) : (
                          filteredTimeOff.map(request => (
                            <tr key={request.id} className="border-t hover:bg-muted/20">
                              <td className="p-4">{getStaffName(request.staff_id)}</td>
                              <td className="p-4">{request.leave_type}</td>
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
                              <td className="p-4">
                                {request.status === 'pending' && (
                                  <div className="flex gap-2">
                                    <Button size="sm" className="bg-green-600 hover:bg-green-700" onClick={() => handleApproveTimeOff(request.id)}>
                                      <CheckIcon size={14} />
                                    </Button>
                                    <Button size="sm" variant="destructive" onClick={() => handleRejectTimeOff(request.id)}>
                                      <XIcon size={14} />
                                    </Button>
                                  </div>
                                )}
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

            {/* Schedules Tab */}
            <TabsContent value="schedules">
              <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
                <CardContent className="p-6">
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {staff.map(s => {
                      const staffSchedules = filteredSchedules.filter(sch => sch.staff_id === s.id);
                      return (
                        <Card key={s.id} className="border border-border/30">
                          <CardHeader className="pb-2">
                            <CardTitle className="text-lg flex items-center gap-2">
                              <UserIcon size={18} /> {s.full_name}
                            </CardTitle>
                          </CardHeader>
                          <CardContent>
                            {staffSchedules.length === 0 ? (
                              <p className="text-sm text-muted-foreground">No schedule set</p>
                            ) : (
                              <div className="space-y-2">
                                {staffSchedules.slice(0, 5).map(sch => (
                                  <div key={sch.id} className="flex justify-between text-sm">
                                    <span>{sch.date || sch.day_of_week}</span>
                                    <span className="text-muted-foreground">{sch.start_time} - {sch.end_time}</span>
                                  </div>
                                ))}
                              </div>
                            )}
                          </CardContent>
                        </Card>
                      );
                    })}
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        )}
      </main>
    </div>
  );
};

export default AdminTimeManagementPage;
