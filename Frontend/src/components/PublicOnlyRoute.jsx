import { Navigate } from "react-router-dom";
import { useStore } from "../store/useStore";
import { Spinner } from "./ui/Spinner";

export const PublicOnlyRoute = ({ children }) => {
  const { user, isLoading } = useStore();

  if (isLoading) {
    return (
      <div className="flex bg-slate-50 h-screen w-screen items-center justify-center">
        <Spinner size={32} className="text-indigo-600" />
      </div>
    );
  }

  if (user) {
    return <Navigate to={user.role === "admin" ? "/admin" : "/dashboard"} replace />;
  }

  return children;
};
