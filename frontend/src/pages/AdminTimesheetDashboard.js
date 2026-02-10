import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Clock, Users, AlertTriangle, CheckCircle, Lock, Download, Calendar, RefreshCw, ChevronDown } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import useAuthStore from '../store/authStore';

const API_URL = process.env.REACT_APP_BACKEND_URL;

export default function AdminTimesheetDashboard() {
  const navigate = useNavigate();
  const { token } = useAuthStore();
  const [loading, setLoading] = useState(false);
  const [payPeriods, setPayPeriods] = useState([]);
  const [selectedPeriod, setSelectedPeriod] = useState(null);
  const [timesheetSummaries, setTimesheetSummaries] = useState([]);
  const [discrepancies, setDiscrepancies] = useState([]);
  const [createPeriodOpen, setCreatePeriodOpen] = useState(false);
  const [newPeriod, setNewPeriod] = useState({
    name: '',
    period_type: 'biweekly',
    start_date: '',
    end_date: ''
  });

  // Fetch pay periods
  const fetchPayPeriods = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/api/timeclock/pay-periods`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setPayPeriods(data);
        if (data.length > 0 && !selectedPeriod) {
          setSelectedPeriod(data[0]);
        }
      }
    } catch (error) {
      console.error('Failed to fetch pay periods:', error);
    }
  }, [token, selectedPeriod]);

  // Fetch timesheet summary for selected period
  const fetchSummary = useCallback(async () => {
    if (!selectedPeriod) return;
    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/api/timeclock/pay-periods/${selectedPeriod.id}/summary`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setTimesheetSummaries(data);
      }
    } catch (error) {
      console.error('Failed to fetch summary:', error);
    }
    setLoading(false);
  }, [token, selectedPeriod]);

  // Fetch discrepancies
  const fetchDiscrepancies = useCallback(async () => {
    if (!selectedPeriod) return;
    try {
      const response = await fetch(
        `${API_URL}/api/scheduling/reports/discrepancies?start_date=${selectedPeriod.start_date}&end_date=${selectedPeriod.end_date}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (response.ok) {
        const data = await response.json();
        setDiscrepancies(data.entries || []);
      }
    } catch (error) {
      console.error('Failed to fetch discrepancies:', error);
    }
  }, [token, selectedPeriod]);

  useEffect(() => {
    fetchPayPeriods();
  }, [fetchPayPeriods]);

  useEffect(() => {
    if (selectedPeriod) {
      fetchSummary();
      fetchDiscrepancies();
    }
  }, [selectedPeriod, fetchSummary, fetchDiscrepancies]);

  // Create pay period
  const handleCreatePeriod = async () => {
    if (!newPeriod.name || !newPeriod.start_date || !newPeriod.end_date) {
      toast.error('Please fill all required fields');
      return;
    }
    
    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/api/timeclock/pay-periods`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          ...newPeriod,
          start_date: new Date(newPeriod.start_date).toISOString(),
          end_date: new Date(newPeriod.end_date).toISOString()
        })
      });
      
      if (response.ok) {
        toast.success('Pay period created');
        setCreatePeriodOpen(false);
        setNewPeriod({ name: '', period_type: 'biweekly', start_date: '', end_date: '' });
        fetchPayPeriods();
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Failed to create pay period');
      }
    } catch (error) {
      toast.error('Failed to create pay period');
    }
    setLoading(false);
  };

  // Approve pay period
  const handleApprovePeriod = async () => {
    if (!selectedPeriod) return;
    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/api/timeclock/pay-periods/${selectedPeriod.id}/approve`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` }
      });
      
      if (response.ok) {
        toast.success('Pay period approved');
        fetchPayPeriods();
        fetchSummary();
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Failed to approve');
      }
    } catch (error) {
      toast.error('Failed to approve pay period');
    }
    setLoading(false);
  };

  // Lock pay period
  const handleLockPeriod = async () => {
    if (!selectedPeriod) return;
    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/api/timeclock/pay-periods/${selectedPeriod.id}/lock`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` }
      });
      
      if (response.ok) {
        toast.success('Pay period locked');
        fetchPayPeriods();
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Failed to lock');
      }
    } catch (error) {
      toast.error('Failed to lock pay period');
    }
    setLoading(false);
  };

  // Export CSV
  const handleExport = async (type) => {
    if (!selectedPeriod) return;
    try {
      const url = type === 'detail' 
        ? `${API_URL}/api/exports/timesheets/csv?pay_period_id=${selectedPeriod.id}`
        : `${API_URL}/api/exports/timesheets/summary/csv?pay_period_id=${selectedPeriod.id}`;
      
      const response = await fetch(url, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      if (response.ok) {
        const blob = await response.blob();
        const downloadUrl = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = downloadUrl;
        a.download = `timesheet_${type}_${selectedPeriod.name.replace(/\s/g, '_')}.csv`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        toast.success('Export downloaded');
      } else {
        toast.error('Export failed');
      }
    } catch (error) {
      toast.error('Export failed');
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '';
    return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'locked': return 'bg-slate-500';
      case 'approved': return 'bg-green-500';
      case 'pending_approval': return 'bg-yellow-500';
      default: return 'bg-blue-500';
    }
  };

  // Calculate totals
  const totalRegular = timesheetSummaries.reduce((sum, s) => sum + s.regular_hours, 0);
  const totalOT = timesheetSummaries.reduce((sum, s) => sum + s.overtime_hours, 0);
  const totalDiscrepancies = timesheetSummaries.reduce((sum, s) => sum + s.discrepancy_count, 0);

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      {/* Header */}
      <header className="bg-slate-900/80 backdrop-blur-sm border-b border-slate-800 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="icon" onClick={() => navigate('/admin/dashboard')}>
              <ArrowLeft className="h-5 w-5" />
            </Button>
            <div>
              <h1 className="text-xl font-bold flex items-center gap-2">
                <Clock className="h-5 w-5" />
                Timesheet Management
              </h1>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" onClick={() => setCreatePeriodOpen(true)}>
              <Calendar className="h-4 w-4 mr-2" />
              New Period
            </Button>
            <Button variant="ghost" size="icon" onClick={() => { fetchSummary(); fetchDiscrepancies(); }}>
              <RefreshCw className={`h-5 w-5 ${loading ? 'animate-spin' : ''}`} />
            </Button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6 space-y-6">
        {/* Pay Period Selector */}
        <Card className="bg-slate-900 border-slate-800">
          <CardContent className="p-4">
            <div className="flex flex-wrap items-center gap-4">
              <div className="flex-1 min-w-[200px]">
                <label className="text-sm text-slate-400 mb-1 block">Pay Period</label>
                <Select 
                  value={selectedPeriod?.id || ''} 
                  onValueChange={(val) => setSelectedPeriod(payPeriods.find(p => p.id === val))}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select pay period" />
                  </SelectTrigger>
                  <SelectContent>
                    {payPeriods.map((period) => (
                      <SelectItem key={period.id} value={period.id}>
                        {period.name} ({formatDate(period.start_date)} - {formatDate(period.end_date)})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              
              {selectedPeriod && (
                <>
                  <Badge className={getStatusColor(selectedPeriod.status)}>
                    {selectedPeriod.status?.toUpperCase()}
                  </Badge>
                  
                  <div className="flex gap-2">
                    {selectedPeriod.status === 'open' && (
                      <Button onClick={handleApprovePeriod} disabled={loading}>
                        <CheckCircle className="h-4 w-4 mr-2" />
                        Approve All
                      </Button>
                    )}
                    {selectedPeriod.status === 'approved' && (
                      <Button onClick={handleLockPeriod} disabled={loading} variant="destructive">
                        <Lock className="h-4 w-4 mr-2" />
                        Lock Period
                      </Button>
                    )}
                    <Button variant="outline" onClick={() => handleExport('summary')}>
                      <Download className="h-4 w-4 mr-2" />
                      Export Summary
                    </Button>
                    <Button variant="outline" onClick={() => handleExport('detail')}>
                      <Download className="h-4 w-4 mr-2" />
                      Export Detail
                    </Button>
                  </div>
                </>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Summary Stats */}
        <div className="grid grid-cols-4 gap-4">
          <Card className="bg-slate-900 border-slate-800">
            <CardContent className="p-4 text-center">
              <Users className="h-8 w-8 mx-auto mb-2 text-blue-400" />
              <p className="text-3xl font-bold">{timesheetSummaries.length}</p>
              <p className="text-sm text-slate-400">Staff Members</p>
            </CardContent>
          </Card>
          <Card className="bg-slate-900 border-slate-800">
            <CardContent className="p-4 text-center">
              <Clock className="h-8 w-8 mx-auto mb-2 text-green-400" />
              <p className="text-3xl font-bold">{totalRegular.toFixed(1)}</p>
              <p className="text-sm text-slate-400">Regular Hours</p>
            </CardContent>
          </Card>
          <Card className="bg-slate-900 border-slate-800">
            <CardContent className="p-4 text-center">
              <Clock className="h-8 w-8 mx-auto mb-2 text-yellow-400" />
              <p className="text-3xl font-bold">{totalOT.toFixed(1)}</p>
              <p className="text-sm text-slate-400">Overtime Hours</p>
            </CardContent>
          </Card>
          <Card className="bg-slate-900 border-slate-800">
            <CardContent className="p-4 text-center">
              <AlertTriangle className="h-8 w-8 mx-auto mb-2 text-red-400" />
              <p className="text-3xl font-bold">{totalDiscrepancies}</p>
              <p className="text-sm text-slate-400">Discrepancies</p>
            </CardContent>
          </Card>
        </div>

        {/* Timesheet Table */}
        <Card className="bg-slate-900 border-slate-800">
          <CardHeader>
            <CardTitle>Staff Timesheets</CardTitle>
            <CardDescription>Hours breakdown by staff member</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-slate-800">
                    <th className="text-left p-3 text-sm text-slate-400">Staff</th>
                    <th className="text-right p-3 text-sm text-slate-400">Entries</th>
                    <th className="text-right p-3 text-sm text-slate-400">Regular</th>
                    <th className="text-right p-3 text-sm text-slate-400">OT</th>
                    <th className="text-right p-3 text-sm text-slate-400">Double</th>
                    <th className="text-right p-3 text-sm text-slate-400">Total</th>
                    <th className="text-right p-3 text-sm text-slate-400">Breaks</th>
                    <th className="text-center p-3 text-sm text-slate-400">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {timesheetSummaries.map((summary) => (
                    <tr key={summary.staff_id} className="border-b border-slate-800/50 hover:bg-slate-800/30">
                      <td className="p-3">
                        <div className="font-medium">{summary.staff_name}</div>
                        {summary.discrepancy_count > 0 && (
                          <div className="text-xs text-red-400 flex items-center gap-1">
                            <AlertTriangle className="h-3 w-3" />
                            {summary.discrepancy_count} issues
                          </div>
                        )}
                      </td>
                      <td className="p-3 text-right">{summary.entry_count}</td>
                      <td className="p-3 text-right font-mono">{summary.regular_hours.toFixed(2)}</td>
                      <td className="p-3 text-right font-mono text-yellow-400">
                        {summary.overtime_hours > 0 ? summary.overtime_hours.toFixed(2) : '-'}
                      </td>
                      <td className="p-3 text-right font-mono text-red-400">
                        {summary.double_time_hours > 0 ? summary.double_time_hours.toFixed(2) : '-'}
                      </td>
                      <td className="p-3 text-right font-mono font-bold">{summary.total_hours.toFixed(2)}</td>
                      <td className="p-3 text-right text-sm text-slate-400">{summary.total_break_minutes}m</td>
                      <td className="p-3 text-center">
                        <Badge variant={summary.entries_approved === summary.entry_count ? 'success' : summary.entries_flagged > 0 ? 'destructive' : 'secondary'}>
                          {summary.entries_approved}/{summary.entry_count}
                        </Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr className="bg-slate-800/50 font-bold">
                    <td className="p-3">TOTALS</td>
                    <td className="p-3 text-right">{timesheetSummaries.reduce((s, t) => s + t.entry_count, 0)}</td>
                    <td className="p-3 text-right font-mono">{totalRegular.toFixed(2)}</td>
                    <td className="p-3 text-right font-mono text-yellow-400">{totalOT.toFixed(2)}</td>
                    <td className="p-3 text-right font-mono text-red-400">
                      {timesheetSummaries.reduce((s, t) => s + t.double_time_hours, 0).toFixed(2)}
                    </td>
                    <td className="p-3 text-right font-mono">
                      {(totalRegular + totalOT + timesheetSummaries.reduce((s, t) => s + t.double_time_hours, 0)).toFixed(2)}
                    </td>
                    <td className="p-3 text-right text-sm">
                      {timesheetSummaries.reduce((s, t) => s + t.total_break_minutes, 0)}m
                    </td>
                    <td></td>
                  </tr>
                </tfoot>
              </table>
            </div>
          </CardContent>
        </Card>

        {/* Discrepancies */}
        {discrepancies.length > 0 && (
          <Card className="bg-slate-900 border-slate-800">
            <CardHeader>
              <CardTitle className="text-red-400 flex items-center gap-2">
                <AlertTriangle className="h-5 w-5" />
                Discrepancies Requiring Attention
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {discrepancies.slice(0, 10).map((entry) => (
                  <div key={entry.id} className="flex items-center justify-between p-3 bg-red-900/20 rounded-lg border border-red-900/50">
                    <div>
                      <p className="font-medium">{entry.staff_name}</p>
                      <p className="text-sm text-slate-400">
                        {new Date(entry.clock_in).toLocaleDateString()} - {entry.discrepancies?.join(', ')}
                      </p>
                    </div>
                    <Button variant="outline" size="sm">
                      Resolve
                    </Button>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}
      </main>

      {/* Create Pay Period Dialog */}
      <Dialog open={createPeriodOpen} onOpenChange={setCreatePeriodOpen}>
        <DialogContent className="bg-slate-900 border-slate-800">
          <DialogHeader>
            <DialogTitle>Create Pay Period</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <label className="text-sm text-slate-400 mb-1 block">Name</label>
              <input
                type="text"
                value={newPeriod.name}
                onChange={(e) => setNewPeriod({...newPeriod, name: e.target.value})}
                placeholder="e.g., Feb 1-14 2026"
                className="w-full p-2 bg-slate-800 border border-slate-700 rounded-lg"
              />
            </div>
            <div>
              <label className="text-sm text-slate-400 mb-1 block">Type</label>
              <Select value={newPeriod.period_type} onValueChange={(val) => setNewPeriod({...newPeriod, period_type: val})}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="weekly">Weekly</SelectItem>
                  <SelectItem value="biweekly">Bi-Weekly</SelectItem>
                  <SelectItem value="semimonthly">Semi-Monthly</SelectItem>
                  <SelectItem value="monthly">Monthly</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm text-slate-400 mb-1 block">Start Date</label>
                <input
                  type="date"
                  value={newPeriod.start_date}
                  onChange={(e) => setNewPeriod({...newPeriod, start_date: e.target.value})}
                  className="w-full p-2 bg-slate-800 border border-slate-700 rounded-lg"
                />
              </div>
              <div>
                <label className="text-sm text-slate-400 mb-1 block">End Date</label>
                <input
                  type="date"
                  value={newPeriod.end_date}
                  onChange={(e) => setNewPeriod({...newPeriod, end_date: e.target.value})}
                  className="w-full p-2 bg-slate-800 border border-slate-700 rounded-lg"
                />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreatePeriodOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleCreatePeriod} disabled={loading}>
              Create Period
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
