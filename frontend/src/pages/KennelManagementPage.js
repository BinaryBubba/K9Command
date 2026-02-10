import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { Switch } from '../components/ui/switch';
import { toast } from 'sonner';
import { 
  PlusIcon, 
  HomeIcon,
  DogIcon,
  EditIcon,
  TrashIcon,
  ArrowLeftIcon,
  FilterIcon,
  MapPinIcon,
  ThermometerIcon,
  VideoIcon,
  SunIcon
} from 'lucide-react';
import api from '../utils/api';

const KENNEL_TYPES = [
  { value: 'run', label: 'Run', color: 'bg-green-500' },
  { value: 'suite', label: 'Suite', color: 'bg-purple-500' },
  { value: 'crate', label: 'Crate', color: 'bg-blue-500' },
  { value: 'luxury', label: 'Luxury', color: 'bg-amber-500' },
];

const SIZE_CATEGORIES = [
  { value: 'small', label: 'Small (0-25 lbs)' },
  { value: 'medium', label: 'Medium (26-50 lbs)' },
  { value: 'large', label: 'Large (51-100 lbs)' },
  { value: 'xlarge', label: 'X-Large (100+ lbs)' },
];

const FEATURES = [
  { value: 'outdoor_access', label: 'Outdoor Access', icon: SunIcon },
  { value: 'webcam', label: 'Webcam', icon: VideoIcon },
  { value: 'climate_control', label: 'Climate Control', icon: ThermometerIcon },
  { value: 'raised_bed', label: 'Raised Bed', icon: HomeIcon },
];

const STATUS_COLORS = {
  available: 'bg-green-500/20 text-green-400 border-green-500/30',
  occupied: 'bg-red-500/20 text-red-400 border-red-500/30',
  reserved: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
  cleaning: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  maintenance: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
  out_of_service: 'bg-slate-500/20 text-slate-400 border-slate-500/30',
};

export default function KennelManagementPage() {
  const navigate = useNavigate();
  const [kennels, setKennels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [typeFilter, setTypeFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingKennel, setEditingKennel] = useState(null);
  
  // Form state
  const [formData, setFormData] = useState({
    name: '',
    kennel_type: 'run',
    size_category: 'medium',
    max_dogs: 1,
    features: [],
    price_modifier: 0,
    min_weight: '',
    max_weight: '',
    notes: '',
  });

  useEffect(() => {
    loadKennels();
  }, []);

  const loadKennels = async () => {
    setLoading(true);
    try {
      const response = await api.get('/moego/kennels');
      setKennels(response.data);
    } catch (error) {
      toast.error('Failed to load kennels');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateKennel = async () => {
    if (!formData.name.trim()) {
      toast.error('Please enter a kennel name');
      return;
    }

    try {
      const payload = {
        ...formData,
        location_id: 'main',
        min_weight: formData.min_weight ? parseFloat(formData.min_weight) : null,
        max_weight: formData.max_weight ? parseFloat(formData.max_weight) : null,
        price_modifier: parseFloat(formData.price_modifier) || 0,
      };

      if (editingKennel) {
        await api.patch(`/moego/kennels/${editingKennel.id}`, payload);
        toast.success('Kennel updated');
      } else {
        await api.post('/moego/kennels', payload);
        toast.success('Kennel created');
      }
      
      setShowCreateModal(false);
      setEditingKennel(null);
      resetForm();
      loadKennels();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save kennel');
    }
  };

  const handleDeleteKennel = async (kennelId) => {
    if (!window.confirm('Are you sure you want to deactivate this kennel?')) return;
    
    try {
      await api.delete(`/moego/kennels/${kennelId}`);
      toast.success('Kennel deactivated');
      loadKennels();
    } catch (error) {
      toast.error('Failed to delete kennel');
    }
  };

  const handleEditKennel = (kennel) => {
    setEditingKennel(kennel);
    setFormData({
      name: kennel.name,
      kennel_type: kennel.kennel_type,
      size_category: kennel.size_category,
      max_dogs: kennel.max_dogs,
      features: kennel.features || [],
      price_modifier: kennel.price_modifier || 0,
      min_weight: kennel.min_weight || '',
      max_weight: kennel.max_weight || '',
      notes: kennel.notes || '',
    });
    setShowCreateModal(true);
  };

  const resetForm = () => {
    setFormData({
      name: '',
      kennel_type: 'run',
      size_category: 'medium',
      max_dogs: 1,
      features: [],
      price_modifier: 0,
      min_weight: '',
      max_weight: '',
      notes: '',
    });
  };

  const toggleFeature = (feature) => {
    setFormData(prev => ({
      ...prev,
      features: prev.features.includes(feature)
        ? prev.features.filter(f => f !== feature)
        : [...prev.features, feature]
    }));
  };

  const filteredKennels = kennels.filter(k => {
    if (typeFilter !== 'all' && k.kennel_type !== typeFilter) return false;
    if (statusFilter !== 'all' && k.status !== statusFilter) return false;
    return true;
  });

  const getTypeColor = (type) => {
    return KENNEL_TYPES.find(t => t.value === type)?.color || 'bg-slate-500';
  };

  // Group kennels by type for visual display
  const groupedKennels = KENNEL_TYPES.map(type => ({
    ...type,
    kennels: filteredKennels.filter(k => k.kennel_type === type.value)
  })).filter(g => g.kennels.length > 0);

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="animate-spin h-8 w-8 border-2 border-blue-500 border-t-transparent rounded-full"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950" data-testid="kennel-management-page">
      {/* Header */}
      <header className="bg-slate-900 border-b border-slate-700 px-6 py-4">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => navigate('/admin')}
                className="text-slate-400 hover:text-white"
              >
                <ArrowLeftIcon size={20} />
              </Button>
              <div>
                <h1 className="text-2xl font-bold text-white">Kennel Management</h1>
                <p className="text-slate-400 text-sm">Manage runs, suites, and crates</p>
              </div>
            </div>
            <Button
              onClick={() => { resetForm(); setShowCreateModal(true); }}
              className="bg-blue-600 hover:bg-blue-700 text-white"
              data-testid="add-kennel-btn"
            >
              <PlusIcon size={18} className="mr-2" />
              Add Kennel
            </Button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-8">
          <Card className="bg-slate-900 border-slate-700">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-blue-500/20 flex items-center justify-center">
                  <HomeIcon className="text-blue-400" size={20} />
                </div>
                <div>
                  <p className="text-slate-400 text-sm">Total</p>
                  <p className="text-2xl font-bold text-white">{kennels.length}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {KENNEL_TYPES.map(type => (
            <Card key={type.value} className="bg-slate-900 border-slate-700">
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className={`w-10 h-10 rounded-lg ${type.color}/20 flex items-center justify-center`}>
                    <HomeIcon className={`${type.color.replace('bg-', 'text-').replace('-500', '-400')}`} size={20} />
                  </div>
                  <div>
                    <p className="text-slate-400 text-sm">{type.label}s</p>
                    <p className="text-2xl font-bold text-white">
                      {kennels.filter(k => k.kennel_type === type.value).length}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Filters */}
        <div className="flex items-center gap-3 mb-6">
          <Select value={typeFilter} onValueChange={setTypeFilter}>
            <SelectTrigger className="w-40 bg-slate-800 border-slate-700 text-white">
              <FilterIcon size={14} className="mr-2" />
              <SelectValue placeholder="Type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Types</SelectItem>
              {KENNEL_TYPES.map(t => (
                <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-40 bg-slate-800 border-slate-700 text-white">
              <FilterIcon size={14} className="mr-2" />
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Status</SelectItem>
              <SelectItem value="available">Available</SelectItem>
              <SelectItem value="occupied">Occupied</SelectItem>
              <SelectItem value="reserved">Reserved</SelectItem>
              <SelectItem value="cleaning">Cleaning</SelectItem>
              <SelectItem value="maintenance">Maintenance</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Kennel Grid - Grouped by Type */}
        {groupedKennels.length === 0 ? (
          <Card className="bg-slate-900 border-slate-700">
            <CardContent className="py-12 text-center">
              <HomeIcon className="mx-auto text-slate-600 mb-4" size={48} />
              <h3 className="text-lg font-semibold text-slate-400 mb-2">No kennels found</h3>
              <p className="text-slate-500 mb-4">Add your first kennel to get started</p>
              <Button onClick={() => setShowCreateModal(true)} className="bg-blue-600 hover:bg-blue-700">
                <PlusIcon size={16} className="mr-2" />
                Add Kennel
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-8">
            {groupedKennels.map(group => (
              <div key={group.value}>
                <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                  <div className={`w-3 h-3 rounded-full ${group.color}`}></div>
                  {group.label}s ({group.kennels.length})
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                  {group.kennels.map(kennel => (
                    <Card 
                      key={kennel.id}
                      className="bg-slate-900 border-slate-700 hover:border-slate-600 transition-colors"
                      data-testid={`kennel-card-${kennel.id}`}
                    >
                      <CardContent className="p-4">
                        <div className="flex items-start justify-between mb-3">
                          <div>
                            <h3 className="font-semibold text-white">{kennel.name}</h3>
                            <p className="text-slate-400 text-sm capitalize">{kennel.size_category}</p>
                          </div>
                          <Badge className={STATUS_COLORS[kennel.status]}>
                            {kennel.status}
                          </Badge>
                        </div>

                        <div className="flex items-center gap-2 mb-3 text-slate-400 text-sm">
                          <DogIcon size={14} />
                          <span>Max {kennel.max_dogs} dog{kennel.max_dogs > 1 ? 's' : ''}</span>
                          {kennel.price_modifier > 0 && (
                            <span className="text-green-400">+${kennel.price_modifier}</span>
                          )}
                        </div>

                        {kennel.features?.length > 0 && (
                          <div className="flex flex-wrap gap-1 mb-3">
                            {kennel.features.map(f => (
                              <Badge key={f} variant="outline" className="text-xs border-slate-600 text-slate-400">
                                {f.replace('_', ' ')}
                              </Badge>
                            ))}
                          </div>
                        )}

                        {kennel.current_dog_ids?.length > 0 && (
                          <div className="bg-slate-800 rounded-lg p-2 mb-3">
                            <p className="text-xs text-slate-400">
                              Currently occupied by {kennel.current_dog_ids.length} dog(s)
                            </p>
                          </div>
                        )}

                        <div className="flex gap-2">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleEditKennel(kennel)}
                            className="flex-1 border-slate-600 text-slate-300"
                          >
                            <EditIcon size={14} className="mr-1" />
                            Edit
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleDeleteKennel(kennel.id)}
                            className="text-slate-400 hover:text-red-400"
                          >
                            <TrashIcon size={14} />
                          </Button>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </main>

      {/* Create/Edit Modal */}
      <Dialog open={showCreateModal} onOpenChange={(open) => { setShowCreateModal(open); if (!open) setEditingKennel(null); }}>
        <DialogContent className="bg-slate-900 border-slate-700 max-w-lg">
          <DialogHeader>
            <DialogTitle className="text-white">
              {editingKennel ? 'Edit Kennel' : 'Add New Kennel'}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <Label className="text-slate-300">Name</Label>
              <Input
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="e.g., Run A1, Suite 3"
                className="mt-1 bg-slate-800 border-slate-600 text-white"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label className="text-slate-300">Type</Label>
                <Select value={formData.kennel_type} onValueChange={(v) => setFormData({ ...formData, kennel_type: v })}>
                  <SelectTrigger className="mt-1 bg-slate-800 border-slate-600 text-white">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {KENNEL_TYPES.map(t => (
                      <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label className="text-slate-300">Size Category</Label>
                <Select value={formData.size_category} onValueChange={(v) => setFormData({ ...formData, size_category: v })}>
                  <SelectTrigger className="mt-1 bg-slate-800 border-slate-600 text-white">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {SIZE_CATEGORIES.map(s => (
                      <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label className="text-slate-300">Max Dogs</Label>
                <Input
                  type="number"
                  min={1}
                  max={4}
                  value={formData.max_dogs}
                  onChange={(e) => setFormData({ ...formData, max_dogs: parseInt(e.target.value) || 1 })}
                  className="mt-1 bg-slate-800 border-slate-600 text-white"
                />
              </div>

              <div>
                <Label className="text-slate-300">Price Modifier ($)</Label>
                <Input
                  type="number"
                  value={formData.price_modifier}
                  onChange={(e) => setFormData({ ...formData, price_modifier: parseFloat(e.target.value) || 0 })}
                  className="mt-1 bg-slate-800 border-slate-600 text-white"
                  placeholder="0"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label className="text-slate-300">Min Weight (lbs)</Label>
                <Input
                  type="number"
                  value={formData.min_weight}
                  onChange={(e) => setFormData({ ...formData, min_weight: e.target.value })}
                  className="mt-1 bg-slate-800 border-slate-600 text-white"
                  placeholder="Optional"
                />
              </div>

              <div>
                <Label className="text-slate-300">Max Weight (lbs)</Label>
                <Input
                  type="number"
                  value={formData.max_weight}
                  onChange={(e) => setFormData({ ...formData, max_weight: e.target.value })}
                  className="mt-1 bg-slate-800 border-slate-600 text-white"
                  placeholder="Optional"
                />
              </div>
            </div>

            <div>
              <Label className="text-slate-300 mb-2 block">Features</Label>
              <div className="grid grid-cols-2 gap-2">
                {FEATURES.map(feature => (
                  <label
                    key={feature.value}
                    className={`flex items-center gap-2 p-2 rounded-lg border cursor-pointer transition-colors ${
                      formData.features.includes(feature.value)
                        ? 'border-blue-500 bg-blue-500/10'
                        : 'border-slate-600 hover:border-slate-500'
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={formData.features.includes(feature.value)}
                      onChange={() => toggleFeature(feature.value)}
                      className="sr-only"
                    />
                    <feature.icon size={16} className={formData.features.includes(feature.value) ? 'text-blue-400' : 'text-slate-400'} />
                    <span className={formData.features.includes(feature.value) ? 'text-white' : 'text-slate-400'}>
                      {feature.label}
                    </span>
                  </label>
                ))}
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCreateModal(false)} className="border-slate-600 text-slate-300">
              Cancel
            </Button>
            <Button onClick={handleCreateKennel} className="bg-blue-600 hover:bg-blue-700">
              {editingKennel ? 'Update' : 'Create'} Kennel
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
