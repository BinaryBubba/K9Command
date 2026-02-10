import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { Textarea } from '../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { toast } from 'sonner';
import { 
  ArrowLeftIcon,
  RefreshCwIcon,
  CheckCircleIcon,
  XCircleIcon,
  DogIcon,
  CalendarIcon,
  AlertTriangleIcon,
  UserIcon,
  HomeIcon,
  ClockIcon
} from 'lucide-react';
import api from '../utils/api';

export default function BookingApprovalPage() {
  const navigate = useNavigate();
  const [pendingBookings, setPendingBookings] = useState([]);
  const [kennels, setKennels] = useState([]);
  const [loading, setLoading] = useState(true);
  
  // Modal state
  const [showApproveModal, setShowApproveModal] = useState(false);
  const [showRejectModal, setShowRejectModal] = useState(false);
  const [selectedBooking, setSelectedBooking] = useState(null);
  const [selectedKennel, setSelectedKennel] = useState('');
  const [approvalNotes, setApprovalNotes] = useState('');
  const [rejectionReason, setRejectionReason] = useState('');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [bookingsRes, kennelsRes] = await Promise.all([
        api.get('/k9/bookings/pending-approval'),
        api.get('/k9/kennels')
      ]);
      
      setPendingBookings(bookingsRes.data);
      setKennels(kennelsRes.data.filter(k => k.status === 'available'));
    } catch (error) {
      console.error('Failed to load data:', error);
      toast.error('Failed to load pending bookings');
    } finally {
      setLoading(false);
    }
  };

  const handleApproveClick = (booking) => {
    setSelectedBooking(booking);
    setSelectedKennel(booking.kennel_id || '');
    setApprovalNotes('');
    setShowApproveModal(true);
  };

  const handleRejectClick = (booking) => {
    setSelectedBooking(booking);
    setRejectionReason('');
    setShowRejectModal(true);
  };

  const approveBooking = async () => {
    if (!selectedBooking) return;
    
    try {
      await api.post(`/k9/bookings/${selectedBooking.id}/approve`, null, {
        params: {
          kennel_id: selectedKennel || undefined,
          notes: approvalNotes || undefined
        }
      });
      
      toast.success('Booking approved successfully');
      setShowApproveModal(false);
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to approve booking');
    }
  };

  const rejectBooking = async () => {
    if (!selectedBooking || !rejectionReason.trim()) {
      toast.error('Please provide a rejection reason');
      return;
    }
    
    try {
      await api.post(`/k9/bookings/${selectedBooking.id}/reject`, null, {
        params: { reason: rejectionReason }
      });
      
      toast.success('Booking rejected');
      setShowRejectModal(false);
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to reject booking');
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
    <div className="min-h-screen bg-slate-950" data-testid="booking-approval-page">
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
                <h1 className="text-2xl font-bold text-white">Booking Approvals</h1>
                <p className="text-slate-400 text-sm">Review blocked bookings requiring admin approval</p>
              </div>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={loadData}
              className="border-slate-600 text-slate-300"
            >
              <RefreshCwIcon size={16} className="mr-2" />
              Refresh
            </Button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Stats */}
        <Card className="bg-amber-500/10 border-amber-500/30 mb-8">
          <CardContent className="p-4 flex items-center gap-3">
            <AlertTriangleIcon className="text-amber-400" size={24} />
            <div>
              <p className="text-white font-semibold">{pendingBookings.length} Booking(s) Pending Approval</p>
              <p className="text-sm text-slate-400">These bookings were auto-blocked due to eligibility check failures</p>
            </div>
          </CardContent>
        </Card>

        {/* Pending Bookings List */}
        <div className="space-y-4">
          {pendingBookings.length === 0 ? (
            <Card className="bg-slate-900 border-slate-700">
              <CardContent className="py-12 text-center">
                <CheckCircleIcon className="mx-auto text-green-500 mb-4" size={48} />
                <h3 className="text-lg font-semibold text-white">All Clear!</h3>
                <p className="text-slate-400">No bookings pending approval</p>
              </CardContent>
            </Card>
          ) : (
            pendingBookings.map(booking => (
              <Card 
                key={booking.id} 
                className="bg-slate-900 border-slate-700 border-l-4 border-l-amber-500"
                data-testid={`approval-card-${booking.id}`}
              >
                <CardContent className="p-6">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      {/* Customer & Dogs */}
                      <div className="flex items-center gap-3 mb-4">
                        <div className="w-12 h-12 rounded-full bg-slate-700 flex items-center justify-center">
                          <UserIcon className="text-slate-400" size={24} />
                        </div>
                        <div>
                          <h3 className="text-white font-semibold text-lg">{booking.customer_name || 'Unknown Customer'}</h3>
                          <p className="text-sm text-slate-400">{booking.customer_email}</p>
                        </div>
                      </div>

                      {/* Dogs */}
                      <div className="flex flex-wrap gap-2 mb-4">
                        {booking.dog_names?.map((name, i) => (
                          <Badge key={i} className="bg-slate-800 text-white">
                            <DogIcon size={12} className="mr-1" />
                            {name}
                          </Badge>
                        ))}
                      </div>

                      {/* Booking Details */}
                      <div className="grid grid-cols-2 gap-4 text-sm mb-4">
                        <div className="flex items-center gap-2 text-slate-400">
                          <CalendarIcon size={14} />
                          <span>Check-in: {new Date(booking.check_in_date).toLocaleDateString()}</span>
                        </div>
                        <div className="flex items-center gap-2 text-slate-400">
                          <CalendarIcon size={14} />
                          <span>Check-out: {new Date(booking.check_out_date).toLocaleDateString()}</span>
                        </div>
                        <div className="flex items-center gap-2 text-slate-400">
                          <ClockIcon size={14} />
                          <span>{booking.nights} night(s)</span>
                        </div>
                        <div className="flex items-center gap-2 text-slate-400">
                          <span className="font-semibold text-white">${booking.total_price}</span>
                        </div>
                      </div>

                      {/* Eligibility Errors */}
                      {booking.eligibility_errors?.length > 0 && (
                        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 mb-4">
                          <h4 className="text-red-400 font-medium mb-2 flex items-center gap-2">
                            <AlertTriangleIcon size={16} />
                            Eligibility Issues (Auto-Blocked)
                          </h4>
                          <ul className="space-y-2">
                            {booking.eligibility_errors.map((error, i) => (
                              <li key={i} className="text-sm text-red-300">
                                <strong>{error.dog_name}:</strong> {error.message}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {/* Warnings */}
                      {booking.eligibility_warnings?.length > 0 && (
                        <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-4">
                          <h4 className="text-amber-400 font-medium mb-2">Warnings</h4>
                          <ul className="space-y-1">
                            {booking.eligibility_warnings.map((warning, i) => (
                              <li key={i} className="text-sm text-amber-300">{warning.message}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>

                    {/* Action Buttons */}
                    <div className="flex flex-col gap-2 ml-6">
                      <Button
                        onClick={() => handleApproveClick(booking)}
                        className="bg-green-600 hover:bg-green-700"
                        data-testid={`approve-btn-${booking.id}`}
                      >
                        <CheckCircleIcon size={16} className="mr-2" />
                        Approve
                      </Button>
                      <Button
                        onClick={() => handleRejectClick(booking)}
                        variant="outline"
                        className="border-red-500 text-red-400 hover:bg-red-500/10"
                        data-testid={`reject-btn-${booking.id}`}
                      >
                        <XCircleIcon size={16} className="mr-2" />
                        Reject
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))
          )}
        </div>
      </main>

      {/* Approve Modal */}
      <Dialog open={showApproveModal} onOpenChange={setShowApproveModal}>
        <DialogContent className="bg-slate-900 border-slate-700 max-w-md">
          <DialogHeader>
            <DialogTitle className="text-white flex items-center gap-2">
              <CheckCircleIcon size={20} className="text-green-400" />
              Approve Booking
            </DialogTitle>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            <div className="bg-slate-800 rounded-lg p-3">
              <p className="text-slate-400 text-sm">Customer</p>
              <p className="text-white">{selectedBooking?.customer_name}</p>
            </div>

            {/* Kennel Assignment */}
            <div>
              <label className="text-sm text-slate-400 mb-2 block">Assign Kennel (Optional)</label>
              <Select value={selectedKennel} onValueChange={setSelectedKennel}>
                <SelectTrigger className="bg-slate-800 border-slate-700 text-white">
                  <SelectValue placeholder="Select kennel" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">No kennel assigned</SelectItem>
                  {kennels.map(kennel => (
                    <SelectItem key={kennel.id} value={kennel.id}>
                      {kennel.name} ({kennel.kennel_type}, {kennel.size_category})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Notes */}
            <div>
              <label className="text-sm text-slate-400 mb-2 block">Approval Notes</label>
              <Textarea
                value={approvalNotes}
                onChange={(e) => setApprovalNotes(e.target.value)}
                placeholder="Any notes about why this booking was approved..."
                className="bg-slate-800 border-slate-700 text-white"
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowApproveModal(false)} className="border-slate-600 text-slate-300">
              Cancel
            </Button>
            <Button onClick={approveBooking} className="bg-green-600 hover:bg-green-700">
              <CheckCircleIcon size={16} className="mr-2" />
              Approve Booking
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Reject Modal */}
      <Dialog open={showRejectModal} onOpenChange={setShowRejectModal}>
        <DialogContent className="bg-slate-900 border-slate-700 max-w-md">
          <DialogHeader>
            <DialogTitle className="text-white flex items-center gap-2">
              <XCircleIcon size={20} className="text-red-400" />
              Reject Booking
            </DialogTitle>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            <div className="bg-slate-800 rounded-lg p-3">
              <p className="text-slate-400 text-sm">Customer</p>
              <p className="text-white">{selectedBooking?.customer_name}</p>
            </div>

            {/* Rejection Reason */}
            <div>
              <label className="text-sm text-slate-400 mb-2 block">Rejection Reason *</label>
              <Textarea
                value={rejectionReason}
                onChange={(e) => setRejectionReason(e.target.value)}
                placeholder="Provide a reason for rejecting this booking..."
                className="bg-slate-800 border-slate-700 text-white"
                required
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowRejectModal(false)} className="border-slate-600 text-slate-300">
              Cancel
            </Button>
            <Button onClick={rejectBooking} className="bg-red-600 hover:bg-red-700">
              <XCircleIcon size={16} className="mr-2" />
              Reject Booking
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
