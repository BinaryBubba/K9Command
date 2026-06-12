import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import useAuthStore from '../store/authStore';
import api from '../utils/api';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { DogIcon, AlertCircleIcon, RefreshCwIcon, ArrowLeftRightIcon } from 'lucide-react';
import { toast } from 'sonner';

const KennelManagementPage = () => {
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const [rooms, setRooms] = useState([]);
  const [stays, setStays] = useState([]);
  const [loading, setLoading] = useState(true);
  const [transferStay, setTransferStay] = useState(null);

  const fetchData = useCallback(async () => {
    try {
      const [roomsRes, staysRes] = await Promise.all([
        api.get('/facility/rooms'),
        api.get('/stays/on-site'),
      ]);
      setRooms(roomsRes.data || []);
      setStays(staysRes.data || []);
    } catch {
      toast.error('Failed to load kennel status');
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

  // Group stays by room_id
  const staysByRoom = stays.reduce((acc, stay) => {
    const key = stay.room_id || 'unassigned';
    if (!acc[key]) acc[key] = [];
    acc[key].push(stay);
    return acc;
  }, {});

  const totalDogs = stays.length;
  const occupiedRooms = rooms.filter(r => staysByRoom[r.id]?.length > 0);
  const emptyRooms = rooms.filter(r => !staysByRoom[r.id]?.length);

  return (
    <div className="min-h-screen bg-[#F9F7F2]">
      <header className="bg-white border-b shadow-sm sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between">
          <div>
            <h1 className="text-lg font-serif font-bold text-primary">Kennels</h1>
            <p className="text-xs text-muted-foreground">
              {totalDogs} dog{totalDogs !== 1 ? 's' : ''} on site · {emptyRooms.length} space{emptyRooms.length !== 1 ? 's' : ''} available
            </p>
          </div>
          <Button variant="ghost" size="sm" onClick={fetchData}>
            <RefreshCwIcon size={16} />
          </Button>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-6 space-y-3">
        {/* Occupied rooms first */}
        {rooms.map(room => {
          const roomStays = staysByRoom[room.id] || [];
          return (
            <Card key={room.id} className={room.is_out_of_service ? 'opacity-50' : ''}>
              <CardHeader className="pb-1 pt-3 px-4">
                <CardTitle className="text-sm flex items-center justify-between">
                  <span className="flex items-center gap-2">
                    {room.name}
                    {room.room_type && room.room_type !== 'room' && (
                      <Badge variant="secondary" className="text-xs">{room.room_type.replace('crate_', 'Crate ')}</Badge>
                    )}
                    {room.is_out_of_service && (
                      <Badge variant="outline" className="text-xs text-red-500 border-red-200">OOS</Badge>
                    )}
                  </span>
                  <span className={`text-xs font-normal ${roomStays.length >= room.max_dogs ? 'text-red-500' : 'text-muted-foreground'}`}>
                    {roomStays.length}/{room.max_dogs}
                  </span>
                </CardTitle>
              </CardHeader>
              <CardContent className="px-4 pb-3">
                {roomStays.length === 0 ? (
                  <p className="text-xs text-muted-foreground italic">Empty</p>
                ) : (
                  <div className="space-y-1.5">
                    {roomStays.map(stay => (
                      <DogCard
                        key={stay.id}
                        stay={{...stay, room_name: room.name}}
                        onNavigate={() => navigate(`/admin/dogs/${stay.dog_id}`)}
                        onTransfer={() => setTransferStay({...stay, room_name: room.name})}
                      />
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          );
        })}

        {/* Unassigned stays */}
        {staysByRoom['unassigned']?.length > 0 && (
          <Card className="border-amber-200">
            <CardHeader className="pb-1 pt-3 px-4">
              <CardTitle className="text-sm text-amber-700">⚠️ No Room Assigned</CardTitle>
            </CardHeader>
            <CardContent className="px-4 pb-3 space-y-1.5">
              {staysByRoom['unassigned'].map(stay => (
                <DogCard key={stay.id} stay={stay}
                  onNavigate={() => navigate(`/admin/dogs/${stay.dog_id}`)}
                  onTransfer={() => setTransferStay(stay)} />
              ))}
            </CardContent>
          </Card>
        )}
      </main>

      {transferStay && (
        <TransferModal
          stay={transferStay}
          rooms={rooms}
          onClose={() => setTransferStay(null)}
          onSuccess={() => { setTransferStay(null); fetchData(); toast.success('Dog moved successfully'); }}
        />
      )}
    </div>
  );
};

const DogCard = ({ stay, onNavigate, onTransfer }) => (
  <div className={`flex items-center justify-between p-2 rounded-lg border ${
    stay.has_medical_alert || stay.medical_alert ? 'bg-red-50 border-red-200' : 'bg-muted/50 border-border'
  }`}>
    <div className="flex items-center gap-2 flex-1 cursor-pointer hover:opacity-80" onClick={onNavigate}>
      <DogIcon size={14} className="text-muted-foreground" />
      <div>
        <p className="text-sm font-medium">{stay.dog_name}</p>
        {stay.dog_breed && <p className="text-xs text-muted-foreground">{stay.dog_breed}</p>}
      </div>
    </div>
    <div className="flex items-center gap-1.5">
      {stay.is_first_stay && <Badge variant="secondary" className="text-xs px-1">1st</Badge>}
      <Button variant="ghost" size="sm" className="h-6 w-6 p-0 text-muted-foreground hover:text-primary"
        title="Move to different room" onClick={e => { e.stopPropagation(); onTransfer(); }}>
        <ArrowLeftRightIcon size={12} />
      </Button>
    </div>
  </div>
);

const TransferModal = ({ stay, rooms, onClose, onSuccess }) => {
  const [roomId, setRoomId] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const rooms_only = rooms.filter(r => !r.room_type || r.room_type === 'room');
  const crates = rooms.filter(r => r.room_type && r.room_type !== 'room');

  const handleTransfer = async () => {
    if (!roomId) { toast.error('Select a room'); return; }
    setSubmitting(true);
    try {
      await api.patch(`/stays/${stay.id}/room`, { room_id: roomId });
      onSuccess();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Transfer failed');
    } finally { setSubmitting(false); }
  };

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-end md:items-center justify-center p-4">
      <div className="bg-white rounded-t-2xl md:rounded-2xl w-full max-w-md">
        <div className="p-6 space-y-4">
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-lg font-bold">Move {stay.dog_name}</h2>
              <p className="text-sm text-muted-foreground">Currently in {stay.room_name || '—'}</p>
            </div>
            <button onClick={onClose} className="text-muted-foreground text-xl leading-none">×</button>
          </div>
          <div>
            <p className="text-xs font-medium text-muted-foreground mb-2">Rooms</p>
            <div className="grid grid-cols-4 gap-2">
              {rooms_only.map(r => (
                <button key={r.id} type="button" onClick={() => setRoomId(r.id)}
                  disabled={r.is_out_of_service || r.id === stay.room_id}
                  className={`p-2 rounded-lg border text-xs font-medium transition-colors ${
                    roomId === r.id ? 'bg-primary text-primary-foreground border-primary' :
                    r.is_out_of_service || r.id === stay.room_id ? 'bg-gray-100 text-gray-400 cursor-not-allowed' :
                    'border-border hover:bg-muted'
                  }`}>{r.name}</button>
              ))}
            </div>
            {crates.length > 0 && <>
              <p className="text-xs text-muted-foreground mt-3 mb-1">Crates</p>
              <div className="grid grid-cols-4 gap-2">
                {crates.map(r => (
                  <button key={r.id} type="button" onClick={() => setRoomId(r.id)}
                    disabled={r.is_out_of_service || r.id === stay.room_id}
                    className={`p-2 rounded-lg border text-xs font-medium transition-colors ${
                      roomId === r.id ? 'bg-primary text-primary-foreground border-primary' :
                      r.is_out_of_service || r.id === stay.room_id ? 'bg-gray-100 text-gray-400 cursor-not-allowed' :
                      'border-border hover:bg-muted'
                    }`}>{r.name}</button>
                ))}
              </div>
            </>}
          </div>
          <div className="flex gap-3 pt-2">
            <Button variant="outline" className="flex-1" onClick={onClose}>Cancel</Button>
            <Button className="flex-1" onClick={handleTransfer} disabled={submitting || !roomId}>
              {submitting ? 'Moving...' : 'Confirm Move'}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default KennelManagementPage;
