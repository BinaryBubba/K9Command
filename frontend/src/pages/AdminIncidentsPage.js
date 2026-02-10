import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { ArrowLeftIcon, AlertTriangleIcon, PlusIcon, EditIcon, TrashIcon, SearchIcon, CheckIcon } from 'lucide-react';
import { toast } from 'sonner';
import api from '../utils/api';
import useAuthStore from '../store/authStore';

const AdminIncidentsPage = () => {
  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);
  const [incidents, setIncidents] = useState([]);
  const [dogs, setDogs] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editMode, setEditMode] = useState(false);
  const [selectedIncident, setSelectedIncident] = useState(null);
  const [formData, setFormData] = useState({
    description: '',
    severity: 'low',
    dog_ids: [],
    status: 'open',
    resolution: '',
  });

  useEffect(() => {
    if (!user || user.role !== 'admin') {
      navigate('/auth');
      return;
    }
    fetchData();
  }, [user, navigate]);

  const fetchData = async () => {
    try {
      const [incidentsRes, dogsRes] = await Promise.all([
        api.get('/incidents'),
        api.get('/dogs'),
      ]);
      setIncidents(incidentsRes.data);
      setDogs(dogsRes.data);
    } catch (error) {
      toast.error('Failed to load incidents');
    } finally {
      setLoading(false);
    }
  };

  const openCreateModal = () => {
    setEditMode(false);
    setSelectedIncident(null);
    setFormData({ description: '', severity: 'low', dog_ids: [], status: 'open', resolution: '' });
    setModalOpen(true);
  };

  const openEditModal = (incident) => {
    setEditMode(true);
    setSelectedIncident(incident);
    setFormData({
      description: incident.description || '',
      severity: incident.severity || 'low',
      dog_ids: incident.dog_ids || [],
      status: incident.status || 'open',
      resolution: incident.resolution || '',
    });
    setModalOpen(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editMode) {
        await api.patch(`/incidents/${selectedIncident.id}`, formData);
        toast.success('Incident updated');
      } else {
        await api.post('/incidents', formData);
        toast.success('Incident reported');
      }
      setModalOpen(false);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save incident');
    }
  };

  const handleDelete = async (incidentId) => {
    if (!window.confirm('Are you sure you want to delete this incident?')) return;
    try {
      await api.delete(`/incidents/${incidentId}`);
      toast.success('Incident deleted');
      fetchData();
    } catch (error) {
      toast.error('Failed to delete incident');
    }
  };

  const handleResolve = async (incidentId) => {
    const resolution = window.prompt('Enter resolution notes:');
    if (!resolution) return;
    try {
      await api.patch(`/incidents/${incidentId}`, { status: 'resolved', resolution });
      toast.success('Incident resolved');
      fetchData();
    } catch (error) {
      toast.error('Failed to resolve incident');
    }
  };

  const getSeverityColor = (severity) => {
    const colors = {
      low: 'bg-green-100 text-green-800',
      medium: 'bg-yellow-100 text-yellow-800',
      high: 'bg-orange-100 text-orange-800',
      critical: 'bg-red-100 text-red-800',
    };
    return colors[severity] || 'bg-gray-100 text-gray-800';
  };

  const getStatusColor = (status) => {
    const colors = {
      open: 'bg-red-100 text-red-800',
      investigating: 'bg-yellow-100 text-yellow-800',
      resolved: 'bg-green-100 text-green-800',
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
  };

  const getDogName = (dogId) => {
    const dog = dogs.find(d => d.id === dogId);
    return dog?.name || 'Unknown';
  };

  let filteredIncidents = incidents;
  if (searchQuery) {
    filteredIncidents = filteredIncidents.filter(i => 
      i.description?.toLowerCase().includes(searchQuery.toLowerCase())
    );
  }
  if (statusFilter !== 'all') {
    filteredIncidents = filteredIncidents.filter(i => i.status === statusFilter);
  }

  const openIncidents = incidents.filter(i => i.status === 'open').length;
  const criticalIncidents = incidents.filter(i => i.severity === 'critical').length;

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
          <Button variant="ghost" onClick={() => navigate('/admin/dashboard')} className="flex items-center gap-2 mb-2">
            <ArrowLeftIcon size={18} /> Back to Dashboard
          </Button>
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-serif font-bold text-primary">Incident Reports</h1>
              <p className="text-muted-foreground mt-1">Track and manage all incidents</p>
            </div>
            <Button onClick={openCreateModal} className="rounded-full">
              <PlusIcon size={18} className="mr-2" /> Report Incident
            </Button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 md:px-8 py-8">
        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
            <CardContent className="p-6">
              <p className="text-sm text-muted-foreground mb-1">Total Incidents</p>
              <p className="text-3xl font-serif font-bold text-primary">{incidents.length}</p>
            </CardContent>
          </Card>
          <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
            <CardContent className="p-6">
              <p className="text-sm text-muted-foreground mb-1">Open</p>
              <p className="text-3xl font-serif font-bold text-red-600">{openIncidents}</p>
            </CardContent>
          </Card>
          <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
            <CardContent className="p-6">
              <p className="text-sm text-muted-foreground mb-1">Critical</p>
              <p className="text-3xl font-serif font-bold text-orange-600">{criticalIncidents}</p>
            </CardContent>
          </Card>
          <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
            <CardContent className="p-6">
              <p className="text-sm text-muted-foreground mb-1">Resolved</p>
              <p className="text-3xl font-serif font-bold text-green-600">{incidents.filter(i => i.status === 'resolved').length}</p>
            </CardContent>
          </Card>
        </div>

        {/* Filters */}
        <Card className="mb-6 bg-white rounded-2xl border border-border/50 shadow-sm">
          <CardContent className="p-6">
            <div className="flex flex-col md:flex-row gap-4">
              <div className="flex-1 relative">
                <SearchIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground" size={20} />
                <Input placeholder="Search incidents..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} className="pl-10" />
              </div>
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="w-[150px]"><SelectValue placeholder="Filter status" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Status</SelectItem>
                  <SelectItem value="open">Open</SelectItem>
                  <SelectItem value="investigating">Investigating</SelectItem>
                  <SelectItem value="resolved">Resolved</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        {/* Incidents List */}
        <div className="space-y-4">
          {filteredIncidents.length === 0 ? (
            <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
              <CardContent className="p-12 text-center">
                <AlertTriangleIcon size={48} className="mx-auto text-muted-foreground/50 mb-4" />
                <p className="text-muted-foreground">No incidents found</p>
              </CardContent>
            </Card>
          ) : (
            filteredIncidents.map((incident) => (
              <Card key={incident.id} className={`rounded-2xl border shadow-sm ${incident.status === 'open' ? 'border-red-200 bg-red-50/30' : 'bg-white border-border/50'}`}>
                <CardContent className="p-6">
                  <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <AlertTriangleIcon className={incident.severity === 'critical' ? 'text-red-600' : 'text-orange-500'} size={20} />
                        <h3 className="text-lg font-semibold">Incident #{incident.id.slice(0, 8)}</h3>
                        <Badge className={getSeverityColor(incident.severity)}>{incident.severity}</Badge>
                        <Badge className={getStatusColor(incident.status)}>{incident.status}</Badge>
                      </div>
                      <p className="text-muted-foreground mb-2">{incident.description}</p>
                      
                      {incident.dog_ids?.length > 0 && (
                        <p className="text-sm">
                          <span className="font-medium">Dogs involved:</span>{' '}
                          {incident.dog_ids.map(getDogName).join(', ')}
                        </p>
                      )}
                      
                      {incident.resolution && (
                        <p className="text-sm text-green-600 mt-2">
                          <span className="font-medium">Resolution:</span> {incident.resolution}
                        </p>
                      )}
                      
                      <p className="text-xs text-muted-foreground mt-2">
                        Reported: {new Date(incident.created_at).toLocaleString()}
                      </p>
                    </div>
                    
                    <div className="flex gap-2">
                      {incident.status !== 'resolved' && (
                        <Button size="sm" onClick={() => handleResolve(incident.id)} className="bg-green-600 hover:bg-green-700">
                          <CheckIcon size={14} className="mr-1" /> Resolve
                        </Button>
                      )}
                      <Button variant="outline" size="sm" onClick={() => openEditModal(incident)}>
                        <EditIcon size={14} />
                      </Button>
                      <Button variant="destructive" size="sm" onClick={() => handleDelete(incident.id)}>
                        <TrashIcon size={14} />
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))
          )}
        </div>
      </main>

      {/* Create/Edit Modal */}
      <Dialog open={modalOpen} onOpenChange={setModalOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>{editMode ? 'Edit Incident' : 'Report New Incident'}</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <Label>Description *</Label>
              <textarea
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                className="w-full p-2 border rounded-lg"
                rows={3}
                placeholder="Describe the incident in detail..."
                required
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Severity</Label>
                <Select value={formData.severity} onValueChange={(v) => setFormData({ ...formData, severity: v })}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="low">Low</SelectItem>
                    <SelectItem value="medium">Medium</SelectItem>
                    <SelectItem value="high">High</SelectItem>
                    <SelectItem value="critical">Critical</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Status</Label>
                <Select value={formData.status} onValueChange={(v) => setFormData({ ...formData, status: v })}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="open">Open</SelectItem>
                    <SelectItem value="investigating">Investigating</SelectItem>
                    <SelectItem value="resolved">Resolved</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div>
              <Label>Dogs Involved</Label>
              <Select
                value={formData.dog_ids[0] || 'none'}
                onValueChange={(v) => setFormData({ ...formData, dog_ids: v && v !== 'none' ? [v] : [] })}
              >
                <SelectTrigger><SelectValue placeholder="Select dog (optional)" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">None</SelectItem>
                  {dogs.map((dog) => (
                    <SelectItem key={dog.id} value={dog.id}>{dog.name} - {dog.breed}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            {formData.status === 'resolved' && (
              <div>
                <Label>Resolution</Label>
                <textarea
                  value={formData.resolution}
                  onChange={(e) => setFormData({ ...formData, resolution: e.target.value })}
                  className="w-full p-2 border rounded-lg"
                  rows={2}
                  placeholder="How was this resolved?"
                />
              </div>
            )}
            <div className="flex gap-3 pt-4">
              <Button type="button" variant="outline" onClick={() => setModalOpen(false)} className="flex-1">Cancel</Button>
              <Button type="submit" className="flex-1">{editMode ? 'Update' : 'Report'}</Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default AdminIncidentsPage;
