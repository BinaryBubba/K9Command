import React, { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Switch } from '../components/ui/switch';
import { toast } from 'sonner';
import api from '../utils/api';
import useAuthStore from '../store/authStore';

const BookingModal = ({ isOpen, onClose, booking, onSuccess }) => {
  const { user } = useAuthStore();
  const [loading, setLoading] = useState(false);
  const [dogs, setDogs] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [customerDogs, setCustomerDogs] = useState([]);
  const [locations, setLocations] = useState([]);
  const [customerSearch, setCustomerSearch] = useState('');
  const [formData, setFormData] = useState({
    customer_id: '',
    dog_ids: [],
    location_id: '',
    accommodation_type: 'room',
    booking_type: 'stay',
    check_in_date: '',
    check_out_date: '',
    notes: '',
    needs_separate_playtime: false,
    payment_type: 'invoice',
    meet_greet_override: false,
  });

  const isAdminOrStaff = user?.role === 'admin' || user?.role === 'staff';

  useEffect(() => {
    if (isOpen) {
      fetchData();
      if (booking) {
        setFormData({
          customer_id: booking.customer_id || '',
          dog_ids: booking.dog_ids || [],
          location_id: booking.location_id || '',
          accommodation_type: booking.accommodation_type || 'room',
          booking_type: booking.booking_type || 'stay',
          check_in_date: booking.check_in_date?.split('T')[0] || '',
          check_out_date: booking.check_out_date?.split('T')[0] || '',
          notes: booking.notes || '',
          needs_separate_playtime: booking.needs_separate_playtime || false,
          payment_type: booking.payment_type || 'invoice',
          meet_greet_override: false,
        });
      }
    }
  }, [isOpen, booking]);

  const fetchData = async () => {
    try {
      const [dogsRes, locationsRes] = await Promise.all([
        api.get('/dogs'),
        api.get('/locations'),
      ]);
      setDogs(dogsRes.data);
      setLocations(locationsRes.data);
      if (locationsRes.data.length > 0 && !booking) {
        setFormData(prev => ({ ...prev, location_id: locationsRes.data[0].id }));
      }

      // For admin/staff, also fetch customers
      if (isAdminOrStaff) {
        try {
          const customersRes = await api.get('/admin/users?role=customer');
          setCustomers(customersRes.data || []);
        } catch (e) {
          console.log('Could not load customers');
        }
      }
    } catch (error) {
      toast.error('Failed to load data');
    }
  };

  const handleCustomerSelect = (customerId) => {
    setFormData({ ...formData, customer_id: customerId, dog_ids: [] });
    const customer = customers.find(c => c.id === customerId);
    if (customer) {
      const dogsForCustomer = dogs.filter(d => d.household_id === customer.household_id);
      setCustomerDogs(dogsForCustomer);
    } else {
      setCustomerDogs([]);
    }
  };

  const filteredCustomers = customers.filter(c =>
    c.full_name?.toLowerCase().includes(customerSearch.toLowerCase()) ||
    c.email?.toLowerCase().includes(customerSearch.toLowerCase())
  );

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (isAdminOrStaff && !booking && !formData.customer_id) {
      toast.error('Please select a customer');
      return;
    }
    
    if (formData.dog_ids.length === 0) {
      toast.error('Please select at least one dog');
      return;
    }
    
    setLoading(true);

    try {
      const payload = {
        ...formData,
        check_in_date: new Date(formData.check_in_date).toISOString(),
        check_out_date: new Date(formData.check_out_date).toISOString(),
      };

      if (booking) {
        await api.patch(`/bookings/${booking.id}`, payload);
        toast.success('Booking updated successfully');
      } else if (isAdminOrStaff) {
        // Admin/Staff use the admin endpoint
        await api.post('/bookings/admin', payload);
        toast.success('Booking created successfully');
      } else {
        // Customer uses regular endpoint
        await api.post('/bookings', payload);
        toast.success('Booking created successfully');
      }
      onSuccess();
      onClose();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save booking');
    } finally {
      setLoading(false);
    }
  };

  // Determine which dogs to show
  const availableDogs = isAdminOrStaff && !booking ? customerDogs : dogs;

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{booking ? 'Edit Booking' : 'Create Booking'}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Booking Type Selection */}
          <div>
            <Label>Booking Type *</Label>
            <select
              value={formData.booking_type}
              onChange={(e) => setFormData({ ...formData, booking_type: e.target.value })}
              className="w-full p-2 border rounded-xl mt-1"
            >
              <option value="stay">Stay (Boarding)</option>
              <option value="daycare">Daycare</option>
              <option value="meet_greet">Meet & Greet</option>
            </select>
            {formData.booking_type === 'meet_greet' && (
              <p className="text-xs text-muted-foreground mt-1">New customers must complete a Meet & Greet before booking stays or daycare.</p>
            )}
          </div>

          {/* Customer Selection - Only for Admin/Staff creating new booking */}
          {isAdminOrStaff && !booking && (
            <div>
              <Label>Customer *</Label>
              <Input
                type="text"
                placeholder="Search customer by name or email..."
                value={customerSearch}
                onChange={(e) => setCustomerSearch(e.target.value)}
                className="mt-1 mb-2"
              />
              <div className="max-h-32 overflow-y-auto border rounded-xl p-2">
                {filteredCustomers.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No customers found</p>
                ) : (
                  filteredCustomers.slice(0, 10).map((customer) => (
                    <label 
                      key={customer.id} 
                      className={`flex items-center gap-2 p-2 cursor-pointer rounded hover:bg-muted ${formData.customer_id === customer.id ? 'bg-primary/10' : ''}`}
                    >
                      <input
                        type="radio"
                        name="customer"
                        checked={formData.customer_id === customer.id}
                        onChange={() => handleCustomerSelect(customer.id)}
                      />
                      <span className="text-sm">{customer.full_name} ({customer.email})</span>
                    </label>
                  ))
                )}
              </div>
            </div>
          )}

          <div>
            <Label>Location</Label>
            <select
              value={formData.location_id}
              onChange={(e) => setFormData({ ...formData, location_id: e.target.value })}
              className="w-full p-2 border rounded-xl mt-1"
              required
            >
              <option value="">Select location</option>
              {locations.map((loc) => (
                <option key={loc.id} value={loc.id}>{loc.name}</option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label>Check-In Date</Label>
              <Input
                type="date"
                value={formData.check_in_date}
                onChange={(e) => setFormData({ ...formData, check_in_date: e.target.value })}
                required
                className="mt-1"
              />
            </div>
            <div>
              <Label>Check-Out Date</Label>
              <Input
                type="date"
                value={formData.check_out_date}
                onChange={(e) => setFormData({ ...formData, check_out_date: e.target.value })}
                required
                className="mt-1"
              />
            </div>
          </div>

          <div>
            <Label>Accommodation Type</Label>
            <select
              value={formData.accommodation_type}
              onChange={(e) => setFormData({ ...formData, accommodation_type: e.target.value })}
              className="w-full p-2 border rounded-xl mt-1"
            >
              <option value="room">Room</option>
              <option value="crate">Crate</option>
            </select>
          </div>

          <div>
            <Label>Select Dogs *</Label>
            <div className="mt-2 space-y-2 max-h-40 overflow-y-auto border rounded-xl p-3">
              {availableDogs.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  {isAdminOrStaff && !booking ? 'Select a customer first to see their dogs' : 'No dogs available'}
                </p>
              ) : (
                availableDogs.map((dog) => (
                  <label key={dog.id} className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={formData.dog_ids.includes(dog.id)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setFormData({ ...formData, dog_ids: [...formData.dog_ids, dog.id] });
                        } else {
                          setFormData({ ...formData, dog_ids: formData.dog_ids.filter(id => id !== dog.id) });
                        }
                      }}
                    />
                    <span>{dog.name} - {dog.breed}</span>
                  </label>
                ))
              )}
            </div>
          </div>

          <div>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={formData.needs_separate_playtime}
                onChange={(e) => setFormData({ ...formData, needs_separate_playtime: e.target.checked })}
              />
              <span>Needs Separate Playtime (+$6/day)</span>
            </label>
          </div>

          {/* Payment Type - Only for Admin/Staff */}
          {isAdminOrStaff && !booking && (
            <div>
              <Label>Payment Type</Label>
              <select
                value={formData.payment_type}
                onChange={(e) => setFormData({ ...formData, payment_type: e.target.value })}
                className="w-full p-2 border rounded-xl mt-1"
              >
                <option value="invoice">Invoice (Pay Later)</option>
                <option value="immediate">Immediate Payment</option>
              </select>
            </div>
          )}

          <div>
            <Label>Notes</Label>
            <Textarea
              value={formData.notes}
              onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
              placeholder="Any special instructions"
              className="mt-1"
              rows={3}
            />
          </div>

          <div className="flex gap-3 justify-end">
            <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
            <Button type="submit" disabled={loading}>
              {loading ? 'Saving...' : booking ? 'Update' : 'Create'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
};

export default BookingModal;
