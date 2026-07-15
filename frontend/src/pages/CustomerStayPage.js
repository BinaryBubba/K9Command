import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import useAuthStore from '../store/authStore';
import api from '../utils/api';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { ArrowLeftIcon, DogIcon, CalendarIcon, ImageIcon } from 'lucide-react';
import { toast } from 'sonner';

const STATUS_COLORS = {
  confirmed: 'bg-blue-100 text-blue-700',
  checked_in: 'bg-green-100 text-green-700',
  checked_out: 'bg-gray-100 text-gray-600',
  cancelled: 'bg-red-100 text-red-600',
};

const CustomerStayPage = () => {
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const { bookingId } = useParams();
  const [booking, setBooking] = useState(null);
  const [notes, setNotes] = useState([]);
  const [photos, setPhotos] = useState([]);
  const [dailyUpdates, setDailyUpdates] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    try {
      const [bookRes, notesRes] = await Promise.all([
        api.get(`/bookings/${bookingId}`),
        api.get(`/bookings/${bookingId}/notes`).catch(() => ({ data: [] })),
      ]);
      setBooking(bookRes.data);
      setNotes(notesRes.data || []);

      // Fetch incident photos for dogs in this booking
      const dogPhotos = [];
      for (const dogId of (bookRes.data.dog_ids || [])) {
        const dogRes = await api.get(`/dogs/${dogId}`).catch(() => null);
        if (dogRes?.data?.photo_url) {
          dogPhotos.push({ url: dogRes.data.photo_url, dog_name: dogRes.data.name });
        }
      }
      setPhotos(dogPhotos);

      const updatesRes = await api.get('/daily-updates', { params: { booking_id: bookingId } }).catch(() => ({ data: [] }));
      setDailyUpdates(updatesRes.data || []);
    } catch { toast.error('Failed to load stay'); }
    finally { setLoading(false); }
  }, [bookingId]);

  useEffect(() => {
    if (!user) { navigate('/auth'); return; }
    fetchData();
  }, [user, navigate, fetchData]);

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-primary"></div>
    </div>
  );
  if (!booking) return <div className="p-4">Stay not found</div>;

  const nights = Math.ceil((new Date(booking.check_out_date) - new Date(booking.check_in_date)) / (1000*60*60*24));

  return (
    <div className="min-h-screen bg-[#F9F7F2]">
      <header className="bg-white border-b shadow-sm sticky top-0 z-10">
        <div className="max-w-2xl mx-auto px-4 py-3 flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={() => navigate('/customer/dashboard')}>
            <ArrowLeftIcon size={18} />
          </Button>
          <div>
            <h1 className="text-base font-serif font-bold text-primary">Stay Details</h1>
            <p className="text-xs text-muted-foreground">
              {new Date(booking.check_in_date).toLocaleDateString()} — {new Date(booking.check_out_date).toLocaleDateString()}
            </p>
          </div>
          <Badge className={`ml-auto text-xs ${STATUS_COLORS[booking.status?.toLowerCase()] || 'bg-gray-100 text-gray-600'}`}>
            {booking.status?.replace('_',' ')}
          </Badge>
        </div>
      </header>

      <main className="max-w-2xl mx-auto px-4 py-6 space-y-4">
        {/* Stay summary */}
        <Card>
          <CardContent className="py-4 px-4 space-y-3">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-muted-foreground">Check-In</p>
                <p className="text-sm font-medium">{new Date(booking.check_in_date).toLocaleDateString([], {weekday:'short',month:'short',day:'numeric'})}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Check-Out</p>
                <p className="text-sm font-medium">{new Date(booking.check_out_date).toLocaleDateString([], {weekday:'short',month:'short',day:'numeric'})}</p>
              </div>
            </div>
            <div className="border-t pt-3">
              <p className="text-xs text-muted-foreground">{nights} night{nights !== 1 ? 's' : ''}</p>
              {booking.dog_names?.length > 0 && (
                <div className="flex gap-2 mt-2 flex-wrap">
                  {booking.dog_names.map((name, i) => (
                    <span key={i} className="flex items-center gap-1 text-sm">
                      <DogIcon size={12} className="text-muted-foreground" /> {name}
                    </span>
                  ))}
                </div>
              )}
            </div>
            {booking.special_request && (
              <div className="border-t pt-3">
                <p className="text-xs text-muted-foreground">Special Request</p>
                <p className="text-sm mt-1">{booking.special_request}</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Photos */}
        {photos.length > 0 && (
          <div>
            <h3 className="text-sm font-medium mb-2">Photos</h3>
            <div className="grid grid-cols-2 gap-2">
              {photos.map((p, i) => (
                <div key={i} className="rounded-xl overflow-hidden aspect-square bg-muted">
                  <img src={p.url} alt={p.dog_name} className="w-full h-full object-cover" />
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Daily updates from staff -- photos and notes sent during the stay */}
        {dailyUpdates.length > 0 && (
          <div>
            <h3 className="text-sm font-medium mb-2">Updates From Your Dog's Stay</h3>
            {dailyUpdates.map(update => (
              <Card key={update.id} className="mb-2">
                <CardContent className="py-3 px-4 space-y-2">
                  <p className="text-xs text-muted-foreground">
                    {new Date(update.date).toLocaleDateString([], {weekday:'long', month:'short', day:'numeric'})}
                  </p>
                  {update.staff_snippets?.map((note, i) => (
                    <p key={i} className="text-sm">{note}</p>
                  ))}
                  {update.media_urls?.length > 0 && (
                    <div className="grid grid-cols-2 gap-2 mt-2">
                      {update.media_urls.map((url, i) => (
                        <div key={i} className="rounded-xl overflow-hidden aspect-square bg-muted">
                          <img src={url} alt="Daily update" className="w-full h-full object-cover" />
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        )}
        {/* Staff notes visible to customer */}
        {notes.filter(n => n.note_text).length > 0 ? (
          <div>
            <h3 className="text-sm font-medium mb-2">Updates from Staff</h3>
            {notes.map(note => (
              <Card key={note.id} className="mb-2">
                <CardContent className="py-3 px-4">
                  <p className="text-sm">{note.note_text}</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    {note.created_by_name} · {new Date(note.created_at).toLocaleString()}
                  </p>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <Card>
            <CardContent className="py-8 text-center text-muted-foreground text-sm">
              No updates yet — check back during your dog's stay
            </CardContent>
          </Card>
        )}
      </main>
    </div>
  );
};

export default CustomerStayPage;
