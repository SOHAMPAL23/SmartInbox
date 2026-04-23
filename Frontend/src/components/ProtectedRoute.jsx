import { Navigate, useLocation } from "react-router-dom";
import { useStore } from "../store/useStore";
import { Spinner } from "./ui/Spinner";

export const ProtectedRoute = ({ children, requireAdmin = false }) => {
  const { user, isLoading } = useStore();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="flex bg-slate-50 h-screen w-screen items-center justify-center">
        <Spinner size={32} className="text-indigo-600" />
      </div>
    );
  }

  if (!user) return <Navigate to="/login" state={{ from: location }} replace />;

  if (requireAdmin && user.role !== "admin") {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
};
