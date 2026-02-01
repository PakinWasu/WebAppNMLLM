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
    <header className="sticky top-0 z-20 flex h-14 items-center justify-between border-b border-slate-800 bg-slate-900 px-6">
      <div className="flex flex-1 items-center gap-4">
        <input
          type="search"
          placeholder="Search devices, alerts..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-64 rounded-lg border border-slate-800 bg-slate-800/50 px-3 py-2 text-sm text-slate-200 placeholder-slate-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      </div>
      <div className="flex items-center gap-3">
        <div className="relative">
          <button
            className="relative rounded-lg p-2 text-slate-400 hover:bg-slate-800 hover:text-slate-200"
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
            className="flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-200 hover:bg-slate-700"
          >
            <span className="truncate max-w-[140px]">{projectName}</span>
            <span className="text-slate-500">▾</span>
          </button>
          {projectDropdownOpen && (
            <>
              <div
                className="fixed inset-0 z-10"
                onClick={() => setProjectDropdownOpen(false)}
                aria-hidden="true"
              />
              <div className="absolute right-0 top-full z-20 mt-1 w-56 rounded-lg border border-slate-800 bg-slate-900 py-1 shadow-xl">
                {projects?.length ? (
                  projects.map((p) => (
                    <button
                      key={p.project_id || p.id}
                      onClick={() => {
                        onProjectChange(p.project_id || p.id);
                        setProjectDropdownOpen(false);
                      }}
                      className={`block w-full px-4 py-2 text-left text-sm ${
                        (p.project_id || p.id) === currentProjectId
                          ? "bg-slate-800 text-slate-100"
                          : "text-slate-300 hover:bg-slate-800"
                      }`}
                    >
                      {p.name}
                    </button>
                  ))
                ) : (
                  <p className="px-4 py-2 text-xs text-slate-500">
                    No projects
                  </p>
                )}
              </div>
            </>
          )}
        </div>
        <div className="flex items-center gap-2 border-l border-slate-800 pl-3">
          <span className="text-sm text-slate-400">{authedUser?.username}</span>
          <Button variant="secondary" onClick={onLogout}>
            Sign out
          </Button>
        </div>
      </div>
    </header>
  );
}
