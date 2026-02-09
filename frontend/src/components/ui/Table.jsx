import React from "react";
import { safeDisplay } from "../../utils/format";

export default function Table({
  columns,
  data,
  empty = "No data",
  containerClassName = "",
  minWidthClass = "min-w-full",
}) {
  const textSizeClass = containerClassName.includes("text-[")
    ? containerClassName.match(/text-\[[^\]]+\]/)?.[0]
    : null;
  const tableTextSize = textSizeClass || "text-xs";
  const headerTextSize = textSizeClass
    ? textSizeClass.replace("text-", "text-").replace("px]", "px]")
    : "text-[10px]";
  const headerAtLeastXs = headerTextSize === "text-[10px]" ? "text-xs" : headerTextSize;

  return (
    <div className={`overflow-auto w-full ${containerClassName}`}>
      <table
        className={`${minWidthClass} w-full divide-y divide-slate-300 dark:divide-gray-700`}
        style={{ tableLayout: "auto", width: "100%" }}
      >
        <thead className="bg-slate-100 dark:bg-gray-800 sticky top-0 z-10">
          <tr>
            {columns.map((c) => (
              <th
                key={c.key || c.header}
                className={`px-2 py-1.5 text-left ${headerAtLeastXs} font-semibold uppercase tracking-wider text-slate-800 dark:text-gray-200 border-b border-slate-300 dark:border-gray-700 whitespace-nowrap`}
                style={c.width ? { minWidth: c.width } : undefined}
              >
                {safeDisplay(c.header)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="bg-white dark:bg-gray-900 divide-y divide-slate-300 dark:divide-gray-700">
          {data.length === 0 && (
            <tr>
              <td
                className={`px-4 py-8 ${tableTextSize} text-center text-gray-500 dark:text-gray-400`}
                colSpan={columns.length}
              >
                {safeDisplay(empty)}
              </td>
            </tr>
          )}
          {data.map((row, i) => (
            <tr
              key={i}
              className="hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
            >
              {columns.map((c) => {
                let cellContent;
                if (c.cell) {
                  const raw = c.cell(row, i);
                  if (
                    typeof raw === "object" &&
                    raw !== null &&
                    !React.isValidElement(raw)
                  ) {
                    cellContent = Array.isArray(raw)
                      ? raw.join(", ")
                      : JSON.stringify(raw);
                  } else {
                    cellContent = raw;
                  }
                } else {
                  const raw = row[c.key];
                  if (raw === null || raw === undefined) {
                    cellContent = "—";
                  } else if (typeof raw === "object" && raw !== null) {
                    if (Array.isArray(raw)) {
                      cellContent = raw.length ? raw.join(", ") : "—";
                    } else if (
                      Object.prototype.hasOwnProperty.call(raw, "total") &&
                      Object.prototype.hasOwnProperty.call(raw, "up")
                    ) {
                      cellContent = `${raw.total ?? 0}/${raw.up ?? 0}/${raw.down ?? 0}/${raw.adminDown ?? 0}`;
                    } else {
                      cellContent = JSON.stringify(raw);
                    }
                  } else {
                    cellContent = raw;
                  }
                }
                return (
                  <td
                    key={c.key || c.header}
                    className={`px-2 py-1.5 ${tableTextSize} text-gray-900 dark:text-gray-100 whitespace-nowrap`}
                    style={c.width ? { minWidth: c.width } : undefined}
                  >
                    {cellContent}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
