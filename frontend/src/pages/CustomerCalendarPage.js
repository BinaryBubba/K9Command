import React, { useEffect, useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/card';
import { ChevronLeftIcon, ChevronRightIcon, CalendarIcon, PlusIcon, ArrowLeftIcon, EditIcon, XIcon } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import useAuthStore from '../store/authStore';
import { dataClient, toISODate } from '../data/client';
import { toast } from 'sonner';

const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];

const CustomerCalendarPage = () => {
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [currentMonth, setCurrentMonth] = useState(new Date());
  const [selectedDate, setSelectedDate] = useState(null);
  const [selectedBookings, setSelectedBookings] = useState([]);

  // Edit booking modal
  const [editModal, setEditModal] = useState(false);
  const [editingBooking, setEditingBooking] = useState(null);
  const [editForm, setEditForm] = useState({});
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!user || user.role !== 'customer') {
      navigate('/auth');
      return;
    }
    loadBookings();
  }, [user, navigate]);

  const loadBookings = async () => {
    setLoading(true);
    try {
      const data = await dataClient.listBookings();
      setBookings(data || []);
    } catch (error) {
      console.error('Failed to load bookings:', error);
      toast.error('Failed to load bookings');
    } finally {
      setLoading(false);
    }
  };

  // Generate calendar grid
  const calendarDays = useMemo(() => {
    const year = currentMonth.getFullYear();
    const month = currentMonth.getMonth();
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const startPadding = firstDay.getDay();
    const totalDays = lastDay.getDate();

    const days = [];
    
    // Previous month padding
    const prevMonth = new Date(year, month, 0);
    for (let i = startPadding - 1; i >= 0; i--) {
      days.push({
        date: new Date(year, month - 1, prevMonth.getDate() - i),
        isCurrentMonth: false,
      });
    }

    // Current month
    for (let d = 1; d <= totalDays; d++) {
      days.push({
        date: new Date(year, month, d),
        isCurrentMonth: true,
      });
    }

    // Next month padding
    const remaining = 42 - days.length;
    for (let i = 1; i <= remaining; i++) {
      days.push({
        date: new Date(year, month + 1, i),
        isCurrentMonth: false,
      });
    }

    return days;
  }, [currentMonth]);

  // Get bookings for a specific date
  const getBookingsForDate = (date) => {
    const dateISO = toISODate(date);
    return bookings.filter(b => {
      return dateISO >= b.startDate && dateISO <= b.endDate;
    });
  };

  const handlePrevMonth = () => {
    setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() - 1, 1));
  };

  const handleNextMonth = () => {
    setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1, 1));
  };

  const handleDateClick = (day) => {
    const dateBookings = getBookingsForDate(day.date);
    setSelectedDate(day.date);
    setSelectedBookings(dateBookings);
  };

  // Can edit booking logic
  const canEditBooking = (booking) => {
    const allowedStatuses = ['pending', 'confirmed'];
    if (!allowedStatuses.includes(booking.status)) return false;
    
    const checkInDate = new Date(booking.startDate);
    const now = new Date();
    const hoursUntilCheckIn = (checkInDate - now) / (1000 * 60 * 60);
    return hoursUntilCheckIn >= 24;
  };

  const openEditModal = (booking) => {
    if (!canEditBooking(booking)) {
      toast.error('This booking cannot be modified');
      return;
    }
    setEditingBooking(booking);
    setEditForm({
      startDate: booking.startDate,
      endDate: booking.endDate,
      notes: booking.notes || '',
    });
    setEditModal(true);
  };

  const handleSaveBooking = async () => {
    if (!editingBooking) return;
    setSaving(true);
    try {
      await dataClient.updateBooking(editingBooking.id, editForm);
      toast.success('Booking updated!');
      setEditModal(false);
      setEditingBooking(null);
      loadBookings();
    } catch (error) {
      toast.error(error.message || 'Failed to update booking');
    } finally {
      setSaving(false);
    }
  };

  const handleCancelBooking = async (booking) => {
    if (!canEditBooking(booking)) {
      toast.error('This booking cannot be cancelled');
      return;
    }
    if (!window.confirm('Are you sure you want to cancel this booking?')) return;
    
    try {
      await dataClient.cancelBooking(booking.id);
      toast.success('Booking cancelled');
      loadBookings();
      setSelectedBookings(selectedBookings.filter(b => b.id !== booking.id));
    } catch (error) {
      toast.error(error.message || 'Failed to cancel booking');
    }
  };

  const isToday = (date) => {
    const today = new Date();
    return date.toDateString() === today.toDateString();
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#F9F7F2]">
        <div className="animate-spin h-8 w-8 border-2 border-primary border-t-transparent rounded-full"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#F9F7F2]">
      {/* Header */}
      <header className="bg-white border-b border-border/40 shadow-sm">
        <div className="max-w-6xl mx-auto px-4 md:px-8 py-4 flex justify-between items-center">
          <div className="flex items-center gap-4">
            <Button variant="ghost" onClick={() => navigate('/customer/dashboard')}>
              <ArrowLeftIcon size={20} />
            </Button>
            <div>
              <h1 className="text-2xl font-serif font-bold text-primary flex items-center gap-2">
                <CalendarIcon />
                Booking Calendar
              </h1>
              <p className="text-sm text-muted-foreground">View and manage your stays</p>
            </div>
          </div>
          <Button onClick={() => navigate('/customer/bookings/new')} className="rounded-full">
            <PlusIcon size={18} className="mr-2" />
            Book a Stay
          </Button>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 md:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Calendar */}
          <Card className="lg:col-span-2 bg-white rounded-2xl border border-border/50 shadow-sm">
            <CardHeader className="border-b border-border/40">
              <div className="flex items-center justify-between">
                <Button variant="ghost" size="sm" onClick={handlePrevMonth}>
                  <ChevronLeftIcon size={20} />
                </Button>
                <CardTitle className="text-xl font-serif">
                  {MONTHS[currentMonth.getMonth()]} {currentMonth.getFullYear()}
                </CardTitle>
                <Button variant="ghost" size="sm" onClick={handleNextMonth}>
                  <ChevronRightIcon size={20} />
                </Button>
              </div>
            </CardHeader>
            <CardContent className="p-4">
              {/* Day headers */}
              <div className="grid grid-cols-7 mb-2">
                {DAYS.map(day => (
                  <div key={day} className="text-center text-sm font-medium text-muted-foreground py-2">
                    {day}
                  </div>
                ))}
              </div>
              
              {/* Calendar grid */}
              <div className="grid grid-cols-7 gap-1">
                {calendarDays.map((day, idx) => {
                  const dayBookings = getBookingsForDate(day.date);
                  const hasBookings = dayBookings.length > 0;
                  const isSelected = selectedDate && day.date.toDateString() === selectedDate.toDateString();
                  
                  return (
                    <div
                      key={idx}
                      onClick={() => handleDateClick(day)}
                      className={`
                        aspect-square p-1 rounded-lg cursor-pointer transition-all
                        ${day.isCurrentMonth ? 'bg-white' : 'bg-muted/30'}
                        ${isToday(day.date) ? 'ring-2 ring-primary' : ''}
                        ${isSelected ? 'bg-primary/10' : 'hover:bg-muted/50'}
                        ${hasBookings ? 'border-2 border-primary/50' : 'border border-border/30'}
                      `}
                    >
                      <div className="text-center">
                        <span className={`text-sm ${day.isCurrentMonth ? 'text-foreground' : 'text-muted-foreground'}`}>
                          {day.date.getDate()}
                        </span>
                      </div>
                      {hasBookings && (
                        <div className="mt-1 flex flex-wrap gap-0.5 justify-center">
                          {dayBookings.slice(0, 3).map((b, i) => (
                            <div
                              key={i}
                              className={`w-1.5 h-1.5 rounded-full ${
                                b.status === 'confirmed' ? 'bg-green-500' :
                                b.status === 'pending' ? 'bg-yellow-500' :
                                'bg-gray-400'
                              }`}
                            />
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>

              {/* Legend */}
              <div className="mt-4 flex items-center gap-4 text-sm text-muted-foreground">
                <div className="flex items-center gap-1">
                  <div className="w-3 h-3 rounded-full bg-green-500"></div>
                  <span>Confirmed</span>
                </div>
                <div className="flex items-center gap-1">
                  <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
                  <span>Pending</span>
                </div>
                <div className="flex items-center gap-1">
                  <div className="w-3 h-3 rounded-full bg-gray-400"></div>
                  <span>Other</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Selected Date Details */}
          <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
            <CardHeader className="border-b border-border/40">
              <CardTitle className="text-lg font-serif">
                {selectedDate ? (
                  <>
                    {MONTHS[selectedDate.getMonth()]} {selectedDate.getDate()}, {selectedDate.getFullYear()}
                  </>
                ) : (
                  'Select a date'
                )}
              </CardTitle>
            </CardHeader>
            <CardContent className="p-4">
              {!selectedDate ? (
                <p className="text-muted-foreground text-center py-8">
                  Click on a date to see booking details
                </p>
              ) : selectedBookings.length === 0 ? (
                <div className="text-center py-8">
                  <CalendarIcon className="mx-auto text-muted-foreground/50 mb-4" size={32} />
                  <p className="text-muted-foreground mb-4">No bookings on this day</p>
                  <Button onClick={() => navigate('/customer/bookings/new')} size="sm" className="rounded-full">
                    <PlusIcon size={16} className="mr-2" />
                    Book a Stay
                  </Button>
                </div>
              ) : (
                <div className="space-y-3">
                  {selectedBookings.map(booking => (
                    <div
                      key={booking.id}
                      data-testid={`booking-detail-${booking.id}`}
                      className="p-3 rounded-lg border border-border/40 bg-muted/20"
                    >
                      <div className="flex items-start justify-between mb-2">
                        <div className="font-medium">
                          {booking.dogs?.length ? booking.dogs.join(', ') : 'Booking'}
                        </div>
                        <span className={`text-xs px-2 py-0.5 rounded-full ${
                          booking.status === 'confirmed' ? 'bg-green-100 text-green-700' :
                          booking.status === 'pending' ? 'bg-yellow-100 text-yellow-700' :
                          'bg-gray-100 text-gray-700'
                        }`}>
                          {booking.status}
                        </span>
                      </div>
                      <div className="text-sm text-muted-foreground mb-2">
                        {booking.startDate} → {booking.endDate}
                      </div>
                      {booking.notes && (
                        <p className="text-sm text-muted-foreground mb-2">{booking.notes}</p>
                      )}
                      {canEditBooking(booking) && (
                        <div className="flex gap-2 mt-2">
                          <Button variant="outline" size="sm" onClick={() => openEditModal(booking)}>
                            <EditIcon size={14} className="mr-1" />
                            Edit
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            className="text-red-500 hover:text-red-700"
                            onClick={() => handleCancelBooking(booking)}
                          >
                            <XIcon size={14} className="mr-1" />
                            Cancel
                          </Button>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </main>

      {/* Edit Booking Modal */}
      <Dialog open={editModal} onOpenChange={setEditModal}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Edit Booking</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <Label>Check-in Date</Label>
              <Input
                type="date"
                value={editForm.startDate || ''}
                onChange={(e) => setEditForm({ ...editForm, startDate: e.target.value })}
              />
            </div>
            <div>
              <Label>Check-out Date</Label>
              <Input
                type="date"
                value={editForm.endDate || ''}
                onChange={(e) => setEditForm({ ...editForm, endDate: e.target.value })}
              />
            </div>
            <div>
              <Label>Notes</Label>
              <Textarea
                value={editForm.notes || ''}
                onChange={(e) => setEditForm({ ...editForm, notes: e.target.value })}
                rows={3}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditModal(false)}>Cancel</Button>
            <Button onClick={handleSaveBooking} disabled={saving}>
              {saving ? 'Saving...' : 'Save Changes'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default CustomerCalendarPage;
