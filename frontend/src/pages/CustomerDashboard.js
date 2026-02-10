import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import useAuthStore from '../store/authStore';
import { dataClient, dataMode } from '../data/client';
import { Button } from '../components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Badge } from '../components/ui/badge';
import { PlusIcon, DogIcon, CalendarIcon, ImageIcon, LogOutIcon, CreditCardIcon, SettingsIcon, LayoutGridIcon, EditIcon, XIcon, CheckIcon, ClockIcon, SunIcon, UtensilsIcon, ActivityIcon } from 'lucide-react';
import { toast } from 'sonner';
import NotificationBell from '../components/NotificationBell';
import PushNotificationSettings from '../components/PushNotificationSettings';

const CustomerDashboard = () => {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const [stats, setStats] = useState({});
  const [dogs, setDogs] = useState([]);
  const [bookings, setBookings] = useState([]);
  const [updates, setUpdates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [todayAgenda, setTodayAgenda] = useState([]);

  // Edit dog modal state
  const [editDogModal, setEditDogModal] = useState(false);
  const [editingDog, setEditingDog] = useState(null);
  const [dogForm, setDogForm] = useState({});
  const [savingDog, setSavingDog] = useState(false);

  // Edit booking modal state
  const [editBookingModal, setEditBookingModal] = useState(false);
  const [editingBooking, setEditingBooking] = useState(null);
  const [bookingForm, setBookingForm] = useState({});
  const [savingBooking, setSavingBooking] = useState(false);

  useEffect(() => {
    if (!user || user.role !== 'customer') {
      navigate('/auth');
      return;
    }
    fetchData();
  }, [user, navigate]);

  const fetchData = async () => {
    try {
      const [statsData, dogsData, bookingsData, updatesData] = await Promise.all([
        dataClient.getDashboardStats(),
        dataClient.listDogs(),
        dataClient.listBookings(),
        dataClient.getDailyUpdates(),
      ]);
      setStats(statsData || {});
      setDogs(dogsData || []);
      setBookings(bookingsData || []);
      setUpdates(updatesData || []);
      
      // Build today's agenda from active bookings
      const today = new Date().toISOString().split('T')[0];
      const activeBookings = (bookingsData || []).filter(b => {
        const checkIn = b.check_in_date?.split('T')[0];
        const checkOut = b.check_out_date?.split('T')[0];
        return checkIn <= today && checkOut >= today && ['confirmed', 'checked_in'].includes(b.status);
      });
      
      // Create agenda items for today
      const agenda = [];
      activeBookings.forEach(booking => {
        const dogNames = (booking.dog_ids || []).map(id => {
          const dog = (dogsData || []).find(d => d.id === id);
          return dog?.name || 'Your pup';
        }).join(', ');
        
        if (booking.check_in_date?.split('T')[0] === today) {
          agenda.push({ time: '8:00 AM', type: 'check_in', title: 'Check-In', description: `${dogNames} arriving for ${booking.booking_type || 'stay'}`, icon: 'sun' });
        }
        if (booking.check_out_date?.split('T')[0] === today) {
          agenda.push({ time: '4:00 PM', type: 'check_out', title: 'Check-Out', description: `${dogNames} ready for pickup`, icon: 'check' });
        }
        if (booking.status === 'checked_in') {
          agenda.push({ time: '7:30 AM', type: 'breakfast', title: 'Breakfast', description: `${dogNames} morning meal`, icon: 'utensils' });
          agenda.push({ time: '10:00 AM', type: 'playtime', title: 'Playtime', description: `${dogNames} group play session`, icon: 'activity' });
          agenda.push({ time: '12:30 PM', type: 'lunch', title: 'Lunch', description: `${dogNames} midday meal`, icon: 'utensils' });
          agenda.push({ time: '3:00 PM', type: 'playtime', title: 'Afternoon Activity', description: `${dogNames} afternoon enrichment`, icon: 'activity' });
          agenda.push({ time: '5:30 PM', type: 'dinner', title: 'Dinner', description: `${dogNames} evening meal`, icon: 'utensils' });
        }
      });
      
      // Sort by time
      agenda.sort((a, b) => {
        const timeA = new Date(`2000-01-01 ${a.time}`).getTime();
        const timeB = new Date(`2000-01-01 ${b.time}`).getTime();
        return timeA - timeB;
      });
      
      setTodayAgenda(agenda);
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
      toast.error('Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  // ---------- Dog Edit Functions ----------
  const openEditDog = (dog) => {
    setEditingDog(dog);
    setDogForm({
      name: dog.name || '',
      breed: dog.breed || '',
      age: dog.age || '',
      birthday: dog.birthday || '',
      feedingInstructions: dog.feedingInstructions || dog.feeding_instructions || '',
      medications: dog.medications || '',
      behaviorNotes: dog.behaviorNotes || dog.behavior_notes || '',
    });
    setEditDogModal(true);
  };

  const handleSaveDog = async () => {
    if (!editingDog) return;
    setSavingDog(true);
    try {
      await dataClient.updateDog(editingDog.id, dogForm);
      toast.success('Dog profile updated!');
      setEditDogModal(false);
      setEditingDog(null);
      fetchData();
    } catch (error) {
      toast.error(error.message || 'Failed to update dog');
    } finally {
      setSavingDog(false);
    }
  };

  // ---------- Booking Edit Functions ----------
  const canEditBooking = (booking) => {
    const allowedStatuses = ['pending', 'confirmed'];
    if (!allowedStatuses.includes(booking.status)) return false;
    
    const checkInDate = new Date(booking.startDate);
    const now = new Date();
    const hoursUntilCheckIn = (checkInDate - now) / (1000 * 60 * 60);
    return hoursUntilCheckIn >= 24;
  };

  const openEditBooking = (booking) => {
    if (!canEditBooking(booking)) {
      toast.error('This booking cannot be modified');
      return;
    }
    setEditingBooking(booking);
    setBookingForm({
      startDate: booking.startDate || '',
      endDate: booking.endDate || '',
      notes: booking.notes || '',
    });
    setEditBookingModal(true);
  };

  const handleSaveBooking = async () => {
    if (!editingBooking) return;
    setSavingBooking(true);
    try {
      await dataClient.updateBooking(editingBooking.id, bookingForm);
      toast.success('Booking updated!');
      setEditBookingModal(false);
      setEditingBooking(null);
      fetchData();
    } catch (error) {
      toast.error(error.message || 'Failed to update booking');
    } finally {
      setSavingBooking(false);
    }
  };

  const handleCancelBooking = async (booking) => {
    if (!canEditBooking(booking)) {
      toast.error('This booking cannot be cancelled');
      return;
    }
    if (!window.confirm('Are you sure you want to cancel this booking?')) return;
    
    try {
      await dataClient.cancelBooking(booking.id);
      toast.success('Booking cancelled');
      fetchData();
    } catch (error) {
      toast.error(error.message || 'Failed to cancel booking');
    }
  };

  // Get upcoming bookings
  const upcomingBookings = bookings.filter(b => {
    const checkIn = new Date(b.startDate);
    return checkIn >= new Date() && ['pending', 'confirmed'].includes(b.status);
  }).slice(0, 5);

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
            <span className="text-xs text-muted-foreground hidden sm:block">
              Mode: {dataMode}
            </span>
            <NotificationBell />
            <Button
              variant="outline"
              onClick={() => navigate('/customer/portal')}
              className="flex items-center gap-2"
            >
              <LayoutGridIcon size={18} />
              My Portal
            </Button>
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
                  <p className="text-3xl font-serif font-bold text-primary mt-2">{stats.my_dogs || dogs.length}</p>
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
                  <p className="text-3xl font-serif font-bold text-secondary-foreground mt-2">{stats.my_bookings || bookings.length}</p>
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
                  <p className="text-3xl font-serif font-bold text-primary mt-2">{stats.upcoming_bookings || upcomingBookings.length}</p>
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
                  <p className="text-muted-foreground">Pay invoices & manage cards</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Upcoming Bookings */}
        <Card data-testid="upcoming-bookings-section" className="bg-white rounded-2xl border border-border/50 shadow-sm mb-8">
          <CardHeader className="border-b border-border/40">
            <div className="flex justify-between items-center">
              <CardTitle className="text-2xl font-serif flex items-center gap-2">
                <CalendarIcon className="text-primary" />
                Upcoming Bookings
              </CardTitle>
              {bookings.length > 0 && (
                <Button
                  onClick={() => navigate('/customer/calendar')}
                  variant="outline"
                  className="rounded-full"
                >
                  View Calendar
                </Button>
              )}
            </div>
          </CardHeader>
          <CardContent className="p-6">
            {upcomingBookings.length === 0 ? (
              <div className="text-center py-12">
                <CalendarIcon size={48} className="mx-auto text-muted-foreground/50 mb-4" />
                <p className="text-muted-foreground mb-4">No upcoming bookings.</p>
                <Button onClick={() => navigate('/customer/bookings/new')} className="rounded-full">
                  <PlusIcon size={18} className="mr-2" />
                  Book a Stay
                </Button>
              </div>
            ) : (
              <div className="space-y-4">
                {upcomingBookings.map((booking) => (
                  <div
                    key={booking.id}
                    data-testid={`booking-card-${booking.id}`}
                    className="p-4 rounded-xl border border-border/40 bg-muted/20 hover:bg-muted/30 transition-all"
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="font-medium text-lg">
                          {booking.dogs?.length ? booking.dogs.join(', ') : 'Booking'}
                        </div>
                        <div className="text-sm text-muted-foreground mt-1">
                          {booking.startDate} → {booking.endDate}
                        </div>
                        {booking.notes && (
                          <div className="text-sm mt-1 text-muted-foreground">{booking.notes}</div>
                        )}
                      </div>
                      <div className="flex items-center gap-2">
                        <span className={`text-xs px-3 py-1 rounded-full ${
                          booking.status === 'confirmed' ? 'bg-green-100 text-green-700' :
                          booking.status === 'pending' ? 'bg-yellow-100 text-yellow-700' :
                          'bg-gray-100 text-gray-700'
                        }`}>
                          {booking.status}
                        </span>
                        {canEditBooking(booking) && (
                          <>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={(e) => { e.stopPropagation(); openEditBooking(booking); }}
                            >
                              <EditIcon size={16} />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="text-red-500 hover:text-red-700"
                              onClick={(e) => { e.stopPropagation(); handleCancelBooking(booking); }}
                            >
                              <XIcon size={16} />
                            </Button>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

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
        <Card data-testid="my-dogs-section" className="bg-white rounded-2xl border border-border/50 shadow-sm mb-8">
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
                    className="bg-white rounded-xl border border-border/40 p-6 hover:shadow-md hover:border-primary/30 transition-all relative group"
                  >
                    <Button
                      variant="ghost"
                      size="sm"
                      className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity"
                      onClick={(e) => { e.stopPropagation(); openEditDog(dog); }}
                    >
                      <EditIcon size={16} />
                    </Button>
                    <div className="w-20 h-20 rounded-full bg-primary/10 mx-auto mb-4 flex items-center justify-center">
                      {dog.photo_url || dog.photoUrl ? (
                        <img src={dog.photo_url || dog.photoUrl} alt={dog.name} className="w-full h-full rounded-full object-cover" />
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

        {/* Settings Section */}
        <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
          <CardHeader className="border-b border-border/40">
            <CardTitle className="text-2xl font-serif flex items-center gap-2">
              <SettingsIcon className="text-primary" />
              Notification Settings
            </CardTitle>
          </CardHeader>
          <CardContent className="p-6">
            <PushNotificationSettings />
          </CardContent>
        </Card>
      </main>

      {/* Edit Dog Modal */}
      <Dialog open={editDogModal} onOpenChange={setEditDogModal}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Edit Dog Profile</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <Label>Name</Label>
              <Input
                value={dogForm.name || ''}
                onChange={(e) => setDogForm({ ...dogForm, name: e.target.value })}
              />
            </div>
            <div>
              <Label>Breed</Label>
              <Input
                value={dogForm.breed || ''}
                onChange={(e) => setDogForm({ ...dogForm, breed: e.target.value })}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Age (years)</Label>
                <Input
                  type="number"
                  value={dogForm.age || ''}
                  onChange={(e) => setDogForm({ ...dogForm, age: e.target.value })}
                />
              </div>
              <div>
                <Label>Birthday</Label>
                <Input
                  type="date"
                  value={dogForm.birthday || ''}
                  onChange={(e) => setDogForm({ ...dogForm, birthday: e.target.value })}
                />
              </div>
            </div>
            <div>
              <Label>Feeding Instructions</Label>
              <Textarea
                value={dogForm.feedingInstructions || ''}
                onChange={(e) => setDogForm({ ...dogForm, feedingInstructions: e.target.value })}
                rows={2}
              />
            </div>
            <div>
              <Label>Medications</Label>
              <Textarea
                value={dogForm.medications || ''}
                onChange={(e) => setDogForm({ ...dogForm, medications: e.target.value })}
                rows={2}
              />
            </div>
            <div>
              <Label>Behavior Notes</Label>
              <Textarea
                value={dogForm.behaviorNotes || ''}
                onChange={(e) => setDogForm({ ...dogForm, behaviorNotes: e.target.value })}
                rows={2}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditDogModal(false)}>Cancel</Button>
            <Button onClick={handleSaveDog} disabled={savingDog}>
              {savingDog ? 'Saving...' : 'Save Changes'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Booking Modal */}
      <Dialog open={editBookingModal} onOpenChange={setEditBookingModal}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Edit Booking</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <Label>Check-in Date</Label>
              <Input
                type="date"
                value={bookingForm.startDate || ''}
                onChange={(e) => setBookingForm({ ...bookingForm, startDate: e.target.value })}
              />
            </div>
            <div>
              <Label>Check-out Date</Label>
              <Input
                type="date"
                value={bookingForm.endDate || ''}
                onChange={(e) => setBookingForm({ ...bookingForm, endDate: e.target.value })}
              />
            </div>
            <div>
              <Label>Notes</Label>
              <Textarea
                value={bookingForm.notes || ''}
                onChange={(e) => setBookingForm({ ...bookingForm, notes: e.target.value })}
                rows={3}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditBookingModal(false)}>Cancel</Button>
            <Button onClick={handleSaveBooking} disabled={savingBooking}>
              {savingBooking ? 'Saving...' : 'Save Changes'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default CustomerDashboard;
