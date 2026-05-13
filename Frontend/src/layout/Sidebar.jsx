import React, { useState, memo } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { 
  LayoutDashboard, 
  History, 
  LogOut, 
  ChevronLeft, 
  ChevronRight,
  Zap,
  MessageSquare,
  BarChart3,
  Search,
  Upload,
  Cpu,
  Users,
  ScrollText,
  Shield,
  Settings
} from "lucide-react";
import { useStore } from "../store/useStore";
import Logo from "../components/ui/Logo";

const SidebarItem = memo(({ icon: Icon, label, path, active, collapsed }) => {
  return (
    <Link to={path}>
      <motion.div
        className={`relative flex items-center p-3.5 mb-2 rounded-2xl transition-all group overflow-hidden
          ${active 
            ? "bg-slate-900 text-white shadow-xl shadow-slate-200" 
            : "text-slate-500 hover:text-slate-900 hover:bg-slate-100"
          }`}
        whileHover={{ x: active ? 0 : 4 }}
        whileTap={{ scale: 0.98 }}
      >
        {active && (
          <motion.div 
            layoutId="activePill"
            className="absolute left-0 w-1 h-6 bg-indigo-500 rounded-r-full"
          />
        )}
        <Icon className={`w-5 h-5 ${active ? "text-indigo-400" : "group-hover:text-slate-900"} transition-colors`} />
        
        <AnimatePresence>
          {!collapsed && (
            <motion.span
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -10 }}
              className="ml-3.5 text-[10px] font-black uppercase tracking-[0.15em] whitespace-nowrap"
            >
              {label}
            </motion.span>
          )}
        </AnimatePresence>

        {active && !collapsed && (
          <motion.div 
            initial={{ opacity: 0, scale: 0 }}
            animate={{ opacity: 1, scale: 1 }}
            className="ml-auto w-1.5 h-1.5 rounded-full bg-indigo-500"
          />
        )}
      </motion.div>
    </Link>
  );
});

export const Sidebar = () => {
  const [collapsed, setCollapsed] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const user = useStore((state) => state.user);
  const logout = useStore((state) => state.logout);
  const isAdmin = user?.role === "admin";

  const handleLogout = () => {
    logout();
    navigate("/", { replace: true });
  };

  const mainNav = [
    { label: "Dashboard",    path: "/dashboard",  icon: LayoutDashboard },
    { label: "New Analysis", path: "/scan",        icon: Search          },
    { label: "Batch Upload", path: "/batch",       icon: Upload          },
    { label: "History",      path: "/history",     icon: History         },
    { label: "Analytics",    path: "/analytics",   icon: BarChart3       },
  ];

  const adminNav = [
    { label: "Matrix Core", path: "/admin",          icon: Cpu          },
    { label: "User Nodes",  path: "/admin/users",    icon: Users        },
    { label: "Intercepts",  path: "/admin/messages", icon: MessageSquare },
    { label: "Audit Logs",  path: "/admin/logs",     icon: ScrollText   },
  ];

  return (
    <motion.aside
      initial={false}
      animate={{ width: collapsed ? 88 : 280 }}
      className="relative h-screen bg-white border-r border-slate-200 flex flex-col transition-all z-50 shrink-0 shadow-sm"
    >
      {/* Logo Section */}
      <div className="p-6 flex items-center justify-between border-b border-slate-100/50">
        <AnimatePresence mode="wait">
          {!collapsed ? (
            <motion.div
              key="logo-full"
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -10 }}
              className="flex items-center gap-3"
            >
              <Logo size="sm" horizontal />
            </motion.div>
          ) : (
            <motion.div
              key="logo-collapsed"
              initial={{ opacity: 0, scale: 0.5 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.5 }}
              className="mx-auto"
            >
              <Logo size="sm" showText={false} />
            </motion.div>
          )}
        </AnimatePresence>
        
        {!collapsed && (
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="p-2 hover:bg-slate-100 rounded-xl text-slate-400 hover:text-slate-900 transition-all active:scale-90"
          >
            <ChevronLeft size={18} />
          </button>
        )}
      </div>

      {collapsed && (
        <button
          onClick={() => setCollapsed(false)}
          className="absolute -right-3 top-20 w-6 h-6 bg-white border border-slate-200 rounded-full flex items-center justify-center text-slate-400 hover:text-slate-900 shadow-sm z-50 transition-all hover:scale-110"
        >
          <ChevronRight size={14} />
        </button>
      )}

      {/* Navigation */}
      <div className="flex-1 px-4 mt-8 overflow-y-auto no-scrollbar">
        <div className="mb-10">
          {!collapsed && (
            <motion.h4 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="text-[9px] font-black tracking-[0.3em] uppercase text-slate-400 mb-5 px-4"
            >
              Intelligence Matrix
            </motion.h4>
          )}
          {mainNav.map((item) => (
            <SidebarItem
              key={item.path}
              {...item}
              active={location.pathname === item.path}
              collapsed={collapsed}
            />
          ))}
        </div>

        {isAdmin && (
          <div className="mb-8 pt-6 border-t border-slate-50">
            {!collapsed && (
              <motion.h4 
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="text-[9px] font-black tracking-[0.3em] uppercase text-slate-400 mb-5 px-4"
              >
                Oversight Control
              </motion.h4>
            )}
            {adminNav.map((item) => (
              <SidebarItem
                key={item.path}
                {...item}
                active={location.pathname === item.path}
                collapsed={collapsed}
              />
            ))}
          </div>
        )}
      </div>

      {/* User Section */}
      <div className="p-4 border-t border-slate-100/50 space-y-4">
        <div className={`flex items-center gap-3 p-3.5 rounded-2xl bg-slate-50 border border-slate-100 transition-all ${collapsed ? 'justify-center' : ''}`}>
          <div className="shrink-0 w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 to-indigo-700 flex items-center justify-center text-white font-black text-sm shadow-lg shadow-indigo-100">
            {user?.username?.charAt(0).toUpperCase() || "U"}
          </div>
          {!collapsed && (
            <div className="flex-1 min-w-0">
              <p className="text-[11px] font-black text-slate-900 truncate leading-none mb-1">{user?.username || "Agent"}</p>
              <div className="flex items-center gap-1.5">
                <div className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                <p className="text-[9px] text-slate-400 truncate uppercase font-black tracking-widest leading-none">{user?.role || "USER"}</p>
              </div>
            </div>
          )}
        </div>
        
        <button
          onClick={handleLogout}
          className={`w-full flex items-center gap-3 p-3.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-2xl transition-all group ${collapsed ? 'justify-center' : ''}`}
        >
          <LogOut size={18} className="group-hover:translate-x-0.5 transition-transform" />
          {!collapsed && <span className="font-black text-[10px] uppercase tracking-[0.2em]">Disconnect</span>}
        </button>
      </div>
    </motion.aside>
  );
};

export default Sidebar;


