import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import useAuthStore from '../store/authStore';
import api from '../utils/api';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Textarea } from '../components/ui/textarea';
import { Label } from '../components/ui/label';
import {
  ArrowLeftIcon, CheckCircleIcon, AlertCircleIcon,
  ClipboardListIcon, DogIcon, PlusIcon,
} from 'lucide-react';
import { toast } from 'sonner';

const DailyOpsPage = () => {
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const [onSite, setOnSite] = useState([]);
  const [pendingHandoff, setPendingHandoff] = useState(null);
  const [showHandoffForm, setShowHandoffForm] = useState(false);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    try {
      const [onSiteRes, handoffRes] = await Promise.all([
        api.get('/stays/on-site'),
        api.get('/care/handoffs/pending'),
      ]);
      setOnSite(onSiteRes.data);
      setPendingHandoff(handoffRes.data);
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

      <main className="max-w-3xl mx-auto px-4 py-6 space-y-5">

        {/* Pending handoff to acknowledge */}
        {pendingHandoff && (
          <Card className="border-amber-200 bg-amber-50">
            <CardHeader className="pb-2 pt-4">
              <CardTitle className="text-sm flex items-center gap-2 text-amber-800">
                <AlertCircleIcon size={16} />
                Unacknowledged Shift Handoff
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="text-xs text-amber-700">
                Submitted {new Date(pendingHandoff.submitted_at).toLocaleString()}
              </p>
              {pendingHandoff.staff_notes && (
                <div className="bg-white rounded p-3 text-sm">{pendingHandoff.staff_notes}</div>
              )}
              {pendingHandoff.dogs_on_site_snapshot?.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-amber-700 mb-1">Dogs on site at handoff:</p>
                  <div className="flex flex-wrap gap-1">
                    {pendingHandoff.dogs_on_site_snapshot.map(d => (
                      <Badge key={d.dog_id} variant="outline" className="text-xs">{d.dog_name}</Badge>
                    ))}
                  </div>
                </div>
              )}
              {pendingHandoff.follow_up_items?.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-amber-700 mb-1">Follow-up items:</p>
                  <ul className="text-xs text-amber-800 space-y-1">
                    {pendingHandoff.follow_up_items.map((item, i) => (
                      <li key={i}>· {item}</li>
                    ))}
                  </ul>
                </div>
              )}
              <Button size="sm" onClick={acknowledgeHandoff}
                className="bg-amber-600 hover:bg-amber-700 text-white w-full">
                <CheckCircleIcon size={14} className="mr-1" /> Acknowledge Handoff
              </Button>
            </CardContent>
          </Card>
        )}

        {/* On-site dogs */}
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
                        <p className="text-sm font-medium">{stay.dog_name}</p>
                        {stay.active_alerts?.length > 0 && (
                          <p className="text-xs text-amber-600">{stay.active_alerts[0]?.alert_message}</p>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-1">
                      {stay.is_first_stay && <Badge variant="secondary" className="text-xs">1st stay</Badge>}
                      {stay.alert_count > 0 && (
                        <Badge variant="outline" className="text-xs">
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
        staff_notes: form.staff_notes || undefined,
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
      <div className="bg-white rounded-t-2xl md:rounded-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="p-6 space-y-5">
          <div className="flex justify-between items-center">
            <h2 className="text-lg font-bold">End Shift — Handoff</h2>
            <button onClick={onClose} className="text-muted-foreground text-xl">×</button>
          </div>

          {/* Auto-populated summary */}
          <div className="bg-muted/30 rounded-lg p-3 space-y-2">
            <p className="text-xs font-medium text-muted-foreground">Auto-populated from live data:</p>
            <p className="text-sm">
              <span className="font-medium">{onSite.length}</span> dogs on site
            </p>
            {onSite.some(s => s.alert_count > 0) && (
              <p className="text-sm text-amber-700">
                <span className="font-medium">{onSite.filter(s => s.alert_count > 0).length}</span> dogs with active alerts
              </p>
            )}
          </div>

          <div>
            <Label>Shift Notes</Label>
            <Textarea
              placeholder="Any notes for the incoming shift..."
              value={form.staff_notes}
              onChange={e => setForm(f => ({...f, staff_notes: e.target.value}))}
              className="mt-1" rows={4}
            />
          </div>

          <div>
            <Label>Follow-up Items (one per line)</Label>
            <Textarea
              placeholder="Check Buddy's appetite in the morning&#10;Owner picking up Max at 8am"
              value={form.follow_up_items_text}
              onChange={e => setForm(f => ({...f, follow_up_items_text: e.target.value}))}
              className="mt-1" rows={3}
            />
          </div>

          <div className="flex gap-3 pt-2">
            <Button variant="outline" className="flex-1" onClick={onClose}>Cancel</Button>
            <Button className="flex-1" onClick={handleSubmit} disabled={submitting}>
              {submitting ? 'Submitting...' : 'Submit Handoff'}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DailyOpsPage;
