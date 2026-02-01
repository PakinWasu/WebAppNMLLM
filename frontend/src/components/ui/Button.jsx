import React from "react";

const base =
  "inline-flex items-center justify-center rounded-lg px-3 py-2 text-sm font-medium transition focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-slate-950 disabled:opacity-50 disabled:cursor-not-allowed";

const variants = {
  primary:
    "bg-blue-600 text-white hover:bg-blue-700 focus:ring-blue-500 border border-slate-800",
  secondary:
    "bg-slate-800 text-slate-200 border border-slate-700 hover:bg-slate-700 focus:ring-slate-500",
  ghost:
    "bg-transparent text-slate-300 hover:bg-slate-800 hover:text-slate-200 focus:ring-slate-500",
  danger:
    "bg-rose-600 text-white hover:bg-rose-700 focus:ring-rose-500",
};

/**
 * NOC compact button: primary, secondary, ghost, danger.
 */
export default function Button({
  children,
  onClick,
  variant = "primary",
  disabled,
  className = "",
  type = "button",
}) {
  const style = variants[variant] || variants.primary;
  return (
    <button
      type={type}
      className={`${base} ${style} ${className}`}
      onClick={onClick}
      disabled={disabled}
    >
      {children}
    </button>
  );
}
