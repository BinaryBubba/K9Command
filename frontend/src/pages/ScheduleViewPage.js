import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, ChevronLeft, ChevronRight, Calendar, Clock, Users, RefreshCw, ArrowRightLeft } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Textarea } from '../components/ui/textarea';
import useAuthStore from '../store/authStore';

const API_URL = process.env.REACT_APP_BACKEND_URL;

export default function ScheduleViewPage() {
  const navigate = useNavigate();
  const { user, token } = useAuthStore();
  const [loading, setLoading] = useState(false);
  const [shifts, setShifts] = useState([]);
  const [currentWeek, setCurrentWeek] = useState(new Date());
  const [swapDialogOpen, setSwapDialogOpen] = useState(false);
  const [selectedShift, setSelectedShift] = useState(null);
  const [swapTargetStaff, setSwapTargetStaff] = useState('');
  const [swapReason, setSwapReason] = useState('');
  const [staffList, setStaffList] = useState([]);
  const [mySwapRequests, setMySwapRequests] = useState([]);

  // Get week boundaries
  const getWeekBounds = (date) => {
    const start = new Date(date);
    start.setDate(start.getDate() - start.getDay()); // Sunday
    start.setHours(0, 0, 0, 0);
    
    const end = new Date(start);
    end.setDate(end.getDate() + 6); // Saturday
    end.setHours(23, 59, 59, 999);
    
    return { start, end };
  };

  const { start: weekStart, end: weekEnd } = getWeekBounds(currentWeek);

  // Fetch shifts
  const fetchShifts = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        start_date: weekStart.toISOString(),
        end_date: weekEnd.toISOString()
      });
      
      const response = await fetch(`${API_URL}/api/scheduling/shifts?${params}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      if (response.ok) {
        const data = await response.json();
        setShifts(data);
      }
    } catch (error) {
      console.error('Failed to fetch shifts:', error);
    }
    setLoading(false);
  }, [token, weekStart, weekEnd]);

  // Fetch staff list (for swap requests)
  const fetchStaffList = useCallback(async () => {
    if (user?.role !== 'staff') return;
    try {
      // This endpoint may not exist - using users list
      const response = await fetch(`${API_URL}/api/admin/staff`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setStaffList(data.filter(s => s.id !== user.id));
      }
    } catch (error) {
      console.error('Failed to fetch staff:', error);
    }
  }, [token, user]);

  // Fetch my swap requests
  const fetchSwapRequests = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/api/scheduling/swap-requests`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setMySwapRequests(data);
      }
    } catch (error) {
      console.error('Failed to fetch swap requests:', error);
    }
  }, [token]);

  useEffect(() => {
    fetchShifts();
    fetchStaffList();
    fetchSwapRequests();
  }, [fetchShifts, fetchStaffList, fetchSwapRequests]);

  // Navigate weeks
  const navigateWeek = (direction) => {
    const newDate = new Date(currentWeek);
    newDate.setDate(newDate.getDate() + (direction * 7));
    setCurrentWeek(newDate);
  };

  // Get days of week
  const getDaysOfWeek = () => {
    const days = [];
    const current = new Date(weekStart);
    for (let i = 0; i < 7; i++) {
      days.push(new Date(current));
      current.setDate(current.getDate() + 1);
    }
    return days;
  };

  // Get shifts for a specific day
  const getShiftsForDay = (date) => {
    const dayStart = new Date(date);
    dayStart.setHours(0, 0, 0, 0);
    const dayEnd = new Date(date);
    dayEnd.setHours(23, 59, 59, 999);
    
    return shifts.filter(shift => {
      const shiftStart = new Date(shift.start_time);
      return shiftStart >= dayStart && shiftStart <= dayEnd;
    });
  };

  // Format time
  const formatTime = (dateStr) => {
    return new Date(dateStr).toLocaleTimeString('en-US', { 
      hour: 'numeric', 
      minute: '2-digit',
      hour12: true 
    });
  };

  // Handle swap request
  const handleSwapRequest = async () => {
    if (!selectedShift || !swapTargetStaff) {
      toast.error('Please select a staff member');
      return;
    }
    
    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/api/scheduling/swap-requests`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          shift_id: selectedShift.id,
          target_staff_id: swapTargetStaff,
          reason: swapReason
        })
      });
      
      if (response.ok) {
        toast.success('Swap request submitted');
        setSwapDialogOpen(false);
        setSelectedShift(null);
        setSwapTargetStaff('');
        setSwapReason('');
        fetchSwapRequests();
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Failed to submit swap request');
      }
    } catch (error) {
      toast.error('Failed to submit swap request');
    }
    setLoading(false);
  };

  const isToday = (date) => {
    const today = new Date();
    return date.toDateString() === today.toDateString();
  };

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      {/* Header */}
      <header className="bg-slate-900/80 backdrop-blur-sm border-b border-slate-800 sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="icon" onClick={() => navigate(-1)}>
              <ArrowLeft className="h-5 w-5" />
            </Button>
            <div>
              <h1 className="text-xl font-bold flex items-center gap-2">
                <Calendar className="h-5 w-5" />
                Schedule
              </h1>
            </div>
          </div>
          <Button variant="ghost" size="icon" onClick={fetchShifts} disabled={loading}>
            <RefreshCw className={`h-5 w-5 ${loading ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-6 space-y-6">
        {/* Week Navigation */}
        <div className="flex items-center justify-between">
          <Button variant="outline" onClick={() => navigateWeek(-1)}>
            <ChevronLeft className="h-4 w-4 mr-1" />
            Previous
          </Button>
          <div className="text-center">
            <h2 className="text-lg font-semibold">
              {weekStart.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} - {weekEnd.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
            </h2>
          </div>
          <Button variant="outline" onClick={() => navigateWeek(1)}>
            Next
            <ChevronRight className="h-4 w-4 ml-1" />
          </Button>
        </div>

        {/* Week Grid */}
        <div className="grid grid-cols-7 gap-2">
          {getDaysOfWeek().map((day, index) => (
            <div key={index} className={`min-h-[200px] ${isToday(day) ? 'bg-slate-800/50' : 'bg-slate-900/50'} rounded-lg border ${isToday(day) ? 'border-blue-500' : 'border-slate-800'}`}>
              <div className={`p-2 text-center border-b ${isToday(day) ? 'border-blue-500 bg-blue-500/20' : 'border-slate-800'}`}>
                <p className="text-xs text-slate-400">
                  {day.toLocaleDateString('en-US', { weekday: 'short' })}
                </p>
                <p className={`text-lg font-bold ${isToday(day) ? 'text-blue-400' : ''}`}>
                  {day.getDate()}
                </p>
              </div>
              <div className="p-2 space-y-2">
                {getShiftsForDay(day).map((shift) => (
                  <div 
                    key={shift.id}
                    className="p-2 rounded text-xs cursor-pointer hover:opacity-80 transition-opacity"
                    style={{ backgroundColor: shift.color || '#3B82F6' }}
                    onClick={() => {
                      if (user?.role === 'staff' && shift.staff_id === user.id) {
                        setSelectedShift(shift);
                        setSwapDialogOpen(true);
                      }
                    }}
                  >
                    <p className="font-medium truncate">{shift.staff_name}</p>
                    <p className="opacity-80">
                      {formatTime(shift.start_time)} - {formatTime(shift.end_time)}
                    </p>
                    {shift.status !== 'published' && (
                      <Badge variant="outline" className="mt-1 text-[10px]">
                        {shift.status}
                      </Badge>
                    )}
                  </div>
                ))}
                {getShiftsForDay(day).length === 0 && (
                  <p className="text-slate-600 text-xs text-center py-4">No shifts</p>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* My Swap Requests */}
        {mySwapRequests.length > 0 && (
          <Card className="bg-slate-900 border-slate-800">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <ArrowRightLeft className="h-5 w-5" />
                My Swap Requests
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {mySwapRequests.map((req) => (
                  <div key={req.id} className="flex items-center justify-between p-3 bg-slate-800/50 rounded-lg">
                    <div>
                      <p className="font-medium">
                        {req.requesting_staff_id === user?.id ? 
                          `Requested swap with ${req.target_staff_name}` :
                          `${req.requesting_staff_name} wants to swap`
                        }
                      </p>
                      <p className="text-sm text-slate-400">{req.reason || 'No reason provided'}</p>
                    </div>
                    <Badge variant={
                      req.status === 'approved' ? 'success' :
                      req.status === 'rejected' ? 'destructive' :
                      'secondary'
                    }>
                      {req.status}
                    </Badge>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Summary Stats */}
        <div className="grid grid-cols-3 gap-4">
          <Card className="bg-slate-900 border-slate-800">
            <CardContent className="p-4 text-center">
              <p className="text-3xl font-bold text-blue-400">
                {shifts.filter(s => user?.role === 'admin' || s.staff_id === user?.id).length}
              </p>
              <p className="text-sm text-slate-400">Shifts This Week</p>
            </CardContent>
          </Card>
          <Card className="bg-slate-900 border-slate-800">
            <CardContent className="p-4 text-center">
              <p className="text-3xl font-bold text-green-400">
                {shifts.filter(s => (user?.role === 'admin' || s.staff_id === user?.id)).reduce((sum, s) => {
                  const start = new Date(s.start_time);
                  const end = new Date(s.end_time);
                  return sum + (end - start) / 3600000;
                }, 0).toFixed(1)}
              </p>
              <p className="text-sm text-slate-400">Total Hours</p>
            </CardContent>
          </Card>
          <Card className="bg-slate-900 border-slate-800">
            <CardContent className="p-4 text-center">
              <p className="text-3xl font-bold text-purple-400">
                {new Set(shifts.map(s => s.staff_id)).size}
              </p>
              <p className="text-sm text-slate-400">Staff Scheduled</p>
            </CardContent>
          </Card>
        </div>
      </main>

      {/* Swap Request Dialog */}
      <Dialog open={swapDialogOpen} onOpenChange={setSwapDialogOpen}>
        <DialogContent className="bg-slate-900 border-slate-800">
          <DialogHeader>
            <DialogTitle>Request Shift Swap</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            {selectedShift && (
              <div className="p-3 bg-slate-800 rounded-lg">
                <p className="text-sm text-slate-400">Selected Shift</p>
                <p className="font-medium">
                  {new Date(selectedShift.start_time).toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' })}
                </p>
                <p className="text-sm">
                  {formatTime(selectedShift.start_time)} - {formatTime(selectedShift.end_time)}
                </p>
              </div>
            )}
            
            <div>
              <label className="text-sm text-slate-400 mb-1 block">Swap With</label>
              <Select value={swapTargetStaff} onValueChange={setSwapTargetStaff}>
                <SelectTrigger>
                  <SelectValue placeholder="Select staff member" />
                </SelectTrigger>
                <SelectContent>
                  {staffList.map((staff) => (
                    <SelectItem key={staff.id} value={staff.id}>
                      {staff.full_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            
            <div>
              <label className="text-sm text-slate-400 mb-1 block">Reason (optional)</label>
              <Textarea
                value={swapReason}
                onChange={(e) => setSwapReason(e.target.value)}
                placeholder="Why do you need to swap this shift?"
                className="bg-slate-800 border-slate-700"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setSwapDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleSwapRequest} disabled={loading}>
              Submit Request
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
