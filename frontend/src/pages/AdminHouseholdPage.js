import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import useAuthStore from '../store/authStore';
import api from '../utils/api';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import {
  ArrowLeftIcon, DogIcon, CalendarIcon, PlusIcon, UserIcon,
  PencilIcon, SaveIcon, XIcon, CheckCircleIcon, AlertCircleIcon,
  ShieldCheckIcon, EyeIcon, EyeOffIcon
} from 'lucide-react';
import { toast } from 'sonner';

const STATUS_COLORS = {
  confirmed: 'bg-blue-100 text-blue-700',
  checked_in: 'bg-green-100 text-green-700',
  checked_out: 'bg-gray-100 text-gray-600',
  cancelled: 'bg-red-100 text-red-600',
};

const MAG_COLORS = {
  required: 'bg-amber-100 text-amber-700',
  scheduled: 'bg-blue-100 text-blue-700',
  completed: 'bg-green-100 text-green-700',
  waived: 'bg-gray-100 text-gray-600',
};

const AdminHouseholdPage = () => {
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const { householdId } = useParams();
  const [household, setHousehold] = useState(null);
  const [contacts, setContacts] = useState([]);
  const [dogs, setDogs] = useState([]);
  const [bookings, setBookings] = useState([]);
  const [notes, setNotes] = useState([]);
  const [linkedUsers, setLinkedUsers] = useState([]);
  const [allCustomers, setAllCustomers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [editForm, setEditForm] = useState({ display_name: '', general_notes: '' });
  const [saving, setSaving] = useState(false);
  const [showCancelled, setShowCancelled] = useState(false);
  const [showAddContact, setShowAddContact] = useState(false);
  const [showAddNote, setShowAddNote] = useState(false);
  const [noteText, setNoteText] = useState('');
  const [showLinkUser, setShowLinkUser] = useState(false);
  const [tempPassword, setTempPassword] = useState(null);

  const isManager = ['admin','manager','ADMIN','MANAGER'].includes(user?.role);

  const fetchData = useCallback(async () => {
    try {
      const [hhRes, contactsRes, dogsRes, bookingsRes, customersRes] = await Promise.all([
        api.get(`/households/${householdId}`),
        api.get(`/households/${householdId}/contacts`).catch(() => ({ data: [] })),
        api.get('/dogs', { params: { household_id: householdId } }),
        api.get('/bookings', { params: { household_id: householdId, limit: 50 } }),
        api.get('/users', { params: { role: 'customer', limit: 100 } }).catch(() => ({ data: [] })),
      ]);
      setHousehold(hhRes.data);
      setEditForm({ display_name: hhRes.data.display_name || '', general_notes: hhRes.data.general_notes || '' });
      setContacts(contactsRes.data || []);
      setDogs(dogsRes.data?.dogs || dogsRes.data || []);
      setBookings(bookingsRes.data || []);
      const customers = customersRes.data || [];
      setAllCustomers(customers);
      setLinkedUsers(customers.filter(u => u.household_id === householdId));
      // Load notes from localStorage for now
      const savedNotes = JSON.parse(localStorage.getItem(`household_notes_${householdId}`) || '[]');
      setNotes(savedNotes);
    } catch { toast.error('Failed to load'); }
    finally { setLoading(false); }
  }, [householdId]);

  useEffect(() => {
    if (!user) { navigate('/auth'); return; }
    fetchData();
  }, [user, navigate, fetchData]);

  const handleSave = async () => {
    setSaving(true);
    try {
      await api.patch(`/households/${householdId}`, editForm);
      toast.success('Saved');
      setEditing(false);
      fetchData();
    } catch { toast.error('Failed'); }
    finally { setSaving(false); }
  };

  const handleMagUpdate = async (status) => {
    try {
      await api.patch(`/households/${householdId}`, { meet_and_greet_status: status });
      toast.success(`M&G status updated to ${status}`);
      fetchData();
    } catch { toast.error('Failed'); }
  };

  const handleAddNote = () => {
    if (!noteText.trim()) return;
    const note = { id: Date.now(), text: noteText, created_by: user.full_name, created_at: new Date().toISOString() };
    const updated = [note, ...notes];
    localStorage.setItem(`household_notes_${householdId}`, JSON.stringify(updated));
    setNotes(updated);
    setNoteText('');
    setShowAddNote(false);
    toast.success('Note added');
  };

  const handleSendPortalInvite = async (userId) => {
    try {
      const res = await api.post(`/users/${userId}/reset-password`);
      setTempPassword(res.data.temp_password);
      toast.success('Temporary password generated');
    } catch { toast.error('Failed'); }
  };

  const handleLinkUser = async (userId) => {
    try {
      await api.patch(`/users/${userId}/household`, { household_id: householdId });
      toast.success('Account linked');
      setShowLinkUser(false);
      fetchData();
    } catch { toast.error('Failed to link'); }
  };

  const visibleBookings = showCancelled
    ? bookings
    : bookings.filter(b => !['cancelled','checked_out'].includes(b.status?.toLowerCase()));

  const cancelledCount = bookings.filter(b => ['cancelled','checked_out'].includes(b.status?.toLowerCase())).length;

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
              <p className="text-xs text-muted-foreground">
                Customer since {new Date(household.created_at).toLocaleDateString([], {month:'short',year:'numeric'})}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Badge className={`text-xs ${MAG_COLORS[household.meet_and_greet_status] || MAG_COLORS.required}`}>
              M&G {household.meet_and_greet_status || 'required'}
            </Badge>
            {editing ? (
              <>
                <Button size="sm" variant="outline" onClick={() => setEditing(false)}>Cancel</Button>
                <Button size="sm" onClick={handleSave} disabled={saving}>
                  <SaveIcon size={14} className="mr-1" />{saving ? 'Saving...' : 'Save'}
                </Button>
              </>
            ) : (
              <Button size="sm" variant="outline" onClick={() => setEditing(true)}>
                <PencilIcon size={14} className="mr-1" />Edit
              </Button>
            )}
          </div>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 py-6 space-y-4">

        {/* Edit form */}
        {editing && (
          <Card className="border-primary/30 bg-primary/5">
            <CardContent className="py-4 px-4 space-y-3">
              <div>
                <Label>Household Name</Label>
                <Input value={editForm.display_name}
                  onChange={e => setEditForm(f=>({...f,display_name:e.target.value}))} className="mt-1" />
              </div>
              <div>
                <Label>General Notes</Label>
                <Textarea value={editForm.general_notes} rows={2}
                  onChange={e => setEditForm(f=>({...f,general_notes:e.target.value}))} className="mt-1" />
              </div>
            </CardContent>
          </Card>
        )}

        {/* M&G Management (managers only) */}
        {isManager && (
          <Card>
            <CardHeader className="pb-2 pt-4 px-4">
              <CardTitle className="text-sm flex items-center justify-between">
                Meet & Greet
                <div className="flex gap-1">
                  <Button size="sm" variant="outline" className="h-7 text-xs"
                    onClick={() => navigate(`/admin/meet-and-greet?household_id=${householdId}`)}>
                    Schedule
                  </Button>
                  <Button size="sm" className="h-7 text-xs bg-green-600 hover:bg-green-700"
                    onClick={() => handleMagUpdate('completed')}>
                    Mark Complete
                  </Button>
                  <Button size="sm" variant="outline" className="h-7 text-xs"
                    onClick={() => handleMagUpdate('waived')}>
                    Waive
                  </Button>
                </div>
              </CardTitle>
            </CardHeader>
            <CardContent className="px-4 pb-3">
              <p className="text-sm">Status: <span className="font-medium capitalize">{household.meet_and_greet_status || 'required'}</span></p>
            </CardContent>
          </Card>
        )}

        {/* Contacts */}
        <Card>
          <CardHeader className="pb-2 pt-4 px-4">
            <CardTitle className="text-sm flex items-center justify-between">
              Contacts ({contacts.length})
              <Button size="sm" variant="outline" className="h-7 text-xs" onClick={() => setShowAddContact(!showAddContact)}>
                <PlusIcon size={12} className="mr-1" />Add
              </Button>
            </CardTitle>
          </CardHeader>
          <CardContent className="px-4 pb-4">
            {showAddContact && (
              <AddContactForm householdId={householdId} onSaved={() => { setShowAddContact(false); fetchData(); }} onCancel={() => setShowAddContact(false)} />
            )}
            {contacts.length === 0 && !showAddContact ? (
              <p className="text-sm text-muted-foreground">No contacts on file</p>
            ) : contacts.map(c => (
              <div key={c.id} className="flex items-start justify-between py-2 border-b last:border-0">
                <div>
                  <div className="flex items-center gap-2 flex-wrap">
                    <p className="text-sm font-medium">{c.first_name} {c.last_name}</p>
                    {c.is_authorized_pickup && <Badge className="text-xs bg-green-100 text-green-700">Pickup</Badge>}
                    {c.is_emergency_contact && <Badge className="text-xs bg-red-100 text-red-700">Emergency</Badge>}
                    {c.contact_type && <Badge variant="outline" className="text-xs capitalize">{c.contact_type}</Badge>}
                  </div>
                  {c.phone && <p className="text-xs text-muted-foreground">{c.phone}</p>}
                  {c.email && <p className="text-xs text-muted-foreground">{c.email}</p>}
                </div>
                {editing && (
                  <button className="text-xs text-red-500 hover:underline ml-2"
                    onClick={async () => {
                      try {
                        await api.delete(`/households/${householdId}/contacts/${c.id}`).catch(() =>
                          api.patch(`/households/${householdId}/contacts/${c.id}`, { is_active: false })
                        );
                        fetchData();
                      } catch { toast.error('Failed to remove'); }
                    }}>Remove</button>
                )}
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
                onClick={() => navigate(`/admin/dogs/new?household_id=${householdId}`)}>
                <PlusIcon size={12} className="mr-1" />Add Dog
              </Button>
            </CardTitle>
          </CardHeader>
          <CardContent className="px-4 pb-4 space-y-2">
            {dogs.length === 0 ? (
              <p className="text-sm text-muted-foreground">No dogs registered</p>
            ) : dogs.map(dog => {
              const magOk = dog.meet_and_greet_status === 'completed' || dog.meet_and_greet_status === 'waived';
              return (
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
                  <div className="flex gap-1 items-center">
                    <DogVaxStatus dogId={dog.id} />
                    {!magOk && <Badge className="text-xs bg-amber-100 text-amber-700">M&G needed</Badge>}
                    {magOk && <Badge className="text-xs bg-green-100 text-green-700">Ready</Badge>}
                  </div>
                </div>
              );
            })}
          </CardContent>
        </Card>

        {/* Booking History */}
        <Card>
          <CardHeader className="pb-2 pt-4 px-4">
            <CardTitle className="text-sm flex items-center justify-between">
              Booking History
              <div className="flex gap-2 items-center">
                {cancelledCount > 0 && (
                  <button className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1"
                    onClick={() => setShowCancelled(!showCancelled)}>
                    {showCancelled ? <EyeOffIcon size={12} /> : <EyeIcon size={12} />}
                    {showCancelled ? 'Hide' : `Show`} past/cancelled ({cancelledCount})
                  </button>
                )}
                <Button size="sm" variant="outline" className="h-7 text-xs"
                  onClick={() => navigate(`/admin/bookings/new?household_id=${householdId}`)}>
                  New Booking
                </Button>
              </div>
            </CardTitle>
          </CardHeader>
          <CardContent className="px-4 pb-4 space-y-2">
            {visibleBookings.length === 0 ? (
              <p className="text-sm text-muted-foreground">No bookings on record</p>
            ) : visibleBookings.map(b => (
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

        {/* Household Notes */}
        <Card>
          <CardHeader className="pb-2 pt-4 px-4">
            <CardTitle className="text-sm flex items-center justify-between">
              Staff Notes ({notes.length})
              <Button size="sm" variant="outline" className="h-7 text-xs" onClick={() => setShowAddNote(!showAddNote)}>
                <PlusIcon size={12} className="mr-1" />Add Note
              </Button>
            </CardTitle>
          </CardHeader>
          <CardContent className="px-4 pb-4">
            {showAddNote && (
              <div className="mb-3 space-y-2">
                <Textarea value={noteText} onChange={e => setNoteText(e.target.value)} rows={2} placeholder="Note about this household..." />
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={() => setShowAddNote(false)}>Cancel</Button>
                  <Button size="sm" onClick={handleAddNote}>Save Note</Button>
                </div>
              </div>
            )}
            {notes.length === 0 && !showAddNote ? (
              <p className="text-sm text-muted-foreground">No notes yet</p>
            ) : notes.map(n => (
              <div key={n.id} className="py-2 border-b last:border-0">
                <p className="text-sm">{n.text}</p>
                <p className="text-xs text-muted-foreground mt-0.5">{n.created_by} · {new Date(n.created_at).toLocaleString()}</p>
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Linked Portal Accounts */}
        <Card>
          <CardHeader className="pb-2 pt-4 px-4">
            <CardTitle className="text-sm flex items-center justify-between">
              Customer Portal Accounts ({linkedUsers.length})
              <Button size="sm" variant="outline" className="h-7 text-xs" onClick={() => setShowLinkUser(!showLinkUser)}>
                <PlusIcon size={12} className="mr-1" />Link Account
              </Button>
            </CardTitle>
          </CardHeader>
          <CardContent className="px-4 pb-4">
            {linkedUsers.length === 0 && (
              <p className="text-xs text-amber-600 mb-2">No portal accounts linked — customers can't access their bookings online</p>
            )}
            {linkedUsers.map(u => (
              <div key={u.id} className="flex items-center justify-between py-2 border-b last:border-0">
                <div>
                  <p className="text-sm font-medium">{u.full_name}</p>
                  <p className="text-xs text-muted-foreground">{u.email}</p>
                </div>
                <Button size="sm" variant="outline" className="h-7 text-xs"
                  onClick={() => handleSendPortalInvite(u.id)}>
                  Send Login
                </Button>
              </div>
            ))}
            {tempPassword && (
              <div className="mt-2 p-3 bg-green-50 border border-green-200 rounded-lg">
                <p className="text-xs font-medium text-green-800">Temporary password (share with customer):</p>
                <p className="text-lg font-mono font-bold text-green-900 mt-1">{tempPassword}</p>
                <button className="text-xs text-green-700 hover:underline mt-1" onClick={() => setTempPassword(null)}>Dismiss</button>
              </div>
            )}
            {showLinkUser && (
              <div className="mt-3 space-y-2">
                <p className="text-xs text-muted-foreground">Select a customer account to link:</p>
                <select className="w-full border rounded-md px-3 py-2 text-sm bg-background"
                  onChange={e => e.target.value && handleLinkUser(e.target.value)}>
                  <option value="">Select customer account...</option>
                  {allCustomers.filter(u => !u.household_id).map(u => (
                    <option key={u.id} value={u.id}>{u.full_name} — {u.email}</option>
                  ))}
                </select>
              </div>
            )}
          </CardContent>
        </Card>

      </main>
    </div>
  );
};

const DogVaxStatus = ({ dogId }) => {
  const [status, setStatus] = useState(null);
  useEffect(() => {
    api.get(`/vaccinations/dog/${dogId}`).then(r => {
      const vacs = r.data || [];
      const today = new Date();
      const in30 = new Date(today.getTime() + 30*24*60*60*1000);
      const hasExpired = vacs.some(v => v.expiry_date && new Date(v.expiry_date) < today);
      const hasExpiring = vacs.some(v => v.expiry_date && new Date(v.expiry_date) >= today && new Date(v.expiry_date) <= in30);
      const hasPending = vacs.some(v => v.status === 'pending');
      if (hasExpired) setStatus('red');
      else if (hasExpiring || hasPending) setStatus('amber');
      else if (vacs.length > 0) setStatus('green');
      else setStatus('none');
    }).catch(() => setStatus('none'));
  }, [dogId]);
  if (!status || status === 'none') return <Badge variant="outline" className="text-xs">No vax</Badge>;
  return <span className={`w-2.5 h-2.5 rounded-full ${status === 'green' ? 'bg-green-500' : status === 'amber' ? 'bg-amber-400' : 'bg-red-500'}`} title="Vaccination status"></span>;
};

const AddContactForm = ({ householdId, onSaved, onCancel }) => {
  const [form, setForm] = useState({ first_name:'', last_name:'', phone:'', email:'', contact_type:'secondary', is_authorized_pickup: false, is_emergency_contact: false });
  const [saving, setSaving] = useState(false);
  const handleSave = async () => {
    if (!form.first_name.trim()) { toast.error('First name required'); return; }
    setSaving(true);
    try {
      await api.post(`/households/${householdId}/contacts`, form);
      onSaved();
    } catch { toast.error('Failed to add contact'); }
    finally { setSaving(false); }
  };
  return (
    <div className="mb-3 p-3 border border-primary/30 rounded-lg bg-primary/5 space-y-2">
      <p className="text-xs font-medium text-primary">Add Contact</p>
      <div className="grid grid-cols-2 gap-2">
        <Input placeholder="First name *" value={form.first_name} onChange={e => setForm(f=>({...f,first_name:e.target.value}))} />
        <Input placeholder="Last name" value={form.last_name} onChange={e => setForm(f=>({...f,last_name:e.target.value}))} />
      </div>
      <Input placeholder="Phone" value={form.phone} onChange={e => setForm(f=>({...f,phone:e.target.value}))} />
      <Input placeholder="Email" value={form.email} onChange={e => setForm(f=>({...f,email:e.target.value}))} />
      <select className="w-full border rounded-md px-3 py-2 text-sm bg-background"
        value={form.contact_type} onChange={e => setForm(f=>({...f,contact_type:e.target.value}))}>
        <option value="secondary">Secondary</option>
        <option value="emergency">Emergency</option>
        <option value="authorized_pickup">Authorized Pickup</option>
      </select>
      <div className="flex gap-4">
        <label className="flex items-center gap-2 text-xs cursor-pointer">
          <input type="checkbox" checked={form.is_authorized_pickup}
            onChange={e => setForm(f=>({...f,is_authorized_pickup:e.target.checked}))} />
          Authorized pickup
        </label>
        <label className="flex items-center gap-2 text-xs cursor-pointer">
          <input type="checkbox" checked={form.is_emergency_contact}
            onChange={e => setForm(f=>({...f,is_emergency_contact:e.target.checked}))} />
          Emergency contact
        </label>
      </div>
      <div className="flex gap-2">
        <Button variant="outline" size="sm" className="flex-1" onClick={onCancel}>Cancel</Button>
        <Button size="sm" className="flex-1" onClick={handleSave} disabled={saving}>
          {saving ? 'Saving...' : 'Add Contact'}
        </Button>
      </div>
    </div>
  );
};

export default AdminHouseholdPage;
