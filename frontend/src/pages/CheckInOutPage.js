import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { Checkbox } from '../components/ui/checkbox';
import { Textarea } from '../components/ui/textarea';
import { toast } from 'sonner';
import { 
  ArrowLeftIcon,
  RefreshCwIcon,
  LogInIcon,
  LogOutIcon,
  DogIcon,
  PhoneIcon,
  CalendarIcon,
  HomeIcon,
  CheckCircleIcon,
  ClockIcon,
  ShowerHeadIcon,
  DollarSignIcon,
  AlertTriangleIcon,
  PillIcon,
  UserIcon
} from 'lucide-react';
import api from '../utils/api';

const ITEM_CHECKLIST = [
  { id: 'leash', label: 'Leash' },
  { id: 'collar', label: 'Collar' },
  { id: 'food', label: 'Food' },
  { id: 'bowl', label: 'Bowl' },
  { id: 'bed', label: 'Bed/Blanket' },
  { id: 'toys', label: 'Toys' },
  { id: 'medication', label: 'Medication' },
  { id: 'treats', label: 'Treats' },
];

export default function CheckInOutPage() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('check-ins');
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);
  const [checkIns, setCheckIns] = useState([]);
  const [checkOuts, setCheckOuts] = useState([]);
  const [bathsDue, setBathsDue] = useState([]);
  const [loading, setLoading] = useState(true);
  
  // Modal state
  const [showCheckInModal, setShowCheckInModal] = useState(false);
  const [showCheckOutModal, setShowCheckOutModal] = useState(false);
  const [selectedBooking, setSelectedBooking] = useState(null);
  const [checkInItems, setCheckInItems] = useState([]);
  const [checkInNotes, setCheckInNotes] = useState('');
  const [checkOutItems, setCheckOutItems] = useState([]);
  const [checkOutNotes, setCheckOutNotes] = useState('');
  const [paymentCollected, setPaymentCollected] = useState(false);
  const [skipBathCheck, setSkipBathCheck] = useState(false);

  useEffect(() => {
    loadData();
  }, [selectedDate]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [checkInsRes, checkOutsRes, bathsRes] = await Promise.all([
        api.get(`/k9/operations/check-ins?location_id=main&date=${selectedDate}`),
        api.get(`/k9/operations/check-outs?location_id=main&date=${selectedDate}`),
        api.get(`/k9/operations/baths-due?location_id=main&date=${selectedDate}`)
      ]);
      
      setCheckIns(checkInsRes.data);
      setCheckOuts(checkOutsRes.data);
      setBathsDue(bathsRes.data);
    } catch (error) {
      console.error('Failed to load data:', error);
      toast.error('Failed to load check-in/out data');
    } finally {
      setLoading(false);
    }
  };

  const handleCheckInClick = (booking) => {
    setSelectedBooking(booking);
    setCheckInItems(booking.items_received || []);
    setCheckInNotes('');
    setShowCheckInModal(true);
  };

  const handleCheckOutClick = (booking) => {
    setSelectedBooking(booking);
    setCheckOutItems(booking.items_received || []);
    setCheckOutNotes('');
    setPaymentCollected(booking.payment_status === 'paid');
    setSkipBathCheck(false);
    setShowCheckOutModal(true);
  };

  const performCheckIn = async () => {
    if (!selectedBooking) return;
    
    try {
      await api.post(`/k9/operations/check-in/${selectedBooking.booking_id}`, {
        notes: checkInNotes,
        items_received: checkInItems
      });
      
      toast.success(`${selectedBooking.customer_name} checked in successfully`);
      setShowCheckInModal(false);
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Check-in failed');
    }
  };

  const performCheckOut = async () => {
    if (!selectedBooking) return;
    
    try {
      await api.post(`/k9/operations/check-out/${selectedBooking.booking_id}`, {
        notes: checkOutNotes,
        items_returned: checkOutItems,
        payment_collected: paymentCollected,
        skip_bath_check: skipBathCheck
      });
      
      toast.success(`${selectedBooking.customer_name} checked out successfully`);
      setShowCheckOutModal(false);
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Check-out failed');
    }
  };

  const markBathComplete = async (bookingId) => {
    try {
      await api.post(`/k9/operations/bath/${bookingId}`);
      toast.success('Bath marked as completed');
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to mark bath complete');
    }
  };

  const toggleItem = (itemId, list, setList) => {
    if (list.includes(itemId)) {
      setList(list.filter(i => i !== itemId));
    } else {
      setList([...list, itemId]);
    }
  };

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
                onClick={() => navigate('/admin/dashboard')}
                className="text-slate-400 hover:text-white"
              >
                <ArrowLeftIcon size={20} />
              </Button>
              <div>
                <h1 className="text-2xl font-bold text-white">Check-In / Check-Out</h1>
                <p className="text-slate-400 text-sm">Manage arrivals and departures</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Input
                type="date"
                value={selectedDate}
                onChange={(e) => setSelectedDate(e.target.value)}
                className="bg-slate-800 border-slate-700 text-white w-40"
                data-testid="date-picker"
              />
              <Button
                variant="outline"
                size="sm"
                onClick={loadData}
                className="border-slate-600 text-slate-300"
              >
                <RefreshCwIcon size={16} />
              </Button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Quick Stats */}
        <div className="grid grid-cols-4 gap-4 mb-8">
          <Card className="bg-slate-900 border-slate-700">
            <CardContent className="p-4 flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-green-500/20 flex items-center justify-center">
                <LogInIcon className="text-green-400" size={20} />
              </div>
              <div>
                <p className="text-2xl font-bold text-white">{checkIns.filter(c => !c.checked_in).length}</p>
                <p className="text-xs text-slate-400">Pending Check-Ins</p>
              </div>
            </CardContent>
          </Card>
          
          <Card className="bg-slate-900 border-slate-700">
            <CardContent className="p-4 flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-amber-500/20 flex items-center justify-center">
                <LogOutIcon className="text-amber-400" size={20} />
              </div>
              <div>
                <p className="text-2xl font-bold text-white">{checkOuts.length}</p>
                <p className="text-xs text-slate-400">Pending Check-Outs</p>
              </div>
            </CardContent>
          </Card>
          
          <Card className="bg-slate-900 border-slate-700">
            <CardContent className="p-4 flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-cyan-500/20 flex items-center justify-center">
                <ShowerHeadIcon className="text-cyan-400" size={20} />
              </div>
              <div>
                <p className="text-2xl font-bold text-white">{bathsDue.length}</p>
                <p className="text-xs text-slate-400">Baths Due Today</p>
              </div>
            </CardContent>
          </Card>
          
          <Card className="bg-slate-900 border-slate-700">
            <CardContent className="p-4 flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-blue-500/20 flex items-center justify-center">
                <CheckCircleIcon className="text-blue-400" size={20} />
              </div>
              <div>
                <p className="text-2xl font-bold text-white">{checkIns.filter(c => c.checked_in).length}</p>
                <p className="text-xs text-slate-400">Completed Today</p>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="bg-slate-800 border border-slate-700 mb-6">
            <TabsTrigger value="check-ins" className="data-[state=active]:bg-green-600">
              <LogInIcon size={16} className="mr-2" />
              Check-Ins ({checkIns.length})
            </TabsTrigger>
            <TabsTrigger value="check-outs" className="data-[state=active]:bg-amber-600">
              <LogOutIcon size={16} className="mr-2" />
              Check-Outs ({checkOuts.length})
            </TabsTrigger>
            <TabsTrigger value="baths" className="data-[state=active]:bg-cyan-600">
              <ShowerHeadIcon size={16} className="mr-2" />
              Baths Due ({bathsDue.length})
            </TabsTrigger>
          </TabsList>

          {/* Check-Ins Tab */}
          <TabsContent value="check-ins">
            <div className="space-y-4">
              {checkIns.length === 0 ? (
                <Card className="bg-slate-900 border-slate-700">
                  <CardContent className="py-12 text-center">
                    <LogInIcon className="mx-auto text-slate-600 mb-4" size={48} />
                    <p className="text-slate-400">No check-ins scheduled for this date</p>
                  </CardContent>
                </Card>
              ) : (
                checkIns.map(booking => (
                  <Card 
                    key={booking.booking_id} 
                    className={`bg-slate-900 border-slate-700 ${booking.checked_in ? 'opacity-60' : ''}`}
                    data-testid={`checkin-card-${booking.booking_id}`}
                  >
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          {/* Customer Info */}
                          <div className="flex items-center gap-3 mb-3">
                            <div className="w-10 h-10 rounded-full bg-slate-700 flex items-center justify-center">
                              <UserIcon className="text-slate-400" size={20} />
                            </div>
                            <div>
                              <h3 className="text-white font-semibold">{booking.customer_name}</h3>
                              {booking.customer_phone && (
                                <p className="text-sm text-slate-400 flex items-center gap-1">
                                  <PhoneIcon size={12} />
                                  {booking.customer_phone}
                                </p>
                              )}
                            </div>
                            {booking.checked_in && (
                              <Badge className="bg-green-500/20 text-green-400 ml-2">
                                <CheckCircleIcon size={12} className="mr-1" />
                                Checked In
                              </Badge>
                            )}
                          </div>

                          {/* Dogs */}
                          <div className="flex flex-wrap gap-2 mb-3">
                            {booking.dogs.map(dog => (
                              <div key={dog.id} className="flex items-center gap-2 bg-slate-800 rounded-lg px-3 py-1.5">
                                <DogIcon size={14} className="text-slate-400" />
                                <span className="text-white text-sm">{dog.name}</span>
                                <span className="text-slate-500 text-xs">({dog.breed})</span>
                                {dog.weight && <span className="text-slate-500 text-xs">{dog.weight}lb</span>}
                              </div>
                            ))}
                          </div>

                          {/* Details */}
                          <div className="flex items-center gap-4 text-sm text-slate-400">
                            {booking.kennel_name && (
                              <span className="flex items-center gap-1">
                                <HomeIcon size={14} />
                                {booking.kennel_name}
                              </span>
                            )}
                            <span className="flex items-center gap-1">
                              <CalendarIcon size={14} />
                              Until {new Date(booking.check_out_date).toLocaleDateString()}
                            </span>
                            {booking.bath_scheduled && (
                              <Badge className="bg-cyan-500/20 text-cyan-400">
                                <ShowerHeadIcon size={12} className="mr-1" />
                                Bath ({booking.bath_day})
                              </Badge>
                            )}
                            {booking.special_needs?.length > 0 && (
                              <Badge className="bg-red-500/20 text-red-400">
                                <PillIcon size={12} className="mr-1" />
                                Medication
                              </Badge>
                            )}
                          </div>

                          {/* Payment Status */}
                          <div className="mt-3 flex items-center gap-2">
                            <Badge className={booking.payment_status === 'paid' ? 'bg-green-500/20 text-green-400' : 'bg-amber-500/20 text-amber-400'}>
                              <DollarSignIcon size={12} className="mr-1" />
                              ${booking.total_price} - {booking.payment_status}
                            </Badge>
                          </div>

                          {/* Notes */}
                          {booking.notes && (
                            <p className="mt-2 text-sm text-slate-500 italic">"{booking.notes}"</p>
                          )}
                        </div>

                        {/* Action Button */}
                        <Button
                          onClick={() => handleCheckInClick(booking)}
                          disabled={booking.checked_in}
                          className={booking.checked_in ? 'bg-slate-700' : 'bg-green-600 hover:bg-green-700'}
                          data-testid={`checkin-btn-${booking.booking_id}`}
                        >
                          {booking.checked_in ? 'Done' : 'Check In'}
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                ))
              )}
            </div>
          </TabsContent>

          {/* Check-Outs Tab */}
          <TabsContent value="check-outs">
            <div className="space-y-4">
              {checkOuts.length === 0 ? (
                <Card className="bg-slate-900 border-slate-700">
                  <CardContent className="py-12 text-center">
                    <LogOutIcon className="mx-auto text-slate-600 mb-4" size={48} />
                    <p className="text-slate-400">No check-outs scheduled for this date</p>
                  </CardContent>
                </Card>
              ) : (
                checkOuts.map(booking => (
                  <Card 
                    key={booking.booking_id} 
                    className="bg-slate-900 border-slate-700"
                    data-testid={`checkout-card-${booking.booking_id}`}
                  >
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          {/* Customer Info */}
                          <div className="flex items-center gap-3 mb-3">
                            <div className="w-10 h-10 rounded-full bg-slate-700 flex items-center justify-center">
                              <UserIcon className="text-slate-400" size={20} />
                            </div>
                            <div>
                              <h3 className="text-white font-semibold">{booking.customer_name}</h3>
                              {booking.customer_phone && (
                                <p className="text-sm text-slate-400 flex items-center gap-1">
                                  <PhoneIcon size={12} />
                                  {booking.customer_phone}
                                </p>
                              )}
                            </div>
                          </div>

                          {/* Dogs */}
                          <div className="flex flex-wrap gap-2 mb-3">
                            {booking.dogs.map(dog => (
                              <div key={dog.id} className="flex items-center gap-2 bg-slate-800 rounded-lg px-3 py-1.5">
                                <DogIcon size={14} className="text-slate-400" />
                                <span className="text-white text-sm">{dog.name}</span>
                                <span className="text-slate-500 text-xs">({dog.breed})</span>
                              </div>
                            ))}
                          </div>

                          {/* Details */}
                          <div className="flex items-center gap-4 text-sm text-slate-400">
                            {booking.kennel_name && (
                              <span className="flex items-center gap-1">
                                <HomeIcon size={14} />
                                {booking.kennel_name}
                              </span>
                            )}
                            {booking.bath_scheduled && (
                              <Badge className={booking.bath_completed ? 'bg-green-500/20 text-green-400' : 'bg-amber-500/20 text-amber-400'}>
                                <ShowerHeadIcon size={12} className="mr-1" />
                                Bath: {booking.bath_completed ? 'Done' : 'Pending'}
                              </Badge>
                            )}
                          </div>

                          {/* Balance Due */}
                          <div className="mt-3 flex items-center gap-2">
                            <Badge className={booking.payment_status === 'paid' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}>
                              <DollarSignIcon size={12} className="mr-1" />
                              {booking.payment_status === 'paid' ? 'Paid' : `Balance Due: $${booking.balance_due}`}
                            </Badge>
                          </div>
                        </div>

                        {/* Action Button */}
                        <Button
                          onClick={() => handleCheckOutClick(booking)}
                          className="bg-amber-600 hover:bg-amber-700"
                          data-testid={`checkout-btn-${booking.booking_id}`}
                        >
                          Check Out
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                ))
              )}
            </div>
          </TabsContent>

          {/* Baths Tab */}
          <TabsContent value="baths">
            <div className="space-y-4">
              {bathsDue.length === 0 ? (
                <Card className="bg-slate-900 border-slate-700">
                  <CardContent className="py-12 text-center">
                    <ShowerHeadIcon className="mx-auto text-slate-600 mb-4" size={48} />
                    <p className="text-slate-400">No baths due today</p>
                  </CardContent>
                </Card>
              ) : (
                bathsDue.map(bath => (
                  <Card 
                    key={bath.booking_id} 
                    className="bg-slate-900 border-slate-700"
                    data-testid={`bath-card-${bath.booking_id}`}
                  >
                    <CardContent className="p-4">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-4">
                          <div className="w-12 h-12 rounded-full bg-cyan-500/20 flex items-center justify-center">
                            <ShowerHeadIcon className="text-cyan-400" size={24} />
                          </div>
                          <div>
                            <h3 className="text-white font-semibold">{bath.customer_name}</h3>
                            <div className="flex flex-wrap gap-2 mt-1">
                              {bath.dogs.map(dog => (
                                <span key={dog.id} className="text-sm text-slate-400">
                                  {dog.name}
                                </span>
                              ))}
                            </div>
                            <div className="flex items-center gap-3 mt-2 text-xs text-slate-500">
                              <span className="flex items-center gap-1">
                                <HomeIcon size={12} />
                                {bath.kennel_name || 'No kennel'}
                              </span>
                              <span className="flex items-center gap-1">
                                <CalendarIcon size={12} />
                                Checkout: {new Date(bath.check_out_date).toLocaleDateString()}
                              </span>
                              <Badge className="bg-slate-700 text-slate-300">
                                {bath.bath_day === 'day_before' ? 'Day Before' : 'Checkout Day'}
                              </Badge>
                            </div>
                          </div>
                        </div>
                        <Button
                          onClick={() => markBathComplete(bath.booking_id)}
                          className="bg-cyan-600 hover:bg-cyan-700"
                          data-testid={`bath-complete-btn-${bath.booking_id}`}
                        >
                          <CheckCircleIcon size={16} className="mr-2" />
                          Mark Complete
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                ))
              )}
            </div>
          </TabsContent>
        </Tabs>
      </main>

      {/* Check-In Modal */}
      <Dialog open={showCheckInModal} onOpenChange={setShowCheckInModal}>
        <DialogContent className="bg-slate-900 border-slate-700 max-w-md">
          <DialogHeader>
            <DialogTitle className="text-white flex items-center gap-2">
              <LogInIcon size={20} className="text-green-400" />
              Check In: {selectedBooking?.customer_name}
            </DialogTitle>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            {/* Dogs Summary */}
            <div className="bg-slate-800 rounded-lg p-3">
              <h4 className="text-sm text-slate-400 mb-2">Dogs</h4>
              <div className="space-y-1">
                {selectedBooking?.dogs.map(dog => (
                  <div key={dog.id} className="flex items-center gap-2 text-white">
                    <DogIcon size={14} className="text-slate-500" />
                    {dog.name} ({dog.breed})
                  </div>
                ))}
              </div>
            </div>

            {/* Items Checklist */}
            <div>
              <h4 className="text-sm text-slate-400 mb-2">Items Received</h4>
              <div className="grid grid-cols-2 gap-2">
                {ITEM_CHECKLIST.map(item => (
                  <div key={item.id} className="flex items-center gap-2">
                    <Checkbox
                      id={`checkin-${item.id}`}
                      checked={checkInItems.includes(item.id)}
                      onCheckedChange={() => toggleItem(item.id, checkInItems, setCheckInItems)}
                    />
                    <label htmlFor={`checkin-${item.id}`} className="text-sm text-slate-300 cursor-pointer">
                      {item.label}
                    </label>
                  </div>
                ))}
              </div>
            </div>

            {/* Notes */}
            <div>
              <h4 className="text-sm text-slate-400 mb-2">Check-In Notes</h4>
              <Textarea
                value={checkInNotes}
                onChange={(e) => setCheckInNotes(e.target.value)}
                placeholder="Any notes about the check-in..."
                className="bg-slate-800 border-slate-700 text-white"
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCheckInModal(false)} className="border-slate-600 text-slate-300">
              Cancel
            </Button>
            <Button onClick={performCheckIn} className="bg-green-600 hover:bg-green-700">
              <CheckCircleIcon size={16} className="mr-2" />
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
              Check Out: {selectedBooking?.customer_name}
            </DialogTitle>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            {/* Bath Warning */}
            {selectedBooking?.bath_scheduled && !selectedBooking?.bath_completed && (
              <div className="bg-amber-500/20 border border-amber-500/50 rounded-lg p-3">
                <div className="flex items-center gap-2 text-amber-400 mb-2">
                  <AlertTriangleIcon size={16} />
                  <span className="font-medium">Bath Not Completed</span>
                </div>
                <p className="text-sm text-amber-300/80">
                  This booking has a bath scheduled that hasn't been completed.
                </p>
                <div className="flex items-center gap-2 mt-2">
                  <Checkbox
                    id="skip-bath"
                    checked={skipBathCheck}
                    onCheckedChange={setSkipBathCheck}
                  />
                  <label htmlFor="skip-bath" className="text-sm text-amber-300 cursor-pointer">
                    Skip bath check and proceed
                  </label>
                </div>
              </div>
            )}

            {/* Dogs Summary */}
            <div className="bg-slate-800 rounded-lg p-3">
              <h4 className="text-sm text-slate-400 mb-2">Dogs</h4>
              <div className="space-y-1">
                {selectedBooking?.dogs.map(dog => (
                  <div key={dog.id} className="flex items-center gap-2 text-white">
                    <DogIcon size={14} className="text-slate-500" />
                    {dog.name}
                  </div>
                ))}
              </div>
            </div>

            {/* Items Checklist */}
            <div>
              <h4 className="text-sm text-slate-400 mb-2">Items Returned</h4>
              <div className="grid grid-cols-2 gap-2">
                {ITEM_CHECKLIST.map(item => (
                  <div key={item.id} className="flex items-center gap-2">
                    <Checkbox
                      id={`checkout-${item.id}`}
                      checked={checkOutItems.includes(item.id)}
                      onCheckedChange={() => toggleItem(item.id, checkOutItems, setCheckOutItems)}
                    />
                    <label htmlFor={`checkout-${item.id}`} className="text-sm text-slate-300 cursor-pointer">
                      {item.label}
                    </label>
                  </div>
                ))}
              </div>
            </div>

            {/* Payment */}
            <div className="bg-slate-800 rounded-lg p-3">
              <div className="flex items-center justify-between mb-2">
                <span className="text-slate-400">Balance Due:</span>
                <span className="text-white font-semibold">${selectedBooking?.balance_due || selectedBooking?.total_price}</span>
              </div>
              <div className="flex items-center gap-2">
                <Checkbox
                  id="payment-collected"
                  checked={paymentCollected}
                  onCheckedChange={setPaymentCollected}
                />
                <label htmlFor="payment-collected" className="text-sm text-slate-300 cursor-pointer">
                  Payment collected
                </label>
              </div>
            </div>

            {/* Notes */}
            <div>
              <h4 className="text-sm text-slate-400 mb-2">Check-Out Notes</h4>
              <Textarea
                value={checkOutNotes}
                onChange={(e) => setCheckOutNotes(e.target.value)}
                placeholder="Any notes about the check-out..."
                className="bg-slate-800 border-slate-700 text-white"
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCheckOutModal(false)} className="border-slate-600 text-slate-300">
              Cancel
            </Button>
            <Button onClick={performCheckOut} className="bg-amber-600 hover:bg-amber-700">
              <CheckCircleIcon size={16} className="mr-2" />
              Complete Check-Out
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
