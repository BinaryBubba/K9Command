import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { toast } from 'sonner';
import { 
  SearchIcon, 
  FileTextIcon, 
  ClipboardListIcon,
  CheckCircleIcon,
  ClockIcon,
  ArrowLeftIcon,
  ChevronRightIcon,
  EditIcon,
  AlertCircleIcon
} from 'lucide-react';
import api from '../utils/api';
import useAuthStore from '../store/authStore';

export default function StaffFormsPage() {
  const navigate = useNavigate();
  const { user } = useAuthStore();
  
  const [templates, setTemplates] = useState([]);
  const [submissions, setSubmissions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [activeTab, setActiveTab] = useState('available');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [templatesRes, submissionsRes] = await Promise.all([
        api.get('/forms/templates'),
        api.get('/forms/submissions')
      ]);
      setTemplates(templatesRes.data || []);
      setSubmissions(submissionsRes.data || []);
    } catch (error) {
      console.error('Failed to load forms data:', error);
      toast.error('Failed to load forms');
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'submitted': return 'bg-blue-500/20 text-blue-400 border-blue-500/30';
      case 'approved': return 'bg-green-500/20 text-green-400 border-green-500/30';
      case 'rejected': return 'bg-red-500/20 text-red-400 border-red-500/30';
      case 'draft': return 'bg-amber-500/20 text-amber-400 border-amber-500/30';
      default: return 'bg-slate-500/20 text-slate-400 border-slate-500/30';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'submitted': return <ClockIcon size={14} />;
      case 'approved': return <CheckCircleIcon size={14} />;
      case 'rejected': return <AlertCircleIcon size={14} />;
      default: return <EditIcon size={14} />;
    }
  };

  const filteredTemplates = templates.filter(t => 
    t.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    t.description?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const mySubmissions = submissions.filter(s => s.submitted_by === user?.id);
  const draftSubmissions = mySubmissions.filter(s => s.status === 'draft');
  const submittedSubmissions = mySubmissions.filter(s => s.status !== 'draft');

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="animate-spin h-8 w-8 border-2 border-blue-500 border-t-transparent rounded-full"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950" data-testid="staff-forms-page">
      {/* Header */}
      <header className="bg-slate-900 border-b border-slate-700 px-6 py-4">
        <div className="max-w-5xl mx-auto">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => navigate('/staff')}
                className="text-slate-400 hover:text-white"
              >
                <ArrowLeftIcon size={20} />
              </Button>
              <div>
                <h1 className="text-2xl font-bold text-white">Forms</h1>
                <p className="text-slate-400 text-sm">Fill out and submit forms</p>
              </div>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-8">
        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          <Card className="bg-gradient-to-br from-blue-600 to-blue-700 border-none">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-white/20 flex items-center justify-center">
                  <FileTextIcon className="text-white" size={20} />
                </div>
                <div>
                  <p className="text-blue-100 text-sm">Available Forms</p>
                  <p className="text-2xl font-bold text-white">{templates.length}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-amber-600 to-amber-700 border-none">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-white/20 flex items-center justify-center">
                  <EditIcon className="text-white" size={20} />
                </div>
                <div>
                  <p className="text-amber-100 text-sm">Drafts</p>
                  <p className="text-2xl font-bold text-white">{draftSubmissions.length}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-green-600 to-green-700 border-none">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-white/20 flex items-center justify-center">
                  <CheckCircleIcon className="text-white" size={20} />
                </div>
                <div>
                  <p className="text-green-100 text-sm">Submitted</p>
                  <p className="text-2xl font-bold text-white">{submittedSubmissions.length}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Search */}
        <div className="relative mb-6">
          <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
          <Input
            placeholder="Search forms..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-10 bg-slate-800 border-slate-700 text-white"
          />
        </div>

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="bg-slate-800 mb-6">
            <TabsTrigger value="available" className="data-[state=active]:bg-slate-700">
              Available Forms
            </TabsTrigger>
            <TabsTrigger value="drafts" className="data-[state=active]:bg-slate-700">
              My Drafts
              {draftSubmissions.length > 0 && (
                <Badge className="ml-2 bg-amber-500 text-white">{draftSubmissions.length}</Badge>
              )}
            </TabsTrigger>
            <TabsTrigger value="submitted" className="data-[state=active]:bg-slate-700">
              Submitted
            </TabsTrigger>
          </TabsList>

          {/* Available Forms */}
          <TabsContent value="available">
            {filteredTemplates.length === 0 ? (
              <Card className="bg-slate-900 border-slate-700">
                <CardContent className="py-12 text-center">
                  <FileTextIcon className="mx-auto text-slate-600 mb-4" size={48} />
                  <h3 className="text-lg font-semibold text-slate-400 mb-2">No forms available</h3>
                  <p className="text-slate-500">Check back later for new forms</p>
                </CardContent>
              </Card>
            ) : (
              <div className="space-y-3">
                {filteredTemplates.map(template => (
                  <Card 
                    key={template.id}
                    className="bg-slate-900 border-slate-700 hover:border-slate-600 transition-colors cursor-pointer"
                    onClick={() => navigate(`/staff/forms/submit/${template.id}`)}
                    data-testid={`form-template-${template.id}`}
                  >
                    <CardContent className="p-4">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-4">
                          <div className="w-12 h-12 rounded-lg bg-blue-500/20 flex items-center justify-center">
                            <ClipboardListIcon className="text-blue-400" size={24} />
                          </div>
                          <div>
                            <h3 className="font-medium text-white">{template.name}</h3>
                            {template.description && (
                              <p className="text-slate-400 text-sm line-clamp-1">{template.description}</p>
                            )}
                            <div className="flex items-center gap-3 mt-1 text-xs text-slate-500">
                              <span>{template.fields?.length || 0} fields</span>
                              {template.require_signature && <span>• Signature required</span>}
                              {template.require_gps && <span>• Location required</span>}
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          {template.category && (
                            <Badge variant="outline" className="border-slate-600 text-slate-400">
                              {template.category}
                            </Badge>
                          )}
                          <ChevronRightIcon className="text-slate-500" size={20} />
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </TabsContent>

          {/* Drafts */}
          <TabsContent value="drafts">
            {draftSubmissions.length === 0 ? (
              <Card className="bg-slate-900 border-slate-700">
                <CardContent className="py-12 text-center">
                  <EditIcon className="mx-auto text-slate-600 mb-4" size={48} />
                  <h3 className="text-lg font-semibold text-slate-400 mb-2">No drafts</h3>
                  <p className="text-slate-500">Your saved drafts will appear here</p>
                </CardContent>
              </Card>
            ) : (
              <div className="space-y-3">
                {draftSubmissions.map(submission => (
                  <Card 
                    key={submission.id}
                    className="bg-slate-900 border-slate-700 hover:border-slate-600 transition-colors cursor-pointer"
                    onClick={() => navigate(`/staff/forms/submit/${submission.template_id}/${submission.id}`)}
                  >
                    <CardContent className="p-4">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-4">
                          <div className="w-12 h-12 rounded-lg bg-amber-500/20 flex items-center justify-center">
                            <EditIcon className="text-amber-400" size={24} />
                          </div>
                          <div>
                            <h3 className="font-medium text-white">{submission.template_name}</h3>
                            <p className="text-slate-400 text-sm">
                              Last saved: {new Date(submission.updated_at).toLocaleString()}
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <Badge className={getStatusColor('draft')}>
                            Draft
                          </Badge>
                          <ChevronRightIcon className="text-slate-500" size={20} />
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </TabsContent>

          {/* Submitted */}
          <TabsContent value="submitted">
            {submittedSubmissions.length === 0 ? (
              <Card className="bg-slate-900 border-slate-700">
                <CardContent className="py-12 text-center">
                  <ClipboardListIcon className="mx-auto text-slate-600 mb-4" size={48} />
                  <h3 className="text-lg font-semibold text-slate-400 mb-2">No submissions yet</h3>
                  <p className="text-slate-500">Your submitted forms will appear here</p>
                </CardContent>
              </Card>
            ) : (
              <div className="space-y-3">
                {submittedSubmissions.map(submission => (
                  <Card 
                    key={submission.id}
                    className="bg-slate-900 border-slate-700"
                  >
                    <CardContent className="p-4">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-4">
                          <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${
                            submission.status === 'approved' ? 'bg-green-500/20' :
                            submission.status === 'rejected' ? 'bg-red-500/20' : 'bg-blue-500/20'
                          }`}>
                            {getStatusIcon(submission.status)}
                          </div>
                          <div>
                            <h3 className="font-medium text-white">{submission.template_name}</h3>
                            <p className="text-slate-400 text-sm">
                              Submitted: {new Date(submission.submitted_at || submission.created_at).toLocaleString()}
                            </p>
                            {submission.review_notes && (
                              <p className="text-slate-500 text-xs mt-1">
                                Note: {submission.review_notes}
                              </p>
                            )}
                          </div>
                        </div>
                        <Badge className={getStatusColor(submission.status)}>
                          {getStatusIcon(submission.status)}
                          <span className="ml-1">{submission.status}</span>
                        </Badge>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
}
