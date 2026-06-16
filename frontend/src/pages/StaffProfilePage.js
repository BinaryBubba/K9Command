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
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import {
  UserIcon, PencilIcon, CheckCircleIcon, XCircleIcon,
  KeyIcon, ClipboardListIcon, ActivityIcon, PlusIcon,
} from 'lucide-react';
import { toast } from 'sonner';

const ROLE_COLORS = {
  admin: 'bg-purple-100 text-purple-700',
  manager: 'bg-blue-100 text-blue-700',
  staff: 'bg-green-100 text-green-700',
};

const StaffProfilePage = () => {
  const { user: currentUser } = useAuthStore();
  const navigate = useNavigate();
  const { staffId } = useParams();
  const [staff, setStaff] = useState(null);
  const [tasks, setTasks] = useState([]);
  const [openTasks, setOpenTasks] = useState([]);
  const [activity, setActivity] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [showResetPw, setShowResetPw] = useState(false);
  const [showCreateTask, setShowCreateTask] = useState(false);
  const [tempPassword, setTempPassword] = useState('');

  const isAdmin = currentUser?.role === 'admin';
  const isSelf = currentUser?.id === staffId;

  const fetchData = useCallback(async () => {
    try {
      const [userRes, tasksRes, openRes, activityRes] = await Promise.all([
        api.get(`/users/${staffId}`),
        api.get('/tasks', { params: { assigned_to: staffId } }).catch(() => ({ data: [] })),
        api.get('/tasks', { params: { limit: 50 } }).catch(() => ({ data: [] })),
        api.get(`/users/${staffId}/activity`).catch(() => ({ data: [] })),
      ]);
      setStaff(userRes.data);
      setTasks(tasksRes.data);
      setOpenTasks(openRes.data.filter(t => !t.assigned_to));
      setActivity(activityRes.data);
    } catch { toast.error('Failed to load staff profile'); }
    finally { setLoading(false); }
  }, [staffId]);

  useEffect(() => {
    if (!currentUser) { navigate('/auth'); return; }
    if (!isAdmin && !isSelf) { navigate(-1); return; }
    fetchData();
  }, [currentUser, navigate, fetchData, isAdmin, isSelf]);

  const handleResetPassword = async () => {
    try {
      const res = await api.post(`/users/${staffId}/reset-password`);
      setTempPassword(res.data.temp_password);
      setShowResetPw(true);
    } catch (err) { toast.error(err.response?.data?.detail || err.message || 'Failed to save'); console.error('Save error:', err); }
  };

  const handleToggleActive = async () => {
    try {
      await api.patch(`/users/${staffId}`, { is_active: !staff.is_active });
      toast.success(staff.is_active ? 'Account deactivated' : 'Account activated');
      fetchData();
    } catch { toast.error('Failed to update'); }
  };

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-primary"></div>
    </div>
  );

  if (!staff) return <div className="min-h-screen flex items-center justify-center"><p className="text-muted-foreground">Staff member not found</p></div>;

  return (
    <div className="min-h-screen bg-[#F9F7F2]">
      <header className="bg-white border-b shadow-sm sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between">
          <div>
            <h1 className="text-lg font-serif font-bold text-primary">{staff.full_name}</h1>
            <p className="text-xs text-muted-foreground">{staff.email}</p>
          </div>
          <div className="flex gap-2">
            {isAdmin && (
              <Button size="sm" variant="outline" onClick={handleResetPassword}>
                <KeyIcon size={14} className="mr-1" /> Reset PW
              </Button>
            )}
            <Button size="sm" variant="outline" onClick={() => setEditing(!editing)}>
              <PencilIcon size={14} className="mr-1" /> {editing ? 'Cancel' : 'Edit'}
            </Button>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-6 space-y-5">
        {/* Status banner */}
        {staff.is_active === false && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3 flex items-center justify-between">
            <p className="text-sm text-red-700 font-medium">⚠️ This account is deactivated</p>
            {isAdmin && <Button size="sm" onClick={handleToggleActive}>Reactivate</Button>}
          </div>
        )}

        {editing ? (
          <EditForm staff={staff} isAdmin={isAdmin}
            onSave={() => { setEditing(false); fetchData(); }}
            onCancel={() => setEditing(false)}
            onToggleActive={isAdmin ? handleToggleActive : undefined} />
        ) : (
          <ProfileView staff={staff} isAdmin={isAdmin} onToggleActive={handleToggleActive} />
        )}

        <Tabs defaultValue="tasks">
          <TabsList className="w-full">
            <TabsTrigger value="tasks" className="flex-1">Tasks ({tasks.length})</TabsTrigger>
            <TabsTrigger value="open" className="flex-1">Open Tasks ({openTasks.length})</TabsTrigger>
            <TabsTrigger value="activity" className="flex-1">Activity</TabsTrigger>
          </TabsList>

          <TabsContent value="tasks" className="mt-4 space-y-2">
            <div className="flex justify-end">
              <Button size="sm" onClick={() => setShowCreateTask(true)}>
                <PlusIcon size={14} className="mr-1" /> Assign Task
              </Button>
            </div>
            {tasks.length === 0 ? (
              <Card><CardContent className="py-8 text-center text-muted-foreground">No tasks assigned</CardContent></Card>
            ) : tasks.map(task => <TaskRow key={task.id} task={task} onRefresh={fetchData} />)}
          </TabsContent>

          <TabsContent value="open" className="mt-4 space-y-2">
            <p className="text-xs text-muted-foreground mb-3">Unassigned tasks that can be claimed</p>
            {openTasks.length === 0 ? (
              <Card><CardContent className="py-8 text-center text-muted-foreground">No open tasks</CardContent></Card>
            ) : openTasks.map(task => <TaskRow key={task.id} task={task} onRefresh={fetchData} />)}
          </TabsContent>

          <TabsContent value="activity" className="mt-4">
            {activity.length === 0 ? (
              <Card><CardContent className="py-8 text-center text-muted-foreground">No activity recorded</CardContent></Card>
            ) : (
              <div className="space-y-2">
                {activity.map((a, i) => (
                  <Card key={i}>
                    <CardContent className="py-3 px-4">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <ActivityIcon size={14} className={a.type === 'check_in' ? 'text-green-500' : 'text-blue-500'} />
                          <div>
                            <p className="text-sm font-medium">
                              {a.type === 'check_in' ? 'Checked in' : 'Checked out'} {a.dog_name}
                            </p>
                            {a.room_name && <p className="text-xs text-muted-foreground">→ {a.room_name}</p>}
                          </div>
                        </div>
                        <p className="text-xs text-muted-foreground">
                          {a.timestamp ? new Date(a.timestamp).toLocaleString() : '—'}
                        </p>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </TabsContent>
        </Tabs>
      </main>

      {showResetPw && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl w-full max-w-sm p-6 space-y-4">
            <h2 className="text-lg font-bold">Password Reset</h2>
            <p className="text-sm text-muted-foreground">Share this temporary password with {staff.full_name}:</p>
            <div className="bg-muted rounded-lg p-4 text-center">
              <p className="text-2xl font-mono font-bold tracking-widest">{tempPassword}</p>
            </div>
            <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded p-2">
              ⚠️ This will not be shown again. Copy it now.
            </p>
            <Button className="w-full" onClick={() => { navigator.clipboard.writeText(tempPassword); toast.success('Copied!'); }}>
              Copy to Clipboard
            </Button>
            <Button variant="outline" className="w-full" onClick={() => setShowResetPw(false)}>Done</Button>
          </div>
        </div>
      )}

      {showCreateTask && (
        <CreateTaskModal
          assignedTo={staffId}
          assignedName={staff.full_name}
          onClose={() => setShowCreateTask(false)}
          onSuccess={() => { setShowCreateTask(false); fetchData(); toast.success('Task assigned'); }}
        />
      )}
    </div>
  );
};

const ProfileView = ({ staff, isAdmin, onToggleActive }) => (
  <Card>
    <CardContent className="py-4 px-4 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="shrink-0">
            {staff.avatar_url ? (
              <img src={staff.avatar_url} alt={staff.full_name} className="w-14 h-14 rounded-full object-cover border-2 border-primary/20" />
            ) : (
              <div className="bg-primary/10 p-3 rounded-full"><UserIcon size={20} className="text-primary" /></div>
            )}
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <Badge className={`text-xs ${ROLE_COLORS[staff.role] || ROLE_COLORS.staff}`}>{staff.role}</Badge>
              {staff.is_owner && <Badge className="text-xs bg-amber-100 text-amber-700">Owner</Badge>}
              <Badge className={`text-xs ${staff.is_active !== false ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                {staff.is_active !== false ? 'Active' : 'Inactive'}
              </Badge>
            </div>
            {staff.hire_date && <p className="text-xs text-muted-foreground mt-1">Hired: {new Date(staff.hire_date).toLocaleDateString()}</p>}
          </div>
        </div>
        {isAdmin && (
          <Button size="sm" variant="outline"
            className={staff.is_active !== false ? 'text-red-600 border-red-200' : 'text-green-600 border-green-200'}
            onClick={onToggleActive}>
            {staff.is_active !== false ? <XCircleIcon size={14} className="mr-1" /> : <CheckCircleIcon size={14} className="mr-1" />}
            {staff.is_active !== false ? 'Deactivate' : 'Activate'}
          </Button>
        )}
      </div>
      <div className="grid grid-cols-2 gap-3 pt-2 border-t">
        <InfoRow label="Phone" value={staff.phone} />
        <InfoRow label="Email" value={staff.email} />
        <InfoRow label="Address" value={staff.address} />
        <InfoRow label="Birthday" value={staff.birthday ? new Date(staff.birthday).toLocaleDateString() : null} />
        <InfoRow label="Emergency Contact" value={staff.emergency_contact_name} />
        <InfoRow label="Emergency Phone" value={staff.emergency_contact_phone} />
      </div>
      {staff.notes && (
        <div className="pt-2 border-t">
          <p className="text-xs font-medium text-muted-foreground">Notes</p>
          <p className="text-sm mt-1">{staff.notes}</p>
        </div>
      )}
    </CardContent>
  </Card>
);

const EditForm = ({ staff, isAdmin, onSave, onCancel }) => {
  const [form, setForm] = useState({
    first_name: staff.first_name || '',
    last_name: staff.last_name || '',
    phone: staff.phone || '',
    address: staff.address || '',
    birthday: staff.birthday || '',
    emergency_contact_name: staff.emergency_contact_name || '',
    emergency_contact_phone: staff.emergency_contact_phone || '',
    role: staff.role || 'staff',
    hire_date: staff.hire_date || '',
    notes: staff.notes || '',
    avatar_key: staff.avatar_key || '',
    manager_pin: staff.manager_pin || '',
  });
  const [avatarPreview, setAvatarPreview] = useState(staff.avatar_url || '');
  const [uploading, setUploading] = useState(false);
  const fileRef = React.useRef();

  const handleAvatarUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setAvatarPreview(URL.createObjectURL(file));
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await api.post('/uploads/avatar', formData, { headers: { 'Content-Type': 'multipart/form-data' } });
      setForm(f => ({...f, avatar_key: res.data.key}));
      toast.success('Photo uploaded');
    } catch { toast.error('Upload failed'); setAvatarPreview(staff.avatar_url || ''); }
    finally { setUploading(false); }
  };
  const [submitting, setSubmitting] = useState(false);

  const handleSave = async () => {
    setSubmitting(true);
    try {
      const payload = {
        ...form,
        full_name: [form.first_name, form.last_name].filter(Boolean).join(' ') || form.first_name,
      };
      await api.patch(`/users/${staff.id}`, payload);
      toast.success('Profile updated');
      onSave();
    } catch (err) { toast.error(err.response?.data?.detail || err.message || 'Failed to save'); console.error('Save error:', err); }
    finally { setSubmitting(false); }
  };

  return (
    <Card className="border-primary/30">
      <CardContent className="py-4 px-4 space-y-3">
        <div className="flex items-center gap-4 mb-2">
          <div className="relative">
            {avatarPreview ? (
              <img src={avatarPreview} alt="Avatar" className="w-16 h-16 rounded-full object-cover border-2 border-primary/20" />
            ) : (
              <div className="w-16 h-16 rounded-full bg-muted flex items-center justify-center border-2 border-dashed border-muted-foreground/30">
                <UserIcon size={24} className="text-muted-foreground" />
              </div>
            )}
          </div>
          <div>
            <Button type="button" variant="outline" size="sm" onClick={() => fileRef.current?.click()} disabled={uploading}>
              {uploading ? 'Uploading...' : 'Change Photo'}
            </Button>
            <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={handleAvatarUpload} />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label>First Name</Label>
            <Input value={form.first_name} onChange={e => setForm(f=>({...f,first_name:e.target.value}))} className="mt-1" />
          </div>
          <div>
            <Label>Last Name</Label>
            <Input value={form.last_name} onChange={e => setForm(f=>({...f,last_name:e.target.value}))} className="mt-1" />
          </div>
          <div>
            <Label>Phone</Label>
            <Input value={form.phone} onChange={e => setForm(f=>({...f,phone:e.target.value}))} className="mt-1" />
          </div>
          <div>
            <Label>Birthday</Label>
            <Input type="date" value={form.birthday} onChange={e => setForm(f=>({...f,birthday:e.target.value}))} className="mt-1" />
          </div>
          <div className="col-span-2">
            <Label>Address</Label>
            <Input value={form.address} onChange={e => setForm(f=>({...f,address:e.target.value}))} className="mt-1" />
          </div>
          {isAdmin && (
            <>
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
            </>
          )}
          <div>
            <Label>Emergency Contact Name</Label>
            <Input value={form.emergency_contact_name} onChange={e => setForm(f=>({...f,emergency_contact_name:e.target.value}))} className="mt-1" />
          </div>
          <div>
            <Label>Emergency Contact Phone</Label>
            <Input value={form.emergency_contact_phone} onChange={e => setForm(f=>({...f,emergency_contact_phone:e.target.value}))} className="mt-1" />
          </div>
          {isAdmin && (
            <div className="col-span-2">
              <Label>Admin Notes</Label>
              <Textarea value={form.notes} onChange={e => setForm(f=>({...f,notes:e.target.value}))} className="mt-1" rows={2} />
            </div>
          )}
        </div>
        <div className="flex gap-3 pt-2">
          <Button variant="outline" className="flex-1" onClick={onCancel}>Cancel</Button>
          <Button className="flex-1" onClick={handleSave} disabled={submitting}>
            {submitting ? 'Saving...' : 'Save Changes'}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
};

const TaskRow = ({ task, onRefresh }) => {
  const PRIORITY_COLORS = { urgent: 'bg-red-100 text-red-700', high: 'bg-orange-100 text-orange-700', medium: 'bg-blue-100 text-blue-700', low: 'bg-gray-100 text-gray-600' };
  const STATUS_COLORS = { pending: 'bg-amber-100 text-amber-700', in_progress: 'bg-blue-100 text-blue-700', completed: 'bg-green-100 text-green-700', cancelled: 'bg-gray-100 text-gray-500' };

  const complete = async () => {
    try { await api.post(`/tasks/${task.id}/complete`); toast.success('Task completed'); onRefresh(); }
    catch { toast.error('Failed'); }
  };

  return (
    <Card>
      <CardContent className="py-3 px-4">
        <div className="flex items-center justify-between gap-3">
          <div className="flex-1">
            <div className="flex items-center gap-2 flex-wrap">
              <p className="font-medium text-sm">{task.title}</p>
              <Badge className={`text-xs ${PRIORITY_COLORS[task.priority?.toLowerCase()] || PRIORITY_COLORS.medium}`}>{task.priority?.toLowerCase()}</Badge>
              <Badge className={`text-xs ${STATUS_COLORS[task.status?.toLowerCase()] || STATUS_COLORS.pending}`}>{task.status?.replace('_',' ')}</Badge>
            </div>
            {task.due_date && <p className="text-xs text-muted-foreground mt-0.5">Due: {new Date(task.due_date).toLocaleDateString()}</p>}
          </div>
          {task.status !== 'completed' && task.status !== 'cancelled' && (
            <Button size="sm" variant="outline" className="text-green-600 border-green-200 h-7 text-xs" onClick={complete}>Done</Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
};

const CreateTaskModal = ({ assignedTo, assignedName, onClose, onSuccess }) => {
  const [form, setForm] = useState({ title: '', description: '', priority: 'medium', due_date: '' });
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    if (!form.title.trim()) { toast.error('Title required'); return; }
    setSubmitting(true);
    try {
      await api.post('/tasks', { ...form, priority: form.priority.toUpperCase(), assigned_to: assignedTo, due_date: form.due_date ? new Date(form.due_date).toISOString() : undefined });
      onSuccess();
    } catch (err) { toast.error(err.response?.data?.detail || err.message || 'Failed to save'); console.error('Save error:', err); }
    finally { setSubmitting(false); }
  };

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-end md:items-center justify-center p-4">
      <div className="bg-white rounded-t-2xl md:rounded-2xl w-full max-w-md">
        <div className="p-6 space-y-4">
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-lg font-bold">Assign Task</h2>
              <p className="text-sm text-muted-foreground">→ {assignedName}</p>
            </div>
            <button onClick={onClose} className="text-muted-foreground text-xl">×</button>
          </div>
          <div>
            <Label>Title *</Label>
            <Input value={form.title} onChange={e => setForm(f=>({...f,title:e.target.value}))} className="mt-1" />
          </div>
          <div>
            <Label>Description</Label>
            <Textarea value={form.description} onChange={e => setForm(f=>({...f,description:e.target.value}))} className="mt-1" rows={2} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label>Priority</Label>
              <select className="w-full mt-1 border rounded-md px-3 py-2 text-sm bg-background"
                value={form.priority} onChange={e => setForm(f=>({...f,priority:e.target.value}))}>
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="urgent">Urgent</option>
              </select>
            </div>
            <div>
              <Label>Due Date</Label>
              <Input type="datetime-local" value={form.due_date} onChange={e => setForm(f=>({...f,due_date:e.target.value}))} className="mt-1" />
            </div>
          </div>
          <div className="flex gap-3 pt-2">
            <Button variant="outline" className="flex-1" onClick={onClose}>Cancel</Button>
            <Button className="flex-1" onClick={handleSubmit} disabled={submitting}>
              {submitting ? 'Assigning...' : 'Assign Task'}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

const InfoRow = ({ label, value }) => !value ? null : (
  <div>
    <p className="text-xs text-muted-foreground">{label}</p>
    <p className="text-sm font-medium">{value}</p>
  </div>
);

export default StaffProfilePage;
