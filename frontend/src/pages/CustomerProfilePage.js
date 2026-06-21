import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import useAuthStore from '../store/authStore';
import api from '../utils/api';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { ArrowLeftIcon, SaveIcon } from 'lucide-react';
import { toast } from 'sonner';

const CustomerProfilePage = () => {
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const [form, setForm] = useState({
    full_name: '', phone: '', address: '', birthday: '',
    emergency_contact_name: '', emergency_contact_phone: '',
  });
  const [household, setHousehold] = useState(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!user) { navigate('/auth'); return; }
    api.get('/users/me').then(r => {
      const u = r.data;
      setForm({
        full_name: u.full_name || '', phone: u.phone || '',
        address: u.address || '', birthday: u.birthday || '',
        emergency_contact_name: u.emergency_contact_name || '',
        emergency_contact_phone: u.emergency_contact_phone || '',
      });
      if (u.household_id) {
        api.get(`/households/${u.household_id}`).then(h => setHousehold(h.data)).catch(() => {});
      }
    }).catch(() => {});
  }, [user, navigate]);

  const handleSave = async () => {
    setSaving(true);
    try {
      await api.patch(`/users/${user.id}`, form);
      toast.success('Profile updated');
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed'); }
    finally { setSaving(false); }
  };

  return (
    <div className="min-h-screen bg-[#F9F7F2]">
      <header className="bg-white border-b shadow-sm sticky top-0 z-10">
        <div className="max-w-2xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="sm" onClick={() => navigate('/customer/dashboard')}>
              <ArrowLeftIcon size={18} />
            </Button>
            <h1 className="text-base font-serif font-bold text-primary">My Profile</h1>
          </div>
          <Button size="sm" onClick={handleSave} disabled={saving}>
            <SaveIcon size={14} className="mr-1" />{saving ? 'Saving...' : 'Save'}
          </Button>
        </div>
      </header>

      <main className="max-w-2xl mx-auto px-4 py-6 space-y-4">
        <Card>
          <CardHeader className="pb-2 pt-4"><CardTitle className="text-sm">Account</CardTitle></CardHeader>
          <CardContent className="px-4 pb-4 space-y-1">
            <p className="text-sm"><span className="text-muted-foreground">Email: </span>{user?.email}</p>
            {household && <p className="text-sm"><span className="text-muted-foreground">Household: </span>{household.display_name}</p>}
            <p className="text-xs text-muted-foreground mt-1">To change your email, contact K9 Country Club staff.</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2 pt-4"><CardTitle className="text-sm">Personal Information</CardTitle></CardHeader>
          <CardContent className="px-4 pb-4 space-y-3">
            <div><Label>Full Name</Label><Input value={form.full_name} onChange={e => setForm(f=>({...f,full_name:e.target.value}))} className="mt-1" /></div>
            <div><Label>Phone Number</Label><Input value={form.phone} onChange={e => setForm(f=>({...f,phone:e.target.value}))} className="mt-1" placeholder="(555) 000-0000" /></div>
            <div><Label>Home Address</Label><Input value={form.address} onChange={e => setForm(f=>({...f,address:e.target.value}))} className="mt-1" placeholder="123 Main St, City, State ZIP" /></div>
            <div><Label>Date of Birth</Label><Input type="date" value={form.birthday} onChange={e => setForm(f=>({...f,birthday:e.target.value}))} className="mt-1" /></div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2 pt-4"><CardTitle className="text-sm">Emergency Contact</CardTitle></CardHeader>
          <CardContent className="px-4 pb-4 space-y-3">
            <div><Label>Contact Name</Label><Input value={form.emergency_contact_name} onChange={e => setForm(f=>({...f,emergency_contact_name:e.target.value}))} className="mt-1" /></div>
            <div><Label>Contact Phone</Label><Input value={form.emergency_contact_phone} onChange={e => setForm(f=>({...f,emergency_contact_phone:e.target.value}))} className="mt-1" /></div>
          </CardContent>
        </Card>

        <Button className="w-full" onClick={handleSave} disabled={saving}>
          {saving ? 'Saving...' : 'Save Profile'}
        </Button>
      </main>
    </div>
  );
};

export default CustomerProfilePage;
