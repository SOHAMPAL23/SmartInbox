export const Slider = ({ min = 0, max = 1, step = 0.01, value, onChange, label, variant = "primary", className = "" }) => {
  const colors = {
    primary: "accent-cyan-500",
    danger: "accent-rose-500",
    indigo: "accent-indigo-500",
  };

  return (
    <div className={className}>
      {label && (
        <div className="flex items-center justify-between mb-2">
          <span className="text-[10px] font-bold tracking-widest text-slate-500 uppercase">{label}</span>
          <span className="text-sm font-mono text-cyan-300">{value.toFixed(3)}</span>
        </div>
      )}
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className={`w-full h-2 bg-slate-100 rounded-lg appearance-none cursor-pointer ${colors[variant] || colors.primary}`}
      />
    </div>
  );
};
