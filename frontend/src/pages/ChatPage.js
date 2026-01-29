import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { ArrowLeftIcon, SendIcon, MessageCircleIcon, UserIcon, PlusIcon } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { toast } from 'sonner';
import api from '../utils/api';
import useAuthStore from '../store/authStore';

const ChatPage = () => {
  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);
  const [chats, setChats] = useState([]);
  const [selectedChat, setSelectedChat] = useState(null);
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [availableUsers, setAvailableUsers] = useState([]);
  const [newChatModalOpen, setNewChatModalOpen] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    if (!user) {
      navigate('/auth');
      return;
    }
    fetchChats();
    fetchAvailableUsers();
  }, [user, navigate]);

  useEffect(() => {
    if (selectedChat) {
      fetchMessages(selectedChat.id);
      const interval = setInterval(() => fetchMessages(selectedChat.id), 5000);
      return () => clearInterval(interval);
    }
  }, [selectedChat]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const fetchChats = async () => {
    try {
      const response = await api.get('/chats');
      setChats(response.data);
    } catch (error) {
      toast.error('Failed to load chats');
    } finally {
      setLoading(false);
    }
  };

  const fetchAvailableUsers = async () => {
    try {
      const response = await api.get('/chat/users');
      setAvailableUsers(response.data);
    } catch (error) {
      console.error('Failed to load users');
    }
  };

  const fetchMessages = async (chatId) => {
    try {
      const response = await api.get(`/chats/${chatId}/messages`);
      setMessages(response.data);
    } catch (error) {
      console.error('Failed to load messages');
    }
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!newMessage.trim() || !selectedChat) return;

    setSending(true);
    try {
      await api.post(`/chats/${selectedChat.id}/messages`, {
        chat_id: selectedChat.id,
        content: newMessage.trim(),
      });
      setNewMessage('');
      fetchMessages(selectedChat.id);
      fetchChats();
    } catch (error) {
      toast.error('Failed to send message');
    } finally {
      setSending(false);
    }
  };

  const handleStartChat = async (participantId) => {
    try {
      const chatType = user.role === 'customer' ? 'kennel_customer' : 'admin_staff';
      const response = await api.post('/chats', {
        chat_type: chatType,
        participant_id: participantId,
      });
      setSelectedChat(response.data);
      setNewChatModalOpen(false);
      fetchChats();
    } catch (error) {
      toast.error('Failed to start chat');
    }
  };

  const getOtherParticipantName = (chat) => {
    const otherParticipantId = chat.participants.find(p => p !== user.id);
    return chat.participant_names?.[otherParticipantId] || 'Unknown';
  };

  const getUnreadCount = (chat) => {
    return chat.unread_count?.[user.id] || 0;
  };

  const getDashboardPath = () => {
    if (user.role === 'admin') return '/admin/dashboard';
    if (user.role === 'staff') return '/staff/dashboard';
    return '/customer/dashboard';
  };

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
            onClick={() => navigate(getDashboardPath())}
            className="flex items-center gap-2 mb-2"
          >
            <ArrowLeftIcon size={18} />
            Back to Dashboard
          </Button>
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-serif font-bold text-primary">Messages</h1>
              <p className="text-muted-foreground mt-1">
                {user.role === 'customer' ? 'Chat with the kennel' : 'Internal communication'}
              </p>
            </div>
            <Button
              data-testid="new-chat-btn"
              onClick={() => setNewChatModalOpen(true)}
              className="rounded-full"
            >
              <PlusIcon size={18} className="mr-2" />
              New Chat
            </Button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 md:px-8 py-8">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 h-[calc(100vh-250px)]">
          {/* Chat List */}
          <Card className="bg-white rounded-2xl border border-border/50 shadow-sm overflow-hidden">
            <CardHeader className="border-b border-border/40 py-4">
              <CardTitle className="text-lg font-serif">Conversations</CardTitle>
            </CardHeader>
            <CardContent className="p-0 overflow-y-auto h-[calc(100%-60px)]">
              {chats.length === 0 ? (
                <div className="p-6 text-center">
                  <MessageCircleIcon size={40} className="mx-auto text-muted-foreground/50 mb-3" />
                  <p className="text-muted-foreground text-sm">No conversations yet</p>
                  <Button
                    variant="link"
                    onClick={() => setNewChatModalOpen(true)}
                    className="mt-2"
                  >
                    Start a new chat
                  </Button>
                </div>
              ) : (
                <div className="divide-y divide-border">
                  {chats.map((chat) => (
                    <div
                      key={chat.id}
                      data-testid={`chat-${chat.id}`}
                      onClick={() => setSelectedChat(chat)}
                      className={`p-4 cursor-pointer hover:bg-muted/30 transition-colors ${selectedChat?.id === chat.id ? 'bg-primary/5 border-l-4 border-primary' : ''}`}
                    >
                      <div className="flex items-start gap-3">
                        <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                          <UserIcon className="text-primary" size={18} />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between">
                            <h4 className="font-semibold truncate">{getOtherParticipantName(chat)}</h4>
                            {getUnreadCount(chat) > 0 && (
                              <Badge className="bg-primary text-white text-xs">{getUnreadCount(chat)}</Badge>
                            )}
                          </div>
                          <p className="text-sm text-muted-foreground truncate">
                            {chat.last_message || 'No messages yet'}
                          </p>
                          {chat.last_message_at && (
                            <p className="text-xs text-muted-foreground mt-1">
                              {new Date(chat.last_message_at).toLocaleString()}
                            </p>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Chat Messages */}
          <Card className="md:col-span-2 bg-white rounded-2xl border border-border/50 shadow-sm overflow-hidden flex flex-col">
            {selectedChat ? (
              <>
                <CardHeader className="border-b border-border/40 py-4">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
                      <UserIcon className="text-primary" size={18} />
                    </div>
                    <div>
                      <CardTitle className="text-lg font-serif">{getOtherParticipantName(selectedChat)}</CardTitle>
                      <p className="text-xs text-muted-foreground capitalize">
                        {selectedChat.chat_type.replace('_', ' ')}
                      </p>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="flex-1 overflow-y-auto p-4 space-y-4">
                  {messages.length === 0 ? (
                    <div className="h-full flex items-center justify-center">
                      <p className="text-muted-foreground">No messages yet. Say hello!</p>
                    </div>
                  ) : (
                    messages.map((msg) => (
                      <div
                        key={msg.id}
                        className={`flex ${msg.sender_id === user.id ? 'justify-end' : 'justify-start'}`}
                      >
                        <div
                          className={`max-w-[70%] p-3 rounded-2xl ${msg.sender_id === user.id
                              ? 'bg-primary text-white rounded-br-sm'
                              : 'bg-muted rounded-bl-sm'
                            }`}
                        >
                          <p className="text-sm">{msg.content}</p>
                          <p className={`text-xs mt-1 ${msg.sender_id === user.id ? 'text-white/70' : 'text-muted-foreground'}`}>
                            {new Date(msg.created_at).toLocaleTimeString()}
                          </p>
                        </div>
                      </div>
                    ))
                  )}
                  <div ref={messagesEndRef} />
                </CardContent>
                <div className="border-t border-border/40 p-4">
                  <form onSubmit={handleSendMessage} className="flex gap-2">
                    <Input
                      data-testid="message-input"
                      value={newMessage}
                      onChange={(e) => setNewMessage(e.target.value)}
                      placeholder="Type a message..."
                      className="flex-1"
                    />
                    <Button
                      data-testid="send-message-btn"
                      type="submit"
                      disabled={sending || !newMessage.trim()}
                      className="rounded-full px-6"
                    >
                      <SendIcon size={18} />
                    </Button>
                  </form>
                </div>
              </>
            ) : (
              <div className="h-full flex items-center justify-center">
                <div className="text-center">
                  <MessageCircleIcon size={64} className="mx-auto text-muted-foreground/30 mb-4" />
                  <p className="text-muted-foreground">Select a conversation to start messaging</p>
                </div>
              </div>
            )}
          </Card>
        </div>
      </main>

      {/* New Chat Modal */}
      <Dialog open={newChatModalOpen} onOpenChange={setNewChatModalOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Start New Conversation</DialogTitle>
          </DialogHeader>
          <div className="space-y-2 max-h-[400px] overflow-y-auto">
            {availableUsers.length === 0 ? (
              <p className="text-center text-muted-foreground py-8">No users available for chat</p>
            ) : (
              availableUsers.map((u) => (
                <div
                  key={u.id}
                  data-testid={`user-${u.id}`}
                  onClick={() => handleStartChat(u.id)}
                  className="p-4 rounded-xl border border-border hover:border-primary/50 hover:bg-muted/30 cursor-pointer transition-all"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
                      <UserIcon className="text-primary" size={18} />
                    </div>
                    <div>
                      <h4 className="font-semibold">{u.full_name}</h4>
                      <p className="text-sm text-muted-foreground capitalize">{u.role}</p>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default ChatPage;
