import { useState } from "react";
import { useNavigate, useLocation, Link } from "react-router-dom";
import { Mail, Lock, ShieldCheck, ArrowRight, Zap } from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { loginUser } from "../../api/authApi";
import { toast } from "react-hot-toast";

export const Login = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [formData, setFormData] = useState({ email: "", password: "" });

  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    try {
      const data = await loginUser({ email: formData.email, password: formData.password });
      await login(data);
      toast.success("Signed in successfully.");
      const redirectPath = data.role === "admin" ? "/admin" : "/dashboard";
      navigate(redirectPath, { replace: true });
    } catch (err) {
      const detail = err.response?.data?.detail;
      const message = Array.isArray(detail)
        ? detail.map(d => d.msg).join(", ")
        : detail || "Invalid credentials. Please try again.";
      toast.error(message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#F5F7FA] flex">
      {/* Left branding panel */}
      <div className="hidden lg:flex lg:w-1/2 bg-slate-900 flex-col justify-between p-12">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-white/10 rounded-xl">
            <Zap className="w-5 h-5 text-white" />
          </div>
          <span className="text-white font-semibold text-lg">SmartInbox</span>
        </div>

        <div className="space-y-6">
          <div className="inline-flex items-center gap-2 bg-white/10 px-3 py-1.5 rounded-lg">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <span className="text-emerald-400 text-xs font-medium">AI-Powered Spam Detection</span>
          </div>
          <h1 className="text-4xl font-bold text-white leading-tight">
            Keep your inbox<br />clean and safe.
          </h1>
          <p className="text-slate-400 text-base leading-relaxed max-w-sm">
            SmartInbox uses machine learning to detect and block spam messages before they reach you — with near-instant predictions.
          </p>
        </div>

        <div className="grid grid-cols-3 gap-4">
          {[
            { label: "Accuracy", value: "98.2%" },
            { label: "Avg Latency", value: "<30ms" },
            { label: "Messages Scanned", value: "1M+" },
          ].map((stat) => (
            <div key={stat.label} className="bg-white/5 rounded-xl p-4 border border-white/10">
              <p className="text-xl font-bold text-white">{stat.value}</p>
              <p className="text-xs text-slate-500 mt-1">{stat.label}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Right form panel */}
      <div className="flex-1 flex items-center justify-center px-6 py-12">
        <div className="w-full max-w-md space-y-8">
          {/* Mobile logo */}
          <div className="lg:hidden flex items-center gap-3">
            <div className="p-2 bg-slate-900 rounded-xl">
              <Zap className="w-5 h-5 text-white" />
            </div>
            <span className="text-slate-900 font-semibold text-lg">SmartInbox</span>
          </div>

          <div>
            <h2 className="text-2xl font-semibold text-slate-900">Welcome back</h2>
            <p className="text-slate-500 text-sm mt-1">Sign in to your account to continue.</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-slate-700" htmlFor="email">Email address</label>
              <div className="relative">
                <Mail size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
                <input
                  id="email"
                  type="email"
                  required
                  autoComplete="email"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  className="input-base pl-10"
                  placeholder="you@example.com"
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <label className="text-sm font-medium text-slate-700" htmlFor="password">Password</label>
              <div className="relative">
                <Lock size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
                <input
                  id="password"
                  type="password"
                  required
                  autoComplete="current-password"
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  className="input-base pl-10"
                  placeholder="••••••••"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="btn-primary w-full h-11"
            >
              {isLoading ? (
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <>Sign in <ArrowRight size={16} /></>
              )}
            </button>
          </form>

          <p className="text-center text-sm text-slate-500">
            Don't have an account?{" "}
            <Link to="/register" className="text-blue-600 font-medium hover:text-blue-700 transition-colors">
              Create one
            </Link>
          </p>

          <div className="flex items-center justify-center gap-4 pt-4 border-t border-slate-100">
            <span className="flex items-center gap-1.5 text-xs text-slate-400">
              <Lock size={11} /> End-to-end encrypted
            </span>
            <span className="flex items-center gap-1.5 text-xs text-slate-400">
              <ShieldCheck size={11} /> SOC 2 compliant
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
