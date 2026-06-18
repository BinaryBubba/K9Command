import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import useAuthStore from '../store/authStore';
import api from '../utils/api';
import { Button } from '../components/ui/button';
import { Card, CardContent } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Badge } from '../components/ui/badge';
import { ArrowLeftIcon, PlusIcon, SearchIcon, UsersIcon, DogIcon } from 'lucide-react';
import { toast } from 'sonner';
import PinModal from '../components/PinModal';

const AdminCustomersPage = () => {
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const [households, setHouseholds] = useState([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [newHousehold, setNewHousehold] = useState(null); // triggers M&G prompt
  const [showMagPin, setShowMagPin] = useState(false);

  const fetchHouseholds = useCallback(async () => {
    try {
      const res = await api.get('/households', { params: { search, limit: 100 } });
      setHouseholds(res.data);
    } catch {
      toast.error('Failed to load customers');
    } finally {
      setLoading(false);
    }
  }, [search]);

  useEffect(() => {
    if (!user) { navigate('/auth'); return; }
    const timer = setTimeout(fetchHouseholds, 300);
    return () => clearTimeout(timer);
  }, [user, navigate, fetchHouseholds]);

  return (
    <div className="min-h-screen bg-[#F9F7F2]">
      <header className="bg-white border-b shadow-sm sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="sm" onClick={() => navigate(-1)}>
              <ArrowLeftIcon size={18} />
            </Button>
            <h1 className="text-lg font-serif font-bold text-primary">Customers</h1>
          </div>
          <Button size="sm" onClick={() => setShowCreate(true)}>
            <PlusIcon size={16} className="mr-1" /> New
          </Button>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-6 space-y-4">
        <div className="relative">
          <SearchIcon size={16} className="absolute left-3 top-3 text-muted-foreground" />
          <Input
            placeholder="Search households..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>

        {loading ? (
          <div className="flex justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-primary"></div>
          </div>
        ) : households.length === 0 ? (
          <Card><CardContent className="py-12 text-center text-muted-foreground">
            {search ? 'No households match your search' : 'No customers yet'}
          </CardContent></Card>
        ) : (
          <div className="space-y-2">
            {households.map(h => (
              <Card key={h.id} className="cursor-pointer hover:shadow-md transition-shadow"
                onClick={() => navigate(`/admin/customers/${h.id}`)}>
                <CardContent className="py-3 px-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="bg-primary/10 p-2 rounded-full">
                        <UsersIcon size={16} className="text-primary" />
                      </div>
                      <div>
                        <p className="font-medium">{h.display_name}</p>
                        <div className="flex items-center gap-3 mt-0.5">
                          <MagStatusBadge status={h.meet_and_greet_status} />
                        </div>
                      </div>
                    </div>
                    <Badge variant={h.status === 'active' ? 'outline' : 'secondary'} className="text-xs">
                      {h.status}
                    </Badge>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </main>

      {newHousehold && (
        <MagPromptModal
          household={newHousehold}
          showPin={showMagPin}
          onSchedule={() => { navigate(`/admin/meet-and-greet?household_id=${newHousehold.id}`); setNewHousehold(null); }}
          onPinOverride={() => setShowMagPin(true)}
          onSkip={() => { setNewHousehold(null); setShowMagPin(false); toast.success('Customer created — M&G skipped'); }}
          onPinCancel={() => setShowMagPin(false)}
        />
      )}
      {showCreate && (
        <CreateHouseholdModal
          onClose={() => setShowCreate(false)}
          onSuccess={(household) => { setShowCreate(false); fetchHouseholds(); setNewHousehold(household); }}
        />
      )}
    </div>
  );
};

const MagStatusBadge = ({ status }) => {
  const map = {
    required: { label: 'M&G Required', className: 'text-amber-600' },
    scheduled: { label: 'M&G Scheduled', className: 'text-blue-600' },
    completed: { label: 'M&G Complete', className: 'text-green-600' },
    waived: { label: 'M&G Waived', className: 'text-gray-500' },
  };
  const s = map[status] || map.required;
  return <span className={`text-xs ${s.className}`}>{s.label}</span>;
};

const CreateHouseholdModal = ({ onClose, onSuccess }) => {
  const [form, setForm] = useState({
    display_name: '',
    referral_source: '',
    general_notes: '',
    contact_first_name: '',
    contact_last_name: '',
    contact_phone: '',
    contact_email: '',
  });
  const [duplicates, setDuplicates] = useState([]);
  const [submitting, setSubmitting] = useState(false);

  const checkDuplicates = async () => {
    if (!form.display_name && !form.contact_email && !form.contact_phone) return;
    try {
      const res = await api.get('/households/search/duplicates', {
        params: {
          name: form.display_name || undefined,
          email: form.contact_email || undefined,
          phone: form.contact_phone || undefined,
        }
      });
      setDuplicates(res.data.matches || []);
    } catch { /* silent */ }
  };

  const handleSubmit = async () => {
    if (!form.display_name.trim()) { toast.error('Household name is required'); return; }
    setSubmitting(true);
    try {
      if (!form.contact_first_name.trim()) { toast.error('Primary contact first name is required'); setSubmitting(false); return; }
      if (!form.emergency_first_name?.trim()) { toast.error('Emergency contact first name is required'); setSubmitting(false); return; }
      if (!form.emergency_phone?.trim()) { toast.error('Emergency contact phone is required'); setSubmitting(false); return; }
      const payload = {
        display_name: form.display_name,
        referral_source: form.referral_source || undefined,
        general_notes: form.general_notes || undefined,
        primary_contact: {
          first_name: form.contact_first_name,
          last_name: form.contact_last_name,
          phone: form.contact_phone,
          email: form.contact_email,
          is_authorized_pickup: true,
          is_emergency_contact: false,
        },
      };
      const hhRes = await api.post('/households', payload);
      const hhId = hhRes.data.id;
      if (form.secondary_first_name?.trim()) {
        await api.post(`/households/${hhId}/contacts`, {
          first_name: form.secondary_first_name,
          last_name: form.secondary_last_name,
          phone: form.secondary_phone,
          email: form.secondary_email,
          contact_type: 'secondary',
          is_authorized_pickup: true,
          is_emergency_contact: false,
        }).catch(() => {});
      }
      await api.post(`/households/${hhId}/contacts`, {
        first_name: form.emergency_first_name,
        last_name: form.emergency_last_name,
        phone: form.emergency_phone,
        relationship_to_household: form.emergency_relationship,
        contact_type: 'emergency',
        is_authorized_pickup: false,
        is_emergency_contact: true,
      });
      toast.success('Household created');
      onSuccess({ id: hhId, display_name: form.display_name });
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to create household');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-end md:items-center justify-center p-4">
      <div className="bg-white rounded-t-2xl md:rounded-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="p-6 space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-lg font-bold">New Customer</h2>
            <button onClick={onClose} className="text-muted-foreground text-xl">×</button>
          </div>

          <div>
            <Label>Household Name *</Label>
            <Input
              placeholder="e.g. Smith Family"
              value={form.display_name}
              onChange={e => setForm(f => ({...f, display_name: e.target.value}))}
              onBlur={checkDuplicates}
              className="mt-1"
            />
          </div>

          {duplicates.length > 0 && (
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
              <p className="text-sm font-medium text-amber-800 mb-2">Possible duplicates found:</p>
              {duplicates.map((d, i) => (
                <p key={i} className="text-xs text-amber-700">· {d.household.display_name}</p>
              ))}
            </div>
          )}

          <div className="border-t pt-4 space-y-3">
            <p className="text-sm font-medium text-muted-foreground">Primary Contact *</p>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>First Name *</Label>
                <Input value={form.contact_first_name}
                  onChange={e => setForm(f => ({...f, contact_first_name: e.target.value}))}
                  className="mt-1" placeholder="Required" />
              </div>
              <div>
                <Label>Last Name</Label>
                <Input value={form.contact_last_name}
                  onChange={e => setForm(f => ({...f, contact_last_name: e.target.value}))}
                  className="mt-1" />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>Phone</Label>
                <Input value={form.contact_phone}
                  onChange={e => setForm(f => ({...f, contact_phone: e.target.value}))}
                  onBlur={checkDuplicates} className="mt-1" />
              </div>
              <div>
                <Label>Email</Label>
                <Input value={form.contact_email}
                  onChange={e => setForm(f => ({...f, contact_email: e.target.value}))}
                  onBlur={checkDuplicates} className="mt-1" />
              </div>
            </div>
          </div>

          <div className="border-t pt-4 space-y-3">
            <p className="text-sm font-medium text-muted-foreground">Secondary Contact <span className="text-xs font-normal">(optional — spouse, partner)</span></p>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>First Name</Label>
                <Input value={form.secondary_first_name || ""}
                  onChange={e => setForm(f => ({...f, secondary_first_name: e.target.value}))}
                  className="mt-1" />
              </div>
              <div>
                <Label>Last Name</Label>
                <Input value={form.secondary_last_name || ""}
                  onChange={e => setForm(f => ({...f, secondary_last_name: e.target.value}))}
                  className="mt-1" />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>Phone</Label>
                <Input value={form.secondary_phone || ""}
                  onChange={e => setForm(f => ({...f, secondary_phone: e.target.value}))}
                  className="mt-1" />
              </div>
              <div>
                <Label>Email</Label>
                <Input value={form.secondary_email || ""}
                  onChange={e => setForm(f => ({...f, secondary_email: e.target.value}))}
                  className="mt-1" />
              </div>
            </div>
          </div>

          <div className="border-t pt-4 space-y-3">
            <p className="text-sm font-medium text-muted-foreground">Emergency Contact <span className="text-xs text-red-500">*required</span></p>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>First Name *</Label>
                <Input value={form.emergency_first_name || ""}
                  onChange={e => setForm(f => ({...f, emergency_first_name: e.target.value}))}
                  className="mt-1" placeholder="Required" />
              </div>
              <div>
                <Label>Last Name</Label>
                <Input value={form.emergency_last_name || ""}
                  onChange={e => setForm(f => ({...f, emergency_last_name: e.target.value}))}
                  className="mt-1" />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>Phone *</Label>
                <Input value={form.emergency_phone || ""}
                  onChange={e => setForm(f => ({...f, emergency_phone: e.target.value}))}
                  className="mt-1" placeholder="Required" />
              </div>
              <div>
                <Label>Relationship</Label>
                <Input value={form.emergency_relationship || ""}
                  onChange={e => setForm(f => ({...f, emergency_relationship: e.target.value}))}
                  className="mt-1" placeholder="e.g. Neighbor, sibling" />
              </div>
            </div>
          </div>

          <div>
            <Label>Referral Source</Label>
            <Input placeholder="Google, word of mouth, etc."
              value={form.referral_source}
              onChange={e => setForm(f => ({...f, referral_source: e.target.value}))}
              className="mt-1" />
          </div>

          <div>
            <Label>Notes</Label>
            <Textarea value={form.general_notes}
              onChange={e => setForm(f => ({...f, general_notes: e.target.value}))}
              className="mt-1" rows={2} />
          </div>

          <div className="flex gap-3 pt-2">
            <Button variant="outline" className="flex-1" onClick={onClose}>Cancel</Button>
            <Button className="flex-1" onClick={handleSubmit} disabled={submitting}>
              {submitting ? 'Creating...' : 'Create Customer'}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};


const MagPromptModal = ({ household, onSchedule, onSkip, onPinOverride, showPin, onPinCancel }) => (
  <>
    {!showPin ? (
      <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl w-full max-w-sm p-6 space-y-4">
          <div className="text-center">
            <div className="text-3xl mb-2">🐾</div>
            <h2 className="text-lg font-bold">Schedule Meet & Greet?</h2>
            <p className="text-sm text-muted-foreground mt-1">
              {household?.display_name} has been created. Would you like to schedule a meet & greet?
            </p>
          </div>
          <button className="w-full py-3 bg-primary text-primary-foreground rounded-xl font-medium" onClick={onSchedule}>
            Schedule M&G Now
          </button>
          <button className="w-full py-2 text-sm text-muted-foreground hover:text-foreground" onClick={onPinOverride}>
            Skip (requires manager PIN)
          </button>
        </div>
      </div>
    ) : (
      <PinModal
        title="Skip M&G"
        message="Enter manager PIN to skip M&G scheduling"
        onVerified={onSkip}
        onCancel={onPinCancel}
      />
    )}
  </>
);

export default AdminCustomersPage;
