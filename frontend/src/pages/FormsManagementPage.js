import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { toast } from 'sonner';
import { 
  PlusIcon, 
  SearchIcon, 
  FileTextIcon, 
  EditIcon, 
  TrashIcon,
  EyeIcon,
  ClipboardListIcon,
  CheckCircleIcon,
  ClockIcon,
  XCircleIcon,
  ArrowLeftIcon,
  FilterIcon,
  DownloadIcon,
  BarChart3Icon
} from 'lucide-react';
import api from '../utils/api';

export default function FormsManagementPage() {
  const navigate = useNavigate();
  const [templates, setTemplates] = useState([]);
  const [submissions, setSubmissions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [activeTab, setActiveTab] = useState('templates');
  const [analytics, setAnalytics] = useState(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [templatesRes, submissionsRes, analyticsRes] = await Promise.all([
        api.get('/forms/templates'),
        api.get('/forms/submissions'),
        api.get('/forms/analytics/submissions')
      ]);
      setTemplates(templatesRes.data);
      setSubmissions(submissionsRes.data);
      setAnalytics(analyticsRes.data);
    } catch (error) {
      console.error('Failed to load forms data:', error);
      toast.error('Failed to load forms data');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteTemplate = async (templateId) => {
    if (!window.confirm('Are you sure you want to deactivate this form template?')) return;
    try {
      await api.delete(`/forms/templates/${templateId}`);
      toast.success('Form template deactivated');
      loadData();
    } catch (error) {
      toast.error('Failed to delete template');
    }
  };

  const handleReviewSubmission = async (submissionId, status) => {
    try {
      await api.post(`/forms/submissions/${submissionId}/review?status=${status}`);
      toast.success(`Submission ${status}`);
      loadData();
    } catch (error) {
      toast.error('Failed to review submission');
    }
  };

  const filteredTemplates = templates.filter(t => {
    const matchesSearch = t.name.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesCategory = categoryFilter === 'all' || t.category === categoryFilter;
    return matchesSearch && matchesCategory;
  });

  const filteredSubmissions = submissions.filter(s => {
    const matchesSearch = s.template_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         s.submitted_by_name?.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = statusFilter === 'all' || s.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const getStatusColor = (status) => {
    switch (status) {
      case 'submitted': return 'bg-blue-500/20 text-blue-400 border-blue-500/30';
      case 'approved': return 'bg-green-500/20 text-green-400 border-green-500/30';
      case 'rejected': return 'bg-red-500/20 text-red-400 border-red-500/30';
      case 'draft': return 'bg-slate-500/20 text-slate-400 border-slate-500/30';
      default: return 'bg-slate-500/20 text-slate-400 border-slate-500/30';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'submitted': return <ClockIcon size={14} />;
      case 'approved': return <CheckCircleIcon size={14} />;
      case 'rejected': return <XCircleIcon size={14} />;
      default: return <FileTextIcon size={14} />;
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="animate-spin h-8 w-8 border-2 border-blue-500 border-t-transparent rounded-full"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950" data-testid="forms-management-page">
      {/* Header */}
      <header className="bg-slate-900 border-b border-slate-700 px-6 py-4">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => navigate('/admin')}
                className="text-slate-400 hover:text-white"
              >
                <ArrowLeftIcon size={20} />
              </Button>
              <div>
                <h1 className="text-2xl font-bold text-white">Forms Management</h1>
                <p className="text-slate-400 text-sm">Create and manage form templates</p>
              </div>
            </div>
            <Button
              onClick={() => navigate('/admin/forms/builder')}
              className="bg-blue-600 hover:bg-blue-700 text-white"
              data-testid="create-form-btn"
            >
              <PlusIcon size={18} className="mr-2" />
              Create Form
            </Button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <Card className="bg-gradient-to-br from-blue-600 to-blue-700 border-none">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-white/20 flex items-center justify-center">
                  <FileTextIcon className="text-white" size={20} />
                </div>
                <div>
                  <p className="text-blue-100 text-sm">Templates</p>
                  <p className="text-2xl font-bold text-white">{templates.length}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-emerald-600 to-emerald-700 border-none">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-white/20 flex items-center justify-center">
                  <ClipboardListIcon className="text-white" size={20} />
                </div>
                <div>
                  <p className="text-emerald-100 text-sm">Submissions</p>
                  <p className="text-2xl font-bold text-white">{analytics?.total_submissions || 0}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-amber-600 to-amber-700 border-none">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-white/20 flex items-center justify-center">
                  <ClockIcon className="text-white" size={20} />
                </div>
                <div>
                  <p className="text-amber-100 text-sm">Pending Review</p>
                  <p className="text-2xl font-bold text-white">{analytics?.by_status?.submitted || 0}</p>
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
                  <p className="text-green-100 text-sm">Approved</p>
                  <p className="text-2xl font-bold text-white">{analytics?.by_status?.approved || 0}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <div className="flex items-center justify-between mb-6">
            <TabsList className="bg-slate-800">
              <TabsTrigger value="templates" className="data-[state=active]:bg-slate-700">
                Form Templates
              </TabsTrigger>
              <TabsTrigger value="submissions" className="data-[state=active]:bg-slate-700">
                Submissions
              </TabsTrigger>
              <TabsTrigger value="analytics" className="data-[state=active]:bg-slate-700">
                Analytics
              </TabsTrigger>
            </TabsList>

            <div className="flex items-center gap-3">
              <div className="relative">
                <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
                <Input
                  placeholder="Search..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-9 bg-slate-800 border-slate-700 text-white w-64"
                />
              </div>
              {activeTab === 'templates' && (
                <Select value={categoryFilter} onValueChange={setCategoryFilter}>
                  <SelectTrigger className="w-40 bg-slate-800 border-slate-700 text-white">
                    <FilterIcon size={14} className="mr-2" />
                    <SelectValue placeholder="Category" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Categories</SelectItem>
                    <SelectItem value="checklist">Checklist</SelectItem>
                    <SelectItem value="inspection">Inspection</SelectItem>
                    <SelectItem value="report">Report</SelectItem>
                    <SelectItem value="request">Request</SelectItem>
                  </SelectContent>
                </Select>
              )}
              {activeTab === 'submissions' && (
                <Select value={statusFilter} onValueChange={setStatusFilter}>
                  <SelectTrigger className="w-40 bg-slate-800 border-slate-700 text-white">
                    <FilterIcon size={14} className="mr-2" />
                    <SelectValue placeholder="Status" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Status</SelectItem>
                    <SelectItem value="draft">Draft</SelectItem>
                    <SelectItem value="submitted">Submitted</SelectItem>
                    <SelectItem value="approved">Approved</SelectItem>
                    <SelectItem value="rejected">Rejected</SelectItem>
                  </SelectContent>
                </Select>
              )}
            </div>
          </div>

          {/* Templates Tab */}
          <TabsContent value="templates">
            {filteredTemplates.length === 0 ? (
              <Card className="bg-slate-900 border-slate-700">
                <CardContent className="py-12 text-center">
                  <FileTextIcon className="mx-auto text-slate-600 mb-4" size={48} />
                  <h3 className="text-lg font-semibold text-slate-400 mb-2">No form templates yet</h3>
                  <p className="text-slate-500 mb-4">Create your first form template to get started</p>
                  <Button onClick={() => navigate('/admin/forms/builder')} className="bg-blue-600 hover:bg-blue-700">
                    <PlusIcon size={16} className="mr-2" />
                    Create Form
                  </Button>
                </CardContent>
              </Card>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {filteredTemplates.map(template => (
                  <Card 
                    key={template.id} 
                    className="bg-slate-900 border-slate-700 hover:border-slate-600 transition-colors"
                    data-testid={`template-card-${template.id}`}
                  >
                    <CardHeader className="pb-2">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <CardTitle className="text-white text-lg">{template.name}</CardTitle>
                          {template.description && (
                            <p className="text-slate-400 text-sm mt-1 line-clamp-2">{template.description}</p>
                          )}
                        </div>
                        {template.category && (
                          <Badge variant="outline" className="text-xs border-slate-600 text-slate-400">
                            {template.category}
                          </Badge>
                        )}
                      </div>
                    </CardHeader>
                    <CardContent>
                      <div className="flex items-center gap-4 text-sm text-slate-400 mb-4">
                        <span>{template.fields?.length || 0} fields</span>
                        {template.require_signature && <span>• Signature</span>}
                        {template.require_gps && <span>• GPS</span>}
                      </div>
                      <div className="flex gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => navigate(`/admin/forms/builder/${template.id}`)}
                          className="flex-1 border-slate-600 text-slate-300 hover:text-white"
                        >
                          <EditIcon size={14} className="mr-1" />
                          Edit
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => navigate(`/admin/forms/submissions?template=${template.id}`)}
                          className="flex-1 border-slate-600 text-slate-300 hover:text-white"
                        >
                          <EyeIcon size={14} className="mr-1" />
                          View
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDeleteTemplate(template.id)}
                          className="text-slate-400 hover:text-red-400"
                        >
                          <TrashIcon size={14} />
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </TabsContent>

          {/* Submissions Tab */}
          <TabsContent value="submissions">
            {filteredSubmissions.length === 0 ? (
              <Card className="bg-slate-900 border-slate-700">
                <CardContent className="py-12 text-center">
                  <ClipboardListIcon className="mx-auto text-slate-600 mb-4" size={48} />
                  <h3 className="text-lg font-semibold text-slate-400 mb-2">No submissions yet</h3>
                  <p className="text-slate-500">Form submissions will appear here</p>
                </CardContent>
              </Card>
            ) : (
              <Card className="bg-slate-900 border-slate-700">
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-slate-700">
                        <th className="text-left text-slate-400 font-medium px-4 py-3 text-sm">Form</th>
                        <th className="text-left text-slate-400 font-medium px-4 py-3 text-sm">Submitted By</th>
                        <th className="text-left text-slate-400 font-medium px-4 py-3 text-sm">Date</th>
                        <th className="text-left text-slate-400 font-medium px-4 py-3 text-sm">Status</th>
                        <th className="text-right text-slate-400 font-medium px-4 py-3 text-sm">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredSubmissions.map(submission => (
                        <tr 
                          key={submission.id} 
                          className="border-b border-slate-800 hover:bg-slate-800/50"
                          data-testid={`submission-row-${submission.id}`}
                        >
                          <td className="px-4 py-3">
                            <span className="text-white font-medium">{submission.template_name}</span>
                          </td>
                          <td className="px-4 py-3">
                            <span className="text-slate-300">{submission.submitted_by_name}</span>
                          </td>
                          <td className="px-4 py-3">
                            <span className="text-slate-400 text-sm">
                              {new Date(submission.created_at).toLocaleDateString()}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            <Badge className={`${getStatusColor(submission.status)} flex items-center gap-1 w-fit`}>
                              {getStatusIcon(submission.status)}
                              {submission.status}
                            </Badge>
                          </td>
                          <td className="px-4 py-3 text-right">
                            <div className="flex justify-end gap-2">
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => navigate(`/admin/forms/submission/${submission.id}`)}
                                className="text-slate-400 hover:text-white"
                              >
                                <EyeIcon size={14} />
                              </Button>
                              {submission.status === 'submitted' && (
                                <>
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => handleReviewSubmission(submission.id, 'approved')}
                                    className="text-green-400 hover:text-green-300"
                                  >
                                    <CheckCircleIcon size={14} />
                                  </Button>
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => handleReviewSubmission(submission.id, 'rejected')}
                                    className="text-red-400 hover:text-red-300"
                                  >
                                    <XCircleIcon size={14} />
                                  </Button>
                                </>
                              )}
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>
            )}
          </TabsContent>

          {/* Analytics Tab */}
          <TabsContent value="analytics">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card className="bg-slate-900 border-slate-700">
                <CardHeader>
                  <CardTitle className="text-white flex items-center gap-2">
                    <BarChart3Icon size={20} />
                    Submissions by Status
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {Object.entries(analytics?.by_status || {}).map(([status, count]) => (
                      <div key={status} className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          {getStatusIcon(status)}
                          <span className="text-slate-300 capitalize">{status}</span>
                        </div>
                        <div className="flex items-center gap-3">
                          <div className="w-32 bg-slate-800 rounded-full h-2">
                            <div
                              className={`h-2 rounded-full ${
                                status === 'approved' ? 'bg-green-500' :
                                status === 'rejected' ? 'bg-red-500' :
                                status === 'submitted' ? 'bg-blue-500' : 'bg-slate-500'
                              }`}
                              style={{ width: `${(count / (analytics?.total_submissions || 1)) * 100}%` }}
                            />
                          </div>
                          <span className="text-white font-medium w-8 text-right">{count}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-slate-900 border-slate-700">
                <CardHeader>
                  <CardTitle className="text-white flex items-center gap-2">
                    <FileTextIcon size={20} />
                    Submissions by Form
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {Object.entries(analytics?.by_template || {}).slice(0, 5).map(([name, count]) => (
                      <div key={name} className="flex items-center justify-between">
                        <span className="text-slate-300 truncate max-w-[200px]">{name}</span>
                        <div className="flex items-center gap-3">
                          <div className="w-32 bg-slate-800 rounded-full h-2">
                            <div
                              className="h-2 rounded-full bg-blue-500"
                              style={{ width: `${(count / (analytics?.total_submissions || 1)) * 100}%` }}
                            />
                          </div>
                          <span className="text-white font-medium w-8 text-right">{count}</span>
                        </div>
                      </div>
                    ))}
                    {Object.keys(analytics?.by_template || {}).length === 0 && (
                      <p className="text-slate-500 text-center py-4">No data yet</p>
                    )}
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
}
