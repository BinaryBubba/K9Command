import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import useAuthStore from '../store/authStore';
import api from '../utils/api';
import { Button } from '../components/ui/button';
import { Card, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { ArrowLeftIcon, CalendarIcon, DogIcon, ClockIcon, PlusIcon } from 'lucide-react';
import { CreateBookingModal } from './AdminBookingsPage';
import { toast } from 'sonner';

const STATUS_COLORS = {
  confirmed: 'bg-blue-100 text-blue-700',
  checked_in: 'bg-green-100 text-green-700',
  checked_out: 'bg-gray-100 text-gray-600',
  cancelled: 'bg-red-100 text-red-600',
};

const StaffBookingsPage = () => {
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState('today');
  const [showCreate, setShowCreate] = useState(false);

  const fetchBookings = useCallback(async () => {
    setLoading(true);
    try {
      const now = new Date();
      const params = { limit: 100 };
      if (tab === 'today') {
        const start = new Date(now); start.setHours(0,0,0,0);
        const end = new Date(now); end.setHours(23,59,59,999);
        params.start_date = start.toISOString();
        params.end_date = end.toISOString();
      } else if (tab === 'week') {
        const end = new Date(now); end.setDate(end.getDate() + 7);
        params.start_date = now.toISOString();
        params.end_date = end.toISOString();
      } else if (tab === 'all') {
        params.start_date = now.toISOString();
        params.status = 'CONFIRMED';
      } else if (tab === 'past') {
        params.end_date = now.toISOString();
      } else if (tab === 'cancelled') {
        params.status = 'CANCELLED';
      }
      const res = await api.get('/bookings', { params });
      setBookings(res.data);
    } catch {
      toast.error('Failed to load bookings');
    } finally {
      setLoading(false);
    }
  }, [tab]);

  useEffect(() => {
    if (!user) { navigate('/auth'); return; }
    fetchBookings();
  }, [user, navigate, fetchBookings]);

  const nights = (b) => Math.ceil(
    (new Date(b.check_out_date) - new Date(b.check_in_date)) / (1000 * 60 * 60 * 24)
  );

  return (
    <div className="min-h-screen bg-[#F9F7F2]">
      <header className="bg-white border-b shadow-sm sticky top-0 z-10">
        <div className="max-w-3xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="sm" onClick={() => navigate(-1)}>
              <ArrowLeftIcon size={18} />
            </Button>
            <h1 className="text-lg font-serif font-bold text-primary">Bookings</h1>
          </div>
          {(user?.role !== 'customer') && (
            <Button size="sm" onClick={() => setShowCreate(true)}>
              <PlusIcon size={16} className="mr-1" /> New
            </Button>
          )}
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 py-6">
        <Tabs value={tab} onValueChange={setTab}>
          <TabsList className="w-full mb-6">
            <TabsTrigger value="today" className="flex-1">Today</TabsTrigger>
            <TabsTrigger value="week" className="flex-1">This Week</TabsTrigger>
            <TabsTrigger value="all" className="flex-1">Upcoming</TabsTrigger>
            <TabsTrigger value="past" className="flex-1">Past</TabsTrigger>
            <TabsTrigger value="cancelled" className="flex-1">Cancelled</TabsTrigger>
          </TabsList>

          <TabsContent value={tab}>
            {loading ? (
              <div className="flex justify-center py-12">
                <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-primary"></div>
              </div>
            ) : bookings.length === 0 ? (
              <Card><CardContent className="py-12 text-center text-muted-foreground">
                No bookings for this period
              </CardContent></Card>
            ) : (
              <div className="space-y-3">
                {bookings.map(b => (
                  <Card key={b.id} className="cursor-pointer hover:shadow-md transition-shadow" onClick={() => navigate(`/admin/bookings/${b.id}`)}>
                    <CardContent className="py-4 px-4">
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex items-start gap-3">
                          <div className="bg-primary/10 p-2 rounded-full mt-0.5">
                            <CalendarIcon size={14} className="text-primary" />
                          </div>
                          <div>
                            <div className="flex items-center gap-2 flex-wrap">
                              <p className="font-medium text-sm">
                                {new Date(b.check_in_date).toLocaleDateString(undefined, {month:'short', day:'numeric'})}
                                {' — '}
                                {new Date(b.check_out_date).toLocaleDateString(undefined, {month:'short', day:'numeric'})}
                              </p>
                              <Badge className={`text-xs ${STATUS_COLORS[b.status] || 'bg-gray-100 text-gray-600'}`}>
                                {b.status?.replace('_', ' ')}
                              </Badge>
                            </div>
                            <div className="flex items-center gap-3 mt-1.5">
                              <span className="flex items-center gap-1 text-xs text-muted-foreground">
                                <DogIcon size={11} />
                                {b.dog_ids?.length} dog{b.dog_ids?.length !== 1 ? 's' : ''}
                              </span>
                              <span className="flex items-center gap-1 text-xs text-muted-foreground">
                                <ClockIcon size={11} />
                                {nights(b)} night{nights(b) !== 1 ? 's' : ''}
                              </span>
                              <span className="text-xs text-muted-foreground">
                                In: {new Date(b.check_in_date).toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})}
                              </span>
                            </div>
                          </div>
                        </div>
                        {b.status === 'confirmed' && (
                          <Button size="sm" variant="outline" className="text-xs shrink-0"
                            onClick={() => navigate('/staff/check-in-out')}>
                            Check In
                          </Button>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </TabsContent>
        </Tabs>
      </main>
      {showCreate && (
        <CreateBookingModal
          onClose={() => setShowCreate(false)}
          onSuccess={() => { setShowCreate(false); fetchBookings(); toast.success('Booking created'); }}
        />
      )}
    </div>
  );
};

export default StaffBookingsPage;
