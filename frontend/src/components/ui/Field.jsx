import React from "react";
import { safeDisplay } from "../../utils/format";

export default function Field({ label, children }) {
  return (
    <label className="grid gap-1.5">
      <span className="text-xs font-medium text-gray-600 dark:text-gray-300">
        {safeDisplay(label)}
      </span>
      {children}
    </label>
  );
}
