import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import useAuthStore from '../store/authStore';
import { dataClient, dataMode } from '../data/client';
import { Button } from '../components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Badge } from '../components/ui/badge';
import { ArrowLeftIcon, UsersIcon, CheckIcon, XIcon, UserPlusIcon, ShieldIcon, RefreshCwIcon } from 'lucide-react';
import { toast } from 'sonner';

const AdminStaffManagementPage = () => {
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [staffRequests, setStaffRequests] = useState([]);
  const [isOwner, setIsOwner] = useState(false);

  // Reject modal
  const [showRejectModal, setShowRejectModal] = useState(false);
  const [rejectingRequest, setRejectingRequest] = useState(null);
  const [rejectReason, setRejectReason] = useState('');
  const [rejecting, setRejecting] = useState(false);

  // Create admin modal
  const [showCreateAdminModal, setShowCreateAdminModal] = useState(false);
  const [adminForm, setAdminForm] = useState({ email: '', fullName: '' });
  const [creatingAdmin, setCreatingAdmin] = useState(false);

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
      const [requestsData, ownerStatus] = await Promise.all([
        dataClient.listStaffRequests(),
        dataClient.isOwner(user.id),
      ]);
      setStaffRequests(requestsData || []);
      setIsOwner(ownerStatus);
    } catch (error) {
      console.error('Failed to load data:', error);
      toast.error('Failed to load staff requests');
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (requestId) => {
    try {
      await dataClient.approveStaffRequest(requestId);
      toast.success('Staff request approved!');
      loadData();
    } catch (error) {
      toast.error(error.message || 'Failed to approve request');
    }
  };

  const openRejectModal = (request) => {
    setRejectingRequest(request);
    setRejectReason('');
    setShowRejectModal(true);
  };

  const handleReject = async () => {
    if (!rejectingRequest) return;
    setRejecting(true);
    try {
      await dataClient.rejectStaffRequest(rejectingRequest.id, rejectReason);
      toast.success('Staff request rejected');
      setShowRejectModal(false);
      setRejectingRequest(null);
      loadData();
    } catch (error) {
      toast.error(error.message || 'Failed to reject request');
    } finally {
      setRejecting(false);
    }
  };

  const handleCreateAdmin = async () => {
    if (!adminForm.email || !adminForm.fullName) {
      toast.error('Please fill in all fields');
      return;
    }
    setCreatingAdmin(true);
    try {
      await dataClient.createAdminAccount(adminForm);
      toast.success('Admin account created!');
      setShowCreateAdminModal(false);
      setAdminForm({ email: '', fullName: '' });
    } catch (error) {
      toast.error(error.message || 'Failed to create admin');
    } finally {
      setCreatingAdmin(false);
    }
  };

  const pendingRequests = staffRequests.filter(r => r.status === 'pending');
  const processedRequests = staffRequests.filter(r => r.status !== 'pending');

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-950">
        <div className="animate-spin h-8 w-8 border-2 border-blue-500 border-t-transparent rounded-full"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950">
      {/* Header */}
      <header className="bg-slate-900 border-b border-slate-700 px-6 py-4">
        <div className="max-w-5xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button variant="ghost" onClick={() => navigate('/admin/dashboard')} className="text-slate-400 hover:text-white">
              <ArrowLeftIcon size={20} />
            </Button>
            <div>
              <h1 className="text-2xl font-bold text-white flex items-center gap-2">
                <UsersIcon size={24} />
                Staff Management
              </h1>
              <p className="text-slate-400 text-sm">
                Approve staff requests • Mode: {dataMode}
                {isOwner && <span className="ml-2 text-yellow-400">(Owner)</span>}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" onClick={loadData} className="border-slate-600 text-slate-300">
              <RefreshCwIcon size={16} />
            </Button>
            {isOwner && (
              <Button onClick={() => setShowCreateAdminModal(true)} className="bg-yellow-600 hover:bg-yellow-700">
                <ShieldIcon size={16} className="mr-2" />
                Create Admin
              </Button>
            )}
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-8 space-y-6">
        {/* Pending Requests */}
        <Card className="bg-slate-900 border-slate-700">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <UserPlusIcon size={20} />
              Pending Staff Requests
              {pendingRequests.length > 0 && (
                <Badge className="bg-yellow-500/20 text-yellow-400 ml-2">{pendingRequests.length}</Badge>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {pendingRequests.length === 0 ? (
              <div className="text-center py-8 text-slate-400">
                <UsersIcon size={48} className="mx-auto mb-4 opacity-50" />
                <p>No pending staff requests</p>
              </div>
            ) : (
              <div className="space-y-3">
                {pendingRequests.map((request) => (
                  <div key={request.id} className="bg-slate-800 rounded-lg p-4 border border-slate-700 flex items-center justify-between">
                    <div>
                      <p className="text-white font-medium">{request.fullName || request.full_name}</p>
                      <p className="text-sm text-slate-400">{request.email}</p>
                      <p className="text-xs text-slate-500 mt-1">
                        Requested: {new Date(request.createdAt).toLocaleString()}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => openRejectModal(request)}
                        className="border-red-500/50 text-red-400 hover:bg-red-500/20"
                      >
                        <XIcon size={16} className="mr-1" />
                        Reject
                      </Button>
                      <Button
                        size="sm"
                        onClick={() => handleApprove(request.id)}
                        className="bg-green-600 hover:bg-green-700"
                      >
                        <CheckIcon size={16} className="mr-1" />
                        Approve
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Processed Requests History */}
        {processedRequests.length > 0 && (
          <Card className="bg-slate-900 border-slate-700">
            <CardHeader>
              <CardTitle className="text-white">Request History</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {processedRequests.map((request) => (
                  <div key={request.id} className="bg-slate-800 rounded-lg p-4 border border-slate-700 flex items-center justify-between">
                    <div>
                      <p className="text-white font-medium">{request.fullName || request.full_name}</p>
                      <p className="text-sm text-slate-400">{request.email}</p>
                      {request.reason && (
                        <p className="text-sm text-red-400 mt-1">Reason: {request.reason}</p>
                      )}
                    </div>
                    <Badge className={
                      request.status === 'approved' ? 'bg-green-500/20 text-green-400' :
                      request.status === 'rejected' ? 'bg-red-500/20 text-red-400' :
                      'bg-slate-500/20 text-slate-400'
                    }>
                      {request.status}
                    </Badge>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Owner Info Card */}
        {isOwner && (
          <Card className="bg-yellow-500/10 border-yellow-500/30">
            <CardContent className="p-4">
              <div className="flex items-start gap-3">
                <ShieldIcon size={20} className="text-yellow-500 shrink-0 mt-0.5" />
                <div>
                  <p className="font-medium text-yellow-400">Owner Privileges</p>
                  <p className="text-sm text-yellow-300/70">
                    As the first admin (owner), you can create new admin accounts. Other admins cannot create admin accounts.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </main>

      {/* Reject Modal */}
      <Dialog open={showRejectModal} onOpenChange={setShowRejectModal}>
        <DialogContent className="max-w-sm bg-slate-900 border-slate-700">
          <DialogHeader>
            <DialogTitle className="text-white">Reject Staff Request</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <p className="text-slate-300">
              Rejecting request from <strong>{rejectingRequest?.fullName || rejectingRequest?.full_name}</strong>
            </p>
            <div>
              <Label className="text-slate-300">Reason (optional)</Label>
              <Textarea
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                placeholder="Provide a reason for rejection..."
                className="bg-slate-800 border-slate-700 text-white mt-1"
                rows={3}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowRejectModal(false)} className="border-slate-600 text-slate-300">
              Cancel
            </Button>
            <Button onClick={handleReject} disabled={rejecting} className="bg-red-600 hover:bg-red-700">
              {rejecting ? 'Rejecting...' : 'Reject Request'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Create Admin Modal */}
      <Dialog open={showCreateAdminModal} onOpenChange={setShowCreateAdminModal}>
        <DialogContent className="max-w-sm bg-slate-900 border-slate-700">
          <DialogHeader>
            <DialogTitle className="text-white">Create Admin Account</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <Label className="text-slate-300">Full Name</Label>
              <Input
                value={adminForm.fullName}
                onChange={(e) => setAdminForm({ ...adminForm, fullName: e.target.value })}
                placeholder="John Doe"
                className="bg-slate-800 border-slate-700 text-white mt-1"
              />
            </div>
            <div>
              <Label className="text-slate-300">Email</Label>
              <Input
                type="email"
                value={adminForm.email}
                onChange={(e) => setAdminForm({ ...adminForm, email: e.target.value })}
                placeholder="admin@example.com"
                className="bg-slate-800 border-slate-700 text-white mt-1"
              />
            </div>
            <p className="text-sm text-slate-400">
              The new admin will receive an email with login instructions.
            </p>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCreateAdminModal(false)} className="border-slate-600 text-slate-300">
              Cancel
            </Button>
            <Button onClick={handleCreateAdmin} disabled={creatingAdmin} className="bg-yellow-600 hover:bg-yellow-700">
              <ShieldIcon size={16} className="mr-2" />
              {creatingAdmin ? 'Creating...' : 'Create Admin'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default AdminStaffManagementPage;
