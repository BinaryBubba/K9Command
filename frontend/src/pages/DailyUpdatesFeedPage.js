import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { ArrowLeftIcon, HeartIcon, ThumbsUpIcon, SmileIcon, DownloadIcon, ShoppingCartIcon, ImageIcon, MessageCircleIcon } from 'lucide-react';
import { toast } from 'sonner';
import api from '../utils/api';
import useAuthStore from '../store/authStore';

const DailyUpdatesFeedPage = () => {
  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);
  const [updates, setUpdates] = useState([]);
  const [selectedUpdate, setSelectedUpdate] = useState(null);
  const [comment, setComment] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user || user.role !== 'customer') {
      navigate('/auth');
      return;
    }
    fetchUpdates();
  }, [user, navigate]);

  const fetchUpdates = async () => {
    try {
      const response = await api.get('/daily-updates');
      // Only show sent updates for customers
      const sent = response.data.filter((u) => u.status === 'sent');
      setUpdates(sent);
    } catch (error) {
      toast.error('Failed to load updates');
    } finally {
      setLoading(false);
    }
  };

  const handleReaction = async (updateId, emoji) => {
    try {
      await api.post(`/daily-updates/${updateId}/reactions?reaction=${emoji}`);
      toast.success('Reaction added!');
      fetchUpdates();
    } catch (error) {
      toast.error('Failed to add reaction');
    }
  };

  const handleComment = async (updateId) => {
    if (!comment.trim()) {
      toast.error('Please enter a comment');
      return;
    }

    try {
      await api.post(`/daily-updates/${updateId}/comments?text=${encodeURIComponent(comment)}`);
      toast.success('Comment added!');
      setComment('');
      fetchUpdates();
    } catch (error) {
      toast.error('Failed to add comment');
    }
  };

  const handleDownloadPhoto = (photoUrl) => {
    // Simple download - in production, this would download actual file
    toast.info('Downloading photo... (watermarked)');
  };

  const handlePurchasePhotos = async (updateId) => {
    try {
      const response = await api.post(`/daily-updates/${updateId}/purchase-photos`, {
        payment_method: 'credit_card',
      });
      toast.success(`Photos purchased for $${response.data.amount}! Watermarks removed.`);
      fetchUpdates();
    } catch (error) {
      toast.error('Failed to purchase photos');
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div>
          <p className="mt-4 text-muted-foreground">Loading updates...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#F9F7F2]">
      <header className="bg-white border-b border-border/40 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 md:px-8 py-4">
          <Button
            data-testid="back-to-dashboard-button"
            variant="ghost"
            onClick={() => navigate('/customer/dashboard')}
            className="flex items-center gap-2 mb-2"
          >
            <ArrowLeftIcon size={18} />
            Back to Dashboard
          </Button>
          <h1 className="text-3xl font-serif font-bold text-primary">Daily Updates</h1>
          <p className="text-muted-foreground mt-1">See what your pups have been up to!</p>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 md:px-8 py-8">
        {updates.length === 0 ? (
          <Card className="bg-white rounded-2xl border border-border/50 shadow-sm">
            <CardContent className="p-12 text-center">
              <ImageIcon size={48} className="mx-auto text-muted-foreground/50 mb-4" />
              <p className="text-muted-foreground">No updates yet. Book a stay to receive daily photo updates!</p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-6">
            {updates.map((update) => (
              <Card
                key={update.id}
                data-testid={`update-card-${update.id}`}
                className="bg-white rounded-2xl border border-border/50 shadow-sm overflow-hidden"
              >
                {/* Header */}
                <CardHeader className="border-b border-border/40 bg-gradient-to-r from-primary/5 to-secondary/5">
                  <div className="flex justify-between items-start">
                    <div>
                      <CardTitle className="text-2xl font-serif">
                        {new Date(update.date).toLocaleDateString('en-US', {
                          weekday: 'long',
                          year: 'numeric',
                          month: 'long',
                          day: 'numeric',
                        })}
                      </CardTitle>
                      <p className="text-sm text-muted-foreground mt-1">
                        {update.media_items?.length || 0} photos • Sent at{' '}
                        {new Date(update.sent_at).toLocaleTimeString()}
                      </p>
                    </div>
                    {!update.media_items?.[0]?.purchased && (
                      <Button
                        data-testid={`purchase-photos-${update.id}`}
                        onClick={() => handlePurchasePhotos(update.id)}
                        size="sm"
                        className="rounded-full"
                      >
                        <ShoppingCartIcon size={16} className="mr-2" />
                        Buy Photos $9.99
                      </Button>
                    )}
                  </div>
                </CardHeader>

                <CardContent className="p-6 space-y-6">
                  {/* AI Summary */}
                  {update.ai_summary && (
                    <div className="p-4 rounded-xl bg-primary/5 border border-primary/20">
                      <p className="text-lg leading-relaxed">{update.ai_summary}</p>
                    </div>
                  )}

                  {/* Photos Grid */}
                  {update.media_items && update.media_items.length > 0 && (
                    <div>
                      <h3 className="font-semibold text-lg mb-3">Photos & Videos</h3>
                      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                        {update.media_items.map((media, index) => (
                          <div
                            key={index}
                            data-testid={`media-item-${index}`}
                            className="relative aspect-square rounded-lg overflow-hidden bg-muted group"
                          >
                            {/* Placeholder for photo */}
                            <div className="w-full h-full flex items-center justify-center border border-border">
                              <ImageIcon size={32} className="text-muted-foreground" />
                            </div>

                            {/* Watermark overlay */}
                            {media.watermarked && !media.purchased && (
                              <div className="absolute inset-0 flex items-center justify-center bg-black/20 pointer-events-none">
                                <p className="text-white font-bold text-2xl opacity-50 transform rotate-[-30deg]">
                                  WATERMARK
                                </p>
                              </div>
                            )}

                            {/* Download button */}
                            <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
                              <Button
                                data-testid={`download-photo-${index}`}
                                onClick={() => handleDownloadPhoto(media.url)}
                                size="sm"
                                className="rounded-full h-8 w-8 p-0"
                              >
                                <DownloadIcon size={16} />
                              </Button>
                            </div>

                            {/* Caption */}
                            {media.caption && (
                              <div className="absolute bottom-0 left-0 right-0 bg-black/70 text-white p-2 text-xs">
                                {media.caption}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Reactions */}
                  <div className="border-t border-border/40 pt-4">
                    <div className="flex items-center gap-3 mb-3">
                      <p className="text-sm font-medium text-muted-foreground">
                        {update.reactions?.length || 0} reactions
                      </p>
                    </div>
                    <div className="flex gap-2">
                      <Button
                        data-testid={`react-heart-${update.id}`}
                        onClick={() => handleReaction(update.id, '❤️')}
                        variant="outline"
                        size="sm"
                        className="rounded-full"
                      >
                        <HeartIcon size={16} className="mr-1" />
                        ❤️
                      </Button>
                      <Button
                        data-testid={`react-thumbs-${update.id}`}
                        onClick={() => handleReaction(update.id, '👍')}
                        variant="outline"
                        size="sm"
                        className="rounded-full"
                      >
                        <ThumbsUpIcon size={16} className="mr-1" />
                        👍
                      </Button>
                      <Button
                        data-testid={`react-smile-${update.id}`}
                        onClick={() => handleReaction(update.id, '😊')}
                        variant="outline"
                        size="sm"
                        className="rounded-full"
                      >
                        <SmileIcon size={16} className="mr-1" />
                        😊
                      </Button>
                    </div>
                  </div>

                  {/* Comments */}
                  <div className="border-t border-border/40 pt-4">
                    <h4 className="font-semibold mb-3 flex items-center gap-2">
                      <MessageCircleIcon size={18} />
                      Comments ({update.comments?.length || 0})
                    </h4>

                    {/* Existing Comments */}
                    {update.comments && update.comments.length > 0 && (
                      <div className="space-y-3 mb-4">
                        {update.comments.map((comment, index) => (
                          <div
                            key={index}
                            data-testid={`comment-${index}`}
                            className="p-3 rounded-lg bg-muted/50"
                          >
                            <p className="font-semibold text-sm">{comment.user_name}</p>
                            <p className="text-sm mt-1">{comment.text}</p>
                            <p className="text-xs text-muted-foreground mt-1">
                              {new Date(comment.timestamp).toLocaleString()}
                            </p>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Add Comment */}
                    <div className="flex gap-2">
                      <Input
                        data-testid={`comment-input-${update.id}`}
                        value={comment}
                        onChange={(e) => setComment(e.target.value)}
                        placeholder="Add a comment..."
                        className="flex-1"
                        onKeyPress={(e) => {
                          if (e.key === 'Enter') {
                            handleComment(update.id);
                          }
                        }}
                      />
                      <Button
                        data-testid={`submit-comment-${update.id}`}
                        onClick={() => handleComment(update.id)}
                        className="rounded-full"
                      >
                        Post
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </main>
    </div>
  );
};

export default DailyUpdatesFeedPage;
