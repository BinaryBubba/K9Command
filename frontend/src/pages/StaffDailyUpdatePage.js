import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import useAuthStore from '../store/authStore';
import api from '../utils/api';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Textarea } from '../components/ui/textarea';
import { ArrowLeftIcon, CameraIcon, SendIcon, XIcon, DogIcon } from 'lucide-react';
import { toast } from 'sonner';

const StaffDailyUpdatePage = () => {
  const { user } = useAuthStore();
  const navigate = useNavigate();

  const [stays, setStays] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedStay, setSelectedStay] = useState(null);
  const [noteText, setNoteText] = useState('');
  const [photoKeys, setPhotoKeys] = useState([]);
  const [photoPreviews, setPhotoPreviews] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const fetchStays = useCallback(async () => {
    try {
      const res = await api.get('/stays/on-site');
      setStays(res.data || []);
    } catch {
      toast.error('Failed to load on-site dogs');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!user) { navigate('/auth'); return; }
    fetchStays();
  }, [user, navigate, fetchStays]);

  const handlePhotoSelect = async (e) => {
    const files = Array.from(e.target.files || []);
    if (files.length === 0) return;
    setUploading(true);
    try {
      for (const file of files) {
        const formData = new FormData();
        formData.append('file', file);
        const res = await api.post('/uploads/avatar', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        });
        setPhotoKeys(prev => [...prev, res.data.key]);
        setPhotoPreviews(prev => [...prev, URL.createObjectURL(file)]);
      }
    } catch {
      toast.error('Failed to upload photo');
    } finally {
      setUploading(false);
    }
  };

  const removePhoto = (index) => {
    setPhotoKeys(prev => prev.filter((_, i) => i !== index));
    setPhotoPreviews(prev => prev.filter((_, i) => i !== index));
  };

  const handleSend = async () => {
    if (!selectedStay) {
      toast.error('Select a dog first');
      return;
    }
    if (!noteText.trim() && photoKeys.length === 0) {
      toast.error('Add a note or at least one photo');
      return;
    }
    setSubmitting(true);
    try {
      await api.post('/daily-updates', {
        booking_id: selectedStay.booking_id,
        media_keys: photoKeys,
        staff_snippets: noteText.trim() ? [noteText.trim()] : [],
      });
      toast.success(`Update sent for ${selectedStay.dog_name}!`);
      setSelectedStay(null);
      setNoteText('');
      setPhotoKeys([]);
      setPhotoPreviews([]);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to send update');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#F9F7F2]">
      <header className="bg-white border-b shadow-sm sticky top-0 z-10">
        <div className="max-w-2xl mx-auto px-4 py-3 flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={() => navigate(-1)}>
            <ArrowLeftIcon size={18} />
          </Button>
          <h1 className="text-base font-serif font-bold text-primary">Send Daily Update</h1>
        </div>
      </header>

      <main className="max-w-2xl mx-auto px-4 py-6 space-y-4">
        {!selectedStay ? (
          <Card>
            <CardHeader className="pb-2 pt-4">
              <CardTitle className="text-sm">Which dog is this update for?</CardTitle>
            </CardHeader>
            <CardContent className="px-4 pb-4 space-y-2">
              {loading ? (
                <p className="text-sm text-muted-foreground">Loading on-site dogs...</p>
              ) : stays.length === 0 ? (
                <p className="text-sm text-muted-foreground">No dogs currently on-site.</p>
              ) : (
                stays.map(stay => (
                  <button
                    key={stay.id}
                    onClick={() => setSelectedStay(stay)}
                    className="w-full flex items-center gap-3 p-3 rounded-lg border border-border hover:bg-muted text-left"
                  >
                    <DogIcon size={18} className="text-primary" />
                    <div>
                      <p className="text-sm font-medium">{stay.dog_name}</p>
                      <p className="text-xs text-muted-foreground">{stay.room_name || 'No room assigned'}</p>
                    </div>
                  </button>
                ))
              )}
            </CardContent>
          </Card>
        ) : (
          <>
            <Card>
              <CardContent className="py-3 px-4 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <DogIcon size={18} className="text-primary" />
                  <span className="text-sm font-medium">{selectedStay.dog_name}</span>
                </div>
                <Button variant="ghost" size="sm" onClick={() => setSelectedStay(null)}>
                  Change
                </Button>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2 pt-4">
                <CardTitle className="text-sm">Note</CardTitle>
              </CardHeader>
              <CardContent className="px-4 pb-4">
                <Textarea
                  value={noteText}
                  onChange={e => setNoteText(e.target.value)}
                  placeholder="How's their day going? Any fun moments to share?"
                  rows={4}
                />
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2 pt-4">
                <CardTitle className="text-sm flex items-center gap-2">
                  <CameraIcon size={14} /> Photos
                </CardTitle>
              </CardHeader>
              <CardContent className="px-4 pb-4 space-y-3">
                {photoPreviews.length > 0 && (
                  <div className="grid grid-cols-3 gap-2">
                    {photoPreviews.map((url, i) => (
                      <div key={i} className="relative rounded-lg overflow-hidden aspect-square bg-muted">
                        <img src={url} alt="" className="w-full h-full object-cover" />
                        <button
                          onClick={() => removePhoto(i)}
                          className="absolute top-1 right-1 bg-black/60 rounded-full p-1"
                        >
                          <XIcon size={12} className="text-white" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
                <label className="flex items-center justify-center gap-2 border-2 border-dashed border-border rounded-lg p-4 cursor-pointer hover:bg-muted text-sm text-muted-foreground">
                  <CameraIcon size={16} />
                  {uploading ? 'Uploading...' : 'Add Photo(s)'}
                  <input type="file" accept="image/*" multiple className="hidden" onChange={handlePhotoSelect} disabled={uploading} />
                </label>
              </CardContent>
            </Card>

            <Button className="w-full" onClick={handleSend} disabled={submitting || uploading}>
              <SendIcon size={16} className="mr-2" />
              {submitting ? 'Sending...' : `Send Update to ${selectedStay.dog_name}'s Family`}
            </Button>
          </>
        )}
      </main>
    </div>
  );
};

export default StaffDailyUpdatePage;
