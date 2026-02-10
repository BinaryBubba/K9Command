import React, { useState, useEffect, useRef } from 'react';
import { Clock, User, Coffee, LogIn, LogOut, AlertCircle, CheckCircle } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Card, CardContent } from '../components/ui/card';

const API_URL = process.env.REACT_APP_BACKEND_URL;

// Get device code from URL params or localStorage
const getDeviceCode = () => {
  const params = new URLSearchParams(window.location.search);
  const code = params.get('device') || localStorage.getItem('kiosk_device_code');
  if (code && !localStorage.getItem('kiosk_device_code')) {
    localStorage.setItem('kiosk_device_code', code);
  }
  return code;
};

export default function KioskModePage() {
  const [deviceCode] = useState(getDeviceCode);
  const [deviceInfo, setDeviceInfo] = useState(null);
  const [staffOnSite, setStaffOnSite] = useState([]);
  const [pin, setPin] = useState('');
  const [action, setAction] = useState('clock_in'); // clock_in, clock_out, break_start, break_end
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);
  const [currentTime, setCurrentTime] = useState(new Date());
  const [setupMode, setSetupMode] = useState(!deviceCode);
  const [setupCode, setSetupCode] = useState('');
  const pinInputRef = useRef(null);

  // Update time every second
  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  // Fetch kiosk status
  useEffect(() => {
    if (!deviceCode) return;
    
    const fetchStatus = async () => {
      try {
        const response = await fetch(`${API_URL}/api/scheduling/kiosk/${deviceCode}/status`);
        if (response.ok) {
          const data = await response.json();
          setDeviceInfo(data);
          setStaffOnSite(data.staff_on_site || []);
        } else {
          setSetupMode(true);
        }
      } catch (error) {
        console.error('Failed to fetch kiosk status:', error);
      }
    };
    
    fetchStatus();
    const interval = setInterval(fetchStatus, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, [deviceCode]);

  // Handle PIN input
  const handlePinDigit = (digit) => {
    if (pin.length < 6) {
      setPin(prev => prev + digit);
    }
  };

  const handlePinClear = () => {
    setPin('');
  };

  const handlePinBackspace = () => {
    setPin(prev => prev.slice(0, -1));
  };

  // Submit clock action
  const handleSubmit = async () => {
    if (pin.length < 4) {
      setMessage({ type: 'error', text: 'Please enter your 4-6 digit PIN' });
      return;
    }
    
    setLoading(true);
    setMessage(null);
    
    try {
      const response = await fetch(`${API_URL}/api/scheduling/kiosk/clock`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          device_code: deviceCode,
          staff_pin: pin,
          action: action
        })
      });
      
      const data = await response.json();
      
      if (response.ok) {
        setMessage({ type: 'success', text: data.message });
        setPin('');
        // Refresh status
        const statusRes = await fetch(`${API_URL}/api/scheduling/kiosk/${deviceCode}/status`);
        if (statusRes.ok) {
          const statusData = await statusRes.json();
          setStaffOnSite(statusData.staff_on_site || []);
        }
      } else {
        setMessage({ type: 'error', text: data.detail || 'Action failed' });
      }
    } catch (error) {
      setMessage({ type: 'error', text: 'Connection error. Please try again.' });
    }
    
    setLoading(false);
    
    // Clear message after 5 seconds
    setTimeout(() => {
      setMessage(null);
    }, 5000);
  };

  // Setup mode - enter device code
  const handleSetup = () => {
    if (setupCode) {
      localStorage.setItem('kiosk_device_code', setupCode);
      window.location.href = `/kiosk?device=${setupCode}`;
    }
  };

  if (setupMode) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
        <Card className="bg-slate-900 border-slate-800 w-full max-w-md">
          <CardContent className="p-8 text-center">
            <Clock className="h-16 w-16 mx-auto mb-6 text-blue-400" />
            <h1 className="text-2xl font-bold text-white mb-2">Kiosk Setup</h1>
            <p className="text-slate-400 mb-6">Enter the device code provided by your administrator</p>
            
            <input
              type="text"
              value={setupCode}
              onChange={(e) => setSetupCode(e.target.value)}
              placeholder="Device Code"
              className="w-full p-4 bg-slate-800 border border-slate-700 rounded-lg text-white text-center text-lg mb-4"
            />
            
            <Button onClick={handleSetup} className="w-full" size="lg">
              Activate Kiosk
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-white p-4 md:p-8">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <header className="text-center mb-8">
          <h1 className="text-4xl md:text-6xl font-bold mb-2">
            {currentTime.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}
          </h1>
          <p className="text-xl text-slate-400">
            {currentTime.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' })}
          </p>
          {deviceInfo && (
            <p className="text-sm text-slate-500 mt-2">{deviceInfo.device_name}</p>
          )}
        </header>

        {/* Message Display */}
        {message && (
          <div className={`mb-6 p-4 rounded-lg flex items-center gap-3 ${
            message.type === 'success' ? 'bg-green-900/50 text-green-400' : 'bg-red-900/50 text-red-400'
          }`}>
            {message.type === 'success' ? (
              <CheckCircle className="h-6 w-6" />
            ) : (
              <AlertCircle className="h-6 w-6" />
            )}
            <span className="text-lg">{message.text}</span>
          </div>
        )}

        <div className="grid md:grid-cols-2 gap-6">
          {/* PIN Entry */}
          <Card className="bg-slate-900 border-slate-800">
            <CardContent className="p-6">
              {/* Action Selection */}
              <div className="grid grid-cols-2 gap-2 mb-6">
                <Button
                  variant={action === 'clock_in' ? 'default' : 'outline'}
                  onClick={() => setAction('clock_in')}
                  className="h-16"
                >
                  <LogIn className="h-5 w-5 mr-2" />
                  Clock In
                </Button>
                <Button
                  variant={action === 'clock_out' ? 'default' : 'outline'}
                  onClick={() => setAction('clock_out')}
                  className="h-16"
                >
                  <LogOut className="h-5 w-5 mr-2" />
                  Clock Out
                </Button>
                <Button
                  variant={action === 'break_start' ? 'default' : 'outline'}
                  onClick={() => setAction('break_start')}
                  className="h-12"
                >
                  <Coffee className="h-4 w-4 mr-2" />
                  Start Break
                </Button>
                <Button
                  variant={action === 'break_end' ? 'default' : 'outline'}
                  onClick={() => setAction('break_end')}
                  className="h-12"
                >
                  <Coffee className="h-4 w-4 mr-2" />
                  End Break
                </Button>
              </div>

              {/* PIN Display */}
              <div className="mb-6">
                <label className="text-sm text-slate-400 block mb-2 text-center">Enter Your PIN</label>
                <div className="flex justify-center gap-2">
                  {[0, 1, 2, 3, 4, 5].map((i) => (
                    <div
                      key={i}
                      className={`w-10 h-12 rounded-lg border-2 flex items-center justify-center text-2xl font-bold ${
                        i < pin.length ? 'border-blue-500 bg-blue-500/20' : 'border-slate-700'
                      }`}
                    >
                      {i < pin.length ? '•' : ''}
                    </div>
                  ))}
                </div>
              </div>

              {/* Number Pad */}
              <div className="grid grid-cols-3 gap-2">
                {[1, 2, 3, 4, 5, 6, 7, 8, 9].map((num) => (
                  <Button
                    key={num}
                    variant="outline"
                    className="h-14 text-2xl font-bold text-white border-slate-600 hover:bg-slate-700"
                    onClick={() => handlePinDigit(num.toString())}
                  >
                    {num}
                  </Button>
                ))}
                <Button
                  variant="outline"
                  className="h-14 text-sm text-white border-slate-600 hover:bg-slate-700"
                  onClick={handlePinClear}
                >
                  Clear
                </Button>
                <Button
                  variant="outline"
                  className="h-14 text-2xl font-bold text-white border-slate-600 hover:bg-slate-700"
                  onClick={() => handlePinDigit('0')}
                >
                  0
                </Button>
                <Button
                  variant="outline"
                  className="h-14 text-sm text-white border-slate-600 hover:bg-slate-700"
                  onClick={handlePinBackspace}
                >
                  ←
                </Button>
              </div>

              {/* Submit Button */}
              <Button
                className="w-full h-16 text-xl mt-4"
                onClick={handleSubmit}
                disabled={loading || pin.length < 4}
              >
                {loading ? 'Processing...' : 
                  action === 'clock_in' ? 'Clock In' :
                  action === 'clock_out' ? 'Clock Out' :
                  action === 'break_start' ? 'Start Break' : 'End Break'
                }
              </Button>
            </CardContent>
          </Card>

          {/* Staff On Site */}
          <Card className="bg-slate-900 border-slate-800">
            <CardContent className="p-6">
              <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
                <User className="h-5 w-5" />
                Staff On Site ({staffOnSite.length})
              </h2>
              
              {staffOnSite.length === 0 ? (
                <p className="text-slate-500 text-center py-8">No staff currently on site</p>
              ) : (
                <div className="space-y-3 max-h-[400px] overflow-y-auto">
                  {staffOnSite.map((staff, index) => (
                    <div key={index} className="flex items-center justify-between p-3 bg-slate-800/50 rounded-lg">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-blue-500/20 flex items-center justify-center">
                          <User className="h-5 w-5 text-blue-400" />
                        </div>
                        <span className="font-medium">{staff.staff_name}</span>
                      </div>
                      <span className="text-sm text-slate-400">
                        {new Date(staff.clock_in).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Footer */}
        <footer className="text-center text-slate-600 text-sm mt-8">
          K9Command Time Clock • Kiosk Mode
        </footer>
      </div>
    </div>
  );
}
