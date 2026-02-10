import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Switch } from '../components/ui/switch';
import { Badge } from '../components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { toast } from 'sonner';
import { 
  ArrowLeftIcon, 
  PlusIcon, 
  GripVerticalIcon, 
  TrashIcon, 
  CopyIcon,
  EyeIcon,
  SaveIcon,
  TypeIcon,
  AlignLeftIcon,
  HashIcon,
  CalendarIcon,
  ClockIcon,
  ListIcon,
  CheckSquareIcon,
  CircleIcon,
  UploadIcon,
  CameraIcon,
  PenToolIcon,
  MapPinIcon,
  QrCodeIcon,
  SplitIcon,
  InfoIcon,
  SettingsIcon
} from 'lucide-react';
import api from '../utils/api';

const FIELD_TYPES = [
  { type: 'text', label: 'Text Input', icon: TypeIcon, category: 'basic' },
  { type: 'textarea', label: 'Text Area', icon: AlignLeftIcon, category: 'basic' },
  { type: 'number', label: 'Number', icon: HashIcon, category: 'basic' },
  { type: 'date', label: 'Date', icon: CalendarIcon, category: 'basic' },
  { type: 'time', label: 'Time', icon: ClockIcon, category: 'basic' },
  { type: 'datetime', label: 'Date & Time', icon: CalendarIcon, category: 'basic' },
  { type: 'select', label: 'Dropdown', icon: ListIcon, category: 'choice' },
  { type: 'multiselect', label: 'Multi-Select', icon: ListIcon, category: 'choice' },
  { type: 'checkbox', label: 'Checkbox', icon: CheckSquareIcon, category: 'choice' },
  { type: 'radio', label: 'Radio Buttons', icon: CircleIcon, category: 'choice' },
  { type: 'file', label: 'File Upload', icon: UploadIcon, category: 'media' },
  { type: 'photo', label: 'Camera Capture', icon: CameraIcon, category: 'media' },
  { type: 'signature', label: 'Signature', icon: PenToolIcon, category: 'media' },
  { type: 'gps', label: 'GPS Location', icon: MapPinIcon, category: 'media' },
  { type: 'barcode', label: 'Barcode Scanner', icon: QrCodeIcon, category: 'media' },
  { type: 'section', label: 'Section Divider', icon: SplitIcon, category: 'layout' },
  { type: 'instructions', label: 'Instructions', icon: InfoIcon, category: 'layout' },
];

const FIELD_CATEGORIES = {
  basic: 'Basic Fields',
  choice: 'Choice Fields',
  media: 'Media & Capture',
  layout: 'Layout Elements'
};

const FieldPalette = ({ onAddField }) => {
  const [searchTerm, setSearchTerm] = useState('');

  const filteredFields = FIELD_TYPES.filter(f => 
    f.label.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const groupedFields = Object.entries(FIELD_CATEGORIES).map(([key, label]) => ({
    category: key,
    label,
    fields: filteredFields.filter(f => f.category === key)
  })).filter(g => g.fields.length > 0);

  return (
    <div className="w-64 bg-slate-900 border-r border-slate-700 flex flex-col">
      <div className="p-4 border-b border-slate-700">
        <h3 className="text-sm font-semibold text-white mb-2">Field Types</h3>
        <Input
          placeholder="Search fields..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="bg-slate-800 border-slate-600 text-white text-sm"
        />
      </div>
      <div className="flex-1 overflow-y-auto p-2">
        {groupedFields.map(group => (
          <div key={group.category} className="mb-4">
            <h4 className="text-xs text-slate-400 uppercase tracking-wider px-2 mb-2">
              {group.label}
            </h4>
            <div className="space-y-1">
              {group.fields.map(field => (
                <button
                  key={field.type}
                  onClick={() => onAddField(field.type)}
                  className="w-full flex items-center gap-2 px-3 py-2 text-sm text-slate-300 hover:bg-slate-800 rounded-lg transition-colors"
                  data-testid={`add-field-${field.type}`}
                >
                  <field.icon size={16} />
                  {field.label}
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

const FieldEditor = ({ field, onUpdate, onDelete, onDuplicate, isSelected, onSelect }) => {
  const fieldType = FIELD_TYPES.find(f => f.type === field.field_type);
  const Icon = fieldType?.icon || TypeIcon;

  return (
    <div
      className={`border rounded-lg transition-all ${
        isSelected 
          ? 'border-blue-500 bg-slate-800/50 shadow-lg shadow-blue-500/20' 
          : 'border-slate-700 bg-slate-800/30 hover:border-slate-600'
      }`}
      onClick={() => onSelect(field.id)}
      data-testid={`field-${field.id}`}
    >
      <div className="flex items-center gap-2 p-3 border-b border-slate-700/50">
        <GripVerticalIcon size={16} className="text-slate-500 cursor-move" />
        <Icon size={16} className="text-slate-400" />
        <span className="text-sm text-white flex-1 truncate">{field.label || 'Untitled Field'}</span>
        {field.required && (
          <Badge variant="outline" className="text-xs border-red-500 text-red-400">Required</Badge>
        )}
        <div className="flex gap-1">
          <Button
            variant="ghost"
            size="sm"
            className="h-7 w-7 p-0 text-slate-400 hover:text-white"
            onClick={(e) => { e.stopPropagation(); onDuplicate(field); }}
          >
            <CopyIcon size={14} />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="h-7 w-7 p-0 text-slate-400 hover:text-red-400"
            onClick={(e) => { e.stopPropagation(); onDelete(field.id); }}
          >
            <TrashIcon size={14} />
          </Button>
        </div>
      </div>
      
      {isSelected && (
        <div className="p-4 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              <Label className="text-slate-300 text-xs">Label</Label>
              <Input
                value={field.label}
                onChange={(e) => onUpdate(field.id, { label: e.target.value })}
                className="mt-1 bg-slate-700 border-slate-600 text-white"
                placeholder="Field label"
              />
            </div>
            
            <div className="col-span-2">
              <Label className="text-slate-300 text-xs">Placeholder</Label>
              <Input
                value={field.placeholder || ''}
                onChange={(e) => onUpdate(field.id, { placeholder: e.target.value })}
                className="mt-1 bg-slate-700 border-slate-600 text-white"
                placeholder="Placeholder text"
              />
            </div>

            <div className="col-span-2">
              <Label className="text-slate-300 text-xs">Help Text</Label>
              <Input
                value={field.help_text || ''}
                onChange={(e) => onUpdate(field.id, { help_text: e.target.value })}
                className="mt-1 bg-slate-700 border-slate-600 text-white"
                placeholder="Help text for users"
              />
            </div>

            <div className="flex items-center justify-between col-span-2">
              <Label className="text-slate-300 text-sm">Required Field</Label>
              <Switch
                checked={field.required}
                onCheckedChange={(checked) => onUpdate(field.id, { required: checked })}
              />
            </div>

            <div>
              <Label className="text-slate-300 text-xs">Width</Label>
              <Select
                value={field.width || 'full'}
                onValueChange={(value) => onUpdate(field.id, { width: value })}
              >
                <SelectTrigger className="mt-1 bg-slate-700 border-slate-600 text-white">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="full">Full Width</SelectItem>
                  <SelectItem value="half">Half Width</SelectItem>
                  <SelectItem value="third">Third Width</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {['text', 'textarea'].includes(field.field_type) && (
              <>
                <div>
                  <Label className="text-slate-300 text-xs">Min Length</Label>
                  <Input
                    type="number"
                    value={field.min_length || ''}
                    onChange={(e) => onUpdate(field.id, { min_length: parseInt(e.target.value) || null })}
                    className="mt-1 bg-slate-700 border-slate-600 text-white"
                  />
                </div>
                <div>
                  <Label className="text-slate-300 text-xs">Max Length</Label>
                  <Input
                    type="number"
                    value={field.max_length || ''}
                    onChange={(e) => onUpdate(field.id, { max_length: parseInt(e.target.value) || null })}
                    className="mt-1 bg-slate-700 border-slate-600 text-white"
                  />
                </div>
              </>
            )}

            {field.field_type === 'number' && (
              <>
                <div>
                  <Label className="text-slate-300 text-xs">Min Value</Label>
                  <Input
                    type="number"
                    value={field.min_value || ''}
                    onChange={(e) => onUpdate(field.id, { min_value: parseFloat(e.target.value) || null })}
                    className="mt-1 bg-slate-700 border-slate-600 text-white"
                  />
                </div>
                <div>
                  <Label className="text-slate-300 text-xs">Max Value</Label>
                  <Input
                    type="number"
                    value={field.max_value || ''}
                    onChange={(e) => onUpdate(field.id, { max_value: parseFloat(e.target.value) || null })}
                    className="mt-1 bg-slate-700 border-slate-600 text-white"
                  />
                </div>
              </>
            )}

            {['select', 'multiselect', 'radio', 'checkbox'].includes(field.field_type) && (
              <div className="col-span-2">
                <Label className="text-slate-300 text-xs">Options (one per line)</Label>
                <Textarea
                  value={(field.options || []).map(o => o.label).join('\n')}
                  onChange={(e) => {
                    const options = e.target.value.split('\n').filter(Boolean).map(label => ({
                      value: label.toLowerCase().replace(/\s+/g, '_'),
                      label
                    }));
                    onUpdate(field.id, { options });
                  }}
                  className="mt-1 bg-slate-700 border-slate-600 text-white"
                  rows={4}
                  placeholder="Option 1&#10;Option 2&#10;Option 3"
                />
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

const FormPreview = ({ formName, fields, onClose }) => {
  return (
    <Dialog open={true} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto bg-slate-900 border-slate-700">
        <DialogHeader>
          <DialogTitle className="text-white">{formName || 'Form Preview'}</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 py-4">
          {fields.length === 0 ? (
            <p className="text-slate-400 text-center py-8">No fields added yet</p>
          ) : (
            <div className="grid grid-cols-12 gap-4">
              {fields.map(field => {
                const colSpan = field.width === 'half' ? 6 : field.width === 'third' ? 4 : 12;
                
                return (
                  <div key={field.id} className={`col-span-${colSpan}`} style={{ gridColumn: `span ${colSpan}` }}>
                    {field.field_type === 'section' ? (
                      <div className="border-b border-slate-600 pb-2 mb-2">
                        <h3 className="text-lg font-semibold text-white">{field.label}</h3>
                        {field.help_text && <p className="text-sm text-slate-400">{field.help_text}</p>}
                      </div>
                    ) : field.field_type === 'instructions' ? (
                      <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-3">
                        <p className="text-sm text-blue-200">{field.label}</p>
                      </div>
                    ) : (
                      <div>
                        <Label className="text-slate-300 text-sm">
                          {field.label}
                          {field.required && <span className="text-red-400 ml-1">*</span>}
                        </Label>
                        {field.help_text && (
                          <p className="text-xs text-slate-500 mt-1">{field.help_text}</p>
                        )}
                        <div className="mt-2">
                          {['text', 'number', 'date', 'time', 'datetime'].includes(field.field_type) && (
                            <Input
                              type={field.field_type === 'datetime' ? 'datetime-local' : field.field_type}
                              placeholder={field.placeholder}
                              className="bg-slate-800 border-slate-600 text-white"
                              disabled
                            />
                          )}
                          {field.field_type === 'textarea' && (
                            <Textarea
                              placeholder={field.placeholder}
                              className="bg-slate-800 border-slate-600 text-white"
                              disabled
                            />
                          )}
                          {field.field_type === 'select' && (
                            <Select disabled>
                              <SelectTrigger className="bg-slate-800 border-slate-600 text-white">
                                <SelectValue placeholder={field.placeholder || 'Select...'} />
                              </SelectTrigger>
                            </Select>
                          )}
                          {['checkbox', 'radio'].includes(field.field_type) && (
                            <div className="space-y-2">
                              {(field.options || []).map((opt, i) => (
                                <label key={i} className="flex items-center gap-2 text-slate-300">
                                  <input type={field.field_type} disabled className="accent-blue-500" />
                                  {opt.label}
                                </label>
                              ))}
                            </div>
                          )}
                          {field.field_type === 'signature' && (
                            <div className="border-2 border-dashed border-slate-600 rounded-lg h-24 flex items-center justify-center text-slate-500">
                              <PenToolIcon size={24} className="mr-2" />
                              Sign here
                            </div>
                          )}
                          {field.field_type === 'photo' && (
                            <div className="border-2 border-dashed border-slate-600 rounded-lg h-24 flex items-center justify-center text-slate-500">
                              <CameraIcon size={24} className="mr-2" />
                              Take photo
                            </div>
                          )}
                          {field.field_type === 'file' && (
                            <div className="border-2 border-dashed border-slate-600 rounded-lg h-16 flex items-center justify-center text-slate-500">
                              <UploadIcon size={20} className="mr-2" />
                              Upload file
                            </div>
                          )}
                          {field.field_type === 'gps' && (
                            <div className="border border-slate-600 rounded-lg p-3 flex items-center gap-2 text-slate-400">
                              <MapPinIcon size={20} />
                              <span className="text-sm">Location will be captured</span>
                            </div>
                          )}
                          {field.field_type === 'barcode' && (
                            <div className="border-2 border-dashed border-slate-600 rounded-lg h-16 flex items-center justify-center text-slate-500">
                              <QrCodeIcon size={20} className="mr-2" />
                              Scan barcode
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
        <DialogFooter>
          <Button onClick={onClose} className="bg-blue-600 hover:bg-blue-700">Close Preview</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default function FormBuilderPage() {
  const navigate = useNavigate();
  const { templateId } = useParams();
  const isEditing = Boolean(templateId);

  const [formName, setFormName] = useState('');
  const [formDescription, setFormDescription] = useState('');
  const [category, setCategory] = useState('');
  const [fields, setFields] = useState([]);
  const [selectedFieldId, setSelectedFieldId] = useState(null);
  const [showPreview, setShowPreview] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  
  // Form settings
  const [requireSignature, setRequireSignature] = useState(false);
  const [requireGPS, setRequireGPS] = useState(false);
  const [allowDraft, setAllowDraft] = useState(true);
  const [allowEditAfterSubmit, setAllowEditAfterSubmit] = useState(false);
  const [assignableTo, setAssignableTo] = useState('all');

  // Load existing template if editing
  useEffect(() => {
    if (templateId) {
      loadTemplate();
    }
  }, [templateId]);

  const loadTemplate = async () => {
    setLoading(true);
    try {
      const response = await api.get(`/forms/templates/${templateId}`);
      const template = response.data;
      setFormName(template.name);
      setFormDescription(template.description || '');
      setCategory(template.category || '');
      setFields(template.fields || []);
      setRequireSignature(template.require_signature || false);
      setRequireGPS(template.require_gps || false);
      setAllowDraft(template.allow_save_draft !== false);
      setAllowEditAfterSubmit(template.allow_edit_after_submit || false);
      setAssignableTo(template.assignable_to || 'all');
    } catch (error) {
      toast.error('Failed to load form template');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handleAddField = useCallback((fieldType) => {
    const newField = {
      id: `field_${Date.now()}`,
      field_type: fieldType,
      label: FIELD_TYPES.find(f => f.type === fieldType)?.label || 'New Field',
      placeholder: '',
      help_text: '',
      required: false,
      options: [],
      width: 'full',
      order: fields.length
    };
    setFields(prev => [...prev, newField]);
    setSelectedFieldId(newField.id);
  }, [fields.length]);

  const handleUpdateField = useCallback((fieldId, updates) => {
    setFields(prev => prev.map(f => 
      f.id === fieldId ? { ...f, ...updates } : f
    ));
  }, []);

  const handleDeleteField = useCallback((fieldId) => {
    setFields(prev => prev.filter(f => f.id !== fieldId));
    if (selectedFieldId === fieldId) {
      setSelectedFieldId(null);
    }
  }, [selectedFieldId]);

  const handleDuplicateField = useCallback((field) => {
    const newField = {
      ...field,
      id: `field_${Date.now()}`,
      label: `${field.label} (copy)`,
      order: fields.length
    };
    setFields(prev => [...prev, newField]);
    setSelectedFieldId(newField.id);
  }, [fields.length]);

  const handleSave = async () => {
    if (!formName.trim()) {
      toast.error('Please enter a form name');
      return;
    }
    if (fields.length === 0) {
      toast.error('Please add at least one field');
      return;
    }

    setSaving(true);
    try {
      const payload = {
        name: formName,
        description: formDescription,
        category,
        fields: fields.map((f, i) => ({ ...f, order: i })),
        require_signature: requireSignature,
        require_gps: requireGPS,
        allow_save_draft: allowDraft,
        allow_edit_after_submit: allowEditAfterSubmit,
        assignable_to: assignableTo,
        is_active: true
      };

      if (isEditing) {
        await api.patch(`/api/forms/templates/${templateId}`, payload);
        toast.success('Form template updated');
      } else {
        await api.post('/api/forms/templates', payload);
        toast.success('Form template created');
      }
      navigate('/admin/forms');
    } catch (error) {
      toast.error('Failed to save form template');
      console.error(error);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="animate-spin h-8 w-8 border-2 border-blue-500 border-t-transparent rounded-full"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col" data-testid="form-builder-page">
      {/* Header */}
      <header className="bg-slate-900 border-b border-slate-700 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => navigate('/admin/forms')}
              className="text-slate-400 hover:text-white"
            >
              <ArrowLeftIcon size={20} />
            </Button>
            <div>
              <Input
                value={formName}
                onChange={(e) => setFormName(e.target.value)}
                placeholder="Form Name"
                className="text-xl font-bold bg-transparent border-none text-white focus:ring-0 p-0 h-auto"
                data-testid="form-name-input"
              />
              <Input
                value={formDescription}
                onChange={(e) => setFormDescription(e.target.value)}
                placeholder="Add a description..."
                className="text-sm bg-transparent border-none text-slate-400 focus:ring-0 p-0 h-auto mt-1"
              />
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowSettings(true)}
              className="border-slate-600 text-slate-300 hover:text-white"
            >
              <SettingsIcon size={16} className="mr-2" />
              Settings
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowPreview(true)}
              className="border-slate-600 text-slate-300 hover:text-white"
              data-testid="preview-form-btn"
            >
              <EyeIcon size={16} className="mr-2" />
              Preview
            </Button>
            <Button
              onClick={handleSave}
              disabled={saving}
              className="bg-green-600 hover:bg-green-700 text-white"
              data-testid="save-form-btn"
            >
              <SaveIcon size={16} className="mr-2" />
              {saving ? 'Saving...' : 'Save Form'}
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 flex">
        {/* Field Palette */}
        <FieldPalette onAddField={handleAddField} />

        {/* Form Canvas */}
        <div className="flex-1 p-6 overflow-y-auto">
          <div className="max-w-3xl mx-auto">
            {fields.length === 0 ? (
              <div className="border-2 border-dashed border-slate-700 rounded-xl p-12 text-center">
                <PlusIcon size={48} className="text-slate-600 mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-slate-400 mb-2">
                  Start building your form
                </h3>
                <p className="text-slate-500">
                  Click on a field type from the left panel to add it to your form
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {fields.map((field) => (
                  <FieldEditor
                    key={field.id}
                    field={field}
                    onUpdate={handleUpdateField}
                    onDelete={handleDeleteField}
                    onDuplicate={handleDuplicateField}
                    isSelected={selectedFieldId === field.id}
                    onSelect={setSelectedFieldId}
                  />
                ))}
              </div>
            )}

            {fields.length > 0 && (
              <div className="mt-6 flex justify-center">
                <Button
                  variant="outline"
                  onClick={() => setShowPreview(true)}
                  className="border-slate-600 text-slate-300 hover:text-white"
                >
                  <EyeIcon size={16} className="mr-2" />
                  Preview Form ({fields.length} fields)
                </Button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Preview Modal */}
      {showPreview && (
        <FormPreview
          formName={formName}
          fields={fields}
          onClose={() => setShowPreview(false)}
        />
      )}

      {/* Settings Modal */}
      <Dialog open={showSettings} onOpenChange={setShowSettings}>
        <DialogContent className="bg-slate-900 border-slate-700">
          <DialogHeader>
            <DialogTitle className="text-white">Form Settings</DialogTitle>
          </DialogHeader>
          <div className="space-y-6 py-4">
            <div>
              <Label className="text-slate-300">Category</Label>
              <Select value={category} onValueChange={setCategory}>
                <SelectTrigger className="mt-1 bg-slate-800 border-slate-600 text-white">
                  <SelectValue placeholder="Select category" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="checklist">Checklist</SelectItem>
                  <SelectItem value="inspection">Inspection</SelectItem>
                  <SelectItem value="report">Report</SelectItem>
                  <SelectItem value="request">Request</SelectItem>
                  <SelectItem value="incident">Incident</SelectItem>
                  <SelectItem value="other">Other</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label className="text-slate-300">Assignable To</Label>
              <Select value={assignableTo} onValueChange={setAssignableTo}>
                <SelectTrigger className="mt-1 bg-slate-800 border-slate-600 text-white">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Users</SelectItem>
                  <SelectItem value="staff">Staff Only</SelectItem>
                  <SelectItem value="admin">Admin Only</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <Label className="text-slate-300">Require Signature</Label>
                  <p className="text-xs text-slate-500">Users must sign before submitting</p>
                </div>
                <Switch checked={requireSignature} onCheckedChange={setRequireSignature} />
              </div>

              <div className="flex items-center justify-between">
                <div>
                  <Label className="text-slate-300">Require GPS Location</Label>
                  <p className="text-xs text-slate-500">Capture location on submission</p>
                </div>
                <Switch checked={requireGPS} onCheckedChange={setRequireGPS} />
              </div>

              <div className="flex items-center justify-between">
                <div>
                  <Label className="text-slate-300">Allow Save as Draft</Label>
                  <p className="text-xs text-slate-500">Users can save and complete later</p>
                </div>
                <Switch checked={allowDraft} onCheckedChange={setAllowDraft} />
              </div>

              <div className="flex items-center justify-between">
                <div>
                  <Label className="text-slate-300">Allow Edit After Submit</Label>
                  <p className="text-xs text-slate-500">Users can modify submitted forms</p>
                </div>
                <Switch checked={allowEditAfterSubmit} onCheckedChange={setAllowEditAfterSubmit} />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button onClick={() => setShowSettings(false)} className="bg-blue-600 hover:bg-blue-700">
              Done
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
