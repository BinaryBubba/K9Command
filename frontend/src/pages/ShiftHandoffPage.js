import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import useAuthStore from '../store/authStore';
import api from '../utils/api';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Textarea } from '../components/ui/textarea';
import { Input } from '../components/ui/input';
import { CheckCircleIcon, PlusIcon, XIcon } from 'lucide-react';
import { toast } from 'sonner';

const ShiftHandoffPage = () => {
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const [handoffs, setHandoffs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);

  const fetchHandoffs = useCallback(async () => {
    try {
      const res = await api.get('/care/handoffs', { params: { limit: 20 } });
      setHandoffs(res.data);
    } catch { toast.error('Failed to load handoffs'); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => {
    if (!user) { navigate('/auth'); return; }
    fetchHandoffs();
  }, [user, navigate, fetchHandoffs]);

  const handleAcknowledge = async (id) => {
    try {
      await api.post(`/care/handoffs/${id}/acknowledge`);
      toast.success('Handoff acknowledged');
      fetchHandoffs();
    } catch { toast.error('Failed'); }
  };

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-primary"></div>
    </div>
  );

  return (
    <div className="min-h-screen bg-[#F9F7F2]">
      <header className="bg-white border-b shadow-sm sticky top-0 z-10">
        <div className="max-w-3xl mx-auto px-4 py-3 flex items-center justify-between">
          <h1 className="text-lg font-serif font-bold text-primary">Shift Handoffs</h1>
          <Button size="sm" onClick={() => setShowCreate(true)}>
            Submit Handoff
          </Button>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 py-6 space-y-4">
        {handoffs.length === 0 ? (
          <Card><CardContent className="py-12 text-center text-muted-foreground">No handoffs yet</CardContent></Card>
        ) : handoffs.map(h => (
          <Card key={h.id} className={h.acknowledged_at ? 'opacity-75' : ''}>
            <CardHeader className="pb-2 pt-4 px-4">
              <CardTitle className="text-sm flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span>{h.staff_name}</span>
                  {h.acknowledged_at ? (
                    <Badge className="text-xs bg-green-100 text-green-700">
                      ✓ Ack'd by {h.acknowledged_by_name}
                    </Badge>
                  ) : (
                    <Badge className="text-xs bg-amber-100 text-amber-700">Pending acknowledgment</Badge>
                  )}
                </div>
                <span className="text-xs font-normal text-muted-foreground">
                  {h.submitted_at ? new Date(h.submitted_at).toLocaleString() : ''}
                </span>
              </CardTitle>
            </CardHeader>
            <CardContent className="px-4 pb-4 space-y-3">
              {h.dogs_on_site_snapshot?.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-muted-foreground mb-1">Dogs on site ({h.dogs_on_site_snapshot.length})</p>
                  <div className="flex flex-wrap gap-1">
                    {h.dogs_on_site_snapshot.map((d, i) => (
                      <Badge key={i} variant="outline" className="text-xs">{d.name}{d.room ? ` · ${d.room}` : ''}</Badge>
                    ))}
                  </div>
                </div>
              )}
              {h.active_medications?.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-amber-700 mb-1">💊 Medications</p>
                  {h.active_medications.map((m, i) => (
                    <p key={i} className="text-xs">{m.dog}: {m.medication} {m.dosage} — {m.frequency}</p>
                  ))}
                </div>
              )}
              {h.active_alerts?.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-red-700 mb-1">🚨 Active Alerts</p>
                  {h.active_alerts.map((a, i) => (
                    <p key={i} className="text-xs">{a.dog}: {a.alert}</p>
                  ))}
                </div>
              )}
              {h.open_incidents?.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-orange-700 mb-1">⚠️ Open Incidents</p>
                  {h.open_incidents.map((inc, i) => (
                    <p key={i} className="text-xs">{inc.title} ({inc.severity})</p>
                  ))}
                </div>
              )}
              {h.outstanding_care?.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-blue-700 mb-1">🍽️ Lunch Feeding Reminders</p>
                  {h.outstanding_care.map((c, i) => (
                    <p key={i} className="text-xs">{c.dog}: {c.note}</p>
                  ))}
                </div>
              )}
              {h.follow_up_items?.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-muted-foreground mb-1">Follow-up items</p>
                  {h.follow_up_items.map((f, i) => (
                    <p key={i} className="text-xs">• {f}</p>
                  ))}
                </div>
              )}
              {h.staff_notes && (
                <div className="bg-muted/50 rounded p-2">
                  <p className="text-xs font-medium text-muted-foreground mb-1">Notes from {h.staff_name}</p>
                  <p className="text-sm">{h.staff_notes}</p>
                </div>
              )}
              {!h.acknowledged_at && h.staff_id !== user?.id && (
                <Button size="sm" className="w-full" onClick={() => handleAcknowledge(h.id)}>
                  <CheckCircleIcon size={14} className="mr-1" /> Acknowledge Handoff
                </Button>
              )}
            </CardContent>
          </Card>
        ))}
      </main>

      {showCreate && (
        <CreateHandoffModal
          user={user}
          onClose={() => setShowCreate(false)}
          onSuccess={() => { setShowCreate(false); fetchHandoffs(); }}
        />
      )}
    </div>
  );
};

const CreateHandoffModal = ({ user, onClose, onSuccess }) => {
  const [notes, setNotes] = useState('');
  const [followUps, setFollowUps] = useState(['']);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      await api.post('/care/handoffs', {
        staff_notes: notes,
        follow_up_items: followUps.filter(f => f.trim()),
        shift_start: null,
      });
      toast.success('Handoff submitted — clocked out');
      onSuccess();
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed'); }
    finally { setSubmitting(false); }
  };

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-end md:items-center justify-center p-4">
      <div className="bg-white rounded-t-2xl md:rounded-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="p-6 space-y-4">
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-lg font-bold">End of Shift Handoff</h2>
              <p className="text-sm text-muted-foreground">This will clock you out and notify incoming staff</p>
            </div>
            <button onClick={onClose} className="text-muted-foreground text-xl">×</button>
          </div>
          <div className="bg-blue-50 border border-blue-200 rounded p-3 text-xs text-blue-800">
            ℹ️ Dogs on site, medications, alerts, and incidents will be auto-populated from current data.
          </div>
          <div>
            <label className="text-sm font-medium">Shift Notes</label>
            <Textarea value={notes} onChange={e => setNotes(e.target.value)}
              className="mt-1" rows={4}
              placeholder="How did the shift go? Any observations, behavior notes, or things the next person should know..." />
          </div>
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm font-medium">Follow-up Items</label>
              <button type="button" className="text-xs text-primary hover:underline"
                onClick={() => setFollowUps(f => [...f, ''])}>
                + Add item
              </button>
            </div>
            {followUps.map((item, i) => (
              <div key={i} className="flex gap-2 mb-2">
                <Input value={item} onChange={e => {
                  const f = [...followUps]; f[i] = e.target.value; setFollowUps(f);
                }} placeholder="e.g. Buddy needs lunch at 1pm" className="flex-1" />
                {followUps.length > 1 && (
                  <button onClick={() => setFollowUps(f => f.filter((_, j) => j !== i))}>
                    <XIcon size={14} className="text-muted-foreground" />
                  </button>
                )}
              </div>
            ))}
          </div>
          <div className="flex gap-3 pt-2">
            <Button variant="outline" className="flex-1" onClick={onClose}>Cancel</Button>
            <Button className="flex-1 bg-green-600 hover:bg-green-700" onClick={handleSubmit} disabled={submitting}>
              {submitting ? 'Submitting...' : 'Submit & Clock Out'}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ShiftHandoffPage;
