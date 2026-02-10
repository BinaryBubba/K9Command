import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { Textarea } from '../components/ui/textarea';
import { toast } from 'sonner';
import { 
  ArrowLeftIcon, PlusIcon, UserPlusIcon, UsersIcon, SearchIcon,
  PhoneIcon, MailIcon, DogIcon, CalendarIcon, TrendingUpIcon, 
  TargetIcon, RefreshCwIcon, EditIcon, CheckCircleIcon, XCircleIcon,
  ChevronRightIcon, DollarSignIcon
} from 'lucide-react';
import api from '../utils/api';

const LEAD_SOURCES = [
  { value: 'walk_in', label: 'Walk-in' },
  { value: 'website', label: 'Website' },
  { value: 'referral', label: 'Referral' },
  { value: 'social', label: 'Social Media' },
  { value: 'phone', label: 'Phone Call' },
  { value: 'other', label: 'Other' }
];

const LEAD_STATUS = [
  { value: 'new', label: 'New', color: 'bg-blue-500' },
  { value: 'contacted', label: 'Contacted', color: 'bg-yellow-500' },
  { value: 'qualified', label: 'Qualified', color: 'bg-purple-500' },
  { value: 'converted', label: 'Converted', color: 'bg-green-500' },
  { value: 'lost', label: 'Lost', color: 'bg-red-500' }
];

const LIFECYCLE_COLORS = {
  lead: 'bg-blue-500',
  new: 'bg-emerald-500',
  active: 'bg-green-500',
  at_risk: 'bg-amber-500',
  lapsed: 'bg-orange-500',
  churned: 'bg-red-500'
};

// Admin-expandable custom fields for leads
const DEFAULT_CUSTOM_FIELDS = [
  { id: 'preferred_contact', label: 'Preferred Contact Method', type: 'select', options: ['Phone', 'Email', 'Text'] },
  { id: 'referred_by', label: 'Referred By', type: 'text' },
  { id: 'budget_range', label: 'Budget Range', type: 'select', options: ['Basic', 'Standard', 'Premium'] },
  { id: 'follow_up_date', label: 'Follow-up Date', type: 'date' }
];

export default function CustomerLeadsPage() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('leads');
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterStatus, setFilterStatus] = useState('');
  const [filterSource, setFilterSource] = useState('');
  const [retentionMetrics, setRetentionMetrics] = useState(null);
  
  // Custom fields management (admin expandable)
  const [customFields, setCustomFields] = useState(DEFAULT_CUSTOM_FIELDS);
  const [showFieldManager, setShowFieldManager] = useState(false);
  const [newFieldName, setNewFieldName] = useState('');
  const [newFieldType, setNewFieldType] = useState('text');
  
  // Lead modals
  const [showAddModal, setShowAddModal] = useState(false);
  const [showDetailModal, setShowDetailModal] = useState(false);
  const [selectedLead, setSelectedLead] = useState(null);
  
  // New lead form
  const [newLead, setNewLead] = useState({
    name: '',
    email: '',
    phone: '',
    source: 'walk_in',
    notes: '',
    dog_info: {
      dog_name: '',
      breed: '',
      age: '',
      notes: ''
    },
    custom_fields: {}
  });

  useEffect(() => {
    loadLeads();
    loadRetentionMetrics();
  }, []);

  const loadLeads = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (filterStatus) params.append('status', filterStatus);
      if (filterSource) params.append('source', filterSource);
      
      const res = await api.get(`/moego/crm/leads?${params.toString()}`);
      setLeads(res.data.leads || []);
    } catch (error) {
      toast.error('Failed to load leads');
    } finally {
      setLoading(false);
    }
  };

  const loadRetentionMetrics = async () => {
    try {
      const res = await api.get('/moego/crm/retention-metrics');
      setRetentionMetrics(res.data);
    } catch (error) {
      console.error('Failed to load retention metrics:', error);
    }
  };

  const handleAddLead = async () => {
    if (!newLead.name) {
      toast.error('Name is required');
      return;
    }
    
    try {
      const dogInfo = newLead.dog_info.dog_name ? {
        name: newLead.dog_info.dog_name,
        breed: newLead.dog_info.breed,
        age: newLead.dog_info.age,
        notes: newLead.dog_info.notes
      } : null;
      
      await api.post('/moego/crm/leads', {
        name: newLead.name,
        email: newLead.email || null,
        phone: newLead.phone || null,
        source: newLead.source,
        notes: newLead.notes || null,
        dog_info: dogInfo
      });
      
      toast.success('Lead added successfully');
      setShowAddModal(false);
      resetNewLead();
      loadLeads();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to add lead');
    }
  };

  const handleUpdateStatus = async (leadId, newStatus, notes = '') => {
    try {
      await api.put(`/moego/crm/leads/${leadId}/status`, {
        status: newStatus,
        notes: notes || undefined
      });
      toast.success('Lead updated');
      loadLeads();
      if (selectedLead?.id === leadId) {
        setSelectedLead({ ...selectedLead, status: newStatus });
      }
    } catch (error) {
      toast.error('Failed to update lead');
    }
  };

  const handleConvertLead = async (leadId) => {
    try {
      await api.post(`/moego/crm/leads/${leadId}/convert`);
      toast.success('Lead converted to customer!');
      loadLeads();
      loadRetentionMetrics();
      setShowDetailModal(false);
    } catch (error) {
      toast.error('Failed to convert lead');
    }
  };

  const resetNewLead = () => {
    setNewLead({
      name: '',
      email: '',
      phone: '',
      source: 'walk_in',
      notes: '',
      dog_info: { dog_name: '', breed: '', age: '', notes: '' },
      custom_fields: {}
    });
  };

  const addCustomField = () => {
    if (!newFieldName.trim()) return;
    
    const newField = {
      id: newFieldName.toLowerCase().replace(/\s+/g, '_'),
      label: newFieldName,
      type: newFieldType,
      options: newFieldType === 'select' ? ['Option 1', 'Option 2'] : undefined
    };
    
    setCustomFields([...customFields, newField]);
    setNewFieldName('');
    setNewFieldType('text');
    toast.success('Custom field added');
  };

  const removeCustomField = (fieldId) => {
    setCustomFields(customFields.filter(f => f.id !== fieldId));
    toast.success('Field removed');
  };

  const filteredLeads = leads.filter(lead => {
    const matchesSearch = lead.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         lead.email?.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         lead.phone?.includes(searchTerm);
    return matchesSearch;
  });

  const formatCurrency = (cents) => `$${(cents / 100).toFixed(2)}`;
  const formatDate = (dateStr) => dateStr ? new Date(dateStr).toLocaleDateString() : '-';

  if (loading && leads.length === 0) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="animate-spin h-8 w-8 border-2 border-blue-500 border-t-transparent rounded-full"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950" data-testid="crm-leads-page">
      {/* Header */}
      <header className="bg-slate-900 border-b border-slate-700 px-6 py-4">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Button variant="ghost" size="sm" onClick={() => navigate('/admin/dashboard')} className="text-slate-400 hover:text-white">
                <ArrowLeftIcon size={20} />
              </Button>
              <div>
                <h1 className="text-2xl font-bold text-white">Customer Leads & CRM</h1>
                <p className="text-slate-400 text-sm">Manage leads, track customer lifecycle</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Button variant="outline" size="sm" onClick={() => setShowFieldManager(true)} className="border-slate-600 text-slate-300">
                <EditIcon size={16} className="mr-2" />
                Custom Fields
              </Button>
              <Button variant="outline" size="sm" onClick={() => { loadLeads(); loadRetentionMetrics(); }} className="border-slate-600 text-slate-300">
                <RefreshCwIcon size={16} />
              </Button>
              <Button onClick={() => setShowAddModal(true)} className="bg-blue-600 hover:bg-blue-700" data-testid="add-lead-btn">
                <UserPlusIcon size={16} className="mr-2" />
                Add Lead
              </Button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Retention Metrics Overview */}
        {retentionMetrics && (
          <div className="grid grid-cols-5 gap-4 mb-6">
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
                  <TrendingUpIcon className="text-green-400" size={20} />
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
                  <TargetIcon className="text-amber-400" size={20} />
                </div>
                <div>
                  <p className="text-2xl font-bold text-white">{retentionMetrics.average_visits}</p>
                  <p className="text-xs text-slate-400">Avg Visits</p>
                </div>
              </CardContent>
            </Card>
            <Card className="bg-slate-900 border-slate-700">
              <CardContent className="p-4 flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-purple-500/20 flex items-center justify-center">
                  <DollarSignIcon className="text-purple-400" size={20} />
                </div>
                <div>
                  <p className="text-2xl font-bold text-white">{formatCurrency(retentionMetrics.average_ltv_cents)}</p>
                  <p className="text-xs text-slate-400">Avg LTV</p>
                </div>
              </CardContent>
            </Card>
            <Card className="bg-slate-900 border-slate-700">
              <CardContent className="p-4">
                <p className="text-xs text-slate-400 mb-2">Lifecycle Distribution</p>
                <div className="flex flex-wrap gap-1">
                  {Object.entries(retentionMetrics.by_lifecycle || {}).map(([stage, count]) => (
                    <Badge key={stage} className={`${LIFECYCLE_COLORS[stage] || 'bg-slate-500'} text-white text-xs`}>
                      {stage}: {count}
                    </Badge>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="bg-slate-800 border border-slate-700">
            <TabsTrigger value="leads" className="data-[state=active]:bg-blue-600">
              Lead Pipeline ({leads.filter(l => l.status !== 'converted').length})
            </TabsTrigger>
            <TabsTrigger value="converted" className="data-[state=active]:bg-green-600">
              Converted ({leads.filter(l => l.status === 'converted').length})
            </TabsTrigger>
          </TabsList>

          <TabsContent value="leads">
            {/* Filters */}
            <div className="flex items-center gap-4 mb-4">
              <div className="relative flex-1">
                <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
                <Input
                  placeholder="Search leads by name, email, or phone..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10 bg-slate-800 border-slate-700 text-white"
                />
              </div>
              <Select value={filterStatus} onValueChange={(v) => { setFilterStatus(v); }}>
                <SelectTrigger className="w-40 bg-slate-800 border-slate-700 text-white">
                  <SelectValue placeholder="All Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">All Status</SelectItem>
                  {LEAD_STATUS.filter(s => s.value !== 'converted').map(s => (
                    <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select value={filterSource} onValueChange={(v) => { setFilterSource(v); }}>
                <SelectTrigger className="w-40 bg-slate-800 border-slate-700 text-white">
                  <SelectValue placeholder="All Sources" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">All Sources</SelectItem>
                  {LEAD_SOURCES.map(s => (
                    <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button variant="outline" onClick={loadLeads} className="border-slate-600 text-slate-300">Apply</Button>
            </div>

            {/* Leads Kanban-style Grid */}
            <div className="grid grid-cols-4 gap-4">
              {LEAD_STATUS.filter(s => s.value !== 'converted').map(status => (
                <div key={status.value} className="space-y-3">
                  <div className="flex items-center gap-2 mb-2">
                    <div className={`w-3 h-3 rounded-full ${status.color}`}></div>
                    <h3 className="text-white font-medium">{status.label}</h3>
                    <Badge className="bg-slate-700 text-slate-300">
                      {filteredLeads.filter(l => l.status === status.value).length}
                    </Badge>
                  </div>
                  <div className="space-y-2 min-h-64">
                    {filteredLeads.filter(l => l.status === status.value).map(lead => (
                      <Card 
                        key={lead.id} 
                        className="bg-slate-800 border-slate-700 cursor-pointer hover:bg-slate-750 hover:border-blue-500/50 transition-all"
                        onClick={() => { setSelectedLead(lead); setShowDetailModal(true); }}
                        data-testid={`lead-card-${lead.id}`}
                      >
                        <CardContent className="p-3">
                          <div className="flex items-start justify-between mb-2">
                            <h4 className="text-white font-medium">{lead.name}</h4>
                            <Badge className="bg-slate-700 text-slate-300 text-xs capitalize">{lead.source}</Badge>
                          </div>
                          {lead.email && (
                            <p className="text-xs text-slate-400 flex items-center gap-1 mb-1">
                              <MailIcon size={12} /> {lead.email}
                            </p>
                          )}
                          {lead.phone && (
                            <p className="text-xs text-slate-400 flex items-center gap-1 mb-1">
                              <PhoneIcon size={12} /> {lead.phone}
                            </p>
                          )}
                          {lead.dog_info?.name && (
                            <p className="text-xs text-slate-400 flex items-center gap-1">
                              <DogIcon size={12} /> {lead.dog_info.name}
                            </p>
                          )}
                          <p className="text-xs text-slate-500 mt-2">
                            {formatDate(lead.created_at)}
                          </p>
                        </CardContent>
                      </Card>
                    ))}
                    {filteredLeads.filter(l => l.status === status.value).length === 0 && (
                      <div className="text-center py-8 text-slate-600 text-sm">
                        No leads
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </TabsContent>

          <TabsContent value="converted">
            {/* Converted Leads Table */}
            <Card className="bg-slate-900 border-slate-700">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-slate-700">
                      <th className="text-left p-4 text-slate-400 font-medium">Name</th>
                      <th className="text-left p-4 text-slate-400 font-medium">Contact</th>
                      <th className="text-left p-4 text-slate-400 font-medium">Source</th>
                      <th className="text-left p-4 text-slate-400 font-medium">Dog Info</th>
                      <th className="text-left p-4 text-slate-400 font-medium">Converted Date</th>
                      <th className="text-right p-4 text-slate-400 font-medium">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {leads.filter(l => l.status === 'converted').length === 0 ? (
                      <tr>
                        <td colSpan={6} className="p-8 text-center text-slate-500">
                          No converted leads yet
                        </td>
                      </tr>
                    ) : (
                      leads.filter(l => l.status === 'converted').map(lead => (
                        <tr key={lead.id} className="border-b border-slate-800 hover:bg-slate-800/50">
                          <td className="p-4">
                            <p className="text-white font-medium">{lead.name}</p>
                          </td>
                          <td className="p-4">
                            {lead.email && <p className="text-sm text-slate-300">{lead.email}</p>}
                            {lead.phone && <p className="text-sm text-slate-400">{lead.phone}</p>}
                          </td>
                          <td className="p-4">
                            <Badge className="bg-slate-700 text-slate-300 capitalize">{lead.source}</Badge>
                          </td>
                          <td className="p-4 text-slate-300">
                            {lead.dog_info?.name || '-'}
                          </td>
                          <td className="p-4 text-slate-400">
                            {formatDate(lead.converted_at)}
                          </td>
                          <td className="p-4 text-right">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => { setSelectedLead(lead); setShowDetailModal(true); }}
                              className="text-slate-400 hover:text-white"
                            >
                              View <ChevronRightIcon size={16} />
                            </Button>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </Card>
          </TabsContent>
        </Tabs>
      </main>

      {/* Add Lead Modal */}
      <Dialog open={showAddModal} onOpenChange={setShowAddModal}>
        <DialogContent className="bg-slate-900 border-slate-700 max-w-lg max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-white">Add New Lead</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            {/* Basic Info */}
            <div className="grid grid-cols-2 gap-4">
              <div className="col-span-2">
                <Label className="text-slate-300">Full Name *</Label>
                <Input
                  value={newLead.name}
                  onChange={(e) => setNewLead({ ...newLead, name: e.target.value })}
                  className="bg-slate-800 border-slate-700 text-white mt-1"
                  placeholder="John Doe"
                />
              </div>
              <div>
                <Label className="text-slate-300">Email</Label>
                <Input
                  type="email"
                  value={newLead.email}
                  onChange={(e) => setNewLead({ ...newLead, email: e.target.value })}
                  className="bg-slate-800 border-slate-700 text-white mt-1"
                  placeholder="john@example.com"
                />
              </div>
              <div>
                <Label className="text-slate-300">Phone</Label>
                <Input
                  value={newLead.phone}
                  onChange={(e) => setNewLead({ ...newLead, phone: e.target.value })}
                  className="bg-slate-800 border-slate-700 text-white mt-1"
                  placeholder="(555) 123-4567"
                />
              </div>
              <div className="col-span-2">
                <Label className="text-slate-300">Lead Source</Label>
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
            </div>

            {/* Pet Info Section */}
            <div className="border-t border-slate-700 pt-4">
              <h4 className="text-white font-medium mb-3 flex items-center gap-2">
                <DogIcon size={16} /> Pet Information
              </h4>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="text-slate-300">Dog Name</Label>
                  <Input
                    value={newLead.dog_info.dog_name}
                    onChange={(e) => setNewLead({ ...newLead, dog_info: { ...newLead.dog_info, dog_name: e.target.value } })}
                    className="bg-slate-800 border-slate-700 text-white mt-1"
                    placeholder="Max"
                  />
                </div>
                <div>
                  <Label className="text-slate-300">Breed</Label>
                  <Input
                    value={newLead.dog_info.breed}
                    onChange={(e) => setNewLead({ ...newLead, dog_info: { ...newLead.dog_info, breed: e.target.value } })}
                    className="bg-slate-800 border-slate-700 text-white mt-1"
                    placeholder="Golden Retriever"
                  />
                </div>
                <div>
                  <Label className="text-slate-300">Age</Label>
                  <Input
                    value={newLead.dog_info.age}
                    onChange={(e) => setNewLead({ ...newLead, dog_info: { ...newLead.dog_info, age: e.target.value } })}
                    className="bg-slate-800 border-slate-700 text-white mt-1"
                    placeholder="3 years"
                  />
                </div>
                <div>
                  <Label className="text-slate-300">Pet Notes</Label>
                  <Input
                    value={newLead.dog_info.notes}
                    onChange={(e) => setNewLead({ ...newLead, dog_info: { ...newLead.dog_info, notes: e.target.value } })}
                    className="bg-slate-800 border-slate-700 text-white mt-1"
                    placeholder="Allergies, special needs..."
                  />
                </div>
              </div>
            </div>

            {/* Custom Fields (Admin Expandable) */}
            {customFields.length > 0 && (
              <div className="border-t border-slate-700 pt-4">
                <h4 className="text-white font-medium mb-3">Additional Information</h4>
                <div className="grid grid-cols-2 gap-4">
                  {customFields.map(field => (
                    <div key={field.id}>
                      <Label className="text-slate-300">{field.label}</Label>
                      {field.type === 'select' ? (
                        <Select 
                          value={newLead.custom_fields[field.id] || ''} 
                          onValueChange={(v) => setNewLead({ ...newLead, custom_fields: { ...newLead.custom_fields, [field.id]: v } })}
                        >
                          <SelectTrigger className="bg-slate-800 border-slate-700 text-white mt-1">
                            <SelectValue placeholder="Select..." />
                          </SelectTrigger>
                          <SelectContent>
                            {field.options?.map(opt => (
                              <SelectItem key={opt} value={opt}>{opt}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      ) : field.type === 'date' ? (
                        <Input
                          type="date"
                          value={newLead.custom_fields[field.id] || ''}
                          onChange={(e) => setNewLead({ ...newLead, custom_fields: { ...newLead.custom_fields, [field.id]: e.target.value } })}
                          className="bg-slate-800 border-slate-700 text-white mt-1"
                        />
                      ) : (
                        <Input
                          value={newLead.custom_fields[field.id] || ''}
                          onChange={(e) => setNewLead({ ...newLead, custom_fields: { ...newLead.custom_fields, [field.id]: e.target.value } })}
                          className="bg-slate-800 border-slate-700 text-white mt-1"
                        />
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Notes */}
            <div>
              <Label className="text-slate-300">Notes</Label>
              <Textarea
                value={newLead.notes}
                onChange={(e) => setNewLead({ ...newLead, notes: e.target.value })}
                className="bg-slate-800 border-slate-700 text-white mt-1"
                placeholder="Additional notes about this lead..."
                rows={3}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => { setShowAddModal(false); resetNewLead(); }} className="border-slate-600 text-slate-300">Cancel</Button>
            <Button onClick={handleAddLead} className="bg-blue-600 hover:bg-blue-700" data-testid="submit-lead-btn">Add Lead</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Lead Detail Modal */}
      <Dialog open={showDetailModal} onOpenChange={setShowDetailModal}>
        <DialogContent className="bg-slate-900 border-slate-700 max-w-lg">
          <DialogHeader>
            <DialogTitle className="text-white">Lead Details</DialogTitle>
          </DialogHeader>
          {selectedLead && (
            <div className="space-y-4 py-4">
              <div className="bg-slate-800 rounded-lg p-4">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-xl font-bold text-white">{selectedLead.name}</h3>
                  <Badge className={`${LEAD_STATUS.find(s => s.value === selectedLead.status)?.color || 'bg-slate-500'} text-white capitalize`}>
                    {selectedLead.status}
                  </Badge>
                </div>
                <div className="space-y-2 text-sm">
                  {selectedLead.email && (
                    <p className="text-slate-300 flex items-center gap-2">
                      <MailIcon size={14} /> {selectedLead.email}
                    </p>
                  )}
                  {selectedLead.phone && (
                    <p className="text-slate-300 flex items-center gap-2">
                      <PhoneIcon size={14} /> {selectedLead.phone}
                    </p>
                  )}
                  <p className="text-slate-400 flex items-center gap-2">
                    <CalendarIcon size={14} /> Added: {formatDate(selectedLead.created_at)}
                  </p>
                  <p className="text-slate-400">
                    Source: <span className="capitalize">{selectedLead.source}</span>
                  </p>
                </div>
              </div>

              {selectedLead.dog_info?.name && (
                <div className="bg-slate-800 rounded-lg p-4">
                  <h4 className="text-white font-medium mb-2 flex items-center gap-2">
                    <DogIcon size={16} /> Pet Information
                  </h4>
                  <div className="text-sm text-slate-300 space-y-1">
                    <p>Name: {selectedLead.dog_info.name}</p>
                    {selectedLead.dog_info.breed && <p>Breed: {selectedLead.dog_info.breed}</p>}
                    {selectedLead.dog_info.age && <p>Age: {selectedLead.dog_info.age}</p>}
                    {selectedLead.dog_info.notes && <p>Notes: {selectedLead.dog_info.notes}</p>}
                  </div>
                </div>
              )}

              {selectedLead.notes && (
                <div className="bg-slate-800 rounded-lg p-4">
                  <h4 className="text-white font-medium mb-2">Notes</h4>
                  <p className="text-sm text-slate-300">{selectedLead.notes}</p>
                </div>
              )}

              {/* Status Actions */}
              {selectedLead.status !== 'converted' && (
                <div className="border-t border-slate-700 pt-4">
                  <Label className="text-slate-300 mb-2 block">Update Status</Label>
                  <div className="flex flex-wrap gap-2">
                    {LEAD_STATUS.filter(s => s.value !== selectedLead.status && s.value !== 'converted').map(status => (
                      <Button
                        key={status.value}
                        variant="outline"
                        size="sm"
                        onClick={() => handleUpdateStatus(selectedLead.id, status.value)}
                        className="border-slate-600 text-slate-300"
                      >
                        {status.label}
                      </Button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
          <DialogFooter>
            {selectedLead?.status !== 'converted' && selectedLead?.status !== 'lost' && (
              <Button
                onClick={() => handleConvertLead(selectedLead.id)}
                className="bg-green-600 hover:bg-green-700"
                data-testid="convert-lead-btn"
              >
                <CheckCircleIcon size={16} className="mr-2" />
                Convert to Customer
              </Button>
            )}
            <Button variant="outline" onClick={() => setShowDetailModal(false)} className="border-slate-600 text-slate-300">Close</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Custom Fields Manager Modal */}
      <Dialog open={showFieldManager} onOpenChange={setShowFieldManager}>
        <DialogContent className="bg-slate-900 border-slate-700 max-w-md">
          <DialogHeader>
            <DialogTitle className="text-white">Manage Custom Fields</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <p className="text-sm text-slate-400">Add or remove custom fields to collect additional lead information.</p>
            
            {/* Existing Fields */}
            <div className="space-y-2">
              {customFields.map(field => (
                <div key={field.id} className="flex items-center justify-between bg-slate-800 rounded-lg p-3">
                  <div>
                    <p className="text-white text-sm">{field.label}</p>
                    <p className="text-xs text-slate-500 capitalize">{field.type}</p>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => removeCustomField(field.id)}
                    className="text-red-400 hover:text-red-300"
                  >
                    <XCircleIcon size={16} />
                  </Button>
                </div>
              ))}
            </div>

            {/* Add New Field */}
            <div className="border-t border-slate-700 pt-4">
              <h4 className="text-white font-medium mb-3">Add New Field</h4>
              <div className="space-y-3">
                <div>
                  <Label className="text-slate-300">Field Name</Label>
                  <Input
                    value={newFieldName}
                    onChange={(e) => setNewFieldName(e.target.value)}
                    className="bg-slate-800 border-slate-700 text-white mt-1"
                    placeholder="e.g., Preferred Appointment Time"
                  />
                </div>
                <div>
                  <Label className="text-slate-300">Field Type</Label>
                  <Select value={newFieldType} onValueChange={setNewFieldType}>
                    <SelectTrigger className="bg-slate-800 border-slate-700 text-white mt-1">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="text">Text</SelectItem>
                      <SelectItem value="date">Date</SelectItem>
                      <SelectItem value="select">Dropdown</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <Button onClick={addCustomField} className="w-full bg-blue-600 hover:bg-blue-700">
                  <PlusIcon size={16} className="mr-2" /> Add Field
                </Button>
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowFieldManager(false)} className="border-slate-600 text-slate-300">Done</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
