import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { Mail, Lock, User, ShieldCheck, ArrowRight, Zap } from "lucide-react";
import { registerUser } from "../../api/authApi";
import { toast } from "react-hot-toast";

export const Register = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [formData, setFormData] = useState({ username: "", email: "", password: "" });
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    try {
      await registerUser(formData);
      toast.success("Account created! Please sign in.");
      navigate("/login");
    } catch (err) {
      const detail = err.response?.data?.detail;
      const message = Array.isArray(detail)
        ? detail.map(d => d.msg).join(", ")
        : detail || "Registration failed. Please try again.";
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
            <span className="text-emerald-400 text-xs font-medium">Free to get started</span>
          </div>
          <h1 className="text-4xl font-bold text-white leading-tight">
            Start protecting<br />your inbox today.
          </h1>
          <p className="text-slate-400 text-base leading-relaxed max-w-sm">
            Create your SmartInbox account and immediately gain access to AI-powered spam detection with real-time alerts.
          </p>
        </div>

        <div className="space-y-3">
          {[
            { icon: ShieldCheck, text: "ML model trained on millions of messages" },
            { icon: ShieldCheck, text: "Real-time threat notifications" },
            { icon: ShieldCheck, text: "Batch scanning for large datasets" },
          ].map(({ icon: Icon, text }) => (
            <div key={text} className="flex items-center gap-3">
              <Icon className="w-4 h-4 text-emerald-400 flex-shrink-0" />
              <span className="text-slate-300 text-sm">{text}</span>
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
            <h2 className="text-2xl font-semibold text-slate-900">Create your account</h2>
            <p className="text-slate-500 text-sm mt-1">Get started for free — no credit card required.</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-slate-700" htmlFor="username">Username</label>
              <div className="relative">
                <User size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
                <input
                  id="username"
                  type="text"
                  required
                  value={formData.username}
                  onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                  className="input-base pl-10"
                  placeholder="yourname"
                />
              </div>
            </div>

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
                  autoComplete="new-password"
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  className="input-base pl-10"
                  placeholder="Min. 8 characters"
                />
              </div>
              <p className="text-xs text-slate-400">Must contain uppercase letter and a number.</p>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="btn-primary w-full h-11"
            >
              {isLoading ? (
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <>Create account <ArrowRight size={16} /></>
              )}
            </button>
          </form>

          <p className="text-center text-sm text-slate-500">
            Already have an account?{" "}
            <Link to="/login" className="text-blue-600 font-medium hover:text-blue-700 transition-colors">
              Sign in
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
