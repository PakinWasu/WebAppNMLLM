import React from "react";

const base =
  "inline-flex items-center justify-center rounded-lg px-3 py-1.5 text-xs font-medium shadow-sm transition focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap";
const styles = {
  primary:
    "bg-white/90 dark:bg-white/10 backdrop-blur-sm border border-slate-300/80 dark:border-slate-600/80 text-slate-800 dark:text-slate-100 shadow-sm hover:bg-white dark:hover:bg-white/15 focus:ring-slate-400 dark:focus:ring-slate-500",
  secondary:
    "bg-white text-gray-900 ring-1 ring-gray-300 hover:bg-gray-50 focus:ring-blue-500 dark:bg-gray-800 dark:text-gray-100 dark:ring-gray-600 dark:hover:bg-gray-700",
  ghost:
    "bg-transparent text-gray-700 hover:bg-gray-100 focus:ring-blue-500 dark:text-gray-200 dark:hover:bg-gray-800",
  danger: "bg-rose-600 text-white hover:bg-rose-700 focus:ring-rose-500",
};

export default function Button({
  children,
  onClick,
  variant = "primary",
  disabled,
  className = "",
  type = "button",
}) {
  const style = styles[variant] || styles.primary;
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
