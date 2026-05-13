import React from "react";
import { motion } from "framer-motion";

export const Logo = ({ size = "md", showText = true, horizontal = false }) => {
  const sizes = {
    sm: { box: 24, text: "text-base", tracking: "tracking-[0.1em]", gap: "gap-2" },
    md: { box: 40, text: "text-xl", tracking: "tracking-[0.15em]", gap: "gap-3" },
    lg: { box: 64, text: "text-4xl", tracking: "tracking-[0.2em]", gap: "gap-4" }
  };

  const { box, text, tracking, gap } = sizes[size];

  return (
    <div className={`flex ${horizontal ? 'flex-row items-center' : 'flex-col items-center'} justify-center ${gap}`}>
      <motion.div
        whileHover={{ scale: 1.05 }}
        className="relative flex items-center justify-center shrink-0"
        style={{ width: box, height: box * 0.8 }}
      >
        <svg
          viewBox="0 0 100 80"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className="w-full h-full"
        >
          <defs>
            <linearGradient id="logoGradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#4f46e5" />
              <stop offset="100%" stopColor="#e11d48" />
            </linearGradient>
          </defs>
          
          {/* Main S-Path with Gradient */}
          <path
            d="M75 15H35C26.7157 15 20 21.7157 20 30C20 38.2843 26.7157 45 35 45H65C73.2843 45 80 51.7157 80 60C80 68.2843 73.2843 75 65 75H25"
            stroke="url(#logoGradient)"
            strokeWidth="11"
            strokeLinecap="round"
          />
          
          {/* Terminals and Nodes with Gradient/Color accents */}
          <circle cx="75" cy="15" r="7" stroke="#4f46e5" strokeWidth="4" fill="white" />
          <circle cx="45" cy="30" r="5" fill="#4f46e5" />
          <circle cx="55" cy="45" r="5" fill="#e11d48" />
          <circle cx="25" cy="75" r="7" stroke="#e11d48" strokeWidth="4" fill="white" />
        </svg>
      </motion.div>

      {showText && (
        <span className={`font-black text-slate-900 uppercase ${tracking} ${text} whitespace-nowrap`}>
          SMART<span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-600 to-rose-600">INBOX</span>
        </span>
      )}
    </div>
  );
};

export default Logo;
