import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import useAuthStore from '../store/authStore';
import api from '../utils/api';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { ArrowLeftIcon, DogIcon, CalendarIcon, PlusIcon, PhoneIcon, MailIcon, UserIcon } from 'lucide-react';
import { toast } from 'sonner';

const STATUS_COLORS = {
  confirmed: 'bg-blue-100 text-blue-700',
  checked_in: 'bg-green-100 text-green-700',
  checked_out: 'bg-gray-100 text-gray-600',
  cancelled: 'bg-red-100 text-red-600',
};

const AdminHouseholdPage = () => {
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const { householdId } = useParams();
  const [household, setHousehold] = useState(null);
  const [contacts, setContacts] = useState([]);
  const [dogs, setDogs] = useState([]);
  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [linkedUsers, setLinkedUsers] = useState([]);
  const [allCustomers, setAllCustomers] = useState([]);
  const [showLinkUser, setShowLinkUser] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      const [hhRes, contactsRes, dogsRes, bookingsRes, customersRes] = await Promise.all([
        api.get(`/households/${householdId}`),
        api.get(`/households/${householdId}/contacts`).catch(() => ({ data: [] })),
        api.get('/dogs', { params: { household_id: householdId } }),
        api.get('/bookings', { params: { household_id: householdId, limit: 20 } }),
        api.get('/users', { params: { role: 'customer', limit: 100 } }).catch(() => ({ data: [] })),
      ]);
      setHousehold(hhRes.data);
      setContacts(contactsRes.data || []);
      setDogs(dogsRes.data?.dogs || dogsRes.data || []);
      setBookings(bookingsRes.data || []);
      const customers = customersRes.data || [];
      setAllCustomers(customers);
      setLinkedUsers(customers.filter(u => u.household_id === householdId));
    } catch { toast.error('Failed to load customer'); }
    finally { setLoading(false); }
  }, [householdId]);

  useEffect(() => {
    if (!user) { navigate('/auth'); return; }
    fetchData();
  }, [user, navigate, fetchData]);

  const MAG_COLORS = {
    required: 'bg-amber-100 text-amber-700',
    scheduled: 'bg-blue-100 text-blue-700',
    completed: 'bg-green-100 text-green-700',
    waived: 'bg-gray-100 text-gray-600',
  };

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-primary"></div>
    </div>
  );
  if (!household) return <div className="p-4">Customer not found</div>;

  return (
    <div className="min-h-screen bg-[#F9F7F2]">
      <header className="bg-white border-b shadow-sm sticky top-0 z-10">
        <div className="max-w-3xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="sm" onClick={() => navigate('/admin/customers')}>
              <ArrowLeftIcon size={18} />
            </Button>
            <div>
              <h1 className="text-base font-serif font-bold text-primary">{household.display_name}</h1>
              <p className="text-xs text-muted-foreground">Customer since {new Date(household.created_at).toLocaleDateString([], {month:'short',year:'numeric'})}</p>
            </div>
          </div>
          <div className="flex gap-2">
            {household.meet_and_greet_status && household.meet_and_greet_status !== 'completed' && (
              <Badge className={`text-xs ${MAG_COLORS[household.meet_and_greet_status] || ''}`}>
                M&G {household.meet_and_greet_status}
              </Badge>
            )}
            <Button size="sm" variant="outline"
              onClick={() => navigate(`/admin/meet-and-greet?household_id=${householdId}`)}>
              Schedule M&G
            </Button>
          </div>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 py-6 space-y-4">
        {/* Contacts */}
        <Card>
          <CardHeader className="pb-2 pt-4 px-4">
            <CardTitle className="text-sm flex items-center justify-between">
              Contacts
            </CardTitle>
          </CardHeader>
          <CardContent className="px-4 pb-4 space-y-3">
            {contacts.length === 0 ? (
              <p className="text-sm text-muted-foreground">No contacts on file</p>
            ) : contacts.map(c => (
              <div key={c.id} className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <UserIcon size={14} className="text-muted-foreground" />
                    <p className="text-sm font-medium">{c.first_name} {c.last_name}</p>
                    {c.is_authorized_pickup && <Badge className="text-xs bg-green-100 text-green-700">Authorized pickup</Badge>}
                    {c.is_emergency_contact && <Badge className="text-xs bg-red-100 text-red-700">Emergency</Badge>}
                  </div>
                  {c.phone && <p className="text-xs text-muted-foreground ml-5">{c.phone}</p>}
                  {c.email && <p className="text-xs text-muted-foreground ml-5">{c.email}</p>}
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Dogs */}
        <Card>
          <CardHeader className="pb-2 pt-4 px-4">
            <CardTitle className="text-sm flex items-center justify-between">
              Dogs ({dogs.length})
              <Button size="sm" variant="outline" className="h-7 text-xs"
                onClick={() => navigate(`/admin/customers/${householdId}/add-dog`)}>
                <PlusIcon size={12} className="mr-1" /> Add Dog
              </Button>
            </CardTitle>
          </CardHeader>
          <CardContent className="px-4 pb-4 space-y-2">
            {dogs.length === 0 ? (
              <p className="text-sm text-muted-foreground">No dogs registered</p>
            ) : dogs.map(dog => (
              <div key={dog.id}
                className="flex items-center justify-between p-2 rounded-lg border hover:bg-muted/50 cursor-pointer"
                onClick={() => navigate(`/admin/dogs/${dog.id}`)}>
                <div className="flex items-center gap-2">
                  {dog.photo_url ? (
                    <img src={dog.photo_url} alt={dog.name} className="w-8 h-8 rounded-full object-cover" />
                  ) : (
                    <div className="bg-primary/10 p-1.5 rounded-full">
                      <DogIcon size={14} className="text-primary" />
                    </div>
                  )}
                  <div>
                    <p className="text-sm font-medium">{dog.name}</p>
                    <p className="text-xs text-muted-foreground">
                      {[dog.breed, dog.age ? `${dog.age}y` : null, dog.weight ? `${dog.weight}lbs` : null].filter(Boolean).join(' · ')}
                    </p>
                  </div>
                </div>
                <div className="flex gap-1">
                  {dog.meet_and_greet_status === 'completed' && <Badge className="text-xs bg-green-100 text-green-700">M&G ✓</Badge>}
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Bookings */}
        <Card>
          <CardHeader className="pb-2 pt-4 px-4">
            <CardTitle className="text-sm">Booking History ({bookings.length})</CardTitle>
          </CardHeader>
          <CardContent className="px-4 pb-4 space-y-2">
            {bookings.length === 0 ? (
              <p className="text-sm text-muted-foreground">No bookings on record</p>
            ) : bookings.map(b => (
              <div key={b.id}
                className="flex items-center justify-between p-2 rounded-lg border hover:bg-muted/50 cursor-pointer"
                onClick={() => navigate(`/admin/bookings/${b.id}`)}>
                <div className="flex items-center gap-2">
                  <CalendarIcon size={14} className="text-muted-foreground" />
                  <div>
                    <p className="text-sm">
                      {new Date(b.check_in_date).toLocaleDateString([], {month:'short',day:'numeric'})}
                      {' — '}
                      {new Date(b.check_out_date).toLocaleDateString([], {month:'short',day:'numeric',year:'numeric'})}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {b.dog_names?.join(', ') || `${b.dog_ids?.length || 0} dog(s)`}
                    </p>
                  </div>
                </div>
                <Badge className={`text-xs ${STATUS_COLORS[b.status?.toLowerCase()] || 'bg-gray-100 text-gray-600'}`}>
                  {b.status?.replace('_',' ')}
                </Badge>
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Linked Customer Accounts */}
        <Card>
          <CardHeader className="pb-2 pt-4 px-4">
            <CardTitle className="text-sm flex items-center justify-between">
              Linked Customer Accounts ({linkedUsers.length})
              <Button size="sm" variant="outline" className="h-7 text-xs" onClick={() => setShowLinkUser(!showLinkUser)}>
                Link Account
              </Button>
            </CardTitle>
          </CardHeader>
          <CardContent className="px-4 pb-4">
            {linkedUsers.length === 0 ? (
              <p className="text-xs text-amber-600">No customer accounts linked — customers won't see their bookings online</p>
            ) : linkedUsers.map(u => (
              <div key={u.id} className="flex items-center gap-2 py-1">
                <UserIcon size={14} className="text-muted-foreground" />
                <p className="text-sm">{u.full_name} · {u.email}</p>
              </div>
            ))}
            {showLinkUser && (
              <div className="mt-3 space-y-2">
                <p className="text-xs text-muted-foreground">Select a customer account to link:</p>
                <select className="w-full border rounded-md px-3 py-2 text-sm bg-background"
                  onChange={async (e) => {
                    if (!e.target.value) return;
                    try {
                      await api.patch(`/users/${e.target.value}/household`, { household_id: householdId });
                      toast.success('Account linked');
                      setShowLinkUser(false);
                      fetchData();
                    } catch { toast.error('Failed to link'); }
                  }}>
                  <option value="">Select customer...</option>
                  {allCustomers.filter(u => !u.household_id || u.household_id === householdId).map(u => (
                    <option key={u.id} value={u.id}>{u.full_name} — {u.email}</option>
                  ))}
                </select>
              </div>
            )}
          </CardContent>
        </Card>

        {household.general_notes && (
          <Card>
            <CardContent className="py-3 px-4">
              <p className="text-xs font-medium text-muted-foreground mb-1">Notes</p>
              <p className="text-sm">{household.general_notes}</p>
            </CardContent>
          </Card>
        )}
      </main>
    </div>
  );
};

export default AdminHouseholdPage;
