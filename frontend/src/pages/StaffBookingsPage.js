import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/card';
import { Checkbox } from '../components/ui/checkbox';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { ArrowLeftIcon, CheckCircleIcon, DogIcon, PlusIcon, EditIcon, TrashIcon, SearchIcon, UserIcon, CreditCardIcon, MailIcon } from 'lucide-react';
import { toast } from 'sonner';
import api from '../utils/api';
import useAuthStore from '../store/authStore';

const StaffBookingsPage = () => {
  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);
  const [bookings, setBookings] = useState([]);
  const [selectedBooking, setSelectedBooking] = useState(null);
  const [dogs, setDogs] = useState([]);
  const [allDogs, setAllDogs] = useState([]);
  const [locations, setLocations] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [customerDogs, setCustomerDogs] = useState([]);
  const [items, setItems] = useState({
    toys: false, bowls: false, food: false, blanket: false,
    medication: false, collar: false, leash: false, other_items: '',
  });
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editMode, setEditMode] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [customerSearch, setCustomerSearch] = useState('');
  const [formData, setFormData] = useState({
    customer_id: '',
    dog_ids: [],
    location_id: '',
    accommodation_type: 'room',
    check_in_date: '',
    check_out_date: '',
    notes: '',
    modification_reason: '',
    needs_separate_playtime: false,
    payment_type: 'invoice',
  });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [bookingsRes, dogsRes, locationsRes, customersRes] = await Promise.all([
        api.get('/bookings'),
        api.get('/dogs'),
        api.get('/locations'),
        api.get('/admin/users?role=customer'),
      ]);
      setBookings(bookingsRes.data);
      setAllDogs(dogsRes.data);
      setLocations(locationsRes.data);
      setCustomers(customersRes.data);
      
      if (locationsRes.data.length > 0) {
        setFormData(prev => ({ ...prev, location_id: locationsRes.data[0].id }));
      }
    } catch (error) {
      toast.error('Failed to load data');
    }
  };

  const selectBooking = async (booking) => {
    setSelectedBooking(booking);
    const dogPromises = booking.dog_ids.map((id) => api.get(`/dogs/${id}`).catch(() => null));
    const dogResponses = await Promise.all(dogPromises);
    setDogs(dogResponses.filter(r => r).map((r) => r.data));
    if (booking.items_checklist) setItems(booking.items_checklist);
  };

  const handleCustomerSelect = (customerId) => {
    setFormData({ ...formData, customer_id: customerId, dog_ids: [] });
    const customer = customers.find(c => c.id === customerId);
    if (customer) {
      const dogsForCustomer = allDogs.filter(d => d.household_id === customer.household_id);
      setCustomerDogs(dogsForCustomer);
    } else {
      setCustomerDogs([]);
    }
  };

  const toggleDogSelection = (dogId) => {
    setFormData(prev => ({
      ...prev,
      dog_ids: prev.dog_ids.includes(dogId)
        ? prev.dog_ids.filter(id => id !== dogId)
        : [...prev.dog_ids, dogId]
    }));
  };

  const openCreateModal = () => {
    setEditMode(false);
    setFormData({
      customer_id: '',
      dog_ids: [],
      location_id: locations[0]?.id || '',
      accommodation_type: 'room',
      check_in_date: '',
      check_out_date: '',
      notes: '',
      modification_reason: '',
      needs_separate_playtime: false,
      payment_type: 'invoice',
    });
    setCustomerDogs([]);
    setModalOpen(true);
  };

  const openEditModal = (booking) => {
    setEditMode(true);
    setFormData({
      customer_id: booking.customer_id || '',
      dog_ids: booking.dog_ids || [],
      location_id: booking.location_id,
      accommodation_type: booking.accommodation_type || 'room',
      check_in_date: booking.check_in_date?.split('T')[0] || '',
      check_out_date: booking.check_out_date?.split('T')[0] || '',
      notes: booking.notes || '',
      modification_reason: '',
      needs_separate_playtime: booking.needs_separate_playtime || false,
      payment_type: booking.payment_type || 'invoice',
    });
    setSelectedBooking(booking);
    setModalOpen(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!editMode && !formData.customer_id) {
      toast.error('Please select a customer');
      return;
    }
    
    if (!editMode && formData.dog_ids.length === 0) {
      toast.error('Please select at least one dog');
      return;
    }
    
    if (editMode && !formData.modification_reason) {
      toast.error('Please provide a reason for the modification');
      return;
    }
    
    setLoading(true);
    try {
      if (editMode) {
        await api.patch(`/bookings/${selectedBooking.id}`, formData);
        toast.success('Booking updated successfully');
      } else {
        await api.post('/bookings/admin', {
          ...formData,
          check_in_date: new Date(formData.check_in_date).toISOString(),
          check_out_date: new Date(formData.check_out_date).toISOString(),
        });
        toast.success(`Booking created! ${formData.payment_type === 'invoice' ? 'Invoice will be sent to customer.' : 'Payment required.'}`);
      }
      setModalOpen(false);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save booking');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (bookingId) => {
    const reason = window.prompt('Please provide a reason for cancelling this booking:');
    if (!reason) return;
    
    try {
      await api.delete(`/bookings/${bookingId}`);
      toast.success('Booking cancelled');
      fetchData();
      setSelectedBooking(null);
    } catch (error) {
      toast.error('Failed to cancel booking');
    }
  };

  const handleCheckIn = async () => {
    if (!selectedBooking) return;
    setLoading(true);
    try {
      await api.patch(`/bookings/${selectedBooking.id}/status?status=checked_in`);
      toast.success('Dogs checked in successfully!');
      fetchData();
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
      await api.patch(`/bookings/${selectedBooking.id}/items`, items);
      await api.patch(`/bookings/${selectedBooking.id}/status?status=checked_out`);
      toast.success('Dogs checked out successfully!');
      fetchData();
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
    const colors = {
      confirmed: 'bg-blue-100 text-blue-800',
      checked_in: 'bg-green-100 text-green-800',
      checked_out: 'bg-gray-100 text-gray-800',
      pending: 'bg-yellow-100 text-yellow-800',
      cancelled: 'bg-red-100 text-red-800',
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
  };

  const filteredBookings = bookings.filter(b => 
    b.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
    b.status.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const filteredCustomers = customers.filter(c =>
    c.full_name?.toLowerCase().includes(customerSearch.toLowerCase()) ||
    c.email?.toLowerCase().includes(customerSearch.toLowerCase())
  );

  const getCustomerName = (customerId) => {
    const customer = customers.find(c => c.id === customerId);
    return customer?.full_name || 'Unknown';
  };

  return (
    <div className="min-h-screen bg-[#F9F7F2]">
      <header className="bg-white border-b border-border/40 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 md:px-8 py-4">
          <Button variant="ghost" onClick={() => navigate('/staff/dashboard')} className="flex items-center gap-2 mb-2">
            <ArrowLeftIcon size={18} /> Back to Dashboard
          </Button>
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-serif font-bold text-primary">Manage Bookings</h1>
              <p className="text-muted-foreground mt-1">Create bookings and check in/out dogs</p>
            </div>
            <Button data-testid="create-booking-btn" onClick={openCreateModal} className="rounded-full">
              <PlusIcon size={18} className="mr-2" /> New Booking
            </Button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 md:px-8 py-8">
        {/* Search */}
        <Card className="mb-6 bg-white rounded-2xl border border-border/50 shadow-sm">
          <CardContent className="p-4">
            <div className="relative">
              <SearchIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground" size={20} />
              <Input placeholder="Search bookings..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} className="pl-10" />
            </div>
          </CardContent>
        </Card>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Bookings List */}
          <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
            <CardHeader className="border-b border-border/40">
              <CardTitle className="text-2xl font-serif">All Bookings</CardTitle>
            </CardHeader>
            <CardContent className="p-6 max-h-[600px] overflow-y-auto">
              {filteredBookings.length === 0 ? (
                <p className="text-center text-muted-foreground py-8">No bookings found</p>
              ) : (
                <div className="space-y-3">
                  {filteredBookings.map((booking) => (
                    <div
                      key={booking.id}
                      data-testid={`booking-item-${booking.id}`}
                      className={`p-4 rounded-xl border-2 cursor-pointer transition-all ${
                        selectedBooking?.id === booking.id ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/50'
                      }`}
                      onClick={() => selectBooking(booking)}
                    >
                      <div className="flex justify-between items-start mb-2">
                        <div>
                          <h3 className="font-semibold">#{booking.id.slice(0, 8)}</h3>
                          <p className="text-sm text-muted-foreground">
                            {new Date(booking.check_in_date).toLocaleDateString()} - {new Date(booking.check_out_date).toLocaleDateString()}
                          </p>
                          {booking.customer_id && (
                            <p className="text-xs text-blue-600 flex items-center gap-1 mt-1">
                              <UserIcon size={12} /> {getCustomerName(booking.customer_id)}
                            </p>
                          )}
                        </div>
                        <Badge className={getStatusColor(booking.status)}>{booking.status.replace('_', ' ')}</Badge>
                      </div>
                      <div className="flex items-center justify-between text-sm">
                        <span className="flex items-center gap-1"><DogIcon size={14} /> {booking.dog_ids?.length || 0} dog(s)</span>
                        <div className="flex gap-1">
                          <Button size="sm" variant="ghost" onClick={(e) => { e.stopPropagation(); openEditModal(booking); }}>
                            <EditIcon size={14} />
                          </Button>
                          <Button size="sm" variant="ghost" className="text-red-600" onClick={(e) => { e.stopPropagation(); handleDelete(booking.id); }}>
                            <TrashIcon size={14} />
                          </Button>
                        </div>
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
                <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
                  <CardHeader className="border-b border-border/40">
                    <CardTitle className="text-2xl font-serif">Dogs</CardTitle>
                  </CardHeader>
                  <CardContent className="p-6">
                    <div className="space-y-3">
                      {dogs.map((dog) => (
                        <div key={dog.id} className="p-4 rounded-xl bg-muted/50 border border-border">
                          <h4 className="font-semibold text-lg">{dog.name}</h4>
                          <p className="text-sm text-muted-foreground">{dog.breed} • {dog.age} years old</p>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>

                <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
                  <CardHeader className="border-b border-border/40">
                    <CardTitle className="text-xl font-serif">Items Checklist</CardTitle>
                  </CardHeader>
                  <CardContent className="p-6 space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      {Object.keys(items).filter(k => k !== 'other_items').map((key) => (
                        <div key={key} className="flex items-center space-x-3">
                          <Checkbox id={key} checked={items[key]} onCheckedChange={(c) => setItems({ ...items, [key]: c })} />
                          <Label htmlFor={key} className="capitalize">{key.replace('_', ' ')}</Label>
                        </div>
                      ))}
                    </div>
                    <Button onClick={handleSaveItems} variant="outline" className="w-full rounded-full">Save Items</Button>
                  </CardContent>
                </Card>

                <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
                  <CardContent className="p-6 space-y-3">
                    {selectedBooking.status === 'confirmed' && (
                      <Button onClick={handleCheckIn} disabled={loading} className="w-full py-6 rounded-full bg-green-600 hover:bg-green-700">
                        <CheckCircleIcon size={20} className="mr-2" /> Check In
                      </Button>
                    )}
                    {selectedBooking.status === 'checked_in' && (
                      <Button onClick={handleCheckOut} disabled={loading} className="w-full py-6 rounded-full">
                        <CheckCircleIcon size={20} className="mr-2" /> Check Out
                      </Button>
                    )}
                    <Button variant="outline" onClick={() => openEditModal(selectedBooking)} className="w-full rounded-full">
                      <EditIcon size={16} className="mr-2" /> Edit Booking
                    </Button>
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

      {/* Create/Edit Modal */}
      <Dialog open={modalOpen} onOpenChange={setModalOpen}>
        <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editMode ? 'Edit Booking' : 'Create New Booking'}</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="space-y-4">
            {!editMode && (
              <>
                {/* Customer Selection */}
                <div>
                  <Label>Search Customer *</Label>
                  <Input
                    placeholder="Search by name or email..."
                    value={customerSearch}
                    onChange={(e) => setCustomerSearch(e.target.value)}
                    className="mb-2"
                  />
                  <div className="max-h-40 overflow-y-auto border rounded-lg">
                    {filteredCustomers.length === 0 ? (
                      <p className="p-3 text-sm text-muted-foreground">No customers found</p>
                    ) : (
                      filteredCustomers.slice(0, 10).map((customer) => (
                        <div
                          key={customer.id}
                          onClick={() => handleCustomerSelect(customer.id)}
                          className={`p-3 cursor-pointer hover:bg-muted/50 flex items-center gap-3 ${formData.customer_id === customer.id ? 'bg-primary/10 border-l-4 border-primary' : ''}`}
                        >
                          <UserIcon size={16} className="text-muted-foreground" />
                          <div>
                            <p className="font-medium">{customer.full_name}</p>
                            <p className="text-xs text-muted-foreground">{customer.email}</p>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>

                {/* Dog Selection */}
                {formData.customer_id && (
                  <div>
                    <Label>Select Dogs *</Label>
                    {customerDogs.length === 0 ? (
                      <p className="text-sm text-muted-foreground p-3 border rounded-lg">No dogs registered for this customer</p>
                    ) : (
                      <div className="space-y-2 border rounded-lg p-3">
                        {customerDogs.map((dog) => (
                          <div
                            key={dog.id}
                            onClick={() => toggleDogSelection(dog.id)}
                            className={`p-3 rounded-lg cursor-pointer flex items-center gap-3 ${formData.dog_ids.includes(dog.id) ? 'bg-primary/10 border border-primary' : 'bg-muted/30 hover:bg-muted/50'}`}
                          >
                            <Checkbox checked={formData.dog_ids.includes(dog.id)} />
                            <DogIcon size={16} />
                            <div>
                              <p className="font-medium">{dog.name}</p>
                              <p className="text-xs text-muted-foreground">{dog.breed}</p>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </>
            )}

            <div>
              <Label>Location</Label>
              <Select value={formData.location_id} onValueChange={(v) => setFormData({ ...formData, location_id: v })}>
                <SelectTrigger><SelectValue placeholder="Select location" /></SelectTrigger>
                <SelectContent>
                  {locations.map((loc) => (
                    <SelectItem key={loc.id} value={loc.id}>{loc.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label>Accommodation</Label>
              <Select value={formData.accommodation_type} onValueChange={(v) => setFormData({ ...formData, accommodation_type: v })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="room">Room ($50/night)</SelectItem>
                  <SelectItem value="crate">Crate ($50/night)</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Check-in Date</Label>
                <Input type="date" value={formData.check_in_date} onChange={(e) => setFormData({ ...formData, check_in_date: e.target.value })} required />
              </div>
              <div>
                <Label>Check-out Date</Label>
                <Input type="date" value={formData.check_out_date} onChange={(e) => setFormData({ ...formData, check_out_date: e.target.value })} required />
              </div>
            </div>

            <div className="flex items-center space-x-3">
              <Checkbox
                id="separate_playtime"
                checked={formData.needs_separate_playtime}
                onCheckedChange={(c) => setFormData({ ...formData, needs_separate_playtime: c })}
              />
              <Label htmlFor="separate_playtime">Needs Separate Playtime (+$6/day)</Label>
            </div>

            {!editMode && (
              <div>
                <Label>Payment Method</Label>
                <div className="grid grid-cols-2 gap-3 mt-2">
                  <div
                    onClick={() => setFormData({ ...formData, payment_type: 'immediate' })}
                    className={`p-4 rounded-lg border-2 cursor-pointer text-center transition-all ${formData.payment_type === 'immediate' ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/50'}`}
                  >
                    <CreditCardIcon size={24} className="mx-auto mb-2 text-primary" />
                    <p className="font-medium">Pay Now</p>
                    <p className="text-xs text-muted-foreground">Immediate payment via Square</p>
                  </div>
                  <div
                    onClick={() => setFormData({ ...formData, payment_type: 'invoice' })}
                    className={`p-4 rounded-lg border-2 cursor-pointer text-center transition-all ${formData.payment_type === 'invoice' ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/50'}`}
                  >
                    <MailIcon size={24} className="mx-auto mb-2 text-blue-600" />
                    <p className="font-medium">Send Invoice</p>
                    <p className="text-xs text-muted-foreground">Email invoice to customer</p>
                  </div>
                </div>
              </div>
            )}

            <div>
              <Label>Notes</Label>
              <textarea
                value={formData.notes}
                onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                className="w-full p-2 border rounded-lg"
                rows={2}
              />
            </div>

            {editMode && (
              <div>
                <Label className="text-red-600">Reason for Modification *</Label>
                <textarea
                  value={formData.modification_reason}
                  onChange={(e) => setFormData({ ...formData, modification_reason: e.target.value })}
                  className="w-full p-2 border border-red-200 rounded-lg"
                  rows={2}
                  placeholder="Explain why you are changing this booking..."
                  required
                />
              </div>
            )}

            <div className="flex gap-3 pt-4">
              <Button type="button" variant="outline" onClick={() => setModalOpen(false)} className="flex-1">Cancel</Button>
              <Button type="submit" disabled={loading} className="flex-1">{editMode ? 'Update' : 'Create Booking'}</Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default StaffBookingsPage;
