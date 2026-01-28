import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { API } from '../utils/api';
import useAuthStore from '../store/authStore';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { toast } from 'sonner';

const AuthForm = () => {
  const [isLogin, setIsLogin] = useState(true);
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    full_name: '',
    phone: '',
    role: 'customer',
  });
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const setAuth = useAuthStore((state) => state.setAuth);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const endpoint = isLogin ? '/auth/login' : '/auth/register';
      const payload = isLogin
        ? { email: formData.email, password: formData.password }
        : formData;

      const response = await axios.post(`${API}${endpoint}`, payload);
      const { token, user } = response.data;

      setAuth(user, token);
      toast.success(`Welcome ${user.full_name}!`);

      // Redirect based on role
      if (user.role === 'customer') {
        navigate('/customer/dashboard');
      } else if (user.role === 'staff') {
        navigate('/staff/dashboard');
      } else if (user.role === 'admin') {
        navigate('/admin/dashboard');
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full max-w-md space-y-6">
      <div className="text-center">
        <h2 className="text-3xl font-serif font-bold text-primary">
          {isLogin ? 'Welcome Back' : 'Join Our Pack'}
        </h2>
        <p className="text-muted-foreground mt-2">
          {isLogin ? 'Sign in to your account' : 'Create your account'}
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {!isLogin && (
          <>
            <div>
              <Label htmlFor="full_name">Full Name</Label>
              <Input
                id="full_name"
                data-testid="register-fullname-input"
                value={formData.full_name}
                onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                required
                className="mt-1"
              />
            </div>
            <div>
              <Label htmlFor="phone">Phone</Label>
              <Input
                id="phone"
                data-testid="register-phone-input"
                type="tel"
                value={formData.phone}
                onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                className="mt-1"
              />
            </div>
          </>
        )}

        <div>
          <Label htmlFor="email">Email</Label>
          <Input
            id="email"
            data-testid="auth-email-input"
            type="email"
            value={formData.email}
            onChange={(e) => setFormData({ ...formData, email: e.target.value })}
            required
            className="mt-1"
          />
        </div>

        <div>
          <Label htmlFor="password">Password</Label>
          <Input
            id="password"
            data-testid="auth-password-input"
            type="password"
            value={formData.password}
            onChange={(e) => setFormData({ ...formData, password: e.target.value })}
            required
            className="mt-1"
          />
        </div>

        {!isLogin && (
          <div>
            <Label htmlFor="role">I am a</Label>
            <select
              id="role"
              data-testid="register-role-select"
              value={formData.role}
              onChange={(e) => setFormData({ ...formData, role: e.target.value })}
              className="w-full mt-1 p-2 border rounded-xl"
            >
              <option value="customer">Dog Parent</option>
              <option value="staff">Staff Member</option>
              <option value="admin">Administrator</option>
            </select>
          </div>
        )}

        <Button
          data-testid="auth-submit-button"
          type="submit"
          className="w-full rounded-full py-6 text-lg font-semibold"
          disabled={loading}
        >
          {loading ? 'Please wait...' : isLogin ? 'Sign In' : 'Create Account'}
        </Button>
      </form>

      <div className="text-center">
        <button
          data-testid="auth-toggle-button"
          type="button"
          onClick={() => setIsLogin(!isLogin)}
          className="text-primary hover:underline font-medium"
        >
          {isLogin ? "Don't have an account? Sign up" : 'Already have an account? Sign in'}
        </button>
        {isLogin && (
          <>
            <span className="mx-3 text-muted-foreground">•</span>
            <button
              data-testid="forgot-password-link"
              type="button"
              onClick={() => navigate('/forgot-password')}
              className="text-primary hover:underline font-medium"
            >
              Forgot Password?
            </button>
          </>
        )}
      </div>
    </div>
  );
};

export default AuthForm;
