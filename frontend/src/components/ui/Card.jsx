import React from "react";

/**
 * Card with optional title and actions. Light/dark, rounded, subtle shadow.
 */
export default function Card({ title, actions, children, className = "" }) {
  return (
    <div
      className={`rounded-xl border border-slate-300 dark:border-slate-700/80 bg-white/95 dark:bg-slate-900/95 backdrop-blur-sm shadow-card dark:shadow-card-dark ${className}`}
    >
      {(title || actions) && (
        <div className="flex items-center justify-between border-b border-slate-300 dark:border-slate-800 px-4 py-3">
          <h3 className="text-card-title font-semibold text-slate-800 dark:text-slate-200">{title}</h3>
          <div className="flex gap-2">{actions}</div>
        </div>
      )}
      <div className="p-4">{children}</div>
    </div>
  );
}
