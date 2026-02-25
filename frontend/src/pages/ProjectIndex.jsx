import React, { useState, useMemo } from "react";
import { Card, Badge, Input, Select, Button } from "../components/ui";
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
  const [statusFilter, setStatusFilter] = useState("all");
  const [sortBy, setSortBy] = useState("updated_desc");

  const visible = useMemo(() => {
    if (!authedUser) return [];

    const mine = projects.filter(
      (p) => can("see-all-projects") || isMember(p, authedUser.username)
    );

    const qLower = q.trim().toLowerCase();

    let list = mine.filter((p) => {
      if (!qLower) return true;
      const name = (p.name || "").toLowerCase();
      const desc = (p.desc || "").toLowerCase();
      return name.includes(qLower) || desc.includes(qLower);
    });

    if (statusFilter !== "all") {
      list = list.filter(
        (p) => (p.status || "").toLowerCase() === statusFilter
      );
    }

    const parseDate = (value) => {
      if (!value) return null;
      const d = new Date(value);
      return isNaN(d.getTime()) ? null : d;
    };

    const toNumber = (value) => {
      if (typeof value === "number") return value;
      const n = parseInt(value, 10);
      return isNaN(n) ? 0 : n;
    };

    list = [...list].sort((a, b) => {
      switch (sortBy) {
        case "name_asc": {
          return (a.name || "").localeCompare(b.name || "", undefined, {
            sensitivity: "base",
          });
        }
        case "devices_desc": {
          return toNumber(b.devices) - toNumber(a.devices);
        }
        case "status_asc": {
          return (a.status || "").localeCompare(b.status || "", undefined, {
            sensitivity: "base",
          });
        }
        case "updated_desc":
        default: {
          const da = parseDate(a.updated || a.updated_at);
          const db = parseDate(b.updated || b.updated_at);
          if (da && db) return db - da;
          if (da && !db) return -1;
          if (!da && db) return 1;
          return (a.name || "").localeCompare(b.name || "", undefined, {
            sensitivity: "base",
          });
        }
      }
    });

    return list;
  }, [projects, authedUser, q, can, isMember, statusFilter, sortBy]);

  const linkProps = (targetRoute) => ({
    href: routeToHash ? routeToHash(targetRoute) : "#/",
    onClick: (e) => handleNavClick(e, () => setRoute(targetRoute)),
  });

  return (
    <div className="min-h-[60vh] flex flex-col gap-6 px-4 sm:px-6 lg:px-8 mt-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
        <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100 tracking-tight">
          My Projects
        </h1>
        <div className="flex flex-col sm:flex-row gap-3 sm:gap-4 mt-1 sm:mt-0">
          <div className="flex-1 sm:min-w-[240px]">
            <Input
              placeholder="Search projects..."
              value={q}
              onChange={(e) => setQ(e.target.value)}
              className="w-full rounded-xl border-slate-300 dark:border-slate-600"
            />
          </div>
          <div className="flex flex-wrap gap-3">
            {can("create-project") && (
              <a
                {...linkProps({ name: "newProject" })}
                className="inline-flex items-center justify-center rounded-xl px-5 py-2.5 text-sm font-semibold shadow-md hover:shadow-lg transition-all focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-emerald-500 bg-emerald-600 hover:bg-emerald-700 text-white dark:bg-emerald-600 dark:hover:bg-emerald-500"
              >
                New Project
              </a>
            )}
            {can("user-management") && (
              <a
                {...linkProps({ name: "userAdmin" })}
                className="inline-flex items-center justify-center rounded-xl px-5 py-2.5 text-sm font-semibold border-2 border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 hover:border-slate-400 dark:hover:border-slate-500 transition-all focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-slate-400 shadow-sm"
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
              className="inline-flex items-center justify-center rounded-xl px-5 py-2.5 text-sm font-semibold border-2 border-amber-400 dark:border-amber-500 text-amber-800 dark:text-amber-200 bg-amber-50 dark:bg-amber-900/30 hover:bg-amber-100 dark:hover:bg-amber-900/50 hover:border-amber-500 dark:hover:border-amber-400 transition-all focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-amber-400 shadow-sm"
            >
              Change Password & Information
            </a>
          </div>
        </div>
      </div>

      {/* Filters & sorting */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-2">
        <div className="flex flex-col sm:flex-row gap-2 sm:items-center md:justify-end w-full">
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500 dark:text-slate-400">
              Status
            </span>
            <Select
              value={statusFilter}
              onChange={setStatusFilter}
              options={[
                { value: "all", label: "All statuses" },
                { value: "planning", label: "Planning" },
                { value: "design", label: "Design" },
                { value: "implementation", label: "Implementation" },
                { value: "testing", label: "Testing" },
                { value: "production", label: "Production" },
                { value: "maintenance", label: "Maintenance" },
                { value: "shared", label: "Shared" },
                { value: "inactive", label: "Inactive" },
                { value: "archived", label: "Archived" },
              ]}
            />
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500 dark:text-slate-400">
              Sort by
            </span>
            <Select
              value={sortBy}
              onChange={setSortBy}
              options={[
                { value: "updated_desc", label: "Last updated (newest first)" },
                { value: "name_asc", label: "Name (A → Z)" },
                { value: "devices_desc", label: "Devices (most first)" },
                { value: "status_asc", label: "Status (A → Z)" },
              ]}
            />
          </div>
          {(statusFilter !== "all" || sortBy !== "updated_desc" || q.trim()) && (
            <Button
              variant="secondary"
              size="sm"
              onClick={() => {
                setStatusFilter("all");
                setSortBy("updated_desc");
                setQ("");
              }}
              className="text-xs"
            >
              Clear filters
            </Button>
          )}
        </div>
      </div>

      {/* Project grid */}
      {visible.length === 0 ? (
        <div className="flex-1 flex items-center justify-center rounded-2xl border border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-900/30 py-16 px-6">
          <div className="text-center max-w-sm">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-slate-200 dark:bg-slate-700 flex items-center justify-center text-slate-500 dark:text-slate-400">
              <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
              </svg>
            </div>
            <p className="text-slate-600 dark:text-slate-400 font-medium">
              {q ? "No projects match your search." : "No projects yet."}
            </p>
            <p className="text-sm text-slate-500 dark:text-slate-500 mt-1">
              {q ? "Try a different search term." : "Create a project to get started."}
            </p>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-6">
          {visible.map((p) => (
            <Card
              key={p.id || p.project_id}
              className="overflow-hidden flex flex-col hover:shadow-xl transition-all duration-300 hover:-translate-y-0.5 border-slate-200 dark:border-slate-700"
              title={
                <div className="flex items-center justify-between gap-2 w-full min-w-0">
                  <span className="truncate font-semibold text-slate-800 dark:text-slate-100" title={safeDisplay(p.name)}>
                    {safeDisplay(p.name)}
                  </span>
                  <span className="flex-shrink-0">
                    <Badge
                      className={
                        (p.status || "").toLowerCase() === "shared"
                          ? "bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-200"
                          : (p.status || "").toLowerCase() === "inactive" || (p.status || "").toLowerCase() === "archived"
                          ? "bg-slate-200 text-slate-700 dark:bg-slate-600 dark:text-slate-200"
                          : (p.status || "").toLowerCase() === "production"
                          ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-200"
                          : "bg-slate-100 text-slate-700 dark:bg-slate-600 dark:text-slate-200"
                      }
                    >
                      {safeDisplay(p.status) || "—"}
                    </Badge>
                  </span>
                </div>
              }
            >
              {/* Topology image or placeholder */}
              <div className="-mx-5 -mt-3 mb-4">
                {(p.topoUrl || p.topo_url) ? (
                  <div className="h-44 w-full rounded-xl overflow-hidden border border-slate-200 dark:border-slate-700 bg-slate-100 dark:bg-slate-800 flex items-center justify-center">
                    <img
                      src={p.topoUrl || p.topo_url}
                      alt="Topology"
                      className="w-full h-full object-contain"
                      style={{ imageRendering: "auto" }}
                    />
                  </div>
                ) : (
                  <div className="h-44 w-full rounded-xl border border-slate-200 dark:border-slate-700 bg-gradient-to-br from-slate-100 to-slate-200 dark:from-slate-800 dark:to-slate-900 flex items-center justify-center">
                    <div className="text-center text-slate-400 dark:text-slate-500 p-4">
                      <svg
                        className="w-14 h-14 mx-auto mb-2 opacity-70"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={1.5}
                          d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
                        />
                      </svg>
                      <p className="text-xs font-medium">No topology image</p>
                    </div>
                  </div>
                )}
              </div>

              {/* Description (if any) */}
              {p.desc != null && String(p.desc).trim() !== "" && (
                <p className="text-sm text-slate-600 dark:text-slate-400 line-clamp-2 mb-3">
                  {safeDisplay(p.desc)}
                </p>
              )}

              {/* Metadata: status, manager, updated, devices (real data) */}
              <div className="flex flex-wrap gap-x-5 gap-y-2 text-xs text-slate-500 dark:text-slate-400 pt-2 border-t border-slate-200 dark:border-slate-700">
                <span className="flex items-center gap-1.5" title="Status">
                  <svg className="w-4 h-4 text-slate-400 dark:text-slate-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <span className="font-medium text-slate-700 dark:text-slate-300">{safeDisplay(p.status) || "—"}</span>
                </span>
                <span className="flex items-center gap-1.5" title="Manager">
                  <svg className="w-4 h-4 text-slate-400 dark:text-slate-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                  </svg>
                  <span className="font-medium text-slate-700 dark:text-slate-300">{safeDisplay(p.manager) || "—"}</span>
                </span>
                <span className="flex items-center gap-1.5" title="Last updated">
                  <svg className="w-4 h-4 text-slate-400 dark:text-slate-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <span>{safeDisplay(p.updated) || "—"}</span>
                </span>
                <span className="flex items-center gap-1.5" title="Devices">
                  <svg className="w-4 h-4 text-slate-400 dark:text-slate-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                  </svg>
                  <span>
                    <strong className="text-slate-700 dark:text-slate-300">{typeof p.devices === "number" ? p.devices : (safeDisplay(p.devices) === "—" ? 0 : safeDisplay(p.devices))}</strong>
                    {" "}devices
                  </span>
                </span>
              </div>

              {/* Open Project */}
              <div className="pt-4 mt-auto">
                <a
                  href={
                    p.project_id || p.id
                      ? routeToHash
                        ? routeToHash({ name: "project", projectId: p.project_id || p.id, tab: "summary" })
                        : "#/"
                      : "#/"
                  }
                  onClick={(e) =>
                    handleNavClick(e, () => {
                      if (p.project_id || p.id)
                        setRoute({ name: "project", projectId: p.project_id || p.id, tab: "summary" });
                      else console.error("Project missing project_id:", p);
                    })
                  }
                  className="flex items-center justify-center w-full rounded-xl py-3 px-4 text-sm font-semibold bg-slate-800 dark:bg-slate-200 text-white dark:text-slate-900 hover:bg-slate-700 dark:hover:bg-slate-100 shadow-md hover:shadow-lg transition-all focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-slate-500"
                >
                  Open Project
                </a>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
