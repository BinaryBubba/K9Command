import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import useAuthStore from '../store/authStore';
import api from '../utils/api';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { ArrowLeftIcon, AlertCircleIcon, DogIcon, RefreshCwIcon } from 'lucide-react';
import { toast } from 'sonner';

const KennelManagementPage = () => {
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const [onSite, setOnSite] = useState([]);
  const [rooms, setRooms] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    try {
      const [onSiteRes, roomsRes] = await Promise.all([
        api.get('/stays/on-site'),
        api.get('/bookings/rooms/list'),
      ]);
      setOnSite(onSiteRes.data);
      setRooms(roomsRes.data);
    } catch {
      toast.error('Failed to load occupancy data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!user) { navigate('/auth'); return; }
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [user, navigate, fetchData]);

  // Group stays by room
  const staysByRoom = {};
  onSite.forEach(stay => {
    const roomId = stay.room_id || 'unassigned';
    if (!staysByRoom[roomId]) staysByRoom[roomId] = [];
    staysByRoom[roomId].push(stay);
  });

  const unassigned = staysByRoom['unassigned'] || [];
  const totalCapacity = rooms.reduce((sum, r) => sum + r.max_dogs, 0);
  const occupancyPct = totalCapacity > 0 ? Math.round((onSite.length / totalCapacity) * 100) : 0;

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-primary"></div>
    </div>
  );

  return (
    <div className="min-h-screen bg-[#F9F7F2]">
      <header className="bg-white border-b shadow-sm sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="sm" onClick={() => navigate(-1)}>
              <ArrowLeftIcon size={18} />
            </Button>
            <div>
              <h1 className="text-lg font-serif font-bold text-primary">Occupancy Board</h1>
              <p className="text-xs text-muted-foreground">
                {onSite.length} dogs on site · {occupancyPct}% capacity
              </p>
            </div>
          </div>
          <Button variant="ghost" size="sm" onClick={fetchData}>
            <RefreshCwIcon size={16} />
          </Button>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-6 space-y-4">

        {/* Unassigned dogs warning */}
        {unassigned.length > 0 && (
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 flex items-center gap-2">
            <AlertCircleIcon size={16} className="text-amber-600" />
            <span className="text-sm text-amber-800">
              {unassigned.length} dog{unassigned.length !== 1 ? 's' : ''} on site without a room assignment
            </span>
          </div>
        )}

        {/* Room grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {rooms.map(room => {
            const occupants = staysByRoom[room.id] || [];
            const isFull = occupants.length >= room.max_dogs;
            const isEmpty = occupants.length === 0;
            const hasWarning = occupants.some(s => s.has_warning);

            return (
              <Card key={room.id} className={`${room.is_out_of_service ? 'opacity-50' : ''}`}>
                <CardHeader className="pb-2 pt-4">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-base">{room.name}</CardTitle>
                    <div className="flex items-center gap-2">
                      {hasWarning && <AlertCircleIcon size={16} className="text-red-500" />}
                      <span className={`text-sm font-bold ${isFull ? 'text-red-600' : isEmpty ? 'text-green-600' : 'text-blue-600'}`}>
                        {occupants.length}/{room.max_dogs}
                      </span>
                      <div className={`w-3 h-3 rounded-full ${
                        room.is_out_of_service ? 'bg-gray-400' :
                        isFull ? 'bg-red-500' :
                        isEmpty ? 'bg-green-500' : 'bg-blue-500'
                      }`} />
                    </div>
                  </div>
                  {room.is_out_of_service && (
                    <Badge variant="outline" className="text-xs w-fit">Out of Service</Badge>
                  )}
                </CardHeader>
                <CardContent>
                  {occupants.length === 0 ? (
                    <p className="text-sm text-muted-foreground italic">Available</p>
                  ) : (
                    <div className="space-y-2">
                      {occupants.map(stay => (
                        <DogCard key={stay.id} stay={stay} />
                      ))}
                    </div>
                  )}
                  {/* Empty slots */}
                  {occupants.length < room.max_dogs && occupants.length > 0 && !room.is_out_of_service && (
                    <div className="mt-2 flex gap-1">
                      {Array.from({length: room.max_dogs - occupants.length}).map((_, i) => (
                        <div key={i} className="flex-1 h-1 bg-green-200 rounded-full" />
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>

        {/* Unassigned */}
        {unassigned.length > 0 && (
          <Card className="border-amber-200">
            <CardHeader className="pb-2 pt-4">
              <CardTitle className="text-base text-amber-700">Unassigned</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {unassigned.map(stay => <DogCard key={stay.id} stay={stay} />)}
            </CardContent>
          </Card>
        )}

      </main>
    </div>
  );
};

const DogCard = ({ stay }) => {
  const navigate = useNavigate();
  return (
  <div
    className={`flex items-center justify-between p-2 rounded-lg border cursor-pointer hover:shadow-sm transition-shadow ${
      stay.has_warning ? 'bg-red-50 border-red-200' : 'bg-muted/50 border-border'
    }`}
    onClick={() => navigate(`/admin/dogs/${stay.dog_id}`)}
  >
    <div className="flex items-center gap-2">
      <DogIcon size={14} className={stay.has_warning ? 'text-red-600' : 'text-muted-foreground'} />
      <div>
        <p className="text-sm font-medium">{stay.dog_name}</p>
        {stay.active_alerts?.length > 0 && (
          <p className="text-xs text-amber-600">
            {stay.active_alerts[0]?.alert_message}
          </p>
        )}
      </div>
    </div>
    <div className="flex items-center gap-1">
      {stay.alert_count > 0 && (
        <Badge variant="outline" className="text-xs px-1">
          <AlertCircleIcon size={10} className="mr-1" />{stay.alert_count}
        </Badge>
      )}
      {stay.is_first_stay && (
        <Badge variant="secondary" className="text-xs px-1">1st</Badge>
      )}
    </div>
  </div>
  );
};

export default KennelManagementPage;
