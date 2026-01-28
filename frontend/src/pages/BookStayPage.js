import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/card';
import { Checkbox } from '../components/ui/checkbox';
import { ArrowLeftIcon, AlertCircleIcon, CheckCircleIcon, CalendarIcon } from 'lucide-react';
import { toast } from 'sonner';
import api from '../utils/api';

const BookStayPage = () => {
  const navigate = useNavigate();
  const [step, setStep] = useState(1); // 1: Details, 2: Review, 3: Payment
  const [loading, setLoading] = useState(false);
  const [dogs, setDogs] = useState([]);
  const [locations, setLocations] = useState([]);
  const [availability, setAvailability] = useState(null);
  const [pricing, setPricing] = useState(null);
  
  const [formData, setFormData] = useState({
    dog_ids: [],
    location_id: '',
    accommodation_type: 'room',
    check_in_date: '',
    check_out_date: '',
    notes: '',
    special_request: '',
    needs_separate_playtime: false,
  });

  useEffect(() => {
    fetchInitialData();
  }, []);

  const fetchInitialData = async () => {
    try {
      const [dogsRes, locationsRes] = await Promise.all([
        api.get('/dogs'),
        api.get('/locations'),
      ]);
      setDogs(dogsRes.data);
      setLocations(locationsRes.data);
      
      if (locationsRes.data.length > 0) {
        setFormData(prev => ({ ...prev, location_id: locationsRes.data[0].id }));
      }
    } catch (error) {
      toast.error('Failed to load data');
    }
  };

  const checkAvailability = async () => {
    if (!formData.check_in_date || !formData.check_out_date || !formData.location_id) {
      toast.error('Please select dates and location');
      return;
    }

    try {
      setLoading(true);
      const response = await api.get(`/locations/${formData.location_id}/availability`, {
        params: {
          check_in: formData.check_in_date,
          check_out: formData.check_out_date,
        },
      });
      setAvailability(response.data);
      calculatePricing();
    } catch (error) {
      toast.error('Failed to check availability');
    } finally {
      setLoading(false);
    }
  };

  const calculatePricing = () => {
    const checkIn = new Date(formData.check_in_date);
    const checkOut = new Date(formData.check_out_date);
    const nights = Math.ceil((checkOut - checkIn) / (1000 * 60 * 60 * 24));
    
    if (nights <= 0) {
      toast.error('Invalid date range');
      return;
    }

    // Base pricing
    const basePrice = 50.0;
    let total = basePrice * nights * formData.dog_ids.length;

    // Holiday check (simplified)
    const holidays = ['2025-12-25', '2025-12-31', '2025-07-04', '2025-11-28'];
    const isHoliday = holidays.some(h => {
      const holiday = new Date(h);
      return checkIn <= holiday && holiday < checkOut;
    });

    if (isHoliday) {
      total *= 1.20; // 20% surcharge
    }

    // Separate playtime fee - $6 per day (not $25)
    let separatePlaytimeFee = 0;
    if (formData.needs_separate_playtime) {
      separatePlaytimeFee = 6 * nights;
      total += separatePlaytimeFee;
    }

    setPricing({
      nights,
      basePrice,
      isHoliday,
      separatePlaytimeFee,
      total: total.toFixed(2),
    });
  };

  const handleDogSelection = (dogId) => {
    const selected = formData.dog_ids.includes(dogId);
    if (selected) {
      setFormData({
        ...formData,
        dog_ids: formData.dog_ids.filter((id) => id !== dogId),
      });
    } else {
      setFormData({
        ...formData,
        dog_ids: [...formData.dog_ids, dogId],
      });
    }
  };

  const proceedToReview = () => {
    if (formData.dog_ids.length === 0) {
      toast.error('Please select at least one dog');
      return;
    }
    if (!formData.check_in_date || !formData.check_out_date) {
      toast.error('Please select check-in and check-out dates');
      return;
    }
    checkAvailability();
    setStep(2);
  };

  const proceedToPayment = () => {
    if (!availability) {
      toast.error('Please check availability first');
      return;
    }

    const available = formData.accommodation_type === 'room' 
      ? availability.rooms_available 
      : availability.crates_available;

    if (available <= 0) {
      toast.error('No availability for selected accommodation');
      return;
    }

    setStep(3);
  };

  const handlePayment = async (paymentMethod) => {
    setLoading(true);
    try {
      // Create booking
      const bookingResponse = await api.post('/bookings', {
        ...formData,
        check_in_date: new Date(formData.check_in_date).toISOString(),
        check_out_date: new Date(formData.check_out_date).toISOString(),
      });

      // Confirm payment (mocked)
      await api.post(`/bookings/${bookingResponse.data.id}/confirm-payment`, {
        payment_method: paymentMethod,
      });

      toast.success('Booking confirmed! Your stay has been reserved.');
      navigate('/customer/dashboard');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Booking failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#F9F7F2]">
      <header className="bg-white border-b border-border/40 shadow-sm">
        <div className="max-w-5xl mx-auto px-4 md:px-8 py-4">
          <Button
            variant="ghost"
            onClick={() => step === 1 ? navigate('/customer/dashboard') : setStep(step - 1)}
            className="flex items-center gap-2 mb-2"
          >
            <ArrowLeftIcon size={18} />
            {step === 1 ? 'Back to Dashboard' : 'Back'}
          </Button>
          <h1 className="text-3xl font-serif font-bold text-primary">Book a Stay</h1>
          <div className="flex items-center gap-4 mt-4">
            <div className={`flex items-center gap-2 ${step >= 1 ? 'text-primary' : 'text-muted-foreground'}`}>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center ${step >= 1 ? 'bg-primary text-white' : 'bg-muted'}`}>1</div>
              <span className="font-medium">Details</span>
            </div>
            <div className="h-px bg-border flex-1"></div>
            <div className={`flex items-center gap-2 ${step >= 2 ? 'text-primary' : 'text-muted-foreground'}`}>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center ${step >= 2 ? 'bg-primary text-white' : 'bg-muted'}`}>2</div>
              <span className="font-medium">Review</span>
            </div>
            <div className="h-px bg-border flex-1"></div>
            <div className={`flex items-center gap-2 ${step >= 3 ? 'text-primary' : 'text-muted-foreground'}`}>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center ${step >= 3 ? 'bg-primary text-white' : 'bg-muted'}`}>3</div>
              <span className="font-medium">Payment</span>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 md:px-8 py-8">
        {/* Step 1: Details */}
        {step === 1 && (
          <>
            {/* Select Dogs */}
            <Card data-testid="select-dogs-card" className="mb-6 bg-white rounded-2xl border border-border/50 shadow-sm">
              <CardHeader className="border-b border-border/40">
                <CardTitle className="text-2xl font-serif">Select Dogs</CardTitle>
              </CardHeader>
              <CardContent className="p-6">
                {dogs.length === 0 ? (
                  <div className="text-center py-8">
                    <p className="text-muted-foreground mb-4">You haven't added any dogs yet.</p>
                    <Button onClick={() => navigate('/customer/dogs/add')}>Add Your First Dog</Button>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {dogs.map((dog) => (
                      <div
                        key={dog.id}
                        data-testid={`dog-select-${dog.id}`}
                        className={`p-4 rounded-xl border-2 cursor-pointer transition-all ${
                          formData.dog_ids.includes(dog.id)
                            ? 'border-primary bg-primary/5'
                            : 'border-border hover:border-primary/50'
                        }`}
                        onClick={() => handleDogSelection(dog.id)}
                      >
                        <div className="flex items-center gap-4">
                          <Checkbox checked={formData.dog_ids.includes(dog.id)} />
                          <div>
                            <h3 className="font-semibold text-lg">{dog.name}</h3>
                            <p className="text-sm text-muted-foreground">{dog.breed}</p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Dates & Accommodation */}
            <Card data-testid="dates-accommodation-card" className="mb-6 bg-white rounded-2xl border border-border/50 shadow-sm">
              <CardHeader className="border-b border-border/40">
                <CardTitle className="text-2xl font-serif">Dates & Accommodation</CardTitle>
              </CardHeader>
              <CardContent className="p-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <Label htmlFor="check_in">Check-In Date</Label>
                    <Input
                      id="check_in"
                      data-testid="check-in-date-input"
                      type="date"
                      value={formData.check_in_date}
                      onChange={(e) => setFormData({ ...formData, check_in_date: e.target.value })}
                      min={new Date().toISOString().split('T')[0]}
                      className="mt-1"
                    />
                  </div>
                  <div>
                    <Label htmlFor="check_out">Check-Out Date</Label>
                    <Input
                      id="check_out"
                      data-testid="check-out-date-input"
                      type="date"
                      value={formData.check_out_date}
                      onChange={(e) => setFormData({ ...formData, check_out_date: e.target.value })}
                      min={formData.check_in_date || new Date().toISOString().split('T')[0]}
                      className="mt-1"
                    />
                  </div>
                  <div className="md:col-span-2">
                    <Label>Accommodation Type</Label>
                    <div className="grid grid-cols-2 gap-4 mt-2">
                      <div
                        data-testid="room-option"
                        className={`p-4 rounded-xl border-2 cursor-pointer ${
                          formData.accommodation_type === 'room' ? 'border-primary bg-primary/5' : 'border-border'
                        }`}
                        onClick={() => setFormData({ ...formData, accommodation_type: 'room' })}
                      >
                        <h4 className="font-semibold">Private Room</h4>
                        <p className="text-sm text-muted-foreground">7 available</p>
                      </div>
                      <div
                        data-testid="crate-option"
                        className={`p-4 rounded-xl border-2 cursor-pointer ${
                          formData.accommodation_type === 'crate' ? 'border-primary bg-primary/5' : 'border-border'
                        }`}
                        onClick={() => setFormData({ ...formData, accommodation_type: 'crate' })}
                      >
                        <h4 className="font-semibold">Crate</h4>
                        <p className="text-sm text-muted-foreground">4 available</p>
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Special Requirements */}
            <Card data-testid="special-requirements-card" className="mb-6 bg-white rounded-2xl border border-border/50 shadow-sm">
              <CardHeader className="border-b border-border/40">
                <CardTitle className="text-2xl font-serif">Special Requirements</CardTitle>
              </CardHeader>
              <CardContent className="p-6 space-y-4">
                <div className="flex items-start space-x-3">
                  <Checkbox
                    id="separate_playtime"
                    data-testid="separate-playtime-checkbox"
                    checked={formData.needs_separate_playtime}
                    onCheckedChange={(checked) => setFormData({ ...formData, needs_separate_playtime: checked })}
                  />
                  <div>
                    <Label htmlFor="separate_playtime" className="cursor-pointer">Separate Playtime Needed</Label>
                    <p className="text-sm text-muted-foreground">Due to dog aggression or special needs (+$25/day)</p>
                  </div>
                </div>
                <div>
                  <Label htmlFor="notes">Additional Notes</Label>
                  <Textarea
                    id="notes"
                    data-testid="booking-notes-input"
                    value={formData.notes}
                    onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                    placeholder="Any special instructions or requests"
                    className="mt-1"
                    rows={3}
                  />
                </div>
                <div>
                  <Label htmlFor="special_request">VIP Direct Request (for long-time customers)</Label>
                  <Textarea
                    id="special_request"
                    data-testid="special-request-input"
                    value={formData.special_request}
                    onChange={(e) => setFormData({ ...formData, special_request: e.target.value })}
                    placeholder="Special accommodation requests"
                    className="mt-1"
                    rows={2}
                  />
                </div>
              </CardContent>
            </Card>

            <div className="flex justify-end">
              <Button
                data-testid="proceed-to-review-button"
                onClick={proceedToReview}
                disabled={loading}
                className="rounded-full px-8 py-6 text-lg font-semibold"
              >
                Check Availability & Continue
              </Button>
            </div>
          </>
        )}

        {/* Step 2: Review */}
        {step === 2 && availability && pricing && (
          <>
            {/* Availability Status */}
            <Card data-testid="availability-card" className="mb-6 bg-white rounded-2xl border border-border/50 shadow-sm">
              <CardHeader className="border-b border-border/40">
                <CardTitle className="text-2xl font-serif flex items-center gap-2">
                  <CalendarIcon className="text-primary" />
                  Availability Status
                </CardTitle>
              </CardHeader>
              <CardContent className="p-6">
                <div className="grid grid-cols-2 gap-4">
                  <div className={`p-4 rounded-xl ${availability.rooms_available > 0 ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}`}>
                    <h4 className="font-semibold mb-1">Rooms Available</h4>
                    <p className="text-2xl font-bold">{availability.rooms_available} / {availability.total_rooms}</p>
                  </div>
                  <div className={`p-4 rounded-xl ${availability.crates_available > 0 ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}`}>
                    <h4 className="font-semibold mb-1">Crates Available</h4>
                    <p className="text-2xl font-bold">{availability.crates_available} / {availability.total_crates}</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Pricing Summary */}
            <Card data-testid="pricing-card" className="mb-6 bg-white rounded-2xl border border-border/50 shadow-sm">
              <CardHeader className="border-b border-border/40">
                <CardTitle className="text-2xl font-serif">Pricing Summary</CardTitle>
              </CardHeader>
              <CardContent className="p-6">
                <div className="space-y-3">
                  <div className="flex justify-between text-lg">
                    <span>{formData.dog_ids.length} dog(s) × {pricing.nights} night(s) × ${pricing.basePrice}</span>
                    <span className="font-semibold">${(pricing.basePrice * pricing.nights * formData.dog_ids.length).toFixed(2)}</span>
                  </div>
                  {pricing.isHoliday && (
                    <div className="flex justify-between text-orange-600">
                      <span>Holiday Surcharge (20%)</span>
                      <span className="font-semibold">+${((pricing.basePrice * pricing.nights * formData.dog_ids.length) * 0.20).toFixed(2)}</span>
                    </div>
                  )}
                  {pricing.separatePlaytimeFee > 0 && (
                    <div className="flex justify-between">
                      <span>Separate Playtime</span>
                      <span className="font-semibold">+${pricing.separatePlaytimeFee.toFixed(2)}</span>
                    </div>
                  )}
                  <div className="border-t pt-3 flex justify-between text-2xl font-bold text-primary">
                    <span>Total</span>
                    <span>${pricing.total}</span>
                  </div>
                </div>
              </CardContent>
            </Card>

            <div className="flex justify-end gap-4">
              <Button variant="outline" onClick={() => setStep(1)} className="rounded-full px-8">
                Edit Details
              </Button>
              <Button
                data-testid="proceed-to-payment-button"
                onClick={proceedToPayment}
                className="rounded-full px-8 py-6 text-lg font-semibold"
              >
                Proceed to Payment
              </Button>
            </div>
          </>
        )}

        {/* Step 3: Payment */}
        {step === 3 && (
          <Card data-testid="payment-card" className="bg-white rounded-2xl border border-border/50 shadow-sm">
            <CardHeader className="border-b border-border/40">
              <CardTitle className="text-2xl font-serif">Payment Method</CardTitle>
              <p className="text-sm text-muted-foreground mt-2">This is a simulated checkout. No real payment will be processed.</p>
            </CardHeader>
            <CardContent className="p-6 space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Button
                  data-testid="pay-credit-card-button"
                  onClick={() => handlePayment('credit_card')}
                  disabled={loading}
                  className="h-24 text-lg font-semibold"
                >
                  Credit / Debit Card
                </Button>
                <Button
                  data-testid="pay-square-button"
                  onClick={() => handlePayment('square')}
                  disabled={loading}
                  variant="outline"
                  className="h-24 text-lg font-semibold"
                >
                  Square Payment
                </Button>
              </div>
              <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 flex items-start gap-3">
                <AlertCircleIcon className="text-blue-600 flex-shrink-0 mt-1" size={20} />
                <div>
                  <p className="font-semibold text-blue-900">Payment Simulation</p>
                  <p className="text-sm text-blue-800">Clicking any payment method will create a confirmed booking without actual payment processing.</p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </main>
    </div>
  );
};

export default BookStayPage;
