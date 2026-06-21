import React, { useEffect, useState, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import useAuthStore from '../store/authStore';
import api from '../utils/api';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { CheckCircleIcon, FileTextIcon, DownloadIcon, ChevronRightIcon } from 'lucide-react';
import { toast } from 'sonner';

const TYPE_COLORS = {
  intake: 'bg-blue-100 text-blue-700',
  boarding_agreement: 'bg-purple-100 text-purple-700',
  checklist: 'bg-green-100 text-green-700',
  onboarding: 'bg-orange-100 text-orange-700',
  vaccination: 'bg-teal-100 text-teal-700',
  custom: 'bg-gray-100 text-gray-600',
};

const TYPE_ICONS = {
  intake: '🐾',
  boarding_agreement: '📋',
  checklist: '✅',
  onboarding: '👋',
  vaccination: '💉',
  custom: '📄',
};

const FormsPage = () => {
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const [forms, setForms] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedForm, setSelectedForm] = useState(null);

  const fetchForms = useCallback(async () => {
    try {
      const res = await api.get('/forms');
      setForms(res.data);
    } catch { toast.error('Failed to load forms'); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => {
    if (!user) { navigate('/auth'); return; }
    fetchForms();
  }, [user, navigate, fetchForms]);

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-primary"></div>
    </div>
  );

  if (selectedForm) return (
    <FormRenderer
      form={selectedForm}
      user={user}
      onBack={() => setSelectedForm(null)}
      onSubmitted={() => { setSelectedForm(null); toast.success('Form submitted successfully'); }}
    />
  );

  // Group by type
  const grouped = forms.reduce((acc, f) => {
    if (!acc[f.form_type]) acc[f.form_type] = [];
    acc[f.form_type].push(f);
    return acc;
  }, {});

  return (
    <div className="min-h-screen bg-[#F9F7F2]">
      <header className="bg-white border-b shadow-sm sticky top-0 z-10">
        <div className="max-w-3xl mx-auto px-4 py-3">
          <h1 className="text-lg font-serif font-bold text-primary">Forms</h1>
          <p className="text-xs text-muted-foreground">Complete and submit forms for K9 Country Club</p>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 py-6 space-y-6">
        {Object.entries(grouped).map(([type, typeForms]) => (
          <div key={type}>
            <h2 className="text-sm font-medium text-muted-foreground mb-2 capitalize">
              {TYPE_ICONS[type]} {type.replace('_', ' ')}
            </h2>
            <div className="space-y-2">
              {typeForms.map(form => (
                <Card key={form.id} className="cursor-pointer hover:shadow-md transition-shadow"
                  onClick={() => setSelectedForm(form)}>
                  <CardContent className="py-3 px-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <span className="text-2xl">{TYPE_ICONS[form.form_type]}</span>
                        <div>
                          <p className="font-medium text-sm">{form.title}</p>
                          {form.description && (
                            <p className="text-xs text-muted-foreground">{form.description}</p>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge className={`text-xs ${TYPE_COLORS[form.form_type] || TYPE_COLORS.custom}`}>
                          {form.form_type.replace('_', ' ')}
                        </Badge>
                        <ChevronRightIcon size={16} className="text-muted-foreground" />
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        ))}

        {forms.length === 0 && (
          <Card>
            <CardContent className="py-12 text-center">
              <FileTextIcon size={32} className="mx-auto text-muted-foreground mb-3" />
              <p className="text-muted-foreground">No forms available</p>
            </CardContent>
          </Card>
        )}
      </main>
    </div>
  );
};

const FormRenderer = ({ form, user, onBack, onSubmitted }) => {
  const [responses, setResponses] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const printRef = useRef();

  const updateResponse = (fieldId, value) => {
    setResponses(r => ({ ...r, [fieldId]: value }));
  };

  const validate = () => {
    for (const field of form.fields) {
      if (field.required && !responses[field.id] && field.type !== 'agreement') {
        toast.error(`"${field.label}" is required`);
        return false;
      }
    }
    return true;
  };

  const handleSubmit = async () => {
    if (!validate()) return;
    setSubmitting(true);
    try {
      await api.post(`/forms/${form.id}/submit`, {
        responses,
        signed_name: responses['sig'] || null,
      });
      setSubmitted(true);
      onSubmitted();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to submit');
    } finally { setSubmitting(false); }
  };

  const handlePrint = () => {
    const printContent = printRef.current;
    const win = window.open('', '_blank');
    win.document.write(`
      <html><head><title>${form.title}</title>
      <style>
        body { font-family: Arial, sans-serif; padding: 20px; max-width: 800px; margin: 0 auto; }
        h1 { font-size: 24px; margin-bottom: 8px; }
        h2 { font-size: 14px; color: #666; margin-bottom: 24px; }
        .field { margin-bottom: 20px; }
        .label { font-weight: bold; font-size: 13px; margin-bottom: 6px; }
        .value { font-size: 13px; padding: 8px; border: 1px solid #ddd; border-radius: 4px; min-height: 32px; }
        .agreement { background: #f9f9f9; padding: 12px; border-radius: 4px; font-size: 12px; color: #444; margin-bottom: 8px; }
        .sig { border-bottom: 2px solid #000; padding-bottom: 4px; font-style: italic; margin-top: 32px; }
        .meta { font-size: 11px; color: #888; margin-top: 32px; border-top: 1px solid #eee; padding-top: 12px; }
      </style></head><body>
      <h1>${form.title}</h1>
      <h2>${form.description || ''}</h2>
      ${form.fields.map(f => {
        const val = responses[f.id];
        if (f.type === 'agreement') return `<div class="field"><div class="agreement">${f.content}</div></div>`;
        if (f.type === 'signature') return `<div class="field"><div class="label">${f.label}</div><div class="sig">${val || ''}</div></div>`;
        if (f.type === 'checkbox') return `<div class="field"><div class="label">[${val ? 'X' : ' '}] ${f.label}</div></div>`;
        return `<div class="field"><div class="label">${f.label}</div><div class="value">${val || ''}</div></div>`;
      }).join('')}
      <div class="meta">Submitted by: ${user.full_name} | Date: ${new Date().toLocaleString()} | K9 Country Club</div>
      </body></html>
    `);
    win.document.close();
    win.print();
  };

  return (
    <div className="min-h-screen bg-[#F9F7F2]">
      <header className="bg-white border-b shadow-sm sticky top-0 z-10">
        <div className="max-w-3xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button onClick={onBack} className="text-muted-foreground hover:text-foreground">←</button>
            <div>
              <h1 className="text-base font-serif font-bold text-primary">{form.title}</h1>
              {form.description && <p className="text-xs text-muted-foreground">{form.description}</p>}
            </div>
          </div>
          <Button variant="outline" size="sm" onClick={handlePrint}>
            <DownloadIcon size={14} className="mr-1" /> PDF
          </Button>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 py-6 space-y-4" ref={printRef}>
        {form.fields.map(field => (
          <FormField
            key={field.id}
            field={field}
            value={responses[field.id]}
            onChange={val => updateResponse(field.id, val)}
          />
        ))}

        <div className="pt-4 pb-8">
          <Button className="w-full" onClick={handleSubmit} disabled={submitting}>
            {submitting ? 'Submitting...' : 'Submit Form'}
          </Button>
        </div>
      </main>
    </div>
  );
};

const FormField = ({ field, value, onChange }) => {
  switch (field.type) {
    case 'text':
      return (
        <div>
          <label className="text-sm font-medium">{field.label}{field.required && <span className="text-red-500 ml-1">*</span>}</label>
          <Input value={value || ''} onChange={e => onChange(e.target.value)} className="mt-1" />
        </div>
      );
    case 'number':
      return (
        <div>
          <label className="text-sm font-medium">{field.label}{field.required && <span className="text-red-500 ml-1">*</span>}</label>
          <Input type="number" value={value || ''} onChange={e => onChange(e.target.value)} className="mt-1" />
        </div>
      );
    case 'textarea':
      return (
        <div>
          <label className="text-sm font-medium">{field.label}{field.required && <span className="text-red-500 ml-1">*</span>}</label>
          <Textarea value={value || ''} onChange={e => onChange(e.target.value)} className="mt-1" rows={3} />
        </div>
      );
    case 'select':
      return (
        <div>
          <label className="text-sm font-medium">{field.label}{field.required && <span className="text-red-500 ml-1">*</span>}</label>
          <select className="w-full mt-1 border rounded-md px-3 py-2 text-sm bg-background"
            value={value || ''} onChange={e => onChange(e.target.value)}>
            <option value="">Select...</option>
            {field.options?.map(o => <option key={o} value={o}>{o}</option>)}
          </select>
        </div>
      );
    case 'checkbox':
      return (
        <label className="flex items-start gap-3 cursor-pointer p-3 rounded-lg border hover:bg-muted/50">
          <input type="checkbox" checked={!!value} onChange={e => onChange(e.target.checked)}
            className="mt-0.5 w-4 h-4 shrink-0" />
          <span className="text-sm">{field.label}{field.required && <span className="text-red-500 ml-1">*</span>}</span>
        </label>
      );
    case 'agreement':
      return (
        <Card className="border-amber-200 bg-amber-50/50">
          <CardContent className="py-3 px-4">
            <p className="text-xs font-semibold text-amber-800 mb-2">{field.label}</p>
            <p className="text-xs text-amber-900 leading-relaxed">{field.content}</p>
          </CardContent>
        </Card>
      );
    case 'signature':
      return (
        <div>
          <label className="text-sm font-medium">{field.label}{field.required && <span className="text-red-500 ml-1">*</span>}</label>
          <p className="text-xs text-muted-foreground mt-0.5">Type your full name to sign electronically</p>
          <Input value={value || ''} onChange={e => onChange(e.target.value)}
            className="mt-1 font-serif italic text-lg" placeholder="Your full name..." />
          {value && (
            <p className="text-xs text-green-600 mt-1 flex items-center gap-1">
              <CheckCircleIcon size={12} /> Signed as: {value} · {new Date().toLocaleDateString()}
            </p>
          )}
        </div>
      );
    default:
      return null;
  }
};

export { FormRenderer };
export default FormsPage;
