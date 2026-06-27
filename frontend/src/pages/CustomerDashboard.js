import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import useAuthStore from '../store/authStore';
import api from '../utils/api';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import {
  LogOutIcon, DogIcon, CalendarIcon, FileTextIcon,
  ShieldCheckIcon, ChevronRightIcon, UserIcon, ImageIcon, PhoneIcon, MailIcon
} from 'lucide-react';
import { toast } from 'sonner';

const STATUS_COLORS = {
  confirmed: 'bg-blue-100 text-blue-700',
  checked_in: 'bg-green-100 text-green-700',
  on_site: 'bg-green-100 text-green-700',
  checked_out: 'bg-gray-100 text-gray-600',
  cancelled: 'bg-red-100 text-red-600',
  pending: 'bg-amber-100 text-amber-700',
};

const CustomerDashboard = () => {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const [bookings, setBookings] = useState([]);
  const [magRequests, setMagRequests] = useState([]);
  const [dogs, setDogs] = useState([]);
  const [forms, setForms] = useState([]);
  const [orgSettings, setOrgSettings] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    try {
      const meRes = await api.get('/users/me');
      const householdId = meRes.data.household_id;

      const [bookRes, dogsRes, formsRes, orgRes, magsRes] = await Promise.all([
        householdId ? api.get('/bookings', { params: { household_id: householdId, limit: 30 } }) : Promise.resolve({ data: [] }),
        householdId
          ? api.get('/dogs', { params: { household_id: householdId, limit: 50 } })
          : Promise.resolve({ data: [] }),
        api.get('/forms').catch(() => ({ data: [] })),
        api.get('/users/org/settings').catch(() => ({ data: {} })),
        api.get('/meet-and-greets/upcoming').catch(() => ({ data: [] })),
      ]);

      setBookings(bookRes.data || []);
      // dogs endpoint may return {dogs:[]} or []
      const dogList = dogsRes.data?.dogs || dogsRes.data || [];
      setDogs(dogList);
      setForms(formsRes.data || []);
      setOrgSettings(orgRes.data);
      setMagRequests(magsRes.data || []);
    } catch (err) {
      toast.error('Failed to load data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!user) { navigate('/auth'); return; }
    fetchData();
  }, [user, navigate, fetchData]);

  const handleLogout = () => { logout(); navigate('/'); };

  const currentStay = bookings.find(b => ['checked_in','on_site','CHECKED_IN','ON_SITE'].includes(b.status));
  const pendingStays = bookings.filter(b => ['pending','PENDING'].includes(b.status));
  const upcoming = bookings.filter(b => {
    const s = b.status?.toLowerCase();
    const checkIn = new Date(b.check_in_date);
    return s === 'confirmed' && checkIn >= new Date();
  });
  const past = bookings.filter(b => {
    const s = b.status?.toLowerCase();
    return s === 'checked_out' || s === 'cancelled' || (s === 'confirmed' && new Date(b.check_out_date) < new Date());
  });

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center bg-[#F9F7F2]">
      <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-primary"></div>
    </div>
  );

  return (
    <div className="min-h-screen bg-[#F9F7F2]">
      <header className="bg-white border-b shadow-sm sticky top-0 z-10">
        <div className="max-w-2xl mx-auto px-4 py-3 flex justify-between items-center">
          <div>
            <h1 className="text-base font-serif font-bold text-primary">K9 Country Club</h1>
            <p className="text-xs text-muted-foreground">Welcome, {user?.full_name}</p>
          </div>
          <Button variant="ghost" size="sm" onClick={handleLogout}>
            <LogOutIcon size={16} />
          </Button>
        </div>
      </header>

      <main className="max-w-2xl mx-auto px-4 py-4">
        <Tabs defaultValue="bookings">
          <TabsList className="w-full mb-4">
            <TabsTrigger value="bookings" className="flex-1">Stays</TabsTrigger>
            <TabsTrigger value="dogs" className="flex-1">My Dogs</TabsTrigger>
            <TabsTrigger value="forms" className="flex-1">Forms</TabsTrigger>
            <TabsTrigger value="photos" className="flex-1">Photos</TabsTrigger>
          </TabsList>

          {/* Bookings/Stays tab */}
          <TabsContent value="bookings" className="space-y-4">
            {/* Meet & Greet Appointments */}
            {magRequests.length > 0 && (
              <div>
                <h3 className="text-xs font-medium text-blue-700 mb-2 flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-blue-400 inline-block"></span>
                  Meet & Greet ({magRequests.length})
                </h3>
                {magRequests.map(m => (
                  <div key={m.id} className="p-3 rounded-lg border border-blue-200 bg-blue-50 mb-2">
                    <p className="text-sm font-medium">{m.dog_name} — Meet & Greet</p>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {new Date(m.scheduled_at).toLocaleDateString([], {weekday:'long',month:'short',day:'numeric'})}
                      {' · '}
                      {m.slot === '10:00-10:30' ? '10:00–10:30 AM' :
                       m.slot === '10:30-11:00' ? '10:30–11:00 AM' :
                       m.slot === '11:00-11:30' ? '11:00–11:30 AM' :
                       m.slot === '11:30-12:00' ? '11:30 AM–12:00 PM' :
                       m.slot === '14:00-14:30' ? '2:00–2:30 PM' :
                       m.slot === '14:30-15:00' ? '2:30–3:00 PM' :
                       m.slot === '15:00-15:30' ? '3:00–3:30 PM' :
                       m.slot === '15:30-16:00' ? '3:30–4:00 PM' : m.slot}
                    </p>
                    <span className={`text-xs px-2 py-0.5 rounded-full mt-1 inline-block ${
                      m.status === 'confirmed' ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'
                    }`}>{m.status === 'confirmed' ? 'Confirmed' : 'Pending Confirmation'}</span>
                  </div>
                ))}
              </div>
            )}

            {/* Pending requests */}
            {pendingStays.length > 0 && (
              <div>
                <h3 className="text-xs font-medium text-amber-700 mb-2 flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-amber-400 inline-block"></span>
                  Pending Requests ({pendingStays.length})
                </h3>
                {pendingStays.map(b => (
                  <BookingCard key={b.id} booking={b} onClick={() => navigate(`/customer/stay/${b.id}`)} />
                ))}
              </div>
            )}

            {/* Current stay */}
            {currentStay && (
              <div>
                <h3 className="text-xs font-medium text-green-700 mb-2 flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-green-500 inline-block"></span>
                  Currently Staying
                </h3>
                <Card className="border-green-200 bg-green-50 cursor-pointer"
                  onClick={() => navigate(`/customer/stay/${currentStay.id}`)}>
                  <CardContent className="py-3 px-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-medium text-sm text-green-900">
                          {currentStay.dog_names?.join(', ') || 'Your dog'}
                        </p>
                        <p className="text-xs text-green-700">
                          Checked in {new Date(currentStay.check_in_date).toLocaleDateString()}
                          {' · '}Checking out {new Date(currentStay.check_out_date).toLocaleDateString()}
                        </p>
                      </div>
                      <ChevronRightIcon size={16} className="text-green-600" />
                    </div>
                  </CardContent>
                </Card>
              </div>
            )}

            {/* Contact card */}
            <Card className="bg-primary/5 border-primary/20">
              <CardContent className="py-3 px-4 space-y-1">
                <p className="text-sm font-medium text-primary">Book a stay</p>
                {orgSettings?.contact_phone && (
                  <a href={`tel:${orgSettings.contact_phone}`}
                    className="flex items-center gap-2 text-xs text-primary hover:underline">
                    <PhoneIcon size={12} /> {orgSettings.contact_phone}
                  </a>
                )}
                {orgSettings?.contact_email && (
                  <a href={`mailto:${orgSettings.contact_email}`}
                    className="flex items-center gap-2 text-xs text-primary hover:underline">
                    <MailIcon size={12} /> {orgSettings.contact_email}
                  </a>
                )}
              </CardContent>
            </Card>

            {/* Upcoming */}
            {upcoming.length > 0 && (
              <div>
                <h3 className="text-xs font-medium text-muted-foreground mb-2">Upcoming ({upcoming.length})</h3>
                {upcoming.map(b => (
                  <BookingCard key={b.id} booking={b}
                    onClick={() => navigate(`/customer/stay/${b.id}`)} />
                ))}
              </div>
            )}

            {/* Past */}
            {past.length > 0 && (
              <div>
                <h3 className="text-xs font-medium text-muted-foreground mb-2">Past Stays</h3>
                {past.slice(0, 10).map(b => (
                  <BookingCard key={b.id} booking={b}
                    onClick={() => navigate(`/customer/stay/${b.id}`)} />
                ))}
              </div>
            )}

            {bookings.length === 0 && (
              <Card><CardContent className="py-12 text-center text-muted-foreground">No stays on record</CardContent></Card>
            )}
          </TabsContent>

          {/* Dogs tab */}
          <TabsContent value="dogs" className="space-y-3">
            <div className="flex justify-end mb-2">
              <Button size="sm" variant="outline" onClick={() => navigate('/customer/add-dog')}>+ Add a Dog</Button>
            </div>
            {dogs.length === 0 ? (
              <Card><CardContent className="py-8 text-center space-y-3">
                <p className="text-sm font-medium">No dogs on your account yet</p>
                <p className="text-xs text-muted-foreground">Add your dog — we'll schedule a Meet & Greet before your first stay.</p>
                <Button size="sm" onClick={() => navigate('/customer/add-dog')}>+ Add a Dog</Button>
              </CardContent></Card>
            ) : dogs.map(dog => (
              <Card key={dog.id} className="cursor-pointer hover:shadow-md transition-shadow"
                onClick={() => navigate(`/customer/dog/${dog.id}`)}>
                <CardContent className="py-3 px-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      {dog.photo_url ? (
                        <img src={dog.photo_url} alt={dog.name}
                          className="w-10 h-10 rounded-full object-cover" />
                      ) : (
                        <div className="bg-primary/10 p-2 rounded-full">
                          <DogIcon size={18} className="text-primary" />
                        </div>
                      )}
                      <div>
                        <p className="font-medium text-sm">{dog.name}</p>
                        <p className="text-xs text-muted-foreground">
                          {[dog.breed, dog.age ? `${dog.age} yrs` : null, dog.weight ? `${dog.weight} lbs` : null].filter(Boolean).join(' · ')}
                        </p>
                        <div className="flex gap-1 mt-1">
                          {dog.meet_and_greet_status === 'completed' && (
                            <Badge className="text-xs bg-green-100 text-green-700">M&G ✓</Badge>
                          )}
                        </div>
                      </div>
                    </div>
                    <ChevronRightIcon size={16} className="text-muted-foreground" />
                  </div>
                </CardContent>
              </Card>
            ))}
          </TabsContent>

          {/* Forms tab */}
          <TabsContent value="forms" className="space-y-3">
            <p className="text-xs text-muted-foreground">Complete required forms for your dogs' stays</p>
            {forms.length === 0 ? (
              <Card><CardContent className="py-12 text-center text-muted-foreground">No forms available</CardContent></Card>
            ) : forms.map(form => (
              <Card key={form.id} className="cursor-pointer hover:shadow-md transition-shadow"
                onClick={() => navigate('/forms', { state: { formId: form.id } })}>
                <CardContent className="py-3 px-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <span className="text-xl">{
                        form.form_type === 'intake' ? '🐾' :
                        form.form_type === 'boarding_agreement' ? '📋' :
                        form.form_type === 'vaccination' ? '💉' : '📄'
                      }</span>
                      <div>
                        <p className="font-medium text-sm">{form.title}</p>
                        {form.description && <p className="text-xs text-muted-foreground">{form.description}</p>}
                      </div>
                    </div>
                    <ChevronRightIcon size={16} className="text-muted-foreground" />
                  </div>
                </CardContent>
              </Card>
            ))}
          </TabsContent>

          {/* Photos tab */}
          <TabsContent value="photos">
            <CustomerPhotosView dogs={dogs} />
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
};

const CustomerPhotosView = ({ dogs }) => {
  const [photos, setPhotos] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchPhotos = async () => {
      try {
        const results = await Promise.all(
          dogs.map(d => api.get(`/dogs/${d.id}`).catch(() => ({ data: null })))
        );
        const allPhotos = results.flatMap((r, i) => {
          const dog = r.data;
          if (!dog) return [];
          const photos = [];
          if (dog.photo_url) photos.push({ url: dog.photo_url, dog_name: dogs[i].name, type: 'profile' });
          (dog.mag_photos || []).forEach(p => photos.push({ url: p, dog_name: dogs[i].name, type: 'M&G' }));
          return photos;
        });
        setPhotos(allPhotos);
      } catch { }
      finally { setLoading(false); }
    };
    if (dogs.length > 0) fetchPhotos();
    else setLoading(false);
  }, [dogs]);

  if (loading) return <div className="flex justify-center py-12"><div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-primary"></div></div>;

  if (photos.length === 0) return (
    <Card><CardContent className="py-12 text-center text-muted-foreground">
      <ImageIcon size={32} className="mx-auto mb-2 text-muted-foreground/50" />
      No photos yet
    </CardContent></Card>
  );

  return (
    <div className="grid grid-cols-2 gap-2">
      {photos.map((p, i) => (
        <div key={i} className="relative rounded-xl overflow-hidden aspect-square bg-muted">
          <img src={p.url} alt={p.dog_name} className="w-full h-full object-cover" />
          <div className="absolute bottom-0 left-0 right-0 bg-black/40 px-2 py-1">
            <p className="text-white text-xs font-medium">{p.dog_name}</p>
          </div>
        </div>
      ))}
    </div>
  );
};

const BookingCard = ({ booking: b, onClick }) => {
  const nights = Math.ceil((new Date(b.check_out_date) - new Date(b.check_in_date)) / (1000*60*60*24));
  return (
    <Card className="mb-2 cursor-pointer hover:shadow-md transition-shadow" onClick={onClick}>
      <CardContent className="py-3 px-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <CalendarIcon size={14} className="text-muted-foreground shrink-0" />
            <div>
              <p className="text-sm font-medium">
                {new Date(b.check_in_date).toLocaleDateString([], {month:'short',day:'numeric'})}
                {' — '}
                {new Date(b.check_out_date).toLocaleDateString([], {month:'short',day:'numeric',year:'numeric'})}
              </p>
              <p className="text-xs text-muted-foreground">
                {b.dog_names?.join(', ') || `${b.dog_ids?.length || 0} dog(s)`} · {nights} night{nights !== 1 ? 's' : ''}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-1">
            <Badge className={`text-xs ${STATUS_COLORS[b.status?.toLowerCase()] || 'bg-gray-100 text-gray-600'}`}>
              {b.status?.replace('_',' ')}
            </Badge>
            <ChevronRightIcon size={14} className="text-muted-foreground" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default CustomerDashboard;
