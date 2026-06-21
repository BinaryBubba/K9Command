import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import useAuthStore from '../store/authStore';
import api from '../utils/api';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { PlusIcon, PencilIcon, UsersIcon, TrashIcon, ChevronDownIcon, ChevronUpIcon } from 'lucide-react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';


import { toast } from 'sonner';

const TYPE_COLORS = {
  intake: 'bg-blue-100 text-blue-700',
  boarding_agreement: 'bg-purple-100 text-purple-700',
  checklist: 'bg-green-100 text-green-700',
  onboarding: 'bg-orange-100 text-orange-700',
  vaccination: 'bg-teal-100 text-teal-700',
  custom: 'bg-gray-100 text-gray-600',
};

const FIELD_TYPES = ['text', 'number', 'textarea', 'select', 'checkbox', 'agreement', 'signature'];

const AdminFormsPage = () => {
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const [forms, setForms] = useState([]);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editForm, setEditForm] = useState(null);
  const [showCreate, setShowCreate] = useState(false);
  const [accessModal, setAccessModal] = useState(null);

  const fetchData = useCallback(async () => {
    try {
      const [formsRes, usersRes] = await Promise.all([
        api.get('/forms'),
        api.get('/users', { params: { limit: 100 } }),
      ]);
      setForms(formsRes.data);
      setUsers(usersRes.data.filter(u => u.role !== 'customer'));
    } catch { toast.error('Failed to load'); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => {
    if (!user || !['admin','manager','ADMIN','MANAGER'].includes(user.role)) { navigate('/auth'); return; }
    fetchData();
  }, [user, navigate, fetchData]);

  const handleToggleActive = async (form) => {
    try {
      await api.patch(`/forms/${form.id}`, { is_active: !form.is_active });
      toast.success(form.is_active ? 'Form deactivated' : 'Form activated');
      fetchData();
    } catch { toast.error('Failed'); }
  };

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-primary"></div>
    </div>
  );

  return (
    <div className="min-h-screen bg-[#F9F7F2]">
      <header className="bg-white border-b shadow-sm sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between">
          <h1 className="text-lg font-serif font-bold text-primary">Form Management</h1>
          <Button size="sm" onClick={() => setShowCreate(true)}>
            <PlusIcon size={14} className="mr-1" /> New Form
          </Button>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-4">
        <Tabs defaultValue="manage">
          <TabsList className="w-full mb-4">
            <TabsTrigger value="manage" className="flex-1">Manage Forms</TabsTrigger>
            <TabsTrigger value="fill" className="flex-1">Fill a Form</TabsTrigger>
          </TabsList>
          <TabsContent value="manage" className="space-y-3">
        {forms.map(form => (
          <Card key={form.id} className={!form.is_active ? 'opacity-60' : ''}>
            <CardContent className="py-3 px-4">
              <div className="flex items-center justify-between gap-3">
                <div className="flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <p className="font-medium text-sm">{form.title}</p>
                    <Badge className={`text-xs ${TYPE_COLORS[form.form_type] || TYPE_COLORS.custom}`}>
                      {form.form_type.replace('_', ' ')}
                    </Badge>
                    <Badge variant="outline" className="text-xs">
                      {form.access_level}
                    </Badge>
                    {!form.is_active && <Badge className="text-xs bg-red-100 text-red-600">Inactive</Badge>}
                  </div>
                  {form.description && <p className="text-xs text-muted-foreground mt-0.5">{form.description}</p>}
                  <p className="text-xs text-muted-foreground mt-0.5">{form.fields?.length || 0} fields</p>
                </div>
                <div className="flex gap-1 shrink-0">
                  <Button size="sm" variant="ghost" onClick={() => setAccessModal(form)}
                    title="Manage access">
                    <UsersIcon size={14} />
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => setEditForm(form)}>
                    <PencilIcon size={14} />
                  </Button>
                  <Button size="sm" variant="ghost"
                    className={form.is_active ? 'text-red-500' : 'text-green-600'}
                    onClick={() => handleToggleActive(form)}>
                    {form.is_active ? 'Disable' : 'Enable'}
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </main>

          </TabsContent>
          <TabsContent value="fill">
            <div className="text-center py-12 space-y-3">
              <p className="text-muted-foreground">Fill out forms as staff or customer</p>
              <Button onClick={() => window.open('/forms', '_blank')}>Open Forms Page</Button>
            </div>
          </TabsContent>
        </Tabs>
      {(showCreate || editForm) && (
        <FormEditorModal
          form={editForm}
          onClose={() => { setShowCreate(false); setEditForm(null); }}
          onSave={() => { setShowCreate(false); setEditForm(null); fetchData(); }}
        />
      )}

      {accessModal && (
        <AccessModal
          form={accessModal}
          users={users}
          onClose={() => setAccessModal(null)}
        />
      )}
    </div>
  );
};

const FormEditorModal = ({ form, onClose, onSave }) => {
  const [meta, setMeta] = useState({
    title: form?.title || '',
    description: form?.description || '',
    form_type: form?.form_type || 'custom',
    access_level: form?.access_level || 'staff',
  });
  const [fields, setFields] = useState(form?.fields || []);
  const [saving, setSaving] = useState(false);

  const addField = () => {
    setFields(f => [...f, { id: `f${Date.now()}`, type: 'text', label: '', required: false }]);
  };

  const updateField = (idx, key, val) => {
    setFields(f => f.map((field, i) => i === idx ? { ...field, [key]: val } : field));
  };

  const removeField = (idx) => {
    setFields(f => f.filter((_, i) => i !== idx));
  };

  const moveField = (idx, dir) => {
    const newFields = [...fields];
    const swap = idx + dir;
    if (swap < 0 || swap >= newFields.length) return;
    [newFields[idx], newFields[swap]] = [newFields[swap], newFields[idx]];
    setFields(newFields);
  };

  const handleSave = async () => {
    if (!meta.title.trim()) { toast.error('Title required'); return; }
    setSaving(true);
    try {
      if (form?.id) {
        await api.patch(`/forms/${form.id}`, { ...meta, fields });
      } else {
        await api.post('/forms', { ...meta, fields });
      }
      toast.success(form?.id ? 'Form updated' : 'Form created');
      onSave();
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed'); }
    finally { setSaving(false); }
  };

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-end md:items-center justify-center p-4">
      <div className="bg-white rounded-t-2xl md:rounded-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="p-6 space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-lg font-bold">{form?.id ? 'Edit Form' : 'New Form'}</h2>
            <button onClick={onClose} className="text-muted-foreground text-xl">×</button>
          </div>

          {/* Meta */}
          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2">
              <Label>Title *</Label>
              <Input value={meta.title} onChange={e => setMeta(m=>({...m,title:e.target.value}))} className="mt-1" />
            </div>
            <div className="col-span-2">
              <Label>Description</Label>
              <Textarea value={meta.description} onChange={e => setMeta(m=>({...m,description:e.target.value}))} className="mt-1" rows={2} />
            </div>
            <div>
              <Label>Type</Label>
              <select className="w-full mt-1 border rounded-md px-3 py-2 text-sm bg-background"
                value={meta.form_type} onChange={e => setMeta(m=>({...m,form_type:e.target.value}))}>
                {['intake','boarding_agreement','checklist','onboarding','vaccination','custom'].map(t => (
                  <option key={t} value={t}>{t.replace('_',' ')}</option>
                ))}
              </select>
            </div>
            <div>
              <Label>Default Access</Label>
              <select className="w-full mt-1 border rounded-md px-3 py-2 text-sm bg-background"
                value={meta.access_level} onChange={e => setMeta(m=>({...m,access_level:e.target.value}))}>
                <option value="customer">Customer</option>
                <option value="staff">Staff</option>
                <option value="manager">Manager</option>
                <option value="admin">Admin only</option>
              </select>
            </div>
          </div>

          {/* Fields */}
          <div className="border-t pt-3">
            <div className="flex items-center justify-between mb-3">
              <p className="text-sm font-medium">Fields ({fields.length})</p>
              <Button size="sm" variant="outline" onClick={addField}>
                <PlusIcon size={12} className="mr-1" /> Add Field
              </Button>
            </div>
            <div className="space-y-3">
              {fields.map((field, idx) => (
                <div key={field.id || idx} className="p-3 border rounded-lg bg-muted/30 space-y-2">
                  <div className="flex items-center gap-2">
                    <div className="flex flex-col gap-0.5">
                      <button onClick={() => moveField(idx, -1)} className="text-muted-foreground hover:text-foreground">
                        <ChevronUpIcon size={12} />
                      </button>
                      <button onClick={() => moveField(idx, 1)} className="text-muted-foreground hover:text-foreground">
                        <ChevronDownIcon size={12} />
                      </button>
                    </div>
                    <select className="border rounded px-2 py-1 text-xs bg-background"
                      value={field.type} onChange={e => updateField(idx, 'type', e.target.value)}>
                      {FIELD_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                    </select>
                    <Input className="flex-1 h-7 text-xs" placeholder="Field label"
                      value={field.label} onChange={e => updateField(idx, 'label', e.target.value)} />
                    <label className="flex items-center gap-1 text-xs text-muted-foreground whitespace-nowrap">
                      <input type="checkbox" checked={!!field.required}
                        onChange={e => updateField(idx, 'required', e.target.checked)} className="w-3 h-3" />
                      Required
                    </label>
                    <button onClick={() => removeField(idx)}
                      className="text-red-400 hover:text-red-600 shrink-0">
                      <TrashIcon size={12} />
                    </button>
                  </div>
                  {field.type === 'select' && (
                    <Input className="h-7 text-xs" placeholder="Options (comma separated)"
                      value={Array.isArray(field.options) ? field.options.join(', ') : field.options || ''}
                      onChange={e => updateField(idx, 'options', e.target.value.split(',').map(s => s.trim()))} />
                  )}
                  {field.type === 'agreement' && (
                    <Textarea className="text-xs" rows={2} placeholder="Agreement text content"
                      value={field.content || ''}
                      onChange={e => updateField(idx, 'content', e.target.value)} />
                  )}
                </div>
              ))}
              {fields.length === 0 && (
                <p className="text-sm text-muted-foreground text-center py-4">No fields yet — add some above</p>
              )}
            </div>
          </div>

          <div className="flex gap-3 pt-2">
            <Button variant="outline" className="flex-1" onClick={onClose}>Cancel</Button>
            <Button className="flex-1" onClick={handleSave} disabled={saving}>
              {saving ? 'Saving...' : form?.id ? 'Save Changes' : 'Create Form'}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

const AccessModal = ({ form, users, onClose }) => {
  const [access, setAccess] = useState({});
  const [saving, setSaving] = useState(null);

  const handleSetAccess = async (userId, type) => {
    setSaving(userId);
    try {
      await api.post(`/forms/${form.id}/access`, { user_id: userId, access_type: type });
      setAccess(a => ({ ...a, [userId]: type }));
      toast.success(type === 'granted' ? 'Access granted' : type === 'revoked' ? 'Access revoked' : 'Reset to default');
    } catch { toast.error('Failed'); }
    finally { setSaving(null); }
  };

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-end md:items-center justify-center p-4">
      <div className="bg-white rounded-t-2xl md:rounded-2xl w-full max-w-md max-h-[80vh] overflow-y-auto">
        <div className="p-6 space-y-4">
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-lg font-bold">Form Access</h2>
              <p className="text-sm text-muted-foreground">{form.title}</p>
            </div>
            <button onClick={onClose} className="text-muted-foreground text-xl">×</button>
          </div>
          <p className="text-xs text-muted-foreground">
            Default access: <strong>{form.access_level}</strong> role and above. Override per staff member below.
          </p>
          <div className="space-y-2">
            {users.map(u => (
              <div key={u.id} className="flex items-center justify-between py-2 border-b last:border-0">
                <div>
                  <p className="text-sm font-medium">{u.full_name}</p>
                  <p className="text-xs text-muted-foreground">{u.role}</p>
                </div>
                <div className="flex gap-1">
                  <Button size="sm" variant={access[u.id] === 'granted' ? 'default' : 'outline'}
                    className="h-7 text-xs"
                    disabled={saving === u.id}
                    onClick={() => handleSetAccess(u.id, 'granted')}>
                    Grant
                  </Button>
                  <Button size="sm" variant={access[u.id] === 'revoked' ? 'destructive' : 'outline'}
                    className="h-7 text-xs"
                    disabled={saving === u.id}
                    onClick={() => handleSetAccess(u.id, 'revoked')}>
                    Revoke
                  </Button>
                </div>
              </div>
            ))}
          </div>
          <Button variant="outline" className="w-full" onClick={onClose}>Done</Button>
        </div>
      </div>
    </div>
  );
};

export default AdminFormsPage;
