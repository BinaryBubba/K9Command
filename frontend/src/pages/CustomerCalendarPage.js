import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { Calendar as CalendarComponent } from '../components/ui/calendar';
import { Button } from '../components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/card';
import { ArrowLeftIcon, CalendarIcon, PlusIcon } from 'lucide-react';
import { dataClient, dataMode } from '../data/client';

function toISODate(d) {
  const dt = new Date(d);
  const y = dt.getFullYear();
  const m = String(dt.getMonth() + 1).padStart(2, '0');
  const day = String(dt.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

const CustomerCalendarPage = () => {
  const navigate = useNavigate();
  const [selected, setSelected] = useState(new Date());
  const [view, setView] = useState('day'); // 'day' | 'week'
  const [loading, setLoading] = useState(true);
  const [bookings, setBookings] = useState([]);

  const selectedISO = useMemo(() => toISODate(selected), [selected]);

  useEffect(() => {
    let mounted = true;
    const load = async () => {
      setLoading(true);
      try {
        const list = await dataClient.listBookings();
        if (!mounted) return;
        setBookings(list || []);
      } catch (e) {
        toast.error('Failed to load bookings');
      } finally {
        if (mounted) setLoading(false);
      }
    };
    load();
    return () => {
      mounted = false;
    };
  }, []);

  const dayBookings = useMemo(() => {
    const all = bookings || [];
    return all.filter((b) => selectedISO >= b.startDate && selectedISO <= b.endDate);
  }, [bookings, selectedISO]);

  const weekDates = useMemo(() => {
    const base = new Date(selected);
    const day = base.getDay(); // 0 Sun - 6 Sat
    const diff = (day + 6) % 7; // make Monday start
    base.setDate(base.getDate() - diff);
    return Array.from({ length: 7 }).map((_, i) => {
      const d = new Date(base);
      d.setDate(base.getDate() + i);
      return d;
    });
  }, [selected]);

  const weekBookingsMap = useMemo(() => {
    const map = {};
    for (const d of weekDates) {
      const iso = toISODate(d);
      map[iso] = (bookings || []).filter((b) => iso >= b.startDate && iso <= b.endDate);
    }
    return map;
  }, [bookings, weekDates]);

  return (
    <div className="min-h-screen bg-[#F9F7F2]">
      <header className="bg-white border-b border-border/50 sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Button variant="ghost" onClick={() => navigate('/customer/dashboard')}>
              <ArrowLeftIcon className="mr-2" size={18} />
              Back
            </Button>
            <div className="flex items-center gap-2">
              <CalendarIcon size={20} />
              <h1 className="text-xl font-serif font-bold text-primary">Calendar</h1>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <div className="text-xs text-muted-foreground hidden sm:block">
              Data mode: <span className="font-medium">{dataMode}</span>
            </div>
            <Button onClick={() => navigate('/customer/bookings/new')}>
              <PlusIcon className="mr-2" size={18} />
              New Booking
            </Button>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
            <CardHeader>
              <CardTitle className="font-serif">Pick a date</CardTitle>
            </CardHeader>
            <CardContent>
              <CalendarComponent mode="single" selected={selected} onSelect={(d) => d && setSelected(d)} />
              <div className="mt-4 flex gap-2">
                <Button variant={view === 'day' ? 'default' : 'outline'} onClick={() => setView('day')}>
                  Day
                </Button>
                <Button variant={view === 'week' ? 'default' : 'outline'} onClick={() => setView('week')}>
                  Week
                </Button>
              </div>
            </CardContent>
          </Card>

          <div className="lg:col-span-2 space-y-6">
            <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
              <CardHeader>
                <CardTitle className="font-serif">
                  {view === 'day' ? `Bookings for ${selectedISO}` : 'Bookings this week'}
                </CardTitle>
              </CardHeader>
              <CardContent>
                {loading ? (
                  <div className="text-muted-foreground">Loading…</div>
                ) : view === 'day' ? (
                  dayBookings.length ? (
                    <div className="space-y-3">
                      {dayBookings.map((b) => (
                        <div key={b.id} className="p-4 rounded-xl border border-border/50 bg-muted/30">
                          <div className="flex items-center justify-between">
                            <div className="font-medium">
                              {b.dogs?.length ? b.dogs.join(', ') : 'Booking'}
                            </div>
                            <div className="text-xs px-2 py-1 rounded-full bg-white border border-border/50">
                              {b.status}
                            </div>
                          </div>
                          <div className="text-sm text-muted-foreground mt-1">
                            {b.startDate} → {b.endDate}
                          </div>
                          {b.notes ? <div className="text-sm mt-2">{b.notes}</div> : null}
                          {typeof b.total === 'number' ? (
                            <div className="text-sm mt-2 font-medium">Estimated: ${b.total.toFixed(2)}</div>
                          ) : null}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-muted-foreground">
                      No bookings for this day. Want to create one?
                      <div className="mt-3">
                        <Button variant="outline" onClick={() => navigate('/customer/bookings/new')}>
                          Create booking
                        </Button>
                      </div>
                    </div>
                  )
                ) : (
                  <div className="space-y-3">
                    {weekDates.map((d) => {
                      const iso = toISODate(d);
                      const list = weekBookingsMap[iso] || [];
                      return (
                        <div key={iso} className="p-4 rounded-xl border border-border/50">
                          <div className="flex items-center justify-between">
                            <div className="font-medium">{iso}</div>
                            <div className="text-sm text-muted-foreground">{list.length} booking(s)</div>
                          </div>
                          {list.length ? (
                            <div className="mt-2 space-y-2">
                              {list.slice(0, 4).map((b) => (
                                <div key={b.id} className="text-sm flex items-center justify-between">
                                  <span>{b.dogs?.length ? b.dogs.join(', ') : 'Booking'}</span>
                                  <span className="text-xs px-2 py-1 rounded-full bg-muted">
                                    {b.status}
                                  </span>
                                </div>
                              ))}
                              {list.length > 4 ? (
                                <div className="text-xs text-muted-foreground">+{list.length - 4} more…</div>
                              ) : null}
                            </div>
                          ) : (
                            <div className="text-sm text-muted-foreground mt-2">No bookings</div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </main>
    </div>
  );
};

export default CustomerCalendarPage;
