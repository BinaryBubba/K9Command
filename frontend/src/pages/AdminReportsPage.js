import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/card';
import { ArrowLeftIcon, TrendingUpIcon, DollarSignIcon, UsersIcon, DogIcon } from 'lucide-react';
import { toast } from 'sonner';
import api from '../utils/api';
import useAuthStore from '../store/authStore';

const AdminReportsPage = () => {
  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);
  const [stats, setStats] = useState({});
  const [bookings, setBookings] = useState([]);
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
      const [statsRes, bookingsRes] = await Promise.all([
        api.get('/dashboard/stats'),
        api.get('/bookings'),
      ]);
      setStats(statsRes.data);
      setBookings(bookingsRes.data);
    } catch (error) {
      toast.error('Failed to load reports');
    } finally {
      setLoading(false);
    }
  };

  // Calculate revenue
  const totalRevenue = bookings.reduce((sum, b) => sum + (b.total_price || 0), 0);
  const confirmedRevenue = bookings
    .filter(b => b.status === 'confirmed' || b.status === 'checked_in' || b.status === 'checked_out')
    .reduce((sum, b) => sum + (b.total_price || 0), 0);

  // Calculate occupancy
  const totalCapacity = 11; // 7 rooms + 4 crates
  const currentOccupancy = stats.active_bookings || 0;
  const occupancyRate = ((currentOccupancy / totalCapacity) * 100).toFixed(1);

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
          <h1 className="text-3xl font-serif font-bold text-primary">Reports & Analytics</h1>
          <p className="text-muted-foreground mt-1">Business insights and performance metrics</p>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 md:px-8 py-8">
        {/* Revenue */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <Card className="bg-gradient-to-br from-green-500 to-green-600 text-white rounded-2xl shadow-lg">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm opacity-90 uppercase tracking-wider mb-1">Total Revenue</p>
                  <p className="text-3xl font-serif font-bold">${totalRevenue.toFixed(2)}</p>
                </div>
                <div className="w-12 h-12 rounded-full bg-white/20 flex items-center justify-center">
                  <DollarSignIcon size={24} />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-blue-500 to-blue-600 text-white rounded-2xl shadow-lg">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm opacity-90 uppercase tracking-wider mb-1">Confirmed Revenue</p>
                  <p className="text-3xl font-serif font-bold">${confirmedRevenue.toFixed(2)}</p>
                </div>
                <div className="w-12 h-12 rounded-full bg-white/20 flex items-center justify-center">
                  <TrendingUpIcon size={24} />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-purple-500 to-purple-600 text-white rounded-2xl shadow-lg">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm opacity-90 uppercase tracking-wider mb-1">Occupancy Rate</p>
                  <p className="text-3xl font-serif font-bold">{occupancyRate}%</p>
                  <p className="text-xs opacity-75 mt-1">{currentOccupancy} / {totalCapacity} spots</p>
                </div>
                <div className="w-12 h-12 rounded-full bg-white/20 flex items-center justify-center">
                  <DogIcon size={24} />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Business Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
            <CardContent className="p-6 text-center">
              <p className="text-sm text-muted-foreground uppercase tracking-wider mb-2">Total Customers</p>
              <p className="text-4xl font-serif font-bold text-primary">{stats.total_customers || 0}</p>
            </CardContent>
          </Card>

          <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
            <CardContent className="p-6 text-center">
              <p className="text-sm text-muted-foreground uppercase tracking-wider mb-2">Total Dogs</p>
              <p className="text-4xl font-serif font-bold text-secondary-foreground">{stats.total_dogs || 0}</p>
            </CardContent>
          </Card>

          <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
            <CardContent className="p-6 text-center">
              <p className="text-sm text-muted-foreground uppercase tracking-wider mb-2">Total Bookings</p>
              <p className="text-4xl font-serif font-bold text-primary">{stats.total_bookings || 0}</p>
            </CardContent>
          </Card>

          <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
            <CardContent className="p-6 text-center">
              <p className="text-sm text-muted-foreground uppercase tracking-wider mb-2">Avg Booking Value</p>
              <p className="text-4xl font-serif font-bold text-green-600">
                ${bookings.length > 0 ? (totalRevenue / bookings.length).toFixed(0) : 0}
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Recent Bookings Summary */}
        <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
          <CardHeader className="border-b border-border/40">
            <CardTitle className="text-2xl font-serif">Booking Status Breakdown</CardTitle>
          </CardHeader>
          <CardContent className="p-6">
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              {['pending', 'confirmed', 'checked_in', 'checked_out', 'cancelled'].map((status) => {
                const count = bookings.filter(b => b.status === status).length;
                const percentage = bookings.length > 0 ? ((count / bookings.length) * 100).toFixed(1) : 0;
                return (
                  <div key={status} className="text-center p-4 rounded-xl bg-muted/30">
                    <p className="text-2xl font-serif font-bold mb-1">{count}</p>
                    <p className="text-xs text-muted-foreground uppercase tracking-wider mb-1">{status}</p>
                    <p className="text-xs text-muted-foreground">{percentage}%</p>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      </main>
    </div>
  );
};

export default AdminReportsPage;
