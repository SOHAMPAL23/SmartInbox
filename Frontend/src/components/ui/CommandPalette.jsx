import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Search, Zap, History, Settings, MessageSquare, X } from "lucide-react";
import { useNavigate } from "react-router-dom";

export const CommandPalette = ({ isOpen, onClose }) => {
  const [query, setQuery] = useState("");
  const navigate = useNavigate();

  const actions = [
    { icon: Zap, label: "New Scan", path: "/scan", shortcut: "S" },
    { icon: History, label: "View History", path: "/history", shortcut: "H" },
    { icon: MessageSquare, label: "Analytics", path: "/analytics", shortcut: "A" },
    { icon: Settings, label: "Settings", path: "/settings", shortcut: "," },
  ];

  const filteredActions = actions.filter(action => 
    action.label.toLowerCase().includes(query.toLowerCase())
  );

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        onClose(!isOpen);
      }
      if (e.key === "Escape") onClose(false);
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-[100] flex items-start justify-center pt-[15vh] px-4">
        {/* Backdrop */}
        <motion.div 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={() => onClose(false)}
          className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        />

        {/* Modal */}
        <motion.div
          initial={{ opacity: 0, scale: 0.9, y: -20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.9, y: -20 }}
          className="relative w-full max-w-xl  rounded-2xl border border-slate-200 shadow-md overflow-hidden"
        >
          <div className="p-4 border-b border-slate-100 flex items-center gap-3">
            <Search className="text-slate-500 w-5 h-5" />
            <input 
              autoFocus
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Type a command or search..."
              className="flex-1 bg-transparent border-none focus:ring-0 text-slate-900 placeholder:text-slate-600 text-lg"
            />
            <div className="px-2 py-1 bg-slate-50 rounded text-[10px] font-bold text-slate-500 border border-slate-200 uppercase">
              ESC
            </div>
          </div>

          <div className="max-h-[400px] overflow-y-auto p-2 no-scrollbar">
            {filteredActions.length > 0 ? (
              filteredActions.map((action, i) => (
                <div 
                  key={i}
                  onClick={() => {
                    navigate(action.path);
                    onClose(false);
                  }}
                  className="flex items-center justify-between p-3 rounded-xl hover:bg-slate-50 cursor-pointer group transition-all"
                >
                  <div className="flex items-center gap-4">
                    <div className="p-2 bg-slate-100 rounded-lg group-hover:bg-cyan-500/20 transition-colors">
                      <action.icon className="w-5 h-5 text-slate-500 group-hover:text-cyan-400" />
                    </div>
                    <span className="font-bold text-slate-600 group-hover:text-slate-900">{action.label}</span>
                  </div>
                  <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <span className="text-[10px] font-bold text-slate-600 uppercase">Shortcut:</span>
                    <kbd className="px-1.5 py-0.5 bg-slate-100 rounded text-[10px] font-bold text-slate-500 border border-slate-200">
                      {action.shortcut}
                    </kbd>
                  </div>
                </div>
              ))
            ) : (
              <div className="p-8 text-center text-slate-500 text-sm italic">
                No commands matching "{query}"
              </div>
            )}
          </div>

          <div className="p-3 bg-slate-50 border-t border-slate-100 flex justify-between items-center text-[10px] font-bold text-slate-600 uppercase tracking-widest">
            <span>Commands Available: {actions.length}</span>
            <div className="flex gap-4">
              <span className="flex items-center gap-1"><span className="text-slate-500">↑↓</span> Navigate</span>
              <span className="flex items-center gap-1"><span className="text-slate-500">↵</span> Execute</span>
            </div>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};
