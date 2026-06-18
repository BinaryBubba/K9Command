import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import useAuthStore from '../store/authStore';
import api from '../utils/api';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { ArrowRightIcon, ClockIcon, RefreshCwIcon } from 'lucide-react';
import { toast } from 'sonner';

const PlaygroupHistoryPage = () => {
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchHistory = useCallback(async () => {
    try {
      const res = await api.get('/playgroups/history', { params: { limit: 100 } });
      setHistory(res.data);
    } catch { toast.error('Failed to load history'); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => {
    if (!user) { navigate('/auth'); return; }
    fetchHistory();
  }, [user, navigate, fetchHistory]);

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-primary"></div>
    </div>
  );

  return (
    <div className="min-h-screen bg-[#F9F7F2]">
      <header className="bg-white border-b shadow-sm sticky top-0 z-10">
        <div className="max-w-3xl mx-auto px-4 py-3 flex items-center justify-between">
          <div>
            <h1 className="text-lg font-serif font-bold text-primary">Group Change History</h1>
            <p className="text-xs text-muted-foreground">All recorded group reassignments</p>
          </div>
          <button onClick={fetchHistory} className="p-2 rounded-lg hover:bg-muted">
            <RefreshCwIcon size={16} />
          </button>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 py-6 space-y-2">
        {history.length === 0 ? (
          <Card>
            <CardContent className="py-12 text-center text-muted-foreground">
              No group changes recorded yet
            </CardContent>
          </Card>
        ) : history.map(item => (
          <Card key={item.id}>
            <CardContent className="py-3 px-4">
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-start gap-3">
                  <ClockIcon size={14} className="text-muted-foreground mt-0.5 shrink-0" />
                  <div>
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-sm font-medium">{item.dog_name}</span>
                      {item.from_group !== null && (
                        <>
                          <Badge variant="outline" className="text-xs">Group {item.from_group}</Badge>
                          <ArrowRightIcon size={12} className="text-muted-foreground" />
                        </>
                      )}
                      <Badge variant="outline" className="text-xs bg-blue-50 text-blue-700 border-blue-200">
                        Group {item.to_group}
                      </Badge>
                    </div>
                    {item.reason && (
                      <p className="text-xs text-muted-foreground mt-0.5">Reason: {item.reason}</p>
                    )}
                    <p className="text-xs text-muted-foreground mt-0.5">
                      by {item.changed_by_name || 'Unknown'} · {new Date(item.changed_at).toLocaleString()}
                    </p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </main>
    </div>
  );
};

export default PlaygroupHistoryPage;
