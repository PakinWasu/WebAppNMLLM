import React from "react";

/**
 * NOC-style card: bg-slate-900, border-slate-800, optional title and actions.
 */
export default function Card({ title, actions, children, className = "" }) {
  return (
    <div
      className={`rounded-lg border border-slate-800 bg-slate-900 ${className}`}
    >
      {(title || actions) && (
        <div className="flex items-center justify-between border-b border-slate-800 px-4 py-3">
          <h3 className="text-sm font-semibold text-slate-200">{title}</h3>
          <div className="flex gap-2">{actions}</div>
        </div>
      )}
      <div className="p-4">{children}</div>
    </div>
  );
}
