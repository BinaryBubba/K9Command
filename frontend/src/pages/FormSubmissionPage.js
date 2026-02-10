import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Checkbox } from '../components/ui/checkbox';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { RadioGroup, RadioGroupItem } from '../components/ui/radio-group';
import { toast } from 'sonner';
import { 
  ArrowLeftIcon,
  SaveIcon,
  SendIcon,
  CameraIcon,
  MapPinIcon,
  UploadIcon,
  CheckIcon,
  XIcon,
  Loader2Icon,
  AlertCircleIcon
} from 'lucide-react';
import api from '../utils/api';
import useAuthStore from '../stores/authStore';

const SignaturePad = ({ value, onChange }) => {
  const canvasRef = useRef(null);
  const [isDrawing, setIsDrawing] = useState(false);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = '#1e293b';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.strokeStyle = '#fff';
    ctx.lineWidth = 2;
    ctx.lineCap = 'round';
    
    if (value) {
      const img = new Image();
      img.onload = () => ctx.drawImage(img, 0, 0);
      img.src = value;
    }
  }, []);

  const startDrawing = (e) => {
    setIsDrawing(true);
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const rect = canvas.getBoundingClientRect();
    const x = (e.clientX || e.touches?.[0]?.clientX) - rect.left;
    const y = (e.clientY || e.touches?.[0]?.clientY) - rect.top;
    ctx.beginPath();
    ctx.moveTo(x, y);
  };

  const draw = (e) => {
    if (!isDrawing) return;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const rect = canvas.getBoundingClientRect();
    const x = (e.clientX || e.touches?.[0]?.clientX) - rect.left;
    const y = (e.clientY || e.touches?.[0]?.clientY) - rect.top;
    ctx.lineTo(x, y);
    ctx.stroke();
  };

  const stopDrawing = () => {
    setIsDrawing(false);
    const canvas = canvasRef.current;
    onChange(canvas.toDataURL('image/png'));
  };

  const clearSignature = () => {
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = '#1e293b';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    onChange(null);
  };

  return (
    <div className="space-y-2">
      <canvas
        ref={canvasRef}
        width={400}
        height={150}
        className="border border-slate-600 rounded-lg cursor-crosshair touch-none"
        onMouseDown={startDrawing}
        onMouseMove={draw}
        onMouseUp={stopDrawing}
        onMouseLeave={stopDrawing}
        onTouchStart={startDrawing}
        onTouchMove={draw}
        onTouchEnd={stopDrawing}
      />
      <Button
        type="button"
        variant="outline"
        size="sm"
        onClick={clearSignature}
        className="border-slate-600 text-slate-300"
      >
        Clear Signature
      </Button>
    </div>
  );
};

const PhotoCapture = ({ value, onChange }) => {
  const inputRef = useRef(null);
  const [preview, setPreview] = useState(value);

  const handleCapture = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => {
        setPreview(reader.result);
        onChange(reader.result);
      };
      reader.readAsDataURL(file);
    }
  };

  return (
    <div className="space-y-2">
      {preview ? (
        <div className="relative">
          <img src={preview} alt="Captured" className="w-full max-h-48 object-cover rounded-lg" />
          <Button
            type="button"
            variant="destructive"
            size="sm"
            className="absolute top-2 right-2"
            onClick={() => { setPreview(null); onChange(null); }}
          >
            <XIcon size={14} />
          </Button>
        </div>
      ) : (
        <div 
          onClick={() => inputRef.current?.click()}
          className="border-2 border-dashed border-slate-600 rounded-lg h-32 flex items-center justify-center cursor-pointer hover:border-slate-500 transition-colors"
        >
          <div className="text-center">
            <CameraIcon className="mx-auto text-slate-500 mb-2" size={32} />
            <p className="text-slate-400 text-sm">Tap to take photo</p>
          </div>
        </div>
      )}
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        capture="environment"
        onChange={handleCapture}
        className="hidden"
      />
    </div>
  );
};

const GPSCapture = ({ value, onChange }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const captureLocation = () => {
    setLoading(true);
    setError(null);
    
    if (!navigator.geolocation) {
      setError('Geolocation is not supported');
      setLoading(false);
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        onChange({
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          accuracy: position.coords.accuracy
        });
        setLoading(false);
      },
      (err) => {
        setError(err.message);
        setLoading(false);
      },
      { enableHighAccuracy: true }
    );
  };

  return (
    <div className="space-y-2">
      {value ? (
        <div className="bg-slate-800 rounded-lg p-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <MapPinIcon className="text-green-400" size={20} />
            <div>
              <p className="text-white text-sm">Location Captured</p>
              <p className="text-slate-400 text-xs">
                {value.latitude.toFixed(6)}, {value.longitude.toFixed(6)}
              </p>
            </div>
          </div>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => onChange(null)}
            className="text-slate-400"
          >
            <XIcon size={14} />
          </Button>
        </div>
      ) : (
        <Button
          type="button"
          variant="outline"
          onClick={captureLocation}
          disabled={loading}
          className="w-full border-slate-600 text-slate-300"
        >
          {loading ? (
            <Loader2Icon className="animate-spin mr-2" size={16} />
          ) : (
            <MapPinIcon className="mr-2" size={16} />
          )}
          {loading ? 'Getting location...' : 'Capture Location'}
        </Button>
      )}
      {error && (
        <p className="text-red-400 text-sm flex items-center gap-1">
          <AlertCircleIcon size={14} /> {error}
        </p>
      )}
    </div>
  );
};

export default function FormSubmissionPage() {
  const navigate = useNavigate();
  const { templateId, submissionId } = useParams();
  const [searchParams] = useSearchParams();
  const { user } = useAuthStore();
  
  const [template, setTemplate] = useState(null);
  const [values, setValues] = useState({});
  const [signature, setSignature] = useState(null);
  const [gpsLocation, setGpsLocation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [errors, setErrors] = useState({});

  useEffect(() => {
    loadData();
  }, [templateId, submissionId]);

  const loadData = async () => {
    setLoading(true);
    try {
      if (submissionId) {
        // Load existing submission
        const response = await api.get(`/api/forms/submissions/${submissionId}`);
        const submission = response.data;
        setValues(submission.values || {});
        setSignature(submission.signature_data);
        if (submission.gps_latitude) {
          setGpsLocation({
            latitude: submission.gps_latitude,
            longitude: submission.gps_longitude,
            accuracy: submission.gps_accuracy
          });
        }
        // Load template
        const templateRes = await api.get(`/api/forms/templates/${submission.template_id}`);
        setTemplate(templateRes.data);
      } else if (templateId) {
        // Load template for new submission
        const response = await api.get(`/api/forms/templates/${templateId}`);
        setTemplate(response.data);
      }
    } catch (error) {
      toast.error('Failed to load form');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handleValueChange = (fieldId, value) => {
    setValues(prev => ({ ...prev, [fieldId]: value }));
    setErrors(prev => ({ ...prev, [fieldId]: null }));
  };

  const validateForm = () => {
    const newErrors = {};
    
    if (!template?.fields) return true;

    for (const field of template.fields) {
      if (field.required && !values[field.id]) {
        newErrors[field.id] = `${field.label} is required`;
      }
      if (field.min_length && values[field.id]?.length < field.min_length) {
        newErrors[field.id] = `Minimum ${field.min_length} characters required`;
      }
      if (field.max_length && values[field.id]?.length > field.max_length) {
        newErrors[field.id] = `Maximum ${field.max_length} characters allowed`;
      }
    }

    if (template.require_signature && !signature) {
      newErrors._signature = 'Signature is required';
    }

    if (template.require_gps && !gpsLocation) {
      newErrors._gps = 'GPS location is required';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (asDraft = false) => {
    if (!asDraft && !validateForm()) {
      toast.error('Please fill in all required fields');
      return;
    }

    setSubmitting(true);
    try {
      const payload = {
        template_id: template.id,
        values,
        signature_data: signature,
        gps_latitude: gpsLocation?.latitude,
        gps_longitude: gpsLocation?.longitude,
        gps_accuracy: gpsLocation?.accuracy,
        status: asDraft ? 'draft' : 'submitted'
      };

      if (submissionId) {
        await api.patch(`/api/forms/submissions/${submissionId}`, payload);
        toast.success(asDraft ? 'Draft saved' : 'Form submitted');
      } else {
        await api.post('/api/forms/submissions', payload);
        toast.success(asDraft ? 'Draft saved' : 'Form submitted');
      }

      navigate(user?.role === 'admin' ? '/admin/forms' : '/staff/forms');
    } catch (error) {
      toast.error('Failed to submit form');
      console.error(error);
    } finally {
      setSubmitting(false);
    }
  };

  const renderField = (field) => {
    const error = errors[field.id];
    const value = values[field.id];

    switch (field.field_type) {
      case 'section':
        return (
          <div className="col-span-12 border-b border-slate-700 pb-2 pt-4">
            <h3 className="text-lg font-semibold text-white">{field.label}</h3>
            {field.help_text && <p className="text-sm text-slate-400">{field.help_text}</p>}
          </div>
        );

      case 'instructions':
        return (
          <div className="col-span-12 bg-blue-500/10 border border-blue-500/30 rounded-lg p-4">
            <p className="text-blue-200">{field.label}</p>
          </div>
        );

      case 'text':
      case 'number':
      case 'date':
      case 'time':
      case 'datetime':
        return (
          <div>
            <Label className="text-slate-300">
              {field.label}
              {field.required && <span className="text-red-400 ml-1">*</span>}
            </Label>
            {field.help_text && <p className="text-xs text-slate-500 mt-1">{field.help_text}</p>}
            <Input
              type={field.field_type === 'datetime' ? 'datetime-local' : field.field_type}
              value={value || ''}
              onChange={(e) => handleValueChange(field.id, e.target.value)}
              placeholder={field.placeholder}
              className={`mt-2 bg-slate-800 border-slate-600 text-white ${error ? 'border-red-500' : ''}`}
            />
            {error && <p className="text-red-400 text-xs mt-1">{error}</p>}
          </div>
        );

      case 'textarea':
        return (
          <div>
            <Label className="text-slate-300">
              {field.label}
              {field.required && <span className="text-red-400 ml-1">*</span>}
            </Label>
            {field.help_text && <p className="text-xs text-slate-500 mt-1">{field.help_text}</p>}
            <Textarea
              value={value || ''}
              onChange={(e) => handleValueChange(field.id, e.target.value)}
              placeholder={field.placeholder}
              className={`mt-2 bg-slate-800 border-slate-600 text-white ${error ? 'border-red-500' : ''}`}
              rows={4}
            />
            {error && <p className="text-red-400 text-xs mt-1">{error}</p>}
          </div>
        );

      case 'select':
        return (
          <div>
            <Label className="text-slate-300">
              {field.label}
              {field.required && <span className="text-red-400 ml-1">*</span>}
            </Label>
            {field.help_text && <p className="text-xs text-slate-500 mt-1">{field.help_text}</p>}
            <Select value={value || ''} onValueChange={(v) => handleValueChange(field.id, v)}>
              <SelectTrigger className={`mt-2 bg-slate-800 border-slate-600 text-white ${error ? 'border-red-500' : ''}`}>
                <SelectValue placeholder={field.placeholder || 'Select...'} />
              </SelectTrigger>
              <SelectContent>
                {(field.options || []).map(opt => (
                  <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            {error && <p className="text-red-400 text-xs mt-1">{error}</p>}
          </div>
        );

      case 'multiselect':
        const selectedValues = value || [];
        return (
          <div>
            <Label className="text-slate-300">
              {field.label}
              {field.required && <span className="text-red-400 ml-1">*</span>}
            </Label>
            {field.help_text && <p className="text-xs text-slate-500 mt-1">{field.help_text}</p>}
            <div className="mt-2 space-y-2">
              {(field.options || []).map(opt => (
                <label key={opt.value} className="flex items-center gap-2 text-slate-300">
                  <Checkbox
                    checked={selectedValues.includes(opt.value)}
                    onCheckedChange={(checked) => {
                      const newValues = checked 
                        ? [...selectedValues, opt.value]
                        : selectedValues.filter(v => v !== opt.value);
                      handleValueChange(field.id, newValues);
                    }}
                  />
                  {opt.label}
                </label>
              ))}
            </div>
            {error && <p className="text-red-400 text-xs mt-1">{error}</p>}
          </div>
        );

      case 'checkbox':
        return (
          <div>
            <Label className="text-slate-300">
              {field.label}
              {field.required && <span className="text-red-400 ml-1">*</span>}
            </Label>
            {field.help_text && <p className="text-xs text-slate-500 mt-1">{field.help_text}</p>}
            <div className="mt-2 space-y-2">
              {(field.options || []).map(opt => (
                <label key={opt.value} className="flex items-center gap-2 text-slate-300">
                  <Checkbox
                    checked={(value || []).includes(opt.value)}
                    onCheckedChange={(checked) => {
                      const current = value || [];
                      const newValues = checked 
                        ? [...current, opt.value]
                        : current.filter(v => v !== opt.value);
                      handleValueChange(field.id, newValues);
                    }}
                  />
                  {opt.label}
                </label>
              ))}
            </div>
            {error && <p className="text-red-400 text-xs mt-1">{error}</p>}
          </div>
        );

      case 'radio':
        return (
          <div>
            <Label className="text-slate-300">
              {field.label}
              {field.required && <span className="text-red-400 ml-1">*</span>}
            </Label>
            {field.help_text && <p className="text-xs text-slate-500 mt-1">{field.help_text}</p>}
            <RadioGroup 
              value={value || ''} 
              onValueChange={(v) => handleValueChange(field.id, v)}
              className="mt-2 space-y-2"
            >
              {(field.options || []).map(opt => (
                <div key={opt.value} className="flex items-center gap-2">
                  <RadioGroupItem value={opt.value} id={`${field.id}-${opt.value}`} />
                  <Label htmlFor={`${field.id}-${opt.value}`} className="text-slate-300">{opt.label}</Label>
                </div>
              ))}
            </RadioGroup>
            {error && <p className="text-red-400 text-xs mt-1">{error}</p>}
          </div>
        );

      case 'signature':
        return (
          <div>
            <Label className="text-slate-300">
              {field.label}
              {field.required && <span className="text-red-400 ml-1">*</span>}
            </Label>
            {field.help_text && <p className="text-xs text-slate-500 mt-1">{field.help_text}</p>}
            <div className="mt-2">
              <SignaturePad value={value} onChange={(v) => handleValueChange(field.id, v)} />
            </div>
            {error && <p className="text-red-400 text-xs mt-1">{error}</p>}
          </div>
        );

      case 'photo':
        return (
          <div>
            <Label className="text-slate-300">
              {field.label}
              {field.required && <span className="text-red-400 ml-1">*</span>}
            </Label>
            {field.help_text && <p className="text-xs text-slate-500 mt-1">{field.help_text}</p>}
            <div className="mt-2">
              <PhotoCapture value={value} onChange={(v) => handleValueChange(field.id, v)} />
            </div>
            {error && <p className="text-red-400 text-xs mt-1">{error}</p>}
          </div>
        );

      case 'gps':
        return (
          <div>
            <Label className="text-slate-300">
              {field.label}
              {field.required && <span className="text-red-400 ml-1">*</span>}
            </Label>
            {field.help_text && <p className="text-xs text-slate-500 mt-1">{field.help_text}</p>}
            <div className="mt-2">
              <GPSCapture value={value} onChange={(v) => handleValueChange(field.id, v)} />
            </div>
            {error && <p className="text-red-400 text-xs mt-1">{error}</p>}
          </div>
        );

      case 'file':
        return (
          <div>
            <Label className="text-slate-300">
              {field.label}
              {field.required && <span className="text-red-400 ml-1">*</span>}
            </Label>
            {field.help_text && <p className="text-xs text-slate-500 mt-1">{field.help_text}</p>}
            <div className="mt-2">
              <Input
                type="file"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) handleValueChange(field.id, file.name);
                }}
                className="bg-slate-800 border-slate-600 text-white"
              />
            </div>
            {error && <p className="text-red-400 text-xs mt-1">{error}</p>}
          </div>
        );

      default:
        return null;
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="animate-spin h-8 w-8 border-2 border-blue-500 border-t-transparent rounded-full"></div>
      </div>
    );
  }

  if (!template) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="text-center">
          <AlertCircleIcon className="mx-auto text-red-400 mb-4" size={48} />
          <h2 className="text-xl font-semibold text-white mb-2">Form not found</h2>
          <Button onClick={() => navigate(-1)} className="bg-blue-600 hover:bg-blue-700">
            Go Back
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950" data-testid="form-submission-page">
      {/* Header */}
      <header className="bg-slate-900 border-b border-slate-700 px-6 py-4 sticky top-0 z-10">
        <div className="max-w-3xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => navigate(-1)}
              className="text-slate-400 hover:text-white"
            >
              <ArrowLeftIcon size={20} />
            </Button>
            <div>
              <h1 className="text-xl font-bold text-white">{template.name}</h1>
              {template.description && (
                <p className="text-slate-400 text-sm">{template.description}</p>
              )}
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-6 py-8">
        <Card className="bg-slate-900 border-slate-700">
          <CardContent className="p-6">
            <div className="grid grid-cols-12 gap-6">
              {(template.fields || []).sort((a, b) => a.order - b.order).map(field => {
                const colSpan = field.width === 'half' ? 6 : field.width === 'third' ? 4 : 12;
                return (
                  <div 
                    key={field.id} 
                    className={`col-span-12 md:col-span-${colSpan}`}
                    style={{ gridColumn: `span ${colSpan}` }}
                  >
                    {renderField(field)}
                  </div>
                );
              })}

              {/* Form-level signature */}
              {template.require_signature && (
                <div className="col-span-12 border-t border-slate-700 pt-6">
                  <Label className="text-slate-300">
                    Signature <span className="text-red-400">*</span>
                  </Label>
                  <p className="text-xs text-slate-500 mt-1">Please sign to confirm this submission</p>
                  <div className="mt-2">
                    <SignaturePad value={signature} onChange={setSignature} />
                  </div>
                  {errors._signature && <p className="text-red-400 text-xs mt-1">{errors._signature}</p>}
                </div>
              )}

              {/* Form-level GPS */}
              {template.require_gps && (
                <div className="col-span-12 border-t border-slate-700 pt-6">
                  <Label className="text-slate-300">
                    Location <span className="text-red-400">*</span>
                  </Label>
                  <p className="text-xs text-slate-500 mt-1">Your location will be recorded with this submission</p>
                  <div className="mt-2">
                    <GPSCapture value={gpsLocation} onChange={setGpsLocation} />
                  </div>
                  {errors._gps && <p className="text-red-400 text-xs mt-1">{errors._gps}</p>}
                </div>
              )}
            </div>

            {/* Action Buttons */}
            <div className="flex justify-end gap-3 mt-8 pt-6 border-t border-slate-700">
              {template.allow_save_draft && (
                <Button
                  variant="outline"
                  onClick={() => handleSubmit(true)}
                  disabled={submitting}
                  className="border-slate-600 text-slate-300 hover:text-white"
                  data-testid="save-draft-btn"
                >
                  <SaveIcon size={16} className="mr-2" />
                  Save Draft
                </Button>
              )}
              <Button
                onClick={() => handleSubmit(false)}
                disabled={submitting}
                className="bg-green-600 hover:bg-green-700 text-white"
                data-testid="submit-form-btn"
              >
                {submitting ? (
                  <Loader2Icon className="animate-spin mr-2" size={16} />
                ) : (
                  <SendIcon size={16} className="mr-2" />
                )}
                Submit Form
              </Button>
            </div>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
