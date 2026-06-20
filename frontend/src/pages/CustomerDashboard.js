import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import useAuthStore from '../store/authStore';
import api from '../utils/api';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { LogOutIcon, DogIcon, CalendarIcon, FileTextIcon, ShieldCheckIcon, PlusIcon, ChevronRightIcon } from 'lucide-react';
import { toast } from 'sonner';

const STATUS_COLORS = {
  confirmed: 'bg-blue-100 text-blue-700',
  checked_in: 'bg-green-100 text-green-700',
  checked_out: 'bg-gray-100 text-gray-600',
  cancelled: 'bg-red-100 text-red-600',
  pending: 'bg-amber-100 text-amber-700',
};

const CustomerDashboard = () => {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const [bookings, setBookings] = useState([]);
  const [dogs, setDogs] = useState([]);
  const [forms, setForms] = useState([]);
  const [vaccinations, setVaccinations] = useState([]);
  const [household, setHousehold] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    try {
      const [bookRes, dogsRes, formsRes] = await Promise.all([
        api.get('/bookings', { params: { limit: 20 } }),
        api.get('/dogs', { params: { limit: 50 } }),
        api.get('/forms').catch(() => ({ data: [] })),
      ]);
      setBookings(bookRes.data || []);
      const dogList = dogsRes.data?.dogs || dogsRes.data || [];
      setDogs(dogList);
      setForms(formsRes.data || []);

      // Fetch vaccinations for all dogs
      if (dogList.length > 0) {
        const vacPromises = dogList.map(d =>
          api.get(`/vaccinations/dog/${d.id}`).catch(() => ({ data: [] }))
        );
        const vacResults = await Promise.all(vacPromises);
        const allVacs = vacResults.flatMap((r, i) =>
          (r.data || []).map(v => ({ ...v, dog_name: dogList[i].name, dog_id: dogList[i].id }))
        );
        setVaccinations(allVacs);
      }

      // Get household info
      const hhRes = await api.get('/households').catch(() => ({ data: [] }));
      if (hhRes.data?.length > 0) setHousehold(hhRes.data[0]);
    } catch { toast.error('Failed to load data'); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => {
    if (!user) { navigate('/auth'); return; }
    fetchData();
  }, [user, navigate, fetchData]);

  const handleLogout = () => { logout(); navigate('/'); };

  const upcoming = bookings.filter(b => ['confirmed','pending','checked_in'].includes(b.status?.toLowerCase()));
  const past = bookings.filter(b => ['checked_out','cancelled'].includes(b.status?.toLowerCase()));

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
            <LogOutIcon size={16} className="mr-1" /> Logout
          </Button>
        </div>
      </header>

      <main className="max-w-2xl mx-auto px-4 py-4">
        <Tabs defaultValue="bookings">
          <TabsList className="w-full mb-4">
            <TabsTrigger value="bookings" className="flex-1">
              <CalendarIcon size={14} className="mr-1" /> Bookings
            </TabsTrigger>
            <TabsTrigger value="dogs" className="flex-1">
              <DogIcon size={14} className="mr-1" /> My Dogs
            </TabsTrigger>
            <TabsTrigger value="forms" className="flex-1">
              <FileTextIcon size={14} className="mr-1" /> Forms
            </TabsTrigger>
            <TabsTrigger value="vaccines" className="flex-1">
              <ShieldCheckIcon size={14} className="mr-1" /> Vaccines
            </TabsTrigger>
          </TabsList>

          {/* Bookings tab */}
          <TabsContent value="bookings" className="space-y-4">
            <Card className="bg-primary/5 border-primary/20">
              <CardContent className="py-4 px-4">
                <p className="text-sm font-medium text-primary">Need to book a stay?</p>
                <p className="text-xs text-muted-foreground mt-1">Call us at <strong>(763) 000-0000</strong> or email <strong>info@k9countryclubkennel.com</strong></p>
              </CardContent>
            </Card>

            {upcoming.length > 0 && (
              <div>
                <h3 className="text-sm font-medium text-muted-foreground mb-2">Upcoming ({upcoming.length})</h3>
                {upcoming.map(b => <BookingCard key={b.id} booking={b} dogs={dogs} />)}
              </div>
            )}

            {past.length > 0 && (
              <div>
                <h3 className="text-sm font-medium text-muted-foreground mb-2">Past Stays</h3>
                {past.slice(0, 5).map(b => <BookingCard key={b.id} booking={b} dogs={dogs} />)}
              </div>
            )}

            {bookings.length === 0 && (
              <Card><CardContent className="py-12 text-center text-muted-foreground">No bookings on record</CardContent></Card>
            )}
          </TabsContent>

          {/* Dogs tab */}
          <TabsContent value="dogs" className="space-y-3">
            {dogs.length === 0 ? (
              <Card><CardContent className="py-12 text-center text-muted-foreground">No dogs on your account</CardContent></Card>
            ) : dogs.map(dog => (
              <Card key={dog.id}>
                <CardContent className="py-3 px-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="bg-primary/10 p-2 rounded-full">
                        <DogIcon size={16} className="text-primary" />
                      </div>
                      <div>
                        <p className="font-medium text-sm">{dog.name}</p>
                        <p className="text-xs text-muted-foreground">
                          {[dog.breed, dog.age ? `${dog.age} yrs` : null, dog.weight ? `${dog.weight} lbs` : null].filter(Boolean).join(' · ')}
                        </p>
                        <div className="flex gap-1 mt-1">
                          {dog.meet_and_greet_status === 'completed' && (
                            <Badge className="text-xs bg-green-100 text-green-700">M&G Complete</Badge>
                          )}
                          {dog.is_neutered && <Badge variant="outline" className="text-xs">Fixed</Badge>}
                        </div>
                      </div>
                    </div>
                  </div>
                  {/* Vaccination status for this dog */}
                  {vaccinations.filter(v => v.dog_id === dog.id).length > 0 && (
                    <div className="mt-2 pt-2 border-t">
                      <p className="text-xs font-medium text-muted-foreground mb-1">Vaccinations</p>
                      <div className="flex flex-wrap gap-1">
                        {vaccinations.filter(v => v.dog_id === dog.id).map(v => (
                          <Badge key={v.id} className={`text-xs ${
                            v.status === 'verified' ? 'bg-green-100 text-green-700' :
                            v.status === 'pending' ? 'bg-amber-100 text-amber-700' :
                            'bg-red-100 text-red-700'
                          }`}>
                            {v.vaccine_type}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}
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

          {/* Vaccines tab */}
          <TabsContent value="vaccines" className="space-y-3">
            <Card className="bg-blue-50 border-blue-200">
              <CardContent className="py-3 px-4">
                <p className="text-xs text-blue-800">
                  Upload vaccination records for your dogs. Required: Rabies, Bordetella, DHPP. Records will be reviewed by staff.
                </p>
              </CardContent>
            </Card>
            {dogs.map(dog => (
              <Card key={dog.id}>
                <CardHeader className="pb-2 pt-3 px-4">
                  <CardTitle className="text-sm flex items-center justify-between">
                    <span>{dog.name}</span>
                    <Button size="sm" variant="outline" className="h-7 text-xs"
                      onClick={() => navigate(`/upload/vaccination?dog_id=${dog.id}`)}>
                      <PlusIcon size={12} className="mr-1" /> Upload
                    </Button>
                  </CardTitle>
                </CardHeader>
                <CardContent className="px-4 pb-3">
                  {vaccinations.filter(v => v.dog_id === dog.id).length === 0 ? (
                    <p className="text-xs text-amber-600">No vaccination records on file</p>
                  ) : vaccinations.filter(v => v.dog_id === dog.id).map(v => (
                    <div key={v.id} className="flex items-center justify-between py-1.5 border-b last:border-0">
                      <div>
                        <p className="text-sm">{v.vaccine_type}</p>
                        {v.expiry_date && (
                          <p className="text-xs text-muted-foreground">
                            Expires {new Date(v.expiry_date).toLocaleDateString()}
                          </p>
                        )}
                      </div>
                      <Badge className={`text-xs ${
                        v.status === 'verified' ? 'bg-green-100 text-green-700' :
                        v.status === 'pending' ? 'bg-amber-100 text-amber-700' :
                        'bg-red-100 text-red-700'
                      }`}>{v.status}</Badge>
                    </div>
                  ))}
                </CardContent>
              </Card>
            ))}
            {dogs.length === 0 && (
              <Card><CardContent className="py-8 text-center text-muted-foreground text-sm">No dogs on your account</CardContent></Card>
            )}
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
};

const BookingCard = ({ booking: b, dogs }) => {
  const dogNames = b.dog_names?.length > 0
    ? b.dog_names.join(', ')
    : `${b.dog_ids?.length || 0} dog${b.dog_ids?.length !== 1 ? 's' : ''}`;
  const nights = Math.ceil((new Date(b.check_out_date) - new Date(b.check_in_date)) / (1000*60*60*24));
  return (
    <Card className="mb-2">
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
              <p className="text-xs text-muted-foreground">{dogNames} · {nights} night{nights !== 1 ? 's' : ''}</p>
            </div>
          </div>
          <Badge className={`text-xs shrink-0 ${STATUS_COLORS[b.status?.toLowerCase()] || 'bg-gray-100 text-gray-600'}`}>
            {b.status?.replace('_', ' ')}
          </Badge>
        </div>
      </CardContent>
    </Card>
  );
};

export default CustomerDashboard;
