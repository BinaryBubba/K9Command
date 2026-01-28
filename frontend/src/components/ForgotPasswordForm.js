import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { API } from '../utils/api';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Card, CardContent } from './ui/card';
import { toast } from 'sonner';
import { ArrowLeftIcon } from 'lucide-react';

const ForgotPasswordForm = () => {
  const navigate = useNavigate();
  const [step, setStep] = useState(1); // 1: Email, 2: Token & New Password
  const [email, setEmail] = useState('');
  const [resetToken, setResetToken] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const handleRequestReset = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const response = await axios.post(`${API}/auth/forgot-password?email=${email}`);
      toast.success('Reset token generated! Check the response below.');
      
      // Show token (in production, this would be sent via email)
      if (response.data.reset_token) {
        toast.info(`Reset Token: ${response.data.reset_token}`, { duration: 10000 });
        setResetToken(response.data.reset_token);
      }
      
      setStep(2);
    } catch (error) {
      toast.error('Failed to request reset');
    } finally {
      setLoading(false);
    }
  };

  const handleResetPassword = async (e) => {
    e.preventDefault();

    if (newPassword !== confirmPassword) {
      toast.error('Passwords do not match');
      return;
    }

    if (newPassword.length < 6) {
      toast.error('Password must be at least 6 characters');
      return;
    }

    setLoading(true);

    try {
      await axios.post(`${API}/auth/reset-password`, {
        reset_token: resetToken,
        new_password: newPassword,
      });
      toast.success('Password reset successful! You can now login.');
      navigate('/auth');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to reset password');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full max-w-md space-y-6">
      <Button
        variant="ghost"
        onClick={() => step === 1 ? navigate('/auth') : setStep(1)}
        className="flex items-center gap-2"
      >
        <ArrowLeftIcon size={18} />
        {step === 1 ? 'Back to Login' : 'Back'}
      </Button>

      <div className="text-center">
        <h2 className="text-3xl font-serif font-bold text-primary">
          {step === 1 ? 'Forgot Password?' : 'Reset Password'}
        </h2>
        <p className="text-muted-foreground mt-2">
          {step === 1
            ? "Enter your email to receive a reset token"
            : 'Enter your reset token and new password'}
        </p>
      </div>

      {step === 1 ? (
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
            {loading ? 'Sending...' : 'Send Reset Token'}
          </Button>
        </form>
      ) : (
        <form onSubmit={handleResetPassword} className="space-y-4">
          <Card className="bg-blue-50 border-blue-200">
            <CardContent className="p-4">
              <p className="text-sm text-blue-900">
                <strong>Note:</strong> In production, the reset token would be sent to your email.
                For this demo, the token is displayed above.
              </p>
            </CardContent>
          </Card>

          <div>
            <Label htmlFor="resetToken">Reset Token</Label>
            <Input
              id="resetToken"
              data-testid="reset-token-input"
              value={resetToken}
              onChange={(e) => setResetToken(e.target.value)}
              required
              className="mt-1"
            />
          </div>

          <div>
            <Label htmlFor="newPassword">New Password</Label>
            <Input
              id="newPassword"
              data-testid="new-password-input"
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              required
              className="mt-1"
            />
          </div>

          <div>
            <Label htmlFor="confirmPassword">Confirm Password</Label>
            <Input
              id="confirmPassword"
              data-testid="confirm-password-input"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              className="mt-1"
            />
          </div>

          <Button
            data-testid="reset-password-button"
            type="submit"
            className="w-full rounded-full py-6 text-lg font-semibold"
            disabled={loading}
          >
            {loading ? 'Resetting...' : 'Reset Password'}
          </Button>
        </form>
      )}
    </div>
  );
};

export default ForgotPasswordForm;
