import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import useAuthStore from '../store/authStore';
import api from '../utils/api';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Textarea } from '../components/ui/textarea';
import { RefreshCwIcon, SparklesIcon, CheckIcon, AlertCircleIcon, ArrowRightIcon } from 'lucide-react';
import { toast } from 'sonner';

const GROUP_COLORS = [
  'bg-blue-50 border-blue-200 text-blue-800',
  'bg-green-50 border-green-200 text-green-800',
  'bg-purple-50 border-purple-200 text-purple-800',
  'bg-orange-50 border-orange-200 text-orange-800',
  'bg-pink-50 border-pink-200 text-pink-800',
  'bg-teal-50 border-teal-200 text-teal-800',
];

const GROUP_BADGE_COLORS = [
  'bg-blue-100 text-blue-700',
  'bg-green-100 text-green-700',
  'bg-purple-100 text-purple-700',
  'bg-orange-100 text-orange-700',
  'bg-pink-100 text-pink-700',
  'bg-teal-100 text-teal-700',
];

const PlaygroupsPage = () => {
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const [groups, setGroups] = useState([]);
  const [suggested, setSuggested] = useState(null);
  const [unassigned, setUnassigned] = useState([]);
  const [loading, setLoading] = useState(true);
  const [suggesting, setSuggesting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [mode, setMode] = useState('view'); // view | suggest | edit
  const [editGroups, setEditGroups] = useState([]);
  const [moveModal, setMoveModal] = useState(null);
  const [history, setHistory] = useState([]);

  const fetchGroups = useCallback(async () => {
    try {
      const [groupsRes, unassignedRes] = await Promise.all([
        api.get('/playgroups/today'),
        api.get('/playgroups/unassigned'),
      ]);
      setGroups(groupsRes.data);
      setUnassigned(unassignedRes.data);
    } catch { toast.error('Failed to load groups'); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => {
    if (!user) { navigate('/auth'); return; }
    fetchGroups();
  }, [user, navigate, fetchGroups]);

  const handleSuggest = async () => {
    setSuggesting(true);
    try {
      const res = await api.post('/playgroups/suggest', {});
      setSuggested(res.data);
      setEditGroups(res.data.groups.map((g, i) => ({
        ...g,
        group_number: g.group_number || i + 1,
        label: g.is_individual ? `Individual — ${g.dogs[0]?.dog_name}` : `Group ${g.group_number || i + 1}`,
      })));
      setMode('suggest');
    } catch { toast.error('Failed to generate suggestions'); }
    finally { setSuggesting(false); }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await api.post('/playgroups/assign', { groups: editGroups });
      toast.success("Groups saved — staff will see updates immediately");
      setMode('view');
      setSuggested(null);
      fetchGroups();
    } catch { toast.error('Failed to save groups'); }
    finally { setSaving(false); }
  };

  const handleMoveToNew = async (dog, fromGroupId, reason) => {
    // Create a new group and move the dog into it
    const newGroupNum = Math.max(...groups.map(g => g.group_number), 0) + 1;
    try {
      // Save all current groups plus the new one
      const currentGroups = groups.map(g => ({
        group_number: g.group_number,
        is_individual: g.dogs.length === 1,
        label: g.label,
        notes: g.notes,
        dogs: g.dogs.filter(d => d.dog_id !== dog.dog_id).map(d => ({
          stay_id: d.stay_id, dog_id: d.dog_id
        })),
      })).filter(g => g.dogs.length > 0);
      currentGroups.push({
        group_number: newGroupNum,
        is_individual: true,
        label: `Group ${newGroupNum}`,
        notes: reason || 'Moved to new group',
        dogs: [{ stay_id: dog.stay_id, dog_id: dog.dog_id }],
      });
      await api.post('/playgroups/assign', { groups: currentGroups });
      toast.success(`${dog.dog_name} moved to new Group ${newGroupNum}`);
      setMoveModal(null);
      fetchGroups();
    } catch { toast.error('Failed to create new group'); }
  };

  const handleMove = async (dogId, stayId, fromGroupId, toGroupId, reason) => {
    try {
      await api.patch(`/playgroups/${fromGroupId}/move`, {
        dog_id: dogId,
        stay_id: stayId,
        to_group_id: toGroupId,
        reason,
      });
      toast.success('Dog moved');
      setMoveModal(null);
      fetchGroups();
    } catch (err) { toast.error(err.response?.data?.detail || 'Move failed'); }
  };

  const moveDogInEdit = (dogId, fromGroupIdx, toGroupIdx) => {
    const newGroups = [...editGroups];
    const dog = newGroups[fromGroupIdx].dogs.find(d => d.dog_id === dogId);
    newGroups[fromGroupIdx].dogs = newGroups[fromGroupIdx].dogs.filter(d => d.dog_id !== dogId);
    newGroups[toGroupIdx].dogs.push(dog);
    // Update individual status
    newGroups[fromGroupIdx].is_individual = newGroups[fromGroupIdx].dogs.length === 1;
    newGroups[toGroupIdx].is_individual = newGroups[toGroupIdx].dogs.length === 1;
    setEditGroups(newGroups);
  };

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-primary"></div>
    </div>
  );

  return (
    <div className="min-h-screen bg-[#F9F7F2]">
      <header className="bg-white border-b shadow-sm sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between">
          <div>
            <h1 className="text-lg font-serif font-bold text-primary">Playgroups</h1>
            <p className="text-xs text-muted-foreground">{new Date().toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' })}</p>
          </div>
          <div className="flex gap-2">
            {mode === 'view' && (
              <>
                <Button variant="outline" size="sm" onClick={() => navigate('/admin/playgroups/history')}>
                  History
                </Button>
                <Button variant="outline" size="sm" onClick={fetchGroups}>
                  <RefreshCwIcon size={14} />
                </Button>
                <Button size="sm" onClick={handleSuggest} disabled={suggesting}>
                  <SparklesIcon size={14} className="mr-1" />
                  {suggesting ? 'Generating...' : groups.length > 0 ? 'Re-suggest' : 'Suggest Groups'}
                </Button>
              </>
            )}
            {mode === 'suggest' && (
              <>
                <Button variant="outline" size="sm" onClick={() => setMode('view')}>Cancel</Button>
                <Button size="sm" onClick={handleSave} disabled={saving}>
                  <CheckIcon size={14} className="mr-1" />
                  {saving ? 'Saving...' : 'Publish Groups'}
                </Button>
              </>
            )}
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-6 space-y-4">

        {/* Unassigned dogs warning */}
        {unassigned.length > 0 && mode === 'view' && (
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
            <p className="text-sm font-medium text-amber-800 mb-2">
              ⚠️ {unassigned.length} dog{unassigned.length !== 1 ? 's' : ''} not yet assigned to a group
            </p>
            <div className="flex flex-wrap gap-2">
              {unassigned.map(d => (
                <Badge key={d.stay_id} variant="outline" className="text-xs text-amber-700 border-amber-300">
                  {d.dog_name} {d.room_name ? `· ${d.room_name}` : ''}
                </Badge>
              ))}
            </div>
          </div>
        )}

        {/* No groups yet */}
        {groups.length === 0 && mode === 'view' && (
          <Card>
            <CardContent className="py-12 text-center space-y-3">
              <SparklesIcon size={32} className="mx-auto text-muted-foreground" />
              <p className="font-semibold">No groups set for today</p>
              <p className="text-sm text-muted-foreground">Click "Suggest Groups" to auto-generate based on dog profiles</p>
              <Button onClick={handleSuggest} disabled={suggesting}>
                <SparklesIcon size={14} className="mr-1" />
                {suggesting ? 'Generating...' : 'Suggest Groups'}
              </Button>
            </CardContent>
          </Card>
        )}

        {/* View mode - current groups */}
        {mode === 'view' && groups.map((group, i) => (
          <GroupCard
            key={group.id}
            group={group}
            colorClass={group.is_individual ? 'bg-gray-50 border-gray-200 text-gray-700' : GROUP_COLORS[i % GROUP_COLORS.length]}
            badgeClass={group.is_individual ? 'bg-gray-100 text-gray-600' : GROUP_BADGE_COLORS[i % GROUP_BADGE_COLORS.length]}
            allGroups={groups}
            onMove={(dog) => setMoveModal({ dog, fromGroupId: group.id, fromGroupNum: group.group_number })}
            onNavigate={navigate}
          />
        ))}

        {/* Suggest/Edit mode */}
        {mode === 'suggest' && (
          <div className="space-y-3">
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-sm text-blue-800">
              <p className="font-medium">✨ AI-suggested groups — review and adjust before publishing</p>
              <p className="text-xs mt-1">Drag dogs between groups or use the move button. Changes are saved when you click "Publish Groups".</p>
            </div>
            {editGroups.map((group, i) => (
              <EditGroupCard
                key={i}
                group={group}
                groupIdx={i}
                colorClass={group.is_individual ? 'bg-gray-50 border-gray-200' : GROUP_COLORS[i % GROUP_COLORS.length]}
                allGroups={editGroups}
                onMove={moveDogInEdit}
                onUpdateLabel={(label) => {
                  const ng = [...editGroups];
                  ng[i].label = label;
                  setEditGroups(ng);
                }}
              />
            ))}
          </div>
        )}
      </main>

      {/* Move modal for live groups */}
      {moveModal && (
        <MoveModal
          dog={moveModal.dog}
          fromGroupId={moveModal.fromGroupId}
          fromGroupNum={moveModal.fromGroupNum}
          allGroups={groups}
          onMove={handleMove}
          onMoveToNew={handleMoveToNew}
          onClose={() => setMoveModal(null)}
        />
      )}
    </div>
  );
};

const GroupCard = ({ group, colorClass, badgeClass, allGroups, onMove, onNavigate }) => (
  <Card className={`border ${colorClass.split(' ').slice(0,2).join(' ')}`}>
    <CardHeader className="pb-2 pt-3 px-4">
      <CardTitle className="text-sm flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Badge className={`text-xs ${badgeClass}`}>
            {group.is_individual ? '👤 Individual' : `Group ${group.group_number}`}
          </Badge>
          <span className="font-normal text-muted-foreground text-xs">{group.label}</span>
        </div>
        <span className="text-xs font-normal text-muted-foreground">{group.dogs.length} dog{group.dogs.length !== 1 ? 's' : ''}</span>
      </CardTitle>
    </CardHeader>
    <CardContent className="px-4 pb-3 space-y-2">
      {group.dogs.map(dog => (
        <div key={dog.dog_id} className="flex items-center justify-between p-2 bg-white rounded-lg border border-border/40">
          <div className="cursor-pointer hover:opacity-70" onClick={() => onNavigate(`/admin/dogs/${dog.dog_id}`)}>
            <p className="text-sm font-medium">{dog.dog_name}</p>
            <p className="text-xs text-muted-foreground">
              {dog.breed}{dog.weight ? ` · ${dog.weight}lbs` : ''}{dog.room_name ? ` · ${dog.room_name}` : ''}
            </p>
          </div>
          <Button variant="ghost" size="sm" className="h-7 text-xs text-muted-foreground"
            onClick={() => onMove(dog)}>
            <ArrowRightIcon size={12} className="mr-1" /> Move
          </Button>
        </div>
      ))}
      {group.notes && (
        <p className="text-xs text-muted-foreground italic mt-1">{group.notes}</p>
      )}
    </CardContent>
  </Card>
);

const EditGroupCard = ({ group, groupIdx, colorClass, allGroups, onMove, onUpdateLabel }) => {
  const [movingDog, setMovingDog] = useState(null);
  return (
    <Card className={`border ${colorClass.split(' ').slice(0,2).join(' ')}`}>
      <CardHeader className="pb-2 pt-3 px-4">
        <CardTitle className="text-sm flex items-center gap-2">
          <Badge className="text-xs bg-white border">
            {group.is_individual ? '👤 Individual' : `Group ${group.group_number}`}
          </Badge>
          <input className="text-xs font-normal text-muted-foreground bg-transparent border-none outline-none flex-1"
            value={group.label || ''} onChange={e => onUpdateLabel(e.target.value)}
            placeholder="Group label..." />
        </CardTitle>
      </CardHeader>
      <CardContent className="px-4 pb-3 space-y-2">
        {group.dogs.map(dog => (
          <div key={dog.dog_id} className="flex items-center justify-between p-2 bg-white rounded-lg border border-border/40">
            <div>
              <p className="text-sm font-medium">{dog.dog_name}</p>
              <p className="text-xs text-muted-foreground">
                {dog.breed}{dog.weight ? ` · ${dog.weight}lbs` : ''}
                {dog.is_individual ? ` · ⚠️ ${group.reason}` : ''}
              </p>
            </div>
            <div className="flex gap-1">
              {movingDog === dog.dog_id ? (
                <div className="flex gap-1 flex-wrap max-w-48">
                  {allGroups.map((g, gi) => gi !== groupIdx && (
                    <button key={gi} type="button"
                      onClick={() => { onMove(dog.dog_id, groupIdx, gi); setMovingDog(null); }}
                      className="text-xs px-2 py-1 rounded bg-primary text-primary-foreground hover:bg-primary/80">
                      → {g.label || `Group ${g.group_number}`}
                    </button>
                  ))}
                  <button onClick={() => setMovingDog(null)} className="text-xs px-2 py-1 rounded bg-muted">×</button>
                </div>
              ) : (
                <Button variant="ghost" size="sm" className="h-7 text-xs"
                  onClick={() => setMovingDog(dog.dog_id)}>
                  <ArrowRightIcon size={12} className="mr-1" /> Move
                </Button>
              )}
            </div>
          </div>
        ))}
        {group.reason && (
          <p className="text-xs text-muted-foreground italic">{group.reason}</p>
        )}
      </CardContent>
    </Card>
  );
};

const MoveModal = ({ dog, fromGroupId, fromGroupNum, allGroups, onMove, onClose, onMoveToNew }) => {
  const [toGroupId, setToGroupId] = useState('');
  const [reason, setReason] = useState('');
  const otherGroups = allGroups.filter(g => g.id !== fromGroupId);

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-end md:items-center justify-center p-4">
      <div className="bg-white rounded-t-2xl md:rounded-2xl w-full max-w-md">
        <div className="p-6 space-y-4">
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-lg font-bold">Move {dog.dog_name}</h2>
              <p className="text-sm text-muted-foreground">From Group {fromGroupNum}</p>
            </div>
            <button onClick={onClose} className="text-muted-foreground text-xl">×</button>
          </div>
          <div>
            <p className="text-xs font-medium text-muted-foreground mb-2">Move to:</p>
            <div className="space-y-2">
              {otherGroups.map(g => (
                <button key={g.id} type="button" onClick={() => setToGroupId(g.id)}
                  className={`w-full text-left p-3 rounded-lg border text-sm transition-colors ${
                    toGroupId === g.id ? 'bg-primary/10 border-primary' : 'border-border hover:bg-muted'
                  }`}>
                  <span className="font-medium">{g.is_individual ? '👤 Individual' : `Group ${g.group_number}`}</span>
                  <span className="text-muted-foreground ml-2 text-xs">{g.label}</span>
                  <span className="text-muted-foreground ml-2 text-xs">({g.dogs.length} dogs)</span>
                </button>
              ))}
              <button type="button" onClick={() => setToGroupId('__new__')}
                className={`w-full text-left p-3 rounded-lg border text-sm transition-colors border-dashed ${
                  toGroupId === '__new__' ? 'bg-primary/10 border-primary' : 'border-border hover:bg-muted'
                }`}>
                <span className="font-medium">➕ Create New Group</span>
                <span className="text-muted-foreground ml-2 text-xs">Move to a new group by itself</span>
              </button>
            </div>
          </div>
          <div>
            <p className="text-xs font-medium text-muted-foreground mb-1">Reason for move (optional)</p>
            <Textarea value={reason} onChange={e => setReason(e.target.value)}
              rows={2} placeholder="e.g. Too rough with smaller dogs, owner request..." />
          </div>
          <div className="flex gap-3">
            <Button variant="outline" className="flex-1" onClick={onClose}>Cancel</Button>
            <Button className="flex-1" disabled={!toGroupId}
              onClick={() => {
                if (toGroupId === '__new__') {
                  onMoveToNew(dog, fromGroupId, reason);
                } else {
                  onMove(dog.dog_id, dog.stay_id, fromGroupId, toGroupId, reason);
                }
              }}>
              Confirm Move
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PlaygroupsPage;
