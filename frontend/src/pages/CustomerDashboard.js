import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import useAuthStore from '../store/authStore';
import api from '../utils/api';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { LogOutIcon, DogIcon, CalendarIcon, PhoneIcon } from 'lucide-react';
import { toast } from 'sonner';

const CustomerDashboard = () => {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user) { navigate('/auth'); return; }
    // Customers see their own bookings via household
    api.get('/bookings', { params: { limit: 20 } })
      .then(r => setBookings(r.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [user, navigate]);

  const handleLogout = () => { logout(); navigate('/'); };

  const STATUS_COLORS = {
    confirmed: 'bg-blue-100 text-blue-700',
    checked_in: 'bg-green-100 text-green-700',
    checked_out: 'bg-gray-100 text-gray-600',
    cancelled: 'bg-red-100 text-red-600',
  };

  return (
    <div className="min-h-screen bg-[#F9F7F2]">
      <header className="bg-white border-b shadow-sm">
        <div className="max-w-2xl mx-auto px-4 py-3 flex justify-between items-center">
          <div>
            <h1 className="text-lg font-serif font-bold text-primary">K9 Country Club</h1>
            <p className="text-xs text-muted-foreground">Welcome, {user?.full_name}</p>
          </div>
          <Button variant="ghost" size="sm" onClick={handleLogout}>
            <LogOutIcon size={16} className="mr-1" /> Logout
          </Button>
        </div>
      </header>

      <main className="max-w-2xl mx-auto px-4 py-6 space-y-5">

        <Card>
          <CardContent className="py-6 text-center space-y-3">
            <div className="bg-primary/10 w-14 h-14 rounded-full flex items-center justify-center mx-auto">
              <DogIcon size={24} className="text-primary" />
            </div>
            <div>
              <p className="font-semibold">Need to make a reservation?</p>
              <p className="text-sm text-muted-foreground mt-1">Call us to book your dog's next stay</p>
            </div>
            <div className="flex items-center justify-center gap-2 text-primary font-medium">
              <PhoneIcon size={16} />
              <span>Contact K9 Country Club</span>
            </div>
          </CardContent>
        </Card>

        <div>
          <h2 className="text-sm font-semibold text-muted-foreground mb-3">Your Bookings</h2>
          {loading ? (
            <div className="flex justify-center py-8">
              <div className="animate-spin rounded-full h-6 w-6 border-t-2 border-b-2 border-primary"></div>
            </div>
          ) : bookings.length === 0 ? (
            <Card><CardContent className="py-8 text-center text-muted-foreground text-sm">
              No bookings on record
            </CardContent></Card>
          ) : (
            <div className="space-y-2">
              {bookings.map(b => (
                <Card key={b.id}>
                  <CardContent className="py-3 px-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <CalendarIcon size={16} className="text-muted-foreground" />
                        <div>
                          <p className="text-sm font-medium">
                            {new Date(b.check_in_date).toLocaleDateString()} — {new Date(b.check_out_date).toLocaleDateString()}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            {b.dog_ids?.length} dog{b.dog_ids?.length !== 1 ? 's' : ''}
                          </p>
                        </div>
                      </div>
                      <Badge className={`text-xs ${STATUS_COLORS[b.status] || 'bg-gray-100 text-gray-600'}`}>
                        {b.status?.replace('_', ' ')}
                      </Badge>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>

      </main>
    </div>
  );
};

export default CustomerDashboard;
