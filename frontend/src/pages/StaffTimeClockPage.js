import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Clock, Play, Pause, Coffee, MapPin, CheckCircle, AlertCircle } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import useAuthStore from '../store/authStore';

const API_URL = process.env.REACT_APP_BACKEND_URL;

export default function StaffTimeClockPage() {
  const navigate = useNavigate();
  const { user, token } = useAuthStore();
  const [loading, setLoading] = useState(false);
  const [currentEntry, setCurrentEntry] = useState(null);
  const [currentBreak, setCurrentBreak] = useState(null);
  const [gpsPosition, setGpsPosition] = useState(null);
  const [gpsError, setGpsError] = useState(null);
  const [todayEntries, setTodayEntries] = useState([]);
  const [elapsedTime, setElapsedTime] = useState('00:00:00');

  // Fetch current time entry status
  const fetchCurrentEntry = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/api/timeclock/entries/current`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setCurrentEntry(data);
        
        // Check for active break
        if (data) {
          const breaksRes = await fetch(`${API_URL}/api/timeclock/breaks?time_entry_id=${data.id}`, {
            headers: { Authorization: `Bearer ${token}` }
          });
          if (breaksRes.ok) {
            const breaks = await breaksRes.json();
            const activeBreak = breaks.find(b => !b.end_time);
            setCurrentBreak(activeBreak || null);
          }
        }
      }
    } catch (error) {
      console.error('Failed to fetch current entry:', error);
    }
  }, [token]);

  // Fetch today's entries
  const fetchTodayEntries = useCallback(async () => {
    try {
      const today = new Date().toISOString().split('T')[0];
      const response = await fetch(
        `${API_URL}/api/timeclock/entries?start_date=${today}T00:00:00Z&end_date=${today}T23:59:59Z`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (response.ok) {
        const data = await response.json();
        setTodayEntries(data);
      }
    } catch (error) {
      console.error('Failed to fetch entries:', error);
    }
  }, [token]);

  // Get GPS position
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
            accuracy: position.coords.accuracy
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

  // Initial load
  useEffect(() => {
    fetchCurrentEntry();
    fetchTodayEntries();
    getGPSPosition().catch(() => {});
  }, [fetchCurrentEntry, fetchTodayEntries]);

  // Update elapsed time
  useEffect(() => {
    if (!currentEntry || currentBreak) return;
    
    const interval = setInterval(() => {
      const clockIn = new Date(currentEntry.clock_in);
      const now = new Date();
      const diff = now - clockIn;
      
      const hours = Math.floor(diff / 3600000);
      const minutes = Math.floor((diff % 3600000) / 60000);
      const seconds = Math.floor((diff % 60000) / 1000);
      
      setElapsedTime(
        `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`
      );
    }, 1000);
    
    return () => clearInterval(interval);
  }, [currentEntry, currentBreak]);

  // Clock In
  const handleClockIn = async () => {
    setLoading(true);
    try {
      let position = gpsPosition;
      if (!position) {
        try {
          position = await getGPSPosition();
        } catch (e) {
          // Continue without GPS
        }
      }
      
      const response = await fetch(`${API_URL}/api/timeclock/clock-in`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          location_id: 'main', // TODO: Get from user's location
          latitude: position?.latitude,
          longitude: position?.longitude,
          accuracy: position?.accuracy,
          source: 'mobile'
        })
      });
      
      if (response.ok) {
        const data = await response.json();
        setCurrentEntry(data);
        toast.success('Clocked in successfully!');
        fetchTodayEntries();
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Failed to clock in');
      }
    } catch (error) {
      toast.error('Failed to clock in');
    }
    setLoading(false);
  };

  // Clock Out
  const handleClockOut = async () => {
    setLoading(true);
    try {
      let position = gpsPosition;
      if (!position) {
        try {
          position = await getGPSPosition();
        } catch (e) {}
      }
      
      const params = new URLSearchParams();
      if (position) {
        params.append('latitude', position.latitude);
        params.append('longitude', position.longitude);
        params.append('accuracy', position.accuracy);
      }
      params.append('source', 'mobile');
      
      const response = await fetch(`${API_URL}/api/timeclock/clock-out?${params}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` }
      });
      
      if (response.ok) {
        const data = await response.json();
        setCurrentEntry(null);
        toast.success(`Clocked out! Worked ${data.regular_hours?.toFixed(1) || 0} hours`);
        fetchTodayEntries();
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Failed to clock out');
      }
    } catch (error) {
      toast.error('Failed to clock out');
    }
    setLoading(false);
  };

  // Start Break
  const handleStartBreak = async () => {
    if (!currentEntry) return;
    setLoading(true);
    try {
      let position = gpsPosition;
      if (!position) {
        try {
          position = await getGPSPosition();
        } catch (e) {}
      }
      
      const response = await fetch(`${API_URL}/api/timeclock/breaks/start`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          time_entry_id: currentEntry.id,
          break_type: 'rest',
          latitude: position?.latitude,
          longitude: position?.longitude,
          accuracy: position?.accuracy
        })
      });
      
      if (response.ok) {
        const data = await response.json();
        setCurrentBreak(data);
        toast.success('Break started');
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Failed to start break');
      }
    } catch (error) {
      toast.error('Failed to start break');
    }
    setLoading(false);
  };

  // End Break
  const handleEndBreak = async () => {
    if (!currentEntry) return;
    setLoading(true);
    try {
      let position = gpsPosition;
      if (!position) {
        try {
          position = await getGPSPosition();
        } catch (e) {}
      }
      
      const params = new URLSearchParams({ time_entry_id: currentEntry.id });
      if (position) {
        params.append('latitude', position.latitude);
        params.append('longitude', position.longitude);
        params.append('accuracy', position.accuracy);
      }
      
      const response = await fetch(`${API_URL}/api/timeclock/breaks/end?${params}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` }
      });
      
      if (response.ok) {
        const data = await response.json();
        setCurrentBreak(null);
        toast.success(`Break ended (${data.duration_minutes || 0} minutes)`);
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Failed to end break');
      }
    } catch (error) {
      toast.error('Failed to end break');
    }
    setLoading(false);
  };

  const formatTime = (dateStr) => {
    if (!dateStr) return '--:--';
    return new Date(dateStr).toLocaleTimeString('en-US', { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  };

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      {/* Header */}
      <header className="bg-slate-900/80 backdrop-blur-sm border-b border-slate-800 sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => navigate('/staff/dashboard')}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <h1 className="text-xl font-bold">Time Clock</h1>
            <p className="text-sm text-slate-400">{new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' })}</p>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-6 space-y-6">
        {/* GPS Status */}
        <div className="flex items-center gap-2 text-sm">
          <MapPin className={`h-4 w-4 ${gpsPosition ? 'text-green-400' : 'text-slate-500'}`} />
          {gpsPosition ? (
            <span className="text-green-400">GPS Active (±{Math.round(gpsPosition.accuracy)}m)</span>
          ) : gpsError ? (
            <span className="text-yellow-400">{gpsError}</span>
          ) : (
            <span className="text-slate-500">Acquiring GPS...</span>
          )}
          <Button variant="ghost" size="sm" onClick={() => getGPSPosition().catch(() => {})}>
            Refresh
          </Button>
        </div>

        {/* Main Clock Card */}
        <Card className="bg-slate-900 border-slate-800">
          <CardContent className="p-8 text-center">
            {currentEntry ? (
              <>
                <div className="mb-4">
                  <Badge variant="outline" className={currentBreak ? 'border-yellow-500 text-yellow-400' : 'border-green-500 text-green-400'}>
                    {currentBreak ? 'ON BREAK' : 'CLOCKED IN'}
                  </Badge>
                </div>
                
                <div className="text-6xl font-mono font-bold mb-2 text-green-400">
                  {elapsedTime}
                </div>
                
                <p className="text-slate-400 mb-6">
                  Started at {formatTime(currentEntry.clock_in)}
                </p>
                
                <div className="flex flex-col sm:flex-row gap-4 justify-center">
                  {currentBreak ? (
                    <Button 
                      size="lg" 
                      onClick={handleEndBreak}
                      disabled={loading}
                      className="bg-yellow-600 hover:bg-yellow-700"
                    >
                      <Play className="h-5 w-5 mr-2" />
                      End Break
                    </Button>
                  ) : (
                    <>
                      <Button 
                        size="lg" 
                        variant="outline"
                        onClick={handleStartBreak}
                        disabled={loading}
                        className="border-yellow-600 text-yellow-400 hover:bg-yellow-600/20"
                      >
                        <Coffee className="h-5 w-5 mr-2" />
                        Start Break
                      </Button>
                      <Button 
                        size="lg" 
                        onClick={handleClockOut}
                        disabled={loading}
                        className="bg-red-600 hover:bg-red-700"
                      >
                        <Pause className="h-5 w-5 mr-2" />
                        Clock Out
                      </Button>
                    </>
                  )}
                </div>
              </>
            ) : (
              <>
                <Clock className="h-20 w-20 mx-auto mb-4 text-slate-600" />
                <p className="text-2xl text-slate-400 mb-6">Not Clocked In</p>
                <Button 
                  size="lg" 
                  onClick={handleClockIn}
                  disabled={loading}
                  className="bg-green-600 hover:bg-green-700 text-lg px-8 py-6"
                >
                  <Play className="h-6 w-6 mr-2" />
                  Clock In
                </Button>
              </>
            )}
          </CardContent>
        </Card>

        {/* Today's Entries */}
        <Card className="bg-slate-900 border-slate-800">
          <CardHeader>
            <CardTitle className="text-lg">Today's Time</CardTitle>
            <CardDescription>Your time entries for today</CardDescription>
          </CardHeader>
          <CardContent>
            {todayEntries.length === 0 ? (
              <p className="text-slate-500 text-center py-4">No entries today</p>
            ) : (
              <div className="space-y-3">
                {todayEntries.map((entry) => (
                  <div key={entry.id} className="flex items-center justify-between p-3 bg-slate-800/50 rounded-lg">
                    <div className="flex items-center gap-3">
                      {entry.clock_out ? (
                        <CheckCircle className="h-5 w-5 text-green-400" />
                      ) : (
                        <Clock className="h-5 w-5 text-blue-400 animate-pulse" />
                      )}
                      <div>
                        <p className="font-medium">
                          {formatTime(entry.clock_in)} - {entry.clock_out ? formatTime(entry.clock_out) : 'Active'}
                        </p>
                        {entry.discrepancies?.length > 0 && (
                          <div className="flex items-center gap-1 text-yellow-400 text-sm">
                            <AlertCircle className="h-3 w-3" />
                            {entry.discrepancies.join(', ')}
                          </div>
                        )}
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="font-mono">{(entry.regular_hours || 0).toFixed(1)}h</p>
                      {entry.overtime_hours > 0 && (
                        <p className="text-xs text-yellow-400">+{entry.overtime_hours.toFixed(1)}h OT</p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Quick Stats */}
        <div className="grid grid-cols-3 gap-4">
          <Card className="bg-slate-900 border-slate-800">
            <CardContent className="p-4 text-center">
              <p className="text-2xl font-bold text-green-400">
                {todayEntries.reduce((sum, e) => sum + (e.regular_hours || 0), 0).toFixed(1)}
              </p>
              <p className="text-xs text-slate-400">Regular Hours</p>
            </CardContent>
          </Card>
          <Card className="bg-slate-900 border-slate-800">
            <CardContent className="p-4 text-center">
              <p className="text-2xl font-bold text-yellow-400">
                {todayEntries.reduce((sum, e) => sum + (e.overtime_hours || 0), 0).toFixed(1)}
              </p>
              <p className="text-xs text-slate-400">Overtime</p>
            </CardContent>
          </Card>
          <Card className="bg-slate-900 border-slate-800">
            <CardContent className="p-4 text-center">
              <p className="text-2xl font-bold text-blue-400">
                {todayEntries.reduce((sum, e) => sum + (e.total_break_minutes || 0), 0)}
              </p>
              <p className="text-xs text-slate-400">Break (min)</p>
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  );
}
