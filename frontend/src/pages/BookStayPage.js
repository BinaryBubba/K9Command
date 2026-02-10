import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/card';
import { Checkbox } from '../components/ui/checkbox';
import { Badge } from '../components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { 
  ArrowLeftIcon, 
  AlertCircleIcon, 
  CheckCircleIcon, 
  CalendarIcon,
  AlertTriangleIcon,
  ShowerHeadIcon,
  TagIcon,
  DogIcon,
  ClockIcon
} from 'lucide-react';
import { toast } from 'sonner';
import api from '../utils/api';

const BookStayPage = () => {
  const navigate = useNavigate();
  const [step, setStep] = useState(1); // 1: Details, 2: Review, 3: Payment
  const [loading, setLoading] = useState(false);
  const [dogs, setDogs] = useState([]);
  const [locations, setLocations] = useState([]);
  const [kennels, setKennels] = useState([]);
  const [availability, setAvailability] = useState(null);
  const [pricing, setPricing] = useState(null);
  const [eligibilityResults, setEligibilityResults] = useState(null);
  const [bookingResult, setBookingResult] = useState(null);
  
  const [formData, setFormData] = useState({
    dog_ids: [],
    location_id: '',
    kennel_id: '',
    accommodation_type: 'room',
    check_in_date: '',
    check_out_date: '',
    notes: '',
    special_request: '',
    needs_separate_playtime: false,
    bath_before_pickup: false,
    bath_day: 'checkout',
    coupon_code: '',
  });

  useEffect(() => {
    fetchInitialData();
  }, []);

  const fetchInitialData = async () => {
    try {
      const [dogsRes, locationsRes, kennelsRes] = await Promise.all([
        api.get('/dogs'),
        api.get('/locations'),
        api.get('/k9/kennels').catch(() => ({ data: [] })),
      ]);
      setDogs(dogsRes.data);
      setLocations(locationsRes.data);
      setKennels(kennelsRes.data.filter(k => k.status === 'available'));
      
      if (locationsRes.data.length > 0) {
        setFormData(prev => ({ ...prev, location_id: locationsRes.data[0].id }));
      }
    } catch (error) {
      toast.error('Failed to load data');
    }
  };

  const handleDogSelection = (dogId) => {
    const selected = formData.dog_ids.includes(dogId);
    if (selected) {
      setFormData({
        ...formData,
        dog_ids: formData.dog_ids.filter((id) => id !== dogId),
      });
    } else {
      // Auto-check separate playtime if dog is aggressive/unfriendly
      const dog = dogs.find(d => d.id === dogId);
      if (dog && (dog.friendly_with_dogs === false || dog.incidents_of_aggression)) {
        setFormData(prev => ({
          ...prev,
          dog_ids: [...prev.dog_ids, dogId],
          needs_separate_playtime: true
        }));
        toast.info(`${dog.name} requires separate playtime due to behavior profile`, { duration: 5000 });
      } else {
        setFormData({
          ...formData,
          dog_ids: [...formData.dog_ids, dogId],
        });
      }
    }
    // Reset eligibility when dogs change
    setEligibilityResults(null);
  };

  const calculateLocalPricing = () => {
    const checkIn = new Date(formData.check_in_date);
    const checkOut = new Date(formData.check_out_date);
    const nights = Math.ceil((checkOut - checkIn) / (1000 * 60 * 60 * 24));
    
    if (nights <= 0) return null;

    // Base pricing
    const basePrice = 50.0;
    let subtotal = basePrice * nights * formData.dog_ids.length;

    // Holiday check
    const holidays = ['2025-12-25', '2025-12-31', '2025-07-04', '2025-11-28'];
    const isHoliday = holidays.some(h => {
      const holiday = new Date(h);
      return checkIn <= holiday && holiday < checkOut;
    });

    if (isHoliday) {
      subtotal *= 1.20;
    }

    // Separate playtime fee
    let separatePlaytimeFee = 0;
    if (formData.needs_separate_playtime) {
      separatePlaytimeFee = 6 * nights;
      subtotal += separatePlaytimeFee;
    }

    // Bath fee
    let bathFee = 0;
    if (formData.bath_before_pickup) {
      bathFee = 25 * formData.dog_ids.length;
      subtotal += bathFee;
    }

    return {
      nights,
      basePrice,
      isHoliday,
      separatePlaytimeFee,
      bathFee,
      subtotal: subtotal.toFixed(2),
      total: subtotal.toFixed(2),
    };
  };

  const proceedToReview = async () => {
    if (formData.dog_ids.length === 0) {
      toast.error('Please select at least one dog');
      return;
    }
    if (!formData.check_in_date || !formData.check_out_date) {
      toast.error('Please select check-in and check-out dates');
      return;
    }
    if (!formData.location_id) {
      toast.error('Please select a location');
      return;
    }

    const pricingData = calculateLocalPricing();
    if (!pricingData) {
      toast.error('Invalid date range');
      return;
    }
    setPricing(pricingData);

    try {
      setLoading(true);
      const response = await api.get(`/locations/${formData.location_id}/availability`, {
        params: {
          check_in: formData.check_in_date,
          check_out: formData.check_out_date,
        },
      });
      setAvailability(response.data);
      setStep(2);
    } catch (error) {
      toast.error('Failed to check availability');
    } finally {
      setLoading(false);
    }
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

  const handleSmartBooking = async (paymentMethod) => {
    setLoading(true);
    try {
      // Use smart booking API with eligibility checks
      const bookingData = {
        dog_ids: formData.dog_ids,
        location_id: formData.location_id,
        kennel_id: formData.kennel_id || null,
        check_in_date: new Date(formData.check_in_date).toISOString(),
        check_out_date: new Date(formData.check_out_date).toISOString(),
        bath_before_pickup: formData.bath_before_pickup,
        bath_day: formData.bath_day,
        coupon_code: formData.coupon_code || null,
        notes: formData.notes,
      };

      const response = await api.post('/k9/bookings/smart', bookingData);
      const result = response.data;
      
      setBookingResult(result);
      setEligibilityResults(result.eligibility_results);

      if (result.auto_blocked) {
        // Booking was auto-blocked - show warning
        toast.warning('Your booking requires admin approval due to eligibility issues', {
          duration: 8000
        });
        setStep(4); // Go to blocked confirmation
      } else {
        // Booking confirmed - proceed to payment confirmation
        try {
          await api.post(`/bookings/${result.booking.id}/confirm-payment`, {
            payment_method: paymentMethod,
          });
          toast.success('Booking confirmed! Your stay has been reserved.');
          navigate('/customer/dashboard');
        } catch (payErr) {
          // Payment simulation might fail, but booking is created
          toast.success('Booking created! Payment will be collected at check-in.');
          navigate('/customer/dashboard');
        }
      }
    } catch (error) {
      console.error('Booking error:', error);
      toast.error(error.response?.data?.detail || 'Booking failed');
    } finally {
      setLoading(false);
    }
  };

  const getSelectedDogNames = () => {
    return dogs
      .filter(d => formData.dog_ids.includes(d.id))
      .map(d => d.name)
      .join(', ');
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
                    <p className="text-muted-foreground mb-4">You have not added any dogs yet.</p>
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
                          <div className="flex-1">
                            <h3 className="font-semibold text-lg">{dog.name}</h3>
                            <p className="text-sm text-muted-foreground">{dog.breed}</p>
                          </div>
                          {dog.incidents_of_aggression && (
                            <Badge variant="outline" className="text-amber-600 border-amber-300">
                              <AlertTriangleIcon size={12} className="mr-1" />
                              Special needs
                            </Badge>
                          )}
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
                        <p className="text-sm text-muted-foreground">Spacious kennel runs</p>
                      </div>
                      <div
                        data-testid="crate-option"
                        className={`p-4 rounded-xl border-2 cursor-pointer ${
                          formData.accommodation_type === 'crate' ? 'border-primary bg-primary/5' : 'border-border'
                        }`}
                        onClick={() => setFormData({ ...formData, accommodation_type: 'crate' })}
                      >
                        <h4 className="font-semibold">Crate</h4>
                        <p className="text-sm text-muted-foreground">Cozy indoor crates</p>
                      </div>
                    </div>
                  </div>
                  {kennels.length > 0 && (
                    <div className="md:col-span-2">
                      <Label>Preferred Kennel (Optional)</Label>
                      <Select value={formData.kennel_id || "auto"} onValueChange={(v) => setFormData({ ...formData, kennel_id: v === "auto" ? "" : v })}>
                        <SelectTrigger className="mt-1">
                          <SelectValue placeholder="Auto-assign available kennel" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="auto">Auto-assign</SelectItem>
                          {kennels.map(k => (
                            <SelectItem key={k.id} value={k.id}>
                              {k.name} ({k.kennel_type}, {k.size_category})
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Add-Ons & Services */}
            <Card data-testid="addons-card" className="mb-6 bg-white rounded-2xl border border-border/50 shadow-sm">
              <CardHeader className="border-b border-border/40">
                <CardTitle className="text-2xl font-serif">Add-Ons & Services</CardTitle>
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
                    <p className="text-sm text-muted-foreground">Due to dog aggression or special needs (+$6/day)</p>
                  </div>
                </div>
                
                {/* Bath Add-On */}
                <div className="border-t pt-4 mt-4">
                  <div className="flex items-start space-x-3">
                    <Checkbox
                      id="bath_before_pickup"
                      data-testid="bath-checkbox"
                      checked={formData.bath_before_pickup}
                      onCheckedChange={(checked) => setFormData({ ...formData, bath_before_pickup: checked })}
                    />
                    <div className="flex-1">
                      <Label htmlFor="bath_before_pickup" className="cursor-pointer flex items-center gap-2">
                        <ShowerHeadIcon size={16} className="text-cyan-600" />
                        Bath Before Pickup (+$25/dog)
                      </Label>
                      <p className="text-sm text-muted-foreground">Your pup will be clean and fresh when you pick them up</p>
                    </div>
                  </div>
                  
                  {formData.bath_before_pickup && (
                    <div className="ml-7 mt-3">
                      <Label className="text-sm">When should the bath be scheduled?</Label>
                      <div className="flex gap-3 mt-2">
                        <div
                          className={`px-4 py-2 rounded-lg border-2 cursor-pointer transition-all ${
                            formData.bath_day === 'checkout' ? 'border-cyan-500 bg-cyan-50' : 'border-border'
                          }`}
                          onClick={() => setFormData({ ...formData, bath_day: 'checkout' })}
                        >
                          <span className="text-sm font-medium">Day of Checkout</span>
                        </div>
                        <div
                          className={`px-4 py-2 rounded-lg border-2 cursor-pointer transition-all ${
                            formData.bath_day === 'day_before' ? 'border-cyan-500 bg-cyan-50' : 'border-border'
                          }`}
                          onClick={() => setFormData({ ...formData, bath_day: 'day_before' })}
                        >
                          <span className="text-sm font-medium">Day Before Checkout</span>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Coupon Code */}
            <Card data-testid="coupon-card" className="mb-6 bg-white rounded-2xl border border-border/50 shadow-sm">
              <CardHeader className="border-b border-border/40">
                <CardTitle className="text-xl font-serif flex items-center gap-2">
                  <TagIcon size={20} className="text-amber-600" />
                  Coupon Code
                </CardTitle>
              </CardHeader>
              <CardContent className="p-6">
                <div className="flex gap-3">
                  <Input
                    data-testid="coupon-input"
                    placeholder="Enter coupon code"
                    value={formData.coupon_code}
                    onChange={(e) => setFormData({ ...formData, coupon_code: e.target.value.toUpperCase() })}
                    className="flex-1"
                  />
                </div>
                <p className="text-xs text-muted-foreground mt-2">Coupon will be validated at checkout</p>
              </CardContent>
            </Card>

            {/* Notes */}
            <Card data-testid="notes-card" className="mb-6 bg-white rounded-2xl border border-border/50 shadow-sm">
              <CardHeader className="border-b border-border/40">
                <CardTitle className="text-xl font-serif">Additional Notes</CardTitle>
              </CardHeader>
              <CardContent className="p-6">
                <Textarea
                  id="notes"
                  data-testid="booking-notes-input"
                  value={formData.notes}
                  onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                  placeholder="Any special instructions or requests"
                  rows={4}
                />
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

            {/* Booking Summary */}
            <Card data-testid="summary-card" className="mb-6 bg-white rounded-2xl border border-border/50 shadow-sm">
              <CardHeader className="border-b border-border/40">
                <CardTitle className="text-2xl font-serif">Booking Summary</CardTitle>
              </CardHeader>
              <CardContent className="p-6 space-y-4">
                <div className="flex items-center gap-3">
                  <DogIcon className="text-primary" size={24} />
                  <div>
                    <p className="text-sm text-muted-foreground">Dogs</p>
                    <p className="font-semibold">{getSelectedDogNames()}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <CalendarIcon className="text-primary" size={24} />
                  <div>
                    <p className="text-sm text-muted-foreground">Dates</p>
                    <p className="font-semibold">{formData.check_in_date} → {formData.check_out_date} ({pricing.nights} nights)</p>
                  </div>
                </div>
                {formData.bath_before_pickup && (
                  <div className="flex items-center gap-3">
                    <ShowerHeadIcon className="text-cyan-600" size={24} />
                    <div>
                      <p className="text-sm text-muted-foreground">Bath Add-On</p>
                      <p className="font-semibold">
                        {formData.bath_day === 'checkout' ? 'Day of Checkout' : 'Day Before Checkout'}
                      </p>
                    </div>
                  </div>
                )}
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
                  {pricing.bathFee > 0 && (
                    <div className="flex justify-between text-cyan-600">
                      <span>Bath Before Pickup</span>
                      <span className="font-semibold">+${pricing.bathFee.toFixed(2)}</span>
                    </div>
                  )}
                  {formData.coupon_code && (
                    <div className="flex justify-between text-green-600">
                      <span>Coupon: {formData.coupon_code}</span>
                      <span className="font-semibold">Applied at checkout</span>
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
              <p className="text-sm text-muted-foreground mt-2">Your booking will be checked for eligibility before confirmation.</p>
            </CardHeader>
            <CardContent className="p-6 space-y-4">
              <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 flex items-start gap-3 mb-4">
                <AlertCircleIcon className="text-blue-600 flex-shrink-0 mt-1" size={20} />
                <div>
                  <p className="font-semibold text-blue-900">Smart Booking</p>
                  <p className="text-sm text-blue-800">We'll verify vaccination records and eligibility before confirming. If any issues are found, your booking will be submitted for admin review.</p>
                </div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Button
                  data-testid="pay-credit-card-button"
                  onClick={() => handleSmartBooking('credit_card')}
                  disabled={loading}
                  className="h-24 text-lg font-semibold"
                >
                  {loading ? 'Processing...' : 'Credit / Debit Card'}
                </Button>
                <Button
                  data-testid="pay-square-button"
                  onClick={() => handleSmartBooking('square')}
                  disabled={loading}
                  variant="outline"
                  className="h-24 text-lg font-semibold"
                >
                  {loading ? 'Processing...' : 'Square Payment'}
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Step 4: Booking Blocked - Awaiting Approval */}
        {step === 4 && bookingResult && (
          <Card data-testid="blocked-card" className="bg-white rounded-2xl border border-amber-200 shadow-sm">
            <CardHeader className="border-b border-amber-200 bg-amber-50">
              <CardTitle className="text-2xl font-serif flex items-center gap-2 text-amber-800">
                <AlertTriangleIcon size={28} />
                Booking Requires Review
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6 space-y-6">
              <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
                <p className="text-amber-900">
                  Your booking has been submitted but requires admin approval before it can be confirmed. 
                  You will receive a notification once it's been reviewed.
                </p>
              </div>

              {/* Show eligibility issues */}
              {eligibilityResults && eligibilityResults.some(r => r.errors?.length > 0) && (
                <div className="space-y-3">
                  <h4 className="font-semibold text-red-700 flex items-center gap-2">
                    <AlertCircleIcon size={18} />
                    Eligibility Issues Found:
                  </h4>
                  <div className="space-y-2">
                    {eligibilityResults.map((result, idx) => (
                      result.errors?.map((error, errIdx) => (
                        <div key={`${idx}-${errIdx}`} className="bg-red-50 border border-red-200 rounded-lg p-3">
                          <p className="text-red-800">
                            <strong>{error.dog_name}:</strong> {error.message}
                          </p>
                        </div>
                      ))
                    ))}
                  </div>
                </div>
              )}

              {/* Warnings */}
              {eligibilityResults && eligibilityResults.some(r => r.warnings?.length > 0) && (
                <div className="space-y-3">
                  <h4 className="font-semibold text-amber-700">Warnings:</h4>
                  <div className="space-y-2">
                    {eligibilityResults.map((result, idx) => (
                      result.warnings?.map((warning, warnIdx) => (
                        <div key={`w-${idx}-${warnIdx}`} className="bg-amber-50 border border-amber-200 rounded-lg p-3">
                          <p className="text-amber-800">{warning.message}</p>
                        </div>
                      ))
                    ))}
                  </div>
                </div>
              )}

              <div className="flex items-center gap-3 p-4 bg-slate-50 rounded-xl">
                <ClockIcon className="text-slate-500" size={24} />
                <div>
                  <p className="font-semibold">What happens next?</p>
                  <p className="text-sm text-muted-foreground">Our team will review your booking and contact you within 24 hours. You can check your notifications for updates.</p>
                </div>
              </div>

              <div className="flex justify-end gap-4">
                <Button variant="outline" onClick={() => navigate('/customer/dashboard')} className="rounded-full px-8">
                  Go to Dashboard
                </Button>
              </div>
            </CardContent>
          </Card>
        )}
      </main>
    </div>
  );
};

export default BookStayPage;
