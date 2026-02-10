import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from './ui/card';
import { Button } from './ui/button';
import { Switch } from './ui/switch';
import { Badge } from './ui/badge';
import { toast } from 'sonner';
import { 
  BellIcon, 
  BellOffIcon, 
  CheckCircleIcon, 
  AlertCircleIcon,
  SmartphoneIcon,
  SendIcon,
  Loader2Icon
} from 'lucide-react';
import { usePushNotifications } from '../hooks/usePushNotifications';

const PushNotificationSettings = () => {
  const {
    isSupported,
    permission,
    isSubscribed,
    loading,
    error,
    subscribe,
    unsubscribe,
    sendTest
  } = usePushNotifications();
  
  const [testLoading, setTestLoading] = useState(false);

  const handleToggle = async () => {
    if (isSubscribed) {
      const success = await unsubscribe();
      if (success) {
        toast.success('Push notifications disabled');
      }
    } else {
      const success = await subscribe();
      if (success) {
        toast.success('Push notifications enabled! You\'ll receive alerts for booking updates.');
      } else if (permission === 'denied') {
        toast.error('Please enable notifications in your browser settings');
      }
    }
  };

  const handleSendTest = async () => {
    setTestLoading(true);
    try {
      const result = await sendTest();
      toast.success(result.message);
    } catch (e) {
      toast.error('Failed to send test notification');
    } finally {
      setTestLoading(false);
    }
  };

  if (!isSupported) {
    return (
      <Card className="bg-slate-50 border-slate-200">
        <CardContent className="p-6">
          <div className="flex items-center gap-3 text-slate-500">
            <BellOffIcon size={24} />
            <div>
              <p className="font-medium">Push Notifications Not Supported</p>
              <p className="text-sm">Your browser doesn't support push notifications.</p>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="bg-white border-border/50" data-testid="push-notification-settings">
      <CardHeader className="border-b">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
              <BellIcon className="text-primary" size={20} />
            </div>
            <div>
              <CardTitle className="text-lg">Push Notifications</CardTitle>
              <CardDescription>Get instant alerts on your device</CardDescription>
            </div>
          </div>
          <Switch
            checked={isSubscribed}
            onCheckedChange={handleToggle}
            disabled={loading}
            data-testid="push-toggle"
          />
        </div>
      </CardHeader>
      
      <CardContent className="p-6 space-y-4">
        {/* Status */}
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">Status</span>
          <Badge 
            className={isSubscribed ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-600'}
          >
            {isSubscribed ? (
              <>
                <CheckCircleIcon size={12} className="mr-1" />
                Enabled
              </>
            ) : (
              <>
                <BellOffIcon size={12} className="mr-1" />
                Disabled
              </>
            )}
          </Badge>
        </div>

        {/* Permission Status */}
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">Browser Permission</span>
          <Badge 
            className={
              permission === 'granted' ? 'bg-green-100 text-green-700' :
              permission === 'denied' ? 'bg-red-100 text-red-700' :
              'bg-amber-100 text-amber-700'
            }
          >
            {permission === 'granted' ? 'Allowed' :
             permission === 'denied' ? 'Blocked' : 'Not Set'}
          </Badge>
        </div>

        {/* Error Display */}
        {error && (
          <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
            <AlertCircleIcon size={16} />
            {error}
          </div>
        )}

        {/* Info Box */}
        <div className="p-4 bg-slate-50 rounded-lg">
          <h4 className="font-medium text-sm mb-2 flex items-center gap-2">
            <SmartphoneIcon size={16} />
            You'll be notified when:
          </h4>
          <ul className="text-sm text-muted-foreground space-y-1 ml-6 list-disc">
            <li>Your booking is confirmed or requires review</li>
            <li>Admin approves or updates your booking</li>
            <li>Check-in/check-out reminders</li>
            <li>Payment reminders</li>
          </ul>
        </div>

        {/* Test Button */}
        {isSubscribed && (
          <Button
            variant="outline"
            onClick={handleSendTest}
            disabled={testLoading}
            className="w-full"
            data-testid="test-push-btn"
          >
            {testLoading ? (
              <Loader2Icon size={16} className="mr-2 animate-spin" />
            ) : (
              <SendIcon size={16} className="mr-2" />
            )}
            Send Test Notification
          </Button>
        )}

        {/* Permission Denied Help */}
        {permission === 'denied' && (
          <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg">
            <h4 className="font-medium text-amber-800 text-sm mb-1">Notifications Blocked</h4>
            <p className="text-sm text-amber-700">
              You've blocked notifications. To enable them:
            </p>
            <ol className="text-sm text-amber-700 mt-2 ml-4 list-decimal">
              <li>Click the lock/info icon in your browser's address bar</li>
              <li>Find "Notifications" in the permissions</li>
              <li>Change it to "Allow"</li>
              <li>Refresh this page</li>
            </ol>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default PushNotificationSettings;
