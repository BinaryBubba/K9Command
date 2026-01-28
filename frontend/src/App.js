import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'sonner';
import '@/App.css';

// Pages
import LandingPage from './pages/LandingPage';
import AuthPage from './pages/AuthPage';
import ForgotPasswordPage from './pages/ForgotPasswordPage';
import CustomerDashboard from './pages/CustomerDashboard';
import StaffDashboard from './pages/StaffDashboard';
import AdminDashboard from './pages/AdminDashboard';
import AddDogPage from './pages/AddDogPage';
import BookStayPage from './pages/BookStayPage';
import DailyUpdatesFeedPage from './pages/DailyUpdatesFeedPage';
import StaffUploadPage from './pages/StaffUploadPage';
import StaffBookingsPage from './pages/StaffBookingsPage';
import StaffApprovePage from './pages/StaffApprovePage';

// Store
import useAuthStore from './store/authStore';

// Protected Route Component
const ProtectedRoute = ({ children, allowedRoles }) => {
  const user = useAuthStore((state) => state.user);

  if (!user) {
    return <Navigate to="/auth" replace />;
  }

  if (allowedRoles && !allowedRoles.includes(user.role)) {
    return <Navigate to="/" replace />;
  }

  return children;
};

function App() {
  return (
    <div className="App">
      <Toaster position="top-right" richColors />
      <BrowserRouter>
        <Routes>
          {/* Public Routes */}
          <Route path="/" element={<LandingPage />} />
          <Route path="/auth" element={<AuthPage />} />

          {/* Customer Routes */}
          <Route
            path="/customer/dashboard"
            element={
              <ProtectedRoute allowedRoles={['customer']}>
                <CustomerDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/customer/dogs/add"
            element={
              <ProtectedRoute allowedRoles={['customer']}>
                <AddDogPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/customer/bookings/new"
            element={
              <ProtectedRoute allowedRoles={['customer']}>
                <BookStayPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/customer/*"
            element={
              <ProtectedRoute allowedRoles={['customer']}>
                <CustomerDashboard />
              </ProtectedRoute>
            }
          />

          {/* Staff Routes */}
          <Route
            path="/staff/dashboard"
            element={
              <ProtectedRoute allowedRoles={['staff']}>
                <StaffDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/staff/upload"
            element={
              <ProtectedRoute allowedRoles={['staff']}>
                <StaffUploadPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/staff/bookings"
            element={
              <ProtectedRoute allowedRoles={['staff']}>
                <StaffBookingsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/staff/approve"
            element={
              <ProtectedRoute allowedRoles={['staff']}>
                <StaffApprovePage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/staff/*"
            element={
              <ProtectedRoute allowedRoles={['staff']}>
                <StaffDashboard />
              </ProtectedRoute>
            }
          />

          {/* Admin Routes */}
          <Route
            path="/admin/dashboard"
            element={
              <ProtectedRoute allowedRoles={['admin']}>
                <AdminDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/*"
            element={
              <ProtectedRoute allowedRoles={['admin']}>
                <AdminDashboard />
              </ProtectedRoute>
            }
          />

          {/* Fallback */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;
