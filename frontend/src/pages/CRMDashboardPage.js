import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { Textarea } from '../components/ui/textarea';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { toast } from 'sonner';
import { 
  ArrowLeftIcon, PlusIcon, UsersIcon, TrendingUpIcon, UserPlusIcon,
  PhoneIcon, MailIcon, RefreshCwIcon, CheckCircleIcon, XCircleIcon,
  ChevronRightIcon, ActivityIcon, DollarSignIcon, RepeatIcon
} from 'lucide-react';
import api from '../utils/api';

const LEAD_SOURCES = [
  { value: 'walk_in', label: 'Walk-In' },
  { value: 'website', label: 'Website' },
  { value: 'referral', label: 'Referral' },
  { value: 'social', label: 'Social Media' },
  { value: 'other', label: 'Other' }
];

const LEAD_STATUSES = [
  { value: 'new', label: 'New', color: 'bg-blue-500' },
  { value: 'contacted', label: 'Contacted', color: 'bg-amber-500' },
  { value: 'qualified', label: 'Qualified', color: 'bg-purple-500' },
  { value: 'converted', label: 'Converted', color: 'bg-green-500' },
  { value: 'lost', label: 'Lost', color: 'bg-red-500' }
];

const LIFECYCLE_COLORS = {
  lead: 'bg-blue-500',
  new: 'bg-green-500',
  active: 'bg-emerald-500',
  at_risk: 'bg-amber-500',
  lapsed: 'bg-orange-500',
  churned: 'bg-red-500'
};

export default function CRMDashboardPage() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('leads');
  const [leads, setLeads] = useState([]);
  const [retentionMetrics, setRetentionMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  
  // Lead form
  const [showAddLead, setShowAddLead] = useState(false);
  const [newLead, setNewLead] = useState({
    name: '', email: '', phone: '', source: 'walk_in', notes: ''
  });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [leadsRes, metricsRes] = await Promise.all([
        api.get('/moego/crm/leads'),
        api.get('/moego/crm/retention-metrics')
      ]);
      setLeads(leadsRes.data.leads || []);
      setRetentionMetrics(metricsRes.data);
    } catch (error) {
      console.error('Failed to load CRM data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAddLead = async () => {
    if (!newLead.name) {
      toast.error('Name is required');
      return;
    }
    
    try {
      await api.post('/moego/crm/leads', newLead);
      toast.success('Lead added');
      setShowAddLead(false);
      setNewLead({ name: '', email: '', phone: '', source: 'walk_in', notes: '' });
      loadData();
    } catch (error) {
      toast.error('Failed to add lead');
    }
  };

  const updateLeadStatus = async (leadId, status) => {
    try {
      await api.put(`/moego/crm/leads/${leadId}/status`, { status });
      toast.success('Lead updated');
      loadData();
    } catch (error) {
      toast.error('Failed to update lead');
    }
  };

  const convertLead = async (leadId) => {
    try {
      await api.post(`/moego/crm/leads/${leadId}/convert`);
      toast.success('Lead converted to customer');
      loadData();
    } catch (error) {
      toast.error('Failed to convert lead');
    }
  };

  const formatCurrency = (cents) => `$${(cents / 100).toFixed(2)}`;

  const getStatusBadge = (status) => {
    const statusConfig = LEAD_STATUSES.find(s => s.value === status) || LEAD_STATUSES[0];
    return <Badge className={`${statusConfig.color} text-white`}>{statusConfig.label}</Badge>;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="animate-spin h-8 w-8 border-2 border-blue-500 border-t-transparent rounded-full"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950" data-testid="crm-dashboard-page">
      {/* Header */}
      <header className="bg-slate-900 border-b border-slate-700 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="sm" onClick={() => navigate('/admin/dashboard')} className="text-slate-400 hover:text-white">
              <ArrowLeftIcon size={20} />
            </Button>
            <div>
              <h1 className="text-2xl font-bold text-white">CRM Dashboard</h1>
              <p className="text-slate-400 text-sm">Leads, customers, and retention</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Button variant="outline" size="sm" onClick={loadData} className="border-slate-600 text-slate-300">
              <RefreshCwIcon size={16} />
            </Button>
            <Button onClick={() => setShowAddLead(true)} className="bg-blue-600 hover:bg-blue-700">
              <UserPlusIcon size={16} className="mr-2" />
              Add Lead
            </Button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Retention Metrics Cards */}
        {retentionMetrics && (
          <div className="grid grid-cols-4 gap-4 mb-8">
            <Card className="bg-slate-900 border-slate-700">
              <CardContent className="p-4 flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-blue-500/20 flex items-center justify-center">
                  <UsersIcon className="text-blue-400" size={20} />
                </div>
                <div>
                  <p className="text-2xl font-bold text-white">{retentionMetrics.total_customers}</p>
                  <p className="text-xs text-slate-400">Total Customers</p>
                </div>
              </CardContent>
            </Card>
            <Card className="bg-slate-900 border-slate-700">
              <CardContent className="p-4 flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-green-500/20 flex items-center justify-center">
                  <DollarSignIcon className="text-green-400" size={20} />
                </div>
                <div>
                  <p className="text-2xl font-bold text-white">{formatCurrency(retentionMetrics.average_ltv_cents)}</p>
                  <p className="text-xs text-slate-400">Avg. Lifetime Value</p>
                </div>
              </CardContent>
            </Card>
            <Card className="bg-slate-900 border-slate-700">
              <CardContent className="p-4 flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-purple-500/20 flex items-center justify-center">
                  <RepeatIcon className="text-purple-400" size={20} />
                </div>
                <div>
                  <p className="text-2xl font-bold text-white">{retentionMetrics.repeat_rate_percent}%</p>
                  <p className="text-xs text-slate-400">Repeat Rate</p>
                </div>
              </CardContent>
            </Card>
            <Card className="bg-slate-900 border-slate-700">
              <CardContent className="p-4 flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-amber-500/20 flex items-center justify-center">
                  <ActivityIcon className="text-amber-400" size={20} />
                </div>
                <div>
                  <p className="text-2xl font-bold text-white">{retentionMetrics.average_visits}</p>
                  <p className="text-xs text-slate-400">Avg. Visits</p>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Lifecycle Breakdown */}
        {retentionMetrics?.by_lifecycle && Object.keys(retentionMetrics.by_lifecycle).length > 0 && (
          <Card className="bg-slate-900 border-slate-700 mb-8">
            <CardHeader>
              <CardTitle className="text-white">Customer Lifecycle</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-4">
                {Object.entries(retentionMetrics.by_lifecycle).map(([stage, count]) => (
                  <div key={stage} className="flex items-center gap-2">
                    <Badge className={`${LIFECYCLE_COLORS[stage] || 'bg-slate-500'} text-white capitalize`}>
                      {stage.replace('_', ' ')}
                    </Badge>
                    <span className="text-white font-semibold">{count}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="bg-slate-800 border border-slate-700 mb-6">
            <TabsTrigger value="leads" className="data-[state=active]:bg-blue-600">
              <UserPlusIcon size={16} className="mr-2" />
              Leads ({leads.length})
            </TabsTrigger>
            <TabsTrigger value="pipeline" className="data-[state=active]:bg-blue-600">
              <TrendingUpIcon size={16} className="mr-2" />
              Pipeline View
            </TabsTrigger>
          </TabsList>

          {/* Leads List */}
          <TabsContent value="leads">
            <div className="space-y-4">
              {leads.length === 0 ? (
                <Card className="bg-slate-900 border-slate-700">
                  <CardContent className="py-12 text-center">
                    <UserPlusIcon className="mx-auto text-slate-600 mb-4" size={48} />
                    <p className="text-slate-400">No leads yet. Add your first lead!</p>
                  </CardContent>
                </Card>
              ) : (
                leads.map(lead => (
                  <Card key={lead.id} className="bg-slate-900 border-slate-700" data-testid={`lead-${lead.id}`}>
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-3 mb-2">
                            <h3 className="text-white font-semibold text-lg">{lead.name}</h3>
                            {getStatusBadge(lead.status)}
                            <Badge className="bg-slate-700 text-slate-300 capitalize">{lead.source}</Badge>
                          </div>
                          <div className="flex items-center gap-4 text-sm text-slate-400">
                            {lead.email && (
                              <span className="flex items-center gap-1">
                                <MailIcon size={14} />
                                {lead.email}
                              </span>
                            )}
                            {lead.phone && (
                              <span className="flex items-center gap-1">
                                <PhoneIcon size={14} />
                                {lead.phone}
                              </span>
                            )}
                          </div>
                          {lead.notes && (
                            <p className="text-sm text-slate-500 mt-2 italic">"{lead.notes}"</p>
                          )}
                          <p className="text-xs text-slate-600 mt-2">
                            Created: {new Date(lead.created_at).toLocaleDateString()}
                          </p>
                        </div>
                        
                        <div className="flex items-center gap-2">
                          {lead.status !== 'converted' && lead.status !== 'lost' && (
                            <>
                              <Select
                                value={lead.status}
                                onValueChange={(v) => updateLeadStatus(lead.id, v)}
                              >
                                <SelectTrigger className="w-32 bg-slate-800 border-slate-700 text-white text-sm">
                                  <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                  {LEAD_STATUSES.filter(s => s.value !== 'converted').map(s => (
                                    <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>
                                  ))}
                                </SelectContent>
                              </Select>
                              {lead.status === 'qualified' && (
                                <Button
                                  onClick={() => convertLead(lead.id)}
                                  size="sm"
                                  className="bg-green-600 hover:bg-green-700"
                                >
                                  <CheckCircleIcon size={14} className="mr-1" />
                                  Convert
                                </Button>
                              )}
                            </>
                          )}
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))
              )}
            </div>
          </TabsContent>

          {/* Pipeline View */}
          <TabsContent value="pipeline">
            <div className="grid grid-cols-5 gap-4">
              {LEAD_STATUSES.map(status => {
                const statusLeads = leads.filter(l => l.status === status.value);
                return (
                  <Card key={status.value} className="bg-slate-900 border-slate-700">
                    <CardHeader className="pb-2">
                      <div className="flex items-center justify-between">
                        <Badge className={`${status.color} text-white`}>{status.label}</Badge>
                        <span className="text-slate-500 text-sm">{statusLeads.length}</span>
                      </div>
                    </CardHeader>
                    <CardContent className="p-2 space-y-2 max-h-96 overflow-y-auto">
                      {statusLeads.length === 0 ? (
                        <p className="text-slate-600 text-xs text-center py-4">No leads</p>
                      ) : (
                        statusLeads.map(lead => (
                          <div key={lead.id} className="bg-slate-800 rounded-lg p-3">
                            <p className="text-white text-sm font-medium">{lead.name}</p>
                            <p className="text-slate-500 text-xs capitalize">{lead.source}</p>
                          </div>
                        ))
                      )}
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          </TabsContent>
        </Tabs>
      </main>

      {/* Add Lead Modal */}
      <Dialog open={showAddLead} onOpenChange={setShowAddLead}>
        <DialogContent className="bg-slate-900 border-slate-700 max-w-md">
          <DialogHeader>
            <DialogTitle className="text-white flex items-center gap-2">
              <UserPlusIcon size={20} />
              Add New Lead
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <Label className="text-slate-300">Name *</Label>
              <Input
                value={newLead.name}
                onChange={(e) => setNewLead({ ...newLead, name: e.target.value })}
                className="bg-slate-800 border-slate-700 text-white mt-1"
                placeholder="John Smith"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label className="text-slate-300">Email</Label>
                <Input
                  type="email"
                  value={newLead.email}
                  onChange={(e) => setNewLead({ ...newLead, email: e.target.value })}
                  className="bg-slate-800 border-slate-700 text-white mt-1"
                  placeholder="john@email.com"
                />
              </div>
              <div>
                <Label className="text-slate-300">Phone</Label>
                <Input
                  value={newLead.phone}
                  onChange={(e) => setNewLead({ ...newLead, phone: e.target.value })}
                  className="bg-slate-800 border-slate-700 text-white mt-1"
                  placeholder="555-1234"
                />
              </div>
            </div>
            <div>
              <Label className="text-slate-300">Source</Label>
              <Select value={newLead.source} onValueChange={(v) => setNewLead({ ...newLead, source: v })}>
                <SelectTrigger className="bg-slate-800 border-slate-700 text-white mt-1">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {LEAD_SOURCES.map(s => (
                    <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-slate-300">Notes</Label>
              <Textarea
                value={newLead.notes}
                onChange={(e) => setNewLead({ ...newLead, notes: e.target.value })}
                className="bg-slate-800 border-slate-700 text-white mt-1"
                placeholder="Any additional notes..."
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAddLead(false)} className="border-slate-600 text-slate-300">Cancel</Button>
            <Button onClick={handleAddLead} className="bg-blue-600 hover:bg-blue-700">Add Lead</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
