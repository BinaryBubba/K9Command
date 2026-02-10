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
import AdminCustomersPage from './pages/AdminCustomersPage';
import AdminBookingsPage from './pages/AdminBookingsPage';
import AdminStaffPage from './pages/AdminStaffPage';
import AdminReportsPage from './pages/AdminReportsPage';
import AdminIncidentsPage from './pages/AdminIncidentsPage';
import AdminAuditPage from './pages/AdminAuditPage';
import AddDogPage from './pages/AddDogPage';
import BookStayPage from './pages/BookStayPage';
import DailyUpdatesFeedPage from './pages/DailyUpdatesFeedPage';
import StaffUploadPage from './pages/StaffUploadPage';
import StaffBookingsPage from './pages/StaffBookingsPage';
import StaffApprovePage from './pages/StaffApprovePage';
import StaffTimesheetPage from './pages/StaffTimesheetPage';
import AdminTimesheetPage from './pages/AdminTimesheetPage';
import ChatPage from './pages/ChatPage';
import CustomerCalendarPage from './pages/CustomerCalendarPage';
import CustomerPaymentsPage from './pages/CustomerPaymentsPage';

// Phase 2 - Time Clock & Scheduling Pages
import StaffTimeClockPage from './pages/StaffTimeClockPage';
import ScheduleViewPage from './pages/ScheduleViewPage';
import KioskModePage from './pages/KioskModePage';
import AdminTimesheetDashboard from './pages/AdminTimesheetDashboard';

// Phase 3 - Forms, Tasks, HR Pages
import FormBuilderPage from './pages/FormBuilderPage';
import FormsManagementPage from './pages/FormsManagementPage';
import FormSubmissionPage from './pages/FormSubmissionPage';
import StaffFormsPage from './pages/StaffFormsPage';
import TaskDashboardPage from './pages/TaskDashboardPage';
import TimeOffPage from './pages/TimeOffPage';

// MoeGo Parity - Phase 1 Pages
import KennelManagementPage from './pages/KennelManagementPage';
import DailyOpsPage from './pages/DailyOpsPage';
import CouponManagementPage from './pages/CouponManagementPage';

// MoeGo Parity - Phase 2 Pages
import LodgingMapPage from './pages/LodgingMapPage';
import CheckInOutPage from './pages/CheckInOutPage';

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
          <Route path="/forgot-password" element={<ForgotPasswordPage />} />
          <Route path="/kiosk" element={<KioskModePage />} />

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
            path="/customer/calendar"
            element={
              <ProtectedRoute allowedRoles={['customer']}>
                <CustomerCalendarPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/customer/payments"
            element={
              <ProtectedRoute allowedRoles={['customer']}>
                <CustomerPaymentsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/customer/updates"
            element={
              <ProtectedRoute allowedRoles={['customer']}>
                <DailyUpdatesFeedPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/customer/chat"
            element={
              <ProtectedRoute allowedRoles={['customer']}>
                <ChatPage />
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
            path="/staff/timesheet"
            element={
              <ProtectedRoute allowedRoles={['staff']}>
                <StaffTimesheetPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/staff/chat"
            element={
              <ProtectedRoute allowedRoles={['staff']}>
                <ChatPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/staff/time-clock"
            element={
              <ProtectedRoute allowedRoles={['staff']}>
                <StaffTimeClockPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/staff/schedule"
            element={
              <ProtectedRoute allowedRoles={['staff']}>
                <ScheduleViewPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/staff/forms"
            element={
              <ProtectedRoute allowedRoles={['staff']}>
                <StaffFormsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/staff/forms/submit/:templateId"
            element={
              <ProtectedRoute allowedRoles={['staff']}>
                <FormSubmissionPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/staff/forms/submit/:templateId/:submissionId"
            element={
              <ProtectedRoute allowedRoles={['staff']}>
                <FormSubmissionPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/staff/tasks"
            element={
              <ProtectedRoute allowedRoles={['staff']}>
                <TaskDashboardPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/staff/time-off"
            element={
              <ProtectedRoute allowedRoles={['staff']}>
                <TimeOffPage />
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
            path="/admin/customers"
            element={
              <ProtectedRoute allowedRoles={['admin']}>
                <AdminCustomersPage />
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
            path="/admin/reports"
            element={
              <ProtectedRoute allowedRoles={['admin']}>
                <AdminReportsPage />
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
            path="/admin/timesheet"
            element={
              <ProtectedRoute allowedRoles={['admin']}>
                <AdminTimesheetPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/chat"
            element={
              <ProtectedRoute allowedRoles={['admin']}>
                <ChatPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/time-management"
            element={
              <ProtectedRoute allowedRoles={['admin']}>
                <AdminTimesheetDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/schedule"
            element={
              <ProtectedRoute allowedRoles={['admin']}>
                <ScheduleViewPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/forms"
            element={
              <ProtectedRoute allowedRoles={['admin']}>
                <FormsManagementPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/forms/builder"
            element={
              <ProtectedRoute allowedRoles={['admin']}>
                <FormBuilderPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/forms/builder/:templateId"
            element={
              <ProtectedRoute allowedRoles={['admin']}>
                <FormBuilderPage />
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
            path="/admin/time-off"
            element={
              <ProtectedRoute allowedRoles={['admin']}>
                <TimeOffPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/kennels"
            element={
              <ProtectedRoute allowedRoles={['admin']}>
                <KennelManagementPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/daily-ops"
            element={
              <ProtectedRoute allowedRoles={['admin']}>
                <DailyOpsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/coupons"
            element={
              <ProtectedRoute allowedRoles={['admin']}>
                <CouponManagementPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/lodging-map"
            element={
              <ProtectedRoute allowedRoles={['admin', 'staff']}>
                <LodgingMapPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/check-in-out"
            element={
              <ProtectedRoute allowedRoles={['admin', 'staff']}>
                <CheckInOutPage />
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
