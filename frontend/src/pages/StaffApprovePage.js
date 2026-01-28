import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { ArrowLeftIcon, SparklesIcon, SendIcon, ImageIcon, CheckCircleIcon } from 'lucide-react';
import { toast } from 'sonner';
import api from '../utils/api';

const StaffApprovePage = () => {
  const navigate = useNavigate();
  const [dailyUpdates, setDailyUpdates] = useState([]);
  const [selectedUpdate, setSelectedUpdate] = useState(null);
  const [generating, setGenerating] = useState(false);
  const [sending, setSending] = useState(false);

  useEffect(() => {
    fetchDailyUpdates();
  }, []);

  const fetchDailyUpdates = async () => {
    try {
      const response = await api.get('/daily-updates');
      const pending = response.data.filter(
        (u) => u.status === 'draft' || u.status === 'pending_approval'
      );
      setDailyUpdates(pending);
    } catch (error) {
      toast.error('Failed to load daily updates');
    }
  };

  const selectUpdate = (update) => {
    setSelectedUpdate(update);
  };

  const handleGenerateSummary = async () => {
    if (!selectedUpdate) return;

    if (!selectedUpdate.staff_snippets || selectedUpdate.staff_snippets.length === 0) {
      toast.error('No staff notes available. Please add notes first.');
      return;
    }

    setGenerating(true);
    try {
      await api.post(`/daily-updates/${selectedUpdate.id}/generate-summary`);
      toast.success('AI summary generated!');
      
      const updatedResponse = await api.get('/daily-updates');
      const updated = updatedResponse.data.find((u) => u.id === selectedUpdate.id);
      setSelectedUpdate(updated);
      fetchDailyUpdates();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to generate summary');
    } finally {
      setGenerating(false);
    }
  };

  const handleApproveAndSend = async () => {
    if (!selectedUpdate) return;

    if (!selectedUpdate.ai_summary) {
      toast.error('Please generate AI summary first');
      return;
    }

    setSending(true);
    try {
      await api.post(`/daily-updates/${selectedUpdate.id}/approve`);
      toast.success('Update approved and sent to customer!');
      fetchDailyUpdates();
      setSelectedUpdate(null);
    } catch (error) {
      toast.error('Failed to send update');
    } finally {
      setSending(false);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'draft':
        return 'bg-gray-100 text-gray-800';
      case 'pending_approval':
        return 'bg-yellow-100 text-yellow-800';
      case 'sent':
        return 'bg-green-100 text-green-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="min-h-screen bg-[#F9F7F2]">
      <header className="bg-white border-b border-border/40 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 md:px-8 py-4">
          <Button
            data-testid="back-to-dashboard-button"
            variant="ghost"
            onClick={() => navigate('/staff/dashboard')}
            className="flex items-center gap-2 mb-2"
          >
            <ArrowLeftIcon size={18} />
            Back to Dashboard
          </Button>
          <h1 className="text-3xl font-serif font-bold text-primary">Review & Approve Updates</h1>
          <p className="text-muted-foreground mt-1">Generate AI summaries and send updates to customers</p>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 md:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card data-testid="updates-list-card" className="bg-white rounded-2xl border border-border/50 shadow-sm">
            <CardHeader className="border-b border-border/40">
              <CardTitle className="text-2xl font-serif">Pending Updates</CardTitle>
            </CardHeader>
            <CardContent className="p-6">
              {dailyUpdates.length === 0 ? (
                <div className="text-center py-12">
                  <CheckCircleIcon size={48} className="mx-auto text-green-500 mb-4" />
                  <p className="text-muted-foreground">All updates have been sent!</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {dailyUpdates.map((update) => (
                    <div
                      key={update.id}
                      data-testid={`update-item-${update.id}`}
                      className={`p-4 rounded-xl border-2 cursor-pointer transition-all ${
                        selectedUpdate?.id === update.id
                          ? 'border-primary bg-primary/5'
                          : 'border-border hover:border-primary/50'
                      }`}
                      onClick={() => selectUpdate(update)}
                    >
                      <div className="flex justify-between items-start mb-2">
                        <div>
                          <h3 className="font-semibold text-lg">Update #{update.id.slice(0, 8)}</h3>
                          <p className="text-sm text-muted-foreground">
                            {new Date(update.date).toLocaleDateString()}
                          </p>
                        </div>
                        <Badge className={getStatusColor(update.status)}>
                          {update.status.replace('_', ' ')}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-4 text-sm text-muted-foreground">
                        <span>{update.media_items?.length || 0} photos</span>
                        <span>•</span>
                        <span>{update.staff_snippets?.length || 0} staff notes</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          <div className="space-y-6">
            {selectedUpdate ? (
              <>
                <Card data-testid="staff-notes-card" className="bg-white rounded-2xl border border-border/50 shadow-sm">
                  <CardHeader className="border-b border-border/40">
                    <CardTitle className="text-2xl font-serif">Staff Notes</CardTitle>
                  </CardHeader>
                  <CardContent className="p-6">
                    {!selectedUpdate.staff_snippets || selectedUpdate.staff_snippets.length === 0 ? (
                      <p className="text-center text-muted-foreground py-8">No staff notes yet</p>
                    ) : (
                      <div className="space-y-4">
                        {selectedUpdate.staff_snippets.map((snippet, index) => (
                          <div
                            key={index}
                            data-testid={`snippet-${index}`}
                            className="p-4 rounded-xl bg-muted/50 border border-border"
                          >
                            <div className="flex justify-between items-start mb-2">
                              <p className="font-semibold">{snippet.staff_name}</p>
                              <p className="text-xs text-muted-foreground">
                                {new Date(snippet.timestamp).toLocaleTimeString()}
                              </p>
                            </div>
                            <p className="text-sm">{snippet.text}</p>
                          </div>
                        ))}
                      </div>
                    )}
                  </CardContent>
                </Card>

                <Card data-testid="photos-card" className="bg-white rounded-2xl border border-border/50 shadow-sm">
                  <CardHeader className="border-b border-border/40">
                    <CardTitle className="text-2xl font-serif">Photos & Videos</CardTitle>
                  </CardHeader>
                  <CardContent className="p-6">
                    {!selectedUpdate.media_items || selectedUpdate.media_items.length === 0 ? (
                      <p className="text-center text-muted-foreground py-8">No photos uploaded yet</p>
                    ) : (
                      <div>
                        <p className="text-lg font-semibold mb-4">{selectedUpdate.media_items.length} photo(s) uploaded</p>
                        <div className="grid grid-cols-3 gap-3">
                          {selectedUpdate.media_items.slice(0, 6).map((media, index) => (
                            <div
                              key={index}
                              className="aspect-square rounded-lg bg-muted flex items-center justify-center border border-border"
                            >
                              <ImageIcon size={24} className="text-muted-foreground" />
                            </div>
                          ))}
                        </div>
                        {selectedUpdate.media_items.length > 6 && (
                          <p className="text-sm text-muted-foreground mt-3 text-center">
                            +{selectedUpdate.media_items.length - 6} more
                          </p>
                        )}
                      </div>
                    )}
                  </CardContent>
                </Card>

                <Card data-testid="ai-summary-card" className="bg-white rounded-2xl border border-border/50 shadow-sm">
                  <CardHeader className="border-b border-border/40">
                    <CardTitle className="text-2xl font-serif flex items-center gap-2">
                      <SparklesIcon className="text-primary" />
                      AI-Generated Summary
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-6">
                    {selectedUpdate.ai_summary ? (
                      <div className="space-y-4">
                        <div className="p-4 rounded-xl bg-primary/5 border border-primary/20">
                          <p className="text-lg leading-relaxed">{selectedUpdate.ai_summary}</p>
                        </div>
                        <Button
                          data-testid="regenerate-summary-button"
                          onClick={handleGenerateSummary}
                          disabled={generating}
                          variant="outline"
                          className="w-full rounded-full"
                        >
                          <SparklesIcon size={18} className="mr-2" />
                          {generating ? 'Regenerating...' : 'Regenerate Summary'}
                        </Button>
                      </div>
                    ) : (
                      <div className="text-center py-8">
                        <SparklesIcon size={48} className="mx-auto text-muted-foreground/50 mb-4" />
                        <p className="text-muted-foreground mb-4">Summary not generated yet</p>
                        <Button
                          data-testid="generate-summary-button"
                          onClick={handleGenerateSummary}
                          disabled={generating}
                          className="rounded-full px-8"
                        >
                          <SparklesIcon size={18} className="mr-2" />
                          {generating ? 'Generating...' : 'Generate AI Summary'}
                        </Button>
                      </div>
                    )}
                  </CardContent>
                </Card>

                {selectedUpdate.ai_summary && (
                  <Card className="bg-gradient-to-br from-primary to-primary/80 text-white rounded-2xl">
                    <CardContent className="p-6">
                      <h3 className="text-xl font-serif font-bold mb-2">Ready to Send?</h3>
                      <p className="mb-4 opacity-90">
                        This will send the daily update with photos and summary to the customer.
                      </p>
                      <Button
                        data-testid="approve-send-button"
                        onClick={handleApproveAndSend}
                        disabled={sending}
                        variant="secondary"
                        className="w-full py-6 text-lg font-semibold rounded-full"
                      >
                        <SendIcon size={20} className="mr-2" />
                        {sending ? 'Sending...' : 'Approve & Send Update'}
                      </Button>
                    </CardContent>
                  </Card>
                )}
              </>
            ) : (
              <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
                <CardContent className="p-12 text-center">
                  <SparklesIcon size={48} className="mx-auto text-muted-foreground/50 mb-4" />
                  <p className="text-muted-foreground">Select an update to review and approve</p>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </main>
    </div>
  );
};

export default StaffApprovePage;
