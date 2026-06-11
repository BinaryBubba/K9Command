import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'sonner';
import '@/App.css';

// Pages - Auth
import LandingPage from './pages/LandingPage';
import AuthPage from './pages/AuthPage';
import ForgotPasswordPage from './pages/ForgotPasswordPage';
import StaffRequestPage from './pages/StaffRequestPage';

// Pages - Admin/Owner
import AdminDashboard from './pages/AdminDashboard';
import AdminCustomersPage from './pages/AdminCustomersPage';
import AdminBookingsPage from './pages/AdminBookingsPage';
import AdminStaffPage from './pages/AdminStaffPage';
import AdminIncidentsPage from './pages/AdminIncidentsPage';
import AdminAuditPage from './pages/AdminAuditPage';
import AdminSettingsPage from './pages/AdminSettingsPage';
import AdminOperationsHubPage from './pages/AdminOperationsHubPage';
import AdminCustomerManagementHubPage from './pages/AdminCustomerManagementHubPage';
import AdminAdministrationHubPage from './pages/AdminAdministrationHubPage';

// Pages - Shared Admin+Staff
import KennelManagementPage from './pages/KennelManagementPage';
import CheckInOutPage from './pages/CheckInOutPage';
import DailyOpsPage from './pages/DailyOpsPage';
import TaskDashboardPage from './pages/TaskDashboardPage';
import AddDogPage from './pages/AddDogPage';

// Pages - Staff
import StaffDashboard from './pages/StaffDashboard';
import StaffHubPage from './pages/StaffHubPage';
import StaffBookingsPage from './pages/StaffBookingsPage';

// Components
import NavBar from './components/NavBar';
import BookingProfilePage from './pages/BookingProfilePage';
import MeetAndGreetPage from './pages/MeetAndGreetPage';
// Pages - Customer
import CustomerDashboard from "./pages/CustomerDashboard";
import CustomerProfilePage from "./pages/CustomerProfilePage";
import DogProfilePage from "./pages/DogProfilePage";
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
        <NavBar />
        <div className="md:ml-52">
        <Routes>
          {/* Public Routes */}
          <Route path="/" element={<LandingPage />} />
          <Route path="/auth" element={<AuthPage />} />
          <Route path="/forgot-password" element={<ForgotPasswordPage />} />
          <Route path="/staff-request" element={<StaffRequestPage />} />

          {/* Staff Routes */}
          <Route
            path="/staff/dashboard"
            element={
              <ProtectedRoute allowedRoles={['staff', 'admin']}>
                <StaffDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/staff/hub"
            element={
              <ProtectedRoute allowedRoles={['staff', 'admin']}>
                <StaffHubPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/staff/bookings"
            element={
              <ProtectedRoute allowedRoles={['staff', 'admin']}>
                <StaffBookingsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/staff/tasks"
            element={
              <ProtectedRoute allowedRoles={['staff', 'admin']}>
                <TaskDashboardPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/staff/check-in-out"
            element={
              <ProtectedRoute allowedRoles={['staff', 'admin']}>
                <CheckInOutPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/staff/daily-ops"
            element={
              <ProtectedRoute allowedRoles={['staff', 'admin']}>
                <DailyOpsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/staff/*"
            element={
              <ProtectedRoute allowedRoles={['staff', 'admin']}>
                <StaffDashboard />
              </ProtectedRoute>
            }
          />

          {/* Admin/Owner Routes */}
          <Route
            path="/admin/dashboard"
            element={
              <ProtectedRoute allowedRoles={['admin']}>
                <AdminDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/operations"
            element={
              <ProtectedRoute allowedRoles={['admin']}>
                <AdminOperationsHubPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/customer-management"
            element={
              <ProtectedRoute allowedRoles={['admin']}>
                <AdminCustomerManagementHubPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/administration"
            element={
              <ProtectedRoute allowedRoles={['admin']}>
                <AdminAdministrationHubPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/customers"
            element={
              <ProtectedRoute allowedRoles={['admin']}>
                <AdminCustomersPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/dogs/add"
            element={
              <ProtectedRoute allowedRoles={['admin', 'staff']}>
                <AddDogPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/bookings"
            element={
              <ProtectedRoute allowedRoles={['admin']}>
                <AdminBookingsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/staff"
            element={
              <ProtectedRoute allowedRoles={['admin']}>
                <AdminStaffPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/incidents"
            element={
              <ProtectedRoute allowedRoles={['admin']}>
                <AdminIncidentsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/audit"
            element={
              <ProtectedRoute allowedRoles={['admin']}>
                <AdminAuditPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/kennels"
            element={
              <ProtectedRoute allowedRoles={['admin', 'staff']}>
                <KennelManagementPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/tasks"
            element={
              <ProtectedRoute allowedRoles={['admin']}>
                <TaskDashboardPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/settings"
            element={
              <ProtectedRoute allowedRoles={['admin']}>
                <AdminSettingsPage />
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
          <Route
            path="/customer/dashboard"
            element={
              <ProtectedRoute allowedRoles={["customer", "admin", "staff"]}>
                <CustomerDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/dogs/:dogId"
            element={
              <ProtectedRoute allowedRoles={["admin", "staff"]}>
                <DogProfilePage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/customers/:householdId"
            element={
              <ProtectedRoute allowedRoles={["admin", "staff"]}>
                <CustomerProfilePage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/meet-and-greet"
            element={
              <ProtectedRoute allowedRoles={["admin", "staff"]}>
                <MeetAndGreetPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/bookings/:bookingId"
            element={
              <ProtectedRoute allowedRoles={["admin", "staff"]}>
                <BookingProfilePage />
              </ProtectedRoute>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
        </div>
      </BrowserRouter>
    </div>
  );
}

export default App;
