import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { toast } from 'sonner';
import { 
  ArrowLeftIcon,
  CalendarIcon,
  HistoryIcon,
  CreditCardIcon,
  ReceiptIcon,
  DogIcon,
  RefreshCwIcon,
  RepeatIcon,
  HomeIcon,
  CheckCircleIcon,
  ClockIcon,
  AlertCircleIcon,
  ChevronRightIcon,
  DownloadIcon,
  BellIcon,
  BellRingIcon
} from 'lucide-react';
import api from '../utils/api';
import SavedCardsManager from '../components/SavedCardsManager';
import { Switch } from '../components/ui/switch';

const STATUS_COLORS = {
  confirmed: 'bg-green-500',
  pending_approval: 'bg-amber-500',
  checked_in: 'bg-blue-500',
  checked_out: 'bg-slate-500',
  completed: 'bg-slate-500',
  cancelled: 'bg-red-500'
};

export default function CustomerPortalPage() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('upcoming');
  const [upcoming, setUpcoming] = useState([]);
  const [history, setHistory] = useState([]);
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);
  
  // Rebook modal state
  const [showRebookModal, setShowRebookModal] = useState(false);
  const [rebookingFrom, setRebookingFrom] = useState(null);
  const [rebookCheckIn, setRebookCheckIn] = useState('');
  const [rebookCheckOut, setRebookCheckOut] = useState('');
  const [rebookLoading, setRebookLoading] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [upcomingRes, historyRes, invoicesRes] = await Promise.all([
        api.get('/moego/portal/upcoming'),
        api.get('/moego/portal/service-history'),
        api.get('/moego/portal/invoices')
      ]);
      
      setUpcoming(upcomingRes.data.upcoming || []);
      setHistory(historyRes.data.history || []);
      setInvoices(invoicesRes.data.invoices || []);
    } catch (error) {
      console.error('Failed to load portal data:', error);
      toast.error('Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const handleRebookClick = (booking) => {
    setRebookingFrom(booking);
    setRebookCheckIn('');
    setRebookCheckOut('');
    setShowRebookModal(true);
  };

  const handleRebook = async () => {
    if (!rebookCheckIn || !rebookCheckOut) {
      toast.error('Please select dates');
      return;
    }
    
    setRebookLoading(true);
    try {
      await api.post(`/moego/portal/rebook/${rebookingFrom.id}`, {
        check_in_date: new Date(rebookCheckIn).toISOString(),
        check_out_date: new Date(rebookCheckOut).toISOString()
      });
      
      toast.success('Booking created! Redirecting to your dashboard...');
      setShowRebookModal(false);
      navigate('/customer/dashboard');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create booking');
    } finally {
      setRebookLoading(false);
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '';
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    });
  };

  const formatCurrency = (cents) => {
    return `$${(cents / 100).toFixed(2)}`;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#F9F7F2] flex items-center justify-center">
        <div className="animate-spin h-8 w-8 border-2 border-primary border-t-transparent rounded-full"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#F9F7F2]" data-testid="customer-portal-page">
      {/* Header */}
      <header className="bg-white border-b border-border/40 shadow-sm px-6 py-4">
        <div className="max-w-6xl mx-auto">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => navigate('/customer/dashboard')}
              >
                <ArrowLeftIcon size={20} />
              </Button>
              <div>
                <h1 className="text-2xl font-serif font-bold text-primary">My Portal</h1>
                <p className="text-sm text-muted-foreground">Manage bookings, payments, and history</p>
              </div>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={loadData}
            >
              <RefreshCwIcon size={16} className="mr-2" />
              Refresh
            </Button>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-8">
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="bg-white border mb-6">
            <TabsTrigger value="upcoming" className="data-[state=active]:bg-primary data-[state=active]:text-white">
              <CalendarIcon size={16} className="mr-2" />
              Upcoming ({upcoming.length})
            </TabsTrigger>
            <TabsTrigger value="history" className="data-[state=active]:bg-primary data-[state=active]:text-white">
              <HistoryIcon size={16} className="mr-2" />
              History ({history.length})
            </TabsTrigger>
            <TabsTrigger value="payments" className="data-[state=active]:bg-primary data-[state=active]:text-white">
              <CreditCardIcon size={16} className="mr-2" />
              Payment Methods
            </TabsTrigger>
            <TabsTrigger value="invoices" className="data-[state=active]:bg-primary data-[state=active]:text-white">
              <ReceiptIcon size={16} className="mr-2" />
              Invoices ({invoices.length})
            </TabsTrigger>
          </TabsList>

          {/* Upcoming Bookings */}
          <TabsContent value="upcoming">
            <div className="space-y-4">
              {upcoming.length === 0 ? (
                <Card className="bg-white">
                  <CardContent className="py-12 text-center">
                    <CalendarIcon className="mx-auto text-slate-300 mb-4" size={48} />
                    <h3 className="text-lg font-medium mb-2">No Upcoming Bookings</h3>
                    <p className="text-muted-foreground mb-4">Ready to book your next stay?</p>
                    <Button onClick={() => navigate('/customer/book-stay')}>
                      Book a Stay
                    </Button>
                  </CardContent>
                </Card>
              ) : (
                upcoming.map(booking => (
                  <Card key={booking.id} className="bg-white" data-testid={`upcoming-${booking.id}`}>
                    <CardContent className="p-6">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-3 mb-3">
                            <Badge className={`${STATUS_COLORS[booking.status]} text-white`}>
                              {booking.status === 'pending_approval' ? 'Pending Review' : booking.status}
                            </Badge>
                            {booking.status === 'checked_in' && (
                              <Badge className="bg-blue-100 text-blue-700">Currently Staying</Badge>
                            )}
                          </div>
                          
                          {/* Dogs */}
                          <div className="flex items-center gap-2 mb-2">
                            <DogIcon className="text-primary" size={18} />
                            <span className="font-medium">
                              {booking.dogs?.map(d => d.name).join(', ') || 'Your pup'}
                            </span>
                          </div>
                          
                          {/* Dates */}
                          <div className="flex items-center gap-4 text-sm text-muted-foreground mb-2">
                            <span className="flex items-center gap-1">
                              <CalendarIcon size={14} />
                              {formatDate(booking.check_in_date)} → {formatDate(booking.check_out_date)}
                            </span>
                            <span>{booking.nights} night(s)</span>
                          </div>
                          
                          {/* Kennel */}
                          {booking.kennel && (
                            <div className="flex items-center gap-2 text-sm text-muted-foreground">
                              <HomeIcon size={14} />
                              {booking.kennel.name} ({booking.kennel.kennel_type})
                            </div>
                          )}
                          
                          {/* Price */}
                          <div className="mt-3">
                            <span className="text-lg font-semibold text-primary">
                              ${booking.total_price}
                            </span>
                            <span className="text-sm text-muted-foreground ml-2">
                              {booking.payment_status === 'paid' ? '(Paid)' : '(Due at checkout)'}
                            </span>
                          </div>
                        </div>
                        
                        <ChevronRightIcon className="text-slate-300" size={24} />
                      </div>
                    </CardContent>
                  </Card>
                ))
              )}
            </div>
          </TabsContent>

          {/* Service History */}
          <TabsContent value="history">
            <div className="space-y-4">
              {history.length === 0 ? (
                <Card className="bg-white">
                  <CardContent className="py-12 text-center">
                    <HistoryIcon className="mx-auto text-slate-300 mb-4" size={48} />
                    <h3 className="text-lg font-medium mb-2">No Past Stays</h3>
                    <p className="text-muted-foreground">Your completed bookings will appear here</p>
                  </CardContent>
                </Card>
              ) : (
                history.map(booking => (
                  <Card key={booking.id} className="bg-white" data-testid={`history-${booking.id}`}>
                    <CardContent className="p-6">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          {/* Dogs */}
                          <div className="flex items-center gap-2 mb-2">
                            <DogIcon className="text-primary" size={18} />
                            <span className="font-medium">
                              {booking.dogs?.map(d => d.name).join(', ') || 'Your pup'}
                            </span>
                          </div>
                          
                          {/* Dates */}
                          <div className="flex items-center gap-4 text-sm text-muted-foreground mb-2">
                            <span className="flex items-center gap-1">
                              <CalendarIcon size={14} />
                              {formatDate(booking.check_in_date)} → {formatDate(booking.check_out_date)}
                            </span>
                            <span>{booking.nights} night(s)</span>
                          </div>
                          
                          {/* Price */}
                          <div className="flex items-center gap-2">
                            <span className="font-semibold">${booking.total_price}</span>
                            <Badge className="bg-green-100 text-green-700">
                              <CheckCircleIcon size={12} className="mr-1" />
                              Completed
                            </Badge>
                          </div>
                        </div>
                        
                        {/* Rebook Button */}
                        <Button
                          variant="outline"
                          onClick={() => handleRebookClick(booking)}
                          className="flex items-center gap-2"
                        >
                          <RepeatIcon size={16} />
                          Book Again
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                ))
              )}
            </div>
          </TabsContent>

          {/* Payment Methods */}
          <TabsContent value="payments">
            <Card className="bg-white">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <CreditCardIcon className="text-primary" size={24} />
                  Saved Payment Methods
                </CardTitle>
                <CardDescription>
                  Manage your saved cards for faster checkout
                </CardDescription>
              </CardHeader>
              <CardContent className="p-6">
                <SavedCardsManager />
              </CardContent>
            </Card>
          </TabsContent>

          {/* Invoices */}
          <TabsContent value="invoices">
            <div className="space-y-4">
              {invoices.length === 0 ? (
                <Card className="bg-white">
                  <CardContent className="py-12 text-center">
                    <ReceiptIcon className="mx-auto text-slate-300 mb-4" size={48} />
                    <h3 className="text-lg font-medium mb-2">No Invoices Yet</h3>
                    <p className="text-muted-foreground">Your payment receipts will appear here</p>
                  </CardContent>
                </Card>
              ) : (
                invoices.map(invoice => (
                  <Card key={invoice.payment_id} className="bg-white" data-testid={`invoice-${invoice.payment_id}`}>
                    <CardContent className="p-6">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-3 mb-2">
                            <ReceiptIcon className="text-primary" size={20} />
                            <span className="font-medium">
                              {formatCurrency(invoice.amount_cents)}
                            </span>
                            <Badge className={invoice.status === 'COMPLETED' ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-700'}>
                              {invoice.status}
                            </Badge>
                          </div>
                          
                          {/* Dogs */}
                          {invoice.dog_names?.length > 0 && (
                            <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
                              <DogIcon size={14} />
                              {invoice.dog_names.join(', ')}
                            </div>
                          )}
                          
                          {/* Dates */}
                          {invoice.check_in_date && (
                            <div className="flex items-center gap-2 text-sm text-muted-foreground">
                              <CalendarIcon size={14} />
                              {formatDate(invoice.check_in_date)} → {formatDate(invoice.check_out_date)}
                            </div>
                          )}
                          
                          {/* Payment Date */}
                          <div className="text-xs text-muted-foreground mt-2">
                            <ClockIcon size={12} className="inline mr-1" />
                            Paid on {formatDate(invoice.created_at)}
                          </div>
                        </div>
                        
                        {/* Download Receipt */}
                        {invoice.receipt_url && (
                          <Button
                            variant="outline"
                            size="sm"
                            asChild
                          >
                            <a href={invoice.receipt_url} target="_blank" rel="noopener noreferrer">
                              <DownloadIcon size={14} className="mr-2" />
                              Receipt
                            </a>
                          </Button>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                ))
              )}
            </div>
          </TabsContent>
        </Tabs>
      </main>

      {/* Rebook Modal */}
      <Dialog open={showRebookModal} onOpenChange={setShowRebookModal}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <RepeatIcon size={20} className="text-primary" />
              Book Again
            </DialogTitle>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            {rebookingFrom && (
              <div className="bg-slate-50 rounded-lg p-4">
                <p className="text-sm text-muted-foreground mb-1">Rebooking for:</p>
                <p className="font-medium flex items-center gap-2">
                  <DogIcon size={16} className="text-primary" />
                  {rebookingFrom.dogs?.map(d => d.name).join(', ')}
                </p>
              </div>
            )}

            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="rebook-checkin">Check-In Date</Label>
                <Input
                  id="rebook-checkin"
                  type="date"
                  value={rebookCheckIn}
                  onChange={(e) => setRebookCheckIn(e.target.value)}
                  min={new Date().toISOString().split('T')[0]}
                  className="mt-1"
                />
              </div>
              <div>
                <Label htmlFor="rebook-checkout">Check-Out Date</Label>
                <Input
                  id="rebook-checkout"
                  type="date"
                  value={rebookCheckOut}
                  onChange={(e) => setRebookCheckOut(e.target.value)}
                  min={rebookCheckIn || new Date().toISOString().split('T')[0]}
                  className="mt-1"
                />
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowRebookModal(false)}>
              Cancel
            </Button>
            <Button onClick={handleRebook} disabled={rebookLoading}>
              {rebookLoading ? 'Creating...' : 'Create Booking'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
