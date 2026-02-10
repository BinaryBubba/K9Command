import { useState, useEffect, useCallback } from 'react';
import api from '../utils/api';

// Check if push notifications are supported
export const isPushSupported = () => {
  return 'serviceWorker' in navigator && 'PushManager' in window;
};

// Check if notifications are permitted
export const getNotificationPermission = () => {
  if (!('Notification' in window)) return 'unsupported';
  return Notification.permission;
};

// Request notification permission
export const requestNotificationPermission = async () => {
  if (!('Notification' in window)) {
    return 'unsupported';
  }
  
  const permission = await Notification.requestPermission();
  return permission;
};

// Convert a base64 string to Uint8Array (for VAPID key)
function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - base64String.length % 4) % 4);
  const base64 = (base64String + padding)
    .replace(/-/g, '+')
    .replace(/_/g, '/');
  
  const rawData = window.atob(base64);
  const outputArray = new Uint8Array(rawData.length);
  
  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  return outputArray;
}

// Custom hook for push notification management
export function usePushNotifications() {
  const [isSupported, setIsSupported] = useState(false);
  const [permission, setPermission] = useState('default');
  const [isSubscribed, setIsSubscribed] = useState(false);
  const [subscription, setSubscription] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Check support and current state on mount
  useEffect(() => {
    const checkSupport = async () => {
      const supported = isPushSupported();
      setIsSupported(supported);
      
      if (supported) {
        setPermission(getNotificationPermission());
        
        // Check if already subscribed
        try {
          const registration = await navigator.serviceWorker.ready;
          const existingSub = await registration.pushManager.getSubscription();
          if (existingSub) {
            setIsSubscribed(true);
            setSubscription(existingSub);
          }
        } catch (e) {
          console.error('Error checking subscription:', e);
        }
      }
    };
    
    checkSupport();
  }, []);

  // Subscribe to push notifications
  const subscribe = useCallback(async () => {
    if (!isSupported) {
      setError('Push notifications are not supported');
      return false;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      // Request permission
      const perm = await requestNotificationPermission();
      setPermission(perm);
      
      if (perm !== 'granted') {
        setError('Notification permission denied');
        setLoading(false);
        return false;
      }
      
      // Register service worker
      const registration = await navigator.serviceWorker.register('/sw.js');
      await navigator.serviceWorker.ready;
      
      // Get VAPID public key from server
      const vapidRes = await api.get('/k9/push/vapid-key');
      const vapidPublicKey = vapidRes.data.vapid_public_key;
      
      if (!vapidPublicKey) {
        throw new Error('VAPID key not configured on server');
      }
      
      // Subscribe to push manager
      const pushSubscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(vapidPublicKey)
      });
      
      // Send subscription to server
      const subscriptionJson = pushSubscription.toJSON();
      await api.post('/k9/push/subscribe/web', {
        subscription: {
          endpoint: subscriptionJson.endpoint,
          keys: subscriptionJson.keys
        },
        device_info: {
          userAgent: navigator.userAgent,
          platform: navigator.platform,
          language: navigator.language
        }
      });
      
      setIsSubscribed(true);
      setSubscription(pushSubscription);
      setLoading(false);
      return true;
      
    } catch (e) {
      console.error('Push subscription error:', e);
      setError(e.message || 'Failed to subscribe');
      setLoading(false);
      return false;
    }
  }, [isSupported]);

  // Unsubscribe from push notifications
  const unsubscribe = useCallback(async () => {
    if (!subscription) return false;
    
    setLoading(true);
    setError(null);
    
    try {
      await subscription.unsubscribe();
      setIsSubscribed(false);
      setSubscription(null);
      setLoading(false);
      return true;
    } catch (e) {
      console.error('Push unsubscribe error:', e);
      setError(e.message || 'Failed to unsubscribe');
      setLoading(false);
      return false;
    }
  }, [subscription]);

  // Send test notification
  const sendTest = useCallback(async () => {
    try {
      const res = await api.post('/k9/push/test');
      return res.data;
    } catch (e) {
      console.error('Test notification error:', e);
      throw e;
    }
  }, []);

  return {
    isSupported,
    permission,
    isSubscribed,
    loading,
    error,
    subscribe,
    unsubscribe,
    sendTest
  };
}

export default usePushNotifications;
