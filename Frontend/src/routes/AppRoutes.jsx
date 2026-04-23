import { lazy, Suspense } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { ProtectedRoute } from "../components/ProtectedRoute";
import { PublicOnlyRoute } from "../components/PublicOnlyRoute";
import { DashboardLayout } from "../layout/DashboardLayout";
import { useAuth } from "../context/AuthContext";

// Public pages (loaded immediately — small)
import { Login }    from "../pages/auth/Login";
import { Register } from "../pages/auth/Register";

// Lazy-load heavy dashboard pages for code splitting
const LandingPage      = lazy(() => import("../pages/LandingPage").then(m => ({ default: m.LandingPage })));
const UserDashboard    = lazy(() => import("../pages/dashboard/UserDashboard").then(m => ({ default: m.UserDashboard })));
const AdminDashboard   = lazy(() => import("../pages/dashboard/AdminDashboard").then(m => ({ default: m.AdminDashboard })));
const ScanPage         = lazy(() => import("../pages/dashboard/ScanPage").then(m => ({ default: m.ScanPage })));
const ResultsPage      = lazy(() => import("../pages/dashboard/ResultsPage").then(m => ({ default: m.ResultsPage })));
const HistoryPage      = lazy(() => import("../pages/dashboard/HistoryPage").then(m => ({ default: m.HistoryPage })));
const AnalyticsPage    = lazy(() => import("../pages/dashboard/AnalyticsPage").then(m => ({ default: m.AnalyticsPage })));
const BatchUploadPage  = lazy(() => import("../pages/dashboard/BatchUploadPage").then(m => ({ default: m.BatchUploadPage })));
const AdminUsersPage   = lazy(() => import("../pages/dashboard/AdminUsersPage").then(m => ({ default: m.AdminUsersPage })));
const AdminMessagesPage = lazy(() => import("../pages/dashboard/AdminMessagesPage").then(m => ({ default: m.AdminMessagesPage })));
const AdminLogsPage    = lazy(() => import("../pages/dashboard/AdminLogsPage").then(m => ({ default: m.AdminLogsPage })));

// Minimal skeleton fallback for lazy pages
const PageSkeleton = () => (
  <div className="space-y-6 animate-pulse">
    <div className="h-8 w-48 skeleton rounded-lg" />
    <div className="grid grid-cols-4 gap-4">
      {[...Array(4)].map((_, i) => (
        <div key={i} className="h-28 skeleton rounded-2xl" />
      ))}
    </div>
    <div className="h-72 skeleton rounded-2xl" />
  </div>
);

const SmartRedirect = () => {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  return <Navigate to={user.role === "admin" ? "/admin" : "/dashboard"} replace />;
};

export const AppRoutes = () => (
  <Suspense fallback={<PageSkeleton />}>
    <Routes>
      {/* Public */}
      <Route path="/" element={<PublicOnlyRoute><LandingPage /></PublicOnlyRoute>} />
      <Route path="/login" element={<PublicOnlyRoute><Login /></PublicOnlyRoute>} />
      <Route path="/register" element={<PublicOnlyRoute><Register /></PublicOnlyRoute>} />

      {/* Protected User */}
      <Route element={<ProtectedRoute><DashboardLayout /></ProtectedRoute>}>
        <Route path="/dashboard" element={<UserDashboard />} />
        <Route path="/scan"      element={<ScanPage />} />
        <Route path="/results"   element={<ResultsPage />} />
        <Route path="/history"   element={<HistoryPage />} />
        <Route path="/analytics" element={<AnalyticsPage />} />
        <Route path="/batch"     element={<BatchUploadPage />} />
      </Route>

      {/* Protected Admin */}
      <Route element={<ProtectedRoute requireAdmin><DashboardLayout isAdmin /></ProtectedRoute>}>
        <Route path="/admin"          element={<AdminDashboard />} />
        <Route path="/admin/users"    element={<AdminUsersPage />} />
        <Route path="/admin/messages" element={<AdminMessagesPage />} />
        <Route path="/admin/logs"     element={<AdminLogsPage />} />
      </Route>

      <Route path="*" element={<SmartRedirect />} />
    </Routes>
  </Suspense>
);
