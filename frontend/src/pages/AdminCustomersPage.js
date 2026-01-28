import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { ArrowLeftIcon, SearchIcon, DogIcon, MailIcon, PhoneIcon } from 'lucide-react';
import { toast } from 'sonner';
import api from '../utils/api';
import useAuthStore from '../store/authStore';

const AdminCustomersPage = () => {
  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);
  const [customers, setCustomers] = useState([]);
  const [dogs, setDogs] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user || user.role !== 'admin') {
      navigate('/auth');
      return;
    }
    fetchData();
  }, [user, navigate]);

  const fetchData = async () => {
    try {
      const [usersRes, dogsRes] = await Promise.all([
        api.get('/auth/me').then(() => api.get('/bookings')),
        api.get('/dogs'),
      ]);
      
      // Get unique customers (would need a proper users endpoint in production)
      setDogs(dogsRes.data);
    } catch (error) {
      toast.error('Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const filteredDogs = dogs.filter((dog) =>
    dog.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    dog.breed.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Group dogs by household
  const dogsByHousehold = filteredDogs.reduce((acc, dog) => {
    if (!acc[dog.household_id]) {
      acc[dog.household_id] = [];
    }
    acc[dog.household_id].push(dog);
    return acc;
  }, {});

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
          <Button
            variant="ghost"
            onClick={() => navigate('/admin/dashboard')}
            className="flex items-center gap-2 mb-2"
          >
            <ArrowLeftIcon size={18} />
            Back to Dashboard
          </Button>
          <h1 className="text-3xl font-serif font-bold text-primary">Customer & Dog Management</h1>
          <p className="text-muted-foreground mt-1">View all customers and their dogs</p>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 md:px-8 py-8">
        {/* Search */}
        <Card className="mb-6 bg-white rounded-2xl border border-border/50 shadow-sm">
          <CardContent className="p-6">
            <div className="relative">
              <SearchIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground" size={20} />
              <Input
                data-testid="search-input"
                placeholder="Search by dog name or breed..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>
          </CardContent>
        </Card>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
            <CardContent className="p-6">
              <p className="text-sm text-muted-foreground mb-1">Total Households</p>
              <p className="text-3xl font-serif font-bold text-primary">{Object.keys(dogsByHousehold).length}</p>
            </CardContent>
          </Card>
          <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
            <CardContent className="p-6">
              <p className="text-sm text-muted-foreground mb-1">Total Dogs</p>
              <p className="text-3xl font-serif font-bold text-secondary-foreground">{dogs.length}</p>
            </CardContent>
          </Card>
          <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
            <CardContent className="p-6">
              <p className="text-sm text-muted-foreground mb-1">Avg Dogs/Household</p>
              <p className="text-3xl font-serif font-bold text-primary">
                {Object.keys(dogsByHousehold).length > 0 
                  ? (dogs.length / Object.keys(dogsByHousehold).length).toFixed(1)
                  : 0}
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Households List */}
        <div className="space-y-6">
          {Object.entries(dogsByHousehold).map(([householdId, householdDogs]) => (
            <Card key={householdId} data-testid={`household-${householdId}`} className="bg-white rounded-2xl border border-border/50 shadow-sm">
              <CardHeader className="border-b border-border/40">
                <CardTitle className="text-xl font-serif">Household {householdId.slice(0, 8)}</CardTitle>
              </CardHeader>
              <CardContent className="p-6">
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {householdDogs.map((dog) => (
                    <div
                      key={dog.id}
                      className="p-4 rounded-xl border border-border bg-[#F9F7F2] hover:border-primary/50 transition-all"
                    >
                      <div className="flex items-start gap-3">
                        <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                          {dog.photo_url ? (
                            <img src={dog.photo_url} alt={dog.name} className="w-full h-full rounded-full object-cover" />
                          ) : (
                            <DogIcon className="text-primary" size={24} />
                          )}
                        </div>
                        <div className="flex-1 min-w-0">
                          <h4 className="font-semibold text-lg truncate">{dog.name}</h4>
                          <p className="text-sm text-muted-foreground">{dog.breed}</p>
                          {dog.age && <p className="text-sm text-muted-foreground">{dog.age} years old</p>}
                          {dog.friendly_with_dogs === false && (
                            <p className="text-xs text-orange-600 mt-1">⚠️ Separate playtime needed</p>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {filteredDogs.length === 0 && (
          <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
            <CardContent className="p-12 text-center">
              <DogIcon size={48} className="mx-auto text-muted-foreground/50 mb-4" />
              <p className="text-muted-foreground">No dogs found</p>
            </CardContent>
          </Card>
        )}
      </main>
    </div>
  );
};

export default AdminCustomersPage;
