import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import useAuthStore from '../store/authStore';
import api from '../utils/api';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import {
  ArrowLeftIcon, DogIcon, AlertCircleIcon,
  ClipboardListIcon, HomeIcon, ActivityIcon,
} from 'lucide-react';
import { toast } from 'sonner';

const StaffHubPage = () => {
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    try {
      const [dashRes, onSiteRes] = await Promise.all([
        api.get('/dashboard'),
        api.get('/stays/on-site'),
      ]);
      setData({ dashboard: dashRes.data, onSite: onSiteRes.data });
    } catch {
      toast.error('Failed to load hub data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!user) { navigate('/auth'); return; }
    fetchData();
  }, [user, navigate, fetchData]);

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-primary"></div>
    </div>
  );

  const dash = data?.dashboard;
  const onSite = data?.onSite || [];

  return (
    <div className="min-h-screen bg-[#F9F7F2]">
      <header className="bg-white border-b shadow-sm sticky top-0 z-10">
        <div className="max-w-3xl mx-auto px-4 py-3 flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={() => navigate(-1)}>
            <ArrowLeftIcon size={18} />
          </Button>
          <h1 className="text-lg font-serif font-bold text-primary">Staff Hub</h1>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 py-6 space-y-5">

        {/* Quick nav */}
        <div className="grid grid-cols-2 gap-3">
          <Button variant="outline" className="h-14 flex gap-2 justify-start px-4"
            onClick={() => navigate('/staff/check-in-out')}>
            <ActivityIcon size={18} className="text-green-600" />
            <div className="text-left">
              <p className="text-sm font-medium">Check In / Out</p>
              <p className="text-xs text-muted-foreground">{dash?.arriving_today_count ?? 0} arriving today</p>
            </div>
          </Button>
          <Button variant="outline" className="h-14 flex gap-2 justify-start px-4"
            onClick={() => navigate('/admin/kennels')}>
            <HomeIcon size={18} className="text-blue-600" />
            <div className="text-left">
              <p className="text-sm font-medium">Occupancy Board</p>
              <p className="text-xs text-muted-foreground">{dash?.on_site_count ?? 0} on site</p>
            </div>
          </Button>
          <Button variant="outline" className="h-14 flex gap-2 justify-start px-4"
            onClick={() => navigate('/staff/daily-ops')}>
            <ClipboardListIcon size={18} className="text-purple-600" />
            <div className="text-left">
              <p className="text-sm font-medium">Daily Operations</p>
              <p className="text-xs text-muted-foreground">Handoffs & care</p>
            </div>
          </Button>
          <Button variant="outline" className="h-14 flex gap-2 justify-start px-4"
            onClick={() => navigate('/staff/bookings')}>
            <DogIcon size={18} className="text-orange-600" />
            <div className="text-left">
              <p className="text-sm font-medium">Bookings</p>
              <p className="text-xs text-muted-foreground">View schedule</p>
            </div>
          </Button>
        </div>

        {/* Active alerts */}
        {dash?.warning_alerts?.length > 0 && (
          <Card className="border-red-200">
            <CardHeader className="pb-2 pt-4">
              <CardTitle className="text-sm text-red-700 flex items-center gap-2">
                <AlertCircleIcon size={14} />
                Active Warnings
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {dash.warning_alerts.map(a => (
                <div key={a.id} className="bg-red-50 rounded p-2 text-xs text-red-800">
                  {a.alert_message}
                </div>
              ))}
            </CardContent>
          </Card>
        )}

        {/* On-site dogs compact */}
        <Card>
          <CardHeader className="pb-2 pt-4">
            <CardTitle className="text-sm flex items-center gap-2">
              <DogIcon size={14} className="text-blue-500" />
              On Site ({onSite.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            {onSite.length === 0 ? (
              <p className="text-sm text-muted-foreground">No dogs currently on site</p>
            ) : (
              <div className="grid grid-cols-2 gap-2">
                {onSite.map(stay => (
                  <div key={stay.id} className={`p-2 rounded-lg border text-sm ${
                    stay.has_warning ? 'bg-red-50 border-red-200' : 'bg-muted/30 border-border'
                  }`}>
                    <p className="font-medium truncate">{stay.dog_name}</p>
                    {stay.alert_count > 0 && (
                      <p className="text-xs text-amber-600 flex items-center gap-1 mt-0.5">
                        <AlertCircleIcon size={10} /> {stay.alert_count} alert{stay.alert_count !== 1 ? 's' : ''}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

      </main>
    </div>
  );
};

export default StaffHubPage;
