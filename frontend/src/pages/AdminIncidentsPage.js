import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { ArrowLeftIcon, AlertCircleIcon, AlertTriangleIcon } from 'lucide-react';
import { toast } from 'sonner';
import api from '../utils/api';
import useAuthStore from '../store/authStore';

const AdminIncidentsPage = () => {
  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);
  const [incidents, setIncidents] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user || user.role !== 'admin') {
      navigate('/auth');
      return;
    }
    fetchIncidents();
  }, [user, navigate]);

  const fetchIncidents = async () => {
    try {
      const response = await api.get('/incidents');
      setIncidents(response.data);
    } catch (error) {
      toast.error('Failed to load incidents');
    } finally {
      setLoading(false);
    }
  };

  const getSeverityColor = (severity) => {
    switch (severity.toLowerCase()) {
      case 'critical':
        return 'bg-red-100 text-red-800';
      case 'high':
        return 'bg-orange-100 text-orange-800';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800';
      case 'low':
        return 'bg-blue-100 text-blue-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const unresolvedIncidents = incidents.filter(i => !i.resolved);
  const resolvedIncidents = incidents.filter(i => i.resolved);

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
          <h1 className="text-3xl font-serif font-bold text-primary">Incident Reports</h1>
          <p className="text-muted-foreground mt-1">Safety and compliance tracking</p>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 md:px-8 py-8">
        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground uppercase tracking-wider mb-1">Total Incidents</p>
                  <p className="text-3xl font-serif font-bold text-primary">{incidents.length}</p>
                </div>
                <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center">
                  <AlertCircleIcon className="text-primary" size={24} />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground uppercase tracking-wider mb-1">Unresolved</p>
                  <p className="text-3xl font-serif font-bold text-red-600">{unresolvedIncidents.length}</p>
                </div>
                <div className="w-12 h-12 rounded-full bg-red-100 flex items-center justify-center">
                  <AlertTriangleIcon className="text-red-600" size={24} />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground uppercase tracking-wider mb-1">Resolved</p>
                  <p className="text-3xl font-serif font-bold text-green-600">{resolvedIncidents.length}</p>
                </div>
                <div className="w-12 h-12 rounded-full bg-green-100 flex items-center justify-center">
                  <AlertCircleIcon className="text-green-600" size={24} />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Incidents List */}
        {incidents.length === 0 ? (
          <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
            <CardContent className="p-12 text-center">
              <AlertCircleIcon size={48} className="mx-auto text-green-500 mb-4" />
              <p className="text-muted-foreground">No incidents reported - great job!</p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-4">
            {incidents.map((incident) => (
              <Card key={incident.id} className="bg-white rounded-2xl border border-border/50 shadow-sm">
                <CardContent className="p-6">
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <h3 className="text-xl font-serif font-semibold">{incident.title}</h3>
                        <Badge className={getSeverityColor(incident.severity)}>
                          {incident.severity}
                        </Badge>
                        {incident.resolved && (
                          <Badge className="bg-green-100 text-green-800">Resolved</Badge>
                        )}
                      </div>
                      <p className="text-sm text-muted-foreground mb-3">
                        Reported on {new Date(incident.created_at).toLocaleString()}
                      </p>
                    </div>
                  </div>
                  <p className="text-sm mb-3">{incident.description}</p>
                  {incident.resolution_notes && (
                    <div className="mt-3 p-3 rounded-lg bg-green-50 border border-green-200">
                      <p className="text-sm font-medium text-green-900 mb-1">Resolution:</p>
                      <p className="text-sm text-green-800">{incident.resolution_notes}</p>
                      {incident.resolved_at && (
                        <p className="text-xs text-green-600 mt-2">
                          Resolved on {new Date(incident.resolved_at).toLocaleString()}
                        </p>
                      )}
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </main>
    </div>
  );
};

export default AdminIncidentsPage;
