import React from "react";

const base =
  "inline-flex items-center justify-center gap-2 rounded-xl px-3 py-2 text-sm font-medium transition focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed focus:ring-offset-white dark:focus:ring-offset-slate-900";

const variants = {
  primary:
    "bg-white/90 dark:bg-white/10 backdrop-blur-sm border border-slate-300/80 dark:border-slate-600/80 text-slate-800 dark:text-slate-100 shadow-sm hover:bg-white dark:hover:bg-white/15 focus:ring-slate-400 dark:focus:ring-slate-500",
  secondary:
    "bg-slate-100/90 dark:bg-slate-800/80 border border-slate-300/80 dark:border-slate-600/80 text-slate-800 dark:text-slate-200 hover:bg-slate-200/90 dark:hover:bg-slate-700/80 focus:ring-slate-400 dark:focus:ring-slate-500 backdrop-blur-sm",
  ghost:
    "bg-transparent text-slate-600 dark:text-slate-400 hover:bg-slate-100/80 dark:hover:bg-slate-800/60 focus:ring-slate-400 dark:focus:ring-slate-500",
  danger:
    "bg-rose-500/90 dark:bg-rose-600/80 text-white border border-rose-400/50 dark:border-rose-500/50 shadow-sm hover:bg-rose-500 dark:hover:bg-rose-500 focus:ring-rose-400 dark:focus:ring-rose-500 backdrop-blur-sm",
};

/**
 * Button: primary, secondary, ghost, danger. Supports light/dark and rounded style.
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
