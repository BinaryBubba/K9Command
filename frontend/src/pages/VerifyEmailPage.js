import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import api from '../utils/api';
import { Button } from '../components/ui/button';
import { CheckCircleIcon, XCircleIcon } from 'lucide-react';

const VerifyEmailPage = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');

  const [status, setStatus] = useState('loading'); // 'loading' | 'success' | 'error'
  const [message, setMessage] = useState('');

  useEffect(() => {
    if (!token) {
      setStatus('error');
      setMessage('This verification link is missing its token.');
      return;
    }
    api.post('/auth/verify-email', { token })
      .then(res => {
        setStatus('success');
        setMessage(res.data?.message || 'Email verified successfully!');
      })
      .catch(err => {
        setStatus('error');
        setMessage(err.response?.data?.detail || 'Failed to verify email. The link may have expired.');
      });
  }, [token]);

  return (
    <div className="min-h-screen bg-[#F9F7F2] flex items-center justify-center p-4">
      <div className="w-full max-w-md space-y-6 text-center">
        {status === 'loading' && (
          <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-primary mx-auto"></div>
        )}
        {status === 'success' && (
          <>
            <CheckCircleIcon size={48} className="mx-auto text-green-500" />
            <h2 className="text-2xl font-serif font-bold text-primary">Email Verified!</h2>
            <p className="text-muted-foreground">{message}</p>
            <Button className="w-full" onClick={() => navigate('/customer/dashboard')}>
              Go to Dashboard
            </Button>
          </>
        )}
        {status === 'error' && (
          <>
            <XCircleIcon size={48} className="mx-auto text-red-500" />
            <h2 className="text-2xl font-serif font-bold text-primary">Verification Failed</h2>
            <p className="text-muted-foreground">{message}</p>
            <Button className="w-full" onClick={() => navigate('/customer/dashboard')}>
              Go to Dashboard
            </Button>
          </>
        )}
      </div>
    </div>
  );
};

export default VerifyEmailPage;
