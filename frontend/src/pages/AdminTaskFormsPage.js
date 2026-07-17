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
import { ArrowLeftIcon, PlusIcon, PencilIcon, TrashIcon, ChevronUpIcon, ChevronDownIcon } from 'lucide-react';
import { toast } from 'sonner';

const FIELD_TYPES = ['text', 'number', 'select', 'boolean'];

const AdminTaskFormsPage = () => {
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editTemplate, setEditTemplate] = useState(null);
  const [showCreate, setShowCreate] = useState(false);

  const fetchTemplates = useCallback(async () => {
    try {
      const res = await api.get('/task-forms/templates');
      setTemplates(res.data || []);
    } catch {
      toast.error('Failed to load form templates');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!user || !['admin'].includes(user.role?.toLowerCase())) { navigate('/auth'); return; }
    fetchTemplates();
  }, [user, navigate, fetchTemplates]);

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-primary"></div>
    </div>
  );

  return (
    <div className="min-h-screen bg-[#F9F7F2]">
      <header className="bg-white border-b shadow-sm sticky top-0 z-10">
        <div className="max-w-3xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="sm" onClick={() => navigate(-1)}>
              <ArrowLeftIcon size={18} />
            </Button>
            <h1 className="text-lg font-serif font-bold text-primary">Task Form Templates</h1>
          </div>
          <Button size="sm" onClick={() => setShowCreate(true)}>
            <PlusIcon size={14} className="mr-1" /> New Template
          </Button>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 py-6 space-y-3">
        <p className="text-xs text-muted-foreground">
          These templates can be attached to tasks (e.g. "require this form before completing").
        </p>
        {templates.length === 0 ? (
          <Card><CardContent className="py-12 text-center text-muted-foreground">
            No form templates yet — create one above.
          </CardContent></Card>
        ) : (
          templates.map(t => (
            <Card key={t.id} className={!t.is_active ? 'opacity-60' : ''}>
              <CardContent className="py-3 px-4">
                <div className="flex items-center justify-between gap-3">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <p className="font-medium text-sm">{t.name}</p>
                      {t.category && <Badge variant="outline" className="text-xs">{t.category}</Badge>}
                      {!t.is_active && <Badge className="text-xs bg-red-100 text-red-600">Inactive</Badge>}
                    </div>
                    {t.description && <p className="text-xs text-muted-foreground mt-0.5">{t.description}</p>}
                    <p className="text-xs text-muted-foreground mt-0.5">{t.fields?.length || 0} fields</p>
                  </div>
                  <Button size="sm" variant="ghost" onClick={() => setEditTemplate(t)}>
                    <PencilIcon size={14} />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </main>

      {(showCreate || editTemplate) && (
        <TemplateEditorModal
          template={editTemplate}
          onClose={() => { setShowCreate(false); setEditTemplate(null); }}
          onSave={() => { setShowCreate(false); setEditTemplate(null); fetchTemplates(); }}
        />
      )}
    </div>
  );
};

const TemplateEditorModal = ({ template, onClose, onSave }) => {
  const [meta, setMeta] = useState({
    name: template?.name || '',
    description: template?.description || '',
    category: template?.category || '',
    is_active: template?.is_active ?? true,
  });
  const [fields, setFields] = useState(template?.fields || []);
  const [saving, setSaving] = useState(false);

  const addField = () => {
    setFields(f => [...f, { key: `field_${Date.now()}`, label: '', type: 'text', required: false }]);
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
    if (!meta.name.trim()) { toast.error('Name is required'); return; }
    for (const f of fields) {
      if (!f.label.trim()) { toast.error('Every field needs a label'); return; }
    }
    setSaving(true);
    try {
      if (template?.id) {
        await api.patch(`/task-forms/templates/${template.id}`, { ...meta, fields });
      } else {
        await api.post('/task-forms/templates', { ...meta, fields });
      }
      toast.success(template?.id ? 'Template updated' : 'Template created');
      onSave();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to save template');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-end md:items-center justify-center p-4">
      <div className="bg-white rounded-t-2xl md:rounded-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="p-6 space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-lg font-bold">{template?.id ? 'Edit Template' : 'New Template'}</h2>
            <button onClick={onClose} className="text-muted-foreground text-xl">×</button>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2">
              <Label>Name *</Label>
              <Input value={meta.name} onChange={e => setMeta(m => ({ ...m, name: e.target.value }))} className="mt-1" />
            </div>
            <div className="col-span-2">
              <Label>Description</Label>
              <Textarea value={meta.description} onChange={e => setMeta(m => ({ ...m, description: e.target.value }))} className="mt-1" rows={2} />
            </div>
            <div>
              <Label>Category</Label>
              <Input value={meta.category} onChange={e => setMeta(m => ({ ...m, category: e.target.value }))} className="mt-1" placeholder="e.g. inspection" />
            </div>
            {template?.id && (
              <div className="flex items-end pb-1">
                <label className="flex items-center gap-2 text-sm">
                  <input type="checkbox" checked={meta.is_active}
                    onChange={e => setMeta(m => ({ ...m, is_active: e.target.checked }))} />
                  Active
                </label>
              </div>
            )}
          </div>

          <div className="border-t pt-3">
            <div className="flex items-center justify-between mb-3">
              <p className="text-sm font-medium">Fields ({fields.length})</p>
              <Button size="sm" variant="outline" onClick={addField}>
                <PlusIcon size={12} className="mr-1" /> Add Field
              </Button>
            </div>
            <div className="space-y-3">
              {fields.map((field, idx) => (
                <div key={field.key || idx} className="p-3 border rounded-lg bg-muted/30 space-y-2">
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
                    <button onClick={() => removeField(idx)} className="text-red-400 hover:text-red-600 shrink-0">
                      <TrashIcon size={12} />
                    </button>
                  </div>
                  {field.type === 'select' && (
                    <Input className="h-7 text-xs" placeholder="Options (comma separated)"
                      value={Array.isArray(field.options) ? field.options.join(', ') : field.options || ''}
                      onChange={e => updateField(idx, 'options', e.target.value.split(',').map(s => s.trim()).filter(Boolean))} />
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
              {saving ? 'Saving...' : template?.id ? 'Save Changes' : 'Create Template'}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminTaskFormsPage;
