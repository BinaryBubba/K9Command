import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import useAuthStore from '../store/authStore';
import api from '../utils/api';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import {
  CalendarIcon, DogIcon, UserIcon, PhoneIcon,
  MailIcon, AlertCircleIcon, PillIcon, UtensilsIcon,
  ShieldIcon, CheckCircleIcon, XCircleIcon,
} from 'lucide-react';
import { toast } from 'sonner';

const STATUS_COLORS = {
  confirmed: 'bg-blue-100 text-blue-700',
  checked_in: 'bg-green-100 text-green-700',
  checked_out: 'bg-gray-100 text-gray-600',
  cancelled: 'bg-red-100 text-red-600',
};

const BookingProfilePage = () => {
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const { bookingId } = useParams();
  const [booking, setBooking] = useState(null);
  const [household, setHousehold] = useState(null);
  const [dogs, setDogs] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    try {
      const bookingRes = await api.get(`/bookings/${bookingId}`);
      setBooking(bookingRes.data);

      const [hhRes, ...dogResults] = await Promise.all([
        api.get(`/households/${bookingRes.data.household_id}`),
        ...bookingRes.data.dog_ids.map(id =>
          Promise.all([
            api.get(`/dogs/${id}`),
            api.get(`/vaccinations/dog/${id}/status`).catch(() => ({ data: { issues: [] } })),
            api.get(`/care/medications/dog/${id}`).catch(() => ({ data: [] })),
          ])
        ),
      ]);
      setHousehold(hhRes.data);
      setDogs(dogResults.map(([dogRes, vaxRes, medsRes]) => ({
        ...dogRes.data,
        vax_issues: vaxRes.data.issues || [],
        medications: medsRes.data || [],
      })));
    } catch {
      toast.error('Failed to load booking');
    } finally {
      setLoading(false);
    }
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

  if (!booking) return <div className="min-h-screen flex items-center justify-center"><p className="text-muted-foreground">Booking not found</p></div>;

  const nights = Math.ceil((new Date(booking.check_out_date) - new Date(booking.check_in_date)) / (1000*60*60*24));
  const primaryContact = household?.contacts?.find(c => c.is_primary);
  const emergencyContact = household?.contacts?.find(c => c.is_emergency_contact);
  const authorizedPickups = household?.contacts?.filter(c => c.is_authorized_pickup) || [];

  return (
    <div className="min-h-screen bg-[#F9F7F2]">
      <header className="bg-white border-b shadow-sm sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between">
          <div>
            <h1 className="text-lg font-serif font-bold text-primary">{household?.display_name}</h1>
            <p className="text-xs text-muted-foreground">
              {new Date(booking.check_in_date).toLocaleDateString()} — {new Date(booking.check_out_date).toLocaleDateString()} · {nights} night{nights !== 1 ? 's' : ''}
            </p>
          </div>
          <Badge className={`${STATUS_COLORS[booking.status] || 'bg-gray-100 text-gray-600'}`}>
            {booking.status?.replace('_', ' ')}
          </Badge>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-6 space-y-5">

        {/* Contacts */}
        <Card>
          <CardHeader className="pb-2 pt-4">
            <CardTitle className="text-sm flex items-center gap-2"><UserIcon size={14} /> Contacts</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {primaryContact && (
              <ContactRow label="Primary" contact={primaryContact} />
            )}
            {emergencyContact && emergencyContact.id !== primaryContact?.id && (
              <ContactRow label="Emergency" contact={emergencyContact} highlight />
            )}
            {authorizedPickups.length > 0 && (
              <div>
                <p className="text-xs font-medium text-muted-foreground mb-1">Authorized Pickups</p>
                {authorizedPickups.map(c => <ContactRow key={c.id} contact={c} />)}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Dogs */}
        {dogs.map(dog => (
          <Card key={dog.id}>
            <CardHeader className="pb-2 pt-4">
              <CardTitle className="text-sm flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <DogIcon size={14} />
                  {dog.name}
                  {(dog.escape_risk || dog.medical_alert || dog.behavior_profile?.bite_history) && (
                    <AlertCircleIcon size={14} className="text-red-500" />
                  )}
                </span>
                <Button size="sm" variant="ghost" className="h-7 text-xs"
                  onClick={() => navigate(`/admin/dogs/${dog.id}`)}>
                  Full Profile →
                </Button>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {/* Safety flags */}
              {(dog.escape_risk || dog.medical_alert || dog.behavior_profile?.bite_history || dog.behavior_profile?.muzzle_required) && (
                <div className="bg-red-50 border border-red-200 rounded p-2 space-y-0.5">
                  {dog.escape_risk && <p className="text-xs text-red-700">⚠️ Escape risk</p>}
                  {dog.medical_alert && <p className="text-xs text-red-700">🏥 Medical alert</p>}
                  {dog.behavior_profile?.bite_history && <p className="text-xs text-red-700">🦷 Bite history</p>}
                  {dog.behavior_profile?.muzzle_required && <p className="text-xs text-red-700">😷 Muzzle required</p>}
                </div>
              )}

              {/* Vaccination status */}
              <div className="flex items-center gap-2">
                <ShieldIcon size={14} className={dog.vax_issues.length > 0 ? 'text-amber-500' : 'text-green-500'} />
                <span className="text-xs">
                  {dog.vax_issues.length === 0 ? (
                    <span className="text-green-600">Vaccinations up to date</span>
                  ) : (
                    <span className="text-amber-600">{dog.vax_issues.length} vaccination issue{dog.vax_issues.length !== 1 ? 's' : ''}: {dog.vax_issues.map(i => i.vaccination_type).join(', ')}</span>
                  )}
                </span>
              </div>

              {/* Feeding */}
              {dog.meal_routine && (
                <div className="flex items-start gap-2">
                  <UtensilsIcon size={14} className="text-muted-foreground mt-0.5 shrink-0" />
                  <p className="text-xs">{dog.meal_routine}</p>
                </div>
              )}

              {/* Allergies */}
              {dog.allergies && (
                <div className="bg-amber-50 border border-amber-100 rounded p-2">
                  <p className="text-xs font-medium text-amber-800">Allergies: {dog.allergies}</p>
                </div>
              )}

              {/* Medications */}
              {dog.medications?.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-muted-foreground mb-1 flex items-center gap-1">
                    <PillIcon size={12} /> Medications ({dog.medications.length})
                  </p>
                  {dog.medications.map(med => (
                    <div key={med.id} className="text-xs bg-muted/30 rounded p-2 mb-1">
                      <span className="font-medium">{med.name}</span> · {med.dose} · {med.frequency}
                      {med.administration_instructions && <p className="text-muted-foreground mt-0.5">{med.administration_instructions}</p>}
                    </div>
                  ))}
                </div>
              )}

              {/* Behavioral notes */}
              {dog.behavioral_notes && (
                <div className="text-xs text-muted-foreground border-t pt-2">{dog.behavioral_notes}</div>
              )}
            </CardContent>
          </Card>
        ))}

        {/* Booking notes */}
        {(booking.notes || booking.special_request) && (
          <Card>
            <CardHeader className="pb-2 pt-4"><CardTitle className="text-sm">Booking Notes</CardTitle></CardHeader>
            <CardContent>
              {booking.notes && <p className="text-sm">{booking.notes}</p>}
              {booking.special_request && <p className="text-sm text-muted-foreground mt-1">Special request: {booking.special_request}</p>}
            </CardContent>
          </Card>
        )}

        {/* Actions */}
        <div className="flex gap-3 pb-6">
          {booking.status === 'confirmed' && (
            <Button className="flex-1 bg-green-600 hover:bg-green-700" onClick={() => navigate('/admin/check-in-out')}>
              Go to Check In
            </Button>
          )}
          {booking.status === 'checked_in' && (
            <Button className="flex-1" onClick={() => navigate('/admin/check-in-out')}>
              Go to Check Out
            </Button>
          )}
          <Button variant="outline" className="flex-1" onClick={() => navigate(`/admin/customers/${booking.household_id}`)}>
            Customer Profile
          </Button>
        </div>
      </main>
    </div>
  );
};

const ContactRow = ({ label, contact, highlight }) => (
  <div className={`p-2 rounded-lg ${highlight ? 'bg-red-50 border border-red-100' : 'bg-muted/30'}`}>
    <div className="flex items-center gap-2 flex-wrap">
      {label && <Badge className={`text-xs ${highlight ? 'bg-red-100 text-red-700' : 'bg-blue-100 text-blue-700'}`}>{label}</Badge>}
      <p className="text-sm font-medium">{contact.first_name} {contact.last_name}</p>
      {contact.is_authorized_pickup && <Badge className="text-xs bg-green-100 text-green-700">Pickup OK</Badge>}
    </div>
    <div className="flex gap-4 mt-1">
      {contact.phone && <span className="text-xs text-muted-foreground flex items-center gap-1"><PhoneIcon size={11} />{contact.phone}</span>}
      {contact.email && <span className="text-xs text-muted-foreground flex items-center gap-1"><MailIcon size={11} />{contact.email}</span>}
    </div>
  </div>
);

export default BookingProfilePage;
