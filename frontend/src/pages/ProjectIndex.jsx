import React, { useState, useMemo } from "react";
import { Card, Badge, Input } from "../components/ui";
import { safeDisplay } from "../utils/format";

export default function ProjectIndex({
  authedUser,
  can,
  projects,
  setRoute,
  routeToHash,
  isMember,
  handleNavClick,
}) {
  const [q, setQ] = useState("");
  const visible = useMemo(() => {
    if (!authedUser) return [];
    const mine = projects.filter(
      (p) => can("see-all-projects") || isMember(p, authedUser.username)
    );
    return mine.filter((p) => p.name.toLowerCase().includes(q.toLowerCase()));
  }, [projects, authedUser, q, can, isMember]);

  const linkProps = (targetRoute) => ({
    href: routeToHash ? routeToHash(targetRoute) : "#/",
    onClick: (e) => handleNavClick(e, () => setRoute(targetRoute)),
  });

  return (
    <div className="grid gap-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">My Projects</h1>
        <div className="flex items-center gap-2">
          <Input
            placeholder="Search projects..."
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
          {can("create-project") && (
            <a
              {...linkProps({ name: "newProject" })}
              className="inline-flex items-center justify-center rounded-lg px-3 py-1.5 text-xs font-medium shadow-sm transition focus:outline-none focus:ring-2 focus:ring-offset-2 bg-white/90 dark:bg-white/10 backdrop-blur-sm border border-slate-300/80 dark:border-slate-600/80 text-slate-800 dark:text-slate-100 hover:bg-white dark:hover:bg-white/15 focus:ring-slate-400 dark:focus:ring-slate-500"
            >
              New Project
            </a>
          )}
          {can("user-management") && (
            <a
              {...linkProps({ name: "userAdmin" })}
              className="inline-flex items-center justify-center rounded-lg px-3 py-1.5 text-xs font-medium shadow-sm transition focus:outline-none focus:ring-2 focus:ring-offset-2 bg-white text-gray-900 ring-1 ring-gray-300 hover:bg-gray-50 focus:ring-blue-500 dark:bg-gray-800 dark:text-gray-100 dark:ring-gray-600 dark:hover:bg-gray-700"
            >
              User Admin
            </a>
          )}
          <a
            {...linkProps({
              name: "changePassword",
              username: authedUser?.username,
              fromIndex: true,
            })}
            className="inline-flex items-center justify-center rounded-lg px-3 py-1.5 text-xs font-medium transition focus:outline-none focus:ring-2 focus:ring-offset-2 bg-transparent text-gray-700 hover:bg-gray-100 focus:ring-blue-500 dark:text-gray-200 dark:hover:bg-gray-800"
          >
            Change Password
          </a>
        </div>
      </div>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {visible.map((p) => (
          <Card
            key={p.id || p.project_id}
            className="hover:shadow-lg transition-all duration-200 hover:scale-[1.02]"
            title={p.name}
            actions={
              <Badge
                className={
                  p.visibility === "Shared"
                    ? "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-100"
                    : "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-100"
                }
              >
                {p.visibility === "Shared" ? "Shared" : "Active"}
              </Badge>
            }
          >
            {(p.topoUrl || p.topo_url) ? (
              <div className="h-48 w-full rounded-xl mb-4 border border-slate-300 dark:border-[#1F2937] shadow-sm bg-gray-50 dark:bg-gray-900 overflow-hidden flex items-center justify-center">
                <img
                  src={p.topoUrl || p.topo_url}
                  alt="topology"
                  className="max-w-full max-h-full w-auto h-auto object-contain"
                  style={{ imageRendering: "auto" }}
                />
              </div>
            ) : (
              <div className="h-48 w-full bg-gradient-to-br from-gray-100 to-gray-200 dark:from-gray-800 dark:to-gray-900 rounded-xl mb-4 border border-slate-300 dark:border-[#1F2937] flex items-center justify-center">
                <div className="text-center text-gray-400 dark:text-gray-500">
                  <svg
                    className="w-12 h-12 mx-auto mb-2"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
                    />
                  </svg>
                  <p className="text-xs">No topology image</p>
                </div>
              </div>
            )}
            <div className="grid gap-3">
              {p.desc != null && (
                <div className="text-sm text-gray-600 dark:text-gray-300 line-clamp-2 min-h-[2.5rem]">
                  {safeDisplay(p.desc)}
                </div>
              )}
              <div className="flex flex-wrap gap-x-4 gap-y-2 text-xs text-gray-500 dark:text-gray-400 pt-1 border-t border-slate-300 dark:border-[#1F2937]">
                <span className="flex items-center gap-1.5">
                  <svg
                    className="w-4 h-4 text-gray-400 dark:text-gray-500"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
                    />
                  </svg>
                  <span className="font-medium text-gray-700 dark:text-gray-300">
                    {safeDisplay(p.manager) || "—"}
                  </span>
                </span>
                <span className="flex items-center gap-1.5">
                  <svg
                    className="w-4 h-4 text-gray-400 dark:text-gray-500"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                  <span>{safeDisplay(p.updated)}</span>
                </span>
                <span className="flex items-center gap-1.5">
                  <svg
                    className="w-4 h-4 text-gray-400 dark:text-gray-500"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
                    />
                  </svg>
                  <span>
                    <b className="text-gray-700 dark:text-gray-300">
                      {safeDisplay(p.devices) === "—" ? 0 : safeDisplay(p.devices)}
                    </b>{" "}
                    devices
                  </span>
                </span>
              </div>
              <div className="pt-2">
                <a
                  href={
                    p.project_id || p.id
                      ? routeToHash
                        ? routeToHash({
                            name: "project",
                            projectId: p.project_id || p.id,
                            tab: "setting",
                          })
                        : "#/"
                      : "#/"
                  }
                  onClick={(e) =>
                    handleNavClick(e, () => {
                      if (p.project_id || p.id)
                        setRoute({
                          name: "project",
                          projectId: p.project_id || p.id,
                          tab: "setting",
                        });
                      else console.error("Project missing project_id:", p);
                    })
                  }
                  className="inline-flex items-center justify-center w-full rounded-lg px-3 py-1.5 text-xs font-medium shadow-sm transition focus:outline-none focus:ring-2 focus:ring-offset-2 bg-white/90 dark:bg-white/10 backdrop-blur-sm border border-slate-300/80 dark:border-slate-600/80 text-slate-800 dark:text-slate-100 hover:bg-white dark:hover:bg-white/15 focus:ring-slate-400 dark:focus:ring-slate-500"
                >
                  Open Project
                </a>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
