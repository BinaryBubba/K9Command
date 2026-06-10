import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import useAuthStore from '../store/authStore';
import api from '../utils/api';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import {
  ArrowLeftIcon, AlertCircleIcon, DogIcon,
  ShieldIcon, UtensilsIcon, PillIcon, ClipboardListIcon,
} from 'lucide-react';
import { toast } from 'sonner';

const DogProfilePage = () => {
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const { dogId } = useParams();
  const [dog, setDog] = useState(null);
  const [stays, setStays] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchDog = useCallback(async () => {
    try {
      const [dogRes, medsRes] = await Promise.all([
        api.get(`/dogs/${dogId}`),
        api.get(`/care/medications/dog/${dogId}`).catch(() => ({ data: [] })),
      ]);
      setDog({ ...dogRes.data, medications: medsRes.data });
    } catch {
      toast.error('Failed to load dog profile');
    } finally {
      setLoading(false);
    }
  }, [dogId]);

  useEffect(() => {
    if (!user) { navigate('/auth'); return; }
    fetchDog();
  }, [user, navigate, fetchDog]);

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-primary"></div>
    </div>
  );

  if (!dog) return (
    <div className="min-h-screen flex items-center justify-center">
      <p className="text-muted-foreground">Dog not found</p>
    </div>
  );

  const hasWarnings = dog.escape_risk || dog.medical_alert ||
    dog.behavior_profile?.bite_history || dog.behavior_profile?.active_safety_alert;

  return (
    <div className="min-h-screen bg-[#F9F7F2]">
      <header className="bg-white border-b shadow-sm sticky top-0 z-10">
        <div className="max-w-3xl mx-auto px-4 py-3 flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={() => navigate(-1)}>
            <ArrowLeftIcon size={18} />
          </Button>
          <div className="flex items-center gap-2">
            <h1 className="text-lg font-serif font-bold text-primary">{dog.name}</h1>
            {hasWarnings && <AlertCircleIcon size={16} className="text-red-500" />}
          </div>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 py-6 space-y-4">

        {/* Safety warnings banner */}
        {hasWarnings && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 space-y-1">
            <p className="text-sm font-semibold text-red-800 flex items-center gap-2">
              <AlertCircleIcon size={16} /> Safety Flags
            </p>
            {dog.escape_risk && <p className="text-xs text-red-700">⚠️ Escape risk — ensure secure handling</p>}
            {dog.medical_alert && <p className="text-xs text-red-700">🏥 Medical alert — review care instructions</p>}
            {dog.behavior_profile?.bite_history && <p className="text-xs text-red-700">🦷 Bite history on record</p>}
            {dog.behavior_profile?.muzzle_required && <p className="text-xs text-red-700">😷 Muzzle required</p>}
            {dog.behavior_profile?.active_safety_alert && (
              <p className="text-xs text-red-700 font-medium">🚨 {dog.behavior_profile.safety_alert_detail || 'Active safety alert'}</p>
            )}
          </div>
        )}

        {/* Quick info */}
        <Card>
          <CardContent className="py-4 px-4">
            <div className="flex items-start gap-4">
              <div className="bg-primary/10 p-3 rounded-full">
                <DogIcon size={24} className="text-primary" />
              </div>
              <div className="flex-1 grid grid-cols-2 gap-x-6 gap-y-1">
                <InfoRow label="Breed" value={dog.breed} />
                <InfoRow label="Age" value={dog.age ? `${dog.age} yr${dog.age !== 1 ? 's' : ''}` : null} />
                <InfoRow label="Weight" value={dog.weight ? `${dog.weight} lbs` : null} />
                <InfoRow label="Gender" value={dog.gender} />
                <InfoRow label="Color" value={dog.color} />
                <InfoRow label="Spay/Neuter" value={dog.spay_neuter_status} />
                {dog.microchip_number && <InfoRow label="Microchip" value={dog.microchip_number} />}
              </div>
            </div>
            <div className="flex gap-2 mt-4 flex-wrap">
              <Badge className={dog.boarding_eligible ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}>
                {dog.boarding_eligible ? '✓ Boarding eligible' : '✗ Boarding ineligible'}
              </Badge>
              <Badge className={dog.daycare_eligible ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}>
                {dog.daycare_eligible ? '✓ Daycare eligible' : '✗ Daycare ineligible'}
              </Badge>
              <Badge variant="outline" className="text-xs">
                M&G: {dog.meet_and_greet_status}
              </Badge>
            </div>
          </CardContent>
        </Card>

        <Tabs defaultValue="care">
          <TabsList className="w-full">
            <TabsTrigger value="care" className="flex-1">Care</TabsTrigger>
            <TabsTrigger value="behavior" className="flex-1">Behavior</TabsTrigger>
            <TabsTrigger value="vaccinations" className="flex-1">Vaccinations</TabsTrigger>
          </TabsList>

          {/* CARE TAB */}
          <TabsContent value="care" className="space-y-4 mt-4">
            <Card>
              <CardHeader className="pb-2 pt-4">
                <CardTitle className="text-sm flex items-center gap-2">
                  <UtensilsIcon size={14} /> Feeding
                </CardTitle>
              </CardHeader>
              <CardContent>
                {dog.meal_routine ? (
                  <p className="text-sm">{dog.meal_routine}</p>
                ) : (
                  <p className="text-sm text-muted-foreground">No feeding routine on file</p>
                )}
                {dog.allergies && (
                  <div className="mt-3 p-2 bg-amber-50 rounded border border-amber-100">
                    <p className="text-xs font-medium text-amber-800">Allergies / Dietary restrictions:</p>
                    <p className="text-xs text-amber-700 mt-0.5">{dog.allergies}</p>
                  </div>
                )}
              </CardContent>
            </Card>

            {dog.medications?.length > 0 && (
              <Card>
                <CardHeader className="pb-2 pt-4">
                  <CardTitle className="text-sm flex items-center gap-2">
                    <PillIcon size={14} /> Medications ({dog.medications.length})
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  {dog.medications.map(med => (
                    <div key={med.id} className="p-3 bg-muted/30 rounded-lg border">
                      <div className="flex items-start justify-between">
                        <div>
                          <p className="font-medium text-sm">{med.name}</p>
                          <p className="text-xs text-muted-foreground">{med.dose} · {med.frequency}</p>
                          {med.administration_instructions && (
                            <p className="text-xs text-muted-foreground mt-1">{med.administration_instructions}</p>
                          )}
                        </div>
                        <Badge variant="outline" className="text-xs">Active</Badge>
                      </div>
                    </div>
                  ))}
                </CardContent>
              </Card>
            )}

            {dog.behavioral_notes && (
              <Card>
                <CardHeader className="pb-2 pt-4">
                  <CardTitle className="text-sm flex items-center gap-2">
                    <ClipboardListIcon size={14} /> Care Notes
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm">{dog.behavioral_notes}</p>
                </CardContent>
              </Card>
            )}
          </TabsContent>

          {/* BEHAVIOR TAB */}
          <TabsContent value="behavior" className="space-y-4 mt-4">
            <Card>
              <CardHeader className="pb-2 pt-4">
                <CardTitle className="text-sm flex items-center gap-2">
                  <ShieldIcon size={14} /> Behavior Profile
                </CardTitle>
              </CardHeader>
              <CardContent>
                {dog.behavior_profile ? (
                  <div className="grid grid-cols-2 gap-3">
                    <FlagRow label="Bite history" value={dog.behavior_profile.bite_history} />
                    <FlagRow label="Food guarding" value={dog.behavior_profile.food_guarding} />
                    <FlagRow label="Toy guarding" value={dog.behavior_profile.toy_guarding} />
                    <FlagRow label="Barrier reactivity" value={dog.behavior_profile.barrier_reactivity} />
                    <FlagRow label="Muzzle required" value={dog.behavior_profile.muzzle_required} />
                    <FlagRow label="Escape risk" value={dog.escape_risk} />
                    {dog.behavior_profile.handlers_required > 1 && (
                      <div className="col-span-2 p-2 bg-amber-50 rounded border border-amber-100">
                        <p className="text-xs text-amber-800">Requires {dog.behavior_profile.handlers_required} handlers</p>
                      </div>
                    )}
                    {dog.behavior_profile.handling_restrictions && (
                      <div className="col-span-2">
                        <p className="text-xs font-medium text-muted-foreground">Handling restrictions:</p>
                        <p className="text-sm mt-1">{dog.behavior_profile.handling_restrictions}</p>
                      </div>
                    )}
                    {dog.behavior_profile.known_triggers && (
                      <div className="col-span-2">
                        <p className="text-xs font-medium text-muted-foreground">Known triggers:</p>
                        <p className="text-sm mt-1">{dog.behavior_profile.known_triggers}</p>
                      </div>
                    )}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">No behavior profile on file</p>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* VACCINATIONS TAB */}
          <TabsContent value="vaccinations" className="space-y-3 mt-4">
            {dog.vaccinations?.length === 0 ? (
              <Card><CardContent className="py-8 text-center text-muted-foreground text-sm">
                No vaccination records on file
              </CardContent></Card>
            ) : (
              dog.vaccinations?.map(v => (
                <Card key={v.id}>
                  <CardContent className="py-3 px-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-medium text-sm">{v.vaccination_type}</p>
                        <p className="text-xs text-muted-foreground">
                          {v.expiration_date ? `Expires: ${new Date(v.expiration_date).toLocaleDateString()}` : 'No expiry'}
                          {v.provider && ` · ${v.provider}`}
                        </p>
                      </div>
                      <Badge className={
                        v.verification_status === 'verified' ? 'bg-green-100 text-green-700' :
                        v.verification_status === 'rejected' ? 'bg-red-100 text-red-700' :
                        'bg-amber-100 text-amber-700'
                      }>
                        {v.verification_status}
                      </Badge>
                    </div>
                  </CardContent>
                </Card>
              ))
            )}
          </TabsContent>
        </Tabs>

      </main>
    </div>
  );
};

const InfoRow = ({ label, value }) => {
  if (!value) return null;
  return (
    <div>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-sm font-medium capitalize">{value}</p>
    </div>
  );
};

const FlagRow = ({ label, value }) => (
  <div className={`p-2 rounded border text-xs font-medium flex items-center gap-1.5 ${
    value ? 'bg-red-50 border-red-200 text-red-700' : 'bg-muted/30 border-border text-muted-foreground'
  }`}>
    <span>{value ? '⚠️' : '✓'}</span> {label}
  </div>
);

export default DogProfilePage;
