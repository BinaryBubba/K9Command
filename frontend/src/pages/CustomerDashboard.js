import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import useAuthStore from '../store/authStore';
import api from '../utils/api';
import { Button } from '../components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/card';
import { PlusIcon, DogIcon, CalendarIcon, ImageIcon, LogOutIcon, CreditCardIcon } from 'lucide-react';
import { toast } from 'sonner';
import NotificationBell from '../components/NotificationBell';

const CustomerDashboard = () => {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const [stats, setStats] = useState({});
  const [dogs, setDogs] = useState([]);
  const [bookings, setBookings] = useState([]);
  const [updates, setUpdates] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user || user.role !== 'customer') {
      navigate('/auth');
      return;
    }
    fetchData();
  }, [user, navigate]);

  const fetchData = async () => {
    try {
      const [statsRes, dogsRes, bookingsRes, updatesRes] = await Promise.all([
        api.get('/dashboard/stats'),
        api.get('/dogs'),
        api.get('/bookings'),
        api.get('/daily-updates'),
      ]);
      setStats(statsRes.data);
      setDogs(dogsRes.data);
      setBookings(bookingsRes.data);
      setUpdates(updatesRes.data);
    } catch (error) {
      toast.error('Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div>
          <p className="mt-4 text-muted-foreground">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#F9F7F2]">
      {/* Header */}
      <header className="bg-white border-b border-border/40 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 md:px-8 py-4 flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-serif font-bold text-primary">My Dashboard</h1>
            <p className="text-sm text-muted-foreground">Welcome back, {user?.full_name}</p>
          </div>
          <div className="flex items-center gap-4">
            <NotificationBell />
            <Button
              data-testid="logout-button"
              onClick={handleLogout}
              variant="ghost"
              className="flex items-center gap-2"
            >
              <LogOutIcon size={18} />
              Logout
            </Button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 md:px-8 py-8">
        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <Card data-testid="stat-card-dogs" className="bg-white rounded-2xl border border-border/50 shadow-sm">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground uppercase tracking-wider">My Dogs</p>
                  <p className="text-3xl font-serif font-bold text-primary mt-2">{stats.my_dogs || 0}</p>
                </div>
                <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center">
                  <DogIcon className="text-primary" size={24} />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card data-testid="stat-card-bookings" className="bg-white rounded-2xl border border-border/50 shadow-sm">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground uppercase tracking-wider">Total Bookings</p>
                  <p className="text-3xl font-serif font-bold text-secondary-foreground mt-2">{stats.my_bookings || 0}</p>
                </div>
                <div className="w-12 h-12 rounded-full bg-secondary/20 flex items-center justify-center">
                  <CalendarIcon className="text-secondary-foreground" size={24} />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card data-testid="stat-card-upcoming" className="bg-white rounded-2xl border border-border/50 shadow-sm">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground uppercase tracking-wider">Upcoming</p>
                  <p className="text-3xl font-serif font-bold text-primary mt-2">{stats.upcoming_bookings || 0}</p>
                </div>
                <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center">
                  <CalendarIcon className="text-primary" size={24} />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Quick Actions */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          <Card data-testid="action-card-add-dog" className="bg-gradient-to-br from-primary to-primary/80 text-white rounded-2xl shadow-lg cursor-pointer hover:shadow-xl hover:-translate-y-1 transition-all duration-300" onClick={() => navigate('/customer/dogs/add')}>
            <CardContent className="p-8">
              <div className="flex items-center gap-4">
                <div className="w-16 h-16 rounded-full bg-white/20 backdrop-blur-sm flex items-center justify-center">
                  <PlusIcon size={32} />
                </div>
                <div>
                  <h3 className="text-2xl font-serif font-bold">Add a Dog</h3>
                  <p className="opacity-90">Register a new furry friend</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card data-testid="action-card-book-stay" className="bg-gradient-to-br from-secondary to-secondary/80 text-secondary-foreground rounded-2xl shadow-lg cursor-pointer hover:shadow-xl hover:-translate-y-1 transition-all duration-300" onClick={() => navigate('/customer/bookings/new')}>
            <CardContent className="p-8">
              <div className="flex items-center gap-4">
                <div className="w-16 h-16 rounded-full bg-white/30 backdrop-blur-sm flex items-center justify-center">
                  <CalendarIcon size={32} />
                </div>
                <div>
                  <h3 className="text-2xl font-serif font-bold">Book a Stay</h3>
                  <p className="opacity-90">Reserve your next visit</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card data-testid="action-card-calendar" className="bg-white rounded-2xl border border-border/50 shadow-lg cursor-pointer hover:shadow-xl hover:-translate-y-1 transition-all duration-300" onClick={() => navigate('/customer/calendar')}>
            <CardContent className="p-8">
              <div className="flex items-center gap-4">
                <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center">
                  <CalendarIcon className="text-primary" size={32} />
                </div>
                <div>
                  <h3 className="text-2xl font-serif font-bold text-primary">Calendar</h3>
                  <p className="text-muted-foreground">View stays by day or week</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card data-testid="action-card-payments" className="bg-white rounded-2xl border border-border/50 shadow-lg cursor-pointer hover:shadow-xl hover:-translate-y-1 transition-all duration-300" onClick={() => navigate('/customer/payments')}>
            <CardContent className="p-8">
              <div className="flex items-center gap-4">
                <div className="w-16 h-16 rounded-full bg-secondary/20 flex items-center justify-center">
                  <CreditCardIcon className="text-secondary-foreground" size={32} />
                </div>
                <div>
                  <h3 className="text-2xl font-serif font-bold text-primary">Payments</h3>
                  <p className="text-muted-foreground">Pay invoices (Square) + crypto soon</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Recent Updates */}
        <Card data-testid="recent-updates-section" className="bg-white rounded-2xl border border-border/50 shadow-sm mb-8">
          <CardHeader className="border-b border-border/40">
            <div className="flex justify-between items-center">
              <CardTitle className="text-2xl font-serif flex items-center gap-2">
                <ImageIcon className="text-primary" />
                Recent Daily Updates
              </CardTitle>
              {updates.length > 0 && (
                <Button
                  data-testid="view-all-updates-button"
                  onClick={() => navigate('/customer/updates')}
                  variant="outline"
                  className="rounded-full"
                >
                  View All
                </Button>
              )}
            </div>
          </CardHeader>
          <CardContent className="p-6">
            {updates.length === 0 ? (
              <div className="text-center py-12">
                <ImageIcon size={48} className="mx-auto text-muted-foreground/50 mb-4" />
                <p className="text-muted-foreground">No updates yet. Book a stay to receive daily photo updates!</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {updates.slice(0, 6).map((update) => (
                  <div
                    key={update.id}
                    data-testid={`update-card-${update.id}`}
                    className="bg-[#F9F7F2] rounded-xl p-4 border border-border/30 hover:border-primary/30 transition-all cursor-pointer"
                    onClick={() => navigate('/customer/updates')}
                  >
                    <div className="aspect-square bg-primary/5 rounded-lg mb-3 flex items-center justify-center">
                      <ImageIcon size={32} className="text-primary/30" />
                    </div>
                    <p className="text-sm text-muted-foreground mb-1">
                      {new Date(update.date).toLocaleDateString()}
                    </p>
                    <p className="text-sm line-clamp-2">{update.ai_summary || 'Processing...'}</p>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* My Dogs */}
        <Card data-testid="my-dogs-section" className="bg-white rounded-2xl border border-border/50 shadow-sm">
          <CardHeader className="border-b border-border/40">
            <CardTitle className="text-2xl font-serif flex items-center gap-2">
              <DogIcon className="text-primary" />
              My Dogs
            </CardTitle>
          </CardHeader>
          <CardContent className="p-6">
            {dogs.length === 0 ? (
              <div className="text-center py-12">
                <DogIcon size={48} className="mx-auto text-muted-foreground/50 mb-4" />
                <p className="text-muted-foreground mb-4">You haven't added any dogs yet.</p>
                <Button
                  data-testid="add-first-dog-button"
                  onClick={() => navigate('/customer/dogs/add')}
                  className="rounded-full"
                >
                  <PlusIcon size={18} className="mr-2" />
                  Add Your First Dog
                </Button>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {dogs.map((dog) => (
                  <div
                    key={dog.id}
                    data-testid={`dog-card-${dog.id}`}
                    className="bg-white rounded-xl border border-border/40 p-6 hover:shadow-md hover:border-primary/30 transition-all cursor-pointer"
                    onClick={() => navigate(`/customer/dogs/${dog.id}`)}
                  >
                    <div className="w-20 h-20 rounded-full bg-primary/10 mx-auto mb-4 flex items-center justify-center">
                      {dog.photo_url ? (
                        <img src={dog.photo_url} alt={dog.name} className="w-full h-full rounded-full object-cover" />
                      ) : (
                        <DogIcon size={32} className="text-primary" />
                      )}
                    </div>
                    <h3 className="text-xl font-serif font-semibold text-center mb-2">{dog.name}</h3>
                    <p className="text-sm text-muted-foreground text-center">{dog.breed}</p>
                    {dog.age && <p className="text-sm text-muted-foreground text-center">{dog.age} years old</p>}
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </main>
    </div>
  );
};

export default CustomerDashboard;
