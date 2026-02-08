import React, { useState } from "react";
import Button from "../ui/Button";

export default function TopNavbar({
  projects,
  currentProjectId,
  onProjectChange,
  authedUser,
  onLogout,
  notificationCount = 0,
}) {
  const [searchQuery, setSearchQuery] = useState("");
  const [projectDropdownOpen, setProjectDropdownOpen] = useState(false);

  const currentProject = projects?.find(
    (p) => (p.project_id || p.id) === currentProjectId
  );
  const projectName = currentProject?.name || "Select project";

  return (
    <header className="sticky top-0 z-20 flex h-12 sm:h-14 items-center justify-between gap-2 px-3 sm:px-6 border-b border-slate-300 dark:border-slate-800 bg-white/95 dark:bg-slate-900/95 backdrop-blur-sm shadow-sm dark:shadow-none">
      <div className="flex flex-1 items-center gap-2 min-w-0">
        <input
          type="search"
          placeholder="Search devices, alerts..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-32 xs:w-48 sm:w-56 max-w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50 px-3 py-2 text-sm text-slate-800 dark:text-slate-200 placeholder-slate-500 dark:placeholder-slate-400 focus:border-blue-500 dark:focus:border-blue-400 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:focus:ring-blue-400 transition-colors"
        />
      </div>
      <div className="flex items-center gap-2 sm:gap-3 flex-shrink-0">
        <div className="relative">
          <button
            className="relative rounded-lg p-2 text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-slate-700 dark:hover:text-slate-200 transition-colors"
            aria-label="Notifications"
          >
            <span className="text-lg">🔔</span>
            {notificationCount > 0 && (
              <span className="absolute -right-0.5 -top-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-rose-500 text-[10px] font-bold text-white">
                {notificationCount > 9 ? "9+" : notificationCount}
              </span>
            )}
          </button>
        </div>
        <div className="relative">
          <button
            onClick={() => setProjectDropdownOpen(!projectDropdownOpen)}
            className="flex items-center gap-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-2 sm:px-3 py-2 text-sm text-slate-800 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors min-w-0"
          >
            <span className="truncate max-w-[100px] sm:max-w-[140px]">{projectName}</span>
            <span className="text-slate-500 dark:text-slate-400 flex-shrink-0">▾</span>
          </button>
          {projectDropdownOpen && (
            <>
              <div
                className="fixed inset-0 z-10"
                onClick={() => setProjectDropdownOpen(false)}
                aria-hidden="true"
              />
              <div className="absolute right-0 top-full z-20 mt-1 w-48 sm:w-56 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 py-1 shadow-dropdown dark:shadow-lg">
                {projects?.length ? (
                  projects.map((p) => (
                    <button
                      key={p.project_id || p.id}
                      onClick={() => {
                        onProjectChange(p.project_id || p.id);
                        setProjectDropdownOpen(false);
                      }}
                      className={`block w-full px-4 py-2.5 text-left text-sm rounded-lg mx-1 ${
                        (p.project_id || p.id) === currentProjectId
                          ? "bg-blue-50 dark:bg-slate-800 text-blue-700 dark:text-slate-100 font-medium"
                          : "text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
                      }`}
                    >
                      {p.name}
                    </button>
                  ))
                ) : (
                  <p className="px-4 py-2 text-xs text-slate-500 dark:text-slate-400">
                    No projects
                  </p>
                )}
              </div>
            </>
          )}
        </div>
        <div className="hidden xs:flex items-center gap-2 border-l border-slate-300 dark:border-slate-800 pl-2 sm:pl-3">
          <span className="text-sm text-slate-600 dark:text-slate-400 truncate max-w-[80px] sm:max-w-none">{authedUser?.username}</span>
          <Button variant="secondary" onClick={onLogout}>
            Sign out
          </Button>
        </div>
      </div>
    </header>
  );
}
