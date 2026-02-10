import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Badge } from '../components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { Calendar } from '../components/ui/calendar';
import { toast } from 'sonner';
import { 
  PlusIcon, 
  CalendarIcon, 
  ClockIcon, 
  CheckCircleIcon,
  XCircleIcon,
  ArrowLeftIcon,
  UmbrellaIcon,
  HeartPulseIcon,
  PlaneIcon,
  BriefcaseIcon,
  AlertCircleIcon,
  FilterIcon
} from 'lucide-react';
import api from '../utils/api';
import useAuthStore from '../store/authStore';

const REQUEST_TYPES = [
  { value: 'vacation', label: 'Vacation', icon: PlaneIcon, color: 'blue' },
  { value: 'sick', label: 'Sick Leave', icon: HeartPulseIcon, color: 'red' },
  { value: 'personal', label: 'Personal Day', icon: UmbrellaIcon, color: 'purple' },
  { value: 'unpaid', label: 'Unpaid Leave', icon: BriefcaseIcon, color: 'gray' },
];

export default function TimeOffPage() {
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const isAdmin = user?.role === 'admin';
  
  const [requests, setRequests] = useState([]);
  const [policies, setPolicies] = useState([]);
  const [balances, setBalances] = useState({});
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('all');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [selectedDates, setSelectedDates] = useState([]);
  const [activeTab, setActiveTab] = useState('my-requests');

  // Create request form
  const [newRequest, setNewRequest] = useState({
    policy_type: 'vacation',
    start_date: '',
    end_date: '',
    reason: '',
    hours: 8
  });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [requestsRes, policiesRes] = await Promise.all([
        api.get('/hr/requests'),
        api.get('/hr/policies').catch(() => ({ data: [] }))
      ]);
      setRequests(requestsRes.data || []);
      setPolicies(policiesRes.data || []);
      
      // Calculate balances (simplified)
      const balanceMap = {};
      for (const policy of (policiesRes.data || [])) {
        balanceMap[policy.policy_type] = {
          available: policy.accrual_amount || 0,
          used: 0,
          pending: 0
        };
      }
      setBalances(balanceMap);
    } catch (error) {
      console.error('Failed to load time off data:', error);
      toast.error('Failed to load time off data');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateRequest = async () => {
    if (!newRequest.start_date || !newRequest.end_date) {
      toast.error('Please select start and end dates');
      return;
    }

    try {
      await api.post('/hr/requests', {
        ...newRequest,
        status: 'pending'
      });
      toast.success('Time off request submitted');
      setShowCreateModal(false);
      setNewRequest({ policy_type: 'vacation', start_date: '', end_date: '', reason: '', hours: 8 });
      loadData();
    } catch (error) {
      toast.error('Failed to submit request');
    }
  };

  const handleReviewRequest = async (requestId, status, notes = '') => {
    try {
      await api.post(`/hr/requests/${requestId}/review?status=${status}${notes ? `&notes=${encodeURIComponent(notes)}` : ''}`);
      toast.success(`Request ${status}`);
      loadData();
    } catch (error) {
      toast.error('Failed to review request');
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'approved': return 'bg-green-500/20 text-green-400 border-green-500/30';
      case 'rejected': return 'bg-red-500/20 text-red-400 border-red-500/30';
      case 'pending': return 'bg-amber-500/20 text-amber-400 border-amber-500/30';
      case 'cancelled': return 'bg-slate-500/20 text-slate-400 border-slate-500/30';
      default: return 'bg-slate-500/20 text-slate-400 border-slate-500/30';
    }
  };

  const getTypeInfo = (type) => {
    return REQUEST_TYPES.find(t => t.value === type) || REQUEST_TYPES[0];
  };

  const filteredRequests = requests.filter(r => {
    if (statusFilter === 'all') return true;
    return r.status === statusFilter;
  });

  const myRequests = filteredRequests.filter(r => r.staff_id === user?.id);
  const pendingApprovals = filteredRequests.filter(r => r.status === 'pending');

  const calculateDays = (start, end) => {
    if (!start || !end) return 0;
    const startDate = new Date(start);
    const endDate = new Date(end);
    const diffTime = Math.abs(endDate - startDate);
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24)) + 1;
    return diffDays;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="animate-spin h-8 w-8 border-2 border-blue-500 border-t-transparent rounded-full"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950" data-testid="time-off-page">
      {/* Header */}
      <header className="bg-slate-900 border-b border-slate-700 px-6 py-4">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => navigate(isAdmin ? '/admin' : '/staff')}
                className="text-slate-400 hover:text-white"
              >
                <ArrowLeftIcon size={20} />
              </Button>
              <div>
                <h1 className="text-2xl font-bold text-white">Time Off</h1>
                <p className="text-slate-400 text-sm">Request and manage time off</p>
              </div>
            </div>
            <Button
              onClick={() => setShowCreateModal(true)}
              className="bg-blue-600 hover:bg-blue-700 text-white"
              data-testid="request-time-off-btn"
            >
              <PlusIcon size={18} className="mr-2" />
              Request Time Off
            </Button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Balance Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          {REQUEST_TYPES.map(type => {
            const balance = balances[type.value] || { available: 0, used: 0, pending: 0 };
            return (
              <Card key={type.value} className="bg-slate-900 border-slate-700">
                <CardContent className="p-4">
                  <div className="flex items-center gap-3">
                    <div className={`w-10 h-10 rounded-lg bg-${type.color}-500/20 flex items-center justify-center`}>
                      <type.icon className={`text-${type.color}-400`} size={20} />
                    </div>
                    <div className="flex-1">
                      <p className="text-slate-400 text-sm">{type.label}</p>
                      <div className="flex items-baseline gap-1">
                        <span className="text-2xl font-bold text-white">{balance.available}</span>
                        <span className="text-slate-500 text-sm">hrs available</span>
                      </div>
                    </div>
                  </div>
                  {balance.pending > 0 && (
                    <p className="text-amber-400 text-xs mt-2">{balance.pending} hrs pending</p>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <div className="flex items-center justify-between mb-6">
            <TabsList className="bg-slate-800">
              <TabsTrigger value="my-requests" className="data-[state=active]:bg-slate-700">
                My Requests
              </TabsTrigger>
              {isAdmin && (
                <TabsTrigger value="approvals" className="data-[state=active]:bg-slate-700">
                  Approvals
                  {pendingApprovals.length > 0 && (
                    <Badge className="ml-2 bg-amber-500 text-white">{pendingApprovals.length}</Badge>
                  )}
                </TabsTrigger>
              )}
              <TabsTrigger value="calendar" className="data-[state=active]:bg-slate-700">
                Calendar
              </TabsTrigger>
            </TabsList>

            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-40 bg-slate-800 border-slate-700 text-white">
                <FilterIcon size={14} className="mr-2" />
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="pending">Pending</SelectItem>
                <SelectItem value="approved">Approved</SelectItem>
                <SelectItem value="rejected">Rejected</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* My Requests Tab */}
          <TabsContent value="my-requests">
            {myRequests.length === 0 ? (
              <Card className="bg-slate-900 border-slate-700">
                <CardContent className="py-12 text-center">
                  <CalendarIcon className="mx-auto text-slate-600 mb-4" size={48} />
                  <h3 className="text-lg font-semibold text-slate-400 mb-2">No time off requests</h3>
                  <p className="text-slate-500 mb-4">Submit your first time off request</p>
                  <Button onClick={() => setShowCreateModal(true)} className="bg-blue-600 hover:bg-blue-700">
                    <PlusIcon size={16} className="mr-2" />
                    Request Time Off
                  </Button>
                </CardContent>
              </Card>
            ) : (
              <div className="space-y-3">
                {myRequests.map(request => {
                  const typeInfo = getTypeInfo(request.policy_type);
                  return (
                    <Card key={request.id} className="bg-slate-900 border-slate-700" data-testid={`request-card-${request.id}`}>
                      <CardContent className="p-4">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-4">
                            <div className={`w-10 h-10 rounded-lg bg-${typeInfo.color}-500/20 flex items-center justify-center`}>
                              <typeInfo.icon className={`text-${typeInfo.color}-400`} size={20} />
                            </div>
                            <div>
                              <div className="flex items-center gap-2">
                                <h3 className="font-medium text-white">{typeInfo.label}</h3>
                                <Badge className={getStatusColor(request.status)}>
                                  {request.status}
                                </Badge>
                              </div>
                              <p className="text-slate-400 text-sm">
                                {new Date(request.start_date).toLocaleDateString()} - {new Date(request.end_date).toLocaleDateString()}
                                <span className="mx-2">•</span>
                                {calculateDays(request.start_date, request.end_date)} day(s)
                              </p>
                              {request.reason && (
                                <p className="text-slate-500 text-sm mt-1">{request.reason}</p>
                              )}
                            </div>
                          </div>
                          {request.status === 'pending' && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleReviewRequest(request.id, 'cancelled')}
                              className="text-slate-400 hover:text-red-400"
                            >
                              Cancel
                            </Button>
                          )}
                        </div>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            )}
          </TabsContent>

          {/* Approvals Tab (Admin) */}
          {isAdmin && (
            <TabsContent value="approvals">
              {pendingApprovals.length === 0 ? (
                <Card className="bg-slate-900 border-slate-700">
                  <CardContent className="py-12 text-center">
                    <CheckCircleIcon className="mx-auto text-green-500 mb-4" size={48} />
                    <h3 className="text-lg font-semibold text-slate-400 mb-2">All caught up!</h3>
                    <p className="text-slate-500">No pending time off requests to review</p>
                  </CardContent>
                </Card>
              ) : (
                <div className="space-y-3">
                  {pendingApprovals.map(request => {
                    const typeInfo = getTypeInfo(request.policy_type);
                    return (
                      <Card key={request.id} className="bg-slate-900 border-slate-700">
                        <CardContent className="p-4">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-4">
                              <div className={`w-10 h-10 rounded-lg bg-${typeInfo.color}-500/20 flex items-center justify-center`}>
                                <typeInfo.icon className={`text-${typeInfo.color}-400`} size={20} />
                              </div>
                              <div>
                                <div className="flex items-center gap-2">
                                  <h3 className="font-medium text-white">{request.staff_name || 'Staff Member'}</h3>
                                  <Badge variant="outline" className="border-slate-600 text-slate-400">
                                    {typeInfo.label}
                                  </Badge>
                                </div>
                                <p className="text-slate-400 text-sm">
                                  {new Date(request.start_date).toLocaleDateString()} - {new Date(request.end_date).toLocaleDateString()}
                                  <span className="mx-2">•</span>
                                  {calculateDays(request.start_date, request.end_date)} day(s)
                                </p>
                                {request.reason && (
                                  <p className="text-slate-500 text-sm mt-1">{request.reason}</p>
                                )}
                              </div>
                            </div>
                            <div className="flex gap-2">
                              <Button
                                size="sm"
                                onClick={() => handleReviewRequest(request.id, 'approved')}
                                className="bg-green-600 hover:bg-green-700"
                              >
                                <CheckCircleIcon size={16} className="mr-1" />
                                Approve
                              </Button>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => handleReviewRequest(request.id, 'rejected')}
                                className="border-red-500/50 text-red-400 hover:bg-red-500/20"
                              >
                                <XCircleIcon size={16} className="mr-1" />
                                Reject
                              </Button>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    );
                  })}
                </div>
              )}
            </TabsContent>
          )}

          {/* Calendar Tab */}
          <TabsContent value="calendar">
            <Card className="bg-slate-900 border-slate-700">
              <CardContent className="p-6">
                <div className="flex justify-center">
                  <Calendar
                    mode="multiple"
                    selected={selectedDates}
                    onSelect={setSelectedDates}
                    className="rounded-md border border-slate-700"
                    modifiers={{
                      approved: requests
                        .filter(r => r.status === 'approved')
                        .flatMap(r => {
                          const dates = [];
                          let current = new Date(r.start_date);
                          const end = new Date(r.end_date);
                          while (current <= end) {
                            dates.push(new Date(current));
                            current.setDate(current.getDate() + 1);
                          }
                          return dates;
                        }),
                      pending: requests
                        .filter(r => r.status === 'pending')
                        .flatMap(r => {
                          const dates = [];
                          let current = new Date(r.start_date);
                          const end = new Date(r.end_date);
                          while (current <= end) {
                            dates.push(new Date(current));
                            current.setDate(current.getDate() + 1);
                          }
                          return dates;
                        })
                    }}
                    modifiersStyles={{
                      approved: { backgroundColor: 'rgba(34, 197, 94, 0.3)', color: 'white' },
                      pending: { backgroundColor: 'rgba(234, 179, 8, 0.3)', color: 'white' }
                    }}
                  />
                </div>
                <div className="flex justify-center gap-6 mt-4 text-sm">
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 rounded bg-green-500/30"></div>
                    <span className="text-slate-400">Approved</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 rounded bg-amber-500/30"></div>
                    <span className="text-slate-400">Pending</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </main>

      {/* Create Request Modal */}
      <Dialog open={showCreateModal} onOpenChange={setShowCreateModal}>
        <DialogContent className="bg-slate-900 border-slate-700 max-w-md">
          <DialogHeader>
            <DialogTitle className="text-white">Request Time Off</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <Label className="text-slate-300">Type</Label>
              <Select 
                value={newRequest.policy_type} 
                onValueChange={(v) => setNewRequest({ ...newRequest, policy_type: v })}
              >
                <SelectTrigger className="mt-1 bg-slate-800 border-slate-600 text-white">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {REQUEST_TYPES.map(type => (
                    <SelectItem key={type.value} value={type.value}>
                      <div className="flex items-center gap-2">
                        <type.icon size={16} />
                        {type.label}
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label className="text-slate-300">Start Date</Label>
                <Input
                  type="date"
                  value={newRequest.start_date}
                  onChange={(e) => setNewRequest({ ...newRequest, start_date: e.target.value })}
                  className="mt-1 bg-slate-800 border-slate-600 text-white"
                />
              </div>
              <div>
                <Label className="text-slate-300">End Date</Label>
                <Input
                  type="date"
                  value={newRequest.end_date}
                  onChange={(e) => setNewRequest({ ...newRequest, end_date: e.target.value })}
                  className="mt-1 bg-slate-800 border-slate-600 text-white"
                />
              </div>
            </div>

            {newRequest.start_date && newRequest.end_date && (
              <div className="bg-slate-800 rounded-lg p-3 text-center">
                <p className="text-slate-400 text-sm">
                  Total: <span className="text-white font-semibold">{calculateDays(newRequest.start_date, newRequest.end_date)} day(s)</span>
                </p>
              </div>
            )}

            <div>
              <Label className="text-slate-300">Reason (Optional)</Label>
              <Textarea
                value={newRequest.reason}
                onChange={(e) => setNewRequest({ ...newRequest, reason: e.target.value })}
                placeholder="Enter reason for time off..."
                className="mt-1 bg-slate-800 border-slate-600 text-white"
                rows={3}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCreateModal(false)} className="border-slate-600 text-slate-300">
              Cancel
            </Button>
            <Button onClick={handleCreateRequest} className="bg-blue-600 hover:bg-blue-700">
              Submit Request
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
