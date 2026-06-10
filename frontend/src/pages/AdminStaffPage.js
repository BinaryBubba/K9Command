import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import useAuthStore from '../store/authStore';
import api from '../utils/api';
import { Button } from '../components/ui/button';
import { Card, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { ArrowLeftIcon, PlusIcon, UserIcon, SearchIcon } from 'lucide-react';
import { toast } from 'sonner';

const ROLE_COLORS = {
  admin: 'bg-purple-100 text-purple-700',
  staff: 'bg-blue-100 text-blue-700',
  customer: 'bg-gray-100 text-gray-600',
};

const AdminStaffPage = () => {
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const [staff, setStaff] = useState([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [showInvite, setShowInvite] = useState(false);

  const fetchStaff = useCallback(async () => {
    try {
      const res = await api.get('/users', { params: { role: 'staff', limit: 100 } });
      setStaff(res.data);
    } catch {
      // Fallback: try /auth/users or show empty state
      setStaff([]);
      toast.error('Failed to load staff');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!user || user.role !== 'admin') { navigate('/auth'); return; }
    fetchStaff();
  }, [user, navigate, fetchStaff]);

  const filtered = staff.filter(s =>
    !search || s.full_name?.toLowerCase().includes(search.toLowerCase()) ||
    s.email?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="min-h-screen bg-[#F9F7F2]">
      <header className="bg-white border-b shadow-sm sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="sm" onClick={() => navigate(-1)}>
              <ArrowLeftIcon size={18} />
            </Button>
            <h1 className="text-lg font-serif font-bold text-primary">Staff</h1>
          </div>
          <Button size="sm" onClick={() => setShowInvite(true)}>
            <PlusIcon size={16} className="mr-1" /> Add Staff
          </Button>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-6 space-y-4">
        <div className="relative">
          <SearchIcon size={16} className="absolute left-3 top-3 text-muted-foreground" />
          <Input placeholder="Search staff..." value={search}
            onChange={e => setSearch(e.target.value)} className="pl-9" />
        </div>

        {loading ? (
          <div className="flex justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-primary"></div>
          </div>
        ) : filtered.length === 0 ? (
          <Card><CardContent className="py-12 text-center text-muted-foreground">
            {search ? 'No staff match your search' : 'No staff accounts yet'}
          </CardContent></Card>
        ) : (
          <div className="space-y-2">
            {filtered.map(s => (
              <Card key={s.id}>
                <CardContent className="py-3 px-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="bg-blue-50 p-2 rounded-full">
                        <UserIcon size={16} className="text-blue-600" />
                      </div>
                      <div>
                        <p className="font-medium">{s.full_name}</p>
                        <p className="text-xs text-muted-foreground">{s.email}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {s.is_owner && (
                        <Badge className="text-xs bg-amber-100 text-amber-700">Owner</Badge>
                      )}
                      <Badge className={`text-xs ${ROLE_COLORS[s.role?.toLowerCase()] || ROLE_COLORS.staff}`}>
                        {s.role?.toLowerCase()}
                      </Badge>
                      <Badge variant="outline" className={`text-xs ${s.is_active ? 'text-green-600' : 'text-gray-400'}`}>
                        {s.is_active ? 'Active' : 'Inactive'}
                      </Badge>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </main>

      {showInvite && (
        <InviteStaffModal
          onClose={() => setShowInvite(false)}
          onSuccess={() => { setShowInvite(false); fetchStaff(); }}
        />
      )}
    </div>
  );
};

const InviteStaffModal = ({ onClose, onSuccess }) => {
  const [form, setForm] = useState({ full_name: '', email: '', password: '', role: 'staff' });
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    if (!form.full_name.trim()) { toast.error('Name is required'); return; }
    if (!form.email.trim()) { toast.error('Email is required'); return; }
    if (!form.password || form.password.length < 8) { toast.error('Password must be at least 8 characters'); return; }
    setSubmitting(true);
    try {
      await api.post('/auth/register', {
        full_name: form.full_name,
        email: form.email,
        password: form.password,
        role: form.role,
      });
      toast.success('Staff account created');
      onSuccess();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to create account');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-end md:items-center justify-center p-4">
      <div className="bg-white rounded-t-2xl md:rounded-2xl w-full max-w-md">
        <div className="p-6 space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-lg font-bold">Add Staff Account</h2>
            <button onClick={onClose} className="text-muted-foreground text-xl">×</button>
          </div>

          <div>
            <Label>Full Name *</Label>
            <Input value={form.full_name}
              onChange={e => setForm(f => ({...f, full_name: e.target.value}))}
              className="mt-1" placeholder="Jane Smith" />
          </div>
          <div>
            <Label>Email *</Label>
            <Input type="email" value={form.email}
              onChange={e => setForm(f => ({...f, email: e.target.value}))}
              className="mt-1" placeholder="jane@k9cc.com" />
          </div>
          <div>
            <Label>Temporary Password *</Label>
            <Input type="password" value={form.password}
              onChange={e => setForm(f => ({...f, password: e.target.value}))}
              className="mt-1" placeholder="Min 8 characters" />
          </div>
          <div>
            <Label>Role</Label>
            <select className="w-full mt-1 border rounded-md px-3 py-2 text-sm bg-background"
              value={form.role} onChange={e => setForm(f => ({...f, role: e.target.value}))}>
              <option value="staff">Staff</option>
              <option value="admin">Admin</option>
            </select>
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
