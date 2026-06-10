import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import useAuthStore from '../store/authStore';
import api from '../utils/api';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import {
  ArrowLeftIcon, DogIcon, UserIcon, PhoneIcon,
  MailIcon, PlusIcon, AlertCircleIcon,
} from 'lucide-react';
import { toast } from 'sonner';

const CustomerProfilePage = () => {
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const { householdId } = useParams();
  const [household, setHousehold] = useState(null);
  const [dogs, setDogs] = useState([]);
  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAddContact, setShowAddContact] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      const [hhRes, dogsRes, bookingsRes] = await Promise.all([
        api.get(`/households/${householdId}`),
        api.get('/dogs', { params: { household_id: householdId } }),
        api.get('/bookings', { params: { household_id: householdId, limit: 10 } }),
      ]);
      setHousehold(hhRes.data);
      setDogs(dogsRes.data);
      setBookings(bookingsRes.data);
    } catch {
      toast.error('Failed to load customer profile');
    } finally {
      setLoading(false);
    }
  }, [householdId]);

  useEffect(() => {
    if (!user) { navigate('/auth'); return; }
    fetchData();
  }, [user, navigate, fetchData]);

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-primary"></div>
    </div>
  );

  if (!household) return (
    <div className="min-h-screen flex items-center justify-center">
      <p className="text-muted-foreground">Customer not found</p>
    </div>
  );

  const primaryContact = household.contacts?.find(c => c.is_primary);
  const otherContacts = household.contacts?.filter(c => !c.is_primary) || [];
  const magStatus = household.meet_and_greet_status;

  const STATUS_COLORS = {
    confirmed: 'bg-blue-100 text-blue-700',
    checked_in: 'bg-green-100 text-green-700',
    checked_out: 'bg-gray-100 text-gray-600',
    cancelled: 'bg-red-100 text-red-600',
  };

  return (
    <div className="min-h-screen bg-[#F9F7F2]">
      <header className="bg-white border-b shadow-sm sticky top-0 z-10">
        <div className="max-w-3xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="sm" onClick={() => navigate('/admin/customers')}>
              <ArrowLeftIcon size={18} />
            </Button>
            <h1 className="text-lg font-serif font-bold text-primary">{household.display_name}</h1>
          </div>
          <Button size="sm" variant="outline"
            onClick={() => navigate(`/admin/dogs/add?household_id=${householdId}`)}>
            <PlusIcon size={14} className="mr-1" /> Add Dog
          </Button>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 py-6 space-y-5">

        {/* Status badges */}
        <div className="flex gap-2 flex-wrap">
          <Badge variant="outline" className={
            magStatus === 'completed' ? 'text-green-600 border-green-300' :
            magStatus === 'scheduled' ? 'text-blue-600 border-blue-300' :
            'text-amber-600 border-amber-300'
          }>
            M&G: {magStatus}
          </Badge>
          <Badge variant="outline" className={household.status === 'active' ? 'text-green-600' : 'text-gray-500'}>
            {household.status}
          </Badge>
          {household.referral_source && (
            <Badge variant="secondary" className="text-xs">Via: {household.referral_source}</Badge>
          )}
        </div>

        {/* Primary contact */}
        <Card>
          <CardHeader className="pb-2 pt-4">
            <CardTitle className="text-sm flex items-center justify-between">
              <span className="flex items-center gap-2"><UserIcon size={14} /> Contacts</span>
              <Button size="sm" variant="ghost" className="h-7 text-xs"
                onClick={() => setShowAddContact(true)}>
                <PlusIcon size={12} className="mr-1" /> Add
              </Button>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {household.contacts?.length === 0 ? (
              <p className="text-sm text-muted-foreground">No contacts on file</p>
            ) : (
              household.contacts?.map(contact => (
                <div key={contact.id} className="flex items-start justify-between p-3 bg-muted/30 rounded-lg border">
                  <div>
                    <div className="flex items-center gap-2">
                      <p className="font-medium text-sm">
                        {contact.first_name} {contact.last_name}
                      </p>
                      {contact.is_primary && <Badge className="text-xs bg-blue-100 text-blue-700">Primary</Badge>}
                      {contact.is_emergency_contact && <Badge className="text-xs bg-red-100 text-red-700">Emergency</Badge>}
                      {contact.is_authorized_pickup && <Badge className="text-xs bg-green-100 text-green-700">Pickup OK</Badge>}
                    </div>
                    {contact.relationship_to_household && (
                      <p className="text-xs text-muted-foreground capitalize">{contact.relationship_to_household}</p>
                    )}
                    <div className="flex gap-3 mt-1.5">
                      {contact.phone && (
                        <span className="flex items-center gap-1 text-xs text-muted-foreground">
                          <PhoneIcon size={11} /> {contact.phone}
                        </span>
                      )}
                      {contact.email && (
                        <span className="flex items-center gap-1 text-xs text-muted-foreground">
                          <MailIcon size={11} /> {contact.email}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        {/* Dogs */}
        <Card>
          <CardHeader className="pb-2 pt-4">
            <CardTitle className="text-sm flex items-center justify-between">
              <span className="flex items-center gap-2"><DogIcon size={14} /> Dogs ({dogs.length})</span>
              <Button size="sm" variant="ghost" className="h-7 text-xs"
                onClick={() => navigate(`/admin/dogs/add?household_id=${householdId}`)}>
                <PlusIcon size={12} className="mr-1" /> Add Dog
              </Button>
            </CardTitle>
          </CardHeader>
          <CardContent>
            {dogs.length === 0 ? (
              <p className="text-sm text-muted-foreground">No dogs on file</p>
            ) : (
              <div className="space-y-2">
                {dogs.map(dog => (
                  <div key={dog.id}
                    className="flex items-center justify-between p-3 bg-muted/30 rounded-lg border cursor-pointer hover:bg-muted/50 transition-colors"
                    onClick={() => navigate(`/admin/dogs/${dog.id}`)}>
                    <div className="flex items-center gap-3">
                      <DogIcon size={16} className="text-muted-foreground" />
                      <div>
                        <div className="flex items-center gap-2">
                          <p className="font-medium text-sm">{dog.name}</p>
                          {(dog.escape_risk || dog.medical_alert) && (
                            <AlertCircleIcon size={12} className="text-red-500" />
                          )}
                        </div>
                        <p className="text-xs text-muted-foreground">{dog.breed} · {dog.age ? `${dog.age} yrs` : 'Age unknown'}</p>
                      </div>
                    </div>
                    <div className="flex gap-1.5">
                      {dog.boarding_eligible && <Badge className="text-xs bg-green-100 text-green-700">Boarding</Badge>}
                      {dog.daycare_eligible && <Badge className="text-xs bg-blue-100 text-blue-700">Daycare</Badge>}
                      {!dog.boarding_eligible && !dog.daycare_eligible && (
                        <Badge className="text-xs bg-amber-100 text-amber-700">M&G required</Badge>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Notes */}
        {household.general_notes && (
          <Card>
            <CardHeader className="pb-2 pt-4">
              <CardTitle className="text-sm">Notes</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm">{household.general_notes}</p>
            </CardContent>
          </Card>
        )}

        {/* Recent bookings */}
        <Card>
          <CardHeader className="pb-2 pt-4">
            <CardTitle className="text-sm">Recent Bookings</CardTitle>
          </CardHeader>
          <CardContent>
            {bookings.length === 0 ? (
              <p className="text-sm text-muted-foreground">No bookings on record</p>
            ) : (
              <div className="space-y-2">
                {bookings.map(b => (
                  <div key={b.id} className="flex items-center justify-between py-2 border-b last:border-0">
                    <div>
                      <p className="text-sm">
                        {new Date(b.check_in_date).toLocaleDateString()} — {new Date(b.check_out_date).toLocaleDateString()}
                      </p>
                      <p className="text-xs text-muted-foreground">{b.dog_ids?.length} dog{b.dog_ids?.length !== 1 ? 's' : ''}</p>
                    </div>
                    <Badge className={`text-xs ${STATUS_COLORS[b.status] || 'bg-gray-100 text-gray-600'}`}>
                      {b.status?.replace('_', ' ')}
                    </Badge>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

      </main>

      {showAddContact && (
        <AddContactModal
          householdId={householdId}
          onClose={() => setShowAddContact(false)}
          onSuccess={() => { setShowAddContact(false); fetchData(); }}
        />
      )}
    </div>
  );
};

const AddContactModal = ({ householdId, onClose, onSuccess }) => {
  const [form, setForm] = useState({
    first_name: '', last_name: '', phone: '', email: '',
    contact_type: 'secondary', relationship_to_household: '',
    is_emergency_contact: false, is_authorized_pickup: false,
  });
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    if (!form.first_name.trim()) { toast.error('First name is required'); return; }
    setSubmitting(true);
    try {
      await api.post(`/households/${householdId}/contacts`, form);
      toast.success('Contact added');
      onSuccess();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to add contact');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-end md:items-center justify-center p-4">
      <div className="bg-white rounded-t-2xl md:rounded-2xl w-full max-w-md max-h-[90vh] overflow-y-auto">
        <div className="p-6 space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-lg font-bold">Add Contact</h2>
            <button onClick={onClose} className="text-muted-foreground text-xl">×</button>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label>First Name *</Label>
              <Input value={form.first_name} onChange={e => setForm(f=>({...f,first_name:e.target.value}))} className="mt-1" />
            </div>
            <div>
              <Label>Last Name</Label>
              <Input value={form.last_name} onChange={e => setForm(f=>({...f,last_name:e.target.value}))} className="mt-1" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label>Phone</Label>
              <Input value={form.phone} onChange={e => setForm(f=>({...f,phone:e.target.value}))} className="mt-1" />
            </div>
            <div>
              <Label>Email</Label>
              <Input value={form.email} onChange={e => setForm(f=>({...f,email:e.target.value}))} className="mt-1" />
            </div>
          </div>
          <div>
            <Label>Relationship</Label>
            <Input placeholder="e.g. Spouse, dog walker, neighbor"
              value={form.relationship_to_household}
              onChange={e => setForm(f=>({...f,relationship_to_household:e.target.value}))} className="mt-1" />
          </div>
          <div>
            <Label>Contact Type</Label>
            <select className="w-full mt-1 border rounded-md px-3 py-2 text-sm bg-background"
              value={form.contact_type} onChange={e => setForm(f=>({...f,contact_type:e.target.value}))}>
              <option value="secondary">Secondary</option>
              <option value="emergency">Emergency</option>
              <option value="pickup_only">Pickup only</option>
            </select>
          </div>
          <div className="flex gap-4">
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input type="checkbox" checked={form.is_emergency_contact}
                onChange={e => setForm(f=>({...f,is_emergency_contact:e.target.checked}))} className="w-4 h-4" />
              Emergency contact
            </label>
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input type="checkbox" checked={form.is_authorized_pickup}
                onChange={e => setForm(f=>({...f,is_authorized_pickup:e.target.checked}))} className="w-4 h-4" />
              Authorized pickup
            </label>
          </div>
          <div className="flex gap-3 pt-2">
            <Button variant="outline" className="flex-1" onClick={onClose}>Cancel</Button>
            <Button className="flex-1" onClick={handleSubmit} disabled={submitting}>
              {submitting ? 'Adding...' : 'Add Contact'}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CustomerProfilePage;
