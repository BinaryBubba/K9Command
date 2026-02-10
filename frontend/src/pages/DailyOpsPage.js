import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { toast } from 'sonner';
import { 
  DogIcon, 
  ArrowLeftIcon,
  SearchIcon,
  CalendarIcon,
  ClockIcon,
  HomeIcon,
  PillIcon,
  UtensilsIcon,
  AlertTriangleIcon,
  PhoneIcon,
  ShowerHeadIcon,
  ChevronRightIcon,
  LogInIcon,
  LogOutIcon,
  RefreshCwIcon
} from 'lucide-react';
import api from '../utils/api';

export default function DailyOpsPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [summary, setSummary] = useState(null);
  const [dogsOnSite, setDogsOnSite] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);
  const [activeTab, setActiveTab] = useState('on-site');

  useEffect(() => {
    loadData();
  }, [selectedDate]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [summaryRes, dogsRes] = await Promise.all([
        api.get(`/k9/operations/summary?location_id=main&date=${selectedDate}`),
        api.get(`/k9/operations/dogs-on-site?location_id=main&date=${selectedDate}`)
      ]);
      setSummary(summaryRes.data);
      setDogsOnSite(dogsRes.data);
    } catch (error) {
      console.error('Failed to load operations data:', error);
      toast.error('Failed to load operations data');
    } finally {
      setLoading(false);
    }
  };

  const filteredDogs = dogsOnSite.filter(dog =>
    dog.dog_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    dog.customer_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    dog.kennel_name?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const checkInsToday = dogsOnSite.filter(d => {
    const checkIn = new Date(d.check_in_date).toISOString().split('T')[0];
    return checkIn === selectedDate;
  });

  const checkOutsToday = dogsOnSite.filter(d => {
    const checkOut = new Date(d.check_out_date).toISOString().split('T')[0];
    return checkOut === selectedDate;
  });

  const needsAttention = dogsOnSite.filter(d => 
    d.needs_medication || d.special_diet || d.bath_scheduled
  );

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="animate-spin h-8 w-8 border-2 border-blue-500 border-t-transparent rounded-full"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950" data-testid="daily-ops-page">
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
                <h1 className="text-2xl font-bold text-white">Daily Operations</h1>
                <p className="text-slate-400 text-sm">Dogs on site & daily schedule</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Input
                type="date"
                value={selectedDate}
                onChange={(e) => setSelectedDate(e.target.value)}
                className="bg-slate-800 border-slate-700 text-white w-40"
              />
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
        {/* Summary Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 mb-8">
          <Card className="bg-gradient-to-br from-blue-600 to-blue-700 border-none">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <DogIcon className="text-white" size={24} />
                <div>
                  <p className="text-blue-100 text-sm">Dogs On Site</p>
                  <p className="text-2xl font-bold text-white">{summary?.dogs_on_site || 0}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-emerald-600 to-emerald-700 border-none">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <LogInIcon className="text-white" size={24} />
                <div>
                  <p className="text-emerald-100 text-sm">Check-Ins</p>
                  <p className="text-2xl font-bold text-white">
                    {summary?.check_ins_completed || 0}/{summary?.check_ins_scheduled || 0}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-amber-600 to-amber-700 border-none">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <LogOutIcon className="text-white" size={24} />
                <div>
                  <p className="text-amber-100 text-sm">Check-Outs</p>
                  <p className="text-2xl font-bold text-white">
                    {summary?.check_outs_completed || 0}/{summary?.check_outs_scheduled || 0}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-purple-600 to-purple-700 border-none">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <HomeIcon className="text-white" size={24} />
                <div>
                  <p className="text-purple-100 text-sm">Occupancy</p>
                  <p className="text-2xl font-bold text-white">{summary?.occupancy_rate || 0}%</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-cyan-600 to-cyan-700 border-none">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <ShowerHeadIcon className="text-white" size={24} />
                <div>
                  <p className="text-cyan-100 text-sm">Baths</p>
                  <p className="text-2xl font-bold text-white">
                    {summary?.baths_completed || 0}/{summary?.baths_scheduled || 0}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-slate-600 to-slate-700 border-none">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <HomeIcon className="text-white" size={24} />
                <div>
                  <p className="text-slate-100 text-sm">Available</p>
                  <p className="text-2xl font-bold text-white">
                    {summary?.available_kennels || 0}/{summary?.total_kennels || 0}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <div className="flex items-center justify-between mb-6">
            <TabsList className="bg-slate-800">
              <TabsTrigger value="on-site" className="data-[state=active]:bg-slate-700">
                All Dogs ({dogsOnSite.length})
              </TabsTrigger>
              <TabsTrigger value="check-ins" className="data-[state=active]:bg-slate-700">
                Check-Ins ({checkInsToday.length})
              </TabsTrigger>
              <TabsTrigger value="check-outs" className="data-[state=active]:bg-slate-700">
                Check-Outs ({checkOutsToday.length})
              </TabsTrigger>
              <TabsTrigger value="attention" className="data-[state=active]:bg-slate-700">
                Needs Attention ({needsAttention.length})
              </TabsTrigger>
            </TabsList>

            <div className="relative">
              <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
              <Input
                placeholder="Search dogs..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-9 bg-slate-800 border-slate-700 text-white w-64"
              />
            </div>
          </div>

          {/* All Dogs Tab */}
          <TabsContent value="on-site">
            <DogList dogs={filteredDogs} />
          </TabsContent>

          {/* Check-Ins Tab */}
          <TabsContent value="check-ins">
            <DogList dogs={checkInsToday.filter(d => 
              d.dog_name?.toLowerCase().includes(searchTerm.toLowerCase())
            )} showCheckInTime />
          </TabsContent>

          {/* Check-Outs Tab */}
          <TabsContent value="check-outs">
            <DogList dogs={checkOutsToday.filter(d => 
              d.dog_name?.toLowerCase().includes(searchTerm.toLowerCase())
            )} showCheckOutTime />
          </TabsContent>

          {/* Needs Attention Tab */}
          <TabsContent value="attention">
            <DogList dogs={needsAttention.filter(d => 
              d.dog_name?.toLowerCase().includes(searchTerm.toLowerCase())
            )} showAttentionItems />
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
}

function DogList({ dogs, showCheckInTime, showCheckOutTime, showAttentionItems }) {
  const navigate = useNavigate();

  if (dogs.length === 0) {
    return (
      <Card className="bg-slate-900 border-slate-700">
        <CardContent className="py-12 text-center">
          <DogIcon className="mx-auto text-slate-600 mb-4" size={48} />
          <h3 className="text-lg font-semibold text-slate-400 mb-2">No dogs found</h3>
          <p className="text-slate-500">No dogs match the current filter</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {dogs.map(dog => (
        <Card 
          key={`${dog.booking_id}-${dog.dog_id}`}
          className="bg-slate-900 border-slate-700 hover:border-slate-600 transition-colors cursor-pointer"
          onClick={() => navigate(`/admin/bookings/${dog.booking_id}`)}
          data-testid={`dog-card-${dog.dog_id}`}
        >
          <CardContent className="p-4">
            <div className="flex items-start gap-3">
              {/* Dog Photo/Avatar */}
              <div className="w-14 h-14 rounded-lg bg-slate-800 flex items-center justify-center flex-shrink-0 overflow-hidden">
                {dog.photo_url ? (
                  <img src={dog.photo_url} alt={dog.dog_name} className="w-full h-full object-cover" />
                ) : (
                  <DogIcon className="text-slate-500" size={28} />
                )}
              </div>

              {/* Dog Info */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <h3 className="font-semibold text-white truncate">{dog.dog_name}</h3>
                  {dog.nights_remaining <= 1 && (
                    <Badge className="bg-amber-500/20 text-amber-400 border-amber-500/30 text-xs">
                      {dog.nights_remaining === 0 ? 'Checkout Today' : '1 night left'}
                    </Badge>
                  )}
                </div>
                <p className="text-slate-400 text-sm">{dog.breed}</p>
                <p className="text-slate-500 text-xs">{dog.customer_name}</p>
              </div>

              <ChevronRightIcon className="text-slate-500" size={20} />
            </div>

            {/* Kennel & Stay Info */}
            <div className="mt-3 pt-3 border-t border-slate-800 grid grid-cols-2 gap-2 text-sm">
              <div className="flex items-center gap-2 text-slate-400">
                <HomeIcon size={14} />
                <span>{dog.kennel_name || 'Unassigned'}</span>
              </div>
              <div className="flex items-center gap-2 text-slate-400">
                <CalendarIcon size={14} />
                <span>{dog.nights_remaining} nights left</span>
              </div>
            </div>

            {/* Attention Items */}
            {(showAttentionItems || dog.needs_medication || dog.special_diet || dog.bath_scheduled) && (
              <div className="mt-3 pt-3 border-t border-slate-800 flex flex-wrap gap-2">
                {dog.needs_medication && (
                  <Badge className="bg-red-500/20 text-red-400 border-red-500/30 text-xs">
                    <PillIcon size={12} className="mr-1" />
                    Medication
                  </Badge>
                )}
                {dog.special_diet && (
                  <Badge className="bg-orange-500/20 text-orange-400 border-orange-500/30 text-xs">
                    <UtensilsIcon size={12} className="mr-1" />
                    Special Diet
                  </Badge>
                )}
                {dog.bath_scheduled && !dog.bath_completed && (
                  <Badge className="bg-cyan-500/20 text-cyan-400 border-cyan-500/30 text-xs">
                    <ShowerHeadIcon size={12} className="mr-1" />
                    Bath Scheduled
                  </Badge>
                )}
                {dog.bath_completed && (
                  <Badge className="bg-green-500/20 text-green-400 border-green-500/30 text-xs">
                    <ShowerHeadIcon size={12} className="mr-1" />
                    Bath Done
                  </Badge>
                )}
              </div>
            )}

            {/* Customer Phone (for quick contact) */}
            {dog.customer_phone && (
              <div className="mt-3 pt-3 border-t border-slate-800">
                <a 
                  href={`tel:${dog.customer_phone}`}
                  onClick={(e) => e.stopPropagation()}
                  className="flex items-center gap-2 text-blue-400 hover:text-blue-300 text-sm"
                >
                  <PhoneIcon size={14} />
                  {dog.customer_phone}
                </a>
              </div>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
