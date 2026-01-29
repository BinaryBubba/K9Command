import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { ArrowLeftIcon, TrendingUpIcon, TrendingDownIcon, DollarSignIcon, CalendarIcon, DogIcon, MoonIcon } from 'lucide-react';
import { toast } from 'sonner';
import api from '../utils/api';
import useAuthStore from '../store/authStore';
import { AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';

const AdminReportsPage = () => {
  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);
  const [stats, setStats] = useState({});
  const [bookings, setBookings] = useState([]);
  const [revenueSummary, setRevenueSummary] = useState(null);
  const [revenueTrends, setRevenueTrends] = useState([]);
  const [accommodationBreakdown, setAccommodationBreakdown] = useState(null);
  const [period, setPeriod] = useState('month');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user || user.role !== 'admin') {
      navigate('/auth');
      return;
    }
    fetchData();
  }, [user, navigate, period]);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [statsRes, bookingsRes, summaryRes, trendsRes, accommodationRes] = await Promise.all([
        api.get('/dashboard/stats'),
        api.get('/bookings'),
        api.get(`/admin/revenue/summary?period=${period}`),
        api.get(`/admin/revenue/trends?period=${period}`),
        api.get('/admin/revenue/by-accommodation'),
      ]);
      setStats(statsRes.data);
      setBookings(bookingsRes.data);
      setRevenueSummary(summaryRes.data);
      setRevenueTrends(trendsRes.data);
      setAccommodationBreakdown(accommodationRes.data);
    } catch (error) {
      toast.error('Failed to load reports');
    } finally {
      setLoading(false);
    }
  };

  // Calculate metrics
  const totalRevenue = bookings.reduce((sum, b) => sum + (b.total_price || 0), 0);
  const totalCapacity = 11;
  const currentOccupancy = stats.active_bookings || 0;
  const occupancyRate = ((currentOccupancy / totalCapacity) * 100).toFixed(1);

  // Pie chart data for accommodation
  const pieData = accommodationBreakdown ? [
    { name: 'Rooms', value: accommodationBreakdown.room?.revenue || 0, count: accommodationBreakdown.room?.count || 0 },
    { name: 'Crates', value: accommodationBreakdown.crate?.revenue || 0, count: accommodationBreakdown.crate?.count || 0 },
  ] : [];

  const COLORS = ['#22c55e', '#3b82f6'];

  const formatCurrency = (value) => `$${value.toLocaleString()}`;
  const formatDate = (dateStr) => {
    if (period === 'year') {
      const [year, month] = dateStr.split('-');
      return new Date(year, month - 1).toLocaleDateString('en-US', { month: 'short' });
    }
    return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

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
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-serif font-bold text-primary">Revenue Dashboard</h1>
              <p className="text-muted-foreground mt-1">Business insights and performance metrics</p>
            </div>
            <Select value={period} onValueChange={setPeriod}>
              <SelectTrigger data-testid="period-select" className="w-[140px]">
                <SelectValue placeholder="Select period" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="week">Last 7 Days</SelectItem>
                <SelectItem value="month">Last 30 Days</SelectItem>
                <SelectItem value="year">Last Year</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 md:px-8 py-8">
        {/* Revenue Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <Card data-testid="revenue-card" className="bg-gradient-to-br from-green-500 to-green-600 text-white rounded-2xl shadow-lg">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm opacity-90 uppercase tracking-wider mb-1">Revenue ({period})</p>
                  <p className="text-3xl font-serif font-bold">${revenueSummary?.current_revenue?.toLocaleString() || 0}</p>
                  {revenueSummary && (
                    <div className="flex items-center gap-1 mt-2 text-sm">
                      {revenueSummary.revenue_change_percent >= 0 ? (
                        <TrendingUpIcon size={16} />
                      ) : (
                        <TrendingDownIcon size={16} />
                      )}
                      <span>{revenueSummary.revenue_change_percent >= 0 ? '+' : ''}{revenueSummary.revenue_change_percent}%</span>
                      <span className="opacity-75">vs prev period</span>
                    </div>
                  )}
                </div>
                <div className="w-12 h-12 rounded-full bg-white/20 flex items-center justify-center">
                  <DollarSignIcon size={24} />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card data-testid="bookings-card" className="bg-gradient-to-br from-blue-500 to-blue-600 text-white rounded-2xl shadow-lg">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm opacity-90 uppercase tracking-wider mb-1">Bookings ({period})</p>
                  <p className="text-3xl font-serif font-bold">{revenueSummary?.total_bookings || 0}</p>
                  <p className="text-sm opacity-75 mt-2">
                    {revenueSummary?.prev_bookings || 0} prev period
                  </p>
                </div>
                <div className="w-12 h-12 rounded-full bg-white/20 flex items-center justify-center">
                  <CalendarIcon size={24} />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card data-testid="avg-stay-card" className="bg-gradient-to-br from-purple-500 to-purple-600 text-white rounded-2xl shadow-lg">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm opacity-90 uppercase tracking-wider mb-1">Avg Stay Duration</p>
                  <p className="text-3xl font-serif font-bold">{revenueSummary?.avg_stay_nights || 0} nights</p>
                </div>
                <div className="w-12 h-12 rounded-full bg-white/20 flex items-center justify-center">
                  <MoonIcon size={24} />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card data-testid="occupancy-card" className="bg-gradient-to-br from-amber-500 to-amber-600 text-white rounded-2xl shadow-lg">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm opacity-90 uppercase tracking-wider mb-1">Current Occupancy</p>
                  <p className="text-3xl font-serif font-bold">{occupancyRate}%</p>
                  <p className="text-sm opacity-75 mt-2">{currentOccupancy} / {totalCapacity} spots</p>
                </div>
                <div className="w-12 h-12 rounded-full bg-white/20 flex items-center justify-center">
                  <DogIcon size={24} />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Charts Row */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
          {/* Revenue Trend Chart */}
          <Card className="lg:col-span-2 bg-white rounded-2xl border border-border/50 shadow-sm">
            <CardHeader className="border-b border-border/40">
              <CardTitle className="text-xl font-serif">Revenue Trend</CardTitle>
            </CardHeader>
            <CardContent className="p-6">
              {revenueTrends.length > 0 ? (
                <ResponsiveContainer width="100%" height={300}>
                  <AreaChart data={revenueTrends}>
                    <defs>
                      <linearGradient id="colorRevenue" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#22c55e" stopOpacity={0.3}/>
                        <stop offset="95%" stopColor="#22c55e" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis 
                      dataKey="date" 
                      tickFormatter={formatDate}
                      tick={{ fontSize: 12 }}
                      stroke="#9ca3af"
                    />
                    <YAxis 
                      tickFormatter={(v) => `$${v}`}
                      tick={{ fontSize: 12 }}
                      stroke="#9ca3af"
                    />
                    <Tooltip 
                      formatter={(value) => [`$${value.toLocaleString()}`, 'Revenue']}
                      labelFormatter={formatDate}
                      contentStyle={{ borderRadius: '8px', border: '1px solid #e5e7eb' }}
                    />
                    <Area 
                      type="monotone" 
                      dataKey="revenue" 
                      stroke="#22c55e" 
                      strokeWidth={2}
                      fillOpacity={1} 
                      fill="url(#colorRevenue)" 
                    />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-[300px] flex items-center justify-center text-muted-foreground">
                  No revenue data for this period
                </div>
              )}
            </CardContent>
          </Card>

          {/* Accommodation Breakdown Pie Chart */}
          <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
            <CardHeader className="border-b border-border/40">
              <CardTitle className="text-xl font-serif">By Accommodation</CardTitle>
            </CardHeader>
            <CardContent className="p-6">
              {pieData.some(d => d.value > 0) ? (
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={pieData}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                      outerRadius={80}
                      fill="#8884d8"
                      dataKey="value"
                    >
                      {pieData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(value) => `$${value.toLocaleString()}`} />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-[300px] flex items-center justify-center text-muted-foreground">
                  No accommodation data available
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Bookings per Day Chart */}
        <Card className="bg-white rounded-2xl border border-border/50 shadow-sm mb-8">
          <CardHeader className="border-b border-border/40">
            <CardTitle className="text-xl font-serif">Daily Bookings</CardTitle>
          </CardHeader>
          <CardContent className="p-6">
            {revenueTrends.length > 0 ? (
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={revenueTrends}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis 
                    dataKey="date" 
                    tickFormatter={formatDate}
                    tick={{ fontSize: 12 }}
                    stroke="#9ca3af"
                  />
                  <YAxis 
                    tick={{ fontSize: 12 }}
                    stroke="#9ca3af"
                  />
                  <Tooltip 
                    labelFormatter={formatDate}
                    contentStyle={{ borderRadius: '8px', border: '1px solid #e5e7eb' }}
                  />
                  <Bar dataKey="bookings" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[250px] flex items-center justify-center text-muted-foreground">
                No booking data for this period
              </div>
            )}
          </CardContent>
        </Card>

        {/* Additional Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mb-8">
          <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
            <CardContent className="p-6 text-center">
              <p className="text-sm text-muted-foreground uppercase tracking-wider mb-2">Total Customers</p>
              <p className="text-3xl font-serif font-bold text-primary">{stats.total_customers || 0}</p>
            </CardContent>
          </Card>
          <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
            <CardContent className="p-6 text-center">
              <p className="text-sm text-muted-foreground uppercase tracking-wider mb-2">Total Dogs</p>
              <p className="text-3xl font-serif font-bold text-primary">{stats.total_dogs || 0}</p>
            </CardContent>
          </Card>
          <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
            <CardContent className="p-6 text-center">
              <p className="text-sm text-muted-foreground uppercase tracking-wider mb-2">All-Time Bookings</p>
              <p className="text-3xl font-serif font-bold text-primary">{stats.total_bookings || 0}</p>
            </CardContent>
          </Card>
          <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
            <CardContent className="p-6 text-center">
              <p className="text-sm text-muted-foreground uppercase tracking-wider mb-2">All-Time Revenue</p>
              <p className="text-3xl font-serif font-bold text-green-600">${totalRevenue.toLocaleString()}</p>
            </CardContent>
          </Card>
        </div>

        {/* Booking Status Breakdown */}
        <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
          <CardHeader className="border-b border-border/40">
            <CardTitle className="text-xl font-serif">Booking Status Breakdown</CardTitle>
          </CardHeader>
          <CardContent className="p-6">
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              {['pending', 'confirmed', 'checked_in', 'checked_out', 'cancelled'].map((status) => {
                const count = bookings.filter(b => b.status === status).length;
                const percentage = bookings.length > 0 ? ((count / bookings.length) * 100).toFixed(1) : 0;
                const colors = {
                  pending: 'bg-yellow-50 border-yellow-200',
                  confirmed: 'bg-blue-50 border-blue-200',
                  checked_in: 'bg-green-50 border-green-200',
                  checked_out: 'bg-gray-50 border-gray-200',
                  cancelled: 'bg-red-50 border-red-200',
                };
                return (
                  <div key={status} className={`text-center p-4 rounded-xl border ${colors[status]}`}>
                    <p className="text-2xl font-serif font-bold mb-1">{count}</p>
                    <p className="text-xs text-muted-foreground uppercase tracking-wider mb-1">{status.replace('_', ' ')}</p>
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
