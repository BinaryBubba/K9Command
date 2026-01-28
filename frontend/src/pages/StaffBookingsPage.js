import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/card';
import { Checkbox } from '../components/ui/checkbox';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { ArrowLeftIcon, CheckCircleIcon, DogIcon } from 'lucide-react';
import { toast } from 'sonner';
import api from '../utils/api';

const StaffBookingsPage = () => {
  const navigate = useNavigate();
  const [bookings, setBookings] = useState([]);
  const [selectedBooking, setSelectedBooking] = useState(null);
  const [dogs, setDogs] = useState([]);
  const [items, setItems] = useState({
    toys: false,
    bowls: false,
    food: false,
    blanket: false,
    medication: false,
    collar: false,
    leash: false,
    other_items: '',
  });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchBookings();
  }, []);

  const fetchBookings = async () => {
    try {
      const response = await api.get('/bookings');
      setBookings(response.data);
    } catch (error) {
      toast.error('Failed to load bookings');
    }
  };

  const selectBooking = async (booking) => {
    setSelectedBooking(booking);
    
    // Fetch dogs
    const dogPromises = booking.dog_ids.map((id) => api.get(`/dogs/${id}`));
    const dogResponses = await Promise.all(dogPromises);
    setDogs(dogResponses.map((r) => r.data));

    // Load items checklist if exists
    if (booking.items_checklist) {
      setItems(booking.items_checklist);
    }
  };

  const handleCheckIn = async () => {
    if (!selectedBooking) return;

    setLoading(true);
    try {
      await api.patch(`/bookings/${selectedBooking.id}/status?status=checked_in`);
      toast.success('Dogs checked in successfully!');
      fetchBookings();
      setSelectedBooking(null);
    } catch (error) {
      toast.error('Failed to check in');
    } finally {
      setLoading(false);
    }
  };

  const handleCheckOut = async () => {
    if (!selectedBooking) return;

    setLoading(true);
    try {
      // Update items checklist first
      await api.patch(`/bookings/${selectedBooking.id}/items`, items);
      
      // Then check out
      await api.patch(`/bookings/${selectedBooking.id}/status?status=checked_out`);
      toast.success('Dogs checked out successfully! All items returned.');
      fetchBookings();
      setSelectedBooking(null);
    } catch (error) {
      toast.error('Failed to check out');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveItems = async () => {
    if (!selectedBooking) return;

    try {
      await api.patch(`/bookings/${selectedBooking.id}/items`, items);
      toast.success('Items checklist saved');
    } catch (error) {
      toast.error('Failed to save items');
    }
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
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="min-h-screen bg-[#F9F7F2]">
      <header className="bg-white border-b border-border/40 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 md:px-8 py-4">
          <Button
            data-testid="back-to-dashboard-button"
            variant="ghost"
            onClick={() => navigate('/staff/dashboard')}
            className="flex items-center gap-2 mb-2"
          >
            <ArrowLeftIcon size={18} />
            Back to Dashboard
          </Button>
          <h1 className="text-3xl font-serif font-bold text-primary">Manage Bookings</h1>
          <p className="text-muted-foreground mt-1">Check in/out dogs and track their items</p>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 md:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Bookings List */}
          <Card data-testid="bookings-list-card" className="bg-white rounded-2xl border border-border/50 shadow-sm">
            <CardHeader className="border-b border-border/40">
              <CardTitle className="text-2xl font-serif">All Bookings</CardTitle>
            </CardHeader>
            <CardContent className="p-6">
              {bookings.length === 0 ? (
                <p className="text-center text-muted-foreground py-8">No bookings found</p>
              ) : (
                <div className="space-y-3">
                  {bookings.map((booking) => (
                    <div
                      key={booking.id}
                      data-testid={`booking-item-${booking.id}`}
                      className={`p-4 rounded-xl border-2 cursor-pointer transition-all ${
                        selectedBooking?.id === booking.id
                          ? 'border-primary bg-primary/5'
                          : 'border-border hover:border-primary/50'
                      }`}
                      onClick={() => selectBooking(booking)}
                    >
                      <div className="flex justify-between items-start mb-2">
                        <div>
                          <h3 className="font-semibold text-lg">Booking #{booking.id.slice(0, 8)}</h3>
                          <p className="text-sm text-muted-foreground">
                            {new Date(booking.check_in_date).toLocaleDateString()} - {new Date(booking.check_out_date).toLocaleDateString()}
                          </p>
                        </div>
                        <Badge className={getStatusColor(booking.status)}>
                          {booking.status.replace('_', ' ')}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-2 text-sm">
                        <DogIcon size={16} className="text-primary" />
                        <span>{booking.dog_ids.length} dog(s)</span>
                        <span className="text-muted-foreground">• {booking.accommodation_type}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Booking Details */}
          <div className="space-y-6">
            {selectedBooking ? (
              <>
                {/* Dog Details */}
                <Card data-testid="dogs-details-card" className="bg-white rounded-2xl border border-border/50 shadow-sm">
                  <CardHeader className="border-b border-border/40">
                    <CardTitle className="text-2xl font-serif">Dogs</CardTitle>
                  </CardHeader>
                  <CardContent className="p-6">
                    <div className="space-y-3">
                      {dogs.map((dog) => (
                        <div key={dog.id} className="p-4 rounded-xl bg-muted/50 border border-border">
                          <h4 className="font-semibold text-lg">{dog.name}</h4>
                          <p className="text-sm text-muted-foreground">{dog.breed} • {dog.age} years old</p>
                          {dog.medication_requirements && (
                            <p className="text-sm mt-2">
                              <span className="font-medium text-orange-600">Medication:</span> {dog.medication_requirements}
                            </p>
                          )}
                          {dog.allergies && (
                            <p className="text-sm mt-1">
                              <span className="font-medium text-red-600">Allergies:</span> {dog.allergies}
                            </p>
                          )}
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>

                {/* Items Checklist */}
                <Card data-testid="items-checklist-card" className="bg-white rounded-2xl border border-border/50 shadow-sm">
                  <CardHeader className="border-b border-border/40">
                    <CardTitle className="text-2xl font-serif">Items Checklist</CardTitle>
                    <p className="text-sm text-muted-foreground mt-1">Track items left with the dogs</p>
                  </CardHeader>
                  <CardContent className="p-6 space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      {Object.keys(items)
                        .filter((key) => key !== 'other_items')
                        .map((key) => (
                          <div key={key} className="flex items-center space-x-3">
                            <Checkbox
                              id={key}
                              data-testid={`item-${key}`}
                              checked={items[key]}
                              onCheckedChange={(checked) => setItems({ ...items, [key]: checked })}
                            />
                            <Label htmlFor={key} className="cursor-pointer capitalize">
                              {key.replace('_', ' ')}
                            </Label>
                          </div>
                        ))}
                    </div>
                    <div>
                      <Label htmlFor="other_items">Other Items</Label>
                      <textarea
                        id="other_items"
                        data-testid="other-items-input"
                        value={items.other_items}
                        onChange={(e) => setItems({ ...items, other_items: e.target.value })}
                        placeholder="List any other items..."
                        className="w-full mt-1 p-2 border rounded-xl"
                        rows={2}
                      />
                    </div>
                    <Button
                      data-testid="save-items-button"
                      onClick={handleSaveItems}
                      variant="outline"
                      className="w-full rounded-full"
                    >
                      Save Items
                    </Button>
                  </CardContent>
                </Card>

                {/* Actions */}
                <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
                  <CardContent className="p-6">
                    {selectedBooking.status === 'confirmed' && (
                      <Button
                        data-testid="check-in-button"
                        onClick={handleCheckIn}
                        disabled={loading}
                        className="w-full py-6 text-lg font-semibold rounded-full bg-green-600 hover:bg-green-700"
                      >
                        <CheckCircleIcon size={20} className="mr-2" />
                        Check In
                      </Button>
                    )}
                    {selectedBooking.status === 'checked_in' && (
                      <Button
                        data-testid="check-out-button"
                        onClick={handleCheckOut}
                        disabled={loading}
                        className="w-full py-6 text-lg font-semibold rounded-full"
                      >
                        <CheckCircleIcon size={20} className="mr-2" />
                        Check Out
                      </Button>
                    )}
                    {selectedBooking.status === 'checked_out' && (
                      <div className="text-center py-4">
                        <CheckCircleIcon size={48} className="mx-auto text-green-600 mb-2" />
                        <p className="font-semibold text-lg">Checked Out</p>
                      </div>
                    )}
                  </CardContent>
                </Card>
              </>
            ) : (
              <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
                <CardContent className="p-12 text-center">
                  <DogIcon size={48} className="mx-auto text-muted-foreground/50 mb-4" />
                  <p className="text-muted-foreground">Select a booking to view details</p>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </main>
    </div>
  );
};

export default StaffBookingsPage;
