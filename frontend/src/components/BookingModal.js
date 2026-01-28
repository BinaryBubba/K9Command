import React, { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { toast } from 'sonner';
import api from '../utils/api';

const BookingModal = ({ isOpen, onClose, booking, onSuccess }) => {
  const [loading, setLoading] = useState(false);
  const [dogs, setDogs] = useState([]);
  const [locations, setLocations] = useState([]);
  const [formData, setFormData] = useState({
    dog_ids: [],
    location_id: '',
    accommodation_type: 'room',
    check_in_date: '',
    check_out_date: '',
    notes: '',
    needs_separate_playtime: false,
  });

  useEffect(() => {
    if (isOpen) {
      fetchData();
      if (booking) {
        setFormData({
          dog_ids: booking.dog_ids || [],
          location_id: booking.location_id || '',
          accommodation_type: booking.accommodation_type || 'room',
          check_in_date: booking.check_in_date?.split('T')[0] || '',
          check_out_date: booking.check_out_date?.split('T')[0] || '',
          notes: booking.notes || '',
          needs_separate_playtime: booking.needs_separate_playtime || false,
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
    } catch (error) {
      toast.error('Failed to load data');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
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
      } else {
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

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{booking ? 'Edit Booking' : 'Create Booking'}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
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
            <Label>Select Dogs</Label>
            <div className="mt-2 space-y-2 max-h-40 overflow-y-auto border rounded-xl p-3">
              {dogs.map((dog) => (
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
              ))}
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
