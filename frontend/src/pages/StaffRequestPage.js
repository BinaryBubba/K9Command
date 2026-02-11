import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { ArrowLeftIcon, UserPlusIcon, CheckCircleIcon } from 'lucide-react';
import { toast } from 'sonner';
import api from '../utils/api';

/**
 * Staff Request Page
 * 
 * ROLE GOVERNANCE:
 * - Staff accounts require admin approval
 * - This page submits a request that goes to admin for review
 * - Account is NOT created until admin approves
 */
const StaffRequestPage = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [formData, setFormData] = useState({
    full_name: '',
    email: '',
    phone: '',
    password: '',
    confirmPassword: '',
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (formData.password !== formData.confirmPassword) {
      toast.error('Passwords do not match');
      return;
    }
    
    if (formData.password.length < 8) {
      toast.error('Password must be at least 8 characters');
      return;
    }
    
    setLoading(true);
    try {
      // Submit as staff role - backend will create a pending request
      await api.post('/auth/register', {
        ...formData,
        role: 'staff'
      });
      
      // If we get here, something unexpected happened
      // The backend should return 202 for staff requests
      setSubmitted(true);
    } catch (error) {
      if (error.response?.status === 202) {
        // Expected response - request submitted successfully
        setSubmitted(true);
        toast.success('Request submitted successfully!');
      } else {
        toast.error(error.response?.data?.detail || 'Failed to submit request');
      }
    } finally {
      setLoading(false);
    }
  };

  if (submitted) {
    return (
      <div className="min-h-screen bg-[#F9F7F2] flex items-center justify-center p-4">
        <Card className="max-w-md w-full bg-white rounded-2xl border border-border/50 shadow-lg">
          <CardContent className="p-8 text-center">
            <div className="w-16 h-16 rounded-full bg-green-100 mx-auto mb-6 flex items-center justify-center">
              <CheckCircleIcon className="text-green-600" size={32} />
            </div>
            <h2 className="text-2xl font-serif font-bold text-primary mb-4">Request Submitted!</h2>
            <p className="text-muted-foreground mb-6">
              Your staff access request has been submitted for review. 
              An administrator will review your application and you'll receive 
              an email once your account is approved.
            </p>
            <Button onClick={() => navigate('/auth')} className="w-full rounded-full">
              Return to Login
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#F9F7F2]">
      <header className="bg-white border-b border-border/40 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 md:px-8 py-4">
          <Button variant="ghost" onClick={() => navigate('/auth')} className="flex items-center gap-2">
            <ArrowLeftIcon size={18} /> Back to Login
          </Button>
        </div>
      </header>

      <main className="max-w-md mx-auto px-4 py-12">
        <Card className="bg-white rounded-2xl border border-border/50 shadow-lg">
          <CardHeader className="text-center pb-2">
            <div className="w-16 h-16 rounded-full bg-primary/10 mx-auto mb-4 flex items-center justify-center">
              <UserPlusIcon className="text-primary" size={32} />
            </div>
            <CardTitle className="text-2xl font-serif">Request Staff Access</CardTitle>
            <p className="text-sm text-muted-foreground mt-2">
              Submit your information to request a staff account. 
              An administrator will review and approve your request.
            </p>
          </CardHeader>
          <CardContent className="p-6">
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <Label htmlFor="full_name">Full Name *</Label>
                <Input
                  id="full_name"
                  value={formData.full_name}
                  onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                  required
                  className="mt-1"
                  placeholder="John Doe"
                />
              </div>
              
              <div>
                <Label htmlFor="email">Email *</Label>
                <Input
                  id="email"
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  required
                  className="mt-1"
                  placeholder="john@example.com"
                />
              </div>
              
              <div>
                <Label htmlFor="phone">Phone</Label>
                <Input
                  id="phone"
                  type="tel"
                  value={formData.phone}
                  onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                  className="mt-1"
                  placeholder="(555) 123-4567"
                />
              </div>
              
              <div>
                <Label htmlFor="password">Password *</Label>
                <Input
                  id="password"
                  type="password"
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  required
                  className="mt-1"
                  placeholder="At least 8 characters"
                />
              </div>
              
              <div>
                <Label htmlFor="confirmPassword">Confirm Password *</Label>
                <Input
                  id="confirmPassword"
                  type="password"
                  value={formData.confirmPassword}
                  onChange={(e) => setFormData({ ...formData, confirmPassword: e.target.value })}
                  required
                  className="mt-1"
                />
              </div>
              
              <Button 
                type="submit" 
                className="w-full rounded-full py-6 text-lg font-semibold mt-6"
                disabled={loading}
              >
                {loading ? 'Submitting...' : 'Submit Request'}
              </Button>
            </form>
          </CardContent>
        </Card>
      </main>
    </div>
  );
};

export default StaffRequestPage;
