import React from "react";
import { safeDisplay, safeChild } from "../../utils/format";

export default function Card({
  title,
  actions,
  children,
  className = "",
  compact = false,
  compactHeader = false,
  headerClassName = "",
}) {
  const isFlexCard =
    className.includes("flex flex-col") || className.includes("flex-1");
  const isFullScreen =
    className.includes("overflow-hidden") && isFlexCard;
  const headerCompact = compact || compactHeader;
  const isTitleElement = React.isValidElement(title);
  return (
    <div
      className={`rounded-2xl border border-slate-300 dark:border-[#1F2937] bg-white dark:bg-[#111827] shadow-sm ${className}`}
    >
      {(title || actions) && (
        <div
          className={`flex items-center justify-between border-b border-gray-100 dark:border-[#1F2937] flex-shrink-0 ${
            headerCompact ? "px-3 py-2" : compact ? "px-2 py-1" : "px-5 py-3"
          } ${headerClassName}`}
        >
          {isTitleElement ? (
            <div className="flex items-center justify-between w-full min-w-0">{safeChild(title)}</div>
          ) : (
            <h3
              className={`${
                compact ? "text-[10px]" : compactHeader ? "text-xs" : "text-sm"
              } font-semibold text-gray-700 dark:text-gray-200`}
            >
              {safeDisplay(title)}
            </h3>
          )}
          {!isTitleElement && (
            <div className={`flex gap-2 ${compactHeader ? "gap-1.5" : ""}`}>
              {safeChild(actions)}
            </div>
          )}
        </div>
      )}
      <div
        className={
          isFlexCard
            ? isFullScreen
              ? "flex-1 min-h-0 flex flex-col overflow-hidden"
              : compact
                ? "p-1 flex-1 min-h-0 flex flex-col overflow-hidden"
                : "p-5 flex-1 min-h-0 flex flex-col overflow-hidden"
            : compact
              ? "p-1"
              : "p-5"
        }
      >
        {safeChild(children)}
      </div>
    </div>
  );
}
