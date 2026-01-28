import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { ArrowLeftIcon, CalendarIcon, SearchIcon, FilterIcon } from 'lucide-react';
import { toast } from 'sonner';
import api from '../utils/api';
import useAuthStore from '../store/authStore';

const AdminBookingsPage = () => {
  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);
  const [bookings, setBookings] = useState([]);
  const [filteredBookings, setFilteredBookings] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user || user.role !== 'admin') {
      navigate('/auth');
      return;
    }
    fetchBookings();
  }, [user, navigate]);

  useEffect(() => {
    filterBookings();
  }, [bookings, searchQuery, statusFilter]);

  const fetchBookings = async () => {
    try {
      const response = await api.get('/bookings');
      setBookings(response.data);
    } catch (error) {
      toast.error('Failed to load bookings');
    } finally {
      setLoading(false);
    }
  };

  const filterBookings = () => {
    let filtered = bookings;

    if (statusFilter !== 'all') {
      filtered = filtered.filter((b) => b.status === statusFilter);
    }

    if (searchQuery) {
      filtered = filtered.filter((b) =>
        b.id.toLowerCase().includes(searchQuery.toLowerCase())
      );
    }

    setFilteredBookings(filtered);
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'confirmed':
        return 'bg-blue-100 text-blue-800';
      case 'checked_in':
        return 'bg-green-100 text-green-800';
      case 'checked_out':
        return 'bg-gray-100 text-gray-800';
      case 'pending':
        return 'bg-yellow-100 text-yellow-800';
      case 'cancelled':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const statuses = ['all', 'pending', 'confirmed', 'checked_in', 'checked_out', 'cancelled'];

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
          <h1 className="text-3xl font-serif font-bold text-primary">Bookings Management</h1>
          <p className="text-muted-foreground mt-1">View and manage all reservations</p>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 md:px-8 py-8">
        {/* Filters */}
        <Card className="mb-6 bg-white rounded-2xl border border-border/50 shadow-sm">
          <CardContent className="p-6">
            <div className="flex flex-col md:flex-row gap-4">
              <div className="flex-1 relative">
                <SearchIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground" size={20} />
                <Input
                  placeholder="Search by booking ID..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10"
                />
              </div>
              <div className="flex gap-2 flex-wrap">
                {statuses.map((status) => (
                  <Button
                    key={status}
                    onClick={() => setStatusFilter(status)}
                    variant={statusFilter === status ? 'default' : 'outline'}
                    size="sm"
                    className="rounded-full capitalize"
                  >
                    {status}
                  </Button>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
          {statuses.filter(s => s !== 'all').map((status) => (
            <Card key={status} className="bg-white rounded-xl border border-border/50 shadow-sm">
              <CardContent className="p-4 text-center">
                <p className="text-xs text-muted-foreground uppercase tracking-wider mb-1 capitalize">{status}</p>
                <p className="text-2xl font-serif font-bold">
                  {bookings.filter(b => b.status === status).length}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Bookings List */}
        <div className="space-y-4">
          {filteredBookings.length === 0 ? (
            <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
              <CardContent className="p-12 text-center">
                <CalendarIcon size={48} className="mx-auto text-muted-foreground/50 mb-4" />
                <p className="text-muted-foreground">No bookings found</p>
              </CardContent>
            </Card>
          ) : (
            filteredBookings.map((booking) => (
              <Card key={booking.id} className="bg-white rounded-2xl border border-border/50 shadow-sm hover:shadow-md transition-all">
                <CardContent className="p-6">
                  <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <h3 className="text-lg font-semibold">Booking #{booking.id.slice(0, 8)}</h3>
                        <Badge className={getStatusColor(booking.status)}>
                          {booking.status.replace('_', ' ')}
                        </Badge>
                      </div>
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-2 text-sm text-muted-foreground">
                        <div>
                          <span className="font-medium">Check-in:</span> {new Date(booking.check_in_date).toLocaleDateString()}
                        </div>
                        <div>
                          <span className="font-medium">Check-out:</span> {new Date(booking.check_out_date).toLocaleDateString()}
                        </div>
                        <div>
                          <span className="font-medium">Dogs:</span> {booking.dog_ids.length}
                        </div>
                        <div>
                          <span className="font-medium">Type:</span> {booking.accommodation_type}
                        </div>
                        <div>
                          <span className="font-medium">Total:</span> ${booking.total_price}
                        </div>
                        <div>
                          <span className="font-medium">Payment:</span> {booking.payment_status}
                        </div>
                      </div>
                      {booking.notes && (
                        <p className="text-sm text-muted-foreground mt-2">
                          <span className="font-medium">Notes:</span> {booking.notes}
                        </p>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))
          )}
        </div>
      </main>
    </div>
  );
};

export default AdminBookingsPage;
