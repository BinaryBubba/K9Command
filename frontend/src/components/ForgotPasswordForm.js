import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../utils/api';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { toast } from 'sonner';
import { ArrowLeftIcon, CheckCircleIcon } from 'lucide-react';

const ForgotPasswordForm = () => {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const handleRequestReset = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await api.post('/auth/forgot-password', { email });
      setSubmitted(true);
    } catch (error) {
      const errorMsg = error.response?.data?.detail || 'Failed to request reset';
      toast.error(typeof errorMsg === 'string' ? errorMsg : 'Failed to request reset');
    } finally {
      setLoading(false);
    }
  };

  if (submitted) return (
    <div className="w-full max-w-md space-y-6 text-center">
      <CheckCircleIcon size={48} className="mx-auto text-green-500" />
      <h2 className="text-2xl font-serif font-bold text-primary">Check your email</h2>
      <p className="text-muted-foreground">
        If an account exists for <strong>{email}</strong>, we've sent a password reset link.
        It's valid for 1 hour.
      </p>
      <Button variant="outline" className="w-full" onClick={() => navigate('/auth')}>
        Back to Login
      </Button>
    </div>
  );

  return (
    <div className="w-full max-w-md space-y-6">
      <Button
        variant="ghost"
        onClick={() => navigate('/auth')}
        className="flex items-center gap-2"
      >
        <ArrowLeftIcon size={18} />
        Back to Login
      </Button>

      <div className="text-center">
        <h2 className="text-3xl font-serif font-bold text-primary">Forgot Password?</h2>
        <p className="text-muted-foreground mt-2">
          Enter your email and we'll send you a link to reset your password.
        </p>
      </div>

      <form onSubmit={handleRequestReset} className="space-y-4">
        <div>
          <Label htmlFor="email">Email</Label>
          <Input
            id="email"
            data-testid="forgot-password-email-input"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className="mt-1"
          />
        </div>

        <Button
          data-testid="request-reset-button"
          type="submit"
          className="w-full rounded-full py-6 text-lg font-semibold"
          disabled={loading}
        >
          {loading ? 'Sending...' : 'Send Reset Link'}
        </Button>
      </form>
    </div>
  );
};

export default ForgotPasswordForm;
