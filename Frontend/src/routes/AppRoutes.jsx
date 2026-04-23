import { lazy, Suspense } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { ProtectedRoute } from "../components/ProtectedRoute";
import { PublicOnlyRoute } from "../components/PublicOnlyRoute";
import { DashboardLayout } from "../layout/DashboardLayout";
import { useStore } from "../store/useStore";
import { Spinner } from "../components/ui/Spinner";

// Public pages
const LandingPage = lazy(() => import("../pages/LandingPage").then(module => ({ default: module.LandingPage })));
const Login = lazy(() => import("../pages/auth/Login").then(module => ({ default: module.Login })));
const Register = lazy(() => import("../pages/auth/Register").then(module => ({ default: module.Register })));

// Dashboard pages
const UserDashboard = lazy(() => import("../pages/dashboard/UserDashboard").then(module => ({ default: module.UserDashboard })));
const AdminDashboard = lazy(() => import("../pages/dashboard/AdminDashboard").then(module => ({ default: module.AdminDashboard })));
const ScanPage = lazy(() => import("../pages/dashboard/ScanPage").then(module => ({ default: module.ScanPage })));
const ResultsPage = lazy(() => import("../pages/dashboard/ResultsPage").then(module => ({ default: module.ResultsPage })));
const HistoryPage = lazy(() => import("../pages/dashboard/HistoryPage").then(module => ({ default: module.HistoryPage })));
const AnalyticsPage = lazy(() => import("../pages/dashboard/AnalyticsPage").then(module => ({ default: module.AnalyticsPage })));
const BatchUploadPage = lazy(() => import("../pages/dashboard/BatchUploadPage").then(module => ({ default: module.BatchUploadPage })));

// Admin-specific pages
const AdminUsersPage = lazy(() => import("../pages/dashboard/AdminUsersPage").then(module => ({ default: module.AdminUsersPage })));
const AdminMessagesPage = lazy(() => import("../pages/dashboard/AdminMessagesPage").then(module => ({ default: module.AdminMessagesPage })));
const AdminLogsPage = lazy(() => import("../pages/dashboard/AdminLogsPage").then(module => ({ default: module.AdminLogsPage })));

const SuspenseLayout = ({ children }) => (
  <Suspense fallback={
    <div className="flex h-64 w-full items-center justify-center">
      <Spinner size={32} className="text-indigo-600" />
    </div>
  }>
    {children}
  </Suspense>
);

const SmartRedirect = () => {
  const user = useStore((state) => state.user);
  if (!user) return <Navigate to="/login" replace />;
  return <Navigate to={user.role === "admin" ? "/admin" : "/dashboard"} replace />;
};

export const AppRoutes = () => {
  return (
    <Routes>
      <Route
        path="/"
        element={
          <PublicOnlyRoute>
            <SuspenseLayout>
              <LandingPage />
            </SuspenseLayout>
          </PublicOnlyRoute>
        }
      />
      <Route
        path="/login"
        element={
          <PublicOnlyRoute>
            <SuspenseLayout>
              <Login />
            </SuspenseLayout>
          </PublicOnlyRoute>
        }
      />
      <Route
        path="/register"
        element={
          <PublicOnlyRoute>
            <SuspenseLayout>
              <Register />
            </SuspenseLayout>
          </PublicOnlyRoute>
        }
      />

      <Route
        element={
          <ProtectedRoute>
            <DashboardLayout />
          </ProtectedRoute>
        }
      >
        <Route path="/dashboard" element={<SuspenseLayout><UserDashboard /></SuspenseLayout>} />
        <Route path="/scan"      element={<SuspenseLayout><ScanPage /></SuspenseLayout>}      />
        <Route path="/results"   element={<SuspenseLayout><ResultsPage /></SuspenseLayout>}   />
        <Route path="/history"   element={<SuspenseLayout><HistoryPage /></SuspenseLayout>}   />
        <Route path="/analytics" element={<SuspenseLayout><AnalyticsPage /></SuspenseLayout>} />
        <Route path="/batch"     element={<SuspenseLayout><BatchUploadPage /></SuspenseLayout>} />
      </Route>

      <Route
        element={
          <ProtectedRoute requireAdmin={true}>
            <DashboardLayout isAdmin />
          </ProtectedRoute>
        }
      >
        <Route path="/admin"          element={<SuspenseLayout><AdminDashboard /></SuspenseLayout>}  />
        <Route path="/admin/users"    element={<SuspenseLayout><AdminUsersPage /></SuspenseLayout>}  />
        <Route path="/admin/messages" element={<SuspenseLayout><AdminMessagesPage /></SuspenseLayout>} />
        <Route path="/admin/logs"     element={<SuspenseLayout><AdminLogsPage /></SuspenseLayout>}   />
      </Route>

      <Route path="*" element={<SmartRedirect />} />
    </Routes>
  );
};
