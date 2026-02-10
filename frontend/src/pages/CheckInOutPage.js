import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Textarea } from '../components/ui/textarea';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Checkbox } from '../components/ui/checkbox';
import { toast } from 'sonner';
import { 
  LogInIcon,
  LogOutIcon,
  ArrowLeftIcon,
  SearchIcon,
  DogIcon,
  CalendarIcon,
  HomeIcon,
  AlertTriangleIcon,
  CheckCircleIcon,
  XCircleIcon,
  ShieldAlertIcon,
  ShowerHeadIcon,
  ClockIcon,
  PhoneIcon,
  UserIcon
} from 'lucide-react';
import api from '../utils/api';

export default function CheckInOutPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('check-in');
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);
  
  const [checkIns, setCheckIns] = useState([]);
  const [checkOuts, setCheckOuts] = useState([]);
  const [kennels, setKennels] = useState([]);
  
  // Modal states
  const [showCheckInModal, setShowCheckInModal] = useState(false);
  const [showCheckOutModal, setShowCheckOutModal] = useState(false);
  const [selectedBooking, setSelectedBooking] = useState(null);
  const [eligibilityResult, setEligibilityResult] = useState(null);
  const [checkingEligibility, setCheckingEligibility] = useState(false);
  
  // Check-in form
  const [selectedKennel, setSelectedKennel] = useState('');
  const [checkInNotes, setCheckInNotes] = useState('');
  const [overrideEligibility, setOverrideEligibility] = useState(false);
  const [overrideReason, setOverrideReason] = useState('');
  
  // Check-out form
  const [bathCompleted, setBathCompleted] = useState(false);
  const [checkOutNotes, setCheckOutNotes] = useState('');

  useEffect(() => {
    loadData();
  }, [selectedDate]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [bookingsRes, kennelsRes] = await Promise.all([
        api.get('/bookings'),
        api.get('/moego/kennels?status=available')
      ]);
      
      const dateStr = selectedDate;
      const bookings = bookingsRes.data || [];
      
      // Filter check-ins (bookings with check_in_date matching selected date)
      const todayCheckIns = bookings.filter(b => {
        const checkInDate = b.check_in_date?.split('T')[0];
        return checkInDate === dateStr && b.status === 'confirmed';
      });
      
      // Filter check-outs (bookings with check_out_date matching selected date)
      const todayCheckOuts = bookings.filter(b => {
        const checkOutDate = b.check_out_date?.split('T')[0];
        return checkOutDate === dateStr && b.status === 'checked_in';
      });
      
      setCheckIns(todayCheckIns);
      setCheckOuts(todayCheckOuts);
      setKennels(kennelsRes.data || []);
    } catch (error) {
      console.error('Failed to load data:', error);
      toast.error('Failed to load bookings');
    } finally {
      setLoading(false);
    }
  };

  const checkEligibility = async (booking) => {
    setCheckingEligibility(true);
    setEligibilityResult(null);
    
    try {
      const results = [];
      for (const dogId of booking.dog_ids || []) {
        const response = await api.post(`/moego/eligibility/check?dog_id=${dogId}&location_id=main`);
        results.push(response.data);
      }
      setEligibilityResult(results);
    } catch (error) {
      console.error('Eligibility check failed:', error);
      setEligibilityResult([{ is_eligible: true, errors: [], warnings: [] }]);
    } finally {
      setCheckingEligibility(false);
    }
  };

  const handleCheckInClick = async (booking) => {
    setSelectedBooking(booking);
    setSelectedKennel(booking.kennel_id || '');
    setCheckInNotes('');
    setOverrideEligibility(false);
    setOverrideReason('');
    setShowCheckInModal(true);
    
    // Check eligibility
    await checkEligibility(booking);
  };

  const handleCheckOutClick = (booking) => {
    setSelectedBooking(booking);
    setBathCompleted(booking.bath_completed || false);
    setCheckOutNotes('');
    setShowCheckOutModal(true);
  };

  const processCheckIn = async () => {
    if (!selectedKennel) {
      toast.error('Please select a kennel');
      return;
    }
    
    const hasBlockingErrors = eligibilityResult?.some(r => !r.is_eligible && r.errors?.length > 0);
    
    if (hasBlockingErrors && !overrideEligibility) {
      toast.error('Please resolve eligibility issues or request admin override');
      return;
    }
    
    if (overrideEligibility && !overrideReason) {
      toast.error('Please provide a reason for override');
      return;
    }

    try {
      await api.patch(`/bookings/${selectedBooking.id}`, {
        status: 'checked_in',
        kennel_id: selectedKennel,
        check_in_notes: checkInNotes,
        eligibility_overridden: overrideEligibility,
        eligibility_override_reason: overrideReason,
        actual_check_in_time: new Date().toISOString()
      });
      
      // Update kennel status
      await api.patch(`/moego/kennels/${selectedKennel}`, {
        status: 'occupied',
        current_booking_id: selectedBooking.id,
        current_dog_ids: selectedBooking.dog_ids
      });
      
      toast.success('Check-in complete!');
      setShowCheckInModal(false);
      loadData();
    } catch (error) {
      toast.error('Check-in failed');
      console.error(error);
    }
  };

  const processCheckOut = async () => {
    try {
      await api.patch(`/bookings/${selectedBooking.id}`, {
        status: 'checked_out',
        bath_completed: bathCompleted,
        check_out_notes: checkOutNotes,
        actual_check_out_time: new Date().toISOString()
      });
      
      // Free up kennel
      if (selectedBooking.kennel_id) {
        await api.patch(`/moego/kennels/${selectedBooking.kennel_id}`, {
          status: 'cleaning',
          current_booking_id: null,
          current_dog_ids: []
        });
      }
      
      toast.success('Check-out complete!');
      setShowCheckOutModal(false);
      loadData();
    } catch (error) {
      toast.error('Check-out failed');
      console.error(error);
    }
  };

  const filteredCheckIns = checkIns.filter(b => 
    b.customer_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    b.dog_names?.some(n => n.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  const filteredCheckOuts = checkOuts.filter(b => 
    b.customer_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    b.dog_names?.some(n => n.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="animate-spin h-8 w-8 border-2 border-blue-500 border-t-transparent rounded-full"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950" data-testid="check-in-out-page">
      {/* Header */}
      <header className="bg-slate-900 border-b border-slate-700 px-6 py-4">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => navigate('/admin')}
                className="text-slate-400 hover:text-white"
              >
                <ArrowLeftIcon size={20} />
              </Button>
              <div>
                <h1 className="text-2xl font-bold text-white">Check-In / Check-Out</h1>
                <p className="text-slate-400 text-sm">Process arrivals and departures</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Input
                type="date"
                value={selectedDate}
                onChange={(e) => setSelectedDate(e.target.value)}
                className="bg-slate-800 border-slate-700 text-white w-40"
              />
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
          <Card className="bg-gradient-to-br from-emerald-600 to-emerald-700 border-none">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <LogInIcon className="text-white" size={28} />
                <div>
                  <p className="text-emerald-100 text-sm">Check-Ins Today</p>
                  <p className="text-3xl font-bold text-white">{checkIns.length}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-amber-600 to-amber-700 border-none">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <LogOutIcon className="text-white" size={28} />
                <div>
                  <p className="text-amber-100 text-sm">Check-Outs Today</p>
                  <p className="text-3xl font-bold text-white">{checkOuts.length}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Search */}
        <div className="relative mb-6">
          <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
          <Input
            placeholder="Search by customer or dog name..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-10 bg-slate-800 border-slate-700 text-white"
          />
        </div>

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="bg-slate-800 mb-6">
            <TabsTrigger value="check-in" className="data-[state=active]:bg-slate-700">
              <LogInIcon size={16} className="mr-2" />
              Check-Ins ({filteredCheckIns.length})
            </TabsTrigger>
            <TabsTrigger value="check-out" className="data-[state=active]:bg-slate-700">
              <LogOutIcon size={16} className="mr-2" />
              Check-Outs ({filteredCheckOuts.length})
            </TabsTrigger>
          </TabsList>

          {/* Check-Ins Tab */}
          <TabsContent value="check-in">
            {filteredCheckIns.length === 0 ? (
              <Card className="bg-slate-900 border-slate-700">
                <CardContent className="py-12 text-center">
                  <LogInIcon className="mx-auto text-slate-600 mb-4" size={48} />
                  <h3 className="text-lg font-semibold text-slate-400">No check-ins scheduled</h3>
                  <p className="text-slate-500">No arrivals scheduled for {selectedDate}</p>
                </CardContent>
              </Card>
            ) : (
              <div className="space-y-3">
                {filteredCheckIns.map(booking => (
                  <BookingCard 
                    key={booking.id}
                    booking={booking}
                    type="check-in"
                    onAction={() => handleCheckInClick(booking)}
                  />
                ))}
              </div>
            )}
          </TabsContent>

          {/* Check-Outs Tab */}
          <TabsContent value="check-out">
            {filteredCheckOuts.length === 0 ? (
              <Card className="bg-slate-900 border-slate-700">
                <CardContent className="py-12 text-center">
                  <LogOutIcon className="mx-auto text-slate-600 mb-4" size={48} />
                  <h3 className="text-lg font-semibold text-slate-400">No check-outs scheduled</h3>
                  <p className="text-slate-500">No departures scheduled for {selectedDate}</p>
                </CardContent>
              </Card>
            ) : (
              <div className="space-y-3">
                {filteredCheckOuts.map(booking => (
                  <BookingCard 
                    key={booking.id}
                    booking={booking}
                    type="check-out"
                    onAction={() => handleCheckOutClick(booking)}
                  />
                ))}
              </div>
            )}
          </TabsContent>
        </Tabs>
      </main>

      {/* Check-In Modal */}
      <Dialog open={showCheckInModal} onOpenChange={setShowCheckInModal}>
        <DialogContent className="bg-slate-900 border-slate-700 max-w-lg max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-white flex items-center gap-2">
              <LogInIcon size={20} className="text-emerald-400" />
              Process Check-In
            </DialogTitle>
          </DialogHeader>
          
          {selectedBooking && (
            <div className="space-y-4 py-4">
              {/* Booking Summary */}
              <div className="bg-slate-800 rounded-lg p-3">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-white font-medium">{selectedBooking.customer_name}</span>
                  <Badge className="bg-blue-500/20 text-blue-400">
                    {selectedBooking.dog_names?.length || 0} dog(s)
                  </Badge>
                </div>
                <div className="text-sm text-slate-400">
                  {selectedBooking.dog_names?.join(', ')}
                </div>
                <div className="text-xs text-slate-500 mt-1">
                  {new Date(selectedBooking.check_in_date).toLocaleDateString()} - {new Date(selectedBooking.check_out_date).toLocaleDateString()}
                </div>
              </div>

              {/* Eligibility Check */}
              <div className="border border-slate-700 rounded-lg p-3">
                <h4 className="text-white font-medium mb-3 flex items-center gap-2">
                  <ShieldAlertIcon size={16} />
                  Eligibility Check
                </h4>
                
                {checkingEligibility ? (
                  <div className="flex items-center gap-2 text-slate-400">
                    <div className="animate-spin h-4 w-4 border-2 border-blue-500 border-t-transparent rounded-full"></div>
                    Checking eligibility...
                  </div>
                ) : eligibilityResult ? (
                  <div className="space-y-2">
                    {eligibilityResult.map((result, idx) => (
                      <div key={idx} className={`p-2 rounded ${result.is_eligible ? 'bg-green-500/10' : 'bg-red-500/10'}`}>
                        <div className="flex items-center gap-2 mb-1">
                          {result.is_eligible ? (
                            <CheckCircleIcon size={16} className="text-green-400" />
                          ) : (
                            <XCircleIcon size={16} className="text-red-400" />
                          )}
                          <span className={result.is_eligible ? 'text-green-400' : 'text-red-400'}>
                            {result.dog_name}
                          </span>
                        </div>
                        
                        {result.errors?.map((err, i) => (
                          <div key={i} className="text-red-400 text-xs ml-6">
                            ⚠️ {err.message}
                          </div>
                        ))}
                        
                        {result.warnings?.map((warn, i) => (
                          <div key={i} className="text-amber-400 text-xs ml-6">
                            ⚡ {warn.message}
                          </div>
                        ))}
                        
                        {result.missing_vaccines?.length > 0 && (
                          <div className="text-red-400 text-xs ml-6">
                            Missing vaccines: {result.missing_vaccines.join(', ')}
                          </div>
                        )}
                      </div>
                    ))}
                    
                    {/* Override Option */}
                    {eligibilityResult.some(r => !r.is_eligible) && (
                      <div className="border-t border-slate-700 pt-3 mt-3">
                        <label className="flex items-center gap-2 cursor-pointer">
                          <Checkbox
                            checked={overrideEligibility}
                            onCheckedChange={setOverrideEligibility}
                          />
                          <span className="text-amber-400 text-sm">Request Admin Override</span>
                        </label>
                        
                        {overrideEligibility && (
                          <Textarea
                            value={overrideReason}
                            onChange={(e) => setOverrideReason(e.target.value)}
                            placeholder="Reason for override (required)..."
                            className="mt-2 bg-slate-800 border-slate-600 text-white text-sm"
                            rows={2}
                          />
                        )}
                      </div>
                    )}
                  </div>
                ) : null}
              </div>

              {/* Kennel Selection */}
              <div>
                <Label className="text-slate-300">Assign Kennel</Label>
                <Select value={selectedKennel} onValueChange={setSelectedKennel}>
                  <SelectTrigger className="mt-1 bg-slate-800 border-slate-600 text-white">
                    <SelectValue placeholder="Select kennel..." />
                  </SelectTrigger>
                  <SelectContent>
                    {kennels.map(k => (
                      <SelectItem key={k.id} value={k.id}>
                        {k.name} ({k.kennel_type}, {k.size_category})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Notes */}
              <div>
                <Label className="text-slate-300">Check-In Notes (Optional)</Label>
                <Textarea
                  value={checkInNotes}
                  onChange={(e) => setCheckInNotes(e.target.value)}
                  placeholder="Any notes about the check-in..."
                  className="mt-1 bg-slate-800 border-slate-600 text-white"
                  rows={2}
                />
              </div>
            </div>
          )}

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCheckInModal(false)} className="border-slate-600 text-slate-300">
              Cancel
            </Button>
            <Button 
              onClick={processCheckIn} 
              className="bg-emerald-600 hover:bg-emerald-700"
              disabled={!selectedKennel || (eligibilityResult?.some(r => !r.is_eligible) && !overrideEligibility)}
            >
              <LogInIcon size={16} className="mr-2" />
              Complete Check-In
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Check-Out Modal */}
      <Dialog open={showCheckOutModal} onOpenChange={setShowCheckOutModal}>
        <DialogContent className="bg-slate-900 border-slate-700 max-w-md">
          <DialogHeader>
            <DialogTitle className="text-white flex items-center gap-2">
              <LogOutIcon size={20} className="text-amber-400" />
              Process Check-Out
            </DialogTitle>
          </DialogHeader>
          
          {selectedBooking && (
            <div className="space-y-4 py-4">
              {/* Booking Summary */}
              <div className="bg-slate-800 rounded-lg p-3">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-white font-medium">{selectedBooking.customer_name}</span>
                  <Badge className="bg-blue-500/20 text-blue-400">
                    {selectedBooking.dog_names?.length || 0} dog(s)
                  </Badge>
                </div>
                <div className="text-sm text-slate-400">
                  {selectedBooking.dog_names?.join(', ')}
                </div>
                {selectedBooking.kennel_name && (
                  <div className="text-xs text-slate-500 mt-1 flex items-center gap-1">
                    <HomeIcon size={12} />
                    {selectedBooking.kennel_name}
                  </div>
                )}
              </div>

              {/* Bath Status */}
              {selectedBooking.bath_requested && (
                <div className="border border-slate-700 rounded-lg p-3">
                  <h4 className="text-white font-medium mb-2 flex items-center gap-2">
                    <ShowerHeadIcon size={16} className="text-cyan-400" />
                    Bath Service
                  </h4>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <Checkbox
                      checked={bathCompleted}
                      onCheckedChange={setBathCompleted}
                    />
                    <span className="text-slate-300">Bath completed</span>
                  </label>
                </div>
              )}

              {/* Notes */}
              <div>
                <Label className="text-slate-300">Check-Out Notes (Optional)</Label>
                <Textarea
                  value={checkOutNotes}
                  onChange={(e) => setCheckOutNotes(e.target.value)}
                  placeholder="Any notes about the check-out..."
                  className="mt-1 bg-slate-800 border-slate-600 text-white"
                  rows={2}
                />
              </div>
            </div>
          )}

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCheckOutModal(false)} className="border-slate-600 text-slate-300">
              Cancel
            </Button>
            <Button onClick={processCheckOut} className="bg-amber-600 hover:bg-amber-700">
              <LogOutIcon size={16} className="mr-2" />
              Complete Check-Out
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// Booking Card Component
function BookingCard({ booking, type, onAction }) {
  return (
    <Card className="bg-slate-900 border-slate-700 hover:border-slate-600 transition-colors">
      <CardContent className="p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${
              type === 'check-in' ? 'bg-emerald-500/20' : 'bg-amber-500/20'
            }`}>
              {type === 'check-in' ? (
                <LogInIcon className="text-emerald-400" size={24} />
              ) : (
                <LogOutIcon className="text-amber-400" size={24} />
              )}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-medium text-white">{booking.customer_name}</h3>
                {booking.check_in_slot?.time && (
                  <Badge variant="outline" className="border-slate-600 text-slate-400 text-xs">
                    <ClockIcon size={10} className="mr-1" />
                    {booking.check_in_slot.time}
                  </Badge>
                )}
              </div>
              <div className="flex items-center gap-2 text-sm text-slate-400">
                <DogIcon size={14} />
                {booking.dog_names?.join(', ') || `${booking.dog_ids?.length || 0} dog(s)`}
              </div>
              <div className="flex items-center gap-3 mt-1 text-xs text-slate-500">
                {booking.kennel_name && (
                  <span className="flex items-center gap-1">
                    <HomeIcon size={12} />
                    {booking.kennel_name}
                  </span>
                )}
                {booking.bath_requested && (
                  <Badge className={`text-xs ${booking.bath_completed ? 'bg-green-500/20 text-green-400' : 'bg-cyan-500/20 text-cyan-400'}`}>
                    <ShowerHeadIcon size={10} className="mr-1" />
                    {booking.bath_completed ? 'Bath Done' : 'Bath Requested'}
                  </Badge>
                )}
              </div>
            </div>
          </div>
          
          <Button
            onClick={onAction}
            className={type === 'check-in' ? 'bg-emerald-600 hover:bg-emerald-700' : 'bg-amber-600 hover:bg-amber-700'}
          >
            {type === 'check-in' ? 'Check In' : 'Check Out'}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
