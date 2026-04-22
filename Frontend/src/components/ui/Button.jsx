import { clsx } from "clsx";
import { Loader2 } from "lucide-react";

export const Button = ({ children, variant = "primary", isLoading, className, disabled, ...props }) => {
  const baseClasses = "flex items-center justify-center gap-2 font-medium rounded-lg transition-all duration-200 outline-none focus:ring-2 disabled:opacity-50 disabled:cursor-not-allowed px-4 py-2 shadow-sm active:scale-[0.98]";

  const variants = {
    primary: "bg-slate-50 hover:bg-slate-100 text-slate-900 focus:ring-slate-200",
    secondary: "bg-white hover:bg-slate-50 text-slate-700 border border-slate-200 focus:ring-slate-100",
    danger: "bg-red-50 hover:bg-red-100 text-red-600 border border-red-200 focus:ring-red-100",
    ghost: "bg-transparent hover:bg-slate-100 text-slate-600 shadow-none border border-transparent hover:text-slate-900",
  };

  return (
    <button
      className={clsx(baseClasses, variants[variant], className)}
      disabled={disabled || isLoading}
      {...props}
    >
      {isLoading && <Loader2 size={16} className="animate-spin" />}
      {children}
    </button>
  );
};
