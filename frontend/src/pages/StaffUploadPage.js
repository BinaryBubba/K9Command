import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDropzone } from 'react-dropzone';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/card';
import { Checkbox } from '../components/ui/checkbox';
import { ArrowLeftIcon, UploadIcon, XIcon, ImageIcon } from 'lucide-react';
import { toast } from 'sonner';
import api from '../utils/api';
import useAuthStore from '../store/authStore';

const StaffUploadPage = () => {
  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);
  const [loading, setLoading] = useState(false);
  const [activeBookings, setActiveBookings] = useState([]);
  const [selectedBooking, setSelectedBooking] = useState(null);
  const [dogs, setDogs] = useState([]);
  const [dailyUpdate, setDailyUpdate] = useState(null);
  const [uploads, setUploads] = useState([]);
  const [staffSnippet, setStaffSnippet] = useState('');

  useEffect(() => {
    fetchActiveBookings();
  }, []);

  const fetchActiveBookings = async () => {
    try {
      const response = await api.get('/bookings');
      const active = response.data.filter(
        (b) => b.status === 'checked_in'
      );
      setActiveBookings(active);
    } catch (error) {
      toast.error('Failed to load bookings');
    }
  };

  const selectBooking = async (booking) => {
    setSelectedBooking(booking);
    
    // Fetch dogs for this booking
    const dogPromises = booking.dog_ids.map((id) => api.get(`/dogs/${id}`));
    const dogResponses = await Promise.all(dogPromises);
    setDogs(dogResponses.map((r) => r.data));

    // Check if daily update exists, if not create one
    try {
      const updatesRes = await api.get('/daily-updates');
      const existingUpdate = updatesRes.data.find(
        (u) => u.booking_id === booking.id && u.status !== 'sent'
      );

      if (existingUpdate) {
        setDailyUpdate(existingUpdate);
      } else {
        // Create new daily update
        const newUpdate = await api.post('/daily-updates', {
          household_id: booking.household_id,
          booking_id: booking.id,
        });
        setDailyUpdate(newUpdate.data);
      }
    } catch (error) {
      console.error('Error with daily update:', error);
    }
  };

  const onDrop = (acceptedFiles) => {
    const newUploads = acceptedFiles.map((file) => ({
      file,
      preview: URL.createObjectURL(file),
      taggedDogs: [],
      caption: '',
    }));
    setUploads([...uploads, ...newUploads]);
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'image/*': [], 'video/*': [] },
    multiple: true,
  });

  const removeUpload = (index) => {
    setUploads(uploads.filter((_, i) => i !== index));
  };

  const toggleDogTag = (uploadIndex, dogId) => {
    const newUploads = [...uploads];
    const tagged = newUploads[uploadIndex].taggedDogs.includes(dogId);
    if (tagged) {
      newUploads[uploadIndex].taggedDogs = newUploads[uploadIndex].taggedDogs.filter(
        (id) => id !== dogId
      );
    } else {
      newUploads[uploadIndex].taggedDogs.push(dogId);
    }
    setUploads(newUploads);
  };

  const updateCaption = (index, caption) => {
    const newUploads = [...uploads];
    newUploads[index].caption = caption;
    setUploads(newUploads);
  };

  const handleUploadAll = async () => {
    if (!dailyUpdate) {
      toast.error('Please select a booking first');
      return;
    }

    setLoading(true);
    try {
      // Upload each photo
      for (const upload of uploads) {
        const formData = new FormData();
        formData.append('file', upload.file);
        formData.append('dog_ids', upload.taggedDogs.join(','));
        formData.append('caption', upload.caption || '');

        await api.post(`/daily-updates/${dailyUpdate.id}/media`, formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        });
      }

      toast.success(`${uploads.length} photo(s) uploaded successfully!`);
      setUploads([]);
    } catch (error) {
      toast.error('Failed to upload photos');
    } finally {
      setLoading(false);
    }
  };

  const handleAddSnippet = async () => {
    if (!staffSnippet.trim()) {
      toast.error('Please write a note about the dogs\' activities');
      return;
    }

    if (!dailyUpdate) {
      toast.error('Please select a booking first');
      return;
    }

    try {
      const formData = new FormData();
      formData.append('snippet_text', staffSnippet);

      await api.post(`/daily-updates/${dailyUpdate.id}/snippets`, formData);
      toast.success('Your note has been added!');
      setStaffSnippet('');
    } catch (error) {
      toast.error('Failed to add note');
    }
  };

  return (
    <div className="min-h-screen bg-[#F9F7F2]">
      <header className="bg-white border-b border-border/40 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 md:px-8 py-4">
          <Button
            data-testid="back-to-dashboard-button"
            variant="ghost"
            onClick={() => navigate('/staff/dashboard')}
            className="flex items-center gap-2 mb-2"
          >
            <ArrowLeftIcon size={18} />
            Back to Dashboard
          </Button>
          <h1 className="text-3xl font-serif font-bold text-primary">Upload Daily Photos</h1>
          <p className="text-muted-foreground mt-1">Share the fun moments from today!</p>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 md:px-8 py-8">
        {/* Select Booking */}
        <Card data-testid="select-booking-card" className="mb-6 bg-white rounded-2xl border border-border/50 shadow-sm">
          <CardHeader className="border-b border-border/40">
            <CardTitle className="text-2xl font-serif">Select Active Booking</CardTitle>
          </CardHeader>
          <CardContent className="p-6">
            {activeBookings.length === 0 ? (
              <p className="text-center text-muted-foreground py-8">No active bookings today</p>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {activeBookings.map((booking) => (
                  <div
                    key={booking.id}
                    data-testid={`booking-select-${booking.id}`}
                    className={`p-4 rounded-xl border-2 cursor-pointer transition-all ${
                      selectedBooking?.id === booking.id
                        ? 'border-primary bg-primary/5'
                        : 'border-border hover:border-primary/50'
                    }`}
                    onClick={() => selectBooking(booking)}
                  >
                    <h3 className="font-semibold text-lg mb-1">Booking #{booking.id.slice(0, 8)}</h3>
                    <p className="text-sm text-muted-foreground">{booking.dog_ids.length} dog(s)</p>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {selectedBooking && (
          <>
            {/* Add Staff Note */}
            <Card data-testid="staff-note-card" className="mb-6 bg-white rounded-2xl border border-border/50 shadow-sm">
              <CardHeader className="border-b border-border/40">
                <CardTitle className="text-2xl font-serif">Add Your Note</CardTitle>
                <p className="text-sm text-muted-foreground mt-1">
                  Write a quick note about what the dogs did during your shift. Multiple staff can add notes throughout the day.
                </p>
              </CardHeader>
              <CardContent className="p-6">
                <Textarea
                  data-testid="staff-snippet-input"
                  value={staffSnippet}
                  onChange={(e) => setStaffSnippet(e.target.value)}
                  placeholder="e.g., Max and Bella had a blast playing fetch! They ran around for 30 minutes and made lots of new friends."
                  rows={4}
                  className="mb-4"
                />
                <Button
                  data-testid="add-snippet-button"
                  onClick={handleAddSnippet}
                  className="rounded-full"
                >
                  Add Note
                </Button>
              </CardContent>
            </Card>

            {/* Upload Photos */}
            <Card data-testid="upload-photos-card" className="mb-6 bg-white rounded-2xl border border-border/50 shadow-sm">
              <CardHeader className="border-b border-border/40">
                <CardTitle className="text-2xl font-serif">Upload Photos & Videos</CardTitle>
              </CardHeader>
              <CardContent className="p-6">
                {/* Dropzone */}
                <div
                  {...getRootProps()}
                  data-testid="dropzone"
                  className={`border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-all ${
                    isDragActive ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/50'
                  }`}
                >
                  <input {...getInputProps()} />
                  <UploadIcon size={48} className="mx-auto text-muted-foreground mb-4" />
                  <p className="text-lg font-medium mb-2">
                    {isDragActive ? 'Drop files here' : 'Drag & drop photos/videos here'}
                  </p>
                  <p className="text-sm text-muted-foreground">or click to browse</p>
                </div>

                {/* Uploaded Files */}
                {uploads.length > 0 && (
                  <div className="mt-6 space-y-4">
                    <h3 className="font-semibold text-lg">{uploads.length} file(s) ready to upload</h3>
                    {uploads.map((upload, index) => (
                      <Card key={index} data-testid={`upload-item-${index}`} className="border border-border/40">
                        <CardContent className="p-4">
                          <div className="flex gap-4">
                            {/* Preview */}
                            <div className="w-24 h-24 rounded-lg overflow-hidden flex-shrink-0 bg-muted">
                              {upload.file.type.startsWith('image') ? (
                                <img
                                  src={upload.preview}
                                  alt="Preview"
                                  className="w-full h-full object-cover"
                                />
                              ) : (
                                <div className="w-full h-full flex items-center justify-center">
                                  <ImageIcon size={32} className="text-muted-foreground" />
                                </div>
                              )}
                            </div>

                            {/* Details */}
                            <div className="flex-1 space-y-3">
                              <div className="flex justify-between items-start">
                                <p className="font-medium truncate">{upload.file.name}</p>
                                <Button
                                  data-testid={`remove-upload-${index}`}
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => removeUpload(index)}
                                >
                                  <XIcon size={16} />
                                </Button>
                              </div>

                              {/* Tag Dogs */}
                              <div>
                                <Label className="text-sm font-medium mb-2 block">Tag Dogs:</Label>
                                <div className="flex flex-wrap gap-2">
                                  {dogs.map((dog) => (
                                    <div
                                      key={dog.id}
                                      data-testid={`tag-dog-${index}-${dog.id}`}
                                      className={`px-3 py-1 rounded-full border-2 cursor-pointer text-sm ${
                                        upload.taggedDogs.includes(dog.id)
                                          ? 'border-primary bg-primary/10 font-medium'
                                          : 'border-border'
                                      }`}
                                      onClick={() => toggleDogTag(index, dog.id)}
                                    >
                                      {dog.name}
                                    </div>
                                  ))}
                                </div>
                              </div>

                              {/* Caption */}
                              <Input
                                data-testid={`caption-input-${index}`}
                                placeholder="Add caption (optional)"
                                value={upload.caption}
                                onChange={(e) => updateCaption(index, e.target.value)}
                              />
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    ))}

                    <Button
                      data-testid="upload-all-button"
                      onClick={handleUploadAll}
                      disabled={loading}
                      className="w-full py-6 text-lg font-semibold rounded-full"
                    >
                      {loading ? 'Uploading...' : `Upload All ${uploads.length} File(s)`}
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Next Steps */}
            <Card className="bg-gradient-to-br from-primary to-primary/80 text-white rounded-2xl">
              <CardContent className="p-6">
                <h3 className="text-xl font-serif font-bold mb-2">What's Next?</h3>
                <p className="mb-4">
                  After all staff have added their notes and photos, someone will need to generate the AI summary and approve the update for sending.
                </p>
                <Button
                  data-testid="go-to-approve-button"
                  onClick={() => navigate('/staff/approve')}
                  variant="secondary"
                  className="rounded-full"
                >
                  Go to Approval Page
                </Button>
              </CardContent>
            </Card>
          </>
        )}
      </main>
    </div>
  );
};

export default StaffUploadPage;
