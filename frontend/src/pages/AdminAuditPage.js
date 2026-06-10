import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import useAuthStore from '../store/authStore';
import api from '../utils/api';
import { Button } from '../components/ui/button';
import { Card, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { ArrowLeftIcon, ShieldIcon } from 'lucide-react';
import { toast } from 'sonner';

const ACTION_COLORS = {
  create: 'bg-green-100 text-green-700',
  update: 'bg-blue-100 text-blue-700',
  delete: 'bg-red-100 text-red-700',
  login: 'bg-gray-100 text-gray-600',
  check_in: 'bg-teal-100 text-teal-700',
  check_out: 'bg-orange-100 text-orange-700',
};

const AdminAuditPage = () => {
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);

  const fetchLogs = useCallback(async () => {
    try {
      const res = await api.get('/audit-logs', {
        params: { skip: page * 50, limit: 50 }
      });
      setLogs(res.data);
    } catch {
      // Audit log endpoint may not exist yet - show placeholder
      setLogs([]);
    } finally {
      setLoading(false);
    }
  }, [page]);

  useEffect(() => {
    if (!user || user.role !== 'admin') { navigate('/auth'); return; }
    fetchLogs();
  }, [user, navigate, fetchLogs]);

  return (
    <div className="min-h-screen bg-[#F9F7F2]">
      <header className="bg-white border-b shadow-sm sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={() => navigate(-1)}>
            <ArrowLeftIcon size={18} />
          </Button>
          <h1 className="text-lg font-serif font-bold text-primary">Audit Log</h1>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-6 space-y-3">
        {loading ? (
          <div className="flex justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-primary"></div>
          </div>
        ) : logs.length === 0 ? (
          <Card>
            <CardContent className="py-12 text-center">
              <ShieldIcon size={32} className="mx-auto mb-3 text-muted-foreground" />
              <p className="text-muted-foreground">No audit logs available yet</p>
              <p className="text-xs text-muted-foreground mt-1">Actions will appear here as staff use the system</p>
            </CardContent>
          </Card>
        ) : (
          <>
            {logs.map(log => (
              <Card key={log.id}>
                <CardContent className="py-3 px-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <Badge className={`text-xs ${ACTION_COLORS[log.action?.toLowerCase()] || 'bg-gray-100 text-gray-600'}`}>
                          {log.action}
                        </Badge>
                        <span className="text-sm font-medium">{log.resource_type}</span>
                      </div>
                      <p className="text-xs text-muted-foreground">{log.description || log.resource_id}</p>
                      <p className="text-xs text-muted-foreground mt-0.5">by {log.user_id}</p>
                    </div>
                    <p className="text-xs text-muted-foreground whitespace-nowrap">
                      {new Date(log.created_at).toLocaleString()}
                    </p>
                  </div>
                </CardContent>
              </Card>
            ))}
            <div className="flex justify-between pt-2">
              <Button variant="outline" size="sm" disabled={page === 0} onClick={() => setPage(p => p - 1)}>
                Previous
              </Button>
              <Button variant="outline" size="sm" disabled={logs.length < 50} onClick={() => setPage(p => p + 1)}>
                Next
              </Button>
            </div>
          </>
        )}
      </main>
    </div>
  );
};

export default AdminAuditPage;
