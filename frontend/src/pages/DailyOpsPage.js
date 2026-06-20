import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import useAuthStore from '../store/authStore';
import api from '../utils/api';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Textarea } from '../components/ui/textarea';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import {
  ArrowLeftIcon, CheckCircleIcon, AlertCircleIcon,
  ClipboardListIcon, DogIcon, UtensilsIcon, PillIcon,
} from 'lucide-react';
import { toast } from 'sonner';

const DailyOpsPage = () => {
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const [onSite, setOnSite] = useState([]);
  const [pendingHandoff, setPendingHandoff] = useState(null);
  const [showHandoffForm, setShowHandoffForm] = useState(false);
  const [loading, setLoading] = useState(true);
  const [feedingPlans, setFeedingPlans] = useState([]);
  const [medications, setMedications] = useState([]);
  const [playtimeHistory, setPlaytimeHistory] = useState([]);
  const [tab, setTab] = useState('current');

  const fetchData = useCallback(async () => {
    try {
      const [onSiteRes, handoffRes, feedRes, medRes, playtimeRes] = await Promise.all([
        api.get('/stays/on-site'),
        api.get('/care/handoffs', { params: { limit: 1 } }).catch(() => ({ data: [] })),
        api.get('/care/feeding-plans').catch(() => ({ data: [] })),
        api.get('/care/medications').catch(() => ({ data: [] })),
        api.get('/care/handoffs', { params: { limit: 20 } }).catch(() => ({ data: [] })),
      ]);
      setOnSite(onSiteRes.data || []);
      const handoffs = handoffRes.data || [];
      setPendingHandoff(handoffs.find(h => !h.acknowledged_at) || null);
      setFeedingPlans(feedRes.data || []);
      setMedications(medRes.data || []);
      setPlaytimeHistory(playtimeRes.data || []);
    } catch {
      toast.error('Failed to load ops data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!user) { navigate('/auth'); return; }
    fetchData();
  }, [user, navigate, fetchData]);

  const acknowledgeHandoff = async () => {
    if (!pendingHandoff) return;
    try {
      await api.post(`/care/handoffs/${pendingHandoff.id}/acknowledge`);
      toast.success('Handoff acknowledged');
      fetchData();
    } catch {
      toast.error('Failed to acknowledge handoff');
    }
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
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="sm" onClick={() => navigate(-1)}>
              <ArrowLeftIcon size={18} />
            </Button>
            <h1 className="text-lg font-serif font-bold text-primary">Daily Operations</h1>
          </div>
          <Button size="sm" onClick={() => setShowHandoffForm(true)}>
            <ClipboardListIcon size={16} className="mr-1" /> End Shift
          </Button>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 py-4">
        <Tabs value={tab} onValueChange={setTab}>
          <TabsList className="w-full mb-4">
            <TabsTrigger value="current" className="flex-1">On Site</TabsTrigger>
            <TabsTrigger value="feeding" className="flex-1">Feeding & Meds</TabsTrigger>
            <TabsTrigger value="history" className="flex-1">Shift History</TabsTrigger>
          </TabsList>

          {/* Current / On-site tab */}
          <TabsContent value="current" className="space-y-4">
            {pendingHandoff && (
              <Card className="border-amber-200 bg-amber-50">
                <CardHeader className="pb-2 pt-4">
                  <CardTitle className="text-sm flex items-center gap-2 text-amber-800">
                    <AlertCircleIcon size={16} /> Unacknowledged Shift Handoff
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <p className="text-xs text-amber-700">
                    From {pendingHandoff.staff_name} · {new Date(pendingHandoff.submitted_at).toLocaleString()}
                  </p>
                  {pendingHandoff.staff_notes && (
                    <div className="bg-white rounded p-3 text-sm">{pendingHandoff.staff_notes}</div>
                  )}
                  {pendingHandoff.follow_up_items?.length > 0 && (
                    <div>
                      <p className="text-xs font-medium text-amber-700 mb-1">Follow-up items:</p>
                      {pendingHandoff.follow_up_items.map((item, i) => (
                        <p key={i} className="text-xs text-amber-800">· {item}</p>
                      ))}
                    </div>
                  )}
                  {pendingHandoff.active_alerts?.length > 0 && (
                    <div>
                      <p className="text-xs font-medium text-red-700 mb-1">🚨 Alerts:</p>
                      {pendingHandoff.active_alerts.map((a, i) => (
                        <p key={i} className="text-xs">{a.dog}: {a.alert}</p>
                      ))}
                    </div>
                  )}
                  {pendingHandoff.outstanding_care?.length > 0 && (
                    <div>
                      <p className="text-xs font-medium text-blue-700 mb-1">🍽️ Lunch reminders:</p>
                      {pendingHandoff.outstanding_care.map((c, i) => (
                        <p key={i} className="text-xs">{c.dog}: {c.note}</p>
                      ))}
                    </div>
                  )}
                  <Button size="sm" onClick={acknowledgeHandoff}
                    className="bg-amber-600 hover:bg-amber-700 text-white w-full">
                    <CheckCircleIcon size={14} className="mr-1" /> Acknowledge Handoff
                  </Button>
                </CardContent>
              </Card>
            )}

            <Card>
              <CardHeader className="pb-2 pt-4">
                <CardTitle className="text-sm flex items-center gap-2">
                  <DogIcon size={14} className="text-blue-500" />
                  On Site Now ({onSite.length})
                </CardTitle>
              </CardHeader>
              <CardContent>
                {onSite.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No dogs currently on site</p>
                ) : (
                  <div className="space-y-2">
                    {onSite.map(stay => (
                      <div key={stay.id} className={`flex items-center justify-between p-3 rounded-lg border ${
                        stay.has_warning ? 'bg-red-50 border-red-200' : 'bg-muted/30 border-border'
                      }`}>
                        <div className="flex items-center gap-2">
                          <DogIcon size={14} className={stay.has_warning ? 'text-red-500' : 'text-muted-foreground'} />
                          <div>
                            <p className="text-sm font-medium">{stay.dog_name}
                              {stay.room_name && <span className="ml-2 text-xs font-normal text-muted-foreground">· {stay.room_name}</span>}
                            </p>
                            {stay.active_alerts?.length > 0 && (
                              <p className="text-xs text-amber-600">{stay.active_alerts[0]?.alert_message}</p>
                            )}
                          </div>
                        </div>
                        <div className="flex items-center gap-1">
                          {stay.is_first_stay && <Badge variant="secondary" className="text-xs">1st stay</Badge>}
                          {stay.alert_count > 0 && (
                            <Badge variant="outline" className="text-xs text-amber-600">
                              <AlertCircleIcon size={10} className="mr-0.5" />{stay.alert_count}
                            </Badge>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Feeding & Medications tab */}
          <TabsContent value="feeding" className="space-y-4">
            <Card>
              <CardHeader className="pb-2 pt-4">
                <CardTitle className="text-sm flex items-center gap-2">
                  <UtensilsIcon size={14} className="text-green-600" /> Feeding Plans
                </CardTitle>
              </CardHeader>
              <CardContent>
                {onSite.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No dogs on site</p>
                ) : onSite.map(stay => {
                  const plan = feedingPlans.find(f => f.dog_id === stay.dog_id);
                  return (
                    <div key={stay.id} className="flex items-start justify-between py-2 border-b last:border-0">
                      <div>
                        <p className="text-sm font-medium">{stay.dog_name}
                          {stay.room_name && <span className="ml-1 text-xs text-muted-foreground">· {stay.room_name}</span>}
                        </p>
                        {plan ? (
                          <p className="text-xs text-muted-foreground mt-0.5">
                            {plan.food_type} · {plan.amount_per_meal} · {plan.meals_per_day}x/day
                            {plan.special_instructions && ` · ${plan.special_instructions}`}
                          </p>
                        ) : (
                          <p className="text-xs text-amber-600">No feeding plan on file</p>
                        )}
                      </div>
                    </div>
                  );
                })}
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2 pt-4">
                <CardTitle className="text-sm flex items-center gap-2">
                  <PillIcon size={14} className="text-purple-600" /> Active Medications
                </CardTitle>
              </CardHeader>
              <CardContent>
                {medications.filter(m => onSite.some(s => s.dog_id === m.dog_id)).length === 0 ? (
                  <p className="text-sm text-muted-foreground">No active medications for dogs on site</p>
                ) : medications.filter(m => onSite.some(s => s.dog_id === m.dog_id)).map(med => {
                  const stay = onSite.find(s => s.dog_id === med.dog_id);
                  return (
                    <div key={med.id} className="flex items-start justify-between py-2 border-b last:border-0">
                      <div>
                        <p className="text-sm font-medium">{stay?.dog_name || med.dog_name}
                          {stay?.room_name && <span className="ml-1 text-xs text-muted-foreground">· {stay.room_name}</span>}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {med.name} · {med.dosage} · {med.frequency}
                          {med.instructions && ` · ${med.instructions}`}
                        </p>
                      </div>
                      <Badge className="text-xs bg-purple-100 text-purple-700 shrink-0">Rx</Badge>
                    </div>
                  );
                })}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Shift History tab */}
          <TabsContent value="history" className="space-y-3">
            <p className="text-xs text-muted-foreground">Recent shift handoffs and notes from all staff</p>
            {playtimeHistory.length === 0 ? (
              <Card><CardContent className="py-8 text-center text-muted-foreground text-sm">No shift history yet</CardContent></Card>
            ) : playtimeHistory.map(h => (
              <Card key={h.id}>
                <CardContent className="py-3 px-4">
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-sm font-medium">{h.staff_name}</p>
                    <div className="flex items-center gap-2">
                      {h.acknowledged_at ? (
                        <Badge className="text-xs bg-green-100 text-green-700">✓ Acknowledged</Badge>
                      ) : (
                        <Badge className="text-xs bg-amber-100 text-amber-700">Pending</Badge>
                      )}
                      <span className="text-xs text-muted-foreground">
                        {h.submitted_at ? new Date(h.submitted_at).toLocaleString([], {month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'}) : ''}
                      </span>
                    </div>
                  </div>
                  {h.staff_notes && <p className="text-sm text-muted-foreground">{h.staff_notes}</p>}
                  {h.dogs_on_site_snapshot?.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-2">
                      {h.dogs_on_site_snapshot.map((d, i) => (
                        <Badge key={i} variant="outline" className="text-xs">{d.name}</Badge>
                      ))}
                    </div>
                  )}
                  {h.follow_up_items?.filter(Boolean).length > 0 && (
                    <div className="mt-2">
                      {h.follow_up_items.filter(Boolean).map((f, i) => (
                        <p key={i} className="text-xs text-amber-700">· {f}</p>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </TabsContent>
        </Tabs>
      </main>

      {showHandoffForm && (
        <HandoffModal
          onSite={onSite}
          onClose={() => setShowHandoffForm(false)}
          onSuccess={() => { setShowHandoffForm(false); fetchData(); toast.success('Shift handoff submitted'); }}
        />
      )}
    </div>
  );
};

const HandoffModal = ({ onSite, onClose, onSuccess }) => {
  const [form, setForm] = useState({ staff_notes: '', follow_up_items_text: '' });
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      const follow_up_items = form.follow_up_items_text
        .split('\n').map(s => s.trim()).filter(Boolean);
      await api.post('/care/handoffs', {
        staff_notes: form.staff_notes,
        follow_up_items,
      });
      onSuccess();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to submit handoff');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-end md:items-center justify-center p-4">
      <div className="bg-white rounded-t-2xl md:rounded-2xl w-full max-w-lg max-h-[85vh] overflow-y-auto">
        <div className="p-6 space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-lg font-bold">End of Shift Handoff</h2>
            <button onClick={onClose} className="text-muted-foreground text-xl">×</button>
          </div>
          <div className="bg-blue-50 border border-blue-200 rounded p-3 text-xs text-blue-800">
            Dogs on site, medications, alerts and incidents will be auto-populated.
          </div>
          <div className="bg-muted/30 rounded p-3">
            <p className="text-xs font-medium mb-2">Currently on site ({onSite.length} dogs)</p>
            <div className="flex flex-wrap gap-1">
              {onSite.map(s => (
                <Badge key={s.id} variant="outline" className="text-xs">
                  {s.dog_name}{s.room_name ? ` · ${s.room_name}` : ''}
                </Badge>
              ))}
            </div>
          </div>
          <div>
            <label className="text-sm font-medium">Shift Notes</label>
            <Textarea value={form.staff_notes}
              onChange={e => setForm(f => ({...f, staff_notes: e.target.value}))}
              className="mt-1" rows={4}
              placeholder="How did the shift go? Any observations or things to pass on..." />
          </div>
          <div>
            <label className="text-sm font-medium">Follow-up Items</label>
            <p className="text-xs text-muted-foreground">One item per line</p>
            <Textarea value={form.follow_up_items_text}
              onChange={e => setForm(f => ({...f, follow_up_items_text: e.target.value}))}
              className="mt-1" rows={3}
              placeholder="e.g. Buddy needs lunch at 1pm&#10;Check Rex's paw at 3pm" />
          </div>
          <div className="flex gap-3">
            <Button variant="outline" className="flex-1" onClick={onClose}>Cancel</Button>
            <Button className="flex-1 bg-green-600 hover:bg-green-700 text-white"
              onClick={handleSubmit} disabled={submitting}>
              {submitting ? 'Submitting...' : 'Submit & Clock Out'}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DailyOpsPage;
