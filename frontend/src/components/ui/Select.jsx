import React from "react";
import { safeDisplay } from "../../utils/format";

export default function Select({
  options = [],
  value,
  onChange,
  className = "",
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className={`rounded-xl border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 ${className}`}
    >
      {options.map((o) => (
        <option key={safeDisplay(o.value)} value={o.value}>
          {safeDisplay(o.label)}
        </option>
      ))}
    </select>
  );
}
