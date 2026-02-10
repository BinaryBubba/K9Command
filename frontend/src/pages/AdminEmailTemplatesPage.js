import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import useAuthStore from '../store/authStore';
import { dataClient, dataMode } from '../data/client';
import { Button } from '../components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { ArrowLeftIcon, MailIcon, SendIcon, EyeIcon, SaveIcon, InboxIcon, RefreshCwIcon } from 'lucide-react';
import { toast } from 'sonner';

const AdminEmailTemplatesPage = () => {
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [templates, setTemplates] = useState({});
  const [outbox, setOutbox] = useState([]);
  const [activeTemplate, setActiveTemplate] = useState('booking_confirmation');

  // Template form
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');

  // Preview/Test modal
  const [showPreview, setShowPreview] = useState(false);
  const [showTestModal, setShowTestModal] = useState(false);
  const [testEmail, setTestEmail] = useState('');
  const [sendingTest, setSendingTest] = useState(false);

  useEffect(() => {
    if (!user || user.role !== 'admin') {
      navigate('/auth');
      return;
    }
    loadData();
  }, [user, navigate]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [templatesData, outboxData] = await Promise.all([
        dataClient.getEmailTemplates(),
        dataClient.getEmailOutbox(),
      ]);
      setTemplates(templatesData || {});
      setOutbox(outboxData || []);

      // Load active template
      const template = templatesData?.[activeTemplate];
      if (template) {
        setSubject(template.subject || '');
        setBody(template.body || '');
      }
    } catch (error) {
      console.error('Failed to load email data:', error);
      toast.error('Failed to load email data');
    } finally {
      setLoading(false);
    }
  };

  const handleTemplateChange = (templateName) => {
    setActiveTemplate(templateName);
    const template = templates[templateName];
    if (template) {
      setSubject(template.subject || '');
      setBody(template.body || '');
    } else {
      setSubject('');
      setBody('');
    }
  };

  const handleSaveTemplate = async () => {
    setSaving(true);
    try {
      await dataClient.updateEmailTemplate(activeTemplate, { subject, body });
      toast.success('Template saved!');
      loadData();
    } catch (error) {
      toast.error('Failed to save template');
    } finally {
      setSaving(false);
    }
  };

  const handleSendTest = async () => {
    if (!testEmail) {
      toast.error('Please enter an email address');
      return;
    }
    setSendingTest(true);
    try {
      await dataClient.sendTestEmail(activeTemplate, testEmail);
      toast.success(dataMode === 'mock' ? 'Test email added to outbox!' : 'Test email sent!');
      setShowTestModal(false);
      setTestEmail('');
      loadData();
    } catch (error) {
      toast.error('Failed to send test email');
    } finally {
      setSendingTest(false);
    }
  };

  const getPreviewContent = () => {
    // Replace placeholders with sample data
    const sampleData = {
      startDate: '2024-03-15',
      endDate: '2024-03-20',
      dogs: 'Buddy, Max',
      status: 'confirmed',
      total: '275.00',
    };

    let previewSubject = subject;
    let previewBody = body;

    Object.entries(sampleData).forEach(([key, value]) => {
      const regex = new RegExp(`\\{\\{${key}\\}\\}`, 'g');
      previewSubject = previewSubject.replace(regex, value);
      previewBody = previewBody.replace(regex, value);
    });

    return { subject: previewSubject, body: previewBody };
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-950">
        <div className="animate-spin h-8 w-8 border-2 border-blue-500 border-t-transparent rounded-full"></div>
      </div>
    );
  }

  const preview = getPreviewContent();

  return (
    <div className="min-h-screen bg-slate-950">
      {/* Header */}
      <header className="bg-slate-900 border-b border-slate-700 px-6 py-4">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button variant="ghost" onClick={() => navigate('/admin/dashboard')} className="text-slate-400 hover:text-white">
              <ArrowLeftIcon size={20} />
            </Button>
            <div>
              <h1 className="text-2xl font-bold text-white flex items-center gap-2">
                <MailIcon size={24} />
                Email Templates
              </h1>
              <p className="text-slate-400 text-sm">Manage email notifications • Mode: {dataMode}</p>
            </div>
          </div>
          <Button variant="outline" onClick={loadData} className="border-slate-600 text-slate-300">
            <RefreshCwIcon size={16} className="mr-2" />
            Refresh
          </Button>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-8">
        <Tabs defaultValue="editor" className="space-y-6">
          <TabsList className="bg-slate-800 border border-slate-700">
            <TabsTrigger value="editor" className="data-[state=active]:bg-blue-600">
              Template Editor
            </TabsTrigger>
            <TabsTrigger value="outbox" className="data-[state=active]:bg-blue-600">
              <InboxIcon size={16} className="mr-2" />
              Outbox ({outbox.length})
            </TabsTrigger>
          </TabsList>

          {/* Editor Tab */}
          <TabsContent value="editor">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Template Selector */}
              <Card className="bg-slate-900 border-slate-700">
                <CardHeader>
                  <CardTitle className="text-white">Templates</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  <Button
                    variant={activeTemplate === 'booking_confirmation' ? 'default' : 'ghost'}
                    className="w-full justify-start"
                    onClick={() => handleTemplateChange('booking_confirmation')}
                  >
                    Booking Confirmation
                  </Button>
                  <Button
                    variant={activeTemplate === 'booking_reminder' ? 'default' : 'ghost'}
                    className="w-full justify-start"
                    onClick={() => handleTemplateChange('booking_reminder')}
                  >
                    Booking Reminder
                  </Button>
                  <Button
                    variant={activeTemplate === 'check_in_reminder' ? 'default' : 'ghost'}
                    className="w-full justify-start"
                    onClick={() => handleTemplateChange('check_in_reminder')}
                  >
                    Check-in Reminder
                  </Button>
                  <Button
                    variant={activeTemplate === 'check_out_reminder' ? 'default' : 'ghost'}
                    className="w-full justify-start"
                    onClick={() => handleTemplateChange('check_out_reminder')}
                  >
                    Check-out Reminder
                  </Button>
                </CardContent>
              </Card>

              {/* Editor */}
              <div className="lg:col-span-2 space-y-4">
                <Card className="bg-slate-900 border-slate-700">
                  <CardHeader className="flex flex-row items-center justify-between">
                    <CardTitle className="text-white">
                      Edit: {activeTemplate.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                    </CardTitle>
                    <div className="flex gap-2">
                      <Button variant="outline" size="sm" onClick={() => setShowPreview(true)} className="border-slate-600 text-slate-300">
                        <EyeIcon size={16} className="mr-2" />
                        Preview
                      </Button>
                      <Button variant="outline" size="sm" onClick={() => setShowTestModal(true)} className="border-slate-600 text-slate-300">
                        <SendIcon size={16} className="mr-2" />
                        Send Test
                      </Button>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div>
                      <Label className="text-slate-300">Subject</Label>
                      <Input
                        value={subject}
                        onChange={(e) => setSubject(e.target.value)}
                        placeholder="Email subject..."
                        className="bg-slate-800 border-slate-700 text-white mt-1"
                      />
                    </div>
                    <div>
                      <Label className="text-slate-300">Body</Label>
                      <Textarea
                        value={body}
                        onChange={(e) => setBody(e.target.value)}
                        placeholder="Email body..."
                        rows={12}
                        className="bg-slate-800 border-slate-700 text-white mt-1 font-mono text-sm"
                      />
                    </div>
                    <div className="bg-slate-800 rounded-lg p-4">
                      <p className="text-sm text-slate-400 mb-2">Available placeholders:</p>
                      <div className="flex flex-wrap gap-2">
                        {['{{startDate}}', '{{endDate}}', '{{dogs}}', '{{status}}', '{{total}}'].map(p => (
                          <code key={p} className="px-2 py-1 bg-slate-700 rounded text-xs text-blue-400">{p}</code>
                        ))}
                      </div>
                    </div>
                    <Button onClick={handleSaveTemplate} disabled={saving} className="w-full bg-blue-600 hover:bg-blue-700">
                      <SaveIcon size={16} className="mr-2" />
                      {saving ? 'Saving...' : 'Save Template'}
                    </Button>
                  </CardContent>
                </Card>
              </div>
            </div>
          </TabsContent>

          {/* Outbox Tab */}
          <TabsContent value="outbox">
            <Card className="bg-slate-900 border-slate-700">
              <CardHeader>
                <CardTitle className="text-white flex items-center gap-2">
                  <InboxIcon size={20} />
                  Email Outbox
                  {dataMode === 'mock' && (
                    <span className="text-xs px-2 py-1 bg-yellow-500/20 text-yellow-400 rounded-full ml-2">Mock Mode</span>
                  )}
                </CardTitle>
              </CardHeader>
              <CardContent>
                {outbox.length === 0 ? (
                  <div className="text-center py-12 text-slate-400">
                    <InboxIcon size={48} className="mx-auto mb-4 opacity-50" />
                    <p>No emails sent yet</p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {outbox.map((email) => (
                      <div key={email.id} className="bg-slate-800 rounded-lg p-4 border border-slate-700">
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-1">
                              <span className={`text-xs px-2 py-0.5 rounded-full ${
                                email.type === 'test' ? 'bg-purple-500/20 text-purple-400' :
                                email.type === 'booking_confirmation' ? 'bg-green-500/20 text-green-400' :
                                'bg-blue-500/20 text-blue-400'
                              }`}>
                                {email.type}
                              </span>
                              <span className="text-xs text-slate-500">{email.status}</span>
                            </div>
                            <p className="text-white font-medium">{email.subject}</p>
                            <p className="text-sm text-slate-400">To: {email.to}</p>
                          </div>
                          <div className="text-xs text-slate-500">
                            {new Date(email.sentAt).toLocaleString()}
                          </div>
                        </div>
                        <div className="mt-3 p-3 bg-slate-900 rounded text-sm text-slate-300 whitespace-pre-wrap max-h-32 overflow-y-auto">
                          {email.body}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </main>

      {/* Preview Modal */}
      <Dialog open={showPreview} onOpenChange={setShowPreview}>
        <DialogContent className="max-w-lg bg-slate-900 border-slate-700">
          <DialogHeader>
            <DialogTitle className="text-white">Email Preview</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="bg-slate-800 rounded-lg p-4">
              <Label className="text-slate-400 text-xs">Subject</Label>
              <p className="text-white font-medium mt-1">{preview.subject}</p>
            </div>
            <div className="bg-slate-800 rounded-lg p-4">
              <Label className="text-slate-400 text-xs">Body</Label>
              <div className="text-slate-300 mt-2 whitespace-pre-wrap text-sm">{preview.body}</div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowPreview(false)} className="border-slate-600 text-slate-300">
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Send Test Modal */}
      <Dialog open={showTestModal} onOpenChange={setShowTestModal}>
        <DialogContent className="max-w-sm bg-slate-900 border-slate-700">
          <DialogHeader>
            <DialogTitle className="text-white">Send Test Email</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <Label className="text-slate-300">Email Address</Label>
              <Input
                type="email"
                value={testEmail}
                onChange={(e) => setTestEmail(e.target.value)}
                placeholder="test@example.com"
                className="bg-slate-800 border-slate-700 text-white mt-1"
              />
            </div>
            <p className="text-sm text-slate-400">
              {dataMode === 'mock' 
                ? 'In mock mode, the email will be added to the outbox instead of being sent.'
                : 'This will send a real email via SMTP.'}
            </p>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowTestModal(false)} className="border-slate-600 text-slate-300">
              Cancel
            </Button>
            <Button onClick={handleSendTest} disabled={sendingTest} className="bg-blue-600 hover:bg-blue-700">
              <SendIcon size={16} className="mr-2" />
              {sendingTest ? 'Sending...' : 'Send Test'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default AdminEmailTemplatesPage;
