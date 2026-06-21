import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import useAuthStore from '../store/authStore';
import api from '../utils/api';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { ArrowLeftIcon, DogIcon, PlusIcon } from 'lucide-react';
import { toast } from 'sonner';

const CustomerDogPage = () => {
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const { dogId } = useParams();
  const [dog, setDog] = useState(null);
  const [vaccinations, setVaccinations] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    try {
      const [dogRes, vacRes] = await Promise.all([
        api.get(`/dogs/${dogId}`),
        api.get(`/vaccinations/dog/${dogId}`).catch(() => ({ data: [] })),
      ]);
      setDog(dogRes.data);
      setVaccinations(vacRes.data || []);
    } catch { toast.error('Failed to load dog profile'); }
    finally { setLoading(false); }
  }, [dogId]);

  useEffect(() => {
    if (!user) { navigate('/auth'); return; }
    fetchData();
  }, [user, navigate, fetchData]);

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-primary"></div>
    </div>
  );
  if (!dog) return <div className="p-4">Dog not found</div>;

  const today = new Date();
  const in30 = new Date(today.getTime() + 30*24*60*60*1000);

  const handlePhotoUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('dog_id', dogId);
      await api.post('/uploads/dog-photo', formData, { headers: { 'Content-Type': 'multipart/form-data' } });
      toast.success('Photo uploaded!');
      fetchDog();
    } catch { toast.error('Upload failed'); }
  };

  const photoRef = React.useRef();

  return (
    <div className="min-h-screen bg-[#F9F7F2]">
      <header className="bg-white border-b shadow-sm sticky top-0 z-10">
        <div className="max-w-2xl mx-auto px-4 py-3 flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={() => navigate('/customer/dashboard')}>
            <ArrowLeftIcon size={18} />
          </Button>
          <h1 className="text-base font-serif font-bold text-primary">{dog.name}</h1>
        </div>
      </header>

      <main className="max-w-2xl mx-auto px-4 py-6 space-y-4">
        {/* Dog profile */}
        <Card>
          <CardContent className="py-4 px-4">
            <div className="flex items-center gap-4">
              {dog.photo_url ? (
                <img src={dog.photo_url} alt={dog.name} className="w-16 h-16 rounded-full object-cover" />
              ) : (
                <div className="bg-primary/10 w-16 h-16 rounded-full flex items-center justify-center">
                  <DogIcon size={28} className="text-primary" />
                </div>
              )}
              <div>
                <h2 className="text-lg font-bold">{dog.name}</h2>
                <p className="text-sm text-muted-foreground">
                  {[dog.breed, dog.age ? `${dog.age} yrs` : null, dog.weight ? `${dog.weight} lbs` : null].filter(Boolean).join(' · ')}
                </p>
                <div className="flex gap-1 mt-1">
                  {dog.meet_and_greet_status === 'completed' && <Badge className="text-xs bg-green-100 text-green-700">M&G ✓</Badge>}
                  {dog.is_neutered && <Badge variant="outline" className="text-xs">Fixed</Badge>}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Vaccinations */}
        <Card>
          <CardHeader className="pb-2 pt-4 px-4">
            <CardTitle className="text-sm flex items-center justify-between">
              Vaccinations
              <Button size="sm" variant="outline" className="h-7 text-xs">
                <PlusIcon size={12} className="mr-1" /> Upload Record
              </Button>
            </CardTitle>
          </CardHeader>
          <CardContent className="px-4 pb-4">
            {vaccinations.length === 0 ? (
              <p className="text-sm text-amber-600">No vaccination records on file</p>
            ) : vaccinations.map(v => {
              const expiry = v.expiry_date ? new Date(v.expiry_date) : null;
              const isExpiring = expiry && expiry > today && expiry <= in30;
              const isExpired = expiry && expiry < today;
              return (
                <div key={v.id} className="flex items-center justify-between py-2 border-b last:border-0">
                  <div>
                    <p className="text-sm font-medium">{v.vaccine_type}</p>
                    {expiry && (
                      <p className={`text-xs ${isExpired ? 'text-red-600' : isExpiring ? 'text-amber-600' : 'text-muted-foreground'}`}>
                        {isExpired ? '⚠️ Expired' : isExpiring ? '⚠️ Expiring soon'  : 'Expires'} {expiry.toLocaleDateString()}
                      </p>
                    )}
                  </div>
                  <Badge className={`text-xs ${
                    v.status === 'verified' ? 'bg-green-100 text-green-700' :
                    v.status === 'pending' ? 'bg-amber-100 text-amber-700' :
                    'bg-red-100 text-red-700'}`}>{v.status}</Badge>
                </div>
              );
            })}
          </CardContent>
        </Card>

        {/* Photos */}
        {dog.photo_url && (
          <Card>
            <CardHeader className="pb-2 pt-4 px-4">
              <CardTitle className="text-sm">Photos</CardTitle>
            </CardHeader>
            <CardContent className="px-4 pb-4">
              <div className="grid grid-cols-3 gap-2">
                <div className="rounded-lg overflow-hidden aspect-square bg-muted">
                  <img src={dog.photo_url} alt={dog.name} className="w-full h-full object-cover" />
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </main>
    </div>
  );
};

export default CustomerDogPage;
