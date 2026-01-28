import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { ArrowLeftIcon, FileTextIcon, SearchIcon } from 'lucide-react';
import { toast } from 'sonner';
import api from '../utils/api';
import useAuthStore from '../store/authStore';

const AdminAuditPage = () => {
  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);
  const [auditLogs, setAuditLogs] = useState([]);
  const [filteredLogs, setFilteredLogs] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [actionFilter, setActionFilter] = useState('all');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user || user.role !== 'admin') {
      navigate('/auth');
      return;
    }
    fetchAuditLogs();
  }, [user, navigate]);

  useEffect(() => {
    filterLogs();
  }, [auditLogs, searchQuery, actionFilter]);

  const fetchAuditLogs = async () => {
    try {
      const response = await api.get('/audit-logs');
      setAuditLogs(response.data);
    } catch (error) {
      toast.error('Failed to load audit logs');
    } finally {
      setLoading(false);
    }
  };

  const filterLogs = () => {
    let filtered = auditLogs;

    if (actionFilter !== 'all') {
      filtered = filtered.filter((log) => log.action === actionFilter);
    }

    if (searchQuery) {
      filtered = filtered.filter(
        (log) =>
          log.resource_type.toLowerCase().includes(searchQuery.toLowerCase()) ||
          log.user_id.toLowerCase().includes(searchQuery.toLowerCase())
      );
    }

    setFilteredLogs(filtered);
  };

  const getActionColor = (action) => {
    switch (action) {
      case 'create':
        return 'bg-green-100 text-green-800';
      case 'update':
        return 'bg-blue-100 text-blue-800';
      case 'delete':
        return 'bg-red-100 text-red-800';
      case 'login':
        return 'bg-purple-100 text-purple-800';
      case 'logout':
        return 'bg-gray-100 text-gray-800';
      case 'check_in':
        return 'bg-teal-100 text-teal-800';
      case 'check_out':
        return 'bg-orange-100 text-orange-800';
      case 'payment':
        return 'bg-yellow-100 text-yellow-800';
      case 'incident':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const actions = ['all', 'create', 'update', 'delete', 'login', 'check_in', 'check_out', 'payment', 'incident'];

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="inline-block animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#F9F7F2]">
      <header className="bg-white border-b border-border/40 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 md:px-8 py-4">
          <Button
            variant="ghost"
            onClick={() => navigate('/admin/dashboard')}
            className="flex items-center gap-2 mb-2"
          >
            <ArrowLeftIcon size={18} />
            Back to Dashboard
          </Button>
          <h1 className="text-3xl font-serif font-bold text-primary">Audit Logs</h1>
          <p className="text-muted-foreground mt-1">Complete system activity history (7-year retention)</p>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 md:px-8 py-8">
        {/* Filters */}
        <Card className="mb-6 bg-white rounded-2xl border border-border/50 shadow-sm">
          <CardContent className="p-6">
            <div className="flex flex-col md:flex-row gap-4">
              <div className="flex-1 relative">
                <SearchIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground" size={20} />
                <Input
                  placeholder="Search by resource type or user..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10"
                />
              </div>
              <div className="flex gap-2 flex-wrap">
                {actions.map((action) => (
                  <Button
                    key={action}
                    onClick={() => setActionFilter(action)}
                    variant={actionFilter === action ? 'default' : 'outline'}
                    size="sm"
                    className="rounded-full capitalize"
                  >
                    {action.replace('_', ' ')}
                  </Button>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <Card className="bg-white rounded-xl border border-border/50 shadow-sm">
            <CardContent className="p-4 text-center">
              <p className="text-xs text-muted-foreground uppercase tracking-wider mb-1">Total Logs</p>
              <p className="text-2xl font-serif font-bold">{auditLogs.length}</p>
            </CardContent>
          </Card>
          <Card className="bg-white rounded-xl border border-border/50 shadow-sm">
            <CardContent className="p-4 text-center">
              <p className="text-xs text-muted-foreground uppercase tracking-wider mb-1">Today</p>
              <p className="text-2xl font-serif font-bold">
                {auditLogs.filter(log => {
                  const logDate = new Date(log.created_at).toDateString();
                  const today = new Date().toDateString();
                  return logDate === today;
                }).length}
              </p>
            </CardContent>
          </Card>
          <Card className="bg-white rounded-xl border border-border/50 shadow-sm">
            <CardContent className="p-4 text-center">
              <p className="text-xs text-muted-foreground uppercase tracking-wider mb-1">Actions</p>
              <p className="text-2xl font-serif font-bold">
                {[...new Set(auditLogs.map(l => l.action))].length}
              </p>
            </CardContent>
          </Card>
          <Card className="bg-white rounded-xl border border-border/50 shadow-sm">
            <CardContent className="p-4 text-center">
              <p className="text-xs text-muted-foreground uppercase tracking-wider mb-1">Resources</p>
              <p className="text-2xl font-serif font-bold">
                {[...new Set(auditLogs.map(l => l.resource_type))].length}
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Logs List */}
        {filteredLogs.length === 0 ? (
          <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
            <CardContent className="p-12 text-center">
              <FileTextIcon size={48} className="mx-auto text-muted-foreground/50 mb-4" />
              <p className="text-muted-foreground">No audit logs found</p>
            </CardContent>
          </Card>
        ) : (
          <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
            <CardContent className="p-6">
              <div className="space-y-3">
                {filteredLogs.map((log) => (
                  <div
                    key={log.id}
                    className="p-4 rounded-xl bg-muted/30 border border-border hover:border-primary/30 transition-all"
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex items-center gap-3">
                        <Badge className={getActionColor(log.action)}>
                          {log.action.replace('_', ' ')}
                        </Badge>
                        <span className="font-semibold">{log.resource_type}</span>
                      </div>
                      <span className="text-xs text-muted-foreground">
                        {new Date(log.created_at).toLocaleString()}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <span>User: {log.user_id.slice(0, 8)}</span>
                      {log.resource_id && (
                        <>
                          <span>•</span>
                          <span>Resource: {log.resource_id.slice(0, 8)}</span>
                        </>
                      )}
                    </div>
                    {log.details && Object.keys(log.details).length > 0 && (
                      <div className="mt-2 p-2 rounded bg-muted/50 text-xs font-mono">
                        {JSON.stringify(log.details, null, 2)}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}
      </main>
    </div>
  );
};

export default AdminAuditPage;
