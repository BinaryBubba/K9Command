import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import useAuthStore from '../store/authStore';
import api from '../utils/api';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { CalendarIcon, PencilIcon, PlusIcon, ClockIcon, DogIcon } from 'lucide-react';
import { toast } from 'sonner';

const STATUS_COLORS = {
  confirmed: 'bg-blue-100 text-blue-700',
  checked_in: 'bg-green-100 text-green-700',
  checked_out: 'bg-gray-100 text-gray-600',
  cancelled: 'bg-red-100 text-red-700',
  pending: 'bg-amber-100 text-amber-700',
};

const BookingProfilePage = () => {
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const { bookingId } = useParams();
  const [booking, setBooking] = useState(null);
  const [dogs, setDogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [showAddNote, setShowAddNote] = useState(false);
  const [noteText, setNoteText] = useState('');
  const [notes, setNotes] = useState([]);
  const [changes, setChanges] = useState([]);

  const fetchData = useCallback(async () => {
    try {
      const res = await api.get(`/bookings/${bookingId}`);
      setBooking(res.data);
      // Load notes and changes from localStorage (quick solution)
      const [notesRes, changesRes] = await Promise.all([
        api.get(`/bookings/${bookingId}/notes`).catch(() => ({ data: [] })),
        Promise.resolve({ data: JSON.parse(localStorage.getItem(`booking_changes_${bookingId}`) || '[]') }),
      ]);
      setNotes(notesRes.data);
      setChanges(changesRes.data);
      // Fetch dog details
      if (res.data.dog_ids?.length) {
        const dogData = await Promise.all(
          res.data.dog_ids.map(id => api.get(`/dogs/${id}`).catch(() => null))
        );
        setDogs(dogData.filter(Boolean).map(r => r.data));
      }
    } catch { toast.error('Failed to load booking'); }
    finally { setLoading(false); }
  }, [bookingId]);

  useEffect(() => {
    if (!user) { navigate('/auth'); return; }
    fetchData();
  }, [user, navigate, fetchData]);

  const handleAddNote = async () => {
    if (!noteText.trim()) return;
    try {
      await api.post(`/bookings/${bookingId}/notes`, { note_text: noteText });
      setNoteText('');
      setShowAddNote(false);
      toast.success('Note added');
      fetchData();
    } catch { toast.error('Failed to add note'); }
  };

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-primary"></div>
    </div>
  );

  if (!booking) return <div className="p-4">Booking not found</div>;

  const nights = Math.ceil((new Date(booking.check_out_date) - new Date(booking.check_in_date)) / (1000*60*60*24));

  return (
    <div className="min-h-screen bg-[#F9F7F2]">
      <header className="bg-white border-b shadow-sm sticky top-0 z-10">
        <div className="max-w-3xl mx-auto px-4 py-3 flex items-center justify-between">
          <div>
            <h1 className="text-base font-serif font-bold text-primary">
              {booking.household_name || 'Booking'}
            </h1>
            <p className="text-xs text-muted-foreground">
              {new Date(booking.check_in_date).toLocaleDateString()} — {new Date(booking.check_out_date).toLocaleDateString()} · {nights} night{nights !== 1 ? 's' : ''}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Badge className={`text-xs ${STATUS_COLORS[booking.status?.toLowerCase()] || STATUS_COLORS.confirmed}`}>
              {booking.status?.replace('_', ' ')}
            </Badge>
            {user?.role !== 'customer' && (
              <Button size="sm" variant="outline" onClick={() => setEditing(!editing)}>
                <PencilIcon size={14} className="mr-1" /> {editing ? 'Cancel' : 'Edit'}
              </Button>
            )}
          </div>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 py-6 space-y-4">
        {/* Booking details */}
        <Card>
          <CardContent className="py-4 space-y-3">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-muted-foreground">Check-In</p>
                <p className="text-sm font-medium">{new Date(booking.check_in_date).toLocaleDateString([], {weekday:'short', month:'short', day:'numeric', year:'numeric'})}</p>
                <p className="text-xs text-muted-foreground">{new Date(booking.check_in_date).toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Check-Out</p>
                <p className="text-sm font-medium">{new Date(booking.check_out_date).toLocaleDateString([], {weekday:'short', month:'short', day:'numeric', year:'numeric'})}</p>
                <p className="text-xs text-muted-foreground">{new Date(booking.check_out_date).toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})}</p>
              </div>
            </div>
            <div className="border-t pt-3">
              <p className="text-xs text-muted-foreground mb-2">Dogs</p>
              <div className="flex flex-wrap gap-2">
                {dogs.map(dog => (
                  <button key={dog.id}
                    onClick={() => navigate(`/admin/dogs/${dog.id}`)}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-muted rounded-full text-sm hover:bg-muted/80">
                    <DogIcon size={12} />
                    {dog.name}
                    {dog.breed && <span className="text-muted-foreground text-xs">· {dog.breed}</span>}
                  </button>
                ))}
              </div>
            </div>
            {booking.special_request && (
              <div className="border-t pt-3">
                <p className="text-xs text-muted-foreground">Special Request</p>
                <p className="text-sm mt-1">{booking.special_request}</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Edit form */}
        {editing && (
          <BookingEditForm
            booking={booking}
            onSave={(change) => {
              const updated = [change, ...changes];
              localStorage.setItem(`booking_changes_${bookingId}`, JSON.stringify(updated));
              setChanges(updated);
              setEditing(false);
              fetchData();
            }}
            onCancel={() => setEditing(false)}
            currentUser={user}
          />
        )}

        {/* Notes */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-medium">Stay Notes ({notes.length})</h3>
            <Button size="sm" onClick={() => setShowAddNote(!showAddNote)}>
              <PlusIcon size={14} className="mr-1" /> Add Note
            </Button>
          </div>
          {showAddNote && (
            <Card className="mb-3 border-primary/30">
              <CardContent className="pt-4 space-y-3">
                <Textarea value={noteText} onChange={e => setNoteText(e.target.value)}
                  rows={3} placeholder="Note about this stay..." />
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={() => setShowAddNote(false)}>Cancel</Button>
                  <Button size="sm" onClick={handleAddNote}>Save Note</Button>
                </div>
              </CardContent>
            </Card>
          )}
          {notes.length === 0 ? (
            <Card><CardContent className="py-8 text-center text-muted-foreground text-sm">No notes yet</CardContent></Card>
          ) : notes.map(note => (
            <Card key={note.id} className="mb-2">
              <CardContent className="py-3 px-4">
                <p className="text-sm">{note.note_text || note.text}</p>
                <p className="text-xs text-muted-foreground mt-1">
                  {note.created_by_name || note.created_by} · {new Date(note.created_at).toLocaleString()}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Change history */}
        {changes.length > 0 && (
          <div>
            <h3 className="text-sm font-medium mb-3">Change History</h3>
            {changes.map((c, i) => (
              <Card key={i} className="mb-2 border-amber-100">
                <CardContent className="py-3 px-4">
                  <div className="flex items-start gap-2">
                    <ClockIcon size={14} className="text-amber-500 mt-0.5 shrink-0" />
                    <div>
                      <p className="text-sm font-medium">{c.description}</p>
                      {c.reason && <p className="text-xs text-muted-foreground">Reason: {c.reason}</p>}
                      <p className="text-xs text-muted-foreground mt-0.5">
                        {c.changed_by} · {new Date(c.changed_at).toLocaleString()}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </main>
    </div>
  );
};

const BookingEditForm = ({ booking, onSave, onCancel, currentUser }) => {
  const [form, setForm] = useState({
    check_in_date: booking.check_in_date ? new Date(booking.check_in_date).toISOString().slice(0,16) : '',
    check_out_date: booking.check_out_date ? new Date(booking.check_out_date).toISOString().slice(0,16) : '',
    special_request: booking.special_request || '',
    notes: booking.notes || '',
  });
  const [reason, setReason] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleSave = async () => {
    if (!reason.trim()) { toast.error('Please provide a reason for the change'); return; }
    setSubmitting(true);
    try {
      await api.patch(`/bookings/${booking.id}`, {
        check_in_date: new Date(form.check_in_date).toISOString(),
        check_out_date: new Date(form.check_out_date).toISOString(),
        special_request: form.special_request,
        notes: form.notes,
      });
      const changes = [];
      if (new Date(form.check_in_date).toISOString() !== booking.check_in_date)
        changes.push(`Check-in changed to ${new Date(form.check_in_date).toLocaleDateString()}`);
      if (new Date(form.check_out_date).toISOString() !== booking.check_out_date)
        changes.push(`Check-out changed to ${new Date(form.check_out_date).toLocaleDateString()}`);
      if (form.special_request !== booking.special_request)
        changes.push('Special request updated');
      onSave({
        description: changes.join(', ') || 'Booking updated',
        reason,
        changed_by: currentUser.full_name,
        changed_at: new Date().toISOString(),
      });
      toast.success('Booking updated');
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed'); }
    finally { setSubmitting(false); }
  };

  return (
    <Card className="border-primary/30">
      <CardHeader className="pb-2 pt-4"><CardTitle className="text-sm">Edit Booking</CardTitle></CardHeader>
      <CardContent className="space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label>Check-In</Label>
            <Input type="datetime-local" value={form.check_in_date}
              onChange={e => setForm(f=>({...f,check_in_date:e.target.value}))} className="mt-1" />
          </div>
          <div>
            <Label>Check-Out</Label>
            <Input type="datetime-local" value={form.check_out_date}
              onChange={e => setForm(f=>({...f,check_out_date:e.target.value}))} className="mt-1" />
          </div>
        </div>
        <div>
          <Label>Special Request</Label>
          <Textarea value={form.special_request} onChange={e => setForm(f=>({...f,special_request:e.target.value}))} className="mt-1" rows={2} />
        </div>
        <div>
          <Label>Reason for Change *</Label>
          <Input value={reason} onChange={e => setReason(e.target.value)} className="mt-1"
            placeholder="e.g. Owner requested early departure, added extra night..." />
        </div>
        <div className="flex gap-3">
          <Button variant="outline" className="flex-1" onClick={onCancel}>Cancel</Button>
          <Button className="flex-1" onClick={handleSave} disabled={submitting}>
            {submitting ? 'Saving...' : 'Save Changes'}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
};

export default BookingProfilePage;
