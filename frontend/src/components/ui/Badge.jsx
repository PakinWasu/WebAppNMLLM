import React from "react";
import { safeChild } from "../../utils/format";

export default function Badge({ children }) {
  return (
    <span className="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-100">
      {safeChild(children)}
    </span>
  );
}
