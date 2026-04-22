export const ProgressBar = ({ value = 0, max = 100, color = "cyan", className = "" }) => {
  const pct = Math.min(100, Math.max(0, (value / max) * 100));
  const colorMap = {
    cyan: "bg-cyan-500",
    rose: "bg-rose-500",
    emerald: "bg-emerald-500",
    indigo: "bg-indigo-500",
  };

  return (
    <div className={`h-2 w-full bg-slate-100 rounded-full overflow-hidden ${className}`}>
      <div
        className={`h-full rounded-full transition-all duration-1000 ease-out ${colorMap[color] || colorMap.cyan}`}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
};
