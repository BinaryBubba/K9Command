import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { ArrowLeftIcon, ClockIcon, SearchIcon, DownloadIcon } from 'lucide-react';
import { toast } from 'sonner';
import api from '../utils/api';
import useAuthStore from '../store/authStore';

const AdminTimesheetPage = () => {
  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);
  const [timeEntries, setTimeEntries] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user || user.role !== 'admin') {
      navigate('/auth');
      return;
    }
    fetchTimeEntries();
  }, [user, navigate]);

  const fetchTimeEntries = async () => {
    try {
      // In production, add endpoint to get all time entries
      setTimeEntries([]);
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
    toast.info('Export feature coming soon!');
  };

  const filteredEntries = timeEntries.filter(entry =>
    searchQuery ? entry.staff_id.toLowerCase().includes(searchQuery.toLowerCase()) : true
  );

  // Group by staff
  const entriesByStaff = filteredEntries.reduce((acc, entry) => {
    if (!acc[entry.staff_id]) {
      acc[entry.staff_id] = [];
    }
    acc[entry.staff_id].push(entry);
    return acc;
  }, {});

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
            <Button onClick={exportToCSV} className="rounded-full">
              <DownloadIcon size={18} className="mr-2" />
              Export CSV
            </Button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 md:px-8 py-8">
        {/* Search */}
        <Card className="mb-6 bg-white rounded-2xl border border-border/50 shadow-sm">
          <CardContent className="p-6">
            <div className="relative">
              <SearchIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground" size={20} />
              <Input
                placeholder="Search by staff ID..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>
          </CardContent>
        </Card>

        {/* Time Entries by Staff */}
        {timeEntries.length === 0 ? (
          <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
            <CardContent className="p-12 text-center">
              <ClockIcon size={48} className="mx-auto text-muted-foreground/50 mb-4" />
              <p className="text-muted-foreground">No timesheet entries found</p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-6">
            {Object.entries(entriesByStaff).map(([staffId, entries]) => {
              const totalHours = entries.reduce((sum, entry) => {
                if (!entry.clock_out) return sum;
                const diff = new Date(entry.clock_out) - new Date(entry.clock_in);
                return sum + (diff / 1000 / 60 / 60);
              }, 0);

              return (
                <Card key={staffId} className="bg-white rounded-2xl border border-border/50 shadow-sm">
                  <CardHeader className="border-b border-border/40">
                    <div className="flex justify-between items-center">
                      <CardTitle className="text-xl font-serif">Staff {staffId.slice(0, 8)}</CardTitle>
                      <div className="text-right">
                        <p className="text-sm text-muted-foreground">Total Hours</p>
                        <p className="text-2xl font-serif font-bold text-primary">{totalHours.toFixed(2)}h</p>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent className="p-6">
                    <div className="space-y-3">
                      {entries.map((entry) => (
                        <div
                          key={entry.id}
                          className="p-4 rounded-xl bg-muted/30 border border-border flex justify-between items-center"
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
                            <p className="text-xl font-serif font-bold">
                              {calculateHours(entry.clock_in, entry.clock_out)}
                            </p>
                          </div>
                        </div>
                      ))}
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
