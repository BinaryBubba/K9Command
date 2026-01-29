import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Badge } from '../components/ui/badge';
import { ArrowLeftIcon, ClockIcon, SearchIcon, DownloadIcon, UserIcon } from 'lucide-react';
import { toast } from 'sonner';
import api from '../utils/api';
import useAuthStore from '../store/authStore';

const AdminTimesheetPage = () => {
  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);
  const [timeEntries, setTimeEntries] = useState([]);
  const [staff, setStaff] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedStaff, setSelectedStaff] = useState('all');
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
      const [entriesRes, staffRes] = await Promise.all([
        api.get('/time-entries'),
        api.get('/admin/users?role=staff'),
      ]);
      setTimeEntries(entriesRes.data);
      setStaff(staffRes.data);
    } catch (error) {
      toast.error('Failed to load timesheets');
    } finally {
      setLoading(false);
    }
  };

  const calculateHours = (clockIn, clockOut) => {
    if (!clockOut) return 'In Progress';
    const diff = new Date(clockOut) - new Date(clockIn);
    const hours = Math.floor(diff / 1000 / 60 / 60);
    const minutes = Math.floor((diff / 1000 / 60) % 60);
    return `${hours}h ${minutes}m`;
  };

  const exportToCSV = () => {
    const headers = ['Staff Name', 'Date', 'Clock In', 'Clock Out', 'Hours'];
    const rows = timeEntries.map(entry => {
      const staffMember = staff.find(s => s.id === entry.staff_id);
      return [
        staffMember?.full_name || entry.staff_id,
        new Date(entry.clock_in).toLocaleDateString(),
        new Date(entry.clock_in).toLocaleTimeString(),
        entry.clock_out ? new Date(entry.clock_out).toLocaleTimeString() : 'In Progress',
        calculateHours(entry.clock_in, entry.clock_out),
      ];
    });

    const csv = [headers, ...rows].map(row => row.join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `timesheets_${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    toast.success('Timesheet exported!');
  };

  // Filter entries
  let filteredEntries = timeEntries;
  if (selectedStaff !== 'all') {
    filteredEntries = filteredEntries.filter(e => e.staff_id === selectedStaff);
  }
  if (searchQuery) {
    filteredEntries = filteredEntries.filter(entry => {
      const staffMember = staff.find(s => s.id === entry.staff_id);
      return staffMember?.full_name?.toLowerCase().includes(searchQuery.toLowerCase());
    });
  }

  // Group by staff
  const entriesByStaff = filteredEntries.reduce((acc, entry) => {
    if (!acc[entry.staff_id]) {
      acc[entry.staff_id] = [];
    }
    acc[entry.staff_id].push(entry);
    return acc;
  }, {});

  // Calculate totals
  const totalHours = timeEntries.reduce((sum, entry) => {
    if (!entry.clock_out) return sum;
    const diff = new Date(entry.clock_out) - new Date(entry.clock_in);
    return sum + (diff / 1000 / 60 / 60);
  }, 0);

  const activeStaff = timeEntries.filter(e => !e.clock_out).length;

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
          <div className="flex justify-between items-start">
            <div>
              <h1 className="text-3xl font-serif font-bold text-primary">Staff Timesheets</h1>
              <p className="text-muted-foreground mt-1">View all employee work hours</p>
            </div>
            <Button data-testid="export-csv-btn" onClick={exportToCSV} className="rounded-full">
              <DownloadIcon size={18} className="mr-2" />
              Export CSV
            </Button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 md:px-8 py-8">
        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <Card className="bg-gradient-to-br from-primary to-primary/80 text-white rounded-2xl shadow-lg">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm opacity-90 uppercase tracking-wider mb-1">Total Hours Logged</p>
                  <p className="text-3xl font-serif font-bold">{totalHours.toFixed(1)}h</p>
                </div>
                <ClockIcon size={32} className="opacity-50" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-green-500 to-green-600 text-white rounded-2xl shadow-lg">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm opacity-90 uppercase tracking-wider mb-1">Currently Working</p>
                  <p className="text-3xl font-serif font-bold">{activeStaff}</p>
                </div>
                <UserIcon size={32} className="opacity-50" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-blue-500 to-blue-600 text-white rounded-2xl shadow-lg">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm opacity-90 uppercase tracking-wider mb-1">Total Entries</p>
                  <p className="text-3xl font-serif font-bold">{timeEntries.length}</p>
                </div>
                <ClockIcon size={32} className="opacity-50" />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Filters */}
        <Card className="mb-6 bg-white rounded-2xl border border-border/50 shadow-sm">
          <CardContent className="p-6">
            <div className="flex flex-col md:flex-row gap-4">
              <div className="flex-1 relative">
                <SearchIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground" size={20} />
                <Input
                  data-testid="search-input"
                  placeholder="Search by staff name..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10"
                />
              </div>
              <Select value={selectedStaff} onValueChange={setSelectedStaff}>
                <SelectTrigger data-testid="staff-filter" className="w-[200px]">
                  <SelectValue placeholder="Filter by staff" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Staff</SelectItem>
                  {staff.map((s) => (
                    <SelectItem key={s.id} value={s.id}>{s.full_name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        {/* Time Entries by Staff */}
        {Object.keys(entriesByStaff).length === 0 ? (
          <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
            <CardContent className="p-12 text-center">
              <ClockIcon size={48} className="mx-auto text-muted-foreground/50 mb-4" />
              <p className="text-muted-foreground">No timesheet entries found</p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-6">
            {Object.entries(entriesByStaff).map(([staffId, entries]) => {
              const staffMember = staff.find(s => s.id === staffId);
              const totalHours = entries.reduce((sum, entry) => {
                if (!entry.clock_out) return sum;
                const diff = new Date(entry.clock_out) - new Date(entry.clock_in);
                return sum + (diff / 1000 / 60 / 60);
              }, 0);
              const isCurrentlyWorking = entries.some(e => !e.clock_out);

              return (
                <Card key={staffId} data-testid={`staff-timesheet-${staffId}`} className="bg-white rounded-2xl border border-border/50 shadow-sm">
                  <CardHeader className="border-b border-border/40">
                    <div className="flex justify-between items-center">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
                          <UserIcon className="text-primary" size={20} />
                        </div>
                        <div>
                          <CardTitle className="text-xl font-serif">{staffMember?.full_name || 'Unknown Staff'}</CardTitle>
                          <p className="text-sm text-muted-foreground">{staffMember?.email}</p>
                        </div>
                        {isCurrentlyWorking && (
                          <Badge className="bg-green-100 text-green-800">Working Now</Badge>
                        )}
                      </div>
                      <div className="text-right">
                        <p className="text-sm text-muted-foreground">Total Hours</p>
                        <p className="text-2xl font-serif font-bold text-primary">{totalHours.toFixed(2)}h</p>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent className="p-6">
                    <div className="space-y-3">
                      {entries.slice(0, 10).map((entry) => (
                        <div
                          key={entry.id}
                          className={`p-4 rounded-xl border flex justify-between items-center ${!entry.clock_out ? 'bg-green-50 border-green-200' : 'bg-muted/30 border-border'}`}
                        >
                          <div>
                            <p className="font-semibold mb-1">{new Date(entry.clock_in).toLocaleDateString()}</p>
                            <div className="grid grid-cols-2 gap-4 text-sm text-muted-foreground">
                              <span>In: {new Date(entry.clock_in).toLocaleTimeString()}</span>
                              <span>
                                Out: {entry.clock_out ? new Date(entry.clock_out).toLocaleTimeString() : 'In Progress'}
                              </span>
                            </div>
                          </div>
                          <div className="text-right">
                            <p className={`text-xl font-serif font-bold ${!entry.clock_out ? 'text-green-600' : ''}`}>
                              {calculateHours(entry.clock_in, entry.clock_out)}
                            </p>
                          </div>
                        </div>
                      ))}
                      {entries.length > 10 && (
                        <p className="text-center text-sm text-muted-foreground">
                          + {entries.length - 10} more entries
                        </p>
                      )}
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
      </main>
    </div>
  );
};

export default AdminTimesheetPage;
