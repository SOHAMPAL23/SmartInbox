import { Sidebar } from "./Sidebar";
import { NotificationBell } from "../components/ui/NotificationBell";
import { Outlet, useLocation } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";

export const DashboardLayout = () => {
  const location = useLocation();

  return (
    <div className="flex h-screen bg-white overflow-hidden">
      <Sidebar />

      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Top bar */}
        <header className="sticky top-0 z-40 bg-white border-b border-slate-100 px-8 py-3 flex items-center justify-end gap-3">
          <NotificationBell />
        </header>

        {/* Page content */}
        <div className="flex-1 overflow-y-auto overflow-x-hidden no-scrollbar">
          <AnimatePresence mode="wait">
            <motion.div
              key={location.pathname}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.15, ease: "easeOut" }}
              className="p-8 min-h-full"
            >
              <Outlet />
            </motion.div>
          </AnimatePresence>
        </div>
      </main>
    </div>
  );
};
