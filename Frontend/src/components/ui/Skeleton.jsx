import React from "react";

export const Skeleton = ({ className, count = 1 }) => {
  return (
    <div className="flex flex-col gap-4 w-full">
      {Array.from({ length: count }).map((_, i) => (
        <div 
          key={i} 
          className={`bg-slate-50 animate-pulse rounded-xl relative overflow-hidden ${className}`}
        >
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/[0.05] to-transparent -translate-x-full animate-[_2s_infinite]" />
        </div>
      ))}
    </div>
  );
};

export const CardSkeleton = () => (
  <div className=" p-6 rounded-3xl border border-slate-200 space-y-4">
    <div className="w-12 h-12 bg-slate-50 rounded-2xl animate-pulse" />
    <div className="space-y-2">
      <div className="w-24 h-3 bg-slate-50 rounded animate-pulse" />
      <div className="w-32 h-8 bg-slate-50 rounded animate-pulse" />
    </div>
  </div>
);
