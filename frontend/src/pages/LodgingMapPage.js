import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { toast } from 'sonner';
import { 
  HomeIcon,
  DogIcon,
  ArrowLeftIcon,
  RefreshCwIcon,
  CalendarIcon,
  PhoneIcon,
  ClockIcon,
  AlertTriangleIcon,
  CheckCircleIcon,
  XCircleIcon,
  ShowerHeadIcon,
  PillIcon,
  UtensilsIcon
} from 'lucide-react';
import api from '../utils/api';

const STATUS_COLORS = {
  available: { bg: 'bg-green-500/20', border: 'border-green-500', text: 'text-green-400', label: 'Available' },
  occupied: { bg: 'bg-red-500/20', border: 'border-red-500', text: 'text-red-400', label: 'Occupied' },
  reserved: { bg: 'bg-amber-500/20', border: 'border-amber-500', text: 'text-amber-400', label: 'Reserved' },
  cleaning: { bg: 'bg-blue-500/20', border: 'border-blue-500', text: 'text-blue-400', label: 'Cleaning' },
  maintenance: { bg: 'bg-orange-500/20', border: 'border-orange-500', text: 'text-orange-400', label: 'Maintenance' },
  out_of_service: { bg: 'bg-slate-500/20', border: 'border-slate-500', text: 'text-slate-400', label: 'Out of Service' },
};

const TYPE_COLORS = {
  run: 'border-l-green-500',
  suite: 'border-l-purple-500',
  crate: 'border-l-blue-500',
  luxury: 'border-l-amber-500',
};

export default function LodgingMapPage() {
  const navigate = useNavigate();
  const [kennels, setKennels] = useState([]);
  const [dogsOnSite, setDogsOnSite] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);
  const [selectedKennel, setSelectedKennel] = useState(null);
  const [showKennelModal, setShowKennelModal] = useState(false);
  const [typeFilter, setTypeFilter] = useState('all');

  useEffect(() => {
    loadData();
  }, [selectedDate]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [kennelsRes, dogsRes] = await Promise.all([
        api.get('/moego/kennels'),
        api.get(`/moego/operations/dogs-on-site?location_id=main&date=${selectedDate}`)
      ]);
      
      // Map dogs to kennels
      const kennelDogMap = {};
      for (const dog of dogsRes.data) {
        if (dog.kennel_id) {
          if (!kennelDogMap[dog.kennel_id]) {
            kennelDogMap[dog.kennel_id] = [];
          }
          kennelDogMap[dog.kennel_id].push(dog);
        }
      }
      
      // Update kennel status based on dogs
      const updatedKennels = kennelsRes.data.map(kennel => ({
        ...kennel,
        current_dogs: kennelDogMap[kennel.id] || [],
        computed_status: kennelDogMap[kennel.id]?.length > 0 ? 'occupied' : kennel.status
      }));
      
      setKennels(updatedKennels);
      setDogsOnSite(dogsRes.data);
    } catch (error) {
      console.error('Failed to load data:', error);
      toast.error('Failed to load lodging data');
    } finally {
      setLoading(false);
    }
  };

  const handleKennelClick = (kennel) => {
    setSelectedKennel(kennel);
    setShowKennelModal(true);
  };

  const handleStatusChange = async (kennelId, newStatus) => {
    try {
      await api.patch(`/moego/kennels/${kennelId}`, { status: newStatus });
      toast.success('Kennel status updated');
      loadData();
      setShowKennelModal(false);
    } catch (error) {
      toast.error('Failed to update status');
    }
  };

  const filteredKennels = kennels.filter(k => 
    typeFilter === 'all' || k.kennel_type === typeFilter
  );

  // Group by type for display
  const groupedKennels = {
    run: filteredKennels.filter(k => k.kennel_type === 'run'),
    suite: filteredKennels.filter(k => k.kennel_type === 'suite'),
    crate: filteredKennels.filter(k => k.kennel_type === 'crate'),
    luxury: filteredKennels.filter(k => k.kennel_type === 'luxury'),
  };

  // Stats
  const stats = {
    total: kennels.length,
    available: kennels.filter(k => k.computed_status === 'available').length,
    occupied: kennels.filter(k => k.computed_status === 'occupied').length,
    other: kennels.filter(k => !['available', 'occupied'].includes(k.computed_status)).length,
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="animate-spin h-8 w-8 border-2 border-blue-500 border-t-transparent rounded-full"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950" data-testid="lodging-map-page">
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
                <h1 className="text-2xl font-bold text-white">Lodging Map</h1>
                <p className="text-slate-400 text-sm">Visual kennel occupancy</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Input
                type="date"
                value={selectedDate}
                onChange={(e) => setSelectedDate(e.target.value)}
                className="bg-slate-800 border-slate-700 text-white w-40"
              />
              <Select value={typeFilter} onValueChange={setTypeFilter}>
                <SelectTrigger className="w-32 bg-slate-800 border-slate-700 text-white">
                  <SelectValue placeholder="All Types" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Types</SelectItem>
                  <SelectItem value="run">Runs</SelectItem>
                  <SelectItem value="suite">Suites</SelectItem>
                  <SelectItem value="crate">Crates</SelectItem>
                  <SelectItem value="luxury">Luxury</SelectItem>
                </SelectContent>
              </Select>
              <Button
                variant="outline"
                size="sm"
                onClick={loadData}
                className="border-slate-600 text-slate-300"
              >
                <RefreshCwIcon size={16} />
              </Button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Quick Stats */}
        <div className="flex items-center gap-6 mb-8">
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded bg-green-500/50"></div>
            <span className="text-slate-300">Available: {stats.available}</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded bg-red-500/50"></div>
            <span className="text-slate-300">Occupied: {stats.occupied}</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded bg-slate-500/50"></div>
            <span className="text-slate-300">Other: {stats.other}</span>
          </div>
          <div className="ml-auto text-slate-400">
            Occupancy: <span className="text-white font-semibold">
              {stats.total > 0 ? Math.round((stats.occupied / stats.total) * 100) : 0}%
            </span>
          </div>
        </div>

        {/* Kennel Grid by Type */}
        {Object.entries(groupedKennels).map(([type, typeKennels]) => {
          if (typeKennels.length === 0) return null;
          
          return (
            <div key={type} className="mb-8">
              <h2 className="text-lg font-semibold text-white mb-4 capitalize flex items-center gap-2">
                <div className={`w-3 h-3 rounded-full ${
                  type === 'run' ? 'bg-green-500' :
                  type === 'suite' ? 'bg-purple-500' :
                  type === 'crate' ? 'bg-blue-500' : 'bg-amber-500'
                }`}></div>
                {type}s ({typeKennels.length})
              </h2>
              
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 xl:grid-cols-8 gap-3">
                {typeKennels.map(kennel => {
                  const statusStyle = STATUS_COLORS[kennel.computed_status] || STATUS_COLORS.available;
                  const hasDogs = kennel.current_dogs?.length > 0;
                  
                  return (
                    <div
                      key={kennel.id}
                      onClick={() => handleKennelClick(kennel)}
                      className={`
                        relative p-3 rounded-lg border-2 cursor-pointer transition-all
                        ${statusStyle.bg} ${statusStyle.border}
                        hover:scale-105 hover:shadow-lg
                        border-l-4 ${TYPE_COLORS[kennel.kennel_type]}
                      `}
                      data-testid={`kennel-cell-${kennel.id}`}
                    >
                      {/* Kennel Name */}
                      <div className="font-semibold text-white text-sm mb-1">
                        {kennel.name}
                      </div>
                      
                      {/* Size */}
                      <div className="text-xs text-slate-400 capitalize mb-2">
                        {kennel.size_category}
                      </div>
                      
                      {/* Dog Info or Status */}
                      {hasDogs ? (
                        <div className="space-y-1">
                          {kennel.current_dogs.slice(0, 2).map(dog => (
                            <div key={dog.dog_id} className="flex items-center gap-1">
                              <DogIcon size={12} className="text-slate-400" />
                              <span className="text-xs text-white truncate">{dog.dog_name}</span>
                            </div>
                          ))}
                          {kennel.current_dogs.length > 2 && (
                            <div className="text-xs text-slate-400">
                              +{kennel.current_dogs.length - 2} more
                            </div>
                          )}
                        </div>
                      ) : (
                        <div className={`text-xs ${statusStyle.text}`}>
                          {statusStyle.label}
                        </div>
                      )}

                      {/* Indicators */}
                      <div className="absolute top-1 right-1 flex gap-1">
                        {kennel.current_dogs?.some(d => d.needs_medication) && (
                          <PillIcon size={12} className="text-red-400" />
                        )}
                        {kennel.current_dogs?.some(d => d.bath_scheduled && !d.bath_completed) && (
                          <ShowerHeadIcon size={12} className="text-cyan-400" />
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}

        {filteredKennels.length === 0 && (
          <Card className="bg-slate-900 border-slate-700">
            <CardContent className="py-12 text-center">
              <HomeIcon className="mx-auto text-slate-600 mb-4" size={48} />
              <h3 className="text-lg font-semibold text-slate-400">No kennels found</h3>
              <p className="text-slate-500">Add kennels in Kennel Management</p>
            </CardContent>
          </Card>
        )}
      </main>

      {/* Kennel Detail Modal */}
      <Dialog open={showKennelModal} onOpenChange={setShowKennelModal}>
        <DialogContent className="bg-slate-900 border-slate-700 max-w-md">
          {selectedKennel && (
            <>
              <DialogHeader>
                <DialogTitle className="text-white flex items-center gap-2">
                  <HomeIcon size={20} />
                  {selectedKennel.name}
                </DialogTitle>
              </DialogHeader>
              
              <div className="space-y-4 py-4">
                {/* Kennel Info */}
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-slate-400">Type:</span>
                    <span className="text-white ml-2 capitalize">{selectedKennel.kennel_type}</span>
                  </div>
                  <div>
                    <span className="text-slate-400">Size:</span>
                    <span className="text-white ml-2 capitalize">{selectedKennel.size_category}</span>
                  </div>
                  <div>
                    <span className="text-slate-400">Max Dogs:</span>
                    <span className="text-white ml-2">{selectedKennel.max_dogs}</span>
                  </div>
                  <div>
                    <span className="text-slate-400">Status:</span>
                    <Badge className={`ml-2 ${STATUS_COLORS[selectedKennel.computed_status]?.bg} ${STATUS_COLORS[selectedKennel.computed_status]?.text}`}>
                      {STATUS_COLORS[selectedKennel.computed_status]?.label}
                    </Badge>
                  </div>
                </div>

                {/* Features */}
                {selectedKennel.features?.length > 0 && (
                  <div>
                    <span className="text-slate-400 text-sm">Features:</span>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {selectedKennel.features.map(f => (
                        <Badge key={f} variant="outline" className="text-xs border-slate-600 text-slate-300">
                          {f.replace('_', ' ')}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

                {/* Current Occupants */}
                {selectedKennel.current_dogs?.length > 0 && (
                  <div className="border-t border-slate-700 pt-4">
                    <h4 className="text-white font-medium mb-3">Current Occupants</h4>
                    <div className="space-y-3">
                      {selectedKennel.current_dogs.map(dog => (
                        <div key={dog.dog_id} className="bg-slate-800 rounded-lg p-3">
                          <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center gap-2">
                              <DogIcon size={16} className="text-slate-400" />
                              <span className="text-white font-medium">{dog.dog_name}</span>
                            </div>
                            <span className="text-slate-400 text-xs">{dog.breed}</span>
                          </div>
                          <div className="text-xs text-slate-400 space-y-1">
                            <div className="flex items-center gap-1">
                              <CalendarIcon size={12} />
                              Checkout: {new Date(dog.check_out_date).toLocaleDateString()}
                              ({dog.nights_remaining} nights left)
                            </div>
                            <div className="flex items-center gap-1">
                              <PhoneIcon size={12} />
                              {dog.customer_name} {dog.customer_phone && `- ${dog.customer_phone}`}
                            </div>
                          </div>
                          
                          {/* Flags */}
                          <div className="flex gap-2 mt-2">
                            {dog.needs_medication && (
                              <Badge className="bg-red-500/20 text-red-400 text-xs">
                                <PillIcon size={10} className="mr-1" />
                                Medication
                              </Badge>
                            )}
                            {dog.special_diet && (
                              <Badge className="bg-orange-500/20 text-orange-400 text-xs">
                                <UtensilsIcon size={10} className="mr-1" />
                                Special Diet
                              </Badge>
                            )}
                            {dog.bath_scheduled && (
                              <Badge className={`text-xs ${dog.bath_completed ? 'bg-green-500/20 text-green-400' : 'bg-cyan-500/20 text-cyan-400'}`}>
                                <ShowerHeadIcon size={10} className="mr-1" />
                                {dog.bath_completed ? 'Bath Done' : 'Bath Pending'}
                              </Badge>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Status Change */}
                {selectedKennel.current_dogs?.length === 0 && (
                  <div className="border-t border-slate-700 pt-4">
                    <h4 className="text-white font-medium mb-3">Change Status</h4>
                    <div className="grid grid-cols-3 gap-2">
                      {['available', 'cleaning', 'maintenance'].map(status => (
                        <Button
                          key={status}
                          variant={selectedKennel.status === status ? 'default' : 'outline'}
                          size="sm"
                          onClick={() => handleStatusChange(selectedKennel.id, status)}
                          className={selectedKennel.status === status ? 'bg-blue-600' : 'border-slate-600 text-slate-300'}
                        >
                          {status.charAt(0).toUpperCase() + status.slice(1)}
                        </Button>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              <DialogFooter>
                <Button
                  variant="outline"
                  onClick={() => navigate(`/admin/kennels`)}
                  className="border-slate-600 text-slate-300"
                >
                  Manage Kennels
                </Button>
                <Button onClick={() => setShowKennelModal(false)} className="bg-blue-600 hover:bg-blue-700">
                  Close
                </Button>
              </DialogFooter>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
