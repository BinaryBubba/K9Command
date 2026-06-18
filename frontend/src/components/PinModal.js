import React, { useState, useRef, useEffect } from 'react';
import { Button } from './ui/button';
import { toast } from 'sonner';
import api from '../utils/api';

/**
 * PinModal - Manager PIN verification overlay
 * Usage: <PinModal onVerified={(managerName) => doOverride()} onCancel={() => {}} />
 */
const PinModal = ({ onVerified, onCancel, title = "Manager Override Required", message = "Enter a manager PIN to continue" }) => {
  const [pin, setPin] = useState(['', '', '', '']);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const refs = [useRef(), useRef(), useRef(), useRef()];

  useEffect(() => { refs[0].current?.focus(); }, []);

  const handleKey = (i, e) => {
    if (e.key === 'Backspace') {
      if (pin[i]) {
        const newPin = [...pin];
        newPin[i] = '';
        setPin(newPin);
      } else if (i > 0) {
        refs[i-1].current?.focus();
      }
      return;
    }
    if (!/^\d$/.test(e.key)) return;
    const newPin = [...pin];
    newPin[i] = e.key;
    setPin(newPin);
    if (i < 3) refs[i+1].current?.focus();
    else {
      // All 4 digits entered — auto-submit
      setTimeout(() => handleVerify([...newPin]), 100);
    }
  };

  const handleVerify = async (pinArr = pin) => {
    const pinStr = pinArr.join('');
    if (pinStr.length !== 4) { setError('Enter all 4 digits'); return; }
    setLoading(true);
    setError('');
    try {
      const res = await api.post('/users/verify-pin', { pin: pinStr });
      toast.success(`Override approved by ${res.data.user_name}`);
      onVerified(res.data.user_name);
    } catch {
      setError('Invalid PIN — try again');
      setPin(['', '', '', '']);
      refs[0].current?.focus();
    } finally { setLoading(false); }
  };

  return (
    <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl w-full max-w-sm shadow-xl">
        <div className="p-6 space-y-5">
          <div className="text-center">
            <div className="text-3xl mb-2">🔐</div>
            <h2 className="text-lg font-bold">{title}</h2>
            <p className="text-sm text-muted-foreground mt-1">{message}</p>
          </div>

          <div className="flex justify-center gap-3">
            {pin.map((digit, i) => (
              <input
                key={i}
                ref={refs[i]}
                type="password"
                maxLength={1}
                value={digit}
                onKeyDown={e => handleKey(i, e)}
                onChange={() => {}}
                className="w-12 h-14 text-center text-2xl font-bold border-2 rounded-xl focus:border-primary focus:outline-none"
              />
            ))}
          </div>

          {error && <p className="text-center text-sm text-red-600">{error}</p>}

          <div className="flex gap-3">
            <Button variant="outline" className="flex-1" onClick={onCancel}>Cancel</Button>
            <Button className="flex-1" onClick={() => handleVerify()} disabled={loading || pin.join('').length !== 4}>
              {loading ? 'Verifying...' : 'Verify'}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PinModal;
