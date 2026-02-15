import React from "react";
import { Button } from "../ui";
import { safeDisplay } from "../../utils/format";

export default function Header({
  dark,
  setDark,
  authedUser,
  setRoute,
  onLogout,
  routeToHash,
  handleNavClick,
  pageTitle = "",
}) {
  return (
    <div className="flex items-center gap-4 w-full flex-wrap sm:flex-nowrap min-h-10">
      <a
        href={routeToHash ? routeToHash(authedUser ? { name: "index" } : { name: "login" }) : "#/"}
        onClick={(e) => {
          e.preventDefault();
          if (authedUser) setRoute({ name: "index" });
          else setRoute({ name: "login" });
        }}
        className="flex items-center gap-3 hover:opacity-85 transition-opacity cursor-pointer min-w-0 flex-shrink-0"
      >
        <div className="h-8 w-8 sm:h-9 sm:w-9 rounded-xl bg-white/90 dark:bg-white/10 backdrop-blur-sm border border-slate-300/80 dark:border-slate-600/80 flex-shrink-0 shadow-sm" />
        <span className="text-base sm:text-lg font-semibold text-slate-800 dark:text-slate-100 truncate">
          Network Project Platform
        </span>
      </a>
      {pageTitle ? (
        <div className="flex-1 min-w-0 flex justify-center hidden sm:block">
          <span className="text-sm font-medium text-slate-600 dark:text-slate-400 truncate">
            {pageTitle}
          </span>
        </div>
      ) : (
        <div className="flex-1 min-w-0 hidden sm:block" aria-hidden="true" />
      )}
      <div className="flex items-center gap-2 flex-shrink-0">
        <Button
          variant="ghost"
          onClick={() => setDark(!dark)}
          className="text-slate-600 dark:text-slate-400"
          title={dark ? "Switch to light mode" : "Switch to dark mode"}
        >
          {dark ? "🌙 Dark" : "☀️ Light"}
        </Button>
        {authedUser ? (
          <>
            <span className="text-sm text-slate-600 dark:text-slate-400 hidden xs:inline">
              {safeDisplay(authedUser?.username)}
            </span>
            <a
              href={routeToHash ? routeToHash({ name: "login" }) : "#/login"}
              onClick={(e) => handleNavClick(e, onLogout)}
              className="inline-flex items-center justify-center rounded-lg px-3 py-1.5 text-xs font-medium shadow-sm transition focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap bg-white text-gray-900 ring-1 ring-gray-300 hover:bg-gray-50 focus:ring-blue-500 dark:bg-gray-800 dark:text-gray-100 dark:ring-gray-600 dark:hover:bg-gray-700"
            >
              Sign out
            </a>
          </>
        ) : (
          <a
            href={routeToHash ? routeToHash({ name: "login" }) : "#/login"}
            onClick={(e) => handleNavClick(e, () => setRoute({ name: "login" }))}
            className="inline-flex items-center justify-center rounded-lg px-3 py-1.5 text-xs font-medium shadow-sm transition focus:outline-none focus:ring-2 focus:ring-offset-2 bg-transparent text-gray-700 hover:bg-gray-100 focus:ring-blue-500 dark:text-gray-200 dark:hover:bg-gray-800"
          >
            Sign in
          </a>
        )}
      </div>
    </div>
  );
}
