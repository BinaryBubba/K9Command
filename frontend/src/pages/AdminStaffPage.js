import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import useAuthStore from '../store/authStore';
import api from '../utils/api';
import { Button } from '../components/ui/button';
import { Card, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { PlusIcon, UserIcon, ShieldIcon, CheckCircleIcon, XCircleIcon } from 'lucide-react';
import { toast } from 'sonner';

const ROLE_COLORS = {
  admin: 'bg-purple-100 text-purple-700',
  manager: 'bg-blue-100 text-blue-700',
  staff: 'bg-green-100 text-green-700',
  customer: 'bg-gray-100 text-gray-600',
};

const AdminStaffPage = () => {
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const [staff, setStaff] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [search, setSearch] = useState('');

  const fetchStaff = useCallback(async () => {
    try {
      const res = await api.get('/users');
      setStaff(res.data.filter(u => u.role !== 'customer'));
    } catch { toast.error('Failed to load staff'); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => {
    if (!user || user.role !== 'admin') { navigate('/auth'); return; }
    fetchStaff();
  }, [user, navigate, fetchStaff]);

  const filtered = staff.filter(s =>
    s.full_name?.toLowerCase().includes(search.toLowerCase()) ||
    s.email?.toLowerCase().includes(search.toLowerCase())
  );

  const active = filtered.filter(s => s.is_active !== false);
  const inactive = filtered.filter(s => s.is_active === false);

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-primary"></div>
    </div>
  );

  return (
    <div className="min-h-screen bg-[#F9F7F2]">
      <header className="bg-white border-b shadow-sm sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between">
          <h1 className="text-lg font-serif font-bold text-primary">Staff</h1>
          <Button size="sm" onClick={() => setShowCreate(true)}>
            <PlusIcon size={16} className="mr-1" /> Add Staff
          </Button>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-6 space-y-4">
        <Input placeholder="Search by name or email..." value={search}
          onChange={e => setSearch(e.target.value)} />

        <Tabs defaultValue="active">
          <TabsList className="w-full mb-4">
            <TabsTrigger value="active" className="flex-1">Active ({active.length})</TabsTrigger>
            <TabsTrigger value="inactive" className="flex-1">Inactive ({inactive.length})</TabsTrigger>
          </TabsList>

          <TabsContent value="active">
            <StaffList staff={active} onSelect={id => navigate(`/admin/staff/${id}`)} />
          </TabsContent>
          <TabsContent value="inactive">
            <StaffList staff={inactive} onSelect={id => navigate(`/admin/staff/${id}`)} />
          </TabsContent>
        </Tabs>
      </main>

      {showCreate && (
        <CreateStaffModal
          onClose={() => setShowCreate(false)}
          onSuccess={(tempPw, name) => {
            setShowCreate(false);
            fetchStaff();
            toast.success(`${name} created! Temp password: ${tempPw}`, { duration: 15000 });
          }}
        />
      )}
    </div>
  );
};

const StaffList = ({ staff, onSelect }) => {
  if (staff.length === 0) return (
    <Card><CardContent className="py-10 text-center text-muted-foreground">No staff found</CardContent></Card>
  );
  return (
    <div className="space-y-2">
      {staff.map(s => (
        <Card key={s.id} className="cursor-pointer hover:shadow-md transition-shadow" onClick={() => onSelect(s.id)}>
          <CardContent className="py-3 px-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="bg-muted rounded-full p-2"><UserIcon size={16} /></div>
                <div>
                  <div className="flex items-center gap-2">
                    <p className="font-medium text-sm">{s.full_name}</p>
                    <Badge className={`text-xs ${ROLE_COLORS[s.role] || ROLE_COLORS.staff}`}>
                      {s.role}
                    </Badge>
                    {s.is_owner && <Badge className="text-xs bg-amber-100 text-amber-700">Owner</Badge>}
                  </div>
                  <p className="text-xs text-muted-foreground">{s.email}</p>
                  {s.phone && <p className="text-xs text-muted-foreground">{s.phone}</p>}
                </div>
              </div>
              <div className="flex items-center gap-2">
                {s.is_active !== false
                  ? <CheckCircleIcon size={16} className="text-green-500" />
                  : <XCircleIcon size={16} className="text-red-400" />
                }
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
};

const CreateStaffModal = ({ onClose, onSuccess }) => {
  const [form, setForm] = useState({
    full_name: '', email: '', phone: '', role: 'staff',
    hire_date: '', emergency_contact_name: '', emergency_contact_phone: '',
  });
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    if (!form.full_name.trim() || !form.email.trim()) {
      toast.error('Name and email are required'); return;
    }
    setSubmitting(true);
    try {
      const res = await api.post('/users', form);
      onSuccess(res.data.temp_password, res.data.full_name);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to create staff');
    } finally { setSubmitting(false); }
  };

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-end md:items-center justify-center p-4">
      <div className="bg-white rounded-t-2xl md:rounded-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="p-6 space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-lg font-bold">Add Staff Member</h2>
            <button onClick={onClose} className="text-muted-foreground text-xl">×</button>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2">
              <Label>Full Name *</Label>
              <Input value={form.full_name} onChange={e => setForm(f=>({...f,full_name:e.target.value}))} className="mt-1" />
            </div>
            <div className="col-span-2">
              <Label>Email *</Label>
              <Input type="email" value={form.email} onChange={e => setForm(f=>({...f,email:e.target.value}))} className="mt-1" />
            </div>
            <div>
              <Label>Phone</Label>
              <Input value={form.phone} onChange={e => setForm(f=>({...f,phone:e.target.value}))} className="mt-1" />
            </div>
            <div>
              <Label>Role</Label>
              <select className="w-full mt-1 border rounded-md px-3 py-2 text-sm bg-background"
                value={form.role} onChange={e => setForm(f=>({...f,role:e.target.value}))}>
                <option value="staff">Team Member</option>
                <option value="manager">Manager</option>
                <option value="admin">Admin</option>
              </select>
            </div>
            <div>
              <Label>Hire Date</Label>
              <Input type="date" value={form.hire_date} onChange={e => setForm(f=>({...f,hire_date:e.target.value}))} className="mt-1" />
            </div>
          </div>
          <div className="border-t pt-3 space-y-3">
            <p className="text-xs font-medium text-muted-foreground">Emergency Contact</p>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>Name</Label>
                <Input value={form.emergency_contact_name} onChange={e => setForm(f=>({...f,emergency_contact_name:e.target.value}))} className="mt-1" />
              </div>
              <div>
                <Label>Phone</Label>
                <Input value={form.emergency_contact_phone} onChange={e => setForm(f=>({...f,emergency_contact_phone:e.target.value}))} className="mt-1" />
              </div>
            </div>
          </div>
          <div className="bg-amber-50 border border-amber-200 rounded p-3 text-xs text-amber-800">
            A temporary password will be generated and shown once — save it to share with the staff member.
          </div>
          <div className="flex gap-3 pt-2">
            <Button variant="outline" className="flex-1" onClick={onClose}>Cancel</Button>
            <Button className="flex-1" onClick={handleSubmit} disabled={submitting}>
              {submitting ? 'Creating...' : 'Create Account'}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminStaffPage;
