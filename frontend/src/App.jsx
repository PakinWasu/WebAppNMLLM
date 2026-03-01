// src/App.jsx
import React, { useMemo, useState, useEffect, useRef } from "react";
import { flushSync } from "react-dom";
import * as api from "./api";
import MainLayout from "./components/layout/MainLayout";
import Header from "./components/layout/Header";
import { Badge, Button, Card, CodeBlock, ConfirmationModal, Field, Input, NotificationModal, PasswordInput, Select, SelectWithOther, Table, ToastContainer } from "./components/ui";
import { RoutingSection } from "./components/RoutingSection";
import { parseHash } from "./utils/routing";
import { formatDateTime, formatDate, formatFilenameDate, safeDisplay, safeChild, formatError } from "./utils/format";
import { CMDSET, SAMPLE_CORE_SW1, SAMPLE_DIST_SW2, createUploadRecord } from "./utils/constants";
import { globalPollingService, notifyLLMResultReady } from "./services/llmPolling";
import { useHashRoute, useLLMQueue } from "./hooks";
import { useToast } from "./hooks/useToast";
import Login from "./pages/Login";
import ForgotPassword from "./pages/ForgotPassword";
import ChangePassword from "./pages/ChangePassword";
import ProjectIndex from "./pages/ProjectIndex";
import NewProjectPage from "./pages/NewProjectPage";
import UserAdminPage from "./pages/UserAdminPage";
import SettingPage from "./pages/SettingPage";
import { fileToDataURL } from "./utils/file";
import AddMemberInline from "./components/AddMemberInline";
import { Activity, Share2, Shield, CheckCircle2, Info } from "lucide-react";

/**
 * Renders LLM summary text as Markdown-style bullet list with styled bold keys.
 * - Bullet lines (starting with * or -) become list items with spacing.
 * - **Key:** is rendered in a brighter color (e.g. text-sky-400); other **bold** stays bold.
 * - leading-relaxed and vertical spacing for readability; content kept inside card (break-words).
 */
function SummaryMarkdown({ text, className = "", size = "sm" }) {
  if (text == null || String(text).trim() === "") return null;
  const raw = String(text);
  const lines = raw.split(/\r?\n/).map((l) => l.trim()).filter((l) => l.length > 0);
  const textSize = size === "xs" ? "text-xs" : "text-sm";
  const keyClass = "text-sky-400 dark:text-sky-400 font-semibold";

  function renderLineContent(lineContent, lineIdx) {
    const parts = lineContent.split(/(\*\*[^*]+\*\*)/g);
    return parts.map((part, i) => {
      if (part.startsWith("**") && part.endsWith("**")) {
        const inner = part.slice(2, -2);
        const isKey = inner.endsWith(":");
        return (
          <span key={`${lineIdx}-${i}`} className={isKey ? keyClass : "font-semibold text-inherit"}>
            {inner}
          </span>
        );
      }
      return part;
    });
  }

  return (
    <ul
      className={`list-disc list-inside space-y-2 leading-relaxed break-words overflow-hidden ${textSize} text-slate-800 dark:text-slate-300 ${className}`}
      style={{ marginLeft: "0.25rem" }}
    >
      {lines.map((line, idx) => {
        const lineContent = line.replace(/^[\s*\-]+\s*/, "");
        return (
          <li key={idx} className="pl-0.5">
            {renderLineContent(lineContent, idx)}
          </li>
        );
      })}
    </ul>
  );
}

/** Dashboard widget for structured Network Overview (summaryData from backend).
 *  Supports new 9-section format and legacy format for backward compatibility.
 */
function StructuredNetworkOverview({ data, className = "" }) {
  if (!data || typeof data !== "object") return null;

  const health = (data.health_status || "Unknown").toString();
  const isHealthy = /healthy/i.test(health);
  const isWarning = /warning/i.test(health);

  // Section color configs (9 sections with distinct colors like AI Recommendations)
  const sectionColors = {
    overview: { bg: "rgba(59, 130, 246, 0.15)", border: "#3b82f6", badge: "bg-blue-500" },      // Blue
    interfaces: { bg: "rgba(6, 182, 212, 0.15)", border: "#06b6d4", badge: "bg-cyan-500" },      // Cyan
    vlans: { bg: "rgba(99, 102, 241, 0.15)", border: "#6366f1", badge: "bg-indigo-500" },    // Indigo
    stp: { bg: "rgba(168, 85, 247, 0.15)", border: "#a855f7", badge: "bg-purple-500" },    // Purple
    routing: { bg: "rgba(34, 197, 94, 0.15)", border: "#22c55e", badge: "bg-green-500" },     // Green
    neighbors: { bg: "rgba(20, 184, 166, 0.15)", border: "#14b8a6", badge: "bg-teal-500" },      // Teal
    mac_arp: { bg: "rgba(249, 115, 22, 0.15)", border: "#f97316", badge: "bg-orange-500" },    // Orange
    security: { bg: "rgba(244, 63, 94, 0.15)", border: "#f43f5e", badge: "bg-rose-500" },      // Rose
    ha: { bg: "rgba(234, 179, 8, 0.15)", border: "#eab308", badge: "bg-yellow-500" },    // Yellow
  };
  const sectionOrder = ["overview", "interfaces", "vlans", "stp", "routing", "neighbors", "mac_arp", "security", "ha"];

  // New section format - vertical layout like Recommendations
  if (data.sections && typeof data.sections === "object") {
    const availableSections = Object.keys(data.sections);
    const hasAnySections = availableSections.some((key) => {
      const section = data.sections[key];
      return section?.summary && section.summary.trim() !== "";
    });

    if (!hasAnySections) {
      return (
        <div className={`text-slate-500 dark:text-slate-400 italic text-sm ${className}`}>
          No overview data available. Click the AI button to generate.
        </div>
      );
    }

    return (
      <div className={`space-y-3 ${className}`}>
        {/* Section Cards - Vertical layout like Recommendations */}
        {availableSections.map((key) => {
          const section = data.sections[key];
          if (!section) return null;
          const colors = sectionColors[key] || sectionColors.overview;
          const hasContent = section.summary && section.summary.trim() !== "";
          const hasHighlights = Array.isArray(section.highlights) && section.highlights.length > 0;

          // Skip sections with no content
          if (!hasContent && !hasHighlights) return null;

          return (
            <div
              key={key}
              className="p-3 rounded-lg border break-words"
              style={{ backgroundColor: colors.bg, borderColor: colors.border }}
            >
              {/* Section Title Badge */}
              <div className="flex items-start gap-2 mb-1.5">
                <span className={`text-sm font-semibold px-2 py-0.5 rounded text-white ${colors.badge}`}>
                  {section.title || key}
                </span>
              </div>
              {/* Summary */}
              {hasContent && (
                <div className="text-slate-700 dark:text-slate-300 mb-1.5">
                  {section.summary}
                </div>
              )}
              {/* Highlights */}
              {hasHighlights && (
                <div className="text-slate-700 dark:text-slate-200">
                  <span className="font-semibold">Key Points:</span>
                  <ul className="mt-1 ml-4 space-y-0.5 list-disc">
                    {section.highlights.map((h, i) => (
                      <li key={i} className="text-sm">{h}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          );
        })}
      </div>
    );
  }

  // Legacy format (backward compatible)
  const topology = data.topology || {};
  const protocols = Array.isArray(data.protocols) ? data.protocols : [];
  const insights = Array.isArray(data.key_insights) ? data.key_insights : [];
  const recommendations = Array.isArray(data.recommendations) ? data.recommendations : [];
  const mainProtocol = protocols.length > 0 ? protocols[0] : "—";
  const topologyType = topology.type || "—";

  return (
    <div className={`grid grid-cols-1 md:grid-cols-2 gap-4 text-sm ${className}`}>
      {/* Top row: 3 key stat badges */}
      <div className="md:col-span-2 grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div className="flex items-center gap-2 rounded-lg bg-slate-800/50 dark:bg-slate-800/50 border border-slate-700/50 dark:border-slate-600/50 px-3 py-2.5">
          <Activity className="w-4 h-4 flex-shrink-0 text-slate-400 dark:text-slate-400" aria-hidden />
          <div className="min-w-0 flex-1">
            <div className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">Health</div>
            <div className="flex items-center gap-1.5 truncate">
              <span className={`w-2 h-2 rounded-full flex-shrink-0 ${isHealthy ? "bg-green-500" : isWarning ? "bg-amber-500" : "bg-red-500"}`} aria-hidden />
              <span className="text-slate-200 dark:text-slate-300 truncate">{health}</span>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2 rounded-lg bg-slate-800/50 dark:bg-slate-800/50 border border-slate-700/50 dark:border-slate-600/50 px-3 py-2.5">
          <Share2 className="w-4 h-4 flex-shrink-0 text-slate-400 dark:text-slate-400" aria-hidden />
          <div className="min-w-0 flex-1">
            <div className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">Topology</div>
            <div className="text-slate-200 dark:text-slate-300 truncate">{topologyType}</div>
          </div>
        </div>
        <div className="flex items-center gap-2 rounded-lg bg-slate-800/50 dark:bg-slate-800/50 border border-slate-700/50 dark:border-slate-600/50 px-3 py-2.5">
          <Shield className="w-4 h-4 flex-shrink-0 text-slate-400 dark:text-slate-400" aria-hidden />
          <div className="min-w-0 flex-1">
            <div className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">Protocol</div>
            <div className="text-slate-200 dark:text-slate-300 truncate">{mainProtocol}</div>
          </div>
        </div>
      </div>

      {/* Middle: Insight items */}
      <div className="space-y-2">
        <div className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-2">Insights</div>
        {insights.length > 0 ? (
          <div className="space-y-2">
            {insights.map((item, i) => (
              <div key={i} className="flex items-start gap-2">
                {i === 0 ? (
                  <CheckCircle2 className="w-4 h-4 flex-shrink-0 text-green-500 dark:text-green-500 mt-0.5" aria-hidden />
                ) : (
                  <Info className="w-4 h-4 flex-shrink-0 text-blue-400 dark:text-blue-400 mt-0.5" aria-hidden />
                )}
                <span className="text-slate-300 dark:text-slate-300 text-sm leading-snug">{item}</span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-slate-500 dark:text-slate-500 text-sm">No insights available.</p>
        )}
      </div>

      {/* Bottom: Recommendations */}
      <div className="space-y-2">
        <div className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-2">Recommendations</div>
        {recommendations.length > 0 ? (
          <div className="rounded-lg bg-slate-800/50 dark:bg-slate-800/50 border-l-4 border-amber-500 pl-3 py-2 pr-2 space-y-1.5">
            {recommendations.map((item, i) => (
              <div key={i} className="text-slate-300 dark:text-slate-300 text-sm leading-snug">{item}</div>
            ))}
          </div>
        ) : (
          <p className="text-slate-500 dark:text-slate-500 text-sm">No recommendations.</p>
        )}
      </div>
    </div>
  );
}

/** Renders structured Device Summary with colored sections (same format as StructuredNetworkOverview). */
function StructuredDeviceSummary({ data, className = "" }) {
  if (!data || typeof data !== "object") return null;

  const sectionColors = {
    overview: { bg: "rgba(59, 130, 246, 0.15)", border: "#3b82f6", badge: "bg-blue-500" },
    interfaces: { bg: "rgba(6, 182, 212, 0.15)", border: "#06b6d4", badge: "bg-cyan-500" },
    vlans: { bg: "rgba(99, 102, 241, 0.15)", border: "#6366f1", badge: "bg-indigo-500" },
    routing: { bg: "rgba(34, 197, 94, 0.15)", border: "#22c55e", badge: "bg-green-500" },
    security: { bg: "rgba(244, 63, 94, 0.15)", border: "#f43f5e", badge: "bg-rose-500" },
  };

  // New section format - vertical layout with colored cards
  if (data.sections && typeof data.sections === "object") {
    const availableSections = Object.keys(data.sections);
    const hasAnySections = availableSections.some((key) => {
      const section = data.sections[key];
      return section?.summary && section.summary.trim() !== "";
    });

    if (!hasAnySections) {
      return (
        <div className={`text-slate-500 dark:text-slate-400 italic text-sm ${className}`}>
          No summary data available. Click the AI button to generate.
        </div>
      );
    }

    return (
      <div className={`space-y-2 ${className}`}>
        {availableSections.map((key) => {
          const section = data.sections[key];
          if (!section) return null;
          const colors = sectionColors[key] || sectionColors.overview;
          const hasContent = section.summary && section.summary.trim() !== "";
          const hasHighlights = Array.isArray(section.highlights) && section.highlights.length > 0;

          if (!hasContent && !hasHighlights) return null;

          return (
            <div
              key={key}
              className="p-2.5 rounded-lg border break-words"
              style={{ backgroundColor: colors.bg, borderColor: colors.border }}
            >
              <div className="flex items-start gap-2 mb-1">
                <span className={`text-xs font-semibold px-1.5 py-0.5 rounded text-white ${colors.badge}`}>
                  {section.title || key}
                </span>
              </div>
              {hasContent && (
                <div className="text-slate-700 dark:text-slate-300 text-xs mb-1">
                  {section.summary}
                </div>
              )}
              {hasHighlights && (
                <div className="text-slate-700 dark:text-slate-200 text-xs">
                  <span className="font-semibold">Key Points:</span>
                  <ul className="mt-0.5 ml-3 space-y-0.5 list-disc">
                    {section.highlights.map((h, i) => (
                      <li key={i}>{h}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          );
        })}
      </div>
    );
  }

  // Legacy format (backward compatible)
  const role = data.role || "—";
  const uptime = data.uptime_human || "N/A";
  const metrics = data.critical_metrics || {};
  const highlights = Array.isArray(data.config_highlights) ? data.config_highlights : [];
  const security = Array.isArray(data.security_issues) ? data.security_issues : [];
  const keyClass = "text-sky-400 dark:text-sky-400 font-semibold";
  return (
    <div className={`space-y-3 leading-relaxed text-xs text-slate-700 dark:text-slate-300 ${className}`}>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        <div><span className={keyClass}>Role:</span> {role}</div>
        <div><span className={keyClass}>Uptime:</span> {uptime}</div>
      </div>
      <div>
        <span className={keyClass}>Metrics:</span> CPU: {metrics.cpu_load ?? "N/A"}, Memory: {metrics.memory ?? "N/A"}
      </div>
      {highlights.length > 0 && (
        <ul className="list-disc list-inside space-y-0.5">
          <span className={keyClass}>Config:</span>
          {highlights.map((item, i) => (
            <li key={i}>{item}</li>
          ))}
        </ul>
      )}
      {security.length > 0 && (
        <ul className="list-disc list-inside space-y-0.5">
          <span className={keyClass}>Security:</span>
          {security.map((item, i) => (
            <li key={i}>{item}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

/* ========= ROOT APP ========= */
export default function App() {
  // Load dark mode preference from localStorage, default to true
  const [dark, setDark] = useState(() => {
    const saved = localStorage.getItem("darkMode");
    return saved !== null ? saved === "true" : true;
  });
  const [users, setUsers] = useState([]);
  const [projects, setProjects] = useState([]);
  const [authedUser, setAuthedUser] = useState(null); // {username, role}
  const { route, setRoute, routeToHash, handleNavClick } = useHashRoute(api.getToken, authedUser);
  const [uploadHistory, setUploadHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [projectAccessDenied, setProjectAccessDenied] = useState(null); // null = checking, true = denied, false = allowed

  // Global LLM queue: one job at a time per project (Summary + More Detail + Topology share this)
  const projectIdForLLM = (route.name === "project" || route.name === "device") ? (route.projectId || "") : "";
  const { llmBusy, requestRun, onComplete, llmBusyMessage } = useLLMQueue(projectIdForLLM);

  // Toast notification system
  const { toasts, success, error, warning, info, removeToast } = useToast();

  // Global confirmation modal state
  const [confirmModal, setConfirmModal] = useState({
    show: false,
    title: "",
    message: "",
    confirmText: "Confirm",
    cancelText: "Cancel",
    variant: "default",
    loading: false,
    onConfirm: null,
  });

  const showConfirmModal = ({ title, message, confirmText = "Confirm", cancelText = "Cancel", variant = "default", onConfirm }) => {
    setConfirmModal({
      show: true,
      title,
      message,
      confirmText,
      cancelText,
      variant,
      loading: false,
      onConfirm,
    });
  };

  const closeConfirmModal = () => {
    if (!confirmModal.loading) {
      setConfirmModal(prev => ({ ...prev, show: false, onConfirm: null }));
    }
  };

  const handleConfirmModalConfirm = async () => {
    if (confirmModal.onConfirm) {
      setConfirmModal(prev => ({ ...prev, loading: true }));
      try {
        await confirmModal.onConfirm();
      } finally {
        setConfirmModal(prev => ({ ...prev, show: false, loading: false, onConfirm: null }));
      }
    }
  };

  // When on project page, verify access (Shared projects: everyone sees in list but only members can open)
  useEffect(() => {
    if (route.name !== "project" || !route.projectId) {
      setProjectAccessDenied(null);
      return;
    }
    setProjectAccessDenied(null);
    let cancelled = false;
    api.getProject(route.projectId)
      .then(() => { if (!cancelled) setProjectAccessDenied(false); })
      .catch((err) => {
        if (!cancelled) {
          const msg = err?.message ? String(err.message) : "";
          const denied = msg.includes("403") || msg.toLowerCase().includes("not a member") || msg.toLowerCase().includes("forbidden");
          setProjectAccessDenied(denied);
        }
      });
    return () => { cancelled = true; };
  }, [route.name, route.projectId]);

  // Apply dark mode class on mount and when dark changes
  useEffect(() => {
    const root = document.documentElement;
    if (dark) {
      root.classList.add("dark");
    } else {
      root.classList.remove("dark");
    }
    // Save preference to localStorage
    localStorage.setItem("darkMode", dark.toString());
  }, [dark]);

  // Load user info on mount if token exists; then apply hash route so refresh keeps position
  useEffect(() => {
    const loadUser = async () => {
      try {
        const user = await api.getMe();
        setAuthedUser({ username: user.username, role: user.role || "admin" });
        const fromHash = parseHash(window.location.hash);
        setRoute(fromHash.name ? fromHash : { name: "index" });
        await loadProjects();
        if (user.role === "admin") {
          await loadUsers();
        }
      } catch (e) {
        // Not logged in
        api.clearToken();
      }
    };
    if (api.getToken()) {
      loadUser();
    }
  }, []);

  const loadUsers = async () => {
    try {
      const data = await api.getUsers();
      setUsers(data);
    } catch (e) {
      console.error("Failed to load users:", e);
    }
  };

  const loadProjects = async () => {
    try {
      setLoading(true);
      const data = await api.getProjects();
      // Transform backend format to frontend format
      const transformed = await Promise.all(data.map(async (p) => {
        const [members, metrics] = await Promise.all([
          api.getProjectMembers(p.project_id).catch(() => []),
          api.getSummaryMetrics(p.project_id).catch(() => null),
        ]);
        // Find manager (first manager or admin, or created_by)
        const manager = members.find(m => m.role === "manager")?.username ||
          members.find(m => m.role === "admin")?.username ||
          p.created_by;
        const deviceCount = metrics?.total_devices ?? 0;
        return {
          id: p.project_id,
          project_id: p.project_id,
          name: p.name,
          desc: p.description || "",
          description: p.description || "",
          manager: manager,
          updated: formatDateTime(p.updated_at || p.created_at),
          status: p.status ?? null,
          members: members.map(m => ({ username: m.username, role: m.role })),
          devices: deviceCount,
          lastBackup: "—",
          services: 0,
          visibility: p.visibility || "Private",
          backupInterval: p.backup_interval || "Daily",
          topoUrl: p.topo_url || "",
          topo_url: p.topo_url || "",
          logs: [],
          summaryRows: [],
          documents: { config: [], others: [] },
          vlanDetails: {},
          uploadHistory: [],
          device_images: p.device_images || {}, // Include device_images from database
          created_at: p.created_at,
          created_by: p.created_by,
          updated_at: p.updated_at || p.created_at,
        };
      }));
      setProjects(transformed);
    } catch (e) {
      console.error("Failed to load projects:", e);
    } finally {
      setLoading(false);
    }
  };

  const can = (perm, project = null) => {
    const userRole = authedUser?.role; // System role (admin only)
    if (!userRole) return false;

    // Get project role if project is provided
    let projectRole = null;
    if (project && project.members && authedUser?.username) {
      const member = project.members.find(m => m.username === authedUser.username);
      projectRole = member?.role; // manager, engineer, viewer
    }

    // System-level permissions (admin only)
    if (perm === "see-all-projects") return userRole === "admin";
    if (perm === "create-project") return userRole === "admin";
    if (perm === "user-management") return userRole === "admin";

    // Project-level permissions
    if (perm === "project-setting-view") {
      return userRole === "admin" || ["manager", "engineer", "viewer", "admin"].includes(projectRole);
    }
    if (perm === "project-setting-edit") {
      return userRole === "admin" || projectRole === "manager";
    }
    if (perm === "manage-folders") {
      return userRole === "admin" || ["manager", "engineer"].includes(projectRole);
    }
    if (perm === "upload-config") {
      return userRole === "admin" || ["manager", "engineer"].includes(projectRole);
    }
    if (perm === "upload-document") {
      return userRole === "admin" || ["manager", "engineer"].includes(projectRole);
    }
    if (perm === "download-document") {
      return userRole === "admin" || ["manager", "engineer"].includes(projectRole);
    }
    if (perm === "delete-document") {
      return userRole === "admin" || ["manager", "engineer"].includes(projectRole);
    }
    if (perm === "run-llm") {
      return userRole === "admin" || ["manager", "engineer"].includes(projectRole);
    }
    if (perm === "edit-topology") {
      return userRole === "admin" || ["manager", "engineer"].includes(projectRole);
    }
    if (perm === "view-documents") {
      return true; // All authenticated users can view documents
    }
    return false;
  };

  const handleLogin = async (username, password) => {
    try {
      await api.login(username, password);
      const user = await api.getMe();
      setAuthedUser({ username: user.username, role: user.role || "admin" });
      const fromHash = parseHash(window.location.hash);
      setRoute(fromHash.name ? fromHash : { name: "index" });
      await loadProjects();
      if (user.role === "admin") {
        await loadUsers();
      }
    } catch (e) {
      alert("Login failed: " + formatError(e));
    }
  };

  const handleLogout = () => {
    api.clearToken();
    setAuthedUser(null);
    setUsers([]);
    setProjects([]);
    setRoute({ name: "login" });
  };

  const memberUsernames = (p) => (p.members || []).map((m) => m.username);
  const isMember = (p, username) => memberUsernames(p).includes(username);

  /* Single-pane layout for Index, Project, and Device (above-the-fold, no outer scroll) */
  if (authedUser && (route.name === "index" || route.name === "project" || route.name === "device")) {
    const project = (route.name === "project" || route.name === "device")
      ? projects.find((p) => (p.project_id || p.id) === route.projectId)
      : null;

    // Build tabs for project view - Setting moved to end
    const projectTabs = [];
    if (project && route.name === "project") {
      if (can("view-documents", project)) {
        projectTabs.push({ id: "summary", label: "Summary", icon: "📊" });
        projectTabs.push({ id: "documents", label: "Documents", icon: "📄" });
        projectTabs.push({ id: "history", label: "History", icon: "📜" });
      }
      if (can("upload-config", project)) {
        projectTabs.push({ id: "script-generator", label: "Command Template", icon: "⚡" });
      }
      if (can("project-setting-view", project)) {
        projectTabs.push({ id: "setting", label: "Setting", icon: "⚙️" });
      }
    }

    return (
      <>
        <ToastContainer toasts={toasts} onClose={removeToast} />
        <ConfirmationModal
          show={confirmModal.show}
          onClose={closeConfirmModal}
          onConfirm={handleConfirmModalConfirm}
          title={confirmModal.title}
          message={confirmModal.message}
          confirmText={confirmModal.confirmText}
          cancelText={confirmModal.cancelText}
          variant={confirmModal.variant}
          loading={confirmModal.loading}
        />
        <MainLayout
          topBar={
            <div className="h-full flex items-center justify-between gap-2 px-3 sm:px-4 border-b border-slate-300 dark:border-slate-800">
              {/* Left: Hamburger menu (mobile/tablet) + Logo + Platform Name + Breadcrumb */}
              <div className="flex items-center gap-2 sm:gap-4 flex-1 min-w-0">
                {/* Hamburger menu button - show on mobile/tablet (lg-), hide on desktop (lg+) */}
                {project && projectTabs.length > 0 && (
                  <button
                    onClick={() => {
                      const event = new CustomEvent('toggleSideNav');
                      window.dispatchEvent(event);
                    }}
                    className="lg:hidden p-2 rounded-lg text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-slate-900 dark:hover:text-slate-200 transition-colors flex-shrink-0"
                    aria-label="Open navigation menu"
                  >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                    </svg>
                  </button>
                )}
                <a
                  href="#/"
                  onClick={(e) => handleNavClick(e, () => setRoute({ name: "index" }))}
                  className="flex items-center gap-2 sm:gap-3 hover:opacity-85 transition-opacity cursor-pointer flex-shrink-0"
                >
                  <div className="h-7 w-7 rounded-xl bg-white/90 dark:bg-white/10 backdrop-blur-sm border border-slate-300/80 dark:border-slate-600/80 flex-shrink-0 shadow-sm" />
                  <span className="text-xs sm:text-sm font-semibold text-slate-800 dark:text-slate-200 whitespace-nowrap truncate">Network Project Platform</span>
                </a>
                {/* Breadcrumb and Tabs (show when in project or device) - hide tabs on mobile/tablet, show on desktop */}
                {project && (
                  <>
                    <span className="text-slate-400 dark:text-slate-500 flex-shrink-0">/</span>
                    <div className="flex items-center gap-2 sm:gap-4 flex-1 min-w-0">
                      {route.name === "device" ? (
                        <>
                          <a
                            href={`#/project/${encodeURIComponent(route.projectId)}/tab/summary`}
                            onClick={(e) => handleNavClick(e, () => setRoute({ name: "project", projectId: route.projectId, tab: "summary" }))}
                            className="text-xs sm:text-sm font-medium text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-slate-100 truncate"
                          >
                            {safeDisplay(project?.name)}
                          </a>
                          <span className="text-slate-400 dark:text-slate-500 flex-shrink-0">/</span>
                          <span className="text-xs sm:text-sm font-medium text-slate-700 dark:text-slate-300 truncate">{safeDisplay(route?.device)}</span>
                        </>
                      ) : (
                        <>
                          <span className="text-xs sm:text-sm font-medium text-slate-700 dark:text-slate-300 truncate">{safeDisplay(project?.name)}</span>
                          {/* Tabs - hidden on mobile/tablet (lg-), shown on desktop (lg+) */}
                          {projectTabs.length > 0 && (
                            <nav className="hidden lg:flex items-center gap-1 ml-2 sm:ml-4 flex-wrap" aria-label="Project tabs">
                              {projectTabs.map((t) => (
                                <a
                                  key={t.id}
                                  href={`#/project/${encodeURIComponent(route.projectId)}/tab/${encodeURIComponent(t.id)}`}
                                  onClick={(e) => handleNavClick(e, () => setRoute({ ...route, tab: t.id }))}
                                  className={`flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium transition rounded-xl whitespace-nowrap border ${(route.tab || "summary") === t.id
                                    ? "bg-white/90 dark:bg-white/10 backdrop-blur-sm border-slate-300/80 dark:border-slate-600/80 text-slate-800 dark:text-slate-100 shadow-sm"
                                    : "bg-transparent dark:bg-transparent border-transparent text-slate-600 dark:text-slate-400 hover:bg-slate-100/90 dark:hover:bg-slate-800/60 hover:border-slate-300 dark:hover:border-slate-700"
                                    }`}
                                  title={`Go to ${t.label}`}
                                >
                                  <span>{safeDisplay(t.icon)}</span>
                                  <span className="hidden xs:inline">{safeDisplay(t.label)}</span>
                                </a>
                              ))}
                            </nav>
                          )}
                        </>
                      )}
                    </div>
                  </>
                )}
              </div>
              {/* Right: Dark mode + User + Sign out */}
              <div className="flex items-center gap-2 flex-shrink-0">
                <Button variant="ghost" className="text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200" onClick={() => setDark(!dark)} title={dark ? "Light mode" : "Dark mode"}>
                  {dark ? "🌙" : "☀️"}
                </Button>
                <span className="text-xs text-slate-500 dark:text-slate-400 hidden sm:inline truncate max-w-[100px]">{safeDisplay(authedUser?.username)}</span>
                <a
                  href="#/login"
                  onClick={(e) => handleNavClick(e, handleLogout)}
                  className="inline-flex items-center justify-center rounded-lg px-3 py-1.5 text-xs font-medium shadow-sm transition focus:outline-none focus:ring-2 focus:ring-offset-2 bg-white text-gray-900 ring-1 ring-gray-300 hover:bg-gray-50 focus:ring-blue-500 dark:bg-gray-800 dark:text-gray-100 dark:ring-gray-600 dark:hover:bg-gray-700"
                >
                  Sign out
                </a>
              </div>
            </div>
          }
          sideNavigation={
            project && projectTabs.length > 0 ? (
              <nav className="flex flex-col gap-1 px-2">
                {projectTabs.map((t) => {
                  const isActive = (route.tab || "summary") === t.id;
                  return (
                    <a
                      key={t.id}
                      href={`#/project/${encodeURIComponent(project.project_id || project.id)}/tab/${encodeURIComponent(t.id)}`}
                      onClick={(e) => {
                        e.preventDefault();
                        handleNavClick(e, () => {
                          setRoute({ ...route, tab: t.id });
                          // Close side nav after navigation
                          setTimeout(() => {
                            window.dispatchEvent(new CustomEvent('closeSideNav'));
                          }, 100);
                        });
                      }}
                      className={`
                      flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-all
                      ${isActive
                          ? "bg-indigo-50 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 shadow-sm"
                          : "text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-slate-900 dark:hover:text-slate-200"
                        }
                    `}
                    >
                      <span className="text-lg">{safeDisplay(t.icon)}</span>
                      <span className="flex-1">{safeDisplay(t.label)}</span>
                      {isActive && (
                        <span className="text-indigo-600 dark:text-indigo-400">▶</span>
                      )}
                    </a>
                  );
                })}
              </nav>
            ) : null
          }
          mainClassName="bg-slate-50 dark:bg-slate-950"
        >
          {route.name === "index" && (
            <ProjectIndex
              authedUser={authedUser}
              can={can}
              projects={projects}
              setRoute={setRoute}
              routeToHash={routeToHash}
              isMember={isMember}
              handleNavClick={handleNavClick}
            />
          )}
          {route.name === "project" && project && projectAccessDenied === true && (
            <div className="flex-1 flex flex-col items-center justify-center p-8 text-center">
              <p className="text-slate-600 dark:text-slate-300 font-medium mb-2">You are not a member of this project.</p>
              <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">Only members can open and view its content.</p>
              <a
                href="#/"
                onClick={(e) => handleNavClick(e, () => setRoute({ name: "index" }))}
                className="inline-flex items-center justify-center rounded-xl px-4 py-2 text-sm font-medium bg-slate-200 dark:bg-slate-700 text-slate-800 dark:text-slate-200 hover:bg-slate-300 dark:hover:bg-slate-600"
              >
                Back to My Projects
              </a>
            </div>
          )}
          {route.name === "project" && project && projectAccessDenied === false && (
            <ProjectView
              project={project}
              tab={route.tab || "summary"}
              onChangeTab={(tab) => setRoute({ ...route, tab })}
              openDevice={(device) => setRoute({ name: "device", projectId: route.projectId, device })}
              goIndex={() => setRoute({ name: "index" })}
              setProjects={setProjects}
              uploadHistory={uploadHistory}
              setUploadHistory={setUploadHistory}
              can={can}
              authedUser={authedUser}
              llmBusy={llmBusy}
              llmBusyMessage={llmBusyMessage}
              requestRun={requestRun}
              onComplete={onComplete}
              routeToHash={routeToHash}
              handleNavClick={handleNavClick}
              toast={{ success, error, warning, info }}
              showConfirmModal={showConfirmModal}
            />
          )}
          {route.name === "project" && project && projectAccessDenied === null && (
            <div className="flex-1 flex items-center justify-center p-8">
              <span className="text-sm text-slate-500 dark:text-slate-400">Checking access...</span>
            </div>
          )}
          {route.name === "project" && !project && (
            <div className="p-6 text-sm text-rose-400">Project not found.</div>
          )}
          {route.name === "device" && project && route.device && (
            <DeviceDetailsPage
              project={project}
              deviceId={route.device}
              goBack={() => setRoute({ name: "project", projectId: route.projectId, tab: "summary" })}
              goIndex={() => setRoute({ name: "index" })}
              goBackHref={routeToHash({ name: "project", projectId: route.projectId, tab: "summary" })}
              goIndexHref="#/"
              can={can}
              loadProjects={loadProjects}
              uploadHistory={uploadHistory}
              authedUser={authedUser}
              setProjects={setProjects}
              llmBusy={llmBusy}
              llmBusyMessage={llmBusyMessage}
              requestRun={requestRun}
              onComplete={onComplete}
              showConfirmModal={showConfirmModal}
            />
          )}
        </MainLayout>
      </>
    );
  }

  return (
    <div
      className="min-h-screen bg-slate-50 text-slate-900 dark:bg-[#0B0F19] dark:text-slate-100"
    >
      <div className="mx-auto max-w-[1440px] px-4 pt-4 pb-2 sm:px-6 sm:pt-6 sm:pb-3">
        <Header
          dark={dark}
          setDark={setDark}
          authedUser={authedUser}
          setRoute={setRoute}
          onLogout={handleLogout}
          routeToHash={routeToHash}
          handleNavClick={handleNavClick}
          pageTitle={
            route.name === "newProject"
              ? "Create New Project"
              : route.name === "userAdmin"
                ? "User Administration"
                : route.name === "index"
                  ? "My Projects"
                  : ""
          }
        />
      </div>
      <div className="mx-auto max-w-[1440px] px-4 pt-2 pb-4 sm:px-6 sm:pt-3 sm:pb-6">
        <div className="mt-2 sm:mt-3">
          {(!authedUser && route.name !== "changePassword" && route.name !== "forgotPassword") && (
            <Login
              onLogin={handleLogin}
              onForgotPassword={() => setRoute({ name: "forgotPassword" })}
            />
          )}
          {route.name === "forgotPassword" && (
            <ForgotPassword
              goBack={() => setRoute({ name: "login" })}
            />
          )}
          {route.name === "changePassword" && (
            <ChangePassword
              initialUsername={route.username || authedUser?.username || ""}
              isLoggedIn={!!authedUser}
              authedUser={authedUser}
              goBack={() => {
                if (route.fromIndex && authedUser) {
                  // Go back to index if changing password from logged in state
                  setRoute({ name: "index" });
                } else {
                  // Clear token if changing password from login page
                  if (!authedUser) {
                    api.clearToken();
                  }
                  setRoute({ name: "login" });
                }
              }}
            />
          )}

          {authedUser && route.name === "index" && (
            <ProjectIndex
              authedUser={authedUser}
              can={can}
              projects={projects}
              setRoute={setRoute}
              routeToHash={routeToHash}
              isMember={isMember}
              handleNavClick={handleNavClick}
            />
          )}
          {authedUser &&
            route.name === "newProject" &&
            can("create-project") && (
              <div className="-mt-2 sm:-mt-3">
                <NewProjectPage
                  indexHref="#/"
                  authedUser={authedUser}
                  onCancel={() => setRoute({ name: "index" })}
                  onCreate={async (proj) => {
                    await loadProjects();
                    setRoute({ name: "index" });
                  }}
                  handleNavClick={handleNavClick}
                />
              </div>
            )}
          {authedUser &&
            route.name === "userAdmin" &&
            can("user-management") && (
              <div className="-mt-2 sm:-mt-3">
                <UserAdminPage
                  indexHref="#/"
                  users={users}
                  setUsers={setUsers}
                  onClose={async () => {
                    await loadUsers();
                    setRoute({ name: "index" });
                  }}
                  handleNavClick={handleNavClick}
                />
              </div>
            )}
          {authedUser && route.name === "project" && (
            <ProjectView
              can={can}
              authedUser={authedUser}
              project={projects.find((p) => (p.project_id || p.id) === route.projectId)}
              tab={route.tab || "setting"}
              onChangeTab={(tab) => setRoute({ ...route, tab })}
              openDevice={(device) => {
                setRoute({ name: "device", projectId: route.projectId, device });
              }}
              goIndex={() => setRoute({ name: "index" })}
              setProjects={setProjects}
              uploadHistory={uploadHistory}
              setUploadHistory={setUploadHistory}
              llmBusy={llmBusy}
              llmBusyMessage={llmBusyMessage}
              requestRun={requestRun}
              onComplete={onComplete}
              routeToHash={routeToHash}
              handleNavClick={handleNavClick}
              showConfirmModal={showConfirmModal}
            />
          )}
          {authedUser && route.name === "device" && (
            <DeviceDetailsPage
              project={projects.find((p) => (p.project_id || p.id) === route.projectId)}
              deviceId={route.device}
              goBack={() => setRoute({ name: "project", projectId: route.projectId, tab: "summary" })}
              goIndex={() => setRoute({ name: "index" })}
              goBackHref={routeToHash({ name: "project", projectId: route.projectId, tab: "summary" })}
              goIndexHref="#/"
              can={can}
              loadProjects={loadProjects}
              uploadHistory={uploadHistory}
              authedUser={authedUser}
              setProjects={setProjects}
              llmBusy={llmBusy}
              llmBusyMessage={llmBusyMessage}
              requestRun={requestRun}
              onComplete={onComplete}
              showConfirmModal={showConfirmModal}
            />
          )}
        </div>
      </div>
    </div>
  );
}

/* ========= PROJECT VIEW (Sidebar + pages) ========= */
const ProjectView = ({
  can,
  authedUser,
  project,
  tab,
  onChangeTab,
  openDevice,
  goIndex,
  setProjects,
  uploadHistory,
  setUploadHistory,
  llmBusy,
  llmBusyMessage,
  requestRun,
  onComplete,
  routeToHash,
  handleNavClick,
  toast,
  showConfirmModal,
}) => {
  if (!project)
    return <div className="text-sm text-rose-400">Project not found</div>;

  const projectId = project?.project_id || project?.id;
  const [llmNotification, setLlmNotification] = React.useState(null);

  // Show tabs based on permissions - Setting moved to end
  const tabs = [];
  if (can("view-documents", project)) {
    tabs.push({ id: "summary", label: "Summary", icon: "📊" });
    tabs.push({ id: "documents", label: "Documents", icon: "📄" });
    tabs.push({ id: "history", label: "History", icon: "📜" });
  }
  if (can("upload-config", project)) {
    tabs.push({ id: "script-generator", label: "Command Template", icon: "⚡" });
  }
  if (can("project-setting-view", project)) {
    tabs.push({ id: "setting", label: "Setting", icon: "⚙️" });
  }

  return (
    <div className="h-full flex flex-col min-h-0">
      {/* Global LLM completion popup — shows even when user is on Documents/History so they see result without switching back */}
      {llmNotification?.show && (
        <NotificationModal
          show={true}
          onClose={() => setLlmNotification((n) => n ? { ...n, show: false } : null)}
          title={llmNotification.title || "LLM Complete"}
          message={llmNotification.message || ""}
          metrics={llmNotification.metrics}
          type={llmNotification.type || "success"}
          onRegenerate={llmNotification.onRegenerate}
        />
      )}
      {/* Main content - full width (header is now in MainLayout topBar) */}
      <main className="flex-1 min-h-0 overflow-y-auto flex flex-col gap-3 px-4 py-3">
        {tab === "setting" && can("project-setting-view", project) && (
          <SettingPage
            project={project}
            setProjects={setProjects}
            authedUser={authedUser}
            goIndex={goIndex}
          />
        )}
        {tab === "summary" && can("view-documents", project) && (
          <div className="flex-1 min-h-0 overflow-y-auto flex flex-col">
            <SummaryPage
              project={project}
              projectId={projectId}
              routeToHash={routeToHash}
              handleNavClick={handleNavClick}
              can={can}
              authedUser={authedUser}
              setProjects={setProjects}
              openDevice={openDevice}
              llmBusy={llmBusy}
              llmBusyMessage={llmBusyMessage}
              requestRun={requestRun}
              onComplete={onComplete}
              setLlmNotification={setLlmNotification}
              showConfirmModal={showConfirmModal}
            />
          </div>
        )}
        {tab === "documents" && can("view-documents", project) && (
          <div className="flex-1 min-h-0 overflow-y-auto flex flex-col">
            <DocumentsPage
              project={project}
              can={can}
              authedUser={authedUser}
              uploadHistory={uploadHistory}
              setUploadHistory={setUploadHistory}
              setProjects={setProjects}
              showConfirmModal={showConfirmModal}
            />
          </div>
        )}
        {tab === "history" && can("view-documents", project) && (
          <div className="flex-1 min-h-0 overflow-hidden flex flex-col">
            <HistoryPage
              project={project}
              can={can}
              authedUser={authedUser}
            />
          </div>
        )}
        {tab === "script-generator" && can("upload-config", project) && (
          <div className="flex-1 min-h-0 overflow-y-auto flex flex-col">
            <ScriptGeneratorPage
              project={project}
              can={can}
              authedUser={authedUser}
              toast={toast}
              showConfirmModal={showConfirmModal}
            />
          </div>
        )}
      </main>
    </div>
  );
};

/* ========= OVERVIEW ========= */
/* ========= OVERVIEW ========= */
const OverviewPage = ({ project, uploadHistory }) => {
  const [searchActivity, setSearchActivity] = useState("");
  const [filterActivityWho, setFilterActivityWho] = useState("all");
  const [filterActivityWhat, setFilterActivityWhat] = useState("all");

  // Combine project logs with upload history
  const allHistory = [
    ...(project.logs || []).map(log => ({
      time: log.time,
      files: log.target,
      who: log.user,
      what: log.action,
      where: '—',
      when: '—',
      why: '—',
      description: '—',
      type: 'log',
      details: null,
      uploadRecord: null
    })),
    ...(uploadHistory || []).filter(upload => upload.project === project.id).map(upload => ({
      time: formatDateTime(upload.timestamp),
      files: upload.files.map(f => f.name).join(', '),
      who: upload.details?.who || upload.user,
      what: upload.details?.what || '',
      where: upload.details?.where || '',
      when: upload.details?.when || '',
      why: upload.details?.why || '',
      description: upload.details?.description || '',
      type: 'upload',
      details: upload.details,
      uploadRecord: upload
    }))
  ].sort((a, b) => new Date(b.time) - new Date(a.time));

  const uniqueActivityWhos = [...new Set(allHistory.map(h => h.who))];
  const uniqueActivityWhats = [...new Set(allHistory.map(h => h.what))];

  const combinedHistory = useMemo(() => {
    return allHistory.filter(activity => {
      const matchSearch = !searchActivity.trim() ||
        [activity.files, activity.who, activity.what, activity.where, activity.description].some(v =>
          (v || "").toLowerCase().includes(searchActivity.toLowerCase())
        );
      const matchWho = filterActivityWho === "all" || activity.who === filterActivityWho;
      const matchWhat = filterActivityWhat === "all" || activity.what === filterActivityWhat;
      return matchSearch && matchWho && matchWhat;
    }).slice(0, 10); // Show only latest 10
  }, [allHistory, searchActivity, filterActivityWho, filterActivityWhat]);

  return (
    <div className="grid gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">Overview</h2>
          <div className="text-sm text-gray-500 dark:text-gray-400">
            Last updated: {safeDisplay(project?.updated)} · Manager: {safeDisplay(project?.manager)}
          </div>
        </div>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <Card title="Total Devices"><div className="text-3xl font-semibold">{safeDisplay(project?.devices)}</div></Card>
        <Card title="Last Backup"><div className="text-3xl font-semibold">{safeDisplay(project?.lastBackup)}</div></Card>
        <Card title="Team Members"><div className="text-3xl font-semibold">{safeDisplay(project?.members?.length)}</div></Card>
        <Card title="Active Services"><div className="text-3xl font-semibold">{safeDisplay(project?.services)}</div></Card>
      </div>

      {/* Topology */}
      {(project.topoUrl || project.topo_url) && (
        <Card title="Topology Diagram">
          <div className="w-full rounded-xl border border-slate-300 dark:border-gray-700 overflow-hidden bg-gray-50 dark:bg-gray-900/50 flex items-center justify-center p-4">
            <img
              src={project.topoUrl || project.topo_url}
              alt="Topology"
              className="max-w-full max-h-96 w-auto h-auto object-contain rounded-lg"
              style={{ imageRendering: 'auto' }}
            />
          </div>
        </Card>
      )}

      {/* Drift & Changes (30 days) — all devices in project */}
      <Card title="Drift & Changes (30 days)">
        <div className="grid gap-4">
          {(project.summaryRows || []).map((r) => {
            const [oldF, newF] = getComparePair(project, r.device);
            const lines = getDriftLines(r.device);
            return (
              <div
                key={r.device}
                className="rounded-xl border border-slate-300 dark:border-[#1F2937] bg-white dark:bg-[#0F172A] p-4"
              >
                <div className="flex items-center justify-between gap-4">
                  <div className="text-sm">
                    <div className="font-semibold text-gray-800 dark:text-gray-100">Device: {safeDisplay(r.device)}</div>
                    <div className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                      Compare file: <span className="font-mono">{safeDisplay(oldF)}</span> <span className="opacity-70">→</span>{" "}
                      <span className="font-mono">{safeDisplay(newF)}</span>
                    </div>
                  </div>
                </div>

                <ul className="mt-3 space-y-1 text-sm leading-relaxed">
                  {lines.map((line, i) => {
                    const first = line.trim().charAt(0);
                    const color =
                      first === "+" ? "text-emerald-400" :
                        first === "−" ? "text-rose-400" :
                          first === "~" ? "text-amber-300" : "text-gray-300";
                    return (
                      <li key={i} className="font-mono">
                        <span className={`${color} font-semibold mr-2`}>{first}</span>
                        <span className="text-gray-200">{line.slice(1).trim()}</span>
                      </li>
                    );
                  })}
                </ul>
              </div>
            );
          })}
        </div>
      </Card>

      {/* Combined Logs and Upload History */}
      <Card
        title={
          <div className="flex items-center justify-between w-full">
            <span className="text-sm font-semibold text-gray-700 dark:text-gray-200">History</span>
            <div className="relative">
              <input
                type="text"
                placeholder="Search (filename, user, description...)"
                value={searchActivity}
                onChange={(e) => setSearchActivity(e.target.value)}
                className="w-64 pl-8 pr-3 py-1.5 text-xs rounded-lg bg-slate-800/80 border border-slate-600 text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-sky-500 focus:border-sky-500"
              />
              <svg className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
          </div>
        }
        className="overflow-hidden"
      >
        <div className="h-[50vh] overflow-hidden rounded-xl border border-slate-300 dark:border-slate-700">
          <Table
            showToolbar={false}
            columns={[
              { header: "Time", key: "time" },
              { header: "Name", key: "files" },
              { header: "Responsible User", key: "who" },
              { header: "Activity Type", key: "what" },
              { header: "Site", key: "where" },
              { header: "Operational Timing", key: "when" },
              { header: "Purpose", key: "why" },
              { header: "Description", key: "description" },
              {
                header: "Action",
                key: "act",
                filterable: false,
                sortable: false,
                cell: (r) => (
                  r.type === 'upload' && r.uploadRecord?.files?.[0] ? (
                    <div className="flex gap-2">
                      <Button
                        variant="secondary"
                        onClick={() => {
                          const file = r.uploadRecord.files[0];
                          if (!file) return;
                          const blob = new Blob(
                            [file.content || `# ${r.uploadRecord.type === 'config' ? 'Configuration' : 'Document'} Backup\n# File: ${file.name}\n# Uploaded: ${r.time}\n# User: ${r.who}\n\nContent not available. Download from Documents if needed.`],
                            { type: file.type || (r.uploadRecord.type === 'config' ? "text/plain;charset=utf-8" : "application/octet-stream") }
                          );
                          const url = URL.createObjectURL(blob);
                          const a = document.createElement("a");
                          a.href = url;
                          a.download = file.name || "file";
                          document.body.appendChild(a);
                          a.click();
                          a.remove();
                          URL.revokeObjectURL(url);
                        }}
                      >
                        ⬇ Download
                      </Button>
                    </div>
                  ) : "—"
                ),
              },
            ]}
            data={combinedHistory}
            empty="No recent activity"
          />
        </div>
      </Card>
    </div>
  );
};

/* ========= Topology helpers (role + links) ========= */

/* ========= Project Analysis Panel Component (tabbed) ========= */
const ProjectAnalysisPanel = ({ project, summaryRows, coreCount, distCount, accessCount, llmBusy, llmBusyMessage, requestRun, onComplete, setLlmNotification }) => {
  const [activeTab, setActiveTab] = React.useState("overview");
  const [overviewGenerating, setOverviewGenerating] = React.useState(false);
  const [recGenerating, setRecGenerating] = React.useState(false);
  const overviewGenerateRef = React.useRef(null);
  const recGenerateRef = React.useRef(null);
  const overviewGetActionRef = React.useRef(null);
  const recGetActionRef = React.useRef(null);

  const handleAiClick = () => {
    const getAction = activeTab === "overview" ? overviewGetActionRef.current : recGetActionRef.current;
    if (typeof getAction === "function") {
      const result = getAction();
      if (result?.action === "show" && result.data) {
        setLlmNotification(result.data);
        return;
      }
    }
    const fn = activeTab === "overview" ? overviewGenerateRef.current : recGenerateRef.current;
    if (typeof fn !== "function") return;
    requestRun(fn);
  };

  const tabGenerating = activeTab === "overview" ? overviewGenerating : recGenerating;
  const buttonDisabled = summaryRows.length === 0 || llmBusy || tabGenerating;
  const title = summaryRows.length === 0
    ? "Upload configs first"
    : llmBusy
      ? (llmBusyMessage || (tabGenerating ? "Analysis in progress. Please wait..." : "Another task is running. Please wait."))
      : "Generate with AI (for current tab)";

  return (
    <div className="lg:col-span-6 min-h-0 flex flex-col w-full rounded-xl border border-slate-300 dark:border-slate-800 bg-white dark:bg-slate-900/50 overflow-hidden shadow-sm dark:shadow-none">
      {/* Tabs + AI button on top */}
      <div className="flex flex-shrink-0 flex items-center justify-between border-b border-slate-300 dark:border-slate-700/80 bg-slate-50/95 dark:bg-slate-900/50 backdrop-blur-sm">
        <div className="flex min-w-0">
          <button
            type="button"
            onClick={() => setActiveTab("overview")}
            className={`px-3 py-2.5 text-xs sm:text-sm font-medium rounded-t-lg border transition-colors ${activeTab === "overview"
              ? "bg-white/85 dark:bg-white/10 border-slate-300/70 dark:border-slate-600/70 border-b-white dark:border-b-slate-900/50 text-slate-800 dark:text-slate-100 shadow-sm -mb-px"
              : "border-transparent text-slate-700 dark:text-slate-400 hover:bg-slate-100/80 dark:hover:bg-slate-800/40 hover:text-slate-900 dark:hover:text-slate-300"
              }`}
          >
            Network Overview
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("recommendations")}
            className={`px-3 py-2.5 text-xs sm:text-sm font-medium rounded-t-lg border transition-colors ${activeTab === "recommendations"
              ? "bg-white/85 dark:bg-white/10 border-slate-300/70 dark:border-slate-600/70 border-b-white dark:border-b-slate-900/50 text-slate-800 dark:text-slate-100 shadow-sm -mb-px"
              : "border-transparent text-slate-700 dark:text-slate-400 hover:bg-slate-100/80 dark:hover:bg-slate-800/40 hover:text-slate-900 dark:hover:text-slate-300"
              }`}
          >
            Recommendations
          </button>
        </div>
        <button
          type="button"
          onClick={handleAiClick}
          disabled={buttonDisabled}
          className="w-8 h-8 flex items-center justify-center rounded-xl bg-white/90 dark:bg-white/10 backdrop-blur-sm border border-slate-300/80 dark:border-slate-600/80 text-slate-700 dark:text-slate-200 shadow-sm hover:bg-white dark:hover:bg-white/15 transition-colors disabled:opacity-50 disabled:cursor-not-allowed mr-2 text-base flex-shrink-0"
          title={title}
          aria-label="AI Analysis"
        >
          {llmBusy ? "⏳" : "✨"}
        </button>
      </div>
      <div className="flex-1 min-h-0 flex flex-col overflow-hidden">
        {activeTab === "overview" && (
          <NetworkOverviewCard
            project={project}
            summaryRows={summaryRows}
            fullHeight
            onRegisterGenerate={(fn) => { overviewGenerateRef.current = fn; }}
            onRegisterGetAction={(getter) => { overviewGetActionRef.current = getter; }}
            onGeneratingChange={setOverviewGenerating}
            onComplete={onComplete}
            requestRun={requestRun}
            setLlmNotification={setLlmNotification}
          />
        )}
        {activeTab === "recommendations" && (
          <RecommendationsCard
            project={project}
            summaryRows={summaryRows}
            fullHeight
            onRegisterGenerate={(fn) => { recGenerateRef.current = fn; }}
            onRegisterGetAction={(getter) => { recGetActionRef.current = getter; }}
            onGeneratingChange={setRecGenerating}
            onComplete={onComplete}
            requestRun={requestRun}
            setLlmNotification={setLlmNotification}
          />
        )}
      </div>
    </div>
  );
};

/* ========= Network Overview Card Component ========= */
const NetworkOverviewCard = ({ project, summaryRows, fullHeight, onRegisterGenerate, onRegisterGetAction, onGeneratingChange, onComplete, requestRun, setLlmNotification }) => {
  const [overviewData, setOverviewData] = React.useState(null);
  const [overviewText, setOverviewText] = React.useState(null);
  const [llmMetrics, setLlmMetrics] = React.useState(null);
  const applyOverviewResult = (result) => {
    setOverviewData(result.overview && typeof result.overview === "object" ? result.overview : null);
    setOverviewText(result.overview_text || null);
  };
  const [generating, setGenerating] = React.useState(false);
  const [error, setError] = React.useState(null);
  const [loading, setLoading] = React.useState(true);
  const [showNotification, setShowNotification] = React.useState(false);
  const [notificationData, setNotificationData] = React.useState(null);

  const projectId = project?.project_id || project?.id;

  React.useEffect(() => {
    onGeneratingChange?.(generating);
  }, [generating, onGeneratingChange]);

  // Load generating state from localStorage on mount and start polling if needed
  React.useEffect(() => {
    if (!projectId) return;
    const storageKey = `llm_generating_overview_${projectId}`;
    const pollingKey = `overview_${projectId}`;
    const saved = localStorage.getItem(storageKey);
    if (saved === "true") {
      setGenerating(true);
      // If polling is not active but localStorage says generating, start polling immediately
      if (!globalPollingService.isPolling(pollingKey)) {
        // Start polling immediately (don't wait for generating state to trigger it)
        globalPollingService.startPolling(
          pollingKey,
          projectId,
          api.getProjectOverview,
          (result) => {
            notifyLLMResultReady("Network Overview", "LLM analysis completed. Open Summary to view.");
            applyOverviewResult(result);
            setLlmMetrics(result.metrics || null);
            setGenerating(false);
            localStorage.removeItem(storageKey);
            onComplete?.();
            setNotificationData({
              title: "Network Overview Generated",
              message: "LLM analysis completed successfully.",
              metrics: result.metrics,
              type: "success"
            });
            setShowNotification(true);
            setLlmNotification?.({ show: true, type: "success", title: "Network Overview Generated", message: "LLM analysis completed successfully.", metrics: result.metrics, onRegenerate: () => requestRun?.(doGenerate) });
          },
          (errorMsg) => {
            setGenerating(false);
            setError(errorMsg);
            localStorage.removeItem(storageKey);
            onComplete?.();
          }
        );
      } else {
        // Resume existing polling with new callbacks
        globalPollingService.resumePolling(
          pollingKey,
          (result) => {
            notifyLLMResultReady("Network Overview", "LLM analysis completed. Open Summary to view.");
            applyOverviewResult(result);
            setLlmMetrics(result.metrics || null);
            setGenerating(false);
            localStorage.removeItem(storageKey);
            onComplete?.();
            setNotificationData({
              title: "Network Overview Generated",
              message: "LLM analysis completed successfully.",
              metrics: result.metrics,
              type: "success"
            });
            setShowNotification(true);
            setLlmNotification?.({ show: true, type: "success", title: "Network Overview Generated", message: "LLM analysis completed successfully.", metrics: result.metrics, onRegenerate: () => requestRun?.(doGenerate) });
          },
          (errorMsg) => {
            setGenerating(false);
            setError(errorMsg);
            localStorage.removeItem(storageKey);
            onComplete?.();
          }
        );
      }
    }
  }, [projectId]);

  // Load saved full project analysis on mount (use network_overview from full analysis)
  // Timeout so we never block forever if API hangs
  React.useEffect(() => {
    if (!projectId) {
      setLoading(false);
      return;
    }

    let isMounted = true;
    const LOAD_TIMEOUT_MS = 12000;

    const loadSavedAnalysis = async () => {
      const timeoutPromise = new Promise((_, reject) => {
        setTimeout(() => reject(new Error("Load timeout")), LOAD_TIMEOUT_MS);
      });
      try {
        const fullResult = await Promise.race([
          api.getFullProjectAnalysis(projectId),
          timeoutPromise
        ]);
        if (isMounted) {
          setOverviewData(fullResult.overview && typeof fullResult.overview === "object" ? fullResult.overview : null);
          setOverviewText(fullResult.overview_text || (typeof fullResult.overview === "string" ? fullResult.overview : null));
          setLlmMetrics(fullResult.metrics || null);
          return;
        }
      } catch (err) {
        if (err?.message === "Load timeout") {
          if (isMounted) console.warn("Overview load timed out, showing empty state");
        } else {
          try {
            const result = await Promise.race([
              api.getProjectOverview(projectId),
              timeoutPromise
            ]);
            if (isMounted) {
              setOverviewData(result.overview && typeof result.overview === "object" ? result.overview : null);
              setOverviewText(result.overview_text || null);
              setLlmMetrics(result.metrics || null);
            }
          } catch (err2) {
            if (err2?.message !== "Load timeout" && err2?.message && !err2.message.includes("404")) {
              console.warn("Failed to load saved overview:", err2);
            }
          }
        }
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    loadSavedAnalysis();

    return () => {
      isMounted = false;
    };
  }, [projectId]);

  // Poll for updates when generating (works even when user navigates away)
  React.useEffect(() => {
    if (!projectId) return;

    const storageKey = `llm_generating_overview_${projectId}`;
    const pollingKey = `overview_${projectId}`;
    const isGenerating = generating || localStorage.getItem(storageKey) === "true";

    if (!isGenerating) {
      localStorage.removeItem(storageKey);
      globalPollingService.stopPolling(pollingKey);
      return;
    }

    // Use global polling service (works across page navigation)
    // Resume existing polling if it exists, otherwise start new one
    if (globalPollingService.isPolling(pollingKey)) {
      globalPollingService.resumePolling(
        pollingKey,
        (result) => {
          notifyLLMResultReady("Network Overview", "LLM analysis completed. Open Summary to view.");
          applyOverviewResult(result);
          setLlmMetrics(result.metrics || null);
          setGenerating(false);
          localStorage.removeItem(storageKey);
          onComplete?.();
          setNotificationData({
            title: "Network Overview Generated",
            message: "LLM analysis completed successfully.",
            metrics: result.metrics,
            type: "success"
          });
          setShowNotification(true);
          setLlmNotification?.({ show: true, type: "success", title: "Network Overview Generated", message: "LLM analysis completed successfully.", metrics: result.metrics, onRegenerate: () => requestRun?.(doGenerate) });
        },
        (errorMsg) => {
          setGenerating(false);
          setError(errorMsg);
          localStorage.removeItem(storageKey);
          onComplete?.();
        }
      );
    } else {
      globalPollingService.startPolling(
        pollingKey,
        projectId,
        api.getProjectOverview,
        (result) => {
          notifyLLMResultReady("Network Overview", "LLM analysis completed. Open Summary to view.");
          applyOverviewResult(result);
          setLlmMetrics(result.metrics || null);
          setGenerating(false);
          localStorage.removeItem(storageKey);
          onComplete?.();
          setNotificationData({
            title: "Network Overview Generated",
            message: "LLM analysis completed successfully.",
            metrics: result.metrics,
            type: "success"
          });
          setShowNotification(true);
          setLlmNotification?.({ show: true, type: "success", title: "Network Overview Generated", message: "LLM analysis completed successfully.", metrics: result.metrics, onRegenerate: () => requestRun?.(doGenerate) });
        },
        (errorMsg) => {
          setGenerating(false);
          setError(errorMsg);
          localStorage.removeItem(storageKey);
          onComplete?.();
        }
      );
    }

    return () => {
      // Don't stop polling on unmount - let it continue in background
      // Only stop if explicitly requested (when generating is false)
    };
  }, [projectId, generating]);

  const handleGenerate = async () => {
    if (!projectId || generating) return;
    await doGenerate();
  };

  const doGenerate = async () => {
    if (!projectId) return;
    const storageKeyOverview = `llm_generating_overview_${projectId}`;
    if (localStorage.getItem(storageKeyOverview) === "true") return;
    // Update UI immediately so "Analyzing with LLM..." shows on first click (and on regenerate)
    flushSync(() => {
      setShowNotification(false);
      setGenerating(true);
      setError(null);
    });
    localStorage.setItem(storageKeyOverview, "true");
    api.analyzeProjectOverview(projectId)
      .catch((err) => {
        console.error("Project overview analysis request failed:", err);
        // Don't set error here - might be slow, polling will catch it
        // Only set error if it's immediate failure (not timeout)
        if (err.message && !err.message.includes("timeout")) {
          setError(formatError(err) || "Failed to start analysis. Check backend/LLM server.");
          setGenerating(false);
          localStorage.removeItem(storageKeyOverview);
          onComplete?.();
        }
      });
    // Note: We don't set generating=false here - polling will handle it
  };

  const generateRef = React.useRef(doGenerate);
  generateRef.current = doGenerate;
  React.useEffect(() => {
    onRegisterGenerate?.(() => generateRef.current?.());
    return () => onRegisterGenerate?.(null);
  }, [onRegisterGenerate]);

  const hasOverview = overviewData != null || overviewText != null;
  React.useEffect(() => {
    onRegisterGetAction?.(() => (
      hasOverview
        ? { action: "show", data: { show: true, type: "success", title: "Network Overview Generated", message: "LLM analysis completed successfully.", metrics: llmMetrics, onRegenerate: () => requestRun?.(generateRef.current) } }
        : { action: "generate" }
    ));
    return () => onRegisterGetAction?.(null);
  }, [hasOverview, llmMetrics, onRegisterGetAction, requestRun]);

  return (
    <>
      <NotificationModal
        show={showNotification}
        onClose={() => setShowNotification(false)}
        title={notificationData?.title || "Analysis Complete"}
        message={notificationData?.message || "LLM analysis completed."}
        metrics={notificationData?.metrics}
        type={notificationData?.type || "success"}
        onRegenerate={() => {
          setShowNotification(false);
          if (typeof requestRun === "function") requestRun(doGenerate);
          else doGenerate();
        }}
      />

      <div className={`flex-1 min-h-0 flex flex-col rounded-b-xl border border-slate-300 dark:border-slate-800 border-t-0 bg-slate-50/95 dark:bg-slate-900/50 overflow-hidden w-full ${fullHeight ? "min-h-0" : ""}`}>
        <div
          className="flex-1 min-h-0 overflow-y-auto overflow-x-hidden p-4 text-slate-700 dark:text-slate-400"
          style={fullHeight ? {} : { maxHeight: "calc(50vh - 100px)" }}
        >
          <div className={fullHeight ? "text-base" : "text-sm"}>
            {loading && !generating ? (
              <div className="text-slate-600 dark:text-slate-400 italic">Loading...</div>
            ) : (
              <>
                {generating && (
                  <div className="p-2 rounded-lg bg-slate-200/90 dark:bg-slate-700/50 border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 text-sm mb-2">
                    Analyzing with LLM... This may take 1–2 minutes (depending on number of devices). You can switch to Documents or other tabs meanwhile.
                  </div>
                )}
                {error && (
                  <div className="p-2 rounded-lg bg-rose-50 dark:bg-rose-900/20 border border-rose-300 dark:border-rose-700 text-rose-700 dark:text-rose-400 text-sm mb-2 break-words">
                    Error: {safeDisplay(error)}
                  </div>
                )}
                {overviewData != null && (overviewData.sections != null || overviewData.topology != null || overviewData.key_insights != null) ? (
                  <StructuredNetworkOverview data={overviewData} className={fullHeight ? "text-base" : ""} />
                ) : overviewText != null ? (
                  <SummaryMarkdown text={overviewText} className={fullHeight ? "text-base" : ""} />
                ) : (
                  <div className="text-slate-600 dark:text-slate-400 italic">
                    Click the AI button above to generate network overview.
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </>
  );
};

/* Normalize recommendations-only API format to gap_analysis display format */
function recommendationsToGapAnalysis(recommendations) {
  if (!Array.isArray(recommendations)) return [];
  return recommendations.map((r) => {
    // Support both old "device" (string) and new "affected_devices" (array) format
    let affectedDevices = [];
    if (Array.isArray(r.affected_devices) && r.affected_devices.length > 0) {
      affectedDevices = r.affected_devices;
    } else if (r.device && r.device !== "all") {
      affectedDevices = [r.device];
    }
    return {
      severity: r.severity || "Medium",
      affectedDevices: affectedDevices,
      issue: r.issue ?? r.message ?? "",
      recommendation: r.recommendation ?? r.message ?? "",
    };
  });
}

/* ========= Recommendations Card Component ========= */
const RecommendationsCard = ({ project, summaryRows, fullHeight, onRegisterGenerate, onRegisterGetAction, onGeneratingChange, onComplete, requestRun, setLlmNotification }) => {
  const [gapAnalysis, setGapAnalysis] = React.useState([]);
  const [llmMetrics, setLlmMetrics] = React.useState(null);
  const [generatingRecOnly, setGeneratingRecOnly] = React.useState(false);
  const [error, setError] = React.useState(null);
  const [loading, setLoading] = React.useState(true);
  const [showNotification, setShowNotification] = React.useState(false);
  const [notificationData, setNotificationData] = React.useState(null);

  const projectId = project?.project_id || project?.id;

  React.useEffect(() => {
    onGeneratingChange?.(generatingRecOnly);
  }, [generatingRecOnly, onGeneratingChange]);

  // Load generating state from localStorage on mount and start polling if needed
  React.useEffect(() => {
    if (!projectId) return;
    const storageKeyRec = `llm_generating_rec_${projectId}`;
    const pollingKey = `recommendations_${projectId}`;
    const saved = localStorage.getItem(storageKeyRec);

    if (saved === "true") {
      // Set generating state first to show loading UI immediately
      setGeneratingRecOnly(true);

      // If polling is not active but localStorage says generating, start polling immediately
      if (!globalPollingService.isPolling(pollingKey)) {
        // Start polling immediately (don't wait for generatingRecOnly state to trigger it)
        globalPollingService.startPolling(
          pollingKey,
          projectId,
          api.getProjectRecommendations,
          (result) => {
            notifyLLMResultReady("Recommendations", "LLM analysis completed. Open Summary to view.");
            const recs = result.recommendations || [];
            setGapAnalysis(recommendationsToGapAnalysis(recs));
            setLlmMetrics(result.metrics || null);
            setGeneratingRecOnly(false);
            localStorage.removeItem(storageKeyRec);
            onComplete?.();
            setNotificationData({
              title: "Recommendations Generated",
              message: `LLM analysis completed. Found ${recs.length} recommendations.`,
              metrics: result.metrics,
              type: "success"
            });
            setShowNotification(true);
            setLlmNotification?.({ show: true, type: "success", title: "Recommendations Generated", message: `LLM analysis completed. Found ${recs.length} recommendations.`, metrics: result.metrics, onRegenerate: () => requestRun?.(doGenerateRecommendations) });
          },
          (errorMsg) => {
            setGeneratingRecOnly(false);
            setError(errorMsg);
            localStorage.removeItem(storageKeyRec);
            onComplete?.();
          }
        );
      } else {
        // Resume existing polling with new callbacks
        globalPollingService.resumePolling(
          pollingKey,
          (result) => {
            notifyLLMResultReady("Recommendations", "LLM analysis completed. Open Summary to view.");
            const recs = result.recommendations || [];
            setGapAnalysis(recommendationsToGapAnalysis(recs));
            setLlmMetrics(result.metrics || null);
            setGeneratingRecOnly(false);
            localStorage.removeItem(storageKeyRec);
            onComplete?.();
            setNotificationData({
              title: "Recommendations Generated",
              message: `LLM analysis completed. Found ${recs.length} recommendations.`,
              metrics: result.metrics,
              type: "success"
            });
            setShowNotification(true);
            setLlmNotification?.({ show: true, type: "success", title: "Recommendations Generated", message: `LLM analysis completed. Found ${recs.length} recommendations.`, metrics: result.metrics, onRegenerate: () => requestRun?.(doGenerateRecommendations) });
          },
          (errorMsg) => {
            setGeneratingRecOnly(false);
            setError(errorMsg);
            localStorage.removeItem(storageKeyRec);
            onComplete?.();
          }
        );
      }
    } else {
      // Clear generating state if localStorage says not generating
      setGeneratingRecOnly(false);
    }
  }, [projectId]);

  // Load saved analysis on mount: recommendations-only (timeout so we never block forever)
  React.useEffect(() => {
    if (!projectId) {
      setLoading(false);
      return;
    }

    let isMounted = true;
    const LOAD_TIMEOUT_MS = 12000;

    const loadSavedAnalysis = async () => {
      const timeoutPromise = new Promise((_, reject) => {
        setTimeout(() => reject(new Error("Load timeout")), LOAD_TIMEOUT_MS);
      });
      try {
        const recResult = await Promise.race([
          api.getProjectRecommendations(projectId),
          timeoutPromise
        ]);
        const recs = recResult?.recommendations || [];
        if (isMounted) {
          if (recs.length > 0) {
            setGapAnalysis(recommendationsToGapAnalysis(recs));
            setLlmMetrics(recResult.metrics || null);
          }
          if (recResult.generated_at) {
            const storageKeyRec = `llm_generating_rec_${projectId}`;
            const pollingKey = `recommendations_${projectId}`;
            localStorage.removeItem(storageKeyRec);
            setGeneratingRecOnly(false);
            globalPollingService.stopPolling(pollingKey);
          }
        }
      } catch (err) {
        if (err?.message === "Load timeout") {
          if (isMounted) console.warn("Recommendations load timed out, showing empty state");
        } else if (err?.message && !err.message.includes("404")) {
          console.warn("Failed to load saved recommendations:", err);
        }
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    loadSavedAnalysis();

    return () => {
      isMounted = false;
    };
  }, [projectId]);

  // Poll for updates when generating (works even when user navigates away)
  React.useEffect(() => {
    if (!projectId) return;

    const storageKeyRec = `llm_generating_rec_${projectId}`;
    const pollingKey = `recommendations_${projectId}`;
    const isGeneratingRec = generatingRecOnly || localStorage.getItem(storageKeyRec) === "true";

    if (!isGeneratingRec) {
      localStorage.removeItem(storageKeyRec);
      globalPollingService.stopPolling(pollingKey);
      return;
    }

    // Use global polling service (works across page navigation)
    // Resume existing polling if it exists, otherwise start new one
    if (globalPollingService.isPolling(pollingKey)) {
      globalPollingService.resumePolling(
        pollingKey,
        (result) => {
          notifyLLMResultReady("Recommendations", "LLM analysis completed. Open Summary to view.");
          const recs = result.recommendations || [];
          setGapAnalysis(recommendationsToGapAnalysis(recs));
          setLlmMetrics(result.metrics || null);
          setGeneratingRecOnly(false);
          localStorage.removeItem(storageKeyRec);
          onComplete?.();
          setNotificationData({
            title: "Recommendations Generated",
            message: `LLM analysis completed. Found ${recs.length} recommendations.`,
            metrics: result.metrics,
            type: "success"
          });
          setShowNotification(true);
          setLlmNotification?.({ show: true, type: "success", title: "Recommendations Generated", message: `LLM analysis completed. Found ${recs.length} recommendations.`, metrics: result.metrics, onRegenerate: () => requestRun?.(doGenerateRecommendations) });
        },
        (errorMsg) => {
          setGeneratingRecOnly(false);
          setError(errorMsg);
          localStorage.removeItem(storageKeyRec);
          onComplete?.();
        }
      );
    } else {
      globalPollingService.startPolling(
        pollingKey,
        projectId,
        api.getProjectRecommendations,
        (result) => {
          notifyLLMResultReady("Recommendations", "LLM analysis completed. Open Summary to view.");
          const recs = result.recommendations || [];
          setGapAnalysis(recommendationsToGapAnalysis(recs));
          setLlmMetrics(result.metrics || null);
          setGeneratingRecOnly(false);
          localStorage.removeItem(storageKeyRec);
          onComplete?.();
          setNotificationData({
            title: "Recommendations Generated",
            message: `LLM analysis completed. Found ${recs.length} recommendations.`,
            metrics: result.metrics,
            type: "success"
          });
          setShowNotification(true);
          setLlmNotification?.({ show: true, type: "success", title: "Recommendations Generated", message: `LLM analysis completed. Found ${recs.length} recommendations.`, metrics: result.metrics, onRegenerate: () => requestRun?.(doGenerateRecommendations) });
        },
        (errorMsg) => {
          setGeneratingRecOnly(false);
          setError(errorMsg);
          localStorage.removeItem(storageKeyRec);
          onComplete?.();
        }
      );
    }

    return () => {
      // Don't stop polling on unmount - let it continue in background
      // Only stop if explicitly requested (when generatingRecOnly is false)
    };
  }, [projectId, generatingRecOnly]);

  const handleGenerateRecommendationsOnly = async () => {
    if (!projectId) return;
    const storageKey = `llm_generating_rec_${projectId}`;
    const isAlreadyGenerating = generatingRecOnly || localStorage.getItem(storageKey) === "true";
    if (isAlreadyGenerating) {
      console.log("Recommendations analysis already in progress, skipping duplicate request");
      return;
    }
    await doGenerateRecommendations();
  };

  const doGenerateRecommendations = async () => {
    if (!projectId) return;
    const storageKeyRec = `llm_generating_rec_${projectId}`;
    if (localStorage.getItem(storageKeyRec) === "true") return;
    flushSync(() => {
      setShowNotification(false);
      setGeneratingRecOnly(true);
      setError(null);
    });
    localStorage.setItem(storageKeyRec, "true");
    api.analyzeProjectRecommendations(projectId)
      .then(() => {
        // Request sent successfully - polling will handle the result
        console.log("Recommendations analysis request sent successfully");
      })
      .catch((err) => {
        console.error("Recommendations analysis request failed:", err);
        // Only set error for immediate failures (not timeout - that's expected)
        if (err.message && !err.message.includes("timeout") && !err.message.includes("ECONNRESET")) {
          setError(formatError(err) || "Failed to start analysis. Check backend/LLM server.");
          setGeneratingRecOnly(false);
          localStorage.removeItem(storageKeyRec);
          onComplete?.();
        } else {
          // Timeout or connection reset is expected - polling will handle it
          console.log("Request timeout/reset (expected) - polling will continue");
        }
      });
    // Note: We don't set generatingRecOnly=false here - polling will handle it when result is ready
  };

  const generateRef = React.useRef(doGenerateRecommendations);
  generateRef.current = doGenerateRecommendations;
  React.useEffect(() => {
    onRegisterGenerate?.(() => generateRef.current?.());
    return () => onRegisterGenerate?.(null);
  }, [onRegisterGenerate]);

  React.useEffect(() => {
    const hasResult = Array.isArray(gapAnalysis) && gapAnalysis.length > 0;
    onRegisterGetAction?.(() => (
      hasResult
        ? { action: "show", data: { show: true, type: "success", title: "Recommendations Generated", message: `LLM analysis completed. Found ${gapAnalysis.length} recommendations.`, metrics: llmMetrics, onRegenerate: () => requestRun?.(generateRef.current) } }
        : { action: "generate" }
    ));
    return () => onRegisterGetAction?.(null);
  }, [gapAnalysis, llmMetrics, onRegisterGetAction, requestRun]);

  return (
    <>
      <NotificationModal
        show={showNotification}
        onClose={() => setShowNotification(false)}
        title={notificationData?.title || "Analysis Complete"}
        message={notificationData?.message || "LLM analysis completed."}
        metrics={notificationData?.metrics}
        type={notificationData?.type || "success"}
        onRegenerate={() => {
          setShowNotification(false);
          if (typeof requestRun === "function") requestRun(doGenerateRecommendations);
          else doGenerateRecommendations();
        }}
      />

      <div className={`flex-1 min-h-0 flex flex-col rounded-b-xl border border-slate-300 dark:border-slate-800 border-t-0 bg-slate-50/95 dark:bg-slate-900/50 overflow-hidden w-full ${fullHeight ? "min-h-0" : ""}`}>
        <div
          className="flex-1 min-h-0 overflow-y-auto overflow-x-hidden p-4 text-slate-700 dark:text-slate-400"
          style={fullHeight ? {} : { maxHeight: "calc(50vh - 100px)" }}
        >
          {(() => {
            const storageKeyRec = `llm_generating_rec_${projectId}`;
            const isGeneratingFromStorage = localStorage.getItem(storageKeyRec) === "true";
            const isActuallyGenerating = generatingRecOnly || isGeneratingFromStorage;
            const textSize = fullHeight ? "text-base" : "text-sm";
            if (loading && !isActuallyGenerating) {
              return <div className={`text-slate-600 dark:text-slate-400 italic ${textSize}`}>Loading...</div>;
            }
            return (
              <div className={textSize}>
                {isActuallyGenerating && (
                  <div className="p-2 rounded-lg bg-slate-200/90 dark:bg-slate-700/50 border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 text-sm mb-2">
                    ⏳ Analyzing with LLM... This may take 1–2 minutes. You can switch to Documents or other tabs meanwhile.
                  </div>
                )}
                {error && (
                  <div className="p-2 rounded-lg bg-rose-50 dark:bg-rose-900/20 border border-rose-300 dark:border-rose-700 text-rose-700 dark:text-rose-400 text-sm mb-2 break-words">
                    Error: {safeDisplay(error)}
                  </div>
                )}
                {gapAnalysis.length > 0 ? (
                  <div className="space-y-3">
                    {gapAnalysis.map((item, idx) => {
                      const sev = (item.severity || "medium").toLowerCase();
                      const devices = item.affectedDevices || [];
                      const hasDevices = devices.length > 0 && !(devices.length === 1 && devices[0] === "all");
                      return (
                        <div key={idx} className="p-3 rounded-lg border break-words" style={{
                          borderColor: sev === "high" ? "#ef4444" : sev === "medium" ? "#eab308" : "#22c55e",
                          backgroundColor: sev === "high" ? "rgba(239, 68, 68, 0.08)" : sev === "medium" ? "rgba(234, 179, 8, 0.1)" : "rgba(34, 197, 94, 0.08)"
                        }}>
                          <div className="flex items-start gap-2 mb-1.5">
                            <span className={`text-sm font-semibold px-2 py-0.5 rounded ${sev === "high" ? "bg-rose-500 text-white" :
                              sev === "medium" ? "bg-yellow-500 text-white" :
                                "bg-green-500 text-white"
                              }`}>
                              {sev.toUpperCase()}
                            </span>
                          </div>
                          {item.issue != null && (
                            <div className="text-slate-700 dark:text-slate-300 mb-1.5">
                              <span className="font-semibold">Issue:</span> {safeDisplay(item.issue)}
                            </div>
                          )}
                          {item.recommendation != null && (
                            <div className="text-slate-700 dark:text-slate-200 mb-1.5">
                              <span className="font-semibold">Recommendation:</span> {safeDisplay(item.recommendation)}
                            </div>
                          )}
                          {hasDevices && (
                            <div className="flex items-center gap-2 mt-2 pt-2 border-t border-slate-200/50 dark:border-slate-700/50">
                              <span className="text-xs font-semibold text-slate-500 dark:text-slate-400">Affected Devices:</span>
                              <div className="flex flex-wrap gap-1">
                                {devices.map((d, i) => (
                                  <span key={i} className="inline-flex items-center px-2 py-0.5 text-xs font-medium rounded-full bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300">
                                    {d}
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}
                          {!hasDevices && (
                            <div className="flex items-center gap-2 mt-2 pt-2 border-t border-slate-200/50 dark:border-slate-700/50">
                              <span className="text-xs font-semibold text-slate-500 dark:text-slate-400">Affected Devices:</span>
                              <span className="text-xs text-slate-500 dark:text-slate-400 italic">All devices in network</span>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                ) : !isActuallyGenerating ? (
                  <div className="text-slate-500 dark:text-slate-400 italic">
                    Click the AI button above to generate recommendations.
                  </div>
                ) : null}
              </div>
            );
          })()}
        </div>
      </div>
    </>
  );
};

/* ========= Compare Config Modal (side-by-side diff, device → Left/Right config versions) ========= */
const ReactDiffViewer = React.lazy(() => import("react-diff-viewer-continued").then((m) => ({ default: m.default })));

const CompareConfigModal = ({ project, deviceList = [], onClose }) => {
  const projectId = project?.project_id || project?.id;
  const devices = Array.isArray(deviceList) ? deviceList.filter(Boolean) : [];
  const defaultDevice = devices[0] || "";
  const [sourceDevice, setSourceDevice] = useState(defaultDevice);
  const [targetDevice, setTargetDevice] = useState(defaultDevice);
  const [leftConfigs, setLeftConfigs] = useState([]);
  const [rightConfigs, setRightConfigs] = useState([]);
  const [loadingLeftConfigs, setLoadingLeftConfigs] = useState(false);
  const [loadingRightConfigs, setLoadingRightConfigs] = useState(false);
  const [leftConfigId, setLeftConfigId] = useState("");
  const [rightConfigId, setRightConfigId] = useState("");
  const [leftContent, setLeftContent] = useState(null);
  const [rightContent, setRightContent] = useState(null);
  const [loadingDiff, setLoadingDiff] = useState(false);
  const [error, setError] = useState(null);

  // When source device changes, default target to same device
  useEffect(() => {
    setTargetDevice(sourceDevice);
  }, [sourceDevice]);

  useEffect(() => {
    if (!projectId || !sourceDevice) {
      setLeftConfigs([]);
      setLeftConfigId("");
      setLeftContent(null);
      return;
    }
    setLoadingLeftConfigs(true);
    setError(null);
    api.getDeviceConfigs(projectId, sourceDevice)
      .then((list) => {
        setLeftConfigs(list);
        if (list.length) setLeftConfigId(list[0].id);
      })
      .catch((err) => setError(formatError(err) || "Failed to load config list"))
      .finally(() => setLoadingLeftConfigs(false));
  }, [projectId, sourceDevice]);

  useEffect(() => {
    if (!projectId || !targetDevice) {
      setRightConfigs([]);
      setRightConfigId("");
      setRightContent(null);
      return;
    }
    setLoadingRightConfigs(true);
    setError(null);
    api.getDeviceConfigs(projectId, targetDevice)
      .then((list) => {
        setRightConfigs(list);
        if (list.length) setRightConfigId(list[0].id);
      })
      .catch((err) => setError(formatError(err) || "Failed to load config list"))
      .finally(() => setLoadingRightConfigs(false));
  }, [projectId, targetDevice]);

  const parseConfigId = (id) => {
    if (!id || typeof id !== "string") return { document_id: null, version: null };
    const last = id.lastIndexOf("_v");
    if (last === -1) return { document_id: id, version: null };
    const ver = id.slice(last + 2);
    const num = parseInt(ver, 10);
    if (String(num) !== ver) return { document_id: id, version: null };
    return { document_id: id.slice(0, last), version: num };
  };

  useEffect(() => {
    if (!projectId || !leftConfigId || !rightConfigId || leftConfigId === rightConfigId) {
      setLeftContent(null);
      setRightContent(null);
      return;
    }
    setLoadingDiff(true);
    setError(null);
    const left = parseConfigId(leftConfigId);
    const right = parseConfigId(rightConfigId);
    Promise.all([
      api.getDocumentContentText(projectId, left.document_id, left.version, { extractConfig: true }),
      api.getDocumentContentText(projectId, right.document_id, right.version, { extractConfig: true }),
    ])
      .then(([textLeft, textRight]) => {
        setLeftContent(textLeft ?? "");
        setRightContent(textRight ?? "");
      })
      .catch((err) => {
        setError(formatError(err) || "Failed to load config content");
        setLeftContent(null);
        setRightContent(null);
      })
      .finally(() => setLoadingDiff(false));
  }, [projectId, leftConfigId, rightConfigId]);

  const leftConfig = leftConfigs.find((c) => c.id === leftConfigId);
  const rightConfig = rightConfigs.find((c) => c.id === rightConfigId);
  const leftLabel = leftConfig ? leftConfig.filename : "—";
  const rightLabel = rightConfig ? rightConfig.filename : "—";
  const loadingConfigs = loadingLeftConfigs || loadingRightConfigs;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-xl border border-slate-300 dark:border-slate-700 w-[90%] max-w-6xl max-h-[90vh] flex flex-col" onClick={(e) => e.stopPropagation()}>
        <div className="flex-shrink-0 flex items-center justify-between p-4 border-b border-slate-300 dark:border-slate-700">
          <h3 className="text-lg font-semibold text-slate-800 dark:text-slate-100">Compare Configurations</h3>
          <button type="button" className="p-2 rounded-lg text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-slate-700 dark:hover:text-slate-200 transition-colors" onClick={onClose} aria-label="Close">✕</button>
        </div>
        <div className="flex-shrink-0 p-4 space-y-3 border-b border-slate-300 dark:border-slate-700">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div>
              <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Source Device</label>
              <Select
                options={devices.map((d) => ({ value: d, label: d }))}
                value={sourceDevice}
                onChange={setSourceDevice}
                className="w-full"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Target Device</label>
              <Select
                options={devices.map((d) => ({ value: d, label: d }))}
                value={targetDevice}
                onChange={setTargetDevice}
                className="w-full"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Left Config (Source)</label>
              <Select
                options={leftConfigs.map((c) => ({
                  value: c.id,
                  label: `${c.filename}${c.created_at ? ` — ${formatDateTime(c.created_at)}` : ""}`.trim(),
                }))}
                value={leftConfigId}
                onChange={setLeftConfigId}
                className="w-full"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Right Config (Target)</label>
              <Select
                options={rightConfigs.map((c) => ({
                  value: c.id,
                  label: `${c.filename}${c.created_at ? ` — ${formatDateTime(c.created_at)}` : ""}`.trim(),
                }))}
                value={rightConfigId}
                onChange={setRightConfigId}
                className="w-full"
              />
            </div>
          </div>
          {error && !leftContent && (
            <div className="text-sm text-rose-600 dark:text-rose-400">{safeDisplay(error)}</div>
          )}
          {loadingConfigs && <div className="text-sm text-slate-500 dark:text-slate-400">Loading config list…</div>}
          {!loadingConfigs && (
            <>
              {sourceDevice && leftConfigs.length === 0 && (
                <div className="text-sm text-slate-500 dark:text-slate-400">No config versions for source device. Upload configs to the Config folder first.</div>
              )}
              {targetDevice && rightConfigs.length === 0 && (
                <div className="text-sm text-slate-500 dark:text-slate-400">No config versions for target device. Upload configs to the Config folder first.</div>
              )}
            </>
          )}
        </div>
        <div className="flex-1 min-h-0 flex flex-col p-4 overflow-hidden">
          {loadingDiff && (
            <div className="flex-1 flex items-center justify-center text-slate-500 dark:text-slate-400">
              <span className="animate-pulse">Loading…</span>
            </div>
          )}
          {!loadingDiff && leftContent != null && rightContent != null && (
            <>
              <div className="flex-shrink-0 flex gap-4 text-xs font-medium text-slate-600 dark:text-slate-400 mb-2">
                <span className="truncate" title={leftLabel}>Left: {leftLabel}</span>
                <span className="truncate" title={rightLabel}>Right: {rightLabel}</span>
              </div>
              {!leftContent && !rightContent ? (
                <div className="flex-1 flex items-center justify-center text-slate-500 dark:text-slate-400 text-sm">
                  No content to compare (files may be empty).
                </div>
              ) : (
                <div className="flex-1 min-h-0 overflow-auto rounded-xl border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50 [&_.diff]:!font-mono [&_.diff]:!text-xs">
                  <React.Suspense fallback={<div className="p-4 text-slate-500">Loading diff viewer…</div>}>
                    <ReactDiffViewer
                      oldValue={leftContent || " "}
                      newValue={rightContent || " "}
                      splitView={true}
                      showDiffOnly={false}
                    />
                  </React.Suspense>
                </div>
              )}
            </>
          )}
        </div>
        <div className="flex-shrink-0 flex justify-end p-4 border-t border-slate-300 dark:border-slate-700">
          <Button variant="secondary" onClick={onClose}>Close</Button>
        </div>
      </div>
    </div>
  );
};

/* ========= SUMMARY (network-focused) + CSV ========= */
const SummaryPage = ({ project, projectId: projectIdProp, routeToHash, handleNavClick, can, authedUser, setProjects, openDevice, llmBusy, llmBusyMessage, requestRun, onComplete, setLlmNotification, showConfirmModal }) => {
  const projectId = projectIdProp || project?.project_id || project?.id;
  const deviceDetailHref = (deviceId) => routeToHash ? routeToHash({ name: "device", projectId, device: deviceId }) : "#/";
  // LLM metrics state for topology generation (shared with TopologyGraph)
  const [topologyLLMMetrics, setTopologyLLMMetrics] = React.useState(null);
  const [q, setQ] = useState("");
  const [showUploadConfig, setShowUploadConfig] = useState(false);
  const [showCompareConfig, setShowCompareConfig] = useState(false);
  // Use cached project.summaryRows when returning to page so we never show "no data" while refetching
  const [summaryRows, setSummaryRows] = useState(() => project?.summaryRows ?? []);
  const [dashboardMetrics, setDashboardMetrics] = useState(null);
  const [loading, setLoading] = useState(() => !(project?.summaryRows?.length));
  const [error, setError] = useState(null);
  const [folderStructure, setFolderStructure] = useState(null);
  // Removed: searchConfig, filterConfigWho, filterConfigWhat, configUploadHistory (History table removed)

  // Sync from project when project reference changes (e.g. after navigation)
  useEffect(() => {
    if (project?.summaryRows?.length && summaryRows.length === 0) {
      setSummaryRows(project.summaryRows);
      setLoading(false);
    }
  }, [project?.summaryRows, project?.project_id]);

  // Load summary + dashboard metrics from API (NOC backend)
  useEffect(() => {
    let cancelled = false;
    const loadSummary = async () => {
      const projectId = project?.project_id || project?.id;
      if (!projectId) {
        if (!cancelled) setLoading(false);
        return;
      }
      if (!cancelled) setLoading(true);
      if (!cancelled) setError(null);
      try {
        const [summary, metrics] = await Promise.all([
          api.getConfigSummary(projectId),
          api.getSummaryMetrics(projectId).catch(() => null),
        ]);
        if (cancelled) return;
        setSummaryRows(summary.summaryRows || []);
        setDashboardMetrics(metrics || null);

        setProjects(prev => {
          const updated = prev.map(p => {
            const pId = p.project_id || p.id;
            if (pId === projectId) {
              const currentRows = p.summaryRows || [];
              const newRows = summary.summaryRows || [];
              if (JSON.stringify(currentRows) !== JSON.stringify(newRows)) {
                return { ...p, summaryRows: newRows };
              }
            }
            return p;
          });
          return updated;
        });
      } catch (err) {
        if (cancelled) return;
        console.error('Failed to load config summary:', err);
        setError(formatError(err) || 'Failed to load summary data');
        setSummaryRows(prev => prev.length ? prev : []);
        setDashboardMetrics(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    loadSummary();
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [project?.project_id || project?.id]);

  // Load folder structure for upload form
  useEffect(() => {
    const loadFolderStructure = async () => {
      if (!project?.project_id && !project?.id) return;
      try {
        const projectId = project.project_id || project.id;
        const docs = await api.getDocuments(projectId);
        // Build simple folder structure for upload form
        const structure = {
          id: "root",
          name: "/",
          folders: [
            { id: "Config", name: "Config", folders: [], files: [] }
          ],
          files: []
        };
        setFolderStructure(structure);
      } catch (error) {
        console.error('Failed to load folder structure:', error);
      }
    };
    loadFolderStructure();
  }, [project]);

  // Load config upload history from documents
  // Config upload history removed - no longer displayed on Summary page

  const handleUpload = async (uploadRecord, folderId) => {
    console.log('Upload completed:', uploadRecord);
    setShowUploadConfig(false);
    // Reload summary + metrics after upload (wait a bit for backend to parse)
    const projectId = project?.project_id || project?.id;
    if (!projectId) return;

    setLoading(true);
    setTimeout(async () => {
      try {
        const [summary, metrics] = await Promise.all([
          api.getConfigSummary(projectId),
          api.getSummaryMetrics(projectId).catch(() => null),
        ]);
        setSummaryRows(summary.summaryRows || []);
        setDashboardMetrics(metrics || null);
        setProjects(prev => {
          const updated = prev.map(p => {
            const pId = p.project_id || p.id;
            if (pId === projectId) {
              return { ...p, summaryRows: summary.summaryRows || [] };
            }
            return p;
          });
          return updated;
        });
      } catch (error) {
        console.error('Failed to reload summary:', error);
      } finally {
        setLoading(false);
      }
    }, 2000); // Wait 2 seconds for parsing to complete
  };

  const handleDeviceClick = (deviceName) => {
    if (!deviceName) {
      console.error('Device name is missing');
      return;
    }
    if (openDevice) {
      openDevice(deviceName);
    } else {
      console.error('openDevice prop not provided, cannot navigate to device details');
    }
  };

  const filtered = useMemo(() => {
    if (!q.trim()) return summaryRows;
    return summaryRows.filter((r) =>
      [r.device, r.model, r.mgmt_ip, r.serial].some((v) =>
        (v || "").toLowerCase().includes(q.toLowerCase())
      )
    );
  }, [summaryRows, q]);

  const columns = [
    { header: "DEVICE", key: "device", width: "80px" },
    { header: "MODEL", key: "model", width: "100px" },
    { header: "SERIAL", key: "serial", width: "100px" },
    { header: "OS/VER", key: "os_ver", width: "90px" },
    { header: "MGMT IP", key: "mgmt_ip", width: "90px" },
    { header: "IFACES (T/U/D/A)", key: "ifaces", width: "110px" },
    { header: "ACCESS", key: "access", width: "60px" },
    { header: "TRUNK", key: "trunk", width: "60px" },
    { header: "UNUSED", key: "unused", width: "70px" },
    { header: "VLANS", key: "vlans", width: "60px" },
    { header: "NATIVE VLAN", key: "native_vlan", width: "90px" },
    { header: "TRUNK ALLOWED", key: "trunk_allowed", width: "100px", cell: (r) => r.trunk_allowed || "—" },
    { header: "STP", key: "stp", width: "70px" },
    { header: "STP ROLE", key: "stp_role", width: "80px" },
    { header: "OSPF NEIGH", key: "ospf_neigh", width: "90px" },
    { header: "BGP ASN/NEIGH", key: "bgp_asn_neigh", width: "110px" },
    { header: "RT-PROTO", key: "rt_proto", width: "80px", cell: (r) => r.rt_proto || "—" },
    { header: "CPU%", key: "cpu", width: "60px" },
    { header: "MEM%", key: "mem", width: "60px" },
    {
      header: "STATUS", key: "status", cell: (r) => {
        const raw = r.status;
        const status = (raw != null && typeof raw === "object") ? JSON.stringify(raw) : (raw || "OK");
        if (status === "OK") {
          return <span className="text-emerald-400">✅ OK</span>;
        } else if (status === "Drift") {
          return <span className="text-amber-400">⚠ Drift</span>;
        } else {
          return <span className="text-red-400">⚠ {String(status)}</span>;
        }
      }
    },
    {
      header: "MORE", key: "more", width: "40px", cell: (r) => (
        <a
          href={deviceDetailHref(r.device)}
          onClick={(e) => handleNavClick(e, () => handleDeviceClick(r.device))}
          className="w-6 h-6 flex items-center justify-center rounded-lg border border-slate-300 dark:border-slate-600 bg-slate-100/80 dark:bg-slate-800/50 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 text-[10px] transition-colors mx-auto"
          title="Open Details (Ctrl+click for new tab)"
        >
          →
        </a>
      )
    },
  ];

  const exportCSV = () => {
    // Filter out "MORE" column
    const exportColumns = columns.filter(c => c.key !== "more");
    const headers = exportColumns.map(c => c.header);
    const rows = (filtered || []).map(r =>
      exportColumns.map(c => {
        let value;

        // For columns with cell function (like STATUS), get the raw value from row data
        if (c.key === "status") {
          // STATUS column: use the actual status value, not the React element
          value = r.status || "OK";
        } else if (c.key === "ifaces") {
          // IFACES column: backend may send string "total/up/down/adminDown" or object
          if (typeof r.ifaces === "string") value = r.ifaces;
          else { const ifaces = r.ifaces || {}; value = `${ifaces.total || 0}/${ifaces.up || 0}/${ifaces.down || 0}/${ifaces.adminDown || 0}`; }
        } else {
          // For other columns, get the value directly
          value = r[c.key] ?? "";
        }

        // Handle different value types
        if (value === null || value === undefined) {
          value = "";
        } else if (typeof value === 'object' && !Array.isArray(value)) {
          // For other objects, convert to JSON string
          value = JSON.stringify(value);
        }

        return `"${String(value).replaceAll('"', '""')}"`;
      }).join(","));
    downloadCSV([headers.join(","), ...rows].join("\n"), `summary_${safeDisplay(project?.name)}.csv`);
  };

  /* Above-the-fold metrics: from backend dashboard API or fallback to summaryRows */
  const totalDevices = dashboardMetrics?.total_devices ?? summaryRows.length;
  const okCount = dashboardMetrics?.healthy ?? summaryRows.filter((r) => (r.status || "").toLowerCase() === "ok").length;
  const criticalCount = dashboardMetrics?.critical ?? summaryRows.filter((r) => (r.status || "").toLowerCase() !== "ok").length;
  const coreCount = dashboardMetrics?.core ?? summaryRows.filter((r) => /core/i.test(r.device || "")).length;
  const distCount = dashboardMetrics?.dist ?? summaryRows.filter((r) => /dist|distribution/i.test(r.device || "")).length;
  const accessCount = dashboardMetrics?.access ?? summaryRows.filter((r) => /access/i.test(r.device || "")).length;

  // ====== UI: Single-pane, responsive layout ======
  // No overlay when LLM is running - all controls (Search, CSV, Upload, tabs in header) stay usable
  return (
    <div className="h-full flex flex-col gap-0 overflow-hidden min-h-0" style={{ pointerEvents: 'auto' }}>
      {/* Top section: 55% — header + topology + network overview */}
      <div className="flex-[0_0_55%] min-h-0 flex flex-col overflow-hidden">
        <div className="flex-shrink-0 flex items-center justify-between gap-2 py-1 px-2">
          <h2 className="text-base font-bold text-slate-800 dark:text-slate-200 flex items-center gap-2">
            <span className="w-1 h-4 bg-slate-500 dark:bg-slate-400 rounded-full" />
            Summary Config
          </h2>
          <div className="flex gap-1.5 items-center">
            <div className="relative">
              <Input
                placeholder="Search..."
                value={q}
                onChange={(e) => setQ(e.target.value)}
                className="w-28 text-[9px] py-1 px-2.5 h-6 bg-slate-100 dark:bg-slate-900/80 border-slate-300 dark:border-slate-700 focus:border-slate-400 dark:focus:border-slate-500 focus:ring-1 focus:ring-slate-400/50 dark:focus:ring-slate-500/50 rounded-lg text-slate-800 dark:text-slate-200 placeholder:text-slate-600 dark:placeholder:text-slate-500"
              />
              <span className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[9px] text-slate-600 dark:text-slate-500 pointer-events-none">🔍</span>
            </div>
            <button
              className="px-2.5 py-0.5 h-6 flex items-center justify-center rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-100 dark:bg-slate-900/80 hover:bg-slate-200 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300 text-[9px] font-medium transition-colors whitespace-nowrap"
              onClick={exportCSV}
              title="Export CSV"
            >
              CSV
            </button>
            <button
              className="px-2.5 py-0.5 h-6 flex items-center justify-center rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-100 dark:bg-slate-900/80 hover:bg-slate-200 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300 text-[9px] font-medium transition-colors whitespace-nowrap"
              onClick={() => setShowCompareConfig(true)}
              title="Compare two config files line by line"
            >
              Compare Config
            </button>
            {can("upload-config", project) && (
              <button
                className="px-2.5 py-0.5 h-6 flex items-center justify-center rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-100 dark:bg-slate-900/80 hover:bg-slate-200 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300 text-[9px] font-medium transition-colors whitespace-nowrap"
                onClick={() => setShowUploadConfig(true)}
                title="Upload Config"
              >
                Upload
              </button>
            )}
          </div>
        </div>



        {llmBusy && (
          <div className="flex-shrink-0 px-2 py-0.5 text-[10px] text-slate-600 dark:text-slate-500 bg-slate-200 dark:bg-slate-800/30 rounded-lg" title={llmBusyMessage || undefined}>
            {llmBusyMessage ? `⏳ ${llmBusyMessage}` : "Waiting for LLM — You can click Summary / Documents / History tabs above to switch pages."}
          </div>
        )}
        <div className="flex-1 min-h-0 grid grid-cols-1 lg:grid-cols-12 gap-3 overflow-hidden">
          <div className="lg:col-span-6 min-h-0 overflow-hidden rounded-xl border border-slate-300 dark:border-slate-800 bg-white dark:bg-slate-900/50 shadow-sm dark:shadow-none">
            <TopologyGraph project={project} projectId={projectId} routeToHash={routeToHash} handleNavClick={handleNavClick} onOpenDevice={(id) => openDevice(id)} can={can} authedUser={authedUser} setProjects={setProjects} setTopologyLLMMetrics={setTopologyLLMMetrics} topologyLLMMetrics={topologyLLMMetrics} llmBusy={llmBusy} llmBusyMessage={llmBusyMessage} requestRun={requestRun} onComplete={onComplete} setLlmNotification={setLlmNotification} showConfirmModal={showConfirmModal} />
          </div>
          <ProjectAnalysisPanel
            project={project}
            summaryRows={summaryRows}
            coreCount={coreCount}
            distCount={distCount}
            accessCount={accessCount}
            llmBusy={llmBusy}
            llmBusyMessage={llmBusyMessage}
            requestRun={requestRun}
            onComplete={onComplete}
            setLlmNotification={setLlmNotification}
          />
        </div>
      </div>

      {/* Bottom section: 45% — device summary table */}
      {loading ? (
        <div className="flex-[0_0_45%] min-h-0 flex items-center justify-center rounded-xl border border-slate-300 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/50 my-3 overflow-hidden">
          <div className="text-sm text-slate-500 dark:text-slate-400">Loading summary data...</div>
        </div>
      ) : error ? (
        <div className="flex-[0_0_45%] min-h-0 flex flex-col items-center justify-center rounded-xl border border-slate-300 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/50 p-4 my-3 overflow-hidden">
          <div className="text-sm text-rose-600 dark:text-rose-400 font-semibold mb-2">Error loading summary</div>
          <div className="text-xs text-slate-500 dark:text-slate-400 mb-3">{safeDisplay(error)}</div>
          <Button variant="secondary" className="text-xs" onClick={() => {
            setError(null);
            const projectId = project?.project_id || project?.id;
            if (projectId) {
              setLoading(true);
              Promise.all([
                api.getConfigSummary(projectId),
                api.getSummaryMetrics(projectId).catch(() => null),
              ])
                .then(([summary, metrics]) => {
                  setSummaryRows(summary.summaryRows || []);
                  setDashboardMetrics(metrics || null);
                  setLoading(false);
                })
                .catch(err => { setError(formatError(err) || 'Failed to load summary data'); setLoading(false); });
            }
          }}>Retry</Button>
        </div>
      ) : (
        <div className="flex-[0_0_45%] min-h-0 flex flex-col rounded-xl border border-slate-300 dark:border-slate-800 bg-white dark:bg-slate-900/50 shadow-sm dark:shadow-none my-3 overflow-hidden">
          <div className="flex-1 min-h-0 overflow-auto p-1">
            <Table columns={columns} data={filtered} empty="No devices yet. Upload config files to see summary." minWidthClass="min-w-full" containerClassName="text-xs" />
          </div>
        </div>
      )}


      {/* Upload Config Modal */}
      {showUploadConfig && (
        <UploadConfigForm
          project={project}
          authedUser={authedUser}
          onClose={() => setShowUploadConfig(false)}
          onUpload={handleUpload}
        />
      )}
      {/* Compare Config Modal */}
      {showCompareConfig && (
        <CompareConfigModal
          project={project}
          deviceList={(summaryRows || []).map((r) => r.device).filter(Boolean)}
          onClose={() => setShowCompareConfig(false)}
        />
      )}
    </div>
  );
};


/* ========= DEVICE DETAILS PAGE (with header navigation) ========= */
const DeviceDetailsPage = ({ project, deviceId, goBack, goIndex, goBackHref, goIndexHref, can, loadProjects, uploadHistory, authedUser, setProjects, llmBusy, llmBusyMessage, requestRun, onComplete, showConfirmModal }) => {
  if (!project) {
    return <div className="text-sm text-rose-400">Project not found</div>;
  }

  return (
    <div className="h-full flex flex-col min-h-0 px-6 py-4">
      <DeviceDetailsView
        project={project}
        deviceId={deviceId}
        goBack={goBack}
        goBackHref={goBackHref}
        goIndex={goIndex}
        goIndexHref={goIndexHref}
        can={can}
        loadProjects={loadProjects}
        uploadHistory={uploadHistory}
        authedUser={authedUser}
        setProjects={setProjects}
        llmBusy={llmBusy}
        llmBusyMessage={llmBusyMessage}
        requestRun={requestRun}
        onComplete={onComplete}
        showConfirmModal={showConfirmModal}
      />
    </div>
  );
};

/* ========= DEVICE DETAILS (Overview / Interfaces / VLANs / Raw) ========= */
/* ========= DEVICE DETAILS (Overview / Interfaces / VLANs / Raw) ========= */
const DeviceDetailsView = ({ project, deviceId, goBack, goBackHref, goIndex, goIndexHref, can: canProp, loadProjects, uploadHistory, authedUser, setProjects, llmBusy: globalLlmBusy, llmBusyMessage, requestRun, onComplete, showConfirmModal }) => {
  console.log('[DeviceDetailsView] Rendering with props:', { project, deviceId, hasGoBack: !!goBack });
  const can = typeof canProp === "function" ? canProp : () => false;
  const canDeleteDevice = can("upload-config", project);
  const backLink = goBack && (goBackHref != null ? (
    <a href={goBackHref} onClick={(e) => handleNavClick(e, goBack)} className="inline-flex items-center justify-center rounded-lg px-3 py-1.5 text-xs font-medium shadow-sm transition focus:outline-none focus:ring-2 focus:ring-offset-2 bg-white text-gray-900 ring-1 ring-gray-300 hover:bg-gray-50 focus:ring-blue-500 dark:bg-gray-800 dark:text-gray-100 dark:ring-gray-600 dark:hover:bg-gray-700">← Back to Summary</a>
  ) : (
    <Button variant="secondary" onClick={goBack}>← Back to Summary</Button>
  ));

  // Early return if project or deviceId is missing
  if (!project) {
    console.error('[DeviceDetailsView] Project not found');
    return (
      <div className="grid gap-4">
        <div className="text-sm text-rose-400">Project not found</div>
        {goBack && backLink}
      </div>
    );
  }

  if (!deviceId) {
    console.error('[DeviceDetailsView] Device ID not provided');
    return (
      <div className="grid gap-4">
        <div className="text-sm text-rose-400">Device ID not provided</div>
        {goBack && backLink}
      </div>
    );
  }

  // State for API data
  const [deviceData, setDeviceData] = React.useState(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState(null);

  // Fetch device details from API
  React.useEffect(() => {
    const fetchDeviceDetails = async () => {
      if (!project?.project_id && !project?.id) return;
      if (!deviceId) return;

      setLoading(true);
      setError(null);
      try {
        const projectId = project.project_id || project.id;
        const details = await api.getDeviceDetails(projectId, deviceId);
        console.log('📥 Received device details from API:', {
          device_name: details?.device_name,
          neighbors_count: details?.neighbors?.length || 0,
          has_original_content: !!details?.original_content,
          neighbors_sample: details?.neighbors?.slice(0, 2),
          all_keys: Object.keys(details || {})
        });
        setDeviceData(details);
      } catch (err) {
        console.error('Failed to load device details:', err);
        setError(formatError(err) || 'Failed to load device details');
      } finally {
        setLoading(false);
      }
    };

    fetchDeviceDetails();
  }, [project?.project_id || project?.id, deviceId]);

  // Pick device row from summaryRows (real data from API)
  const row =
    project?.summaryRows?.find((r) => r.device === deviceId) ||
    project?.summaryRows?.[0] ||
    null;

  // State for device backups and config history from API
  const [deviceBackups, setDeviceBackups] = React.useState([]);
  const [deviceConfigHistory, setDeviceConfigHistory] = React.useState([]);
  const [loadingBackups, setLoadingBackups] = React.useState(true);
  // Version history for Config Drift: one document's versions (raw config files, 2 latest compared)
  const [deviceConfigVersions, setDeviceConfigVersions] = React.useState(null);
  const [loadingVersions, setLoadingVersions] = React.useState(false);

  // Fetch device config documents (Config folder, filename matches device)
  React.useEffect(() => {
    const fetchDeviceBackups = async () => {
      if (!project?.project_id && !project?.id) return;
      if (!deviceId) return;

      setLoadingBackups(true);
      setDeviceConfigVersions(null);
      try {
        const projectId = project.project_id || project.id;
        const docs = await api.getDocuments(projectId, { folder_id: "Config" });
        const devBase = deviceId.toLowerCase();
        const keyVariants = [
          devBase,
          devBase.replace(/-/g, "_"),
          devBase.replace(/_/g, "-"),
          devBase.replace(/[-_]/g, ""),
        ];
        const matchingDocs = docs.filter((doc) => {
          const name = (doc.filename || "").toLowerCase();
          return keyVariants.some((k) => name.includes(k));
        });
        const sorted = matchingDocs.sort((a, b) => {
          const dateA = new Date(a.created_at || 0);
          const dateB = new Date(b.created_at || 0);
          return dateB - dateA;
        });
        setDeviceBackups(sorted);
        const history = sorted.map(doc => ({
          timestamp: doc.created_at,
          files: [{ name: doc.filename, document_id: doc.document_id, version: doc.version }],
          user: doc.uploader || "Unknown",
          details: { who: doc.metadata?.who || doc.uploader || "Unknown", what: doc.metadata?.what || "—", where: doc.metadata?.where || "—", when: doc.metadata?.when || "—", why: doc.metadata?.why || "—", description: doc.metadata?.description || "—" },
          type: "config",
          project: projectId,
        }));
        setDeviceConfigHistory(history);
      } catch (err) {
        console.error('Failed to load device backups:', err);
        setDeviceBackups([]);
        setDeviceConfigHistory([]);
      } finally {
        setLoadingBackups(false);
      }
    };
    fetchDeviceBackups();
  }, [project?.project_id || project?.id, deviceId]);

  // Fetch version history for first device config document (for Config Drift — raw file versions)
  React.useEffect(() => {
    if (!project?.project_id && !project?.id) return;
    if (!deviceId || deviceBackups.length === 0) {
      setDeviceConfigVersions(null);
      return;
    }
    let cancelled = false;
    setLoadingVersions(true);
    const projectId = project.project_id || project.id;
    const doc = deviceBackups[0];
    api.getDocumentVersions(projectId, doc.document_id)
      .then((res) => {
        if (cancelled) return;
        const versions = (res.versions || []).sort((a, b) => (b.version - a.version));
        setDeviceConfigVersions({
          document_id: doc.document_id,
          filename: res.filename || doc.filename,
          versions,
        });
      })
      .catch(() => {
        if (!cancelled) setDeviceConfigVersions(null);
      })
      .finally(() => {
        if (!cancelled) setLoadingVersions(false);
      });
    return () => { cancelled = true; };
  }, [project?.project_id || project?.id, deviceId, deviceBackups]);

  // default: 2 most recent files
  const [compareOpen, setCompareOpen] = React.useState(false);
  const [leftFileName, setLeftFileName] = React.useState("");
  const [rightFileName, setRightFileName] = React.useState("");

  // Update default file names when deviceBackups change
  React.useEffect(() => {
    if (deviceBackups.length >= 2) {
      setLeftFileName(deviceBackups[1]?.filename || deviceBackups[0]?.filename || "");
      setRightFileName(deviceBackups[0]?.filename || deviceBackups[1]?.filename || "");
    } else if (deviceBackups.length === 1) {
      setLeftFileName(deviceBackups[0]?.filename || "");
      setRightFileName("");
    }
  }, [deviceBackups]);

  const leftFile = deviceBackups.find((f) => f.filename === leftFileName);
  const rightFile = deviceBackups.find((f) => f.filename === rightFileName);

  // simple line-by-line diff
  const simpleDiff = React.useCallback((aText = "", bText = "") => {
    const a = (aText || "").split(/\r?\n/);
    const b = (bText || "").split(/\r?\n/);
    const max = Math.max(a.length, b.length);
    const out = [];
    for (let i = 0; i < max; i++) {
      const L = a[i] ?? "";
      const R = b[i] ?? "";
      if (L === R) out.push({ t: "=", l: L });
      else {
        if (L) out.push({ t: "-", l: L });
        if (R) out.push({ t: "+", l: R });
      }
    }
    return out;
  }, []);


  // Extract facts from API data or fallback to row data
  const overview = deviceData?.device_overview || {};
  const interfaces = deviceData?.interfaces || [];
  const vlansData = deviceData?.vlans || {};
  const stpData = deviceData?.stp || {};
  const routingData = deviceData?.routing || {};
  const neighborsData = deviceData?.neighbors || [];
  const macArpData = deviceData?.mac_arp || {};
  const securityData = deviceData?.security || {};
  const haData = deviceData?.ha || {};

  // Calculate stats from real data
  const totalIfaces = interfaces.length;
  const upIfaces = interfaces.filter(i => i.oper_status === "up").length;
  const downIfaces = interfaces.filter(i => i.oper_status === "down").length;
  const adminDown = interfaces.filter(i => i.admin_status === "down").length;
  const accessPorts = interfaces.filter(i => i.port_mode === "access").length;
  const trunkPorts = interfaces.filter(i => i.port_mode === "trunk").length;
  const vlanList = vlansData.vlan_list || [];
  const vlanCount = vlanList.length;

  // facts - use API data ONLY (no fallback to row/mock data)
  // Note: All device info is now stored in device_overview, not top-level fields
  const facts = {
    device: deviceData?.device_name || deviceId,
    sourceFilename: deviceData?.source_filename || "—",
    model: overview.model || "—",
    osVersion: overview.os_version || "—",
    serial: overview.serial_number || "—",
    mgmtIp: overview.management_ip || overview.mgmt_ip || "—",
    role: overview.role || "—",
    vlanCount: vlanCount || 0,
    stpMode: stpData.mode || "—",
    stpRoot: stpData.root_bridge_id || "—",
    trunkCount: trunkPorts || 0,
    accessCount: accessPorts || 0,
    sviCount: interfaces.filter(i => i.type === "Vlan" || i.name?.startsWith("Vlan")).length || 0,
    hsrpGroups: (Array.isArray(haData.hsrp) ? haData.hsrp : (haData.hsrp?.groups || [])).length || 0,
    vrrpGroups: (Array.isArray(haData.vrrp) ? haData.vrrp : (haData.vrrp?.groups || [])).length || 0,
    routing: Object.keys(routingData).filter(k => routingData[k] && k !== "routes" && k !== "routing_table" && (Array.isArray(routingData[k]) ? routingData[k].length > 0 : typeof routingData[k] === "object" && Object.keys(routingData[k]).length > 0)).join(", ") || (routingData.routes?.length ? "Route table" : "—"),
    ospfNeighbors: routingData.ospf?.neighbors?.length || 0,
    bgpAsn: routingData.bgp?.as_number ?? routingData.bgp?.local_as ?? "—",
    bgpNeighbors: routingData.bgp?.peers?.length || 0,
    cdpNeighbors: neighborsData.filter(n => n.discovery_protocol === "CDP" || n.protocol === "CDP").length || 0,
    lldpNeighbors: neighborsData.filter(n => n.discovery_protocol === "LLDP" || n.protocol === "LLDP").length || 0,
    ntpStatus: securityData.ntp?.status || securityData.ntp?.synchronized ? "Synchronized" : "—",
    snmp: securityData.snmp?.enabled ? "Enabled" : "—",
    syslog: securityData.logging?.enabled || securityData.syslog?.enabled ? "Enabled" : "—",
    cpu: overview.cpu_utilization ?? overview.cpu_util ?? "—",
    mem: overview.memory_usage ?? overview.mem_util ?? "—",
    uptime: overview.uptime || "—",
    ifaces: {
      total: totalIfaces,
      up: upIfaces,
      down: downIfaces,
      adminDown: adminDown
    },
    allowedVlansShort: "—", // Not available from parsed data
  };

  // Device Facts per scope 2.3.2.1.1–2.3.2.1.9: 9 primary fields only, for Overview card
  const lastConfigUpload = deviceData?.upload_timestamp || (deviceBackups[0] && deviceBackups[0].created_at);
  const deviceFactsPrimary = React.useMemo(() => {
    const ov = deviceData?.device_overview || {};
    const hostname = ov.hostname || deviceData?.device_name || deviceId || "—";
    const role = ov.role || ov.device_status?.role || "—";
    const model = ov.model || "—";
    const osVersion = ov.os_version || "—";
    const serial = ov.serial_number || "—";
    const mgmtIp = ov.management_ip || ov.mgmt_ip || "—";
    const uptime = ov.uptime || "—";
    const cpuVal = ov.cpu_utilization ?? ov.cpu_util;
    const memVal = ov.memory_usage ?? ov.mem_util;
    const cpuMem = [cpuVal != null ? `${cpuVal}%` : "", memVal != null ? `${memVal}%` : ""].filter(Boolean).join(" / ") || "—";
    const lastUpload = lastConfigUpload ? formatDateTime(lastConfigUpload) : "—";
    return [
      { key: "hostname", label: "Hostname", value: hostname },
      { key: "role", label: "Device Type / Role", value: role },
      { key: "model", label: "Model / Platform", value: model },
      { key: "osVersion", label: "OS / Firmware Version", value: osVersion },
      { key: "serial", label: "Serial Number", value: serial },
      { key: "mgmtIp", label: "Management IP Address", value: mgmtIp },
      { key: "uptime", label: "Uptime", value: uptime },
      { key: "cpuMem", label: "CPU / Memory Utilization", value: cpuMem },
      { key: "lastUpload", label: "Last Configuration Upload", value: lastUpload },
    ];
  }, [deviceData, deviceId, deviceBackups, lastConfigUpload]);

  // Device narrative - use facts from API data only
  const deviceNarrative = React.useMemo(() => {
    if (!deviceData && loading) return "Device information is being loaded...";
    if (!deviceData) return "No device data available.";

    const parts = [];
    parts.push(`Device summary: ${facts.device}`);
    parts.push([
      `• Model/Platform: ${facts.model} • OS/Version: ${facts.osVersion}`,
      `• Serial: ${facts.serial} • Mgmt IP: ${facts.mgmtIp}`
    ].join("  |  "));

    if (facts.ifaces) {
      parts.push(`• Ports total ${facts.ifaces.total} (Up ${facts.ifaces.up}, Down ${facts.ifaces.down}, AdminDown ${facts.ifaces.adminDown})`);
      parts.push(`• Access ≈ ${facts.accessCount}  |  Trunk ≈ ${facts.trunkCount}`);
    }
    parts.push(`• VLANs: ${facts.vlanCount}  |  STP: ${facts.stpMode}${facts.stpRoot && facts.stpRoot !== "—" ? ` (Root: ${facts.stpRoot})` : ""}`);

    // L3
    const l3 = [];
    if (facts.routing && facts.routing !== "—") l3.push(facts.routing);
    if (facts.ospfNeighbors > 0) l3.push(`OSPF ${facts.ospfNeighbors} neigh`);
    if (facts.bgpAsn && facts.bgpAsn !== "—") l3.push(`BGP ${facts.bgpAsn}/${facts.bgpNeighbors}`);
    if (l3.length) parts.push(`• Routing: ${l3.join(" | ")}`);

    // Neighbors
    if (facts.cdpNeighbors > 0 || facts.lldpNeighbors > 0) {
      parts.push(`• Neighbors: CDP ${facts.cdpNeighbors} / LLDP ${facts.lldpNeighbors}`);
    }

    // Mgmt/Health
    parts.push(`• NTP: ${facts.ntpStatus}  |  SNMP: ${facts.snmp}  |  Syslog: ${facts.syslog}  |  CPU ${facts.cpu}% / MEM ${facts.mem}%`);

    // HA
    if (facts.hsrpGroups > 0 || facts.vrrpGroups > 0) {
      parts.push(`• HA: HSRP ${facts.hsrpGroups} groups / VRRP ${facts.vrrpGroups} groups`);
    }

    return parts.join("\n");
  }, [deviceData, facts, loading]);

  // Project-level gap analysis (fallback when per-device recs not generated)
  const [projectGapAnalysis, setProjectGapAnalysis] = React.useState([]);
  const [projectAnalysisLoading, setProjectAnalysisLoading] = React.useState(true);

  // ----- Per-device LLM (Device Summary / AI Recommendations / Config Drift) -----
  const projectId = project?.project_id || project?.id;
  const deviceStorageKey = projectId ? `llm_generating_device_${projectId}` : null;
  const [deviceOverviewData, setDeviceOverviewData] = React.useState(null);
  const [deviceOverviewText, setDeviceOverviewText] = React.useState(null);
  const [deviceOverviewLoading, setDeviceOverviewLoading] = React.useState(true);
  const [deviceOverviewGenerating, setDeviceOverviewGenerating] = React.useState(false);
  const [deviceOverviewError, setDeviceOverviewError] = React.useState(null);
  const applyDeviceOverviewResult = (r) => {
    setDeviceOverviewData(r.overview && typeof r.overview === "object" ? r.overview : null);
    setDeviceOverviewText(r.overview_text || null);
  };

  const [deviceRecsList, setDeviceRecsList] = React.useState([]);
  const [deviceRecsLoading, setDeviceRecsLoading] = React.useState(true);
  const [deviceRecsGenerating, setDeviceRecsGenerating] = React.useState(false);
  const [deviceRecsError, setDeviceRecsError] = React.useState(null);

  const [deviceDriftData, setDeviceDriftData] = React.useState(null);
  const [deviceDriftLoading, setDeviceDriftLoading] = React.useState(false);
  const [deviceDriftGenerating, setDeviceDriftGenerating] = React.useState(false);
  const [deviceDriftError, setDeviceDriftError] = React.useState(null);
  const [deviceLlmNotification, setDeviceLlmNotification] = React.useState(null);

  // Load device overview on mount
  React.useEffect(() => {
    if (!projectId || !deviceId) {
      setDeviceOverviewLoading(false);
      return;
    }
    let cancelled = false;
    api.getDeviceOverview(projectId, deviceId)
      .then((r) => { if (!cancelled) applyDeviceOverviewResult(r); })
      .catch(() => { if (!cancelled) { setDeviceOverviewData(null); setDeviceOverviewText(null); } })
      .finally(() => { if (!cancelled) setDeviceOverviewLoading(false); });
    return () => { cancelled = true; };
  }, [projectId, deviceId]);

  // Load device recommendations on mount
  React.useEffect(() => {
    if (!projectId || !deviceId) {
      setDeviceRecsLoading(false);
      return;
    }
    let cancelled = false;
    api.getDeviceRecommendations(projectId, deviceId)
      .then((r) => { if (!cancelled) setDeviceRecsList(r.recommendations || []); })
      .catch(() => { if (!cancelled) setDeviceRecsList([]); })
      .finally(() => { if (!cancelled) setDeviceRecsLoading(false); });
    return () => { cancelled = true; };
  }, [projectId, deviceId]);

  // Load saved config drift result when we have 2+ versions
  React.useEffect(() => {
    if (!projectId || !deviceId) {
      setDeviceDriftLoading(false);
      return;
    }
    setDeviceDriftLoading(true);
    let cancelled = false;
    api.getDeviceConfigDrift(projectId, deviceId)
      .then((r) => { if (!cancelled) setDeviceDriftData(r); })
      .catch(() => { if (!cancelled) setDeviceDriftData(null); })
      .finally(() => { if (!cancelled) setDeviceDriftLoading(false); });
    return () => { cancelled = true; };
  }, [projectId, deviceId]);

  // Polling for device overview when generating
  React.useEffect(() => {
    if (!projectId || !deviceId || !deviceOverviewGenerating) return;
    const key = `device_overview_${projectId}_${deviceId}`;
    const endpoint = (pid) => api.getDeviceOverview(pid, deviceId);
    const onUpdate = (result) => {
      applyDeviceOverviewResult(result);
      setDeviceOverviewGenerating(false);
      if (deviceStorageKey) localStorage.removeItem(deviceStorageKey);
      onComplete?.();
    };
    const onError = (msg) => {
      setDeviceOverviewError(msg);
      setDeviceOverviewGenerating(false);
      if (deviceStorageKey) localStorage.removeItem(deviceStorageKey);
      onComplete?.();
    };
    if (globalPollingService.isPolling(key)) {
      globalPollingService.resumePolling(key, onUpdate, onError);
    } else {
      globalPollingService.startPolling(key, projectId, endpoint, onUpdate, onError);
    }
    return () => {
      if (!deviceOverviewGenerating) globalPollingService.stopPolling(key);
    };
  }, [projectId, deviceId, deviceOverviewGenerating, deviceStorageKey, onComplete]);

  // Polling for device recommendations when generating
  React.useEffect(() => {
    if (!projectId || !deviceId || !deviceRecsGenerating) return;
    const key = `device_recs_${projectId}_${deviceId}`;
    const endpoint = (pid) => api.getDeviceRecommendations(pid, deviceId);
    const onUpdate = (result) => {
      setDeviceRecsList(result.recommendations || []);
      setDeviceRecsGenerating(false);
      if (deviceStorageKey) localStorage.removeItem(deviceStorageKey);
      onComplete?.();
    };
    const onError = (msg) => {
      setDeviceRecsError(msg);
      setDeviceRecsGenerating(false);
      if (deviceStorageKey) localStorage.removeItem(deviceStorageKey);
      onComplete?.();
    };
    if (globalPollingService.isPolling(key)) {
      globalPollingService.resumePolling(key, onUpdate, onError);
    } else {
      globalPollingService.startPolling(key, projectId, endpoint, onUpdate, onError);
    }
    return () => {
      if (!deviceRecsGenerating) globalPollingService.stopPolling(key);
    };
  }, [projectId, deviceId, deviceRecsGenerating, deviceStorageKey, onComplete]);

  // Local polling for config drift (result has "changes", not overview_text)
  const deviceDriftPollRef = React.useRef(null);
  React.useEffect(() => {
    if (!projectId || !deviceId || !deviceDriftGenerating) return;
    let cancelled = false;
    const poll = async () => {
      try {
        const r = await api.getDeviceConfigDrift(projectId, deviceId);
        if (!cancelled && r.changes && Array.isArray(r.changes)) {
          setDeviceDriftData(r);
          setDeviceDriftGenerating(false);
          if (deviceStorageKey) localStorage.removeItem(deviceStorageKey);
          onComplete?.();
          if (deviceDriftPollRef.current) {
            clearInterval(deviceDriftPollRef.current);
            deviceDriftPollRef.current = null;
          }
        }
      } catch (_) { }
    };
    poll();
    const id = setInterval(poll, 4000);
    deviceDriftPollRef.current = id;
    return () => {
      cancelled = true;
      if (deviceDriftPollRef.current) {
        clearInterval(deviceDriftPollRef.current);
        deviceDriftPollRef.current = null;
      }
    };
  }, [projectId, deviceId, deviceDriftGenerating, deviceStorageKey, onComplete]);

  const localLlmBusy = deviceOverviewGenerating || deviceRecsGenerating || deviceDriftGenerating;
  const llmBusy = (globalLlmBusy != null ? globalLlmBusy : false) || localLlmBusy;

  const clearDeviceLlmAndComplete = () => {
    if (deviceStorageKey) localStorage.removeItem(deviceStorageKey);
    onComplete?.();
  };

  // When data exists, AI button shows popup first (like Summary); Regenerate in popup runs LLM via queue
  const getDeviceLlmAction = () => {
    const closeAndRun = (fn) => {
      setDeviceLlmNotification((n) => (n ? { ...n, show: false } : null));
      if (typeof requestRun === "function") requestRun(fn);
      else fn();
    };
    if (llmPanelTab === "summary" && (deviceOverviewData != null || deviceOverviewText != null)) {
      return {
        action: "show",
        data: {
          show: true,
          type: "success",
          title: "Device Summary Generated",
          message: "LLM analysis completed successfully.",
          metrics: null,
          onRegenerate: () => closeAndRun(handleDeviceSummaryGenerate),
        },
      };
    }
    if (llmPanelTab === "recommendations" && deviceRecsList.length > 0) {
      return {
        action: "show",
        data: {
          show: true,
          type: "success",
          title: "AI Recommendations Generated",
          message: `LLM analysis completed. Found ${deviceRecsList.length} recommendation(s).`,
          metrics: null,
          onRegenerate: () => closeAndRun(handleDeviceRecsGenerate),
        },
      };
    }
    if (llmPanelTab === "drift" && deviceDriftData) {
      return {
        action: "show",
        data: {
          show: true,
          type: "success",
          title: "Config Drift Generated",
          message: "LLM analysis completed successfully.",
          metrics: deviceDriftData.metrics || null,
          onRegenerate: () => closeAndRun(handleDeviceDriftGenerate),
        },
      };
    }
    return null;
  };

  const handleDeviceAiClick = () => {
    const result = getDeviceLlmAction();
    if (result?.action === "show" && result.data) {
      setDeviceLlmNotification(result.data);
      return;
    }
    const run = () => {
      if (llmPanelTab === "summary") handleDeviceSummaryGenerate();
      else if (llmPanelTab === "recommendations") handleDeviceRecsGenerate();
      else if (llmPanelTab === "drift") handleDeviceDriftGenerate();
    };
    if (typeof requestRun === "function") requestRun(run);
    else run();
  };

  const handleDeviceSummaryGenerate = async () => {
    if (!projectId || !deviceId || deviceOverviewGenerating) return;
    if (deviceStorageKey) localStorage.setItem(deviceStorageKey, "true");
    setDeviceOverviewError(null);
    setDeviceOverviewGenerating(true);
    api.analyzeDeviceOverview(projectId, deviceId).catch((err) => {
      if (err.message && (err.message.includes("timeout") || err.message.includes("abort"))) return;
      setDeviceOverviewError(formatError(err) || "Failed to start analysis.");
      setDeviceOverviewGenerating(false);
      clearDeviceLlmAndComplete();
    });
  };

  const handleDeviceRecsGenerate = async () => {
    if (!projectId || !deviceId || deviceRecsGenerating) return;
    if (deviceStorageKey) localStorage.setItem(deviceStorageKey, "true");
    setDeviceRecsError(null);
    setDeviceRecsGenerating(true);
    api.analyzeDeviceRecommendations(projectId, deviceId).catch((err) => {
      if (err.message && (err.message.includes("timeout") || err.message.includes("abort"))) return;
      setDeviceRecsError(formatError(err) || "Failed to start analysis.");
      setDeviceRecsGenerating(false);
      clearDeviceLlmAndComplete();
    });
  };

  const handleDeviceDriftGenerate = async () => {
    if (!projectId || !deviceId || !hasEnoughVersionsForDrift || deviceDriftGenerating) return;
    const v = deviceConfigVersions?.versions;
    if (!v || v.length < 2) return;
    const older = v[1];
    const newer = v[0];
    if (deviceStorageKey) localStorage.setItem(deviceStorageKey, "true");
    setDeviceDriftError(null);
    setDeviceDriftGenerating(true);
    api.analyzeDeviceConfigDrift(projectId, deviceId, {
      documentId: deviceConfigVersions.document_id,
      fromVersion: older.version,
      toVersion: newer.version,
    }).catch((err) => {
      if (err.message && (err.message.includes("timeout") || err.message.includes("abort"))) return;
      setDeviceDriftError(formatError(err) || "Failed to start analysis.");
      setDeviceDriftGenerating(false);
      clearDeviceLlmAndComplete();
    });
  };

  React.useEffect(() => {
    const projectId = project?.project_id || project?.id;
    if (!projectId) {
      setProjectAnalysisLoading(false);
      return;
    }
    const loadProjectAnalysis = async () => {
      try {
        const result = await api.getFullProjectAnalysis(projectId);
        const deviceGaps = (result.gap_analysis || []).filter(
          item => item.device === facts.device || item.device === "all"
        );
        setProjectGapAnalysis(deviceGaps);
      } catch (err) {
        if (err.message && !err.message.includes("404")) {
          console.warn("Failed to load project gap analysis:", err);
        }
      } finally {
        setProjectAnalysisLoading(false);
      }
    };
    loadProjectAnalysis();
  }, [project, facts.device]);

  // Legacy: use for display only when per-device recs not used
  const deviceRecs = projectGapAnalysis.map(item => {
    const parts = [];
    if (item.issue) parts.push(`Issue: ${item.issue}`);
    if (item.recommendation) parts.push(`Fix: ${item.recommendation}`);
    return parts.length > 0 ? parts.join(" | ") : item.recommendation || item.issue || "";
  });

  // VLANs - transform from API data (use details array from parser if available)
  const vlans = React.useMemo(() => {
    // Prefer details array from parser (has id, name, status, access_ports)
    if (vlansData?.details && Array.isArray(vlansData.details) && vlansData.details.length > 0) {
      return vlansData.details.map(vlanDetail => {
        const vlanId = vlanDetail.id;
        const vlanName = vlanDetail.name || "";
        const vlanStatus = vlanDetail.status || "active";

        // Use access_ports from parser
        const accessPorts = vlanDetail.access_ports || [];

        // Find trunk ports for this VLAN from trunk_ports array
        const trunkPortsForVlan = (vlansData.trunk_ports || [])
          .filter(tp => {
            const allowed = tp.allowed_vlans || "";
            return allowed === "ALL" || allowed.includes(vlanId) || allowed.includes("-");
          })
          .map(tp => tp.port);

        // Find SVI IP
        const sviInterface = interfaces.find(i =>
          (i.type === "SVI" || i.type === "Vlan" || i.name?.startsWith("Vlan")) &&
          (i.name === `Vlan${vlanId}` || i.name === `Vlanif${vlanId}`)
        );
        const sviIp = sviInterface?.ipv4_address || null;

        // Find HSRP VIP (if any)
        const hsrpList = Array.isArray(haData.hsrp) ? haData.hsrp : (haData.hsrp?.groups || []);
        const hsrpGroup = hsrpList.find(g => String(g.vlan_id) === String(vlanId) || g.interface?.includes(vlanId));
        const hsrpVip = hsrpGroup?.virtual_ip || null;

        return {
          vlanId,
          name: vlanName,
          status: vlanStatus,
          accessPorts: accessPorts.join(", ") || "—",
          trunkPorts: trunkPortsForVlan.join(", ") || "—",
          sviIp: sviIp || "—",
          hsrpVip: hsrpVip || "—"
        };
      });
    }

    // Fallback to old method using vlan_list
    if (!vlansData || !vlanList.length) return [];
    return vlanList.map(vlanId => {
      const vlanName = vlansData.vlan_names?.[vlanId] || "";
      const vlanStatus = vlansData.vlan_status?.[vlanId] || "active";
      const accessPorts = interfaces.filter(i => i.port_mode === "access" && String(i.access_vlan) === String(vlanId)).map(i => i.name);
      const trunkPorts = interfaces.filter(i => i.port_mode === "trunk").map(i => i.name);
      const sviInterface = interfaces.find(i => (i.type === "SVI" || i.type === "Vlan" || i.name?.startsWith("Vlan")) && i.name?.includes(vlanId));
      const sviIp = sviInterface?.ipv4_address || null;
      const hsrpList = Array.isArray(haData.hsrp) ? haData.hsrp : (haData.hsrp?.groups || []);
      const hsrpGroup = hsrpList.find(g => String(g.vlan_id) === String(vlanId));
      const hsrpVip = hsrpGroup?.virtual_ip || null;

      return {
        vlanId,
        name: vlanName,
        status: vlanStatus,
        accessPorts: accessPorts.join(", ") || "—",
        trunkPorts: trunkPorts.join(", ") || "—",
        sviIp: sviIp || "—",
        hsrpVip: hsrpVip || "—"
      };
    });
  }, [vlansData, vlanList, interfaces, haData]);

  // Interfaces - transform from API (scope 2.3.2.2.1–2.3.2.2.16); derive type from name if missing
  const ifaces = React.useMemo(() => {
    const inferType = (name) => {
      if (!name || name === "—") return "—";
      const n = String(name);
      if (/^Gi(gabit)?Ethernet|^GE/i.test(n)) return "GigabitEthernet";
      if (/^TenGigabit|^10GE|^XGigabit/i.test(n)) return "TenGigabitEthernet";
      if (/^FastEthernet|^Fa\b/i.test(n)) return "FastEthernet";
      if (/^Ethernet\b/i.test(n)) return "Ethernet";
      if (/^Eth-Trunk|^Port-channel|^Po\b/i.test(n)) return "Aggregate";
      if (/^Vlan|^Vlanif/i.test(n)) return "SVI";
      if (/^Loopback|^Lo\b/i.test(n)) return "Loopback";
      return n.split(/\d/)[0] || "—";
    };
    return interfaces.map(iface => ({
      port: iface.name || "—",
      type: iface.type || inferType(iface.name),
      admin: iface.admin_status || "—",
      oper: iface.oper_status || "—",
      lineProto: iface.line_protocol || iface.protocol || "—",
      desc: iface.description || "—",
      ipv4: iface.ipv4_address || "—",
      ipv6: iface.ipv6_address || "—",
      mac: iface.mac_address || "—",
      speed: iface.speed || "—",
      duplex: iface.duplex || "—",
      mtu: iface.mtu != null ? String(iface.mtu) : "—",
      mode: iface.port_mode || "—",
      accessVlan: iface.access_vlan ?? "—",
      nativeVlan: iface.native_vlan ?? "—",
      allowedShort: (Array.isArray(iface.allowed_vlans) ? iface.allowed_vlans.join(", ") : (typeof iface.allowed_vlans === "string" ? iface.allowed_vlans : null)) || "—",
      stpRole: iface.stp_role || "—",
      stpState: iface.stp_state || "—",
      stpEdgedPort: iface.stp_edged_port !== undefined ? (iface.stp_edged_port ? "Yes" : "No") : "—",
      poeW: iface.poe_power ?? "—",
    }));
  }, [interfaces, stpData]);
  // Columns per 2.3.2.2: Name, Type, Admin, Oper, Line Proto, Desc, IPv4, IPv6, MAC, Speed, Duplex, MTU, Mode, Access VLAN, Native, Allowed
  const ifaceColumns = [
    { header: "Name", key: "port", title: "2.3.2.2.1 Interface Name", cell: (r) => <span className="font-medium text-slate-800 dark:text-slate-200">{r.port}</span> },
    { header: "Type", key: "type", title: "2.3.2.2.2 Interface Type", cell: (r) => r.type || "—" },
    { header: "Admin", key: "admin", title: "2.3.2.2.3 Administrative Status", cell: (r) => r.admin || "—" },
    { header: "Oper", key: "oper", title: "2.3.2.2.4 Operational Status", cell: (r) => r.oper || "—" },
    { header: "Line", key: "lineProto", title: "2.3.2.2.5 Line Protocol Status", cell: (r) => r.lineProto || "—" },
    { header: "Description", key: "desc", title: "2.3.2.2.6 Description", cell: (r) => (r.desc && r.desc !== "—" ? <span className="max-w-[200px] truncate block" title={r.desc}>{r.desc}</span> : "—") },
    { header: "IPv4", key: "ipv4", title: "2.3.2.2.7 IPv4 Address", cell: (r) => r.ipv4 || "—" },
    { header: "IPv6", key: "ipv6", title: "2.3.2.2.8 IPv6 Address", cell: (r) => r.ipv6 || "—" },
    { header: "MAC", key: "mac", title: "2.3.2.2.9 MAC Address", cell: (r) => r.mac || "—" },
    { header: "Speed", key: "speed", title: "2.3.2.2.10 Speed", cell: (r) => r.speed || "—" },
    { header: "Duplex", key: "duplex", title: "2.3.2.2.11 Duplex Mode", cell: (r) => r.duplex || "—" },
    { header: "MTU", key: "mtu", title: "2.3.2.2.12 MTU Value", cell: (r) => r.mtu || "—" },
    { header: "Mode", key: "mode", title: "2.3.2.2.13 Port Mode", cell: (r) => r.mode || "—" },
    { header: "Access", key: "accessVlan", title: "2.3.2.2.14 Access VLAN", cell: (r) => r.accessVlan ?? "—" },
    { header: "Native", key: "nativeVlan", title: "2.3.2.2.15 Native VLAN", cell: (r) => r.nativeVlan ?? "—" },
    { header: "Allowed VLANs", key: "allowedShort", title: "2.3.2.2.16 Allowed VLAN List", cell: (r) => r.allowedShort || "—" },
  ];
  const [qMode, setQMode] = React.useState("all");
  const [qState, setQState] = React.useState("all");
  const [qVlan, setQVlan] = React.useState("");
  const [qSpeed, setQSpeed] = React.useState("all");
  const filteredIfaces = React.useMemo(() => {
    return ifaces.filter((r) => {
      if (qMode !== "all" && r.mode !== qMode) return false;
      if (qState !== "all") {
        const isUp = r.admin === "up" && r.oper === "up";
        if (qState === "up" && !isUp) return false;
        if (qState === "down" && isUp) return false;
      }
      if (qVlan && String(r.accessVlan || "") !== String(qVlan)) return false;
      if (qSpeed !== "all" && String(r.speed || "").toLowerCase() !== String(qSpeed).toLowerCase()) return false;
      return true;
    });
  }, [ifaces, qMode, qState, qVlan, qSpeed]);

  const onExportIfaces = () => {
    const headers = ifaceColumns.map((c) => c.key);
    const rows = filteredIfaces.map((r) =>
      headers.map((h) => (r[h] != null ? `"${String(r[h]).replaceAll('"', '""')}"` : "")).join(",")
    );
    downloadCSV([headers.join(","), ...rows].join("\n"), `${facts.device}_interfaces.csv`);
  };

  const vlanColumns = [
    { header: "VLAN ID", key: "vlanId", cell: (r) => <span className="font-medium text-slate-800 dark:text-slate-200">{r.vlanId}</span> },
    { header: "Name", key: "name", cell: (r) => r.name || "—" },
    {
      header: "Status", key: "status", cell: (r) => {
        const status = r.status || "—";
        const isActive = status.toLowerCase().includes("active") && !status.toLowerCase().includes("unsup");
        return <span className={isActive ? "text-emerald-500" : "text-amber-500"}>{status}</span>;
      }
    },
    { header: "Access Ports", key: "accessPorts", cell: (r) => r.accessPorts || "—" },
    { header: "Trunk Ports", key: "trunkPorts", cell: (r) => r.trunkPorts || "—" },
    { header: "SVI IP", key: "sviIp", cell: (r) => r.sviIp || "—" },
    { header: "HSRP VIP", key: "hsrpVip", cell: (r) => r.hsrpVip || "—" },
  ];
  const exportVlans = () => {
    const headers = ["vlanId", "name", "status", "accessPorts", "trunkPorts", "sviIp", "hsrpVip"];
    const rows = vlans.map((v) => headers.map((h) => `"${String(v[h] ?? "").replaceAll('"', '""')}"`).join(","));
    downloadCSV([headers.join(","), ...rows].join("\n"), `${facts.device}_vlans.csv`);
  };

  // Tabs
  const [tab, setTab] = React.useState("overview"); // overview | interfaces | vlans | stp | routing | neighbors | macarp | security | ha | raw
  const [rawSubTab, setRawSubTab] = React.useState("original"); // original | parsed
  const [llmPanelTab, setLlmPanelTab] = React.useState("summary"); // summary | recommendations | drift — folder-like selection for LLM section
  const [routeTableSearch, setRouteTableSearch] = React.useState("");
  const filteredRouteTable = React.useMemo(() => {
    const r = routingData.routes || [];
    if (!routeTableSearch.trim()) return r;
    const q = routeTableSearch.trim().toLowerCase();
    const protocolLabels = { O: "ospf", C: "connected", L: "local", S: "static", B: "bgp", R: "rip", D: "eigrp", i: "isis" };
    return r.filter((row) => {
      const protoLabel = (row.protocol && protocolLabels[row.protocol]) || (row.protocol || "").toLowerCase();
      return (protoLabel && protoLabel.includes(q))
        || (row.network && row.network.toLowerCase().includes(q))
        || (row.next_hop && String(row.next_hop).toLowerCase().includes(q))
        || (row.interface && String(row.interface).toLowerCase().includes(q));
    });
  }, [routingData.routes, routeTableSearch]);

  // Config drift: compare two latest versions from version history (raw config files)
  const driftSummary = React.useMemo(() => {
    const v = deviceConfigVersions?.versions;
    if (!v || v.length < 2) return null;
    const older = v[1];
    const newer = v[0];
    const fn = deviceConfigVersions.filename || "config";
    return {
      device: facts.device,
      from: `${fn} (v${older.version})`,
      to: `${fn} (v${newer.version})`,
    };
  }, [facts.device, deviceConfigVersions]);
  const hasEnoughVersionsForDrift = (deviceConfigVersions?.versions?.length ?? 0) >= 2;

  return (
    <div className="h-full flex flex-col gap-0 overflow-y-auto min-h-0">
      {deviceLlmNotification?.show && (
        <NotificationModal
          show={true}
          onClose={() => setDeviceLlmNotification((n) => (n ? { ...n, show: false } : null))}
          title={deviceLlmNotification.title || "LLM Complete"}
          message={deviceLlmNotification.message || ""}
          metrics={deviceLlmNotification.metrics}
          type={deviceLlmNotification.type || "success"}
          onRegenerate={deviceLlmNotification.onRegenerate}
        />
      )}
      {/* Header: title larger, tabs and back button */}
      <div className="flex-shrink-0 flex items-center justify-between gap-4 py-3 px-3 flex-wrap border-b border-slate-300 dark:border-slate-700/80 bg-slate-50/80 dark:bg-transparent">
        <div className="flex flex-col gap-0.5 min-w-0">
          <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-200 flex items-center gap-2">
            <span className="w-1 h-4 bg-slate-400 dark:bg-slate-500 rounded-full flex-shrink-0" />
            More Details — {facts.device}
          </h2>
          <span className="text-sm text-slate-600 dark:text-slate-400">
            From config/show parsing {facts.sourceFilename && facts.sourceFilename !== "—" ? "(" + facts.sourceFilename + ")" : ""} • Mgmt IP: {facts.mgmtIp || "—"}
          </span>
        </div>
        {!loading && !error && (
          <div className="flex gap-2 flex-wrap items-center">
            <div className="flex gap-1.5 flex-wrap">
              {[
                { id: "overview", label: "Overview" },
                { id: "interfaces", label: "Interfaces" },
                { id: "vlans", label: "VLANs" },
                { id: "stp", label: "STP" },
                { id: "routing", label: "Routing" },
                { id: "neighbors", label: "Neighbors" },
                { id: "macarp", label: "MAC/ARP" },
                { id: "security", label: "Security" },
                { id: "ha", label: "HA" },
                { id: "raw", label: "Raw" }
              ].map((t) => (
                <button
                  key={t.id}
                  onClick={() => setTab(t.id)}
                  className={`px-3 py-1.5 rounded-xl text-xs font-medium transition-all border ${tab === t.id
                    ? "bg-white/90 dark:bg-white/10 backdrop-blur-sm border-slate-300/80 dark:border-slate-600/80 text-slate-800 dark:text-slate-100 shadow-sm"
                    : "bg-slate-100/80 dark:bg-slate-800/50 border-slate-300 dark:border-slate-700/60 text-slate-700 dark:text-slate-400 hover:bg-slate-200/80 dark:hover:bg-slate-700/50 hover:text-slate-900 dark:hover:text-slate-300"
                    }`}
                >
                  {t.label}
                </button>
              ))}
            </div>
            {goBack && (goBackHref != null ? (
              <a href={goBackHref} onClick={(e) => handleNavClick(e, goBack)} className="inline-flex items-center justify-center rounded-lg px-3 py-1.5 h-8 text-xs font-medium shadow-sm transition focus:outline-none focus:ring-2 focus:ring-offset-2 flex-shrink-0 bg-white text-gray-900 ring-1 ring-gray-300 hover:bg-gray-50 focus:ring-blue-500 dark:bg-gray-800 dark:text-gray-100 dark:ring-gray-600 dark:hover:bg-gray-700">← Back to Summary</a>
            ) : (
              <Button variant="secondary" onClick={goBack} className="text-xs py-1.5 px-3 h-8 flex-shrink-0">← Back to Summary</Button>
            ))}
            {canDeleteDevice && (
              <Button
                variant="danger"
                onClick={() => {
                  showConfirmModal({
                    title: "Delete Device",
                    message: `Are you sure you want to delete device "${deviceId}"? This will remove all config versions, device image, and analysis results. This action cannot be undone.`,
                    confirmText: "Delete Device",
                    cancelText: "Cancel",
                    variant: "danger",
                    onConfirm: async () => {
                      try {
                        const projectId = project?.project_id || project?.id;
                        await api.deleteDevice(projectId, deviceId);
                        if (loadProjects) await loadProjects();
                        if (goBack) goBack();
                      } catch (e) {
                        alert("Failed to delete device: " + formatError(e));
                      }
                    }
                  });
                }}
                className="text-xs py-1.5 px-3 h-8 flex-shrink-0"
              >
                Delete Device
              </Button>
            )}
          </div>
        )}
      </div>

      {loading && (
        <div className="flex-1 flex items-center justify-center text-slate-500 dark:text-slate-400 text-xs py-8">
          Loading device details...
        </div>
      )}

      {error && (
        <div className="rounded-xl border border-rose-300 dark:border-rose-700 bg-rose-50 dark:bg-rose-900/20 p-4 text-xs text-rose-700 dark:text-rose-400">
          Error: {safeDisplay(error)}
        </div>
      )}

      {/* OVERVIEW: Top = Device Image | LLM side by side; Bottom = Device Facts */}
      {!loading && !error && tab === "overview" && (
        <div className="flex-1 min-h-0 flex flex-col gap-3 overflow-hidden p-2">
          {/* Top row: Device Image (left) + LLM section (right) */}
          <div className="grid grid-cols-1 md:grid-cols-12 gap-3 min-h-0 flex-1" style={{ minHeight: "280px" }}>
            <div className="md:col-span-5 min-h-0 overflow-hidden rounded-xl border border-slate-300 dark:border-slate-800 bg-white dark:bg-slate-900/50 flex flex-col shadow-sm dark:shadow-none">
              <Card className="flex-1 min-h-0 flex flex-col overflow-hidden">
                <div className="flex-1 min-h-0 overflow-auto">
                  <DeviceImageUpload
                    project={project}
                    deviceName={deviceId}
                    authedUser={authedUser}
                    setProjects={setProjects}
                    can={can}
                    showConfirmModal={showConfirmModal}
                  />
                </div>
              </Card>
            </div>
            {/* LLM panel: folder-like tabs (like summary page) + AI button + content */}
            <div className="md:col-span-7 min-h-0 flex flex-col rounded-xl border border-slate-300 dark:border-slate-800 bg-white/95 dark:bg-slate-900/50 overflow-hidden shadow-sm dark:shadow-none backdrop-blur-sm">
              <div className="flex-shrink-0 flex items-center justify-between border-b border-slate-300 dark:border-slate-700/80 bg-slate-50/90 dark:bg-slate-900/60 backdrop-blur-sm">
                <div className="flex">
                  <button
                    type="button"
                    onClick={() => setLlmPanelTab("summary")}
                    className={`px-4 py-2.5 text-sm font-medium rounded-t-lg border transition-colors ${llmPanelTab === "summary"
                      ? "bg-white/90 dark:bg-white/10 border-slate-300/70 dark:border-slate-600/70 border-b-white dark:border-b-slate-900/50 text-slate-800 dark:text-slate-100 shadow-sm -mb-px"
                      : "border-transparent text-slate-700 dark:text-slate-400 hover:bg-slate-100/80 dark:hover:bg-slate-800/40 hover:text-slate-900 dark:hover:text-slate-300"
                      }`}
                  >
                    Device Summary
                  </button>
                  <button
                    type="button"
                    onClick={() => setLlmPanelTab("recommendations")}
                    className={`px-4 py-2.5 text-sm font-medium rounded-t-lg border transition-colors ${llmPanelTab === "recommendations"
                      ? "bg-white/90 dark:bg-white/10 border-slate-300/70 dark:border-slate-600/70 border-b-white dark:border-b-slate-900/50 text-slate-800 dark:text-slate-100 shadow-sm -mb-px"
                      : "border-transparent text-slate-700 dark:text-slate-400 hover:bg-slate-100/80 dark:hover:bg-slate-800/40 hover:text-slate-900 dark:hover:text-slate-300"
                      }`}
                  >
                    AI Recommendations
                  </button>
                  <button
                    type="button"
                    onClick={() => setLlmPanelTab("drift")}
                    className={`px-4 py-2.5 text-sm font-medium rounded-t-lg border transition-colors ${llmPanelTab === "drift"
                      ? "bg-white/90 dark:bg-white/10 border-slate-300/70 dark:border-slate-600/70 border-b-white dark:border-b-slate-900/50 text-slate-800 dark:text-slate-100 shadow-sm -mb-px"
                      : "border-transparent text-slate-700 dark:text-slate-400 hover:bg-slate-100/80 dark:hover:bg-slate-800/40 hover:text-slate-900 dark:hover:text-slate-300"
                      }`}
                  >
                    Config Drift
                  </button>
                </div>
                <button
                  type="button"
                  onClick={handleDeviceAiClick}
                  disabled={llmBusy || (llmPanelTab === "drift" && !hasEnoughVersionsForDrift)}
                  className="w-8 h-8 flex items-center justify-center rounded-xl bg-white/90 dark:bg-white/10 backdrop-blur-sm border border-slate-300/80 dark:border-slate-600/80 text-slate-700 dark:text-slate-200 shadow-sm hover:bg-white dark:hover:bg-white/15 transition-colors disabled:opacity-50 disabled:cursor-not-allowed mr-2 text-base flex-shrink-0"
                  title={llmPanelTab === "drift" && !hasEnoughVersionsForDrift ? "At least 2 versions in version history required" : (llmBusy && llmBusyMessage ? llmBusyMessage : "Generate with AI (current tab)")}
                  aria-label="AI Analysis"
                >
                  {llmBusy ? "⏳" : "✨"}
                </button>
              </div>
              <div className="flex-1 min-h-0 overflow-y-auto p-3">
                {llmPanelTab === "summary" && (
                  <div>
                    {deviceOverviewLoading && !deviceOverviewGenerating ? (
                      <div className="text-xs text-slate-500 italic">Loading...</div>
                    ) : (
                      <>
                        {deviceOverviewGenerating && (
                          <div className="p-2 rounded-lg bg-slate-200/90 dark:bg-slate-700/50 border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 text-xs mb-2">
                            Analyzing with LLM... This may take 1–2 minutes. You can switch tabs meanwhile.
                          </div>
                        )}
                        {deviceOverviewError && (
                          <div className="p-2 rounded-lg bg-rose-50 dark:bg-rose-900/20 border border-rose-300 dark:border-rose-700 text-rose-700 dark:text-rose-400 text-xs mb-2 break-words">
                            Error: {safeDisplay(deviceOverviewError)}
                          </div>
                        )}
                        {deviceOverviewData != null && (deviceOverviewData.sections != null || deviceOverviewData.role != null || deviceOverviewData.config_highlights != null) ? (
                          <StructuredDeviceSummary data={deviceOverviewData} className="text-slate-700 dark:text-slate-300" />
                        ) : deviceOverviewText != null ? (
                          <SummaryMarkdown text={deviceOverviewText} size="xs" className="text-slate-700 dark:text-slate-300" />
                        ) : (
                          <div className="text-slate-500 dark:text-slate-400 italic text-xs">
                            Click the AI button above to generate summary.
                          </div>
                        )}
                      </>
                    )}
                  </div>
                )}
                {llmPanelTab === "recommendations" && (
                  <div>
                    <div className="text-xs font-semibold text-slate-800 dark:text-slate-400 uppercase tracking-wide mb-2">AI-generated recommendations for this device</div>
                    {deviceRecsLoading && !deviceRecsGenerating ? (
                      <div className="text-xs text-slate-500">Loading...</div>
                    ) : (
                      <>
                        {deviceRecsGenerating && (
                          <div className="p-2 rounded bg-slate-700/50 border border-slate-600 text-slate-300 text-xs mb-2">
                            Analyzing with LLM... Finding flaws and recommending improvements.
                          </div>
                        )}
                        {deviceRecsError && (
                          <div className="p-2 rounded bg-rose-900/20 border border-rose-700 text-rose-400 text-xs mb-2 break-words">
                            Error: {safeDisplay(deviceRecsError)}
                          </div>
                        )}
                        {deviceRecsList.length ? (
                          <div className="space-y-2">
                            {deviceRecsList.map((item, idx) => {
                              const sev = (item.severity || "medium").toLowerCase();
                              return (
                                <div key={idx} className="p-2 rounded-lg border text-xs break-words" style={{
                                  borderColor: sev === "high" ? "#ef4444" : sev === "medium" ? "#eab308" : "#22c55e",
                                  backgroundColor: sev === "high" ? "rgba(239, 68, 68, 0.08)" : sev === "medium" ? "rgba(234, 179, 8, 0.1)" : "rgba(34, 197, 94, 0.08)"
                                }}>
                                  <div className="flex items-start gap-2 mb-1">
                                    <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ${sev === "high" ? "bg-rose-500 text-white" :
                                      sev === "medium" ? "bg-yellow-500 text-white" :
                                        "bg-green-500 text-white"
                                      }`}>
                                      {sev.toUpperCase()}
                                    </span>
                                  </div>
                                  {item.issue && (
                                    <div className="text-xs text-slate-800 dark:text-slate-300 mb-1">
                                      <span className="font-semibold">Issue:</span> {item.issue}
                                    </div>
                                  )}
                                  {item.recommendation && (
                                    <div className="text-xs text-slate-800 dark:text-slate-300">
                                      <span className="font-semibold">Recommendation:</span> {item.recommendation}
                                    </div>
                                  )}
                                </div>
                              );
                            })}
                          </div>
                        ) : (
                          <div className="text-xs text-slate-700 dark:text-slate-500">
                            No AI recommendations yet. Click the AI button above to generate (LLM will find flaws and recommend config improvements).
                          </div>
                        )}
                      </>
                    )}
                  </div>
                )}
                {llmPanelTab === "drift" && (
                  <div>
                    {!deviceDriftData && (
                      <div className="text-xs font-semibold text-slate-800 dark:text-slate-400 uppercase tracking-wide mb-2">Configuration drift (raw config — 2 latest versions)</div>
                    )}
                    {loadingBackups || loadingVersions ? (
                      <div className="text-xs text-slate-500 dark:text-slate-400">Loading version history...</div>
                    ) : !deviceConfigVersions ? (
                      <div className="text-xs text-slate-500 dark:text-slate-400">No config file for this device in the Config folder.</div>
                    ) : !hasEnoughVersionsForDrift ? (
                      <div className="text-xs text-slate-500 dark:text-slate-400">Use files from this device&apos;s version history — at least 2 versions required to compare (currently {deviceConfigVersions.versions?.length ?? 0} version(s)).</div>
                    ) : (
                      <>
                        {deviceDriftGenerating && (
                          <div className="p-2 rounded-lg bg-slate-200/90 dark:bg-slate-700/50 border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 text-xs mb-2">
                            Comparing latest 2 config versions with LLM (configuration section only)...
                          </div>
                        )}
                        {deviceDriftError && (
                          <div className="p-2 rounded-lg bg-rose-50 dark:bg-rose-900/20 border border-rose-300 dark:border-rose-700 text-rose-700 dark:text-rose-400 text-xs mb-2 break-words">
                            Error: {safeDisplay(deviceDriftError)}
                          </div>
                        )}
                        {deviceDriftData ? (
                          <div className="text-xs text-slate-700 dark:text-slate-300 space-y-3">
                            <div className="flex items-center justify-between">
                              <div className="font-semibold text-slate-800 dark:text-slate-200">Device: {safeDisplay(deviceDriftData.device_name || facts?.device)}</div>
                              <div className="text-slate-500 dark:text-slate-400 text-xs">
                                {(deviceDriftData.changes || []).length} change(s)
                              </div>
                            </div>
                            <div className="text-slate-600 dark:text-slate-400 text-xs bg-slate-100 dark:bg-slate-800/50 px-2 py-1 rounded">
                              Compare: <span className="font-medium">{safeDisplay(deviceDriftData.from_filename)}</span>
                              <span className="mx-2">→</span>
                              <span className="font-medium">{safeDisplay(deviceDriftData.to_filename)}</span>
                            </div>
                            {deviceDriftData.difference_percent != null && (
                              <div className="text-slate-600 dark:text-slate-400 text-xs">
                                Estimated difference:{" "}
                                <span className="font-semibold">
                                  {typeof deviceDriftData.difference_percent === "number"
                                    ? `${Number(deviceDriftData.difference_percent.toFixed(1)).toString().replace(/\.0$/, "")}%`
                                    : `${safeDisplay(deviceDriftData.difference_percent)}%`}
                                </span>{" "}
                                of configuration changed.
                              </div>
                            )}
                            <div className="space-y-2">
                              {(deviceDriftData.changes || []).map((c, i) => {
                                const typeColors = {
                                  add: { bg: "rgba(34, 197, 94, 0.15)", border: "#22c55e", badge: "bg-emerald-500", label: "ADDED" },
                                  remove: { bg: "rgba(244, 63, 94, 0.15)", border: "#f43f5e", badge: "bg-rose-500", label: "REMOVED" },
                                  modify: { bg: "rgba(234, 179, 8, 0.15)", border: "#eab308", badge: "bg-amber-500", label: "MODIFIED" },
                                };
                                const colors = typeColors[c.type] || typeColors.modify;
                                return (
                                  <div
                                    key={i}
                                    className="p-2.5 rounded-lg border"
                                    style={{ backgroundColor: colors.bg, borderColor: colors.border }}
                                  >
                                    <div className="flex items-start gap-2 mb-1.5">
                                      <span className={`text-xs font-semibold px-1.5 py-0.5 rounded text-white ${colors.badge}`}>
                                        {colors.label}
                                      </span>
                                      {c.section && (
                                        <span className="text-xs font-medium text-slate-700 dark:text-slate-300">
                                          {safeDisplay(c.section)}
                                        </span>
                                      )}
                                    </div>
                                    {c.description && (
                                      <div className="text-slate-700 dark:text-slate-300 text-xs mb-1.5">
                                        {safeDisplay(c.description)}
                                      </div>
                                    )}
                                    {(c.old_value || c.new_value) && (
                                      <div className="text-xs space-y-1 mt-2 pt-2 border-t border-slate-300/30 dark:border-slate-600/30">
                                        {c.old_value && (
                                          <div className="flex items-start gap-2">
                                            <span className="text-rose-500 font-mono flex-shrink-0">−</span>
                                            <code className="text-rose-600 dark:text-rose-400 bg-rose-100/50 dark:bg-rose-900/20 px-1 rounded break-all">
                                              {safeDisplay(c.old_value)}
                                            </code>
                                          </div>
                                        )}
                                        {c.new_value && (
                                          <div className="flex items-start gap-2">
                                            <span className="text-emerald-500 font-mono flex-shrink-0">+</span>
                                            <code className="text-emerald-600 dark:text-emerald-400 bg-emerald-100/50 dark:bg-emerald-900/20 px-1 rounded break-all">
                                              {safeDisplay(c.new_value)}
                                            </code>
                                          </div>
                                        )}
                                      </div>
                                    )}
                                  </div>
                                );
                              })}
                            </div>
                            {(deviceDriftData.changes || []).length === 0 && (
                              <div className="text-slate-500 dark:text-slate-400 italic text-center py-4">
                                No configuration changes detected between versions.
                              </div>
                            )}
                          </div>
                        ) : (
                          <div className="grid gap-2">
                            <div className="text-xs text-slate-700 dark:text-slate-300">
                              <b>Device:</b> {safeDisplay(facts?.device)} <br />
                              <b>Version history:</b> {deviceConfigVersions.versions?.length ?? 0} version(s) (raw config) <br />
                              <b>Compare:</b>{" "}
                              <span className="text-slate-600 dark:text-slate-400 font-medium">{safeDisplay(driftSummary?.from)}</span>
                              <span className="mx-1">→</span>
                              <span className="text-slate-600 dark:text-slate-400 font-medium">{safeDisplay(driftSummary?.to)}</span>
                            </div>
                            <div className="text-xs text-slate-500 dark:text-slate-400">
                              Click the AI button above to compare configuration (running-config / current-configuration style) between the 2 latest versions.
                            </div>
                            <Button variant="secondary" onClick={() => setCompareOpen(true)} className="text-xs py-1.5 px-2">Compare Backups</Button>
                          </div>
                        )}
                      </>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Bottom: Device Facts — scope 2.3.2.1.1–2.3.2.1.9 (9 primary fields) */}
          <div className="flex-shrink-0 rounded-xl border border-slate-300 dark:border-slate-800 bg-white dark:bg-slate-900/50 overflow-hidden shadow-sm dark:shadow-none">
            <Card title="Device Facts">
              <div className="grid gap-3 grid-cols-1 sm:grid-cols-2 md:grid-cols-3 text-xs">
                {deviceFactsPrimary.map((item) => (
                  <Metric key={item.key} k={item.label} v={item.value} />
                ))}
              </div>
            </Card>
          </div>
        </div>
      )}

      {/* INTERFACES */}
      {!loading && !error && tab === "interfaces" && (
        <div className="flex-1 min-h-0 overflow-auto">
          <div className="max-h-[80vh] overflow-hidden rounded-2xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900/30 flex flex-col">
            <div className="flex items-center justify-between gap-2 px-4 py-2.5 border-b border-slate-200 dark:border-slate-700 bg-slate-50/70 dark:bg-slate-800/30">
              <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200">Interfaces</h3>
              <Button variant="secondary" onClick={onExportIfaces}>Export CSV</Button>
            </div>
            <div className="flex-1 min-h-0">
              <Table
                searchable
                searchPlaceholder="Search interface name, IP, description..."
                columns={ifaceColumns}
                data={ifaces}
                empty="No interfaces"
                minWidthClass="min-w-[1400px]"
                containerClassName="h-full"
              />
            </div>
          </div>
        </div>
      )}

      {/* VLANS */}
      {!loading && !error && tab === "vlans" && (
        <div className="max-h-[80vh] overflow-hidden rounded-2xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900/30 flex flex-col">
          <div className="flex items-center justify-between gap-2 px-4 py-2.5 border-b border-slate-200 dark:border-slate-700 bg-slate-50/70 dark:bg-slate-800/30">
            <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200">VLANs</h3>
            <Button variant="secondary" onClick={exportVlans}>Export CSV</Button>
          </div>
          <div className="flex-1 min-h-0">
            <Table
              searchable
              searchPlaceholder="Search VLAN ID, name, status..."
              columns={vlanColumns}
              data={vlans}
              empty="No VLANs parsed"
              minWidthClass="min-w-[900px]"
              containerClassName="h-full"
            />
          </div>
        </div>
      )}

      {/* STP */}
      {!loading && !error && tab === "stp" && (
        <div className="grid gap-6">
          <Card title="STP Information">
            <div className="grid gap-4 md:grid-cols-3 lg:grid-cols-4 text-sm mb-6">
              <Metric k="STP Mode" v={stpData.stp_mode || stpData.mode || "—"} />
              <Metric k="Bridge Priority" v={stpData.stp_info?.root_bridge?.priority ?? stpData.bridge_priority ?? "—"} />
              <Metric k="Bridge ID" v={stpData.bridge_id || stpData.stp_info?.root_bridge?.root_bridge_id || "—"} />
              <Metric k="Root Bridge ID" v={stpData.root_bridge_id || "—"} />
              <Metric k="Is Root Bridge" v={
                stpData.stp_info?.root_bridge?.is_local_device_root !== undefined
                  ? (stpData.stp_info.root_bridge.is_local_device_root ? "Yes" : "No")
                  : (stpData.root_bridges?.length > 0 ? "Yes (VLANs: " + stpData.root_bridges.join(", ") + ")" : "—")
              } />
              <Metric k="PortFast Global" v={stpData.portfast_enabled !== undefined ? (stpData.portfast_enabled ? "Enabled" : "Disabled") : "—"} />
              <Metric k="BPDU Guard Global" v={stpData.bpduguard_enabled !== undefined ? (stpData.bpduguard_enabled ? "Enabled" : "Disabled") : "—"} />
            </div>

            {/* STP Interfaces from parser - with full details */}
            {stpData.interfaces && Array.isArray(stpData.interfaces) && stpData.interfaces.length > 0 && (
              <div className="mt-4 max-h-[60vh] overflow-hidden rounded-2xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900/30 flex flex-col">
                <div className="flex items-center justify-between gap-2 px-4 py-2.5 border-b border-slate-200 dark:border-slate-700 bg-slate-50/70 dark:bg-slate-800/30">
                  <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200">STP Ports</h3>
                </div>
                <div className="flex-1 min-h-0">
                  <Table
                    searchable
                    searchPlaceholder="Search port name..."
                    columns={[
                      { header: "Port", key: "port", cell: (r) => <span className="font-medium text-slate-800 dark:text-slate-200">{r.port}</span> },
                      {
                        header: "Role", key: "role", cell: (r) => {
                          const role = r.role || "—";
                          const colorClass = role === "Root" ? "text-emerald-600 dark:text-emerald-500" : role === "Designated" ? "text-blue-600 dark:text-blue-500" : role === "Alternate" ? "text-amber-600 dark:text-amber-500" : "";
                          return <span className={colorClass}>{role}</span>;
                        }
                      },
                      {
                        header: "State", key: "state", cell: (r) => {
                          const state = r.state || "—";
                          const colorClass = state === "Forwarding" ? "text-emerald-600 dark:text-emerald-500" : state === "Blocking" ? "text-rose-600 dark:text-rose-500" : state === "Learning" ? "text-amber-600 dark:text-amber-500" : "";
                          return <span className={colorClass}>{state}</span>;
                        }
                      },
                      { header: "Cost", key: "cost", cell: (r) => r.cost ?? "—" },
                      {
                        header: "PortFast", key: "portfast_enabled", cell: (r) => {
                          const enabled = r.portfast_enabled;
                          return <span className={enabled ? "text-emerald-600 dark:text-emerald-500" : "text-slate-500 dark:text-slate-400"}>{enabled ? "Enabled" : "Disabled"}</span>;
                        }
                      },
                      {
                        header: "BPDU Guard", key: "bpduguard_enabled", cell: (r) => {
                          const enabled = r.bpduguard_enabled;
                          return <span className={enabled ? "text-emerald-600 dark:text-emerald-500" : "text-slate-500 dark:text-slate-400"}>{enabled ? "Enabled" : "Disabled"}</span>;
                        }
                      }
                    ]}
                    data={stpData.interfaces}
                    empty="No STP port information available"
                    minWidthClass="min-w-[800px]"
                    containerClassName="h-full"
                  />
                </div>
              </div>
            )}

            {/* Fallback: use stp_info.interfaces if main interfaces not available */}
            {(!stpData.interfaces || stpData.interfaces.length === 0) && stpData.stp_info?.interfaces && Array.isArray(stpData.stp_info.interfaces) && stpData.stp_info.interfaces.length > 0 && (
              <div className="mt-4 max-h-[60vh] overflow-hidden rounded-2xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900/30 flex flex-col">
                <div className="flex items-center justify-between gap-2 px-4 py-2.5 border-b border-slate-200 dark:border-slate-700 bg-slate-50/70 dark:bg-slate-800/30">
                  <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200">STP Ports</h3>
                </div>
                <div className="flex-1 min-h-0">
                  <Table
                    searchable
                    searchPlaceholder="Search port name..."
                    columns={[
                      { header: "Port", key: "port", cell: (r) => <span className="font-medium text-slate-800 dark:text-slate-200">{r.port}</span> },
                      {
                        header: "Role", key: "role", cell: (r) => {
                          const role = r.role || "—";
                          const colorClass = role === "Root" ? "text-emerald-600 dark:text-emerald-500" : role === "Designated" ? "text-blue-600 dark:text-blue-500" : role === "Alternate" ? "text-amber-600 dark:text-amber-500" : "";
                          return <span className={colorClass}>{role}</span>;
                        }
                      },
                      {
                        header: "State", key: "state", cell: (r) => {
                          const state = r.state || "—";
                          const colorClass = state === "Forwarding" ? "text-emerald-600 dark:text-emerald-500" : state === "Blocking" ? "text-rose-600 dark:text-rose-500" : state === "Learning" ? "text-amber-600 dark:text-amber-500" : "";
                          return <span className={colorClass}>{state}</span>;
                        }
                      },
                      { header: "Cost", key: "cost", cell: (r) => r.cost ?? "—" },
                      {
                        header: "PortFast", key: "portfast_enabled", cell: (r) => {
                          const enabled = r.portfast_enabled;
                          return <span className={enabled ? "text-emerald-600 dark:text-emerald-500" : "text-slate-500 dark:text-slate-400"}>{enabled ? "Enabled" : "Disabled"}</span>;
                        }
                      },
                      {
                        header: "BPDU Guard", key: "bpduguard_enabled", cell: (r) => {
                          const enabled = r.bpduguard_enabled;
                          return <span className={enabled ? "text-emerald-600 dark:text-emerald-500" : "text-slate-500 dark:text-slate-400"}>{enabled ? "Enabled" : "Disabled"}</span>;
                        }
                      }
                    ]}
                    data={stpData.stp_info.interfaces}
                    empty="No STP port information available"
                    minWidthClass="min-w-[800px]"
                    containerClassName="h-full"
                  />
                </div>
              </div>
            )}

            {/* Fallback: Legacy port_roles format */}
            {(!stpData.interfaces || stpData.interfaces.length === 0) && (!stpData.stp_info?.interfaces || stpData.stp_info.interfaces.length === 0) && stpData.port_roles && Object.keys(stpData.port_roles).length > 0 && (
              <div className="mt-4 max-h-[60vh] overflow-hidden rounded-2xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900/30 flex flex-col">
                <div className="flex items-center justify-between gap-2 px-4 py-2.5 border-b border-slate-200 dark:border-slate-700 bg-slate-50/70 dark:bg-slate-800/30">
                  <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200">STP Ports</h3>
                </div>
                <div className="flex-1 min-h-0">
                  <Table
                    searchable
                    searchPlaceholder="Search port name..."
                    columns={[
                      { header: "Port", key: "port" },
                      { header: "Role", key: "role" },
                      { header: "State", key: "state" },
                      { header: "Cost", key: "cost", cell: (r) => r.cost || "—" },
                      { header: "PortFast", key: "portfast", cell: (r) => r.portfast ? "Enabled" : "Disabled" },
                      { header: "BPDU Guard", key: "bpduguard", cell: (r) => r.bpduguard ? "Enabled" : "Disabled" }
                    ]}
                    data={Object.entries(stpData.port_roles || {}).map(([port, role]) => ({
                      port,
                      role: role || "—",
                      state: stpData.port_states?.[port] || "—",
                      cost: stpData.port_costs?.[port] || null,
                      portfast: stpData.portfast_enabled?.[port] || false,
                      bpduguard: stpData.bpdu_guard_enabled?.[port] || false
                    }))}
                    empty="No STP port information available"
                    minWidthClass="min-w-[800px]"
                    containerClassName="h-full"
                  />
                </div>
              </div>
            )}

            {/* No STP data fallback */}
            {(!stpData.interfaces || stpData.interfaces.length === 0) && (!stpData.stp_info?.interfaces || stpData.stp_info.interfaces.length === 0) && (!stpData.port_roles || Object.keys(stpData.port_roles).length === 0) && (
              <div className="text-sm text-gray-500 dark:text-gray-400 mt-4">No STP port information available</div>
            )}
          </Card>
        </div>
      )}

      {/* ROUTING */}
      {!loading && !error && tab === "routing" && (
        <RoutingSection routingData={routingData} />
      )}

      {/* NEIGHBORS */}
      {!loading && !error && tab === "neighbors" && (
        <div className="grid gap-6">
          {/* Summary stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="p-3 rounded-xl border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50">
              <div className="text-xs text-slate-500 dark:text-slate-400">Total Neighbors</div>
              <div className="text-xl font-semibold text-slate-800 dark:text-slate-200">{neighborsData.length}</div>
            </div>
            <div className="p-3 rounded-xl border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50">
              <div className="text-xs text-slate-500 dark:text-slate-400">CDP Neighbors</div>
              <div className="text-xl font-semibold text-emerald-600 dark:text-emerald-400">{neighborsData.filter(n => n.discovery_protocol === "CDP" || n.protocol === "CDP").length}</div>
            </div>
            <div className="p-3 rounded-xl border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50">
              <div className="text-xs text-slate-500 dark:text-slate-400">LLDP Neighbors</div>
              <div className="text-xl font-semibold text-blue-600 dark:text-blue-400">{neighborsData.filter(n => n.discovery_protocol === "LLDP" || n.protocol === "LLDP").length}</div>
            </div>
            <div className="p-3 rounded-xl border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50">
              <div className="text-xs text-slate-500 dark:text-slate-400">Unique Devices</div>
              <div className="text-xl font-semibold text-slate-800 dark:text-slate-200">{[...new Set(neighborsData.map(n => n.device_name || n.neighbor_device_name))].length}</div>
            </div>
          </div>

          {neighborsData.length > 0 ? (
            <div className="max-h-[70vh] overflow-hidden rounded-2xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900/30 flex flex-col">
              <div className="flex items-center justify-between gap-2 px-4 py-2.5 border-b border-slate-200 dark:border-slate-700 bg-slate-50/70 dark:bg-slate-800/30">
                <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200">Neighbor Discovery</h3>
              </div>
              <div className="flex-1 min-h-0">
                <Table
                  searchable
                  searchPlaceholder="Search device name, IP, port..."
                  columns={[
                    { header: "Device Name", key: "device_name", cell: (r) => <span className="font-medium text-slate-800 dark:text-slate-200">{r.device_name || r.neighbor_device_name || "—"}</span> },
                    { header: "IP Address", key: "ip_address", cell: (r) => r.ip_address || r.neighbor_ip || "—" },
                    { header: "Platform", key: "platform", cell: (r) => r.platform || r.model || "—" },
                    { header: "Local Port", key: "local_port", cell: (r) => <span className="text-blue-700 dark:text-blue-400">{r.local_port || "—"}</span> },
                    { header: "Remote Port", key: "remote_port", cell: (r) => <span className="text-emerald-700 dark:text-emerald-400">{r.remote_port || "—"}</span> },
                    { header: "Capabilities", key: "capabilities", cell: (r) => (Array.isArray(r.capabilities) ? r.capabilities.join(", ") : (r.capabilities || "—")) },
                    {
                      header: "Protocol", key: "discovery_protocol", cell: (r) => {
                        const proto = r.discovery_protocol || r.protocol || "—";
                        const colorClass = proto === "CDP" ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400" : proto === "LLDP" ? "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400" : "bg-slate-100 text-slate-700 dark:bg-slate-800/30 dark:text-slate-300";
                        return <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${colorClass}`}>{proto}</span>;
                      }
                    }
                  ]}
                  data={neighborsData}
                  empty="No neighbor information available"
                  minWidthClass="min-w-[1100px]"
                  containerClassName="h-full"
                />
              </div>
            </div>
          ) : (
            <Card title="Neighbor Discovery Table">
              <div className="p-4 rounded-xl border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50">
                <div className="flex items-center gap-3 mb-3">
                  <span className="text-2xl">🔗</span>
                  <span className="text-sm font-medium text-slate-700 dark:text-slate-300">No neighbor information detected</span>
                </div>
                <div className="text-sm text-gray-500 dark:text-gray-400">
                  <p>No CDP/LLDP neighbors were found. This could be because:</p>
                  <ul className="list-disc list-inside mt-2 ml-2 text-xs space-y-1">
                    <li>CDP/LLDP neighbor discovery is not enabled on this device</li>
                    <li>The uploaded configuration does not include neighbor output</li>
                    <li>Include "show cdp neighbors detail" or "show lldp neighbors detail" output</li>
                  </ul>
                </div>
              </div>
            </Card>
          )}
        </div>
      )}

      {/* MAC/ARP */}
      {!loading && !error && tab === "macarp" && (
        <div className="grid gap-6">
          {/* Summary stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="p-3 rounded-xl border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50">
              <div className="text-xs text-slate-500 dark:text-slate-400">Total MAC Entries</div>
              <div className="text-xl font-semibold text-slate-800 dark:text-slate-200">{macArpData.mac_table?.length || 0}</div>
            </div>
            <div className="p-3 rounded-xl border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50">
              <div className="text-xs text-slate-500 dark:text-slate-400">Dynamic MACs</div>
              <div className="text-xl font-semibold text-blue-600 dark:text-blue-400">{(macArpData.mac_table || []).filter(m => m.type === "DYNAMIC" || m.type === "dynamic").length}</div>
            </div>
            <div className="p-3 rounded-xl border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50">
              <div className="text-xs text-slate-500 dark:text-slate-400">ARP Entries</div>
              <div className="text-xl font-semibold text-emerald-600 dark:text-emerald-400">{macArpData.arp_table?.length || 0}</div>
            </div>
            <div className="p-3 rounded-xl border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50">
              <div className="text-xs text-slate-500 dark:text-slate-400">VLANs with MACs</div>
              <div className="text-xl font-semibold text-slate-800 dark:text-slate-200">{[...new Set((macArpData.mac_table || []).map(m => m.vlan))].length}</div>
            </div>
          </div>

          {/* MAC Address Table */}
          {macArpData.mac_table && macArpData.mac_table.length > 0 ? (
            <div className="max-h-[55vh] overflow-hidden rounded-2xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900/30 flex flex-col">
              <div className="flex items-center justify-between gap-2 px-4 py-2.5 border-b border-slate-200 dark:border-slate-700 bg-slate-50/70 dark:bg-slate-800/30">
                <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200">MAC Address Table</h3>
              </div>
              <div className="flex-1 min-h-0">
                <Table
                  searchable
                  searchPlaceholder="Search MAC address, VLAN, port..."
                  columns={[
                    { header: "VLAN", key: "vlan", cell: (r) => <span className="font-medium text-blue-700 dark:text-blue-400">{r.vlan ?? "—"}</span> },
                    { header: "MAC Address", key: "mac_address", cell: (r) => <span className="font-mono text-xs">{r.mac_address || "—"}</span> },
                    {
                      header: "Type", key: "type", cell: (r) => {
                        const type = r.type || "Dynamic";
                        const colorClass = type.toLowerCase() === "dynamic" ? "text-emerald-600 dark:text-emerald-500" : type.toLowerCase() === "static" ? "text-amber-600 dark:text-amber-500" : "";
                        return <span className={colorClass}>{type}</span>;
                      }
                    },
                    { header: "Port", key: "port", cell: (r) => <span className="text-slate-700 dark:text-slate-300">{r.port || "—"}</span> }
                  ]}
                  data={macArpData.mac_table}
                  empty="No MAC address table entries"
                  minWidthClass="min-w-[700px]"
                  containerClassName="h-full"
                />
              </div>
            </div>
          ) : (
            <Card title="MAC Address Table">
              <div className="p-4 rounded-xl border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50">
                <div className="text-sm text-gray-500 dark:text-gray-400">
                  No MAC address table entries. Include "show mac address-table" output to populate this table.
                </div>
              </div>
            </Card>
          )}

          {/* ARP Table */}
          {macArpData.arp_table && macArpData.arp_table.length > 0 ? (
            <div className="max-h-[55vh] overflow-hidden rounded-2xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900/30 flex flex-col">
              <div className="flex items-center justify-between gap-2 px-4 py-2.5 border-b border-slate-200 dark:border-slate-700 bg-slate-50/70 dark:bg-slate-800/30">
                <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200">ARP Table</h3>
              </div>
              <div className="flex-1 min-h-0">
                <Table
                  searchable
                  searchPlaceholder="Search IP, MAC, interface..."
                  columns={[
                    { header: "IP Address", key: "ip_address", cell: (r) => <span className="font-mono text-xs text-slate-800 dark:text-slate-200">{r.ip_address || "—"}</span> },
                    { header: "MAC Address", key: "mac_address", cell: (r) => <span className="font-mono text-xs">{r.mac_address || r.hardware_addr || "—"}</span> },
                    { header: "Type", key: "type", cell: (r) => r.type || "ARPA" },
                    { header: "Interface", key: "interface", cell: (r) => <span className="text-blue-700 dark:text-blue-400">{r.interface || "—"}</span> },
                    { header: "Age (min)", key: "age", cell: (r) => r.age ?? "—" }
                  ]}
                  data={macArpData.arp_table}
                  empty="No ARP table entries"
                  minWidthClass="min-w-[800px]"
                  containerClassName="h-full"
                />
              </div>
            </div>
          ) : (
            <Card title="ARP Table">
              <div className="p-4 rounded-xl border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50">
                <div className="text-sm text-gray-500 dark:text-gray-400">
                  No ARP table entries. Include "show ip arp" output to populate this table.
                </div>
              </div>
            </Card>
          )}
        </div>
      )}

      {/* SECURITY */}
      {!loading && !error && tab === "security" && (
        <div className="grid gap-6">
          {/* Security Summary Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="p-3 rounded-xl border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50">
              <div className="text-xs text-slate-500 dark:text-slate-400">Local Users</div>
              <div className="text-xl font-semibold text-slate-800 dark:text-slate-200">{(securityData.users || securityData.user_accounts || []).length}</div>
            </div>
            <div className="p-3 rounded-xl border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50">
              <div className="text-xs text-slate-500 dark:text-slate-400">SSH</div>
              <div className={`text-xl font-semibold ${securityData.ssh?.enabled ? "text-emerald-600 dark:text-emerald-400" : "text-slate-400"}`}>
                {securityData.ssh?.enabled ? `v${securityData.ssh.version || "2"}` : "Disabled"}
              </div>
            </div>
            <div className="p-3 rounded-xl border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50">
              <div className="text-xs text-slate-500 dark:text-slate-400">NTP Status</div>
              <div className={`text-xl font-semibold ${securityData.ntp?.sync_status === "synchronized" ? "text-emerald-600 dark:text-emerald-400" : "text-amber-600 dark:text-amber-400"}`}>
                {securityData.ntp?.sync_status || (securityData.ntp?.enabled ? "Enabled" : "—")}
              </div>
            </div>
            <div className="p-3 rounded-xl border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50">
              <div className="text-xs text-slate-500 dark:text-slate-400">Logging</div>
              <div className={`text-xl font-semibold ${securityData.logging?.enabled ? "text-emerald-600 dark:text-emerald-400" : "text-slate-400"}`}>
                {securityData.logging?.enabled ? "Enabled" : "—"}
              </div>
            </div>
          </div>

          {/* User Accounts - handle both user_accounts and users structures */}
          {((securityData.user_accounts && securityData.user_accounts.length > 0) || (securityData.users && securityData.users.length > 0)) && (
            <div className="max-h-[40vh] overflow-hidden rounded-2xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900/30 flex flex-col">
              <div className="flex items-center justify-between gap-2 px-4 py-2.5 border-b border-slate-200 dark:border-slate-700 bg-slate-50/70 dark:bg-slate-800/30">
                <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200">Local User Accounts</h3>
              </div>
              <div className="flex-1 min-h-0">
                <Table
                  searchable
                  searchPlaceholder="Search username..."
                  columns={[
                    {
                      header: "Username",
                      key: "username",
                      cell: (r) => (
                        <span className="font-medium text-slate-800 dark:text-slate-200">
                          {r.username || "—"}
                        </span>
                      ),
                    },
                    {
                      header: "Privilege Level",
                      key: "privilege",
                      cell: (r) => {
                        const priv = r.privilege_level ?? r.privilege ?? "—";
                        const colorClass =
                          priv === 15
                            ? "text-rose-600 dark:text-rose-500"
                            : priv >= 5
                              ? "text-amber-600 dark:text-amber-500"
                              : "text-slate-600 dark:text-slate-500";
                        return <span className={colorClass}>{priv}</span>;
                      },
                    },
                  ]}
                  data={securityData.user_accounts || securityData.users || []}
                  empty="No user accounts"
                  minWidthClass="min-w-[300px]"
                  containerClassName="h-full"
                />
              </div>
            </div>
          )}

          {/* AAA Configuration - only show if has meaningful data */}
          {securityData.aaa && (securityData.aaa.authentication || securityData.aaa.authorization || securityData.aaa.accounting || (securityData.aaa.protocols && securityData.aaa.protocols.length > 0)) && (
            <Card title="AAA Configuration">
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 text-sm">
                {securityData.aaa.authentication && <Metric k="Authentication" v={securityData.aaa.authentication} />}
                {securityData.aaa.authorization && <Metric k="Authorization" v={securityData.aaa.authorization} />}
                {securityData.aaa.accounting && <Metric k="Accounting" v={securityData.aaa.accounting} />}
                {securityData.aaa.protocols && securityData.aaa.protocols.length > 0 && (
                  <Metric k="Protocols" v={Array.isArray(securityData.aaa.protocols) ? securityData.aaa.protocols.join(", ") : securityData.aaa.protocols} />
                )}
              </div>
            </Card>
          )}

          {/* SSH Configuration */}
          {securityData.ssh && (
            <Card title="SSH Configuration">
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 text-sm">
                <Metric k="Status" v={securityData.ssh.enabled ? <span className="text-emerald-500">Enabled</span> : <span className="text-rose-500">Disabled</span>} />
                <Metric k="Version" v={securityData.ssh.version || "—"} />
                <Metric k="Connection Timeout" v={securityData.ssh.connection_timeout ? `${securityData.ssh.connection_timeout}s` : "—"} />
                <Metric k="Auth Retries" v={securityData.ssh.auth_retries || "—"} />
              </div>
            </Card>
          )}

          {/* SNMP Configuration - only show if enabled or has communities */}
          {securityData.snmp && (securityData.snmp.enabled || (securityData.snmp.communities && securityData.snmp.communities.length > 0)) && (
            <Card title="SNMP Configuration">
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 text-sm mb-4">
                <Metric k="Status" v={securityData.snmp.enabled ? <span className="text-emerald-500">Enabled</span> : <span className="text-slate-400">Disabled</span>} />
                <Metric k="Version" v={securityData.snmp.version || "—"} />
                {securityData.snmp.communities && securityData.snmp.communities.length > 0 && (
                  <Metric k="Communities" v={securityData.snmp.communities.length} />
                )}
              </div>
              {securityData.snmp.communities && securityData.snmp.communities.length > 0 && (
                <div>
                  <h4 className="text-sm font-semibold mb-2 text-slate-700 dark:text-slate-300">SNMP Communities</h4>
                  <div className="max-h-[25vh] overflow-hidden rounded-xl border border-slate-300 dark:border-[#1F2937] bg-white dark:bg-slate-900/30 flex flex-col">
                    <div className="flex-1 min-h-0">
                      <Table
                        columns={[
                          { header: "Name", key: "name", cell: (r) => (typeof r === "string" ? r : (r?.name || r?.community || "—")) },
                          { header: "Group", key: "group", cell: (r) => (typeof r === "object" && r ? (r.group || "—") : "—") },
                          { header: "Access", key: "access", cell: (r) => (typeof r === "object" && r ? (r.access || r.mode || "—") : "—") },
                        ]}
                        data={securityData.snmp.communities}
                        empty="No SNMP communities"
                        minWidthClass="min-w-[500px]"
                        containerClassName="h-full"
                        showToolbar={false}
                      />
                    </div>
                  </div>
                </div>
              )}
            </Card>
          )}

          {/* NTP Configuration */}
          {securityData.ntp && (
            <Card title="NTP Configuration">
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 text-sm">
                <Metric k="Enabled" v={securityData.ntp.enabled ? <span className="text-emerald-500">Yes</span> : "No"} />
                <Metric k="Sync Status" v={
                  securityData.ntp.sync_status === "synchronized"
                    ? <span className="text-emerald-500">Synchronized</span>
                    : <span className="text-amber-500">{securityData.ntp.sync_status || "Unknown"}</span>
                } />
                <Metric k="Stratum" v={securityData.ntp.stratum || "—"} />
                <Metric k="NTP Servers" v={securityData.ntp.servers?.join(", ") || "—"} />
              </div>
            </Card>
          )}

          {/* Logging / Syslog Configuration */}
          {(securityData.logging || securityData.syslog) && (
            <Card title="Logging Configuration">
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 text-sm">
                <Metric k="Enabled" v={(securityData.logging?.enabled || securityData.syslog?.enabled) ? <span className="text-emerald-500">Yes</span> : "No"} />
                <Metric k="Console Level" v={securityData.logging?.console_level || "—"} />
                <Metric k="Log Hosts" v={securityData.logging?.log_hosts?.join(", ") || securityData.syslog?.servers?.join(", ") || "None"} />
                {securityData.logging?.log_buffer && (
                  <Metric k="Buffer Size" v={securityData.logging.log_buffer.max_size ? `${securityData.logging.log_buffer.max_size} bytes` : "—"} />
                )}
              </div>
            </Card>
          )}

          {/* ACLs */}
          {(securityData.acls && Array.isArray(securityData.acls) && securityData.acls.length > 0) && (
            <Card title="Access Control Lists (ACLs)">
              <div className="grid gap-4">
                {securityData.acls.map((acl, idx) => (
                  <Card key={idx} title={`ACL ${acl.acl_number || acl.name || `#${idx + 1}`}`} className="border border-slate-300 dark:border-gray-700">
                    {acl.rules && Array.isArray(acl.rules) && acl.rules.length > 0 ? (
                      <div className="max-h-[45vh] overflow-hidden rounded-xl border border-slate-300 dark:border-[#1F2937] bg-white dark:bg-slate-900/30 flex flex-col">
                        <div className="flex items-center justify-between gap-2 px-3 py-2 border-b border-slate-200 dark:border-slate-700 bg-slate-50/70 dark:bg-slate-800/30">
                          <span className="text-xs font-semibold text-slate-800 dark:text-slate-200">ACL Rules</span>
                        </div>
                        <div className="flex-1 min-h-0">
                          {(() => {
                            const rules = acl.rules;
                            const hasStringRules = rules.some(r => typeof r === "string");
                            const data = hasStringRules
                              ? rules.map((r, i) => (typeof r === "string" ? { id: i + 1, rule: r } : { id: r.id ?? i + 1, ...r }))
                              : rules;
                            const columns = hasStringRules
                              ? [
                                  { header: "Rule ID", key: "id" },
                                  { header: "Rule", key: "rule", cell: (r) => r.rule || "—" },
                                ]
                              : [
                                  { header: "Rule ID", key: "id" },
                                  { header: "Action", key: "action", cell: (r) => r.action?.toUpperCase() || "—" },
                                  { header: "Protocol", key: "protocol", cell: (r) => r.protocol || "—" },
                                  { header: "Source", key: "source", cell: (r) => r.source || r.source_ip || "—" },
                                  { header: "Source Mask", key: "source_mask", cell: (r) => r.source_mask || "—" },
                                  { header: "Destination", key: "destination", cell: (r) => r.destination || r.destination_ip || "—" },
                                  { header: "Destination Mask", key: "destination_mask", cell: (r) => r.destination_mask || "—" }
                                ];
                            return (
                              <Table
                                columns={columns}
                                data={data}
                                empty="No rules in this ACL"
                                minWidthClass={hasStringRules ? "min-w-[700px]" : "min-w-[1200px]"}
                                containerClassName="h-full"
                                showToolbar={false}
                              />
                            );
                          })()}
                        </div>
                      </div>
                    ) : (
                      <div className="text-sm text-gray-500 dark:text-gray-400">No rules defined for this ACL</div>
                    )}
                  </Card>
                ))}
              </div>
            </Card>
          )}

          {(!securityData.user_accounts || securityData.user_accounts.length === 0) && (!securityData.users || securityData.users.length === 0) && !securityData.aaa && !securityData.ssh && !securityData.snmp && !securityData.ntp && !securityData.syslog && !(securityData.logging && (securityData.logging.enabled || (securityData.logging.log_hosts && securityData.logging.log_hosts.length))) && (!securityData.acls || securityData.acls.length === 0) && (
            <Card title="Security">
              <div className="text-sm text-gray-500 dark:text-gray-400">No security information available</div>
            </Card>
          )}
        </div>
      )}

      {/* HA */}
      {!loading && !error && tab === "ha" && (
        <div className="grid gap-6">
          {/* HA Summary */}
          {(() => {
            const etherchannelCount = (haData.etherchannel?.length || 0) + (haData.port_channels?.length || 0) + (haData.etherchannels?.length || 0);
            const hsrpCount = (Array.isArray(haData.hsrp) ? haData.hsrp : (haData.hsrp?.groups || [])).length;
            const vrrpCount = (Array.isArray(haData.vrrp) ? haData.vrrp : (haData.vrrp?.groups || [])).length;

            return (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className="p-3 rounded-xl border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50">
                  <div className="text-xs text-slate-500 dark:text-slate-400">EtherChannel/LAG</div>
                  <div className={`text-xl font-semibold ${etherchannelCount > 0 ? "text-blue-600 dark:text-blue-400" : "text-slate-400"}`}>{etherchannelCount}</div>
                </div>
                <div className="p-3 rounded-xl border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50">
                  <div className="text-xs text-slate-500 dark:text-slate-400">HSRP Groups</div>
                  <div className={`text-xl font-semibold ${hsrpCount > 0 ? "text-emerald-600 dark:text-emerald-400" : "text-slate-400"}`}>{hsrpCount}</div>
                </div>
                <div className="p-3 rounded-xl border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50">
                  <div className="text-xs text-slate-500 dark:text-slate-400">VRRP Groups</div>
                  <div className={`text-xl font-semibold ${vrrpCount > 0 ? "text-amber-600 dark:text-amber-400" : "text-slate-400"}`}>{vrrpCount}</div>
                </div>
                <div className="p-3 rounded-xl border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50">
                  <div className="text-xs text-slate-500 dark:text-slate-400">Total HA Features</div>
                  <div className="text-xl font-semibold text-slate-800 dark:text-slate-200">{etherchannelCount + hsrpCount + vrrpCount}</div>
                </div>
              </div>
            );
          })()}

          {/* EtherChannel / Port-Channel: support multiple field names */}
          {(() => {
            const ethChannels = haData.etherchannel?.length ? haData.etherchannel : (haData.etherchannels?.length ? haData.etherchannels : (haData.port_channels || []));
            return ethChannels.length > 0 ? (
              <div className="max-h-[55vh] overflow-hidden rounded-2xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900/30 flex flex-col">
                <div className="px-4 pt-3 pb-1 flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200">EtherChannel / Port-Channel</h3>
                </div>
                <div className="flex-1 min-h-0">
                  <Table
                    searchable
                    searchPlaceholder="Search port-channel, protocol..."
                    columns={[
                      { header: "Port-Channel", key: "name", cell: (r) => <span className="font-medium text-slate-800 dark:text-slate-200">{r.name || (r.id != null ? `Po${r.id}` : "—")}</span> },
                      { header: "Protocol", key: "protocol", cell: (r) => r.protocol || r.mode || "—" },
                      {
                        header: "Member Interfaces", key: "members", cell: (r) => {
                          if (!r.members || !Array.isArray(r.members) || r.members.length === 0) return "—";
                          const names = r.members.map(m =>
                            typeof m === "string" ? m : (m.name || m.interface || m.ifname || m.port || "")
                          ).filter(Boolean);
                          return names.length ? names.join(", ") : "—";
                        }
                      },
                      {
                        header: "Status", key: "status", cell: (r) => {
                          const status = r.status || "—";
                          const colorClass = status.toLowerCase().includes("up") ? "text-emerald-600 dark:text-emerald-500" : status.toLowerCase().includes("down") ? "text-rose-600 dark:text-rose-500" : "";
                          return <span className={colorClass}>{status}</span>;
                        }
                      }
                    ]}
                    data={ethChannels.map(p => ({
                      name: p.name || (p.id != null ? `Po${p.id}` : "Po"),
                      protocol: p.protocol || p.mode,
                      members: p.members || p.member_interfaces || p.interfaces || [],
                      status: p.status || p.state
                    }))}
                    empty="No Port-Channel information"
                    minWidthClass="min-w-[800px]"
                    containerClassName="h-full"
                  />
                </div>
              </div>
            ) : null;
          })()}

          {/* HSRP */}
          {(() => {
            const hsrpList = Array.isArray(haData.hsrp) ? haData.hsrp : (haData.hsrp?.groups || []);
            return hsrpList.length > 0 ? (
              <div className="max-h-[55vh] overflow-hidden rounded-2xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900/30 flex flex-col">
                <div className="px-4 pt-3 pb-1 flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200">HSRP Groups</h3>
                </div>
                <div className="flex-1 min-h-0">
                  <Table
                    searchable
                    searchPlaceholder="Search interface, virtual IP..."
                    columns={[
                      { header: "Group", key: "group_id", cell: (r) => <span className="font-medium">{r.group_id ?? r.group ?? "—"}</span> },
                      { header: "Interface", key: "interface", cell: (r) => r.interface || "—" },
                      { header: "Virtual IP", key: "virtual_ip", cell: (r) => <span className="text-blue-700 dark:text-blue-400">{r.virtual_ip || "—"}</span> },
                      {
                        header: "Status", key: "status", cell: (r) => {
                          const status = r.status ?? r.state ?? "—";
                          const colorClass = status.toLowerCase().includes("active") ? "text-emerald-600 dark:text-emerald-500" : status.toLowerCase().includes("standby") ? "text-amber-600 dark:text-amber-500" : "";
                          return <span className={colorClass}>{status}</span>;
                        }
                      },
                      { header: "Priority", key: "priority", cell: (r) => r.priority || "—" },
                      { header: "Preempt", key: "preempt", cell: (r) => r.preempt !== undefined ? (r.preempt ? "Yes" : "No") : "—" }
                    ]}
                    data={hsrpList}
                    empty="No HSRP groups"
                    minWidthClass="min-w-[800px]"
                    containerClassName="h-full"
                  />
                </div>
              </div>
            ) : null;
          })()}

          {/* VRRP */}
          {(() => {
            const vrrpList = Array.isArray(haData.vrrp) ? haData.vrrp : (haData.vrrp?.groups || []);
            return vrrpList.length > 0 ? (
              <div className="max-h-[55vh] overflow-hidden rounded-2xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900/30 flex flex-col">
                <div className="px-4 pt-3 pb-1 flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200">VRRP Groups</h3>
                </div>
                <div className="flex-1 min-h-0">
                  <Table
                    searchable
                    searchPlaceholder="Search interface, virtual IP..."
                    columns={[
                      { header: "VRID", key: "vrid", cell: (r) => <span className="font-medium">{r.vrid ?? r.group ?? "—"}</span> },
                      { header: "Interface", key: "interface", cell: (r) => r.interface || "—" },
                      { header: "Virtual IP", key: "virtual_ip", cell: (r) => <span className="text-blue-700 dark:text-blue-400">{r.virtual_ip || "—"}</span> },
                      {
                        header: "State", key: "state", cell: (r) => {
                          const state = r.state || r.status || "—";
                          const colorClass = state.toLowerCase().includes("master") ? "text-emerald-600 dark:text-emerald-500" : state.toLowerCase().includes("backup") ? "text-amber-600 dark:text-amber-500" : "";
                          return <span className={colorClass}>{state}</span>;
                        }
                      },
                      { header: "Priority", key: "priority", cell: (r) => r.priority ?? r.priority_run ?? "—" },
                      { header: "Preempt", key: "preempt", cell: (r) => r.preempt !== undefined ? (r.preempt ? "Yes" : "No") : "—" }
                    ]}
                    data={vrrpList}
                    empty="No VRRP groups"
                    minWidthClass="min-w-[800px]"
                    containerClassName="h-full"
                  />
                </div>
              </div>
            ) : null;
          })()}

          {/* No HA data message */}
          {(() => {
            const etherchannelCount = (haData.etherchannel?.length || 0) + (haData.port_channels?.length || 0) + (haData.etherchannels?.length || 0);
            const hsrpCount = (Array.isArray(haData.hsrp) ? haData.hsrp : (haData.hsrp?.groups || [])).length;
            const vrrpCount = (Array.isArray(haData.vrrp) ? haData.vrrp : (haData.vrrp?.groups || [])).length;

            if (etherchannelCount === 0 && hsrpCount === 0 && vrrpCount === 0) {
              return (
                <Card title="High Availability">
                  <div className="p-4 rounded-xl border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50">
                    <div className="flex items-center gap-3 mb-3">
                      <span className="text-2xl">🔄</span>
                      <span className="text-sm font-medium text-slate-700 dark:text-slate-300">No High Availability features configured</span>
                    </div>
                    <div className="text-sm text-gray-500 dark:text-gray-400 space-y-1">
                      <p>This device does not have HA features configured. Common HA features include:</p>
                      <ul className="list-disc list-inside mt-2 ml-2 text-xs">
                        <li><strong>EtherChannel/Port-Channel/LAG:</strong> Link aggregation for redundancy</li>
                        <li><strong>HSRP:</strong> Hot Standby Router Protocol for gateway redundancy</li>
                        <li><strong>VRRP:</strong> Virtual Router Redundancy Protocol</li>
                      </ul>
                      <p className="mt-2 text-xs">Include "show etherchannel summary", "show standby brief", or "show vrrp brief" output to view HA information.</p>
                    </div>
                  </div>
                </Card>
              );
            }
            return null;
          })()}
        </div>
      )}

      {/* RAW */}
      {!loading && !error && tab === "raw" && (
        <div className="grid gap-6">
          {/* Tabs for Raw view */}
          <div className="flex gap-2 flex-wrap">
            {[
              { id: "original", label: "Original File Content" },
              { id: "parsed", label: "Parsed Data (JSON)" }
            ].map((t) => (
              <button
                key={t.id}
                onClick={() => setRawSubTab(t.id)}
                className={`px-4 py-2 rounded-xl text-sm font-semibold border transition-all ${rawSubTab === t.id
                  ? "bg-white/90 dark:bg-white/10 backdrop-blur-sm border-slate-300/80 dark:border-slate-600/80 text-slate-800 dark:text-slate-100 shadow-sm"
                  : "bg-slate-100/80 dark:bg-slate-800/50 border-slate-300 dark:border-slate-700/60 text-slate-600 dark:text-slate-400 hover:bg-slate-200/80 dark:hover:bg-slate-700/50"
                  }`}
              >
                {t.label}
              </button>
            ))}
          </div>

          {/* Parsed Data (JSON) */}
          {rawSubTab === "parsed" && (
            <Card
              title="Parsed Data from Database (JSON Structure)"
              actions={
                <button
                  onClick={() => {
                    // Create download link for JSON
                    if (!deviceData) {
                      alert('No data available to download');
                      return;
                    }
                    const jsonContent = JSON.stringify(deviceData, null, 2);
                    const blob = new Blob([jsonContent], { type: 'application/json' });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    const deviceName = deviceData.device_name || deviceId || 'config';
                    a.download = `${deviceName}_parsed.json`;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    URL.revokeObjectURL(url);
                  }}
                  disabled={!deviceData}
                  className="inline-flex items-center gap-2 px-3 py-1.5 text-xs font-semibold rounded-xl bg-white/90 dark:bg-white/10 backdrop-blur-sm border border-slate-300/80 dark:border-slate-600/80 text-slate-800 dark:text-slate-100 shadow-sm hover:bg-white dark:hover:bg-white/15 transition focus:outline-none focus:ring-2 focus:ring-slate-400 dark:focus:ring-slate-500 disabled:opacity-50 disabled:cursor-not-allowed"
                  title="Download as JSON file"
                >
                  <span>⬇</span>
                  <span>Download JSON</span>
                </button>
              }
            >
              <div className="rounded-xl border border-slate-300 dark:border-[#1F2937] p-3 bg-gray-50 dark:bg-[#0F172A] text-sm overflow-auto max-h-[70vh]">
                {deviceData ? (
                  <pre className="whitespace-pre-wrap">{JSON.stringify(deviceData, null, 2)}</pre>
                ) : (
                  <div className="text-sm text-gray-500 dark:text-gray-400">No parsed data available</div>
                )}
              </div>
            </Card>
          )}

          {/* Original File Content */}
          {rawSubTab === "original" && (
            <Card
              title="Original File Content"
              actions={
                <button
                  onClick={() => {
                    // Create download link
                    const content = deviceData?.original_content || '';
                    if (!content) {
                      alert('No content available to download');
                      return;
                    }
                    const blob = new Blob([content], { type: 'text/plain' });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    const deviceName = deviceData?.device_name || deviceId || 'config';
                    a.download = `${deviceName}_original.txt`;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    URL.revokeObjectURL(url);
                  }}
                  disabled={!deviceData?.original_content}
                  className="inline-flex items-center gap-2 px-3 py-1.5 text-xs font-semibold rounded-xl bg-white/90 dark:bg-white/10 backdrop-blur-sm border border-slate-300/80 dark:border-slate-600/80 text-slate-800 dark:text-slate-100 shadow-sm hover:bg-white dark:hover:bg-white/15 transition focus:outline-none focus:ring-2 focus:ring-slate-400 dark:focus:ring-slate-500 disabled:opacity-50 disabled:cursor-not-allowed"
                  title="Download as TXT file"
                >
                  <span>⬇</span>
                  <span>Download TXT</span>
                </button>
              }
            >
              <div className="rounded-xl border border-slate-300 dark:border-[#1F2937] p-3 bg-gray-50 dark:bg-[#0F172A] text-sm overflow-auto max-h-[70vh]">
                {deviceData?.original_content ? (
                  <pre className="whitespace-pre-wrap">{deviceData.original_content}</pre>
                ) : (
                  <div className="text-sm text-gray-500 dark:text-gray-400">
                    Original file content not available. This may be because:
                    <ul className="list-disc list-inside mt-2 ml-4">
                      <li>The file was not uploaded with the configuration</li>
                      <li>The original content was not stored in the database</li>
                      <li>Please re-upload the configuration file</li>
                    </ul>
                  </div>
                )}
              </div>
            </Card>
          )}
        </div>
      )}

      {/* Modal: Compare Backups */}
      {compareOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/50" onClick={() => setCompareOpen(false)} />
          <div className="relative z-10 w-full max-w-5xl">
            <Card
              title={`Compare Backups — ${facts.device}`}
              actions={<Button variant="secondary" onClick={() => setCompareOpen(false)}>Close</Button>}
            >
              <div className="grid gap-3">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <Field label="Left (older)">
                    <Select
                      value={leftFileName}
                      onChange={setLeftFileName}
                      options={deviceBackups.map(f => ({ value: f.name, label: f.name }))}
                    />
                  </Field>
                  <Field label="Right (newer)">
                    <Select
                      value={rightFileName}
                      onChange={setRightFileName}
                      options={deviceBackups.map(f => ({ value: f.name, label: f.name }))}
                    />
                  </Field>
                </div>

                <div className="rounded-xl border border-slate-300 dark:border-[#1F2937] overflow-hidden">
                  <div className="grid grid-cols-1 md:grid-cols-2">
                    <div className="border-b md:border-b-0 md:border-r border-[#1F2937] p-3">
                      <div className="text-xs text-gray-400 mb-2 truncate">{leftFile?.name || "—"}</div>
                      <div className="text-xs text-gray-400 mb-2">vs</div>
                      <div className="text-xs text-gray-400 mb-2 truncate">{rightFile?.name || "—"}</div>
                    </div>
                    <div className="p-3">
                      <div className="text-xs text-gray-400 mb-2">Diff (line by line)</div>
                      <div className="bg-[#0D1422] rounded-lg p-3 h-[60vh] overflow-auto text-sm">
                        {leftFile && rightFile ? (
                          simpleDiff(leftFile.content || "", rightFile.content || "").map((d, i) => (
                            <div key={i} className={
                              d.t === "+" ? "text-emerald-400" :
                                d.t === "-" ? "text-rose-400" : "text-gray-300"
                            }>
                              {d.t} {d.l}
                            </div>
                          ))
                        ) : (
                          <div className="text-gray-400">Select both files to compare.</div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>

                {rightFile && (
                  <div className="flex gap-2">
                    {/* Download buttons removed - only available in Documents page */}
                  </div>
                )}
              </div>
            </Card>
          </div>
        </div>
      )}

    </div>
  );
};






const Metric = ({ k, v }) => (
  <div className="rounded-xl border border-slate-300 dark:border-slate-700/80 bg-white dark:bg-slate-800/50 p-3">
    <div className="text-xs text-slate-500 dark:text-slate-400">{safeDisplay(k)}</div>
    <div className="mt-1 font-semibold text-slate-800 dark:text-slate-100">{safeDisplay(v)}</div>
  </div>
);

/* ========= UPLOAD FORMS ========= */
const UploadConfigForm = ({ project, authedUser, onClose, onUpload }) => {
  const [files, setFiles] = useState([]);
  const [details, setDetails] = useState({
    who: authedUser?.username || '',
    what: '',
    where: '',
    when: '',
    why: '',
    description: ''
  });
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const [projectOptions, setProjectOptions] = useState({ what: [], where: [], when: [], why: [] });

  // Load project-specific options
  useEffect(() => {
    const loadProjectOptions = async () => {
      if (!project?.project_id && !project?.id) return;
      try {
        const projectId = project.project_id || project.id;
        const options = await api.getProjectOptions(projectId);
        setProjectOptions(options || { what: [], where: [], when: [], why: [] });
      } catch (error) {
        console.error('Failed to load project options:', error);
      }
    };
    loadProjectOptions();
  }, [project]);

  const handleFileChange = (e) => {
    const selectedFiles = Array.from(e.target.files || []);
    setFiles(prev => [...prev, ...selectedFiles]);
    setError(null);
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const droppedFiles = Array.from(e.dataTransfer.files);
      setFiles(prev => [...prev, ...droppedFiles]);
      setError(null);
    }
  };

  const removeFile = (index) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (files.length === 0) return;

    setIsUploading(true);
    setError(null);

    try {
      // Upload config files - always to Config folder
      const metadata = {
        who: details.who,
        what: details.what,
        where: details.where || null,
        when: details.when || null,
        why: details.why || null,
        description: details.description || null
      };

      const projectId = project.project_id || project.id;
      const result = await api.uploadDocuments(projectId, files, metadata, "Config"); // Force Config folder

      // Upload successful - close modal and refresh
      // Create upload record for UI consistency
      const uploadRecord = createUploadRecord('config', files, authedUser.username, projectId, {
        ...details,
        folderId: "Config"
      });

      onUpload(uploadRecord, "Config");
      onClose(); // Close modal after successful upload
    } catch (error) {
      console.error('Upload failed:', error);
      setError(formatError(error) || 'Upload failed. Please try again.');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 overflow-y-auto">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="relative z-10 w-full max-w-5xl max-h-[90vh] my-4">
        <Card title="Upload Configuration Files" actions={<Button variant="secondary" onClick={onClose}>Close</Button>}>
          <div className="max-h-[calc(90vh-120px)] overflow-y-auto pr-2">
            <form onSubmit={handleSubmit} className="grid gap-3">
              {error && (
                <div className="rounded-xl border border-rose-300 dark:border-rose-700 bg-rose-50 dark:bg-rose-900/20 p-3 text-sm text-rose-700 dark:text-rose-400">
                  {safeDisplay(error)}
                </div>
              )}

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                <Field label="Responsible User">
                  <Input
                    value={details.who}
                    disabled
                    className="bg-gray-100 dark:bg-gray-700"
                  />
                </Field>
                <Field label="Activity Type">
                  <SelectWithOther
                    value={details.what}
                    onChange={async (value) => {
                      setDetails({ ...details, what: value });
                      // Save custom option to project
                      if (value && !projectOptions.what.includes(value)) {
                        try {
                          const projectId = project.project_id || project.id;
                          await api.saveProjectOption(projectId, 'what', value);
                          setProjectOptions(prev => ({ ...prev, what: [...prev.what, value] }));
                        } catch (error) {
                          console.error('Failed to save option:', error);
                        }
                      }
                    }}
                    options={projectOptions.what.map(v => ({ value: v, label: v }))}
                    placeholder="Type custom value..."
                  />
                </Field>
                <Field label="Site">
                  <SelectWithOther
                    value={details.where}
                    onChange={async (value) => {
                      setDetails({ ...details, where: value });
                      // Save custom option to project
                      if (value && !projectOptions.where.includes(value)) {
                        try {
                          const projectId = project.project_id || project.id;
                          await api.saveProjectOption(projectId, 'where', value);
                          setProjectOptions(prev => ({ ...prev, where: [...prev.where, value] }));
                        } catch (error) {
                          console.error('Failed to save option:', error);
                        }
                      }
                    }}
                    options={projectOptions.where.map(v => ({ value: v, label: v }))}
                    placeholder="Type custom value..."
                  />
                </Field>
                <Field label="Operational Timing">
                  <SelectWithOther
                    value={details.when}
                    onChange={async (value) => {
                      setDetails({ ...details, when: value });
                      // Save custom option to project
                      if (value && !projectOptions.when.includes(value)) {
                        try {
                          const projectId = project.project_id || project.id;
                          await api.saveProjectOption(projectId, 'when', value);
                          setProjectOptions(prev => ({ ...prev, when: [...prev.when, value] }));
                        } catch (error) {
                          console.error('Failed to save option:', error);
                        }
                      }
                    }}
                    options={projectOptions.when.map(v => ({ value: v, label: v }))}
                    placeholder="Type custom value..."
                  />
                </Field>
                <Field label="Purpose">
                  <SelectWithOther
                    value={details.why}
                    onChange={async (value) => {
                      setDetails({ ...details, why: value });
                      // Save custom option to project
                      if (value && !projectOptions.why.includes(value)) {
                        try {
                          const projectId = project.project_id || project.id;
                          await api.saveProjectOption(projectId, 'why', value);
                          setProjectOptions(prev => ({ ...prev, why: [...prev.why, value] }));
                        } catch (error) {
                          console.error('Failed to save option:', error);
                        }
                      }
                    }}
                    options={projectOptions.why.map(v => ({ value: v, label: v }))}
                    placeholder="Type custom value..."
                  />
                </Field>
              </div>

              <Field label="Description">
                <textarea
                  value={details.description}
                  onChange={(e) => setDetails({ ...details, description: e.target.value })}
                  placeholder="Describe the purpose of this upload..."
                  className="w-full rounded-xl border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2 text-sm min-h-[60px]"
                />
              </Field>

              {/* File Upload Section - Moved to bottom */}
              <Field label="Select Configuration Files">
                <div
                  onDragEnter={handleDrag}
                  onDragLeave={handleDrag}
                  onDragOver={handleDrag}
                  onDrop={handleDrop}
                  className={`border-2 border-dashed rounded-xl p-6 text-center transition-colors ${dragActive
                    ? 'border-slate-400/80 dark:border-slate-500/80 bg-slate-100/80 dark:bg-white/10'
                    : 'border-gray-300 dark:border-gray-700 hover:border-gray-400 dark:hover:border-gray-600'
                    }`}
                >
                  <input
                    type="file"
                    multiple
                    accept=".txt,.cfg,.conf,.log"
                    onChange={handleFileChange}
                    className="hidden"
                    id="file-upload-input-config"
                  />
                  <label
                    htmlFor="file-upload-input-config"
                    className="cursor-pointer block"
                  >
                    <div className="text-4xl mb-2">📁</div>
                    <div className="text-sm font-medium mb-1">
                      Drag & drop files here, or click to select
                    </div>
                    <div className="text-xs text-gray-500">
                      You can select multiple files (.txt, .cfg, .conf)
                    </div>
                  </label>
                </div>

                {files.length > 0 && (
                  <div className="mt-4">
                    <div className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Selected {files.length} file(s):
                    </div>
                    <div className="border border-slate-300 dark:border-gray-700 rounded-lg p-2 max-h-48 overflow-y-auto">
                      <div className="space-y-2">
                        {files.map((file, idx) => (
                          <div key={idx} className="flex items-center justify-between rounded-lg border border-slate-300 dark:border-gray-700 p-2 text-sm bg-gray-50 dark:bg-gray-800/50">
                            <div className="flex-1 min-w-0">
                              <div className="font-medium truncate">{file.name}</div>
                              <div className="text-xs text-gray-500">{(file.size / 1024).toFixed(1)} KB</div>
                            </div>
                            <button
                              type="button"
                              onClick={() => removeFile(idx)}
                              className="ml-2 text-rose-500 hover:text-rose-700 text-sm flex-shrink-0"
                            >
                              ✕
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </Field>

              <div className="flex gap-2 justify-end sticky bottom-0 bg-white dark:bg-gray-900 pt-3 pb-1 border-t border-slate-300 dark:border-gray-700 mt-2">
                <Button variant="secondary" onClick={onClose}>Cancel</Button>
                <Button type="submit" disabled={files.length === 0 || isUploading}>
                  {isUploading ? 'Uploading...' : 'Upload Files'}
                </Button>
              </div>
            </form>
          </div>
        </Card>
      </div>
    </div>
  );
};

const UploadDocumentForm = ({ project, authedUser, onClose, onUpload, folderStructure, defaultFolderId = null }) => {
  const [files, setFiles] = useState([]);
  const [selectedFolderId, setSelectedFolderId] = useState(defaultFolderId || '');
  const [details, setDetails] = useState({
    who: authedUser?.username || '',
    what: '',
    where: '',
    when: '',
    why: '',
    description: ''
  });
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const [projectOptions, setProjectOptions] = useState({ what: [], where: [], when: [], why: [] });

  // Load project-specific options
  useEffect(() => {
    const loadProjectOptions = async () => {
      if (!project?.project_id && !project?.id) return;
      try {
        const projectId = project.project_id || project.id;
        const options = await api.getProjectOptions(projectId);
        setProjectOptions(options || { what: [], where: [], when: [], why: [] });
      } catch (error) {
        console.error('Failed to load project options:', error);
      }
    };
    loadProjectOptions();
  }, [project]);

  // Get all folders for selection (exclude Config folder and root, but include Other)
  const getAllFolders = (node, path = []) => {
    let folders = [];

    // Skip root and Config folders
    if (node.id === "root" || node.id === "Config") {
      // Process children with empty path for root, or skip Config entirely
      if (node.id === "root" && node.folders) {
        node.folders.forEach(folder => {
          if (folder.id !== "Config") {
            // Include Other folder and custom folders
            folders = folders.concat(getAllFolders(folder, []));
          }
        });
      }
      return folders;
    }

    // Build path for current folder
    const currentPath = path.length > 0 ? [...path, node.name] : [node.name];

    // Add current folder (including Other folder)
    folders.push({ id: node.id, name: node.name, path: currentPath });

    // Process child folders (exclude Config, but include Other and custom folders)
    if (node.folders) {
      node.folders.forEach(folder => {
        if (folder.id !== "Config") {
          folders = folders.concat(getAllFolders(folder, currentPath));
        }
      });
    }

    return folders;
  };

  const folderOptions = folderStructure ? [
    ...getAllFolders(folderStructure).map(f => ({
      value: f.id,
      label: f.path.join(' / ')
    }))
  ] : [];

  const handleFileChange = (e) => {
    const selectedFiles = Array.from(e.target.files || []);
    setFiles(prev => [...prev, ...selectedFiles]);
    setError(null);
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const droppedFiles = Array.from(e.dataTransfer.files);
      setFiles(prev => [...prev, ...droppedFiles]);
      setError(null);
    }
  };

  const removeFile = (index) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (files.length === 0) return;

    setIsUploading(true);
    setError(null);

    try {
      const projectId = project.project_id || project.id;
      const folderIdToUse = selectedFolderId || null;

      const metadata = {
        who: details.who,
        what: details.what,
        where: details.where || null,
        when: details.when || null,
        why: details.why || null,
        description: details.description || null
      };

      await api.uploadDocuments(projectId, files, metadata, folderIdToUse);

      const uploadRecord = createUploadRecord('document', files, authedUser.username, projectId, {
        ...details,
        folderId: folderIdToUse
      });

      onUpload(uploadRecord, folderIdToUse);
      onClose();
    } catch (error) {
      console.error('Upload failed:', error);
      setError(formatError(error) || 'Upload failed. Please try again.');
    } finally {
      setIsUploading(false);
    }
  };

  // No preset options - only project-specific saved options

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 overflow-y-auto">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="relative z-10 w-full max-w-5xl max-h-[90vh] my-4">
        <Card title="Upload Documents" actions={<Button variant="secondary" onClick={onClose}>Close</Button>}>
          <div className="max-h-[calc(90vh-120px)] overflow-y-auto pr-2">
            <form onSubmit={handleSubmit} className="grid gap-3">
              {error && (
                <div className="rounded-xl border border-rose-300 dark:border-rose-700 bg-rose-50 dark:bg-rose-900/20 p-3 text-sm text-rose-700 dark:text-rose-400">
                  {safeDisplay(error)}
                </div>
              )}

              <Field label="Upload to folder">
                <Select
                  value={selectedFolderId}
                  onChange={setSelectedFolderId}
                  options={[
                    { value: "", label: "Root (no folder)" },
                    ...folderOptions
                  ]}
                  placeholder="Select folder..."
                />
              </Field>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Field label="Responsible User">
                  <Input
                    value={details.who}
                    disabled
                    className="bg-gray-100 dark:bg-gray-700"
                  />
                </Field>
                <Field label="Activity Type">
                  <SelectWithOther
                    value={details.what}
                    onChange={async (value) => {
                      setDetails({ ...details, what: value });
                      // Save custom option to project
                      if (value && !projectOptions.what.includes(value)) {
                        try {
                          const projectId = project.project_id || project.id;
                          await api.saveProjectOption(projectId, 'what', value);
                          setProjectOptions(prev => ({ ...prev, what: [...prev.what, value] }));
                        } catch (error) {
                          console.error('Failed to save option:', error);
                        }
                      }
                    }}
                    options={projectOptions.what.map(v => ({ value: v, label: v }))}
                    placeholder="Type custom value..."
                  />
                </Field>
                <Field label="Site">
                  <SelectWithOther
                    value={details.where}
                    onChange={async (value) => {
                      setDetails({ ...details, where: value });
                      // Save custom option to project
                      if (value && !projectOptions.where.includes(value)) {
                        try {
                          const projectId = project.project_id || project.id;
                          await api.saveProjectOption(projectId, 'where', value);
                          setProjectOptions(prev => ({ ...prev, where: [...prev.where, value] }));
                        } catch (error) {
                          console.error('Failed to save option:', error);
                        }
                      }
                    }}
                    options={projectOptions.where.map(v => ({ value: v, label: v }))}
                    placeholder="Type custom value..."
                  />
                </Field>
                <Field label="Operational Timing">
                  <SelectWithOther
                    value={details.when}
                    onChange={async (value) => {
                      setDetails({ ...details, when: value });
                      // Save custom option to project
                      if (value && !projectOptions.when.includes(value)) {
                        try {
                          const projectId = project.project_id || project.id;
                          await api.saveProjectOption(projectId, 'when', value);
                          setProjectOptions(prev => ({ ...prev, when: [...prev.when, value] }));
                        } catch (error) {
                          console.error('Failed to save option:', error);
                        }
                      }
                    }}
                    options={projectOptions.when.map(v => ({ value: v, label: v }))}
                    placeholder="Type custom value..."
                  />
                </Field>
              </div>

              <Field label="Purpose">
                <SelectWithOther
                  value={details.why}
                  onChange={async (value) => {
                    setDetails({ ...details, why: value });
                    // Save custom option to project
                    if (value && !projectOptions.why.includes(value)) {
                      try {
                        const projectId = project.project_id || project.id;
                        await api.saveProjectOption(projectId, 'why', value);
                        setProjectOptions(prev => ({ ...prev, why: [...prev.why, value] }));
                      } catch (error) {
                        console.error('Failed to save option:', error);
                      }
                    }
                  }}
                  options={projectOptions.why.map(v => ({ value: v, label: v }))}
                  placeholder="Type custom value..."
                />
              </Field>

              <Field label="Description">
                <textarea
                  value={details.description}
                  onChange={(e) => setDetails({ ...details, description: e.target.value })}
                  placeholder="Describe the purpose of this upload..."
                  className="w-full rounded-xl border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2 text-sm min-h-[80px]"
                />
              </Field>

              {/* File Upload Section - Moved to bottom */}
              <Field label="Select Document Files">
                <div
                  onDragEnter={handleDrag}
                  onDragLeave={handleDrag}
                  onDragOver={handleDrag}
                  onDrop={handleDrop}
                  className={`border-2 border-dashed rounded-xl p-6 text-center transition-colors ${dragActive
                    ? 'border-slate-400/80 dark:border-slate-500/80 bg-slate-100/80 dark:bg-white/10'
                    : 'border-gray-300 dark:border-gray-700 hover:border-gray-400 dark:hover:border-gray-600'
                    }`}
                >
                  <input
                    type="file"
                    multiple
                    accept="*/*"
                    onChange={handleFileChange}
                    className="hidden"
                    id="file-upload-input-doc"
                  />
                  <label
                    htmlFor="file-upload-input-doc"
                    className="cursor-pointer block"
                  >
                    <div className="text-4xl mb-2">📁</div>
                    <div className="text-sm font-medium mb-1">
                      Drag & drop files here, or click to select
                    </div>
                    <div className="text-xs text-gray-500">
                      You can select multiple files
                    </div>
                  </label>
                </div>

                {files.length > 0 && (
                  <div className="mt-4">
                    <div className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Selected {files.length} file(s):
                    </div>
                    <div className="border border-slate-300 dark:border-gray-700 rounded-lg p-2 max-h-48 overflow-y-auto">
                      <div className="space-y-2">
                        {files.map((file, idx) => (
                          <div key={idx} className="flex items-center justify-between rounded-lg border border-slate-300 dark:border-gray-700 p-2 text-sm bg-gray-50 dark:bg-gray-800/50">
                            <div className="flex-1 min-w-0">
                              <div className="font-medium truncate">{file.name}</div>
                              <div className="text-xs text-gray-500">{(file.size / 1024).toFixed(1)} KB</div>
                            </div>
                            <button
                              type="button"
                              onClick={() => removeFile(idx)}
                              className="ml-2 text-rose-500 hover:text-rose-700 text-sm flex-shrink-0"
                            >
                              ✕
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </Field>

              <div className="flex gap-2 justify-end sticky bottom-0 bg-white dark:bg-gray-900 pt-3 pb-1 border-t border-slate-300 dark:border-gray-700 mt-2">
                <Button variant="secondary" onClick={onClose}>Cancel</Button>
                <Button type="submit" disabled={files.length === 0 || isUploading}>
                  {isUploading ? 'Uploading...' : 'Upload Files'}
                </Button>
              </div>
            </form>
          </div>
        </Card>
      </div>
    </div>
  );
};

/* ========= DOCUMENTS (file tree + preview) ========= */
/* ========= ANALYSIS PAGE ========= */
const AnalysisPage = ({ project, authedUser, onChangeTab, showConfirmModal }) => {
  const [analyses, setAnalyses] = useState([]);
  const [devices, setDevices] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedAnalysis, setSelectedAnalysis] = useState(null);
  const [showCreate, setShowCreate] = useState(false);
  const [filters, setFilters] = useState({
    device_name: null,
    status: null,
    analysis_type: null
  });
  const [performanceMetrics, setPerformanceMetrics] = useState([]);
  const [showMetrics, setShowMetrics] = useState(false);

  useEffect(() => {
    loadAnalyses();
    loadDevices();
    loadPerformanceMetrics();
  }, [project?.project_id, filters]);

  const loadDevices = async () => {
    try {
      const summary = await api.getConfigSummary(project.project_id);
      const rows = summary.summaryRows || (Array.isArray(summary) ? summary : []);
      const deviceNames = rows.map(d => d.device).filter(Boolean);
      setDevices([...new Set(deviceNames)]);
    } catch (e) {
      console.error("Failed to load devices:", e);
    }
  };

  const loadAnalyses = async () => {
    setLoading(true);
    try {
      const data = await api.getAnalyses(project.project_id, filters);
      setAnalyses(data);
    } catch (e) {
      console.error("Failed to load analyses:", e);
      alert("Failed to load analyses: " + formatError(e));
    } finally {
      setLoading(false);
    }
  };

  const loadPerformanceMetrics = async () => {
    try {
      const metrics = await api.getPerformanceMetrics(project.project_id, filters.device_name, 50);
      setPerformanceMetrics(metrics);
    } catch (e) {
      console.error("Failed to load performance metrics:", e);
    }
  };

  const handleCreateAnalysis = async (deviceName, analysisType, customPrompt, includeOriginal) => {
    setLoading(true);
    try {
      const newAnalysis = await api.createAnalysis(
        project.project_id,
        deviceName,
        analysisType,
        customPrompt,
        includeOriginal
      );
      await loadAnalyses();
      setSelectedAnalysis(newAnalysis);
      setShowCreate(false);
    } catch (e) {
      alert("Failed to create analysis: " + formatError(e));
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyAnalysis = async (analysisId, verifiedContent, comments, status) => {
    setLoading(true);
    try {
      const updated = await api.verifyAnalysis(
        project.project_id,
        analysisId,
        verifiedContent,
        comments,
        status
      );
      await loadAnalyses();
      setSelectedAnalysis(updated);
    } catch (e) {
      alert("Failed to verify analysis: " + formatError(e));
    } finally {
      setLoading(false);
    }
  };

  const analysisTypes = [
    { value: "security_audit", label: "Security Audit" },
    { value: "performance_review", label: "Performance Review" },
    { value: "configuration_compliance", label: "Configuration Compliance" },
    { value: "network_topology", label: "Network Topology" },
    { value: "best_practices", label: "Best Practices" },
    { value: "custom", label: "Custom Analysis" }
  ];

  const statusColors = {
    pending_review: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-100",
    verified: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-100",
    rejected: "bg-rose-100 text-rose-800 dark:bg-rose-900 dark:text-rose-100"
  };


  return (
    <div className="grid gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">AI Analysis</h2>
          <div className="text-sm text-gray-500 dark:text-gray-400">
            LLM-powered network configuration analysis with Human-in-the-Loop workflow
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => setShowMetrics(!showMetrics)}>
            {showMetrics ? "Hide" : "Show"} Metrics
          </Button>
          <Button onClick={() => setShowCreate(true)} disabled={loading || devices.length === 0}>
            + New Analysis
          </Button>
        </div>
      </div>

      {/* Filters */}
      <Card>
        <div className="grid gap-3 md:grid-cols-3">
          <Field label="Device">
            <Select
              options={[{ value: null, label: "All Devices" }, ...devices.map(d => ({ value: d, label: d }))]}
              value={filters.device_name || null}
              onChange={(val) => setFilters({ ...filters, device_name: val || null })}
            />
          </Field>
          <Field label="Status">
            <Select
              options={[
                { value: null, label: "All Status" },
                { value: "pending_review", label: "Pending Review" },
                { value: "verified", label: "Verified" },
                { value: "rejected", label: "Rejected" }
              ]}
              value={filters.status || null}
              onChange={(val) => setFilters({ ...filters, status: val || null })}
            />
          </Field>
          <Field label="Analysis Type">
            <Select
              options={[{ value: null, label: "All Types" }, ...analysisTypes]}
              value={filters.analysis_type || null}
              onChange={(val) => setFilters({ ...filters, analysis_type: val || null })}
            />
          </Field>
        </div>
      </Card>

      {/* Performance Metrics Dashboard */}
      {showMetrics && (
        <Card title="Performance Metrics">
          <PerformanceMetricsView metrics={performanceMetrics} />
        </Card>
      )}

      {/* Create Analysis Modal */}
      {showCreate && (
        <CreateAnalysisModal
          devices={devices}
          analysisTypes={analysisTypes}
          onCreate={handleCreateAnalysis}
          onClose={() => setShowCreate(false)}
          loading={loading}
        />
      )}

      {/* Analysis List */}
      {loading && analyses.length === 0 ? (
        <div className="text-center py-12 text-gray-500">Loading analyses...</div>
      ) : analyses.length === 0 ? (
        <Card>
          <div className="text-center py-12 text-gray-500">
            <p className="mb-4">No analyses found</p>
            <Button onClick={() => setShowCreate(true)}>Create First Analysis</Button>
          </div>
        </Card>
      ) : (
        <div className="grid gap-4">
          {analyses.map((analysis) => (
            <Card
              key={analysis.analysis_id}
              className="hover:shadow-lg transition-all cursor-pointer"
              onClick={() => setSelectedAnalysis(analysis)}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <h3 className="font-semibold">{safeDisplay(analysis?.device_name)}</h3>
                    <Badge className={statusColors[analysis.status]}>
                      {safeDisplay(String(analysis?.status || "").replace("_", " "))}
                    </Badge>
                    <Badge>{safeDisplay(String(analysis?.analysis_type || "").replace("_", " "))}</Badge>
                  </div>
                  <div className="text-sm text-gray-600 dark:text-gray-400 mb-2">
                    {typeof analysis?.ai_draft_text === "string" ? analysis.ai_draft_text.substring(0, 200) + "..." : safeDisplay(analysis?.ai_draft_text)}
                  </div>
                  <div className="flex items-center gap-4 text-xs text-gray-500">
                    <span>Created: {formatDateTime(analysis.created_at)}</span>
                    <span>By: {safeDisplay(analysis?.created_by)}</span>
                    {analysis?.llm_metrics && (
                      <span>
                        {safeDisplay(analysis.llm_metrics.inference_time_ms != null ? Number(analysis.llm_metrics.inference_time_ms).toFixed(0) : null)}ms · {safeDisplay(analysis.llm_metrics?.model_name)}
                      </span>
                    )}
                    {analysis?.accuracy_metrics && (
                      <span className="font-semibold">
                        Accuracy: {safeDisplay(analysis.accuracy_metrics?.accuracy_score)}%
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Analysis Detail Modal */}
      {selectedAnalysis && (
        <AnalysisDetailModal
          analysis={selectedAnalysis}
          authedUser={authedUser}
          onVerify={handleVerifyAnalysis}
          onClose={() => setSelectedAnalysis(null)}
          loading={loading}
          showConfirmModal={showConfirmModal}
        />
      )}
    </div>
  );
};

/* ========= ANALYSIS COMPONENTS ========= */
const CreateAnalysisModal = ({ devices, analysisTypes, onCreate, onClose, loading }) => {
  const [deviceName, setDeviceName] = useState("");
  const [analysisType, setAnalysisType] = useState("security_audit");
  const [customPrompt, setCustomPrompt] = useState("");
  const [includeOriginal, setIncludeOriginal] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!deviceName) {
      alert("Please select a device");
      return;
    }
    onCreate(
      deviceName,
      analysisType,
      analysisType === "custom" ? customPrompt : null,
      includeOriginal
    );
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <Card className="w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">Create New Analysis</h3>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-700">✕</button>
        </div>
        <form onSubmit={handleSubmit} className="grid gap-4">
          <Field label="Device">
            <Select
              options={devices.map(d => ({ value: d, label: d }))}
              value={deviceName}
              onChange={setDeviceName}
            />
          </Field>
          <Field label="Analysis Type">
            <Select
              options={analysisTypes}
              value={analysisType}
              onChange={setAnalysisType}
            />
          </Field>
          {analysisType === "custom" && (
            <Field label="Custom Prompt">
              <textarea
                className="w-full rounded-xl border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                rows={4}
                value={customPrompt}
                onChange={(e) => setCustomPrompt(e.target.value)}
                placeholder="Enter your custom analysis prompt..."
              />
            </Field>
          )}
          <Field>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={includeOriginal}
                onChange={(e) => setIncludeOriginal(e.target.checked)}
                className="rounded border-gray-300"
              />
              <span className="text-sm">Include original configuration content (may increase processing time)</span>
            </label>
          </Field>
          <div className="flex gap-2 justify-end">
            <Button variant="secondary" onClick={onClose} disabled={loading}>Cancel</Button>
            <Button type="submit" disabled={loading || !deviceName}>
              {loading ? "Creating..." : "Create Analysis"}
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
};

const AnalysisDetailModal = ({ analysis, authedUser, onVerify, onClose, loading, showConfirmModal }) => {
  const [viewMode, setViewMode] = useState("draft"); // "draft" or "verified"
  const [isEditing, setIsEditing] = useState(false);
  const [editedContent, setEditedContent] = useState(null);
  const [comments, setComments] = useState("");
  const [showDiff, setShowDiff] = useState(false);

  const statusColors = {
    pending_review: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-100",
    verified: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-100",
    rejected: "bg-rose-100 text-rose-800 dark:bg-rose-900 dark:text-rose-100"
  };

  useEffect(() => {
    if (analysis.verified_version) {
      setEditedContent(analysis.verified_version);
    } else {
      setEditedContent(analysis.ai_draft);
    }
  }, [analysis]);

  const handleSave = async () => {
    if (!editedContent) return;
    await onVerify(
      analysis.analysis_id,
      editedContent,
      comments,
      "verified"
    );
    setIsEditing(false);
  };

  const handleReject = () => {
    showConfirmModal({
      title: "Reject Analysis",
      message: "Are you sure you want to reject this analysis?",
      confirmText: "Reject",
      cancelText: "Cancel",
      variant: "danger",
      onConfirm: async () => {
        await onVerify(
          analysis.analysis_id,
          analysis.ai_draft,
          comments || "Rejected by reviewer",
          "rejected"
        );
      }
    });
  };

  const currentContent = viewMode === "verified" && analysis.verified_version
    ? analysis.verified_version
    : analysis.ai_draft;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <Card className="w-full max-w-6xl max-h-[90vh] overflow-hidden flex flex-col">
        <div className="flex items-center justify-between mb-4 border-b pb-4">
          <div>
            <h3 className="text-lg font-semibold">{safeDisplay(analysis?.device_name)} - {safeDisplay(String(analysis?.analysis_type || "").replace("_", " "))}</h3>
            <div className="flex items-center gap-2 mt-2">
              <Badge className={statusColors[analysis?.status]}>
                {safeDisplay(String(analysis?.status || "").replace("_", " "))}
              </Badge>
              {analysis?.accuracy_metrics && (
                <Badge className="bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-100">
                  Accuracy: {safeDisplay(analysis.accuracy_metrics?.accuracy_score)}%
                </Badge>
              )}
            </div>
          </div>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-700">✕</button>
        </div>

        <div className="flex-1 overflow-y-auto">
          {/* View Mode Toggle */}
          {analysis.verified_version && (
            <div className="flex gap-2 mb-4">
              <Button
                variant={viewMode === "draft" ? "primary" : "secondary"}
                onClick={() => setViewMode("draft")}
              >
                AI Draft
              </Button>
              <Button
                variant={viewMode === "verified" ? "primary" : "secondary"}
                onClick={() => setViewMode("verified")}
              >
                Verified Version
              </Button>
              {analysis.verified_version && (
                <Button
                  variant={showDiff ? "primary" : "secondary"}
                  onClick={() => setShowDiff(!showDiff)}
                >
                  {showDiff ? "Hide" : "Show"} Diff
                </Button>
              )}
            </div>
          )}

          {/* Diff View */}
          {showDiff && analysis.diff_summary && (
            <Card className="mb-4" title="Changes Summary">
              <DiffView diff={analysis.diff_summary} />
            </Card>
          )}

          {/* Content Display/Edit */}
          {isEditing ? (
            <div className="grid gap-4">
              <Field label="Analysis Content (JSON)">
                <textarea
                  className="w-full rounded-xl border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2 text-sm font-mono text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  rows={20}
                  value={JSON.stringify(editedContent, null, 2)}
                  onChange={(e) => {
                    try {
                      setEditedContent(JSON.parse(e.target.value));
                    } catch {
                      // Invalid JSON, keep as is
                    }
                  }}
                />
              </Field>
              <Field label="Comments">
                <textarea
                  className="w-full rounded-xl border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  rows={3}
                  value={comments}
                  onChange={(e) => setComments(e.target.value)}
                  placeholder="Add comments about your changes..."
                />
              </Field>
            </div>
          ) : (
            <div className="prose dark:prose-invert max-w-none">
              <pre className="bg-gray-50 dark:bg-gray-900 p-4 rounded-lg overflow-x-auto text-sm">
                {JSON.stringify(currentContent, null, 2)}
              </pre>
              {analysis.ai_draft_text && viewMode === "draft" && (
                <div className="mt-4 p-4 bg-slate-100/90 dark:bg-white/5 rounded-xl border border-slate-300 dark:border-slate-700/80">
                  <h4 className="font-semibold mb-2">Full AI Response:</h4>
                  <p className="whitespace-pre-wrap text-sm">{safeDisplay(analysis?.ai_draft_text)}</p>
                </div>
              )}
            </div>
          )}

          {/* Metrics */}
          {analysis.llm_metrics && (
            <Card className="mt-4" title="Performance Metrics">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <div className="text-gray-500">Inference Time</div>
                  <div className="font-semibold">{safeDisplay(analysis?.llm_metrics?.inference_time_ms != null ? Number(analysis.llm_metrics.inference_time_ms).toFixed(0) : null)}ms</div>
                </div>
                <div>
                  <div className="text-gray-500">Model</div>
                  <div className="font-semibold">{safeDisplay(analysis?.llm_metrics?.model_name)}</div>
                </div>
                <div>
                  <div className="text-gray-500">Prompt Tokens</div>
                  <div className="font-semibold">{analysis.llm_metrics.token_usage?.prompt_tokens || 0}</div>
                </div>
                <div>
                  <div className="text-gray-500">Completion Tokens</div>
                  <div className="font-semibold">{analysis.llm_metrics.token_usage?.completion_tokens || 0}</div>
                </div>
              </div>
            </Card>
          )}
        </div>

        {/* Actions */}
        {analysis.status === "pending_review" && (
          <div className="flex gap-2 justify-end mt-4 border-t pt-4">
            <Button variant="secondary" onClick={onClose}>Close</Button>
            <Button variant="danger" onClick={handleReject} disabled={loading}>
              Reject
            </Button>
            {isEditing ? (
              <>
                <Button variant="secondary" onClick={() => setIsEditing(false)}>Cancel Edit</Button>
                <Button onClick={handleSave} disabled={loading}>
                  {loading ? "Saving..." : "Save & Verify"}
                </Button>
              </>
            ) : (
              <Button onClick={() => setIsEditing(true)}>
                Edit & Verify
              </Button>
            )}
          </div>
        )}
      </Card>
    </div>
  );
};

const DiffView = ({ diff }) => {
  if (!diff) return null;

  return (
    <div className="grid gap-4">
      <div className="flex items-center gap-4">
        <div>
          <span className="text-sm text-gray-500">Total Changes:</span>
          <span className="ml-2 font-semibold">{diff.total_changes || 0}</span>
        </div>
        <div>
          <span className="text-sm text-gray-500">Accuracy Score:</span>
          <span className="ml-2 font-semibold">{diff.accuracy_score || 0}%</span>
        </div>
      </div>

      {diff.changes_by_type && Object.keys(diff.changes_by_type).length > 0 && (
        <div>
          <h4 className="font-semibold mb-2">Changes by Type:</h4>
          <div className="grid gap-2">
            {Object.entries(diff.changes_by_type).map(([type, changes]) => (
              <div key={type} className="p-2 bg-gray-50 dark:bg-gray-800 rounded">
                <div className="font-medium capitalize">{type}: {changes.length}</div>
                <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                  {changes.slice(0, 5).map((change, idx) => (
                    <div key={idx} className="truncate">
                      {change.field}: {JSON.stringify(change.ai_value)} → {JSON.stringify(change.verified_value)}
                    </div>
                  ))}
                  {changes.length > 5 && <div>... and {changes.length - 5} more</div>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {diff.key_changes && diff.key_changes.length > 0 && (
        <div>
          <h4 className="font-semibold mb-2">Key Changes:</h4>
          <div className="space-y-2">
            {diff.key_changes.map((change, idx) => (
              <div key={idx} className="p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded border border-yellow-200 dark:border-yellow-800">
                <div className="font-medium text-sm">{change.field}</div>
                <div className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                  <div>AI: {JSON.stringify(change.ai_value)}</div>
                  <div>Human: {JSON.stringify(change.verified_value)}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

const PerformanceMetricsView = ({ metrics }) => {
  if (!metrics || metrics.length === 0) {
    return <div className="text-center py-8 text-gray-500">No performance metrics available</div>;
  }

  const avgInferenceTime = metrics.reduce((sum, m) => sum + (m.inference_time_ms || 0), 0) / metrics.length;
  const avgAccuracy = metrics
    .filter(m => m.accuracy_score !== null)
    .reduce((sum, m) => sum + (m.accuracy_score || 0), 0) / metrics.filter(m => m.accuracy_score !== null).length || 0;
  const totalTokens = metrics.reduce((sum, m) => sum + ((m.token_usage?.total_tokens || 0)), 0);

  return (
    <div className="grid gap-4">
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <div className="text-sm text-gray-500">Avg Inference Time</div>
          <div className="text-2xl font-semibold">{avgInferenceTime.toFixed(0)}ms</div>
        </Card>
        <Card>
          <div className="text-sm text-gray-500">Avg Accuracy</div>
          <div className="text-2xl font-semibold">{avgAccuracy.toFixed(1)}%</div>
        </Card>
        <Card>
          <div className="text-sm text-gray-500">Total Requests</div>
          <div className="text-2xl font-semibold">{metrics.length}</div>
        </Card>
        <Card>
          <div className="text-sm text-gray-500">Total Tokens</div>
          <div className="text-2xl font-semibold">{totalTokens.toLocaleString()}</div>
        </Card>
      </div>

      <div className="max-h-96 overflow-y-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 dark:bg-gray-800 sticky top-0">
            <tr>
              <th className="px-4 py-2 text-left">Device</th>
              <th className="px-4 py-2 text-left">Time (ms)</th>
              <th className="px-4 py-2 text-left">Tokens</th>
              <th className="px-4 py-2 text-left">Accuracy</th>
              <th className="px-4 py-2 text-left">Timestamp</th>
            </tr>
          </thead>
          <tbody>
            {metrics.map((m) => (
              <tr key={m.log_id} className="border-b border-slate-300 dark:border-gray-700">
                <td className="px-4 py-2">{m.device_name}</td>
                <td className="px-4 py-2">{m.inference_time_ms?.toFixed(0)}</td>
                <td className="px-4 py-2">{m.token_usage?.total_tokens || 0}</td>
                <td className="px-4 py-2">
                  {m.accuracy_score !== null ? `${m.accuracy_score.toFixed(1)}%` : "—"}
                </td>
                <td className="px-4 py-2">{formatDateTime(m.timestamp)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

/* ========= HISTORY PAGE ========= */
const ROWS_PER_PAGE = 15;

// Filter dropdown component for History table headers
const HistoryFilterDropdown = ({ uniqueValues, filterValue, onFilterChange, onClose, position = "left" }) => {
  const dropdownRef = useRef(null);
  const [searchTerm, setSearchTerm] = useState("");

  const filteredValues = useMemo(() => {
    if (!searchTerm) return uniqueValues;
    const term = searchTerm.toLowerCase();
    return uniqueValues.filter(v => v.toLowerCase().includes(term));
  }, [uniqueValues, searchTerm]);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        onClose();
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [onClose]);

  const positionClass = position === "right" ? "right-0" : "left-0";

  return (
    <div
      ref={dropdownRef}
      className={`absolute top-full ${positionClass} mt-1 z-50 bg-slate-900 border border-slate-700 rounded-lg shadow-xl min-w-[200px] max-w-[280px]`}
      onClick={(e) => e.stopPropagation()}
    >
      {/* Search input */}
      <div className="p-2 border-b border-slate-700">
        <div className="relative">
          <svg className="absolute left-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            type="text"
            placeholder="Search..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-7 pr-2 py-1.5 text-xs rounded bg-slate-800 border border-slate-600 text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-sky-500 focus:border-sky-500"
            autoFocus
          />
        </div>
      </div>

      {/* Options list */}
      <div className="max-h-[200px] overflow-y-auto">
        <button
          onClick={() => { onFilterChange(null); onClose(); }}
          className={`w-full px-3 py-2 text-left text-xs hover:bg-slate-800 flex items-center gap-2 transition-colors ${!filterValue ? 'text-sky-400 bg-slate-800/50' : 'text-slate-300'}`}
        >
          <span className="w-4 flex justify-center">{!filterValue && "✓"}</span>
          <span>All</span>
        </button>
        {filteredValues.map((val, i) => (
          <button
            key={i}
            onClick={() => { onFilterChange(val); onClose(); }}
            className={`w-full px-3 py-2 text-left text-xs hover:bg-slate-800 flex items-center gap-2 truncate transition-colors ${filterValue === val ? 'text-sky-400 bg-slate-800/50' : 'text-slate-300'}`}
          >
            <span className="w-4 flex justify-center">{filterValue === val && "✓"}</span>
            <span className="truncate">{val}</span>
          </button>
        ))}
        {filteredValues.length === 0 && (
          <div className="px-3 py-3 text-xs text-slate-500 text-center">No matches</div>
        )}
      </div>
    </div>
  );
};

const HistoryPage = ({ project, can, authedUser }) => {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchDoc, setSearchDoc] = useState("");
  const [versions, setVersions] = useState([]);
  const [showVersions, setShowVersions] = useState(false);
  const [versionDocument, setVersionDocument] = useState(null);
  const [showDescriptionModal, setShowDescriptionModal] = useState(false);
  const [descriptionContent, setDescriptionContent] = useState({ text: "", filename: "" });
  const [currentPage, setCurrentPage] = useState(1);
  const isOpeningVersions = useRef(false);

  // Column filters state
  const [columnFilters, setColumnFilters] = useState({});
  const [openFilterColumn, setOpenFilterColumn] = useState(null);

  // Sort state
  const [sortConfig, setSortConfig] = useState({ key: 'time', direction: 'desc' });

  // Load documents from API
  useEffect(() => {
    const loadDocuments = async () => {
      if (!project?.project_id && !project?.id) {
        setLoading(false);
        return;
      }
      setLoading(true);
      try {
        const projectId = project.project_id || project.id;
        const docs = await api.getDocuments(projectId);
        setDocuments(Array.isArray(docs) ? docs : []);
      } catch (error) {
        console.error('Failed to load documents:', error);
        setDocuments([]);
      } finally {
        setLoading(false);
      }
    };
    loadDocuments();
  }, [project]);

  // Load versions for selected document
  const loadVersions = async (documentId, documentInfo = null) => {
    try {
      isOpeningVersions.current = true;
      setVersions([]);
      const docInfo = documentInfo || null;
      if (!docInfo) {
        console.error('No document info provided for loadVersions');
        isOpeningVersions.current = false;
        return;
      }
      setVersionDocument(docInfo);
      setShowVersions(true);

      await new Promise(resolve => setTimeout(resolve, 50));

      const projectId = project.project_id || project.id;
      const versionData = await api.getDocumentVersions(projectId, documentId);

      if (versionData && versionData.versions && Array.isArray(versionData.versions)) {
        setVersions(versionData.versions);
        if (versionData.filename) {
          setVersionDocument(prev => ({
            ...(prev || docInfo),
            filename: versionData.filename
          }));
        }
      } else {
        setVersions([]);
      }

      setTimeout(() => {
        isOpeningVersions.current = false;
      }, 200);
    } catch (error) {
      console.error('Failed to load versions:', error);
      setVersions([]);
      isOpeningVersions.current = false;
      alert('Failed to load version history: ' + formatError(error));
    }
  };

  if (!project) {
    return (
      <div className="text-sm text-rose-400">Project not found</div>
    );
  }

  if (!Array.isArray(documents)) {
    return (
      <div className="text-center py-8 text-gray-500">No documents found</div>
    );
  }

  // Show ALL files (including config files) - no filtering
  const allFiles = documents;

  // Define columns for filtering and sorting
  const historyColumns = [
    { key: 'time', header: 'Time', getValue: (d) => formatDateTime(d.created_at), getSortValue: (d) => new Date(d.created_at).getTime() },
    { key: 'name', header: 'Name', getValue: (d) => d.filename, getSortValue: (d) => (d.filename || "").toLowerCase() },
    { key: 'who', header: 'Responsible User', getValue: (d) => d.metadata?.who || d.uploader, getSortValue: (d) => (d.metadata?.who || d.uploader || "").toLowerCase() },
    { key: 'what', header: 'Activity Type', getValue: (d) => d.metadata?.what || "—", getSortValue: (d) => (d.metadata?.what || "").toLowerCase() },
    { key: 'where', header: 'Site', getValue: (d) => d.metadata?.where || "—", getSortValue: (d) => (d.metadata?.where || "").toLowerCase() },
    { key: 'when', header: 'Op. Timing', getValue: (d) => d.metadata?.when || "—", getSortValue: (d) => (d.metadata?.when || "").toLowerCase() },
    { key: 'why', header: 'Purpose', getValue: (d) => d.metadata?.why || "—", getSortValue: (d) => (d.metadata?.why || "").toLowerCase() },
    { key: 'version', header: 'Version', getValue: (d) => `v${d.version}${d.is_latest ? ' (Latest)' : ''}`, getSortValue: (d) => d.version || 0 },
  ];

  // Handle sort
  const handleSort = (key) => {
    setSortConfig(prev => ({
      key,
      direction: prev.key === key && prev.direction === 'asc' ? 'desc' : 'asc'
    }));
  };

  // Get unique values for each filterable column
  const getUniqueValues = (key) => {
    const col = historyColumns.find(c => c.key === key);
    if (!col) return [];
    const values = new Set();
    allFiles.forEach(doc => {
      const val = col.getValue(doc);
      if (val != null && val !== "" && val !== "—") {
        values.add(String(val));
      }
    });
    return Array.from(values).sort((a, b) => a.localeCompare(b, undefined, { numeric: true }));
  };

  const filteredDocs = useMemo(() => {
    // First filter
    let result = allFiles.filter(doc => {
      // Global search filter
      const matchSearch = !searchDoc.trim() ||
        [doc.filename,
        doc.metadata?.who || doc.uploader,
        doc.metadata?.what || "—",
        doc.metadata?.where || "—",
        doc.metadata?.description || "—"].some(v =>
          v.toLowerCase().includes(searchDoc.toLowerCase())
        );

      // Column filters
      const matchColumnFilters = Object.entries(columnFilters).every(([key, filterValue]) => {
        if (!filterValue) return true;
        const col = historyColumns.find(c => c.key === key);
        if (!col) return true;
        return String(col.getValue(doc)) === filterValue;
      });

      return matchSearch && matchColumnFilters;
    });

    // Then sort
    if (sortConfig.key) {
      const col = historyColumns.find(c => c.key === sortConfig.key);
      if (col && col.getSortValue) {
        result = [...result].sort((a, b) => {
          const aVal = col.getSortValue(a);
          const bVal = col.getSortValue(b);

          if (aVal < bVal) return sortConfig.direction === 'asc' ? -1 : 1;
          if (aVal > bVal) return sortConfig.direction === 'asc' ? 1 : -1;
          return 0;
        });
      }
    }

    return result;
  }, [allFiles, searchDoc, columnFilters, sortConfig]);

  const totalPages = Math.max(1, Math.ceil(filteredDocs.length / ROWS_PER_PAGE));
  const clampedPage = Math.min(Math.max(1, currentPage), totalPages);
  const paginatedDocs = filteredDocs.slice((clampedPage - 1) * ROWS_PER_PAGE, clampedPage * ROWS_PER_PAGE);

  useEffect(() => {
    if (currentPage > totalPages && totalPages >= 1) setCurrentPage(totalPages);
  }, [totalPages, currentPage]);

  const openDescription = (r) => {
    setDescriptionContent({
      text: r.metadata?.description || "—",
      filename: r.filename || "Unknown"
    });
    setShowDescriptionModal(true);
  };

  // Download all history as CSV
  const downloadHistoryCSV = async () => {
    try {
      const projectId = project.project_id || project.id;

      // Get all documents (without pagination and filters)
      const allDocs = await api.getDocuments(projectId, {}, { timeout: 60000 });

      if (!Array.isArray(allDocs) || allDocs.length === 0) {
        alert('No documents found to export');
        return;
      }

      // Create CSV headers mapping to History view columns
      const headers = [
        'Time',
        'Filename',
        'Responsible User',
        'Activity Type',
        'Site',
        'Op. Timing',
        'Purpose',
        'Version',
        'Description'
      ];

      // Helper to escape CSV values
      const csvEscape = (val) => {
        if (val == null) return '""';
        let str = String(val);
        // Clean up any newlines or carriage returns that might break CSV formatting
        str = str.replace(/\r?\n|\r/g, " ");
        return `"${str.replace(/"/g, '""')}"`;
      };

      // Create CSV data
      const csvData = [];

      for (const doc of allDocs) {
        // Get all versions for this document
        try {
          const versionData = await api.getDocumentVersions(projectId, doc.document_id);
          const docVersions = versionData?.versions || [];

          // Create rows for each version
          for (const ver of docVersions) {
            // Use metadata from the specific version if available, fallback to latest doc's metadata
            const meta = ver.metadata || doc.metadata || {};
            csvData.push([
              csvEscape(formatDateTime(ver.created_at || doc.created_at)),
              csvEscape(doc.filename),
              csvEscape(meta.who || ver.uploader || doc.uploader),
              csvEscape(meta.what || "—"),
              csvEscape(meta.where || "—"),
              csvEscape(meta.when || "—"),
              csvEscape(meta.why || "—"),
              csvEscape(`v${ver.version}${ver.is_latest ? ' (Latest)' : ''}`),
              csvEscape(meta.description || "—")
            ].join(','));
          }
        } catch (error) {
          console.error('Failed to get versions for document:', doc.document_id, error);
          // Fallback: Add at least the main document info if version fetch fails
          csvData.push([
            csvEscape(formatDateTime(doc.created_at)),
            csvEscape(doc.filename),
            csvEscape(doc.metadata?.who || doc.uploader),
            csvEscape(doc.metadata?.what || "—"),
            csvEscape(doc.metadata?.where || "—"),
            csvEscape(doc.metadata?.when || "—"),
            csvEscape(doc.metadata?.why || "—"),
            csvEscape(`v${doc.version}${doc.is_latest ? ' (Latest)' : ''}`),
            csvEscape(doc.metadata?.description || "—")
          ].join(','));
        }
      }

      // Combine headers and data
      const csvContent = [headers.join(','), ...csvData].join('\n');

      // Create download link
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      // Use Thai date for filename
      const thaiDate = formatFilenameDate();
      link.download = `history_${project.name || 'project'}_${thaiDate}.csv`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);

    } catch (error) {
      console.error('Failed to download history CSV:', error);
      alert('Failed to download history CSV: ' + (error.message || error));
    }
  };

  // Show at most 3 page number buttons; window slides with current page
  const getPageNumbers = () => {
    if (totalPages <= 3) {
      return Array.from({ length: totalPages }, (_, i) => i + 1);
    }
    let start = Math.max(1, clampedPage - 1);
    let end = Math.min(totalPages, start + 2);
    if (end - start + 1 < 3) start = Math.max(1, end - 2);
    return Array.from({ length: end - start + 1 }, (_, i) => start + i);
  };

  return (
    <div className="h-full flex flex-col min-h-0 overflow-hidden p-2">
      {/* Header with search box */}
      <div className="flex-shrink-0 flex items-center justify-between mb-3 px-1">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">History</h2>
        <div className="flex items-center gap-3">
          <button
            onClick={downloadHistoryCSV}
            className="px-3 py-1.5 text-sm rounded bg-green-600 hover:bg-green-700 text-white font-medium transition-colors"
            title="Download all history as CSV"
          >
            📊 CSV
          </button>
          <div className="relative">
            <input
              type="text"
              placeholder="Search (filename, user, description...)"
              value={searchDoc}
              onChange={(e) => setSearchDoc(e.target.value)}
              className="w-72 pl-8 pr-3 py-1.5 text-xs rounded-lg bg-white dark:bg-slate-800/80 border border-slate-300 dark:border-slate-600 text-slate-900 dark:text-slate-200 placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-sky-500 focus:border-sky-500"
            />
            <svg className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>
        </div>
      </div>

      {/* Active filters bar */}
      {Object.keys(columnFilters).length > 0 && (
        <div className="flex-shrink-0 flex items-center gap-2 px-1 py-1.5 mb-2 bg-sky-50 border border-sky-200 rounded-lg dark:bg-slate-800/30 dark:border-slate-700/50">
          <span className="text-xs text-sky-700 dark:text-slate-400 ml-1">Filters:</span>
          {Object.entries(columnFilters).map(([key, value]) => {
            const col = historyColumns.find(c => c.key === key);
            return (
              <span
                key={key}
                className="inline-flex items-center gap-1 px-2 py-0.5 text-xs bg-sky-100 text-sky-700 dark:bg-sky-800/50 dark:text-sky-300 rounded-full"
              >
                <span className="font-medium">{col?.header || key}:</span>
                <span className="max-w-[100px] truncate">{value}</span>
                <button
                  onClick={() => setColumnFilters(prev => {
                    const next = { ...prev };
                    delete next[key];
                    return next;
                  })}
                  className="ml-0.5 hover:text-sky-100"
                >
                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </span>
            );
          })}
          <button
            onClick={() => setColumnFilters({})}
            className="ml-auto text-xs text-sky-700 hover:text-sky-900 dark:text-sky-400 dark:hover:text-sky-200 font-medium mr-1"
          >
            Clear all
          </button>
        </div>
      )}

      <div className="flex-1 min-h-0 flex flex-col overflow-hidden rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900/50">
        {loading ? (
          <div className="flex-1 flex items-center justify-center text-gray-500 dark:text-gray-400">
            <div className="text-center">
              <div className="text-lg mb-2">Loading documents...</div>
            </div>
          </div>
        ) : (
          <div className="flex-1 min-h-0 flex flex-col overflow-hidden">
            <div className="flex-1 min-h-0 overflow-hidden">
              <table className="w-full text-xs text-slate-800 dark:text-slate-200">
                <thead className="bg-slate-100 dark:bg-slate-800/80 sticky top-0 z-20">
                  <tr>
                    <th className="text-center px-2 py-2.5 font-medium text-slate-800 dark:text-slate-300 w-10">#</th>
                    {historyColumns.map((col, colIdx) => {
                      const hasFilter = columnFilters[col.key] != null;
                      const isOpen = openFilterColumn === col.key;
                      const uniqueVals = getUniqueValues(col.key);
                      const isLastColumn = colIdx === historyColumns.length - 1;
                      const isSorted = sortConfig.key === col.key;
                      const sortDirection = isSorted ? sortConfig.direction : null;

                      return (
                        <th key={col.key} className="text-left px-3 py-2.5 font-medium text-slate-800 dark:text-slate-300 whitespace-nowrap relative group">
                          <div className="flex items-center gap-1">
                            {/* Clickable header for sorting */}
                            <button
                              onClick={() => handleSort(col.key)}
                              className="flex items-center gap-0.5 hover:text-slate-900 dark:hover:text-slate-100 transition-colors cursor-pointer"
                            >
                              <span>{col.header}</span>
                              {/* Sort icon */}
                              <span className="ml-0.5 inline-flex flex-col text-[8px] leading-none opacity-60">
                                <span className={sortDirection === 'asc' ? 'text-sky-400' : ''}>▲</span>
                                <span className={sortDirection === 'desc' ? 'text-sky-400' : ''}>▼</span>
                              </span>
                            </button>

                            {/* Filter dropdown trigger */}
                            {uniqueVals.length > 0 && (
                              <button
                                onClick={(e) => { e.stopPropagation(); setOpenFilterColumn(isOpen ? null : col.key); }}
                                className={`p-0.5 rounded transition-all ${hasFilter
                                  ? 'text-sky-700 bg-sky-100 dark:text-sky-400 dark:bg-sky-900/30'
                                  : 'text-slate-400 opacity-0 group-hover:opacity-100 hover:text-slate-700 hover:bg-slate-100 dark:text-slate-500 dark:hover:text-slate-300 dark:hover:bg-slate-700'
                                  }`}
                                title="Filter"
                              >
                                <svg className={`w-3.5 h-3.5 transition-transform ${isOpen ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                                </svg>
                              </button>
                            )}
                          </div>

                          {/* Filter dropdown */}
                          {isOpen && uniqueVals.length > 0 && (
                            <HistoryFilterDropdown
                              uniqueValues={uniqueVals}
                              filterValue={columnFilters[col.key]}
                              onFilterChange={(val) => {
                                setColumnFilters(prev => {
                                  const next = { ...prev };
                                  if (val === null) {
                                    delete next[col.key];
                                  } else {
                                    next[col.key] = val;
                                  }
                                  return next;
                                });
                              }}
                              onClose={() => setOpenFilterColumn(null)}
                              position={isLastColumn ? "right" : "left"}
                            />
                          )}
                        </th>
                      );
                    })}
                    <th className="text-left px-3 py-2.5 font-medium text-slate-600 dark:text-slate-300">Desc.</th>
                    <th className="text-left px-3 py-2.5 font-medium text-slate-600 dark:text-slate-300">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-700/50 bg-white dark:bg-slate-900">
                  {paginatedDocs.length === 0 ? (
                    <tr>
                      <td colSpan={11} className="text-center py-8 text-slate-500 dark:text-slate-400">No document uploads yet</td>
                    </tr>
                  ) : (
                    paginatedDocs.map((r, idx) => (
                      <tr key={r.document_id || idx} className="hover:bg-slate-50 dark:hover:bg-slate-800/30">
                        <td className="text-center px-2 py-2.5 text-slate-700 dark:text-slate-400 w-10">{(clampedPage - 1) * ROWS_PER_PAGE + idx + 1}</td>
                        <td className="px-3 py-2.5 whitespace-nowrap text-slate-800 dark:text-slate-300">{formatDateTime(r.created_at)}</td>
                        <td className="px-3 py-2.5 max-w-[180px]">
                          <span className="block truncate font-medium text-slate-900 dark:text-slate-200" title={r.filename}>{r.filename}</span>
                        </td>
                        <td className="px-3 py-2.5 text-slate-800 dark:text-slate-300">{r.metadata?.who || r.uploader}</td>
                        <td className="px-3 py-2.5 text-slate-800 dark:text-slate-300">{r.metadata?.what || "—"}</td>
                        <td className="px-3 py-2.5 text-slate-800 dark:text-slate-300">{r.metadata?.where || "—"}</td>
                        <td className="px-3 py-2.5 text-slate-800 dark:text-slate-300">{r.metadata?.when || "—"}</td>
                        <td className="px-3 py-2.5 text-slate-800 dark:text-slate-300">{r.metadata?.why || "—"}</td>
                        <td className="px-3 py-2.5">
                          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300">
                            {`v${r.version}${r.is_latest ? ' (Latest)' : ''}`}
                          </span>
                        </td>
                        <td className="px-3 py-2.5">
                          <button
                            onClick={() => openDescription(r)}
                            title="View description"
                            className="px-2 py-1 text-xs rounded bg-slate-200 hover:bg-slate-300 text-slate-800 dark:bg-slate-700 dark:hover:bg-slate-600 dark:text-slate-200 transition-colors"
                          >
                            View
                          </button>
                        </td>
                        <td className="px-3 py-2.5">
                          <div className="flex gap-1">
                            {can("download-document", project) && (
                              <button
                                onClick={async () => {
                                  try {
                                    const projectId = project.project_id || project.id;
                                    await api.downloadDocument(projectId, r.document_id);
                                  } catch (error) {
                                    alert('Download failed: ' + formatError(error));
                                  }
                                }}
                                className="px-2 py-1 text-xs rounded bg-slate-200 hover:bg-slate-300 text-slate-800 dark:bg-slate-700 dark:hover:bg-slate-600 dark:text-slate-200 transition-colors"
                              >
                                Download
                              </button>
                            )}
                            <button
                              onClick={async (e) => {
                                e.stopPropagation();
                                await loadVersions(r.document_id, r);
                              }}
                              className="px-2 py-1 text-xs rounded bg-slate-200 hover:bg-slate-300 text-slate-800 dark:bg-slate-700 dark:hover:bg-slate-600 dark:text-slate-200 transition-colors"
                            >
                              Versions
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
            {/* Pagination footer */}
            {!loading && filteredDocs.length > 0 && (
              <div className="flex-shrink-0 flex items-center justify-center gap-2 py-2 border-t border-slate-700">
                <button
                  disabled={clampedPage <= 1}
                  onClick={() => setCurrentPage(1)}
                  title="First page"
                  className="px-2 py-1 text-xs rounded bg-slate-700 hover:bg-slate-600 text-slate-200 disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  «
                </button>
                <button
                  disabled={clampedPage <= 1}
                  onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                  title="Previous page"
                  className="px-2 py-1 text-xs rounded bg-slate-700 hover:bg-slate-600 text-slate-200 disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  ◀
                </button>
                {getPageNumbers().map((p) => (
                  <button
                    key={p}
                    onClick={() => setCurrentPage(p)}
                    className={`px-3 py-1 text-xs rounded transition-colors ${p === clampedPage ? 'bg-sky-600 text-white' : 'bg-slate-700 hover:bg-slate-600 text-slate-200'}`}
                  >
                    {p}
                  </button>
                ))}
                <button
                  disabled={clampedPage >= totalPages}
                  onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                  title="Next page"
                  className="px-2 py-1 text-xs rounded bg-slate-700 hover:bg-slate-600 text-slate-200 disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  ▶
                </button>
                <button
                  disabled={clampedPage >= totalPages}
                  onClick={() => setCurrentPage(totalPages)}
                  title="Last page"
                  className="px-2 py-1 text-xs rounded bg-slate-700 hover:bg-slate-600 text-slate-200 disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  »
                </button>
                <span className="text-xs text-slate-400 ml-3">
                  Page {clampedPage} of {totalPages}
                </span>
                <span className="text-xs text-slate-500 ml-2">
                  ({filteredDocs.length} rows)
                </span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Description popup */}
      {showDescriptionModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div
            className="absolute inset-0 bg-black/50"
            onClick={() => setShowDescriptionModal(false)}
          />
          <div
            className="relative z-10 w-full max-w-lg rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 shadow-lg"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-700 px-4 py-3">
              <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200">
                Description — {descriptionContent.filename}
              </h3>
              <Button variant="secondary" size="sm" onClick={() => setShowDescriptionModal(false)}>
                Close
              </Button>
            </div>
            <div className="p-4 max-h-[60vh] overflow-y-auto">
              <p className="text-sm text-slate-700 dark:text-slate-300 whitespace-pre-wrap">
                {descriptionContent.text || "—"}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Version History Modal */}
      {showVersions && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div
            className="absolute inset-0 bg-black/50"
            onClick={(e) => {
              e.stopPropagation();
              if (isOpeningVersions.current) {
                return;
              }
              setShowVersions(false);
              setVersionDocument(null);
            }}
          />
          <div
            className="relative z-10 w-full max-w-4xl"
            onClick={(e) => e.stopPropagation()}
          >
            <Card
              title={`Version History — ${versionDocument?.filename || 'Unknown'}`}
              actions={<Button variant="secondary" onClick={() => {
                setShowVersions(false);
                setVersionDocument(null);
              }}>Close</Button>}
            >
              <div className="max-h-[70vh] overflow-auto">
                {versions.length === 0 ? (
                  <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                    No versions found for this document.
                  </div>
                ) : (
                  <Table
                    columns={[
                      { header: "Version", key: "version", cell: (v) => `${v.displayVersion || `v${v.version}`} ${v.is_latest_display ? '(Latest)' : ''}` },
                      { header: "Filename", key: "filename", cell: (v) => safeDisplay(v.filename) },
                      { header: "Uploaded By", key: "uploader", cell: (v) => v.uploader },
                      { header: "Uploaded At", key: "created_at", cell: (v) => formatDateTime(v.created_at) },
                      { header: "Size", key: "size", cell: (v) => `${(v.size / 1024).toFixed(1)} KB` },
                      {
                        header: "Actions",
                        key: "actions",
                        cell: (v) => (
                          <div className="flex gap-2">
                            {can("download-document", project) && (
                              <Button
                                variant="secondary"
                                size="sm"
                                onClick={async () => {
                                  try {
                                    const projectId = project.project_id || project.id;
                                    const docId = versionDocument?.document_id;
                                    await api.downloadDocument(projectId, docId, v.version);
                                  } catch (error) {
                                    alert('Download failed: ' + formatError(error));
                                  }
                                }}
                              >
                                Download
                              </Button>
                            )}
                          </div>
                        )
                      },
                    ]}
                    data={versions}
                  />
                )}
              </div>
            </Card>
          </div>
        </div>
      )}
    </div>
  );
};

/* ========= SCRIPT GENERATOR PAGE ========= */
const ScriptGeneratorPage = ({ project, can, authedUser, toast, showConfirmModal }) => {
  const projectId = project?.project_id || project?.id;
  const [deviceInventory, setDeviceInventory] = React.useState([]);
  const [ciscoCommands, setCiscoCommands] = React.useState("");
  const [huaweiCommands, setHuaweiCommands] = React.useState("");
  const [activeVendorTab, setActiveVendorTab] = React.useState("cisco");
  const [loading, setLoading] = React.useState(true);
  const [saving, setSaving] = React.useState(false);
  const [showDeviceModal, setShowDeviceModal] = React.useState(false);
  const [editingDevice, setEditingDevice] = React.useState(null);
  const [csvFileInput, setCsvFileInput] = React.useState(null);
  const [error, setError] = React.useState("");
  const [showCsvInfoModal, setShowCsvInfoModal] = React.useState(false);
  const [generatedScript, setGeneratedScript] = React.useState(null);
  const [scriptLanguage, setScriptLanguage] = React.useState(null);
  const [scriptFilename, setScriptFilename] = React.useState(null);

  // Device form state
  const [deviceForm, setDeviceForm] = React.useState({
    ip: "",
    hostname: "",
    username: "",
    password: "",
    secret: "",
    port: 22,
    device_type: "cisco_ios"
  });

  // Load settings on mount
  React.useEffect(() => {
    const loadSettings = async () => {
      if (!projectId) return;
      setLoading(true);
      try {
        const settings = await api.getScriptSettings(projectId);
        setDeviceInventory(settings.device_inventory || []);
        setCiscoCommands(settings.cisco_commands || "");
        setHuaweiCommands(settings.huawei_commands || "");
      } catch (err) {
        console.error("Failed to load script settings:", err);
        setError("Failed to load settings: " + formatError(err));
      } finally {
        setLoading(false);
      }
    };
    loadSettings();
  }, [projectId]);

  // Save settings (full: device inventory + commands)
  const handleSave = async () => {
    if (!projectId) return;
    setSaving(true);
    setError("");
    try {
      await api.saveScriptSettings(projectId, {
        device_inventory: deviceInventory,
        cisco_commands: ciscoCommands,
        huawei_commands: huaweiCommands
      });
      if (toast) toast.success("Settings saved successfully!");
    } catch (err) {
      console.error("Failed to save settings:", err);
      setError("Failed to save settings: " + formatError(err));
    } finally {
      setSaving(false);
    }
  };

  // Persist only device inventory (auto-save after add/edit/delete/import)
  const persistDeviceInventory = async (inventory) => {
    if (!projectId) return;
    setSaving(true);
    setError("");
    try {
      await api.saveScriptSettings(projectId, {
        device_inventory: inventory,
        cisco_commands: ciscoCommands,
        huawei_commands: huaweiCommands
      });
    } catch (err) {
      console.error("Failed to save device list:", err);
      setError("Failed to save: " + formatError(err));
    } finally {
      setSaving(false);
    }
  };

  // Device CRUD operations
  const handleAddDevice = () => {
    setDeviceForm({
      ip: "",
      hostname: "",
      username: "",
      password: "",
      secret: "",
      port: 22,
      device_type: "cisco_ios"
    });
    setEditingDevice(null);
    setShowDeviceModal(true);
  };

  const handleEditDevice = (device, index) => {
    setDeviceForm({ ...device });
    setEditingDevice(index);
    setShowDeviceModal(true);
  };

  const handleDeleteDevice = (index) => {
    const device = deviceInventory[index];
    showConfirmModal({
      title: "Delete Device",
      message: `Are you sure you want to delete device "${device?.hostname || device?.ip || 'this device'}"?`,
      confirmText: "Delete",
      variant: "danger",
      onConfirm: () => {
        const next = deviceInventory.filter((_, i) => i !== index);
        setDeviceInventory(next);
        persistDeviceInventory(next);
      }
    });
  };

  const handleSaveDevice = () => {
    if (!deviceForm.ip || !deviceForm.username) {
      alert("IP and Username are required");
      return;
    }
    let next;
    if (editingDevice !== null) {
      next = [...deviceInventory];
      next[editingDevice] = { ...deviceForm };
    } else {
      next = [...deviceInventory, { ...deviceForm }];
    }
    setDeviceInventory(next);
    setShowDeviceModal(false);
    setEditingDevice(null);
    persistDeviceInventory(next);
  };

  // CSV operations: Export template that matches Import format exactly
  const exportCsvTemplate = () => {
    const header = "ip,hostname,username,password,secret,port,device_type";
    const exampleCisco = "192.168.1.1,Core-SW,admin,password123,enable_secret,22,cisco_ios";
    const exampleHuawei = "192.168.1.2,Dist-SW,admin,password456,,22,huawei_vrp";
    const csv = [header, exampleCisco, exampleHuawei].join("\n");
    const blob = new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "device_inventory_template.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleCsvImport = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const text = await file.text();
    const rawLines = text.split(/\r?\n/).map(line => line.trim()).filter(line => line.length > 0);
    // Skip comment lines (starting with #) and find header row
    const lines = rawLines.filter(line => !line.startsWith("#"));
    if (lines.length < 2) {
      alert("CSV must have a header row and at least one data row. Use Export CSV Template for the correct format.");
      return;
    }

    const headers = lines[0].split(",").map(h => h.trim().toLowerCase().replace(/^\s*#\s*/, ""));
    const requiredHeaders = ["ip", "username"];
    const missingHeaders = requiredHeaders.filter(h => !headers.includes(h));
    if (missingHeaders.length > 0) {
      alert(`CSV missing required columns: ${missingHeaders.join(", ")}. Expected: ip, hostname, username, password, secret, port, device_type`);
      return;
    }

    const devices = [];
    for (let i = 1; i < lines.length; i++) {
      const values = lines[i].split(",").map(v => v.trim());
      const device = {};
      headers.forEach((header, idx) => {
        device[header] = values[idx] || "";
      });
      if (device.ip && device.username) {
        const dt = (device.device_type || "cisco_ios").toLowerCase();
        devices.push({
          ip: device.ip,
          hostname: device.hostname || "",
          username: device.username,
          password: device.password || "",
          secret: device.secret || "",
          port: parseInt(device.port, 10) || 22,
          device_type: dt === "huawei_vrp" ? "huawei_vrp" : "cisco_ios"
        });
      }
    }

    if (devices.length > 0) {
      const next = [...deviceInventory, ...devices];
      setDeviceInventory(next);
      persistDeviceInventory(next);
      alert(`Imported ${devices.length} device(s). Saved.`);
    } else {
      alert("No valid devices found in CSV. Each row needs at least ip and username.");
    }
    e.target.value = "";
  };

  // Script generation
  const generateLinuxScript = () => {
    const commands = activeVendorTab === "cisco" ? ciscoCommands : huaweiCommands;
    const vendor = activeVendorTab === "cisco" ? "cisco_ios" : "huawei_vrp";

    const filteredDevices = deviceInventory.filter(d => d.device_type === vendor);
    if (filteredDevices.length === 0) {
      if (toast) toast.warning("No devices found for selected vendor type");
      return;
    }

    // Helper function to sanitize hostname for filename
    const sanitizeFilename = (str) => {
      return (str || "").replace(/[\/\\:*?"<>| ]/g, "_").replace(/_+/g, "_").replace(/^_|_$/g, "");
    };

    let script = "#!/bin/bash\n\n";
    script += "# Auto-generated backup script\n";
    script += "# Generated: " + new Date().toISOString() + "\n\n";
    script += "# Check if sshpass is installed\n";
    script += "if ! command -v sshpass &> /dev/null; then\n";
    script += "    echo \"Error: sshpass is not installed.\"\n";
    script += "    echo \"Please install it using: sudo apt-get install sshpass (Debian/Ubuntu) or sudo yum install sshpass (RHEL/CentOS)\"\n";
    script += "    exit 1\n";
    script += "fi\n\n";
    script += "DATE_DIR=\"$(date +%Y-%m-%d)\"\n";
    script += "OUTPUT_DIR=\"backups/$DATE_DIR\"\n";
    script += "mkdir -p \"$OUTPUT_DIR\"\n";
    script += "SUCCESS_COUNT=0\n";
    script += "TOTAL_DEVICES=" + filteredDevices.length + "\n\n";

    // Build command list
    const commandLines = commands.split("\n").map(c => c.trim()).filter(c => c && !c.startsWith("!"));

    filteredDevices.forEach(device => {
      const hostname = device.hostname || device.ip;
      const safeHostname = sanitizeFilename(hostname);
      const ip = device.ip;
      const username = device.username;
      const password = device.password || "";
      const secret = device.secret || "";
      const port = device.port || 22;
      const isHuawei = device.device_type === "huawei_vrp";

      script += `# Backup device: ${hostname} (${ip})\n`;
      script += `echo "Connecting to ${hostname} (${ip})..."\n`;
      script += `OUTPUT_FILE="$OUTPUT_DIR/${safeHostname}_$(date +%Y%m%d_%H%M%S).txt"\n\n`;

      // Escape password for bash
      const escapedPassword = password.replace(/\\/g, "\\\\").replace(/"/g, '\\"').replace(/\$/g, "\\$").replace(/`/g, "\\`");
      const escapedSecret = secret.replace(/\\/g, "\\\\").replace(/"/g, '\\"').replace(/\$/g, "\\$").replace(/`/g, "\\`");

      // Global SSH options (all vendors)
      let sshOptions = "-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=10";
      // Huawei-specific legacy algorithms for older devices
      if (isHuawei) {
        sshOptions += " -o KexAlgorithms=+diffie-hellman-group1-sha1,diffie-hellman-group14-sha1";
        sshOptions += " -o HostKeyAlgorithms=+ssh-rsa";
        sshOptions += " -o Ciphers=+aes128-cbc,3des-cbc,aes128-ctr,aes256-ctr";
        sshOptions += " -o MACs=+hmac-sha1,hmac-md5,hmac-sha1-96,hmac-md5-96";
      }

      if (secret) {
        script += `sshpass -p "${escapedPassword}" ssh -v ${sshOptions} -p ${port} ${username}@${ip} <<'EOF' | tee "$OUTPUT_FILE"\n`;
        script += "enable\n";
        script += `${escapedSecret}\n`;
        commandLines.forEach(cmd => {
          script += `${cmd}\n`;
        });
        script += "exit\n";
        script += "EOF\n";
      } else {
        script += `sshpass -p "${escapedPassword}" ssh -v ${sshOptions} -p ${port} ${username}@${ip} <<'EOF' | tee "$OUTPUT_FILE"\n`;
        commandLines.forEach(cmd => {
          script += `${cmd}\n`;
        });
        script += "exit\n";
        script += "EOF\n";
      }
      script += "SSH_EXIT_CODE=${PIPESTATUS[0]}\n";
      script += `if [ "$SSH_EXIT_CODE" -eq 0 ]; then\n`;
      script += `    echo "✅ Backup successful for ${hostname}"\n`;
      script += `    SUCCESS_COUNT=$((SUCCESS_COUNT + 1))\n`;
      script += `else\n`;
      script += `    echo "❌ Error: Backup failed for ${hostname}"\n`;
      script += `    rm -f "$OUTPUT_FILE"\n`;
      script += `fi\n`;
      script += `echo ""\n\n`;
    });

    script += "echo \"Backup process completed. $SUCCESS_COUNT/$TOTAL_DEVICES device(s) backed up successfully.\"\n";

    // Determine vendor label for filename (Cisco / Huawei / Mixed_Network)
    const deviceTypes = new Set(filteredDevices.map(d => d.device_type));
    let vendorLabel;
    if (deviceTypes.size > 1) {
      vendorLabel = "Mixed_Network";
    } else {
      const onlyType = deviceTypes.values().next().value;
      if (onlyType === "cisco_ios") {
        vendorLabel = "Cisco";
      } else if (onlyType === "huawei_vrp") {
        vendorLabel = "Huawei";
      } else {
        vendorLabel = "Mixed_Network";
      }
    }
    const osLabel = "Linux";
    const ext = "sh";
    const baseFilename = `${vendorLabel}_Backup_for_${osLabel}.${ext}`;
    const safeFilename = sanitizeFilename(baseFilename);

    // Store script for preview
    setGeneratedScript(script);
    setScriptLanguage("bash");
    setScriptFilename(safeFilename);

    // Also download automatically
    downloadScript(script, safeFilename);
    if (toast) toast.success(`Linux script generated and downloaded: ${safeFilename}`);
  };

  const generatePythonScript = () => {
    const commands = activeVendorTab === "cisco" ? ciscoCommands : huaweiCommands;
    const vendor = activeVendorTab === "cisco" ? "cisco_ios" : "huawei_vrp";

    const filteredDevices = deviceInventory.filter(d => d.device_type === vendor);

    // Helper function to sanitize hostname for filename
    const sanitizeFilename = (str) => {
      return (str || "").replace(/[\/\\:*?"<>| ]/g, "_").replace(/_+/g, "_").replace(/^_|_$/g, "");
    };

    // Helper function to escape strings for Python
    const escapeStr = (s) => (s || "").replace(/\\/g, "\\\\").replace(/"/g, '\\"').replace(/\n/g, "\\n");

    let script = "#!/usr/bin/env python3\n";
    script += "# -*- coding: utf-8 -*-\n";
    script += "\"\"\"\n";
    script += "Auto-generated backup script\n";
    script += "Generated: " + new Date().toISOString() + "\n";
    script += "\"\"\"\n\n";
    script += "from netmiko import ConnectHandler\n";
    script += "from datetime import datetime\n";
    script += "import os\n";
    script += "import re\n";
    script += "# import logging\n";
    script += "# logging.basicConfig(filename='netmiko_debug.log', level=logging.DEBUG)  # Uncomment for debugging\n\n";
    script += "DATE_DIR = datetime.now().strftime('%Y-%m-%d')\n";
    script += "OUTPUT_DIR = os.path.join('backups', DATE_DIR)\n";
    script += "os.makedirs(OUTPUT_DIR, exist_ok=True)\n\n";
    script += "def sanitize_filename(name):\n";
    script += "    \"\"\"Remove invalid characters from filename\"\"\"\n";
    script += "    return re.sub(r'[\\/\\\\:*?\"<>| ]', '_', name).replace('__', '_').strip('_')\n\n";
    script += "DEVICE_INVENTORY = [\n";
    filteredDevices.forEach(device => {
      script += `    {\n`;
      script += `        "device_type": "${device.device_type}",\n`;
      script += `        "host": "${escapeStr(device.ip)}",\n`;
      script += `        "username": "${escapeStr(device.username)}",\n`;
      script += `        "password": "${escapeStr(device.password)}",\n`;
      script += `        "secret": "${escapeStr(device.secret || "")}",\n`;
      script += `        "port": ${device.port || 22},\n`;
      script += `        "hostname": "${escapeStr(device.hostname || device.ip)}"\n`;
      script += `    },\n`;
    });
    script += "]\n\n";
    script += "COMMANDS = \"\"\"\n";
    script += commands + "\n";
    script += "\"\"\"\n\n";
    script += "def backup_device(device_info):\n";
    script += "    try:\n";
    script += "        print(f\"Connecting to {device_info['hostname']} ({device_info['host']})...\")\n";
    script += "        \n";
    script += "        # Create connection handler with robust parameters\n";
    script += "        # Rely on explicit password; do not pass look_for_keys/allow_agent (not in all Netmiko versions)\n";
    script += "        connection_params = {\n";
    script += "            'device_type': device_info['device_type'],\n";
    script += "            'host': device_info['host'],\n";
    script += "            'username': device_info['username'],\n";
    script += "            'password': device_info['password'],\n";
    script += "            'port': device_info['port'],\n";
    script += "            'global_delay_factor': 4,      # Handle very slow / legacy devices\n";
    script += "            'auth_timeout': 60,\n";
    script += "            'banner_timeout': 60,\n";
    script += "            'conn_timeout': 60,            # Extended timeout for initial connection\n";
    script += "        }\n";
    script += "        \n";
    script += "        # Add enable secret only if provided\n";
    script += "        secret = device_info.get('secret')\n";
    script += "        if secret:\n";
    script += "            connection_params['secret'] = secret\n";
    script += "        \n";
    script += "        with ConnectHandler(**connection_params) as conn:\n";
    script += "            # Enter enable mode only when a secret is configured\n";
    script += "            if secret:\n";
    script += "                conn.enable()\n";
    script += "            \n";
    script += "            # Execute commands (send each command separately)\n";
    script += "            command_list = COMMANDS.strip().split('\\n')\n";
    script += "            command_list = [c.strip() for c in command_list if c.strip() and not c.strip().startswith('!')]\n";
    script += "            \n";
    script += "            output_parts = []\n";
    script += "            for cmd in command_list:\n";
    script += "                try:\n";
    script += "                    # Use increased timeout for commands like 'show run' that can be slow\n";
    script += "                    result = conn.send_command(cmd, read_timeout=90)\n";
    script += "                    output_parts.append(f\"=== {cmd} ===\\n{result}\\n\")\n";
    script += "                except Exception as e:\n";
    script += "                    output_parts.append(f\"=== {cmd} ===\\nError: {e}\\n\")\n";
    script += "            \n";
    script += "            output = '\\n'.join(output_parts)\n";
    script += "            \n";
    script += "            # Save output to file with sanitized filename\n";
    script += "            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')\n";
    script += "            safe_hostname = sanitize_filename(device_info['hostname'])\n";
    script += "            filename = os.path.join(OUTPUT_DIR, f\"{safe_hostname}_{timestamp}.txt\")\n";
    script += "            with open(filename, 'w', encoding='utf-8') as f:\n";
    script += "                f.write(output)\n";
    script += "            \n";
    script += "            print(f\"Backup completed for {device_info['hostname']}: {filename}\")\n";
    script += "            return True\n";
    script += "    except Exception as e:\n";
    script += "        print(f\"Error backing up {device_info['hostname']}: {e}\")\n";
    script += "        return False\n\n";
    script += "if __name__ == \"__main__\":\n";
    script += "    print(\"Starting backup process...\")\n";
    script += "    print(f\"Found {len(DEVICE_INVENTORY)} device(s)\")\n";
    script += "    print(\"\")\n";
    script += "    \n";
    script += "    success_count = 0\n";
    script += "    for device in DEVICE_INVENTORY:\n";
    script += "        if backup_device(device):\n";
    script += "            success_count += 1\n";
    script += "        print(\"\")\n";
    script += "    \n";
    script += "    print(f\"Backup process completed. {success_count}/{len(DEVICE_INVENTORY)} device(s) backed up successfully.\")\n";

    // Determine vendor label for filename (Cisco / Huawei / Mixed_Network)
    const deviceTypes = new Set(filteredDevices.map(d => d.device_type));
    let vendorLabel;
    if (deviceTypes.size > 1) {
      vendorLabel = "Mixed_Network";
    } else {
      const onlyType = deviceTypes.values().next().value;
      if (onlyType === "cisco_ios") {
        vendorLabel = "Cisco";
      } else if (onlyType === "huawei_vrp") {
        vendorLabel = "Huawei";
      } else {
        vendorLabel = "Mixed_Network";
      }
    }
    const osLabel = "Windows";
    const ext = "py";
    const baseFilename = `${vendorLabel}_Backup_for_${osLabel}.${ext}`;
    const safeFilename = sanitizeFilename(baseFilename);

    // Store script for preview
    setGeneratedScript(script);
    setScriptLanguage("python");
    setScriptFilename(safeFilename);

    // Also download automatically
    downloadScript(script, safeFilename);
    if (toast) toast.success(`Python script generated and downloaded: ${safeFilename}`);
  };

  const downloadScript = (content, filename) => {
    const blob = new Blob([content], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleDownloadScript = () => {
    if (generatedScript && scriptFilename) {
      downloadScript(generatedScript, scriptFilename);
      if (toast) toast.success(`Script downloaded: ${scriptFilename}`);
    }
  };

  const maskPassword = (str) => {
    if (!str) return "";
    return "•".repeat(Math.min(str.length, 8));
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-gray-500 dark:text-gray-400">Loading script settings...</div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {error && (
        <div className="flex-shrink-0 px-4 py-2 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-700 dark:text-red-400 text-sm">
          {safeDisplay(error)}
        </div>
      )}

      {/* Top 60%: Device Inventory */}
      <div className="flex-[0.6] min-h-0 flex flex-col overflow-hidden flex-shrink-0">
        <Card
          compactHeader
          title={
            <span className="flex items-center gap-1.5 text-base font-semibold text-gray-700 dark:text-gray-200">
              Device Inventory
              <button
                type="button"
                onClick={() => setShowCsvInfoModal(true)}
                className="inline-flex items-center justify-center w-4 h-4 rounded-full bg-slate-300 dark:bg-slate-500 text-slate-700 dark:text-slate-100 hover:bg-slate-400 dark:hover:bg-slate-400 text-[10px] font-semibold focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors"
                title="CSV format and import instructions"
                aria-label="Show CSV instructions"
              >
                i
              </button>
            </span>
          }
          actions={
            <div className="flex items-center gap-1.5 flex-wrap">
              <button
                type="button"
                onClick={exportCsvTemplate}
                className="px-2 py-1 rounded-md text-xs font-medium border border-slate-400 dark:border-slate-500 bg-slate-100 dark:bg-slate-700 text-slate-800 dark:text-slate-200 hover:bg-slate-200 dark:hover:bg-slate-600 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors"
              >
                Export CSV Template
              </button>
              <label className="inline-block">
                <input
                  type="file"
                  accept=".csv"
                  onChange={handleCsvImport}
                  className="hidden"
                  ref={el => setCsvFileInput(el)}
                />
                <span className="inline-flex items-center justify-center px-2 py-1 rounded-md text-xs font-medium bg-blue-600 hover:bg-blue-700 text-white focus:outline-none focus:ring-2 focus:ring-blue-400 dark:bg-blue-600 dark:hover:bg-blue-500 dark:text-white cursor-pointer">
                  Import CSV
                </span>
              </label>
              <button
                type="button"
                onClick={handleAddDevice}
                className="px-2 py-1 rounded-md text-xs font-medium bg-emerald-600 hover:bg-emerald-700 text-white focus:outline-none focus:ring-2 focus:ring-emerald-400 dark:bg-emerald-600 dark:hover:bg-emerald-500 dark:text-white transition-colors"
              >
                + Add Device
              </button>
            </div>
          }
          className="h-full flex flex-col min-h-0 overflow-hidden"
        >
          <div className="flex-1 min-h-0 overflow-auto">
            <table className="w-full border-collapse table-fixed">
              <thead>
                <tr className="bg-slate-100 dark:bg-slate-800 border-b border-slate-200 dark:border-slate-600">
                  <th className="px-4 py-3 text-left text-sm font-semibold text-slate-700 dark:text-slate-200 w-24">Status</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-slate-700 dark:text-slate-200 w-[44%]">Hostname/IP</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-slate-700 dark:text-slate-200 w-32">Vendor</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-slate-700 dark:text-slate-200 w-[28%]">Auth</th>
                  <th className="px-4 py-3 text-right text-sm font-semibold text-slate-700 dark:text-slate-200 w-20">Actions</th>
                </tr>
              </thead>
              <tbody>
                {deviceInventory.length === 0 ? (
                  <tr>
                    <td colSpan="5" className="px-5 py-10 text-center text-slate-600 dark:text-slate-300">
                      No devices added yet. Click "+ Add Device" to get started.
                    </td>
                  </tr>
                ) : (
                  deviceInventory.map((device, index) => (
                    <tr key={index} className="hover:bg-slate-50 dark:hover:bg-slate-800/60 border-b border-slate-200 dark:border-slate-700 transition-colors">
                      <td className="px-4 py-3 align-middle">
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-200 border border-green-300 dark:border-green-700">
                          Ready
                        </span>
                      </td>
                      <td className="px-4 py-3 align-middle">
                        <div className="font-medium text-slate-900 dark:text-slate-100 leading-tight truncate">{device.hostname || device.ip}</div>
                        <div className="text-xs text-slate-600 dark:text-slate-400 mt-0.5 truncate">{device.ip}</div>
                      </td>
                      <td className="px-4 py-3 align-middle">
                        <span className="text-sm font-medium text-slate-700 dark:text-slate-200">
                          {device.device_type === "cisco_ios" ? "Cisco IOS" : "Huawei VRP"}
                        </span>
                      </td>
                      <td className="px-4 py-3 align-middle">
                        <div className="flex items-center gap-2 min-w-0">
                          <span className="font-medium text-slate-700 dark:text-slate-200 truncate">{device.username}</span>
                          <span className="text-slate-400 dark:text-slate-500 flex-shrink-0">/</span>
                          <span className="font-mono text-slate-600 dark:text-slate-300 truncate">{maskPassword(device.password)}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3 align-middle">
                        <div className="flex items-center justify-end gap-1.5">
                          <button
                            type="button"
                            onClick={() => handleEditDevice(device, index)}
                            className="p-1.5 rounded text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-600 hover:text-slate-800 dark:hover:text-slate-100 transition-colors"
                            title="Edit"
                            aria-label="Edit device"
                          >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                            </svg>
                          </button>
                          <button
                            type="button"
                            onClick={() => handleDeleteDevice(index)}
                            className="p-1.5 rounded text-red-600 dark:text-red-400 hover:bg-red-100 dark:hover:bg-red-900/30 transition-colors"
                            title="Delete"
                            aria-label="Delete device"
                          >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                            </svg>
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </Card>
      </div>

      {/* Bottom 40%: Command Template + Export Script */}
      <div className="flex-[0.4] min-h-0 grid grid-cols-3 gap-4 overflow-hidden pt-3">
        {/* Section 2: Command Template (2/3 width) */}
        <Card
          compactHeader
          className="col-span-2 flex flex-col min-h-0 overflow-hidden"
          title="Command Template"
          actions={
            <>
              <Select
                value={activeVendorTab}
                onChange={(val) => setActiveVendorTab(val)}
                options={[
                  { value: "cisco", label: "Cisco IOS" },
                  { value: "huawei", label: "Huawei VRP" }
                ]}
                className="w-32 text-xs py-1"
              />
              <Button variant="success" onClick={handleSave} disabled={saving} className="text-xs py-1 px-2">
                {saving ? "Saving..." : "Save"}
              </Button>
            </>
          }
        >
          <div className="flex-1 min-h-0 flex flex-col p-4 overflow-hidden">
            <textarea
              value={activeVendorTab === "cisco" ? ciscoCommands : huaweiCommands}
              onChange={(e) => {
                if (activeVendorTab === "cisco") {
                  setCiscoCommands(e.target.value);
                } else {
                  setHuaweiCommands(e.target.value);
                }
              }}
              className="flex-1 min-h-[200px] w-full bg-[#1e1e1e] text-[#d4d4d4] font-mono text-sm p-4 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 border border-gray-300 dark:border-gray-700 overflow-y-auto"
              placeholder="Enter commands here..."
            />
          </div>
        </Card>

        {/* Section 3: Script Export (1/3 width) */}
        <Card compactHeader className="col-span-1 flex flex-col min-h-0 overflow-hidden" title="Generate Script">
          <div className="flex-1 min-h-0 flex flex-col p-3 gap-3 overflow-hidden">
            <div className="flex-shrink-0 bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-200 dark:border-indigo-800 rounded-lg px-3 py-2.5 text-indigo-800 dark:text-indigo-200 text-sm">
              <div className="font-medium text-xs mb-1">Device Count</div>
              <div className="text-2xl font-bold leading-tight">{deviceInventory.filter(d => d.device_type === (activeVendorTab === "cisco" ? "cisco_ios" : "huawei_vrp")).length}</div>
              <div className="text-xs opacity-75 mt-1">devices for {activeVendorTab === "cisco" ? "Cisco IOS" : "Huawei VRP"}</div>
            </div>
            <div className="flex-shrink-0 flex flex-col gap-2">
              <button
                type="button"
                onClick={generateLinuxScript}
                disabled={deviceInventory.filter(d => d.device_type === (activeVendorTab === "cisco" ? "cisco_ios" : "huawei_vrp")).length === 0}
                className="w-full py-2.5 bg-orange-600 hover:bg-orange-700 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg flex items-center justify-center gap-2 text-sm font-semibold shadow-sm focus:outline-none focus:ring-2 focus:ring-orange-400 transition-colors"
              >
                <span>🐧</span>
                <span>Linux Script (.sh)</span>
              </button>
              <button
                type="button"
                onClick={generatePythonScript}
                disabled={deviceInventory.filter(d => d.device_type === (activeVendorTab === "cisco" ? "cisco_ios" : "huawei_vrp")).length === 0}
                className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg flex items-center justify-center gap-2 text-sm font-semibold shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 transition-colors"
              >
                <span>🐍</span>
                <span>Windows Script (.py)</span>
              </button>
            </div>
          </div>
        </Card>
      </div>

      {/* Add/Edit Device Modal */}
      {showDeviceModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/50" onClick={() => setShowDeviceModal(false)} />
          <div className="relative z-10 w-full max-w-md">
            <Card
              title={editingDevice !== null ? "Edit Device" : "Add Device"}
              actions={
                <button
                  type="button"
                  onClick={() => setShowDeviceModal(false)}
                  className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 p-1 rounded transition-colors"
                  aria-label="Close"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              }
            >
              <div className="space-y-4">
                <Field label="IP Address *">
                  <Input
                    type="text"
                    value={deviceForm.ip}
                    onChange={(e) => setDeviceForm({ ...deviceForm, ip: e.target.value })}
                    placeholder="192.168.1.1"
                  />
                </Field>
                <Field label="Hostname">
                  <Input
                    type="text"
                    value={deviceForm.hostname}
                    onChange={(e) => setDeviceForm({ ...deviceForm, hostname: e.target.value })}
                    placeholder="Core-SW"
                  />
                </Field>
                <Field label="Username *">
                  <Input
                    type="text"
                    value={deviceForm.username}
                    onChange={(e) => setDeviceForm({ ...deviceForm, username: e.target.value })}
                    placeholder="admin"
                  />
                </Field>
                <Field label="Password">
                  <PasswordInput
                    value={deviceForm.password}
                    onChange={(e) => setDeviceForm({ ...deviceForm, password: e.target.value })}
                    placeholder="password123"
                  />
                </Field>
                <Field label="Secret (Enable)">
                  <PasswordInput
                    value={deviceForm.secret}
                    onChange={(e) => setDeviceForm({ ...deviceForm, secret: e.target.value })}
                    placeholder="Leave empty if same as password or not required"
                  />
                  <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                    Enable/privileged password (Cisco). Leave empty if same as password, not required, or for Huawei devices.
                  </p>
                </Field>
                <div className="grid grid-cols-2 gap-4">
                  <Field label="Port">
                    <Input
                      type="number"
                      value={deviceForm.port}
                      onChange={(e) => setDeviceForm({ ...deviceForm, port: parseInt(e.target.value) || 22 })}
                      placeholder="22"
                    />
                  </Field>
                  <Field label="Device Type">
                    <Select
                      value={deviceForm.device_type}
                      onChange={(val) => setDeviceForm({ ...deviceForm, device_type: val })}
                      options={[
                        { value: "cisco_ios", label: "Cisco IOS" },
                        { value: "huawei_vrp", label: "Huawei VRP" }
                      ]}
                    />
                  </Field>
                </div>
              </div>
              <div className="flex gap-2 justify-end mt-6 pt-4 border-t border-gray-100 dark:border-[#1F2937]">
                <Button variant="secondary" onClick={() => setShowDeviceModal(false)}>
                  Cancel
                </Button>
                <Button variant="success" onClick={handleSaveDevice}>
                  {editingDevice !== null ? "Update" : "Add"}
                </Button>
              </div>
            </Card>
          </div>
        </div>
      )}

      {/* CSV format & import instructions modal */}
      {showCsvInfoModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/50" onClick={() => setShowCsvInfoModal(false)} />
          <div className="relative z-10 w-full max-w-lg max-h-[90vh] overflow-hidden">
            <Card
              title={
                <span className="flex items-center gap-2">
                  <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-blue-100 dark:bg-blue-900/50 text-blue-600 dark:text-blue-300 text-xs font-medium">i</span>
                  CSV Template & Import Guide
                </span>
              }
              actions={
                <button
                  type="button"
                  onClick={() => setShowCsvInfoModal(false)}
                  className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 p-1 rounded transition-colors"
                  aria-label="Close"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              }
              className="flex flex-col max-h-[90vh]"
            >
              <div className="flex-1 overflow-y-auto space-y-4 text-sm text-gray-700 dark:text-gray-300">
                <section>
                  <h4 className="font-semibold text-gray-900 dark:text-gray-100 mb-2">How to use</h4>
                  <ol className="list-decimal list-inside space-y-1.5 pl-1 text-gray-600 dark:text-gray-400">
                    <li>Click <strong className="text-gray-900 dark:text-gray-100">Export CSV Template</strong> to download a template file.</li>
                    <li>Open the file in Excel or a text editor and fill in your device data.</li>
                    <li>Save the file as CSV (UTF-8).</li>
                    <li>Click <strong className="text-gray-900 dark:text-gray-100">Import CSV</strong> and select your saved file.</li>
                    <li>Click <strong className="text-gray-900 dark:text-gray-100">Save Settings</strong> (in Command Template section) to store the devices in this project.</li>
                    <li>Use <strong className="text-gray-900 dark:text-gray-100">Linux Script (.sh)</strong> or <strong className="text-gray-900 dark:text-gray-100">Windows Script (.py)</strong> to generate backup scripts.</li>
                  </ol>
                </section>
                <section>
                  <h4 className="font-semibold text-gray-900 dark:text-gray-100 mb-2">CSV columns (in the exported template)</h4>
                  <ul className="space-y-1.5 border border-gray-200 dark:border-[#1F2937] rounded-lg p-3 bg-gray-50 dark:bg-slate-900/50">
                    <li><strong className="text-gray-900 dark:text-gray-100">ip</strong> (required) — Device IP address, e.g. 192.168.1.1</li>
                    <li><strong className="text-gray-900 dark:text-gray-100">hostname</strong> (optional) — Display name, e.g. Core-SW. If empty, IP is used.</li>
                    <li><strong className="text-gray-900 dark:text-gray-100">username</strong> (required) — SSH login username</li>
                    <li><strong className="text-gray-900 dark:text-gray-100">password</strong> (optional) — SSH password. Leave empty if using key-based auth (script may need editing).</li>
                    <li><strong className="text-gray-900 dark:text-gray-100">secret</strong> (optional) — Enable/privileged password (Cisco). Leave empty for Huawei or if not used.</li>
                    <li><strong className="text-gray-900 dark:text-gray-100">port</strong> (optional) — SSH port; default 22 if empty.</li>
                    <li><strong className="text-gray-900 dark:text-gray-100">device_type</strong> (optional) — Use <code className="px-1 py-0.5 bg-gray-200 dark:bg-slate-700 rounded text-xs font-mono">cisco_ios</code> or <code className="px-1 py-0.5 bg-gray-200 dark:bg-slate-700 rounded text-xs font-mono">huawei_vrp</code>. Default is cisco_ios.</li>
                  </ul>
                </section>
                <section>
                  <h4 className="font-semibold text-gray-900 dark:text-gray-100 mb-2">Import rules</h4>
                  <div className="space-y-1 text-gray-600 dark:text-gray-400">
                    <p>• Rows must have <strong className="text-gray-900 dark:text-gray-100">ip</strong> and <strong className="text-gray-900 dark:text-gray-100">username</strong> to be imported.</p>
                    <p>• Imported devices are <strong className="text-gray-900 dark:text-gray-100">added</strong> to the current list (not replaced).</p>
                    <p>• Lines starting with <strong className="text-gray-900 dark:text-gray-100">#</strong> are ignored (you can add comments in the file).</p>
                    <p>• After importing, click <strong className="text-gray-900 dark:text-gray-100">Save Settings</strong> so devices are saved for script generation.</p>
                  </div>
                </section>
              </div>
              <div className="flex-shrink-0 pt-4 mt-4 border-t border-gray-100 dark:border-[#1F2937]">
                <Button variant="primary" onClick={() => setShowCsvInfoModal(false)}>Close</Button>
              </div>
            </Card>
          </div>
        </div>
      )}
    </div>
  );
};

const DocumentsPage = ({ project, can, authedUser, uploadHistory, setUploadHistory, setProjects, showConfirmModal }) => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [selectedDocument, setSelectedDocument] = useState(null); // Document from API
  const [selectedFolder, setSelectedFolder] = useState(null);
  const [expanded, setExpanded] = useState(
    new Set(["root", "Config"])
  );
  const [layout, setLayout] = useState("side");
  const [showUploadConfig, setShowUploadConfig] = useState(false);
  const [showUploadDocument, setShowUploadDocument] = useState(false);
  const [showFolderDialog, setShowFolderDialog] = useState(false);
  const [folderAction, setFolderAction] = useState("add"); // "add", "edit", "delete"
  const [folderName, setFolderName] = useState("");
  const [folderParent, setFolderParent] = useState(null);
  const [showFileRenameDialog, setShowFileRenameDialog] = useState(false);
  const [fileRenameName, setFileRenameName] = useState("");
  const [fileToRename, setFileToRename] = useState(null);
  const [documents, setDocuments] = useState([]); // Documents from API
  const [loading, setLoading] = useState(true);
  const [previewContent, setPreviewContent] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [pdfBlobUrl, setPdfBlobUrl] = useState(null);
  const [filesPanelCollapsed, setFilesPanelCollapsed] = useState(false);
  const [versions, setVersions] = useState([]);
  const [showVersions, setShowVersions] = useState(false);
  const [versionDocument, setVersionDocument] = useState(null); // Store document info for version modal
  const isOpeningVersions = useRef(false); // Flag to prevent accidental modal close during opening
  const [showMoveFolder, setShowMoveFolder] = useState(false);
  const [moveFolderTarget, setMoveFolderTarget] = useState(null);
  const [moveFolderId, setMoveFolderId] = useState('');
  // Load custom folders from API
  const [customFolders, setCustomFolders] = useState([]);

  // Load folders from API on mount and when project changes
  useEffect(() => {
    const loadFolders = async () => {
      if (!project?.project_id && !project?.id) {
        setCustomFolders([]);
        return;
      }
      try {
        const projectId = project.project_id || project.id;
        const folders = await api.getFolders(projectId);
        // Transform API response: normalize parentId so "root" / undefined become null (root folders)
        const transformedFolders = (folders || []).map(f => ({
          id: f.id,
          name: f.name,
          parentId: (f.parent_id === "root" || f.parent_id == null || f.parent_id === undefined) ? null : (f.parent_id || null),
          deleted: !!f.deleted
        }));
        setCustomFolders(transformedFolders);
      } catch (error) {
        console.error('Failed to load folders:', error);
        setCustomFolders([]);
      }
    };
    loadFolders();
  }, [project]);

  // Load documents from API
  useEffect(() => {
    const loadDocuments = async () => {
      if (!project?.project_id && !project?.id) {
        setLoading(false);
        return;
      }
      setLoading(true);
      try {
        const projectId = project.project_id || project.id;
        const docs = await api.getDocuments(projectId);
        // Ensure docs is an array
        setDocuments(Array.isArray(docs) ? docs : []);
      } catch (error) {
        console.error('Failed to load documents:', error);
        setDocuments([]);
      } finally {
        setLoading(false);
      }
    };
    loadDocuments();
  }, [project]);

  const handleUpload = async (uploadRecord, folderId) => {
    // Add to upload history
    setUploadHistory(prev => [uploadRecord, ...prev]);

    // Always reload documents from API after upload
    // Add a small delay to ensure backend has finished processing
    try {
      const projectId = project.project_id || project.id;

      // Wait a bit for backend to finish processing (especially for config parsing)
      await new Promise(resolve => setTimeout(resolve, 500));

      // Reload all documents (frontend will filter by folder in UI)
      const docs = await api.getDocuments(projectId);
      // Ensure docs is an array
      setDocuments(Array.isArray(docs) ? docs : []);

      console.log('Documents reloaded after upload:', docs.length, 'documents');
    } catch (error) {
      console.error('Failed to reload documents:', error);
      // Still update documents to empty array on error to clear stale data
      setDocuments([]);
    }

    console.log('Upload completed:', uploadRecord);
  };

  // Load preview for selected document
  useEffect(() => {
    const loadPreview = async () => {
      if (!selectedDocument) {
        setPreviewContent(null);
        // Clean up previous PDF blob URL
        if (pdfBlobUrl) {
          URL.revokeObjectURL(pdfBlobUrl);
          setPdfBlobUrl(null);
        }
        return;
      }

      setPreviewLoading(true);
      try {
        const projectId = project.project_id || project.id;

        // For PDF files, load the file directly as blob for iframe viewing
        if (selectedDocument.content_type === "application/pdf") {
          const token = api.getToken();
          const response = await fetch(`/projects/${projectId}/documents/${selectedDocument.document_id}/download`, {
            headers: {
              'Authorization': token ? `Bearer ${token}` : '',
            },
          });

          if (!response.ok) {
            throw new Error('Failed to load PDF');
          }

          const blob = await response.blob();
          // Clean up previous blob URL
          if (pdfBlobUrl) {
            URL.revokeObjectURL(pdfBlobUrl);
          }
          const blobUrl = URL.createObjectURL(blob);
          setPdfBlobUrl(blobUrl);
          setPreviewContent({ preview_type: "pdf", blob_url: blobUrl });
        } else {
          // For other file types, use preview endpoint
          const preview = await api.getDocumentPreview(projectId, selectedDocument.document_id);
          setPreviewContent(preview);
        }
      } catch (error) {
        console.error('Failed to load preview:', error);
        setPreviewContent({ error: formatError(error) });
      } finally {
        setPreviewLoading(false);
      }
    };

    loadPreview();

    // Cleanup function to revoke blob URL when component unmounts or document changes
    return () => {
      if (pdfBlobUrl) {
        URL.revokeObjectURL(pdfBlobUrl);
        setPdfBlobUrl(null);
      }
    };
  }, [selectedDocument, project]); // Don't include pdfBlobUrl in dependencies to avoid infinite loop

  // Load versions for selected document
  const loadVersions = async (documentId, documentInfo = null) => {
    try {
      // Set flag to prevent accidental close during opening
      isOpeningVersions.current = true;

      setVersions([]); // Clear previous versions
      // Store document info for the modal (use provided info or selectedDocument)
      const docInfo = documentInfo || selectedDocument;
      if (!docInfo) {
        console.error('No document info provided for loadVersions');
        isOpeningVersions.current = false;
        return;
      }
      // Set document info and show modal first (with loading state)
      setVersionDocument(docInfo);
      setShowVersions(true);

      // Small delay to ensure modal is rendered before API call
      await new Promise(resolve => setTimeout(resolve, 50));

      const projectId = project.project_id || project.id;
      const versionData = await api.getDocumentVersions(projectId, documentId);
      console.log('Version data received:', versionData);

      if (versionData && versionData.versions && Array.isArray(versionData.versions)) {
        // Sort versions so that the newest logical version (by extracted_date or created_at)
        // appears first, and assign displayVersion numbers so that the latest is highest v.
        const sorted = [...versionData.versions].sort((a, b) => {
          const da = a.extracted_date ? new Date(a.extracted_date) : null;
          const db = b.extracted_date ? new Date(b.extracted_date) : null;
          if (da && db) return db - da;
          if (da && !db) return -1;
          if (!da && db) return 1;
          const ca = a.created_at ? new Date(a.created_at) : null;
          const cb = b.created_at ? new Date(b.created_at) : null;
          if (ca && cb) return cb - ca;
          return 0;
        });

        const total = sorted.length;
        const processed = sorted.map((v, idx) => ({
          ...v,
          // Latest (first row) will get highest version label
          displayVersion: `v${total - idx}`,
          is_latest_display: idx === 0 || v.is_latest,
        }));

        setVersions(processed);
        // Update versionDocument with filename from API if available
        if (versionData.filename) {
          setVersionDocument(prev => ({
            ...(prev || docInfo),
            filename: versionData.filename
          }));
        }
        if (versionData.versions.length === 0) {
          console.warn('Versions array is empty');
        }
      } else {
        setVersions([]);
        console.warn('No versions found or invalid response:', versionData);
      }

      // Clear flag after modal is fully loaded
      setTimeout(() => {
        isOpeningVersions.current = false;
      }, 200);
    } catch (error) {
      console.error('Failed to load versions:', error);
      setVersions([]);
      isOpeningVersions.current = false;
      // Don't close modal on error, show error message instead
      alert('Failed to load version history: ' + formatError(error));
    }
  };

  // Build folder structure from API documents (only latest versions)
  const buildFolderStructure = () => {
    const baseStructure = {
      id: "root",
      name: "/",
      files: [],
      folders: [
        {
          id: "Config",
          name: "Config",
          folders: [],
          files: [],
        },
      ],
    };

    // Merge custom folders into base structure
    // Find folder by ID in a specific location (not recursively - to avoid duplicates)
    const findFolderInLocation = (folders, id) => {
      return folders.find(f => f.id === id) || null;
    };

    // Find folder recursively in entire structure (for file placement)
    const findFolderInStructure = (folders, id) => {
      for (const folder of folders) {
        if (folder.id === id) return folder;
        if (folder.folders && folder.folders.length > 0) {
          const found = findFolderInStructure(folder.folders, id);
          if (found) return found;
        }
      }
      return null;
    };

    // Check if folder already exists anywhere in the structure
    const folderExists = (targetFolders, folderId) => {
      return findFolderInStructure(targetFolders, folderId) !== null;
    };

    // Helper function to ensure a folder exists in the structure at the correct location
    const ensureFolderExists = (targetFolders, folderId, folderName, parentId, customFolders, visited = new Set(), rootFolders = baseStructure.folders) => {
      if (visited.has(folderId)) return false;
      visited.add(folderId);
      // Treat "root" as root (null) so folders always place correctly
      const effectiveParentId = (parentId === "root" || parentId == null) ? null : parentId;

      const existingFolder = findFolderInStructure(rootFolders, folderId);

      if (effectiveParentId) {
        // Find parent folder - search in entire structure, not just targetFolders
        const parentFolder = findFolderInStructure(rootFolders, effectiveParentId);
        if (parentFolder) {
          if (!parentFolder.folders) {
            parentFolder.folders = [];
          }

          // Check if folder already exists in this parent
          const existingInParent = findFolderInLocation(parentFolder.folders, folderId);
          if (existingInParent) {
            return true; // Already exists in correct location
          }

          // If folder exists elsewhere, remove it first (it's in wrong location)
          if (existingFolder && existingFolder !== existingInParent) {
            // Remove from wrong location - search in entire structure
            const removeFromStructure = (folders, id) => {
              const index = folders.findIndex(f => f.id === id);
              if (index !== -1) {
                folders.splice(index, 1);
                return true;
              }
              for (const folder of folders) {
                if (folder.folders && removeFromStructure(folder.folders, id)) {
                  return true;
                }
              }
              return false;
            };
            removeFromStructure(rootFolders, folderId);
          }

          // Create folder in correct location
          parentFolder.folders.push({
            id: folderId,
            name: folderName,
            folders: [],
            files: [],
          });
          return true;
        } else {
          const parentCustomFolder = customFolders.find(f => f.id === effectiveParentId);
          if (parentCustomFolder) {
            let parentTargetFolders = targetFolders;
            const pp = parentCustomFolder.parentId;
            if (pp && pp !== "root") {
              const parentParent = findFolderInStructure(targetFolders, pp);
              if (parentParent) {
                if (!parentParent.folders) {
                  parentParent.folders = [];
                }
                parentTargetFolders = parentParent.folders;
              } else {
                // Parent's parent doesn't exist - can't create parent yet
                return false;
              }
            }

            // Recursively ensure parent exists in the correct location
            if (ensureFolderExists(parentTargetFolders, effectiveParentId, parentCustomFolder.name, parentCustomFolder.parentId, customFolders, visited, rootFolders)) {
              const parentFolderAfter = findFolderInStructure(targetFolders, effectiveParentId);
              if (parentFolderAfter) {
                if (!parentFolderAfter.folders) {
                  parentFolderAfter.folders = [];
                }
                // Check if folder already exists in this parent
                if (!findFolderInLocation(parentFolderAfter.folders, folderId)) {
                  // Remove from wrong location if exists
                  if (existingFolder) {
                    const removeFromStructure = (folders, id) => {
                      const index = folders.findIndex(f => f.id === id);
                      if (index !== -1) {
                        folders.splice(index, 1);
                        return true;
                      }
                      for (const folder of folders) {
                        if (folder.folders && removeFromStructure(folder.folders, id)) {
                          return true;
                        }
                      }
                      return false;
                    };
                    removeFromStructure(rootFolders, folderId);
                  }

                  parentFolderAfter.folders.push({
                    id: folderId,
                    name: folderName,
                    folders: [],
                    files: [],
                  });
                  return true;
                } else {
                  return true; // Already exists in correct location
                }
              }
            }
          }
          return false;
        }
      } else {
        // Add to root (parentId === null)
        // Check if folder already exists in root
        const existingInRoot = findFolderInLocation(targetFolders, folderId);
        if (existingInRoot) {
          // Update name if it changed (for rename operations)
          if (existingInRoot.name !== folderName) {
            existingInRoot.name = folderName;
          }
          return true; // Already exists in root
        }

        // If folder exists elsewhere, remove it first (it's in wrong location)
        // But be careful: only remove if it's NOT in rootFolders (baseStructure.folders)
        // to prevent accidentally removing root folders
        if (existingFolder) {
          // Check if it's in a nested location (not root)
          const isInRoot = findFolderInLocation(rootFolders, folderId) !== null;
          if (!isInRoot) {
            // Only remove if it's nested, not if it's already in root
            const removeFromStructure = (folders, id) => {
              const index = folders.findIndex(f => f.id === id);
              if (index !== -1) {
                folders.splice(index, 1);
                return true;
              }
              for (const folder of folders) {
                if (folder.folders && removeFromStructure(folder.folders, id)) {
                  return true;
                }
              }
              return false;
            };
            // Only remove from nested locations, preserve root folders
            for (const folder of rootFolders) {
              if (folder.folders && removeFromStructure(folder.folders, folderId)) {
                break;
              }
            }
          }
        }

        // Create folder in root (only if it doesn't exist)
        if (!findFolderInLocation(targetFolders, folderId)) {
          targetFolders.push({
            id: folderId,
            name: folderName,
            folders: [],
            files: [],
          });
        }
        return true;
      }
    };

    // Filter out deleted folders
    const activeCustomFolders = customFolders.filter(f => !f.deleted);

    const mergeCustomFolders = (targetFolders, customFolders, parentId = null, processed = new Set()) => {
      // Find all folders that belong to the current parent level (treat null/"root"/undefined as root)
      const isRootLevel = parentId == null || parentId === "root";
      const foldersForThisLevel = customFolders.filter(customFolder => {
        if (customFolder.id === "Config") return false;
        if (processed.has(customFolder.id)) return false;
        const folderParent = customFolder.parentId;
        if (isRootLevel) return folderParent == null || folderParent === "root";
        return folderParent === parentId;
      });

      // First pass: create all folders at this level
      foldersForThisLevel.forEach(customFolder => {
        if (!processed.has(customFolder.id)) {
          const created = ensureFolderExists(targetFolders, customFolder.id, customFolder.name, customFolder.parentId, customFolders, processed, baseStructure.folders);
          if (created) {
            processed.add(customFolder.id);
          }
        }
      });

      // Second pass: recursively merge nested folders for each folder at this level
      foldersForThisLevel.forEach(customFolder => {
        const targetFolder = findFolderInStructure(targetFolders, customFolder.id);
        if (targetFolder) {
          if (!targetFolder.folders) {
            targetFolder.folders = [];
          }
          mergeCustomFolders(targetFolder.folders, customFolders, customFolder.id, processed);
        }
      });
    };

    // Merge custom folders - use multiple passes to ensure parent folders are created first
    if (activeCustomFolders && activeCustomFolders.length > 0) {
      // Calculate depth for each folder (how many levels deep it is)
      const calculateDepth = (folderId, visited = new Set()) => {
        if (visited.has(folderId)) return 0;
        visited.add(folderId);
        const folder = activeCustomFolders.find(f => f.id === folderId);
        const pid = folder?.parentId;
        if (!folder || pid == null || pid === "root") return 0;
        return 1 + calculateDepth(pid, visited);
      };

      // Sort by depth: folders with no parent first, then nested ones by depth
      const sortedFolders = [...activeCustomFolders].sort((a, b) => {
        const depthA = calculateDepth(a.id);
        const depthB = calculateDepth(b.id);
        return depthA - depthB;
      });

      // Single pass merge with proper processing tracking
      // IMPORTANT: Always merge into baseStructure.folders to preserve Config folder
      // and ensure all root folders (parentId === null) are added correctly
      const processed = new Set();
      mergeCustomFolders(baseStructure.folders, sortedFolders, null, processed);

      // Ensure all root folders are present (parentId null/"root"/undefined; not Config)
      const rootFolders = activeCustomFolders.filter(f => (f.parentId == null || f.parentId === "root") && f.id !== "Config");
      rootFolders.forEach(rootFolder => {
        const exists = findFolderInStructure(baseStructure.folders, rootFolder.id);
        if (!exists) {
          // Add root folder if it doesn't exist
          baseStructure.folders.push({
            id: rootFolder.id,
            name: rootFolder.name,
            folders: [],
            files: [],
          });
        } else {
          // Update name if folder exists but name changed
          if (exists.name !== rootFolder.name) {
            exists.name = rootFolder.name;
          }
        }
      });
    }

    // Only show latest versions in file tree
    if (!Array.isArray(documents)) {
      return baseStructure;
    }

    const latestDocs = documents.filter(doc => doc && doc.is_latest);

    // Group documents by folder_id or type
    latestDocs.forEach(doc => {
      if (!doc || !doc.filename) return;

      const fileInfo = {
        name: doc.filename,
        size: doc.size,
        sizeFormatted: `${(doc.size / 1024).toFixed(1)} KB`,
        modified: doc.created_at,
        modifiedFormatted: formatDateTime(doc.created_at),
        document_id: doc.document_id,
        version: doc.version,
        is_latest: doc.is_latest,
        uploader: doc.uploader,
        content_type: doc.content_type,
        extension: doc.filename.split('.').pop() || '',
      };

      if (doc.folder_id) {
        // Find folder by ID recursively (supports nested folders)
        const folder = findFolderInStructure(baseStructure.folders, doc.folder_id);
        if (folder) {
          folder.files.push(fileInfo);
        } else {
          // Folder not found - add to root "Other" folder or create one
          let otherFolder = findFolderInStructure(baseStructure.folders, "Other");
          if (!otherFolder) {
            // Create "Other" folder in root
            baseStructure.folders.push({
              id: "Other",
              name: "Other",
              folders: [],
              files: []
            });
            otherFolder = findFolderInStructure(baseStructure.folders, "Other");
          }
          if (otherFolder) {
            otherFolder.files.push(fileInfo);
          }
        }
      } else {
        // No folder_id - add files directly to root (not to Other folder)
        // Files without folder_id should be in root, not automatically in Other
        if (!baseStructure.files) {
          baseStructure.files = [];
        }
        baseStructure.files.push(fileInfo);
      }
    });

    return baseStructure;
  };

  // Build folder structure with custom folders
  const folderStructure = useMemo(() => buildFolderStructure(), [documents, customFolders]);
  const tree = folderStructure;

  const onToggle = (id) => {
    const n = new Set(expanded);
    n.has(id) ? n.delete(id) : n.add(id);
    setExpanded(n);
  };

  // Find folder by ID in tree structure
  const findFolder = (node, id, parent = null) => {
    if (node.id === id) return { node, parent };
    if (node.folders) {
      for (const folder of node.folders) {
        const result = findFolder(folder, id, node);
        if (result) return result;
      }
    }
    return null;
  };

  // Handle folder actions
  const handleNewFolder = () => {
    setFolderAction("add");
    setFolderName("");
    setFolderParent(null);
    setShowFolderDialog(true);
  };

  const handleEditFolder = (folderId) => {
    // Only prevent editing Config folder
    if (folderId === "Config") {
      alert("Cannot edit the Config folder.");
      return;
    }
    const found = findFolder(tree, folderId);
    if (found) {
      setFolderAction("edit");
      setSelectedFolder(folderId);
      setFolderName(found.node.name);
      // Root folders have parent.id === "root" (virtual node); API expects parent_id null, not "root"
      const parentId = found.parent && found.parent.id !== "root" ? found.parent.id : null;
      setFolderParent(parentId);
      setShowFolderDialog(true);
    } else {
      alert("Folder not found.");
    }
  };

  const handleDeleteFolder = async (folderId) => {
    // Only prevent deleting Config folder and Other folder
    if (folderId === "Config" || folderId === "Other") {
      alert("Cannot delete this folder.");
      return;
    }
    const found = findFolder(tree, folderId);
    if (found) {
      showConfirmModal({
        title: "Delete Folder",
        message: `Are you sure you want to delete folder "${found.node.name}" and all files inside?`,
        confirmText: "Delete",
        variant: "danger",
        onConfirm: async () => {
          try {
            const projectId = project.project_id || project.id;
            await api.deleteFolder(projectId, folderId);
            // Reload folders from API
            const folders = await api.getFolders(projectId);
            const transformedFolders = folders.map(f => ({
              id: f.id,
              name: f.name,
              parentId: f.parent_id || null,
              deleted: f.deleted || false
            }));
            setCustomFolders(transformedFolders);
          } catch (error) {
            console.error('Failed to delete folder:', error);
            alert(`Failed to delete folder: ${formatError(error)}`);
          }
        }
      });
    }
  };

  const handleDownloadFolder = async (folderId) => {
    // Prevent downloading Config folder and Other folder
    if (folderId === "Config" || folderId === "Other") {
      alert("Cannot download this folder.");
      return;
    }

    try {
      const projectId = project.project_id || project.id;

      // Get folder name for the download filename
      const allFolders = [...customFolders, { id: "Config", name: "Config" }, { id: "Other", name: "Other" }];
      const folder = allFolders.find(f => f.id === folderId);
      const folderName = folder ? folder.name : "folder";

      // Download folder as ZIP
      const blob = await api.downloadFolder(projectId, folderId);

      // Create download link
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${folderName.replace(/[^a-zA-Z0-9]/g, '_')}_${new Date().toISOString().slice(0, 10)}.zip`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

    } catch (error) {
      console.error('Failed to download folder:', error);
      alert(`Failed to download folder: ${formatError(error)}`);
    }
  };

  const handleSaveFolder = async () => {
    if (!folderName.trim()) {
      alert("Please enter a folder name.");
      return;
    }

    // Prevent editing Config folder and Other folder
    if (folderAction === "edit" && selectedFolder) {
      if (selectedFolder === "Config" || selectedFolder === "Other") {
        alert("Cannot edit this folder.");
        return;
      }
    }

    try {
      const projectId = project.project_id || project.id;
      const renamedFolderId = selectedFolder; // Store folder ID before rename

      if (folderAction === "add") {
        // Prevent adding to Config folder
        if (folderParent === "Config" || folderParent === "Other") {
          alert("Cannot create a folder inside this folder.");
          return;
        }

        await api.createFolder(projectId, folderName.trim(), folderParent || null);
        alert("Folder created successfully.");

        // Reload folders from API
        const folders = await api.getFolders(projectId);
        const transformedFolders = (folders || []).map(f => ({
          id: f.id,
          name: f.name,
          parentId: (f.parent_id === "root" || f.parent_id == null) ? null : (f.parent_id || null),
          deleted: !!f.deleted
        }));
        setCustomFolders(transformedFolders);

        // Find the newly created folder and expand it and its parent
        const newFolder = transformedFolders.find(f => f.name === folderName.trim() && f.parentId === (folderParent || null));
        const newExpanded = new Set(expanded);
        if (newFolder?.id) {
          newExpanded.add(newFolder.id);
        }
        if (folderParent) {
          newExpanded.add(folderParent);
        }
        setExpanded(newExpanded);
      } else if (folderAction === "edit" && selectedFolder) {
        // API expects parent_id null for root; tree uses "root" as virtual parent id
        const parentIdForApi = (folderParent === "root" || folderParent === "") ? null : (folderParent || null);
        await api.updateFolder(projectId, selectedFolder, folderName.trim(), parentIdForApi);
        alert("Folder updated successfully.");

        // Reload folders from API (normalize parentId so root folders use null, not "root")
        const folders = await api.getFolders(projectId);
        const transformedFolders = (folders || []).map(f => ({
          id: f.id,
          name: f.name,
          parentId: (f.parent_id === "root" || f.parent_id == null) ? null : (f.parent_id || null),
          deleted: !!f.deleted
        }));
        setCustomFolders(transformedFolders);

        // Reload documents to ensure they're properly associated with renamed folder
        const docsResponse = await api.getDocuments(projectId);
        const docs = Array.isArray(docsResponse) ? docsResponse : (docsResponse?.documents || []);
        setDocuments(docs);

        // Keep the renamed folder expanded and ensure parent is expanded too
        const newExpanded = new Set(expanded);
        newExpanded.add(renamedFolderId); // Keep folder expanded after rename
        if (folderParent) {
          newExpanded.add(folderParent);
        }
        // Also expand parent folders recursively
        const findParentFolders = (folderId) => {
          const folder = transformedFolders.find(f => f.id === folderId);
          if (folder && folder.parentId) {
            newExpanded.add(folder.parentId);
            findParentFolders(folder.parentId);
          }
        };
        findParentFolders(renamedFolderId);
        setExpanded(newExpanded);
      }

      setShowFolderDialog(false);
      setFolderName("");
      setSelectedFolder(null);
      setFolderParent(null);
    } catch (error) {
      console.error('Failed to save folder:', error);
      alert(`Failed: ${formatError(error)}`);
    }
  };

  const handleEditFile = (file) => {
    // Check if file has document_id
    if (!file || !file.document_id) {
      console.error("File missing document_id:", file);
      alert("Cannot rename: File information is incomplete");
      return;
    }

    // Prevent renaming files in Config folder
    const doc = documents.find(d => d.document_id === file.document_id);
    if (doc && doc.folder_id === "Config") {
      alert("Cannot rename files in Config folder");
      return;
    }

    setFileToRename(file);
    setFileRenameName(file.name);
    setShowFileRenameDialog(true);
  };

  const handleSaveFileRename = async () => {
    if (!fileRenameName.trim()) {
      alert("Please enter a filename");
      return;
    }

    if (!fileToRename) {
      return;
    }

    try {
      const projectId = project.project_id || project.id;
      await api.renameDocument(projectId, fileToRename.document_id, fileRenameName.trim());
      alert("File renamed successfully");

      // Reload documents
      const docsResponse = await api.getDocuments(projectId);
      const docs = Array.isArray(docsResponse) ? docsResponse : (docsResponse?.documents || []);
      setDocuments(docs);

      // Update selected file if it was the renamed one
      if (selectedFile && selectedFile.document_id === fileToRename.document_id) {
        const updatedDoc = docs.find(d => d.document_id === fileToRename.document_id);
        if (updatedDoc) {
          setSelectedFile({ ...selectedFile, name: fileRenameName.trim() });
          setSelectedDocument(updatedDoc);
        }
      }

      setShowFileRenameDialog(false);
      setFileRenameName("");
      setFileToRename(null);
    } catch (error) {
      console.error('Failed to rename file:', error);
      alert(`Failed: ${formatError(error)}`);
    }
  };

  // Get all folders for parent selection
  const getAllFolders = (node, excludeId = null, path = []) => {
    let folders = [];

    // Skip root node - just process its children
    if (node.id === "root") {
      if (node.folders) {
        node.folders.forEach(folder => {
          folders = folders.concat(getAllFolders(folder, excludeId, []));
        });
      }
      return folders;
    }

    // Build current path - only add node.name if it's not already in path
    const currentPath = path.length > 0 ? [...path, node.name] : [node.name];

    // Add current folder if not excluded
    if (node.id !== excludeId) {
      folders.push({ id: node.id, name: node.name, path: currentPath });
    }

    // Recursively process child folders with updated path
    if (node.folders) {
      node.folders.forEach(folder => {
        folders = folders.concat(getAllFolders(folder, excludeId, currentPath));
      });
    }

    return folders;
  };

  const PreviewPane = (
    <Card
      title={
        <div className="text-sm font-semibold text-gray-700 dark:text-gray-200">
          {safeDisplay(selectedFile?.name) || "Preview"}
        </div>
      }
      actions={
        (() => {
          const doc = selectedDocument || (selectedFile?.document_id && documents?.find(d => d.document_id === selectedFile.document_id));
          if (!selectedFile || !doc) return null;
          return (
            <div className="flex gap-2 flex-wrap">
              {can("download-document", project) && (
                <Button
                  variant="secondary"
                  onClick={async () => {
                    try {
                      const projectId = project.project_id || project.id;
                      await api.downloadDocument(projectId, doc.document_id);
                    } catch (error) {
                      alert('Download failed: ' + formatError(error));
                    }
                  }}
                >
                  ⬇ Download
                </Button>
              )}
              <Button
                variant="secondary"
                onClick={(e) => {
                  e.stopPropagation();
                  loadVersions(doc.document_id, doc);
                }}
              >
                📜 Versions
              </Button>
              {doc.folder_id !== "Config" && (
                <Button
                  variant="secondary"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleEditFile(selectedFile);
                  }}
                >
                  ✏️ Rename
                </Button>
              )}
              {doc.folder_id !== "Config" && (
                <Button
                  variant="secondary"
                  onClick={(e) => {
                    e.stopPropagation();
                    setMoveFolderTarget(doc);
                    setMoveFolderId(doc.folder_id ?? '');
                    setShowMoveFolder(true);
                  }}
                >
                  📁 Move
                </Button>
              )}
              {doc.folder_id !== "Config" && can("delete-document", project) && (
                <Button
                  variant="danger"
                  onClick={(e) => {
                    e.stopPropagation();
                    const filename = doc.filename || selectedFile?.name;
                    showConfirmModal({
                      title: "Delete Document",
                      message: `Are you sure you want to delete "${filename}"?`,
                      confirmText: "Delete",
                      variant: "danger",
                      onConfirm: async () => {
                        try {
                          const projectId = project.project_id || project.id;
                          await api.deleteDocument(projectId, doc.document_id);
                          const docs = await api.getDocuments(projectId);
                          setDocuments(Array.isArray(docs) ? docs : []);
                          setSelectedFile(null);
                          setSelectedDocument(null);
                          setPreviewContent(null);
                        } catch (error) {
                          alert("Failed to delete document: " + formatError(error));
                        }
                      }
                    });
                  }}
                >
                  🗑️ Delete
                </Button>
              )}
            </div>
          );
        })()
      }
      className="flex-1 min-h-0 flex flex-col overflow-hidden"
    >
      <div className="flex-1 min-h-0 flex flex-col">
        {!selectedFile && (
          <div className="flex-1 flex items-center justify-center text-sm text-gray-500 dark:text-gray-400">
            <div className="text-center">
              <div className="text-4xl mb-3">📄</div>
              <div>Select a file to preview</div>
              <div className="text-xs mt-2 text-gray-400 dark:text-gray-500">Supported: .txt, .pdf, .png, .jpg</div>
            </div>
          </div>
        )}

        {previewLoading && (
          <div className="flex-1 flex items-center justify-center text-sm text-gray-500 dark:text-gray-400">
            <div className="text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-400 mx-auto mb-3"></div>
              <div>Loading preview...</div>
            </div>
          </div>
        )}

        {!previewLoading && previewContent && (
          <>
            {previewContent.error ? (
              <div className="flex-1 flex items-center justify-center p-4">
                <div className="text-center">
                  <div className="text-rose-500 dark:text-rose-400 text-lg mb-2">⚠️</div>
                  <div className="text-sm text-rose-500 dark:text-rose-400">
                    Error loading preview: {safeDisplay(previewContent.error)}
                  </div>
                </div>
              </div>
            ) : previewContent.preview_type === "text" ? (
              <div className="flex-1 min-h-0 overflow-y-auto overflow-x-auto rounded-lg border border-slate-300 dark:border-gray-700 p-4 bg-gray-50 dark:bg-[#0F172A]">
                <pre className="whitespace-pre-wrap text-sm leading-relaxed text-gray-800 dark:text-gray-200 font-mono">
                  {previewContent.preview_data || "(empty file)"}
                </pre>
              </div>
            ) : previewContent.preview_type === "image" ? (
              <div className="flex-1 min-h-0 overflow-y-auto overflow-x-auto flex items-center justify-center p-4 bg-gray-50 dark:bg-gray-900/50">
                <img
                  src={previewContent.preview_data}
                  alt={selectedFile?.name || "Preview"}
                  className="max-h-full max-w-full w-auto h-auto object-contain rounded-lg shadow-lg"
                  style={{
                    maxWidth: '100%',
                    maxHeight: '100%',
                    imageRendering: 'auto'
                  }}
                  loading="lazy"
                />
              </div>
            ) : previewContent.preview_type === "pdf" || previewContent.blob_url ? (
              previewContent.blob_url ? (
                <div className="flex-1 min-h-0 overflow-hidden rounded-lg border border-slate-300 dark:border-gray-700 bg-gray-50 dark:bg-gray-900">
                  <iframe
                    src={`${previewContent.blob_url}#toolbar=1&navpanes=1&scrollbar=1`}
                    className="w-full h-full"
                    title="PDF Preview"
                    type="application/pdf"
                  />
                </div>
              ) : (
                <div className="flex-1 flex items-center justify-center text-gray-500 dark:text-gray-300 border border-slate-300 dark:border-gray-700 rounded-lg">
                  <div className="text-center">
                    <div className="text-4xl mb-2">📄</div>
                    <div>{previewContent.preview_data || "PDF Preview"}</div>
                    <div className="text-sm mt-2">Click Download to view PDF</div>
                  </div>
                </div>
              )
            ) : (
              <div className="flex-1 flex items-center justify-center p-4">
                <div className="text-sm text-gray-500 dark:text-gray-400">
                  {previewContent.preview_data || "Preview not available"}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </Card>
  );


  // Early return if no project
  if (!project) {
    return (
      <div className="grid gap-4">
        <div className="text-sm text-rose-400">Project not found</div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col min-h-0 overflow-hidden">
      {/* Header - fixed height */}
      <div className="flex-shrink-0 flex items-center justify-between mb-4 px-1">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">Documents</h2>
        <div className="flex items-center gap-2 flex-wrap justify-end">
          <Button
            variant="secondary"
            onClick={() => {
              setLayout(layout === "side" ? "bottom" : "side");
              if (layout === "side") {
                setFilesPanelCollapsed(true);
              } else {
                setFilesPanelCollapsed(false);
              }
            }}
          >
            {layout === "side" ? "Preview Bottom" : "Preview Side"}
          </Button>
          {can("upload-config", project) && (
            <Button variant="secondary" onClick={() => setShowUploadConfig(true)}>
              Upload Config
            </Button>
          )}
          {can("upload-document", project) && (
            <Button variant="secondary" onClick={() => setShowUploadDocument(true)}>
              Upload Document
            </Button>
          )}
          {can("manage-folders", project) && (
            <>
              <Button variant="secondary" onClick={handleNewFolder}>New Folder</Button>
              {selectedFolder && (
                <>
                  <Button variant="secondary" onClick={() => handleEditFolder(selectedFolder)}>Rename</Button>
                  <Button variant="danger" onClick={() => handleDeleteFolder(selectedFolder)}>Delete</Button>
                </>
              )}
            </>
          )}
        </div>
      </div>

      {/* Content area - fills remaining space, no scroll */}
      <div className="flex-1 min-h-0 flex flex-col gap-4 overflow-hidden">
        {/* File Tree + Preview Section */}
        {layout === "side" ? (
          <div className="flex-1 min-h-0 flex gap-4 overflow-hidden" style={{ height: '100%' }}>
            <Card
              className={filesPanelCollapsed ? "w-12 flex-shrink-0 flex flex-col min-h-0 overflow-hidden" : "w-1/3 flex-shrink-0 flex flex-col min-h-0 overflow-hidden"}
              title={
                <div className={`flex ${filesPanelCollapsed ? 'items-center justify-center h-full' : 'items-center justify-between'} w-full`}>
                  {!filesPanelCollapsed && <span className="text-sm font-semibold">Files</span>}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setFilesPanelCollapsed(!filesPanelCollapsed);
                    }}
                    className={`${filesPanelCollapsed ? 'w-full h-full flex items-center justify-center p-0' : 'p-2'} hover:bg-gray-100 dark:hover:bg-gray-800 rounded transition-colors`}
                    title={filesPanelCollapsed ? "Expand" : "Collapse"}
                  >
                    {filesPanelCollapsed ? (
                      <span className="text-xl font-bold text-gray-600 dark:text-gray-300">▶</span>
                    ) : (
                      "◀"
                    )}
                  </button>
                </div>
              }
            >
              {!filesPanelCollapsed && (
                <div className="flex-1 min-h-0 overflow-y-auto overflow-x-hidden pr-2">
                  <FileTree2
                    node={tree}
                    expanded={expanded}
                    onToggle={onToggle}
                    onSelectFile={(f) => {
                      setSelectedFile(f);
                      setSelectedFolder(null);
                      // Find document from API
                      const doc = documents.find(d => d.document_id === f.document_id);
                      if (doc) {
                        setSelectedDocument(doc);
                      } else {
                        setSelectedDocument(null);
                      }
                    }}
                    onSelectFolder={(id, action) => {
                      if (action === "edit") {
                        handleEditFolder(id);
                      } else {
                        setSelectedFolder(id);
                        setSelectedFile(null);
                        setSelectedDocument(null);
                        setPreviewContent(null);
                      }
                    }}
                    onEditFile={handleEditFile}
                    selectedFile={selectedFile}
                    selectedFolder={selectedFolder}
                  />
                </div>
              )}
            </Card>
            <div className="flex-1 min-h-0 flex flex-col overflow-hidden">{safeChild(PreviewPane)}</div>
          </div>
        ) : (
          <div className="flex-1 min-h-0 flex flex-col gap-4 overflow-hidden">
            {/* File Tree on top when layout is bottom */}
            <Card
              className={`${filesPanelCollapsed ? "h-12" : "h-1/2"} flex-shrink-0 flex flex-col overflow-hidden transition-all duration-300`}
              title={
                <div className={`flex ${filesPanelCollapsed ? 'items-center justify-center' : 'items-center justify-between'} w-full`}>
                  {!filesPanelCollapsed && <span className="text-sm font-semibold">Files</span>}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setFilesPanelCollapsed(!filesPanelCollapsed);
                    }}
                    className={`${filesPanelCollapsed ? 'w-full h-full flex items-center justify-center p-0' : 'p-2'} hover:bg-gray-100 dark:hover:bg-gray-800 rounded transition-colors`}
                    title={filesPanelCollapsed ? "Expand" : "Collapse"}
                  >
                    {filesPanelCollapsed ? (
                      <span className="text-xl font-bold text-gray-600 dark:text-gray-300">▲</span>
                    ) : (
                      "▼"
                    )}
                  </button>
                </div>
              }
            >
              {!filesPanelCollapsed && (
                <div className="flex-1 min-h-0 overflow-y-auto overflow-x-hidden pr-2">
                  <FileTree2
                    node={tree}
                    expanded={expanded}
                    onToggle={onToggle}
                    onSelectFile={(f) => {
                      setSelectedFile(f);
                      setSelectedFolder(null);
                      // Find document from API
                      const doc = documents.find(d => d.document_id === f.document_id);
                      if (doc) {
                        setSelectedDocument(doc);
                      } else {
                        setSelectedDocument(null);
                      }
                    }}
                    onSelectFolder={(id, action) => {
                      if (action === "edit") {
                        handleEditFolder(id);
                      } else {
                        setSelectedFolder(id);
                        setSelectedFile(null);
                        setSelectedDocument(null);
                        setPreviewContent(null);
                      }
                    }}
                    onEditFile={handleEditFile}
                    selectedFile={selectedFile}
                    selectedFolder={selectedFolder}
                  />
                </div>
              )}
            </Card>
            {/* Preview at bottom when layout is bottom */}
            <div className="flex-1 min-h-0 flex flex-col overflow-hidden">{safeChild(PreviewPane)}</div>
          </div>
        )}
      </div>

      {/* Version History Modal */}
      {showVersions && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div
            className="absolute inset-0 bg-black/50"
            onClick={(e) => {
              e.stopPropagation();
              // Prevent closing during opening
              if (isOpeningVersions.current) {
                return;
              }
              setShowVersions(false);
              setVersionDocument(null);
            }}
          />
          <div
            className="relative z-10 w-full max-w-4xl"
            onClick={(e) => e.stopPropagation()}
          >
            <Card
              title={`Version History — ${versionDocument?.filename || selectedDocument?.filename || 'Unknown'}`}
              actions={<Button variant="secondary" onClick={() => {
                setShowVersions(false);
                setVersionDocument(null);
              }}>Close</Button>}
            >
              <div className="max-h-[70vh] overflow-auto">
                {versions.length === 0 ? (
                  <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                    No versions found for this document.
                  </div>
                ) : (
                  <Table
                    columns={[
                      { header: "Version", key: "version", cell: (v) => `${v.displayVersion || `v${v.version}`} ${v.is_latest_display ? '(Latest)' : ''}` },
                      { header: "Filename", key: "filename", cell: (v) => safeDisplay(v.filename) },
                      { header: "Uploaded By", key: "uploader", cell: (v) => v.uploader },
                      { header: "Uploaded At", key: "created_at", cell: (v) => formatDateTime(v.created_at) },
                      { header: "Size", key: "size", cell: (v) => `${(v.size / 1024).toFixed(1)} KB` },
                      {
                        header: "Actions",
                        key: "actions",
                        cell: (v) => (
                          <div className="flex gap-2">
                            <Button
                              variant="secondary"
                              size="sm"
                              onClick={async () => {
                                try {
                                  const projectId = project.project_id || project.id;
                                  const docId = versionDocument?.document_id || selectedDocument?.document_id;
                                  await api.downloadDocument(projectId, docId, v.version);
                                } catch (error) {
                                  alert('Download failed: ' + formatError(error));
                                }
                              }}
                            >
                              Download
                            </Button>
                          </div>
                        )
                      },
                    ]}
                    data={versions}
                  />
                )}
              </div>
            </Card>
          </div>
        </div>
      )}


      {/* Move Folder Dialog */}
      {showMoveFolder && moveFolderTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/50" onClick={() => setShowMoveFolder(false)} />
          <div className="relative z-10 w-full max-w-md">
            <Card
              title={`Move Document — ${moveFolderTarget.filename || ''}`}
              actions={<Button variant="secondary" onClick={() => setShowMoveFolder(false)}>Cancel</Button>}
            >
              <div className="space-y-4">
                <Field label="Move to Folder">
                  <Select
                    value={moveFolderId}
                    onChange={setMoveFolderId}
                    options={[
                      { value: "", label: "Root (No folder)" },
                      ...getAllFolders(folderStructure).map(f => ({
                        value: f.id,
                        label: f.path.join(' / ')
                      })).filter(f => f.value !== "Config" && f.value !== "Other") // Exclude Config and Other folders
                    ]}
                    placeholder="Select folder..."
                  />
                </Field>
                {moveFolderTarget?.folder_id === "Config" && (
                  <div className="text-sm text-red-500 dark:text-red-400">
                    ⚠️ Cannot move files out of the Config folder.
                  </div>
                )}
                {moveFolderId === "Config" && (
                  <div className="text-sm text-red-500 dark:text-red-400">
                    ⚠️ Cannot move files into the Config folder. Please use Upload Config instead.
                  </div>
                )}
                {moveFolderId === "Other" && (
                  <div className="text-sm text-red-500 dark:text-red-400">
                    ⚠️ Cannot move files into the Other folder. Other is a virtual folder for files with invalid folder_id.
                  </div>
                )}
                {moveFolderTarget?.folder_id === "Other" && (
                  <div className="text-sm text-slate-600 dark:text-slate-300">
                    ℹ️ This file is in the Other folder (virtual). You can move it to another folder or Root.
                  </div>
                )}
                <div className="flex gap-2 justify-end">
                  <Button
                    variant="secondary"
                    onClick={() => setShowMoveFolder(false)}
                  >
                    Cancel
                  </Button>
                  <Button
                    onClick={async () => {
                      try {
                        // Prevent moving to/from Config folder
                        if (moveFolderTarget?.folder_id === "Config") {
                          alert('Cannot move files out of the Config folder.');
                          return;
                        }
                        if (moveFolderId === "Config") {
                          alert('Cannot move files into the Config folder. Please use Upload Config instead.');
                          return;
                        }
                        // Prevent moving to Other folder (it's a virtual folder)
                        if (moveFolderId === "Other") {
                          alert('Cannot move files into the Other folder. Other is a virtual folder for files with invalid folder_id.');
                          return;
                        }

                        const projectId = project.project_id || project.id;
                        await api.moveDocumentFolder(projectId, moveFolderTarget.document_id, moveFolderId || null);
                        setShowMoveFolder(false);

                        // Reload documents to reflect the change
                        // Add a small delay to ensure backend has finished processing
                        setTimeout(async () => {
                          try {
                            const projectId2 = project.project_id || project.id;
                            const docs = await api.getDocuments(projectId2);
                            // api.getDocuments returns array directly, not {documents: [...]}
                            setDocuments(Array.isArray(docs) ? docs : []);
                            // Clear selected document since it may have moved
                            setSelectedDocument(null);
                            setSelectedFile(null);
                          } catch (error) {
                            console.error('Failed to reload documents after move:', error);
                            // Still reload to clear stale data
                            const projectId2 = project.project_id || project.id;
                            const docs = await api.getDocuments(projectId2);
                            setDocuments(Array.isArray(docs) ? docs : []);
                          }
                        }, 300);

                        alert('Document moved successfully');
                      } catch (error) {
                        alert('Failed to move document: ' + formatError(error));
                      }
                    }}
                  >
                    Move
                  </Button>
                </div>
              </div>
            </Card>
          </div>
        </div>
      )}

      {/* Upload Forms */}
      {showUploadConfig && (
        <UploadConfigForm
          project={project}
          authedUser={authedUser}
          onClose={() => setShowUploadConfig(false)}
          onUpload={handleUpload}
        />
      )}
      {showUploadDocument && (
        <UploadDocumentForm
          project={project}
          authedUser={authedUser}
          onClose={() => setShowUploadDocument(false)}
          onUpload={handleUpload}
          folderStructure={folderStructure}
        />
      )}

      {/* Folder Management Dialog */}
      {showFolderDialog && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-xl p-6 max-w-md w-full mx-4 shadow-xl">
            <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-gray-100">
              {folderAction === "add" ? "Create new folder" : "Rename folder"}
            </h3>
            <div className="space-y-4">
              {folderAction === "add" && (
                <Field label="Parent folder (optional)">
                  <Select
                    value={folderParent || ""}
                    onChange={(value) => setFolderParent(value || null)}
                    options={[
                      { value: "", label: "Root (top level)" },
                      ...getAllFolders(tree).map(f => ({
                        value: f.id,
                        label: f.path.join(" / ")
                      }))
                    ]}
                  />
                </Field>
              )}
              <Field label="Folder name">
                <Input
                  value={folderName}
                  onChange={(e) => setFolderName(e.target.value)}
                  placeholder="Enter folder name"
                  autoFocus
                />
              </Field>
            </div>
            <div className="flex gap-2 mt-6 justify-end">
              <Button variant="secondary" onClick={() => {
                setShowFolderDialog(false);
                setFolderName("");
                setSelectedFolder(null);
              }}>
                Cancel
              </Button>
              <Button variant="success" onClick={handleSaveFolder}>
                {folderAction === "add" ? "Create" : "Save"}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* File Rename Dialog */}
      {showFileRenameDialog && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-xl p-6 max-w-md w-full mx-4 shadow-xl">
            <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-gray-100">
              Rename File
            </h3>
            <div className="space-y-4">
              <Field label="Filename">
                <Input
                  value={fileRenameName}
                  onChange={(e) => setFileRenameName(e.target.value)}
                  placeholder="Enter filename"
                  autoFocus
                />
              </Field>
            </div>
            <div className="flex gap-2 mt-6 justify-end">
              <Button variant="secondary" onClick={() => {
                setShowFileRenameDialog(false);
                setFileRenameName("");
                setFileToRename(null);
              }}>
                Cancel
              </Button>
              <Button variant="success" onClick={handleSaveFileRename}>
                Save
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
const FileTree2 = ({
  node,
  depth = 0,
  expanded,
  onToggle,
  onSelectFile,
  onSelectFolder,
  onEditFile,
  selectedFile,
  selectedFolder,
  parentPath = [],
  isRoot = false,
  indentSize = 20,
}) => {
  const isRootNode = node.id === "root";

  const FolderRow = ({ folder, open, onSelectFolder }) => {
    const isSelected = selectedFolder === folder.id;
    const paddingLeft = isRootNode ? 8 : 8 + depth * indentSize;

    return (
      <div
        className={`flex items-center gap-2 py-1.5 cursor-pointer hover:bg-gray-100 dark:hover:bg-[#1A2231] ${isSelected ? "bg-slate-100/90 dark:bg-white/10 border-slate-300/80 dark:border-slate-600/80" : ""
          }`}
        style={{ paddingLeft: `${paddingLeft}px` }}
        onClick={(e) => {
          e.stopPropagation();
          if (e.detail === 2 && onSelectFolder) {
            // Double click to edit
            onSelectFolder(folder.id, "edit");
          } else {
            onToggle(folder.id);
            if (onSelectFolder) {
              onSelectFolder(folder.id, "select");
            }
          }
        }}
      >
        {/* Expand/collapse indicator */}
        <div className="flex items-center justify-center flex-shrink-0" style={{ width: '16px' }}>
          <span className="text-xs text-gray-500 dark:text-gray-400">
            {open ? "▼" : "▶"}
          </span>
        </div>
        <span className="text-sm flex-shrink-0">{open ? "📂" : "📁"}</span>
        <span className={`text-sm flex-1 min-w-0 truncate ${isSelected ? 'font-semibold text-slate-800 dark:text-slate-100' : 'font-medium'}`}>
          {folder.name}
        </span>
      </div>
    );
  };

  const FileRow = ({ f, onEditFile, onSelectFile }) => {
    const selected =
      selectedFile?.name === f.name &&
      JSON.stringify(selectedFile?.path) === JSON.stringify(f.path);
    const paddingLeft = isRootNode ? 8 : 8 + (depth + 1) * indentSize;

    // Build tooltip content
    const tooltipContent = [
      `Uploaded by: ${f.uploader || "Unknown"}`,
      `Uploaded at: ${f.modifiedFormatted || f.modified || "Unknown"}`,
      `Size: ${f.sizeFormatted || (f.size ? `${(f.size / 1024).toFixed(1)} KB` : "Unknown")}`,
      `Type: ${f.extension ? `.${f.extension}` : "Unknown"}`
    ].join('\n');

    return (
      <div
        className={`flex items-center py-1.5 cursor-pointer hover:bg-gray-100 dark:hover:bg-[#1A2231] relative group ${selected ? "bg-slate-100/90 dark:bg-white/10" : ""
          }`}
        style={{ paddingLeft: `${paddingLeft}px` }}
        onClick={() => {
          onSelectFile(f);
        }}
        onDoubleClick={(e) => {
          if (onEditFile) {
            e.stopPropagation();
            onEditFile(f);
          }
        }}
        title={tooltipContent}
      >
        {/* Spacer for alignment with folders */}
        <div className="flex items-center justify-center flex-shrink-0" style={{ width: '16px' }}>
          <span className="text-xs text-gray-400">•</span>
        </div>
        <div className="flex items-center gap-2 min-w-0 flex-1">
          <span className="text-sm flex-shrink-0">📄</span>
          <span className={`text-sm truncate ${selected ? 'font-semibold text-slate-800 dark:text-slate-100' : ''}`}>
            {f.name}
          </span>
        </div>
        {/* Tooltip on hover */}
        <div className="absolute left-0 top-full mt-1 z-50 hidden group-hover:block bg-gray-900 dark:bg-gray-800 text-white text-xs rounded-lg px-3 py-2 shadow-lg whitespace-pre-line pointer-events-none" style={{ minWidth: '200px' }}>
          {tooltipContent}
        </div>
      </div>
    );
  };

  return (
    <div>
      {isRootNode && node.files?.length > 0 && (
        <div>
          {node.files.map((f) => (
            <FileRow
              key={f.name}
              f={{ ...f, path: [...parentPath, f.name] }}
              onEditFile={onEditFile}
              onSelectFile={onSelectFile}
            />
          ))}
        </div>
      )}
      {node.folders?.map((folder) => {
        const open = expanded.has(folder.id);
        const current = [...parentPath, folder.name];

        return (
          <div key={folder.id}>
            <FolderRow
              folder={folder}
              open={open}
              onSelectFolder={onSelectFolder}
            />
            {open && (
              <div>
                {folder.files?.map((f) => (
                  <FileRow
                    key={f.name}
                    f={{ ...f, path: current, content: f.content }}
                    onEditFile={onEditFile}
                    onSelectFile={onSelectFile}
                  />
                ))}
                {folder.folders && folder.folders.length > 0 && (
                  <FileTree2
                    node={folder}
                    depth={depth + 1}
                    expanded={expanded}
                    onToggle={onToggle}
                    onSelectFile={onSelectFile}
                    onSelectFolder={onSelectFolder}
                    onEditFile={onEditFile}
                    selectedFile={selectedFile}
                    selectedFolder={selectedFolder}
                    parentPath={current}
                  />
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};

/* ========= COMMAND TEMPLATES ========= */
const CommandTemplatesPage = () => {
  const [selectedOS, setSelectedOS] = useState("cisco-ios");

  const commandTemplates = {
    "cisco-ios": {
      name: "Cisco IOS / IOS-XE / IOS-XR / NX-OS",
      commands: [
        {
          category: "System Information", commands: [
            "show version",
            "show inventory",
            "show running-config",
            "show startup-config",
            "show clock",
            "show uptime"
          ]
        },
        {
          category: "Interfaces", commands: [
            "show interfaces",
            "show interfaces status",
            "show interfaces description",
            "show ip interface brief",
            "show interfaces counters",
            "show interfaces transceiver",
            "show interfaces switchport"
          ]
        },
        {
          category: "VLAN", commands: [
            "show vlan",
            "show vlan brief",
            "show vlan id <vlan-id>",
            "show interfaces trunk"
          ]
        },
        {
          category: "Spanning Tree", commands: [
            "show spanning-tree",
            "show spanning-tree summary",
            "show spanning-tree detail",
            "show spanning-tree root"
          ]
        },
        {
          category: "Routing", commands: [
            "show ip route",
            "show ip route summary",
            "show ip ospf neighbor",
            "show ip ospf database",
            "show ip bgp summary",
            "show ip bgp neighbors",
            "show ip protocols"
          ]
        },
        {
          category: "HSRP/VRRP", commands: [
            "show standby",
            "show standby brief",
            "show vrrp",
            "show vrrp brief"
          ]
        },
        {
          category: "Security", commands: [
            "show port-security",
            "show ip arp inspection",
            "show dhcp snooping",
            "show access-lists"
          ]
        },
        {
          category: "Management", commands: [
            "show snmp",
            "show ntp status",
            "show logging",
            "show users"
          ]
        }
      ]
    },
    "huawei-vrp": {
      name: "Huawei VRP",
      commands: [
        {
          category: "System Information", commands: [
            "display version",
            "display device",
            "display current-configuration",
            "display saved-configuration",
            "display clock",
            "display cpu-usage"
          ]
        },
        {
          category: "Interfaces", commands: [
            "display interface",
            "display interface brief",
            "display ip interface",
            "display interface description",
            "display interface counters"
          ]
        },
        {
          category: "VLAN", commands: [
            "display vlan",
            "display vlan all",
            "display port vlan",
            "display port trunk"
          ]
        },
        {
          category: "Spanning Tree", commands: [
            "display stp",
            "display stp brief",
            "display stp root",
            "display stp region-configuration"
          ]
        },
        {
          category: "Routing", commands: [
            "display ip routing-table",
            "display ospf peer",
            "display ospf lsdb",
            "display bgp peer",
            "display ip routing-table protocol ospf"
          ]
        },
        {
          category: "VRRP", commands: [
            "display vrrp",
            "display vrrp brief",
            "display vrrp statistics"
          ]
        },
        {
          category: "Security", commands: [
            "display port-security",
            "display dhcp snooping",
            "display acl all"
          ]
        },
        {
          category: "Management", commands: [
            "display snmp-agent sys-info",
            "display ntp-service status",
            "display logbuffer",
            "display users"
          ]
        }
      ]
    },
    "h3c-comware": {
      name: "H3C Comware",
      commands: [
        {
          category: "System Information", commands: [
            "display version",
            "display device",
            "display current-configuration",
            "display saved-configuration",
            "display clock",
            "display cpu-usage"
          ]
        },
        {
          category: "Interfaces", commands: [
            "display interface",
            "display interface brief",
            "display ip interface",
            "display interface description",
            "display interface counters"
          ]
        },
        {
          category: "VLAN", commands: [
            "display vlan",
            "display vlan all",
            "display port vlan",
            "display port trunk"
          ]
        },
        {
          category: "Spanning Tree", commands: [
            "display stp",
            "display stp brief",
            "display stp root",
            "display stp region-configuration"
          ]
        },
        {
          category: "Routing", commands: [
            "display ip routing-table",
            "display ospf peer",
            "display ospf lsdb",
            "display bgp peer",
            "display ip routing-table protocol ospf"
          ]
        },
        {
          category: "VRRP", commands: [
            "display vrrp",
            "display vrrp brief",
            "display vrrp statistics"
          ]
        },
        {
          category: "Security", commands: [
            "display port-security",
            "display dhcp snooping",
            "display acl all"
          ]
        },
        {
          category: "Management", commands: [
            "display snmp-agent sys-info",
            "display ntp-service status",
            "display logbuffer",
            "display users"
          ]
        }
      ]
    },
    "juniper-junos": {
      name: "Juniper JunOS",
      commands: [
        {
          category: "System Information", commands: [
            "show version",
            "show chassis hardware",
            "show configuration",
            "show system uptime",
            "show system information"
          ]
        },
        {
          category: "Interfaces", commands: [
            "show interfaces",
            "show interfaces terse",
            "show interfaces detail",
            "show interfaces descriptions",
            "show interfaces statistics"
          ]
        },
        {
          category: "VLAN", commands: [
            "show vlans",
            "show vlans extensive",
            "show ethernet-switching table"
          ]
        },
        {
          category: "Spanning Tree", commands: [
            "show spanning-tree bridge",
            "show spanning-tree interface",
            "show spanning-tree statistics"
          ]
        },
        {
          category: "Routing", commands: [
            "show route",
            "show route summary",
            "show ospf neighbor",
            "show ospf database",
            "show bgp summary",
            "show bgp neighbor",
            "show route protocol ospf"
          ]
        },
        {
          category: "VRRP", commands: [
            "show vrrp",
            "show vrrp extensive",
            "show vrrp statistics"
          ]
        },
        {
          category: "Security", commands: [
            "show security",
            "show firewall",
            "show access-lists"
          ]
        },
        {
          category: "Management", commands: [
            "show snmp",
            "show ntp",
            "show log",
            "show system users"
          ]
        }
      ]
    },
    "arista-eos": {
      name: "Arista EOS",
      commands: [
        {
          category: "System Information", commands: [
            "show version",
            "show inventory",
            "show running-config",
            "show startup-config",
            "show clock",
            "show uptime"
          ]
        },
        {
          category: "Interfaces", commands: [
            "show interfaces",
            "show interfaces status",
            "show interfaces description",
            "show ip interface brief",
            "show interfaces counters",
            "show interfaces transceiver"
          ]
        },
        {
          category: "VLAN", commands: [
            "show vlan",
            "show vlan brief",
            "show vlan id <vlan-id>",
            "show interfaces trunk"
          ]
        },
        {
          category: "Spanning Tree", commands: [
            "show spanning-tree",
            "show spanning-tree summary",
            "show spanning-tree detail",
            "show spanning-tree root"
          ]
        },
        {
          category: "Routing", commands: [
            "show ip route",
            "show ip route summary",
            "show ip ospf neighbor",
            "show ip ospf database",
            "show ip bgp summary",
            "show ip bgp neighbors",
            "show ip protocols"
          ]
        },
        {
          category: "VRRP", commands: [
            "show vrrp",
            "show vrrp brief",
            "show vrrp statistics"
          ]
        },
        {
          category: "Security", commands: [
            "show port-security",
            "show ip arp inspection",
            "show dhcp snooping",
            "show access-lists"
          ]
        },
        {
          category: "Management", commands: [
            "show snmp",
            "show ntp status",
            "show logging",
            "show users"
          ]
        }
      ]
    }
  };

  const osOptions = [
    { value: "cisco-ios", label: "Cisco IOS / IOS-XE / IOS-XR / NX-OS" },
    { value: "huawei-vrp", label: "Huawei VRP" },
    { value: "h3c-comware", label: "H3C Comware" },
    { value: "juniper-junos", label: "Juniper JunOS" },
    { value: "arista-eos", label: "Arista EOS" }
  ];

  const currentTemplates = commandTemplates[selectedOS];

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text).then(() => {
      alert("Copied to clipboard!");
    });
  };

  return (
    <div className="grid gap-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Command Templates</h2>
      </div>

      <Card>
        <div className="grid gap-4">
          <Field label="Select Network OS">
            <Select
              value={selectedOS}
              onChange={setSelectedOS}
              options={osOptions}
            />
          </Field>
        </div>
      </Card>

      <Card title={currentTemplates.name}>
        <div className="grid gap-6">
          {currentTemplates.commands.map((category, idx) => (
            <div key={idx} className="border-b border-slate-300 dark:border-[#1F2937] pb-4 last:border-0">
              <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
                {category.category}
              </h3>
              <div className="grid gap-2">
                {category.commands.map((cmd, cmdIdx) => (
                  <div
                    key={cmdIdx}
                    className="flex items-center justify-between p-3 bg-gray-50 dark:bg-[#0F172A] rounded-lg border border-slate-300 dark:border-[#1F2937] hover:bg-gray-100 dark:hover:bg-[#1A2231] transition"
                  >
                    <code className="text-sm text-gray-800 dark:text-gray-200 font-mono">
                      {cmd}
                    </code>
                    <Button
                      variant="ghost"
                      className="text-xs px-3 py-1"
                      onClick={() => copyToClipboard(cmd)}
                    >
                      📋 Copy
                    </Button>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
};

/* ========= LOGS ========= */
const LogsPage = ({ project, uploadHistory }) => {
  const [searchLog, setSearchLog] = useState("");
  const [filterLogWho, setFilterLogWho] = useState("all");
  const [filterLogWhat, setFilterLogWhat] = useState("all");

  // Combine project logs with upload history
  const allHistory = [
    ...(project.logs || []).map(log => ({
      time: log.time,
      files: log.target,
      who: log.user,
      what: log.action,
      where: '—',
      when: '—',
      why: '—',
      description: '—',
      type: 'log',
      details: null,
      uploadRecord: null
    })),
    ...(uploadHistory || []).filter(upload => upload.project === project.id).map(upload => ({
      time: formatDateTime(upload.timestamp),
      files: upload.files.map(f => f.name).join(', '),
      who: upload.details?.who || upload.user,
      what: upload.details?.what || '',
      where: upload.details?.where || '',
      when: upload.details?.when || '',
      why: upload.details?.why || '',
      description: upload.details?.description || '',
      type: 'upload',
      details: upload.details,
      uploadRecord: upload
    }))
  ].sort((a, b) => new Date(b.time) - new Date(a.time));

  const uniqueLogWhos = [...new Set(allHistory.map(h => h.who))];
  const uniqueLogWhats = [...new Set(allHistory.map(h => h.what))];

  const combinedHistory = useMemo(() => {
    return allHistory.filter(log => {
      const matchSearch = !searchLog.trim() ||
        [log.files, log.who, log.what, log.where, log.description].some(v =>
          (v || "").toLowerCase().includes(searchLog.toLowerCase())
        );
      const matchWho = filterLogWho === "all" || log.who === filterLogWho;
      const matchWhat = filterLogWhat === "all" || log.what === filterLogWhat;
      return matchSearch && matchWho && matchWhat;
    });
  }, [allHistory, searchLog, filterLogWho, filterLogWhat]);

  const exportCSV = () => {
    const headers = ["Time", "Name", "Who", "What", "Where", "When", "Why", "Description"];
    const rows = combinedHistory.map(r =>
      [r.time, r.files, r.who, r.what, r.where, r.when, r.why, r.description]
        .map(v => `"${(v || "").toString().replaceAll('"', '""')}"`).join(",")
    );
    downloadCSV([headers.join(","), ...rows].join("\n"), `logs_${safeDisplay(project?.name)}.csv`);
  };

  return (
    <div className="grid gap-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Log Updates</h2>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={exportCSV}>Export CSV</Button>
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
        <Input
          placeholder="Search (filename, user, description...)"
          value={searchLog}
          onChange={(e) => setSearchLog(e.target.value)}
        />
        <Select
          value={filterLogWho}
          onChange={setFilterLogWho}
          options={[{ value: "all", label: "All (Responsible User)" }, ...uniqueLogWhos.map(w => ({ value: w, label: w }))]}
        />
        <Select
          value={filterLogWhat}
          onChange={setFilterLogWhat}
          options={[{ value: "all", label: "All (Activity Type)" }, ...uniqueLogWhats.map(w => ({ value: w, label: w }))]}
        />
      </div>
      <Table
        columns={[
          { header: "Time", key: "time" },
          { header: "Name", key: "files" },
          { header: "Responsible User", key: "who" },
          { header: "Activity Type", key: "what" },
          { header: "Site", key: "where" },
          { header: "Operational Timing", key: "when" },
          { header: "Purpose", key: "why" },
          { header: "Description", key: "description" },
          {
            header: "Action",
            key: "act",
            cell: (r) => (
              r.type === 'upload' && r.uploadRecord?.files?.[0] ? (
                <div className="flex gap-2">
                  <Button
                    variant="secondary"
                    onClick={() => {
                      const file = r.uploadRecord.files[0];
                      if (!file) return;
                      const blob = new Blob(
                        [file.content || `# ${r.uploadRecord.type === 'config' ? 'Configuration' : 'Document'} Backup\n# File: ${file.name}\n# Uploaded: ${r.time}\n# User: ${r.who}\n\nContent not available. Download from Documents if needed.`],
                        { type: file.type || (r.uploadRecord.type === 'config' ? "text/plain;charset=utf-8" : "application/octet-stream") }
                      );
                      const url = URL.createObjectURL(blob);
                      const a = document.createElement("a");
                      a.href = url;
                      a.download = file.name || "file";
                      document.body.appendChild(a);
                      a.click();
                      a.remove();
                      URL.revokeObjectURL(url);
                    }}
                  >
                    ⬇ Download
                  </Button>
                </div>
              ) : "—"
            ),
          },
        ]}
        data={combinedHistory}
        empty="No logs yet"
      />
    </div>
  );
};

/* ========= HELPERS ========= */
function downloadCSV(csv, filename) {
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
/* ===== Helpers for Overview Drift (UI only) ===== */
function getComparePair(project, device) {
  const hits = (project.documents?.config || [])
    .filter(f => f.name.toLowerCase().includes(device.replace(/-/g, "_")))
    .sort((a, b) => (b.modified || "").localeCompare(a.modified || ""));

  if (hits.length >= 2) return [hits[1].name, hits[0].name]; // older -> newer
  return ["—", "—"];
}

function getDriftLines(device) {
  return ["No config changes detected"];
}
/* ===== Topology helpers & Graph (no extra libs) ===== */



// 2) Simple SVG graph (circular layout)
const TopoGraph = ({ nodes = [], links = [], getNodeTooltip, onNodeClick }) => {
  const size = { w: 780, h: 420 };
  const R = Math.min(size.w, size.h) * 0.36;
  const cx = size.w / 2, cy = size.h / 2;

  // Layout: first node (if role=Core) at center, rest around circle
  const coreIdx = nodes.findIndex(n => n.role === "Core");
  const ordered = coreIdx >= 0 ? [nodes[coreIdx], ...nodes.filter((_, i) => i !== coreIdx)] : nodes;
  const positions = {};
  ordered.forEach((n, i) => {
    if (i === 0 && n.role === "Core") {
      positions[n.id] = { x: cx, y: cy };
    } else {
      const k = (i - (ordered[0]?.role === "Core" ? 1 : 0));
      const theta = (2 * Math.PI * k) / Math.max(1, (ordered.length - (ordered[0]?.role === "Core" ? 1 : 0)));
      positions[n.id] = { x: cx + R * Math.cos(theta), y: cy + R * Math.sin(theta) };
    }
  });

  // Node color by role
  const colorByRole = (role) =>
    role === "Core" ? "#2563eb" : role === "Distribution" ? "#16a34a" : "#f59e0b";

  // tooltip state
  const [tip, setTip] = useState(null); // {x,y,text}

  return (
    <div className="relative">
      <svg viewBox={`0 0 ${size.w} ${size.h}`} className="w-full h-[360px]">
        {/* edges */}
        {links.map((l, i) => {
          const a = positions[l.source], b = positions[l.target];
          if (!a || !b) return null;
          return (
            <g key={i}>
              <line x1={a.x} y1={a.y} x2={b.x} y2={b.y}
                stroke={l.type === "uplink" ? "#94a3b8" : "#cbd5e1"}
                strokeWidth={l.type === "uplink" ? 2.5 : 1.5}
                strokeDasharray={l.type === "uplink" ? "0" : "4 3"}
              />
            </g>
          );
        })}

        {/* nodes */}
        {ordered.map((n) => {
          const p = positions[n.id];
          return (
            <g key={n.id} transform={`translate(${p.x},${p.y})`}
              onMouseEnter={(e) => {
                const rect = e.currentTarget.ownerSVGElement.getBoundingClientRect();
                setTip({
                  x: (p.x / size.w) * rect.width,
                  y: (p.y / size.h) * rect.height,
                  text: getNodeTooltip ? getNodeTooltip(n.id) : n.id
                });
              }}
              onMouseLeave={() => setTip(null)}
              onClick={() => onNodeClick && onNodeClick(n.id)}
              style={{ cursor: "pointer" }}
            >
              <circle r={18} fill={colorByRole(n.role)} stroke="#0b1220" strokeWidth="2"></circle>
              <text y={34} textAnchor="middle" fontSize="11" fill="#cbd5e1">{n.id}</text>
            </g>
          );
        })}
      </svg>

      {/* tooltip */}
      {tip && (
        <div
          className="absolute z-10 text-xs bg-[#0F172A] text-gray-100 border border-[#1F2937] rounded-lg p-2 whitespace-pre"
          style={{ left: tip.x + 8, top: tip.y + 8, pointerEvents: "none", maxWidth: 360 }}
        >
          {tip.text}
        </div>
      )}
    </div>
  );
};







/** Rule-based fallback edges from summary (core/dist/access). */


/* ===== Device Image Upload Component ===== */
const DeviceImageUpload = ({ project, deviceName, authedUser, setProjects, can: canProp, showConfirmModal }) => {
  const [imageUrl, setImageUrl] = React.useState(null);
  const [uploading, setUploading] = React.useState(false);
  const [error, setError] = React.useState(null);
  const fileInputRef = React.useRef(null);

  // Check if user can edit (admin, manager, or engineer — viewer is read-only)
  const can = typeof canProp === "function" ? canProp : () => false;
  const canEdit = can("upload-config", project);

  // Load existing image from project state or API
  React.useEffect(() => {
    const loadImage = async () => {
      try {
        const projectId = project?.project_id || project?.id;
        // First try to get from project state (device_images)
        const deviceImages = project?.device_images || {};
        if (deviceImages[deviceName]) {
          // Check if it's PNG or JPEG based on data format
          const imageData = deviceImages[deviceName];
          const imageFormat = imageData.startsWith('/9j/') ? 'jpeg' : 'png';
          setImageUrl(`data:image/${imageFormat};base64,${imageData}`);
          return;
        }

        // If not in project state, try to fetch from API
        try {
          const result = await api.getDeviceImage(projectId, deviceName);
          if (result.image) {
            // Check if it's PNG or JPEG based on data format
            const imageData = result.image;
            const imageFormat = imageData.startsWith('/9j/') ? 'jpeg' : 'png';
            setImageUrl(`data:image/${imageFormat};base64,${imageData}`);
            // Update project state with fetched image
            if (setProjects) {
              setProjects(prev => prev.map(p => {
                const pId = p.project_id || p.id;
                if (pId === projectId) {
                  const updatedDeviceImages = { ...(p.device_images || {}), [deviceName]: result.image };
                  return { ...p, device_images: updatedDeviceImages };
                }
                return p;
              }));
            }
          }
        } catch (apiErr) {
          // Image not found in API, that's okay
          if (apiErr.message && !apiErr.message.includes("404")) {
            console.error("Failed to load device image from API:", apiErr);
          }
        }
      } catch (err) {
        console.error("Failed to load device image:", err);
      }
    };
    loadImage();
  }, [project, deviceName, setProjects]);

  const handleFileSelect = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith("image/")) {
      setError("Please select an image file");
      return;
    }

    setUploading(true);
    setError(null);

    try {
      const projectId = project?.project_id || project?.id;
      await api.uploadDeviceImage(projectId, deviceName, file);

      // Reload image from API
      const result = await api.getDeviceImage(projectId, deviceName);
      // Check if it's PNG or JPEG based on data format
      const imageData = result.image;
      const imageFormat = imageData.startsWith('/9j/') ? 'jpeg' : 'png';
      const newImageUrl = `data:image/${imageFormat};base64,${imageData}`;
      setImageUrl(newImageUrl);

      // Update project state with new device_images
      if (setProjects) {
        setProjects(prev => prev.map(p => {
          const pId = p.project_id || p.id;
          if (pId === projectId) {
            const deviceImages = p.device_images || {};
            return {
              ...p,
              device_images: {
                ...deviceImages,
                [deviceName]: result.image
              }
            };
          }
          return p;
        }));
      }
    } catch (err) {
      console.error("Upload failed:", err);
      setError(formatError(err) || "Failed to upload image");
    } finally {
      setUploading(false);
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleDelete = () => {
    showConfirmModal({
      title: "Delete Device Image",
      message: `Are you sure you want to delete the image for "${deviceName}"?`,
      confirmText: "Delete",
      variant: "danger",
      onConfirm: async () => {
        try {
          const projectId = project?.project_id || project?.id;
          await api.deleteDeviceImage(projectId, deviceName);
          setImageUrl(null);

          // Update project state to remove device image
          if (setProjects) {
            setProjects(prev => prev.map(p => {
              const pId = p.project_id || p.id;
              if (pId === projectId) {
                const deviceImages = { ...(p.device_images || {}) };
                delete deviceImages[deviceName];
                return {
                  ...p,
                  device_images: deviceImages
                };
              }
              return p;
            }));
          }
        } catch (err) {
          console.error("Delete failed:", err);
          setError(formatError(err) || "Failed to delete image");
        }
      }
    });
  };

  return (
    <div className="flex flex-col h-full min-h-0">
      {/* Single header: "Device Image" (left) + Upload/Delete (right) */}
      {canEdit && (
        <div className="flex-shrink-0 flex items-center justify-between gap-2 pb-2 border-b border-slate-300 dark:border-slate-700/80 px-1">
          <span className="text-sm font-semibold text-slate-800 dark:text-slate-200">Device Image</span>
          <div className="flex gap-2">
            <Button
              variant="secondary"
              size="sm"
              className="text-xs"
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
            >
              {uploading ? "Uploading..." : imageUrl ? "Change Image" : "Upload Image"}
            </Button>
            {imageUrl && (
              <Button
                variant="secondary"
                size="sm"
                className="text-xs"
                onClick={handleDelete}
                disabled={uploading}
              >
                Delete Image
              </Button>
            )}
          </div>
        </div>
      )}
      {!canEdit && (
        <div className="flex-shrink-0 flex items-center justify-between gap-2 pb-2 border-b border-slate-300 dark:border-slate-700/80 px-1">
          <span className="text-sm font-semibold text-slate-800 dark:text-slate-200">Device Image</span>
        </div>
      )}
      {/* Full area for device image display */}
      <div className="flex-1 min-h-[160px] flex items-center justify-center rounded-xl border border-slate-300 dark:border-slate-700/60 bg-slate-100 dark:bg-slate-800/40 mt-2 overflow-hidden">
        {imageUrl ? (
          <img
            src={imageUrl}
            alt={`${deviceName} device`}
            className="max-w-full max-h-full w-full h-full object-contain"
          />
        ) : (
          <div className="flex flex-col items-center justify-center gap-2 text-slate-700 dark:text-slate-500">
            <span className="text-sm font-semibold">No image</span>
            <span className="text-xs max-w-[200px] text-center font-medium">
              Upload 600×600px PNG for topology icon
            </span>
          </div>
        )}
      </div>
      {error && (
        <div className="flex-shrink-0 text-xs text-rose-400 mt-2">{safeDisplay(error)}</div>
      )}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        onChange={handleFileSelect}
        className="hidden"
      />
    </div>
  );
};

/* ===== Network Device Icon Component ===== */
const NetworkDeviceIcon = ({ role, isSelected, isLinkStart, size = 8, imageUrl = null }) => {
  // If image is provided, show image instead of SVG icon
  if (imageUrl) {
    // Make image much larger - 8x the base size for much better visibility
    const imageSize = size * 8;
    return (
      <g>
        {/* Display image directly - no background, no clipPath, preserves transparency */}
        <image
          href={imageUrl}
          x={-imageSize / 2}
          y={-imageSize / 2}
          width={imageSize}
          height={imageSize}
          preserveAspectRatio="xMidYMid meet"
          opacity={isSelected || isLinkStart ? 1 : 0.95}
          style={{ imageRendering: 'auto' }}
        />
        {/* Border highlight when selected - only border, no background fill */}
        {(isSelected || isLinkStart) && (
          <rect
            x={-imageSize / 2 - 1}
            y={-imageSize / 2 - 1}
            width={imageSize + 2}
            height={imageSize + 2}
            fill="none"
            stroke={isLinkStart ? "#10b981" : "#3b82f6"}
            strokeWidth="0.8"
            rx="3"
          />
        )}
      </g>
    );
  }

  // Fallback to SVG icon if no image
  const baseColor = isLinkStart ? "#10b981" : isSelected ? "#3b82f6" : "#F59E0B";
  const strokeColor = isSelected || isLinkStart ? "#ffffff" : "#0B1220";
  const strokeWidth = isSelected || isLinkStart ? "1.5" : "0.5";

  // Router shape (for core)
  if (role === "core") {
    return (
      <g>
        {/* Router body */}
        <rect x={-size} y={-size * 0.6} width={size * 2} height={size * 1.2} rx={size * 0.2}
          fill={baseColor} stroke={strokeColor} strokeWidth={strokeWidth} />
        {/* Antenna lines */}
        <line x1={-size * 0.8} y1={-size * 0.6} x2={-size * 0.8} y2={-size * 0.9}
          stroke={strokeColor} strokeWidth={strokeWidth * 0.7} />
        <line x1={size * 0.8} y1={-size * 0.6} x2={size * 0.8} y2={-size * 0.9}
          stroke={strokeColor} strokeWidth={strokeWidth * 0.7} />
        {/* Port indicators */}
        <circle cx={-size * 0.5} cy={size * 0.3} r={size * 0.15} fill={strokeColor} />
        <circle cx={0} cy={size * 0.3} r={size * 0.15} fill={strokeColor} />
        <circle cx={size * 0.5} cy={size * 0.3} r={size * 0.15} fill={strokeColor} />
      </g>
    );
  }

  // Switch shape (for distribution/access)
  return (
    <g>
      {/* Switch body */}
      <rect x={-size} y={-size * 0.5} width={size * 2} height={size} rx={size * 0.15}
        fill={baseColor} stroke={strokeColor} strokeWidth={strokeWidth} />
      {/* Port rows */}
      <line x1={-size * 0.7} y1={-size * 0.2} x2={size * 0.7} y2={-size * 0.2}
        stroke={strokeColor} strokeWidth={strokeWidth * 0.5} />
      <line x1={-size * 0.7} y1={0} x2={size * 0.7} y2={0}
        stroke={strokeColor} strokeWidth={strokeWidth * 0.5} />
      <line x1={-size * 0.7} y1={size * 0.2} x2={size * 0.7} y2={size * 0.2}
        stroke={strokeColor} strokeWidth={strokeWidth * 0.5} />
      {/* Status indicator */}
      <circle cx={size * 0.6} cy={-size * 0.3} r={size * 0.2} fill={strokeColor} />
    </g>
  );
};

/* ===== Infer role from name (core/distribution/access) ===== */
function classifyRoleByName(name = "") {
  const n = (name || "").toLowerCase();
  if (n.includes("core")) return "core";
  if (n.includes("dist")) return "distribution";
  if (n.includes("access")) return "access";
  if (n.includes("router")) return "router";
  return "unknown";
}

/* ===== TopologyGraph (SVG) ===== */
const TopologyGraph = ({ project, projectId, routeToHash, handleNavClick, onOpenDevice, can, authedUser, setProjects, setTopologyLLMMetrics, topologyLLMMetrics, llmBusy, llmBusyMessage, requestRun, onComplete, setLlmNotification, showConfirmModal }) => {
  const deviceDetailHref = (deviceId) => routeToHash ? routeToHash({ name: "device", projectId: projectId || project?.project_id || project?.id, device: deviceId }) : "#/";
  // Helper function for default positioning - defined first to avoid hoisting issues
  const getDefaultPos = (nodeId, role, index = 0, totalByRole = {}) => {
    const centerX = 50;
    const centerY = 50;

    // Normalize role to lowercase for consistent matching
    const normalizedRole = (role || "default").toLowerCase();

    // Count nodes by role for better distribution
    const coreCount = totalByRole.core || 0;
    const distCount = totalByRole.distribution || 0;
    const accessCount = totalByRole.access || 0;
    const routerCount = totalByRole.router || 0;

    switch (normalizedRole) {
      case "core": {
        // Core nodes: arrange in horizontal line at top-center
        if (coreCount <= 1) {
          return { x: centerX, y: 20 };
        }
        const coreSpacing = 25;
        const coreStartX = centerX - ((coreCount - 1) * coreSpacing) / 2;
        return { x: coreStartX + (index * coreSpacing), y: 20 };
      }

      case "distribution": {
        // Distribution nodes: arrange in horizontal line below core
        if (distCount <= 1) {
          return { x: centerX, y: 45 };
        }
        const distSpacing = 22;
        const distStartX = centerX - ((distCount - 1) * distSpacing) / 2;
        return { x: distStartX + (index * distSpacing), y: 45 };
      }

      case "access": {
        // Access nodes: arrange in two rows below distribution
        if (accessCount <= 1) {
          return { x: centerX, y: 70 };
        }
        const accessPerRow = Math.ceil(accessCount / 2);
        const accessSpacing = 20;
        const row = Math.floor(index / accessPerRow);
        const col = index % accessPerRow;
        const accessStartX = centerX - ((accessPerRow - 1) * accessSpacing) / 2;
        return { x: accessStartX + (col * accessSpacing), y: 70 + (row * 20) };
      }

      case "router": {
        // Router nodes: arrange at bottom
        if (routerCount <= 1) {
          return { x: centerX, y: 85 };
        }
        const routerSpacing = 20;
        const routerStartX = centerX - ((routerCount - 1) * routerSpacing) / 2;
        return { x: routerStartX + (index * routerSpacing), y: 85 };
      }

      default: {
        // Default: arrange in grid
        const defaultSpacing = 15;
        const defaultTotal = totalByRole.default || totalByRole[normalizedRole] || 1;
        const defaultCols = Math.ceil(Math.sqrt(defaultTotal));
        const row = Math.floor(index / defaultCols);
        const col = index % defaultCols;
        return { x: 20 + (col * defaultSpacing), y: 20 + (row * defaultSpacing) };
      }
    }
  };

  // Nudge positions so nodes do not overlap; user can rearrange later
  const nudgePositionsNoOverlap = (positions, nodeIds, minDist = 14) => {
    const pos = { ...positions };
    const ids = nodeIds || Object.keys(pos);
    for (let iter = 0; iter < 8; iter++) {
      let moved = false;
      for (let i = 0; i < ids.length; i++) {
        for (let j = i + 1; j < ids.length; j++) {
          const a = pos[ids[i]], b = pos[ids[j]];
          if (!a || !b) continue;
          const dx = b.x - a.x, dy = b.y - a.y;
          const dist = Math.hypot(dx, dy);
          if (dist < minDist && dist > 0.01) {
            const push = (minDist - dist) / 2;
            const nx = (dx / dist) * push, ny = (dy / dist) * push;
            pos[ids[i]] = { x: a.x - nx, y: a.y - ny };
            pos[ids[j]] = { x: b.x + nx, y: b.y + ny };
            moved = true;
          }
        }
      }
      if (!moved) break;
    }
    return pos;
  };

  const [generatingTopology, setGeneratingTopology] = React.useState(false);
  const [topologyError, setTopologyError] = React.useState(null);
  const [showTopologyNotification, setShowTopologyNotification] = React.useState(false);
  const [topologyNotificationData, setTopologyNotificationData] = React.useState(null);
  /** True while fetching graph data (fast endpoint). Graph shows loading. */
  const [isGraphLoading, setIsGraphLoading] = React.useState(true);
  const [refreshKey, setRefreshKey] = React.useState(0);
  const summaryRowsKey = JSON.stringify(project.summaryRows || []);
  /** True while LLM is analyzing (slow). Graph stays interactive; only AI panel shows loading. */
  const isAiLoading = generatingTopology;

  const rows = project.summaryRows || [];
  // Base nodes from project summary rows - compute first
  const baseNodes = rows.map(r => ({
    id: r.device,
    label: r.device,
    role: classifyRoleByName(r.device),
    type: classifyRoleByName(r.device), // For compatibility with AI-generated topology
    model: r.model, mgmtIp: r.mgmtIp,
    routing: r.routing, stpMode: r.stpMode
  }));

  // Topology nodes state - will be updated when topology is generated
  const [topologyNodes, setTopologyNodes] = useState(() => {
    // Initialize from project.topoNodes if available, otherwise compute baseNodes inline
    if (project.topoNodes && project.topoNodes.length > 0) {
      return project.topoNodes.map(n => ({
        id: n.id || n.device_id,
        label: n.label || n.id || n.device_id,
        role: (n.type || n.role || "access")?.toLowerCase(),
        type: n.type || "Switch",
        model: n.model,
        mgmtIp: n.ip || n.management_ip,
        routing: n.routing,
        stpMode: n.stpMode
      }));
    }
    // Compute baseNodes inline for useState initializer
    const summaryRows = project.summaryRows || [];
    return summaryRows.map(r => ({
      id: r.device,
      label: r.device,
      role: classifyRoleByName(r.device),
      type: classifyRoleByName(r.device),
      model: r.model, mgmtIp: r.mgmtIp,
      routing: r.routing, stpMode: r.stpMode
    }));
  });

  // Use topology nodes if available, otherwise use base nodes
  const nodes = topologyNodes.length > 0 ? topologyNodes : baseNodes;

  // Check if user can edit topology (admin, manager, or engineer — viewer is read-only; settings stay manager-only)
  const projectMember = project?.members?.find(m => m.username === authedUser?.username);
  const canEdit = can("upload-config", project);

  const [editMode, setEditMode] = useState(false);

  // Zoom and Pan state
  const [zoom, setZoom] = useState(1.0);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState(false);
  const [panStart, setPanStart] = useState({ x: 0, y: 0 });

  const [positions, setPositions] = useState(() => {
    if (project.topoPositions) {
      return project.topoPositions;
    }
    const pos = {};
    // Count nodes by role for better distribution - compute baseNodes inline
    const summaryRows = project.summaryRows || [];
    const initialNodes = summaryRows.map(r => ({
      id: r.device,
      label: r.device,
      role: classifyRoleByName(r.device),
      type: classifyRoleByName(r.device),
      model: r.model, mgmtIp: r.mgmtIp,
      routing: r.routing, stpMode: r.stpMode
    }));
    const roleCounts = {};
    const roleIndices = {};
    initialNodes.forEach(n => {
      const role = (n.role || "default").toLowerCase();
      roleCounts[role] = (roleCounts[role] || 0) + 1;
    });
    // Use initialNodes for positioning
    initialNodes.forEach(n => {
      const role = (n.role || "default").toLowerCase();
      roleIndices[role] = (roleIndices[role] || 0);
      pos[n.id] = getDefaultPos(n.id, role, roleIndices[role], roleCounts);
      roleIndices[role]++;
    });
    return pos;
  });

  const [links, setLinks] = useState(() => {
    if (project.topoLinks) {
      return project.topoLinks;
    }
    return deriveLinksFromProject(project);
  });

  // Load generating state from localStorage on mount and start polling if needed
  React.useEffect(() => {
    const projectId = project.project_id || project.id;
    if (!projectId) return;
    const storageKey = `llm_generating_topology_${projectId}`;
    const pollingKey = `topology_${projectId}`;
    const saved = localStorage.getItem(storageKey);

    if (saved === "true") {
      // Set generating state first to show loading UI immediately
      setGeneratingTopology(true);

      // If polling is not active but localStorage says generating, start polling immediately
      if (!globalPollingService.isPolling(pollingKey)) {
        // Start polling immediately (don't wait for generatingTopology state to trigger it)
        globalPollingService.startPolling(
          pollingKey,
          projectId,
          api.getTopology,
          (topologyData) => {
            notifyLLMResultReady("Topology", "LLM topology completed. Open Summary to view.");
            // Process topology result
            const aiNodes = topologyData.topology?.nodes || [];
            const aiEdges = topologyData.topology?.edges || [];

            if (aiNodes.length > 0 || aiEdges.length > 0) {
              // Convert AI nodes to internal format
              const nodeMap = new Map();
              const currentNodes = topologyNodes.length > 0 ? topologyNodes : baseNodes;
              currentNodes.forEach(n => {
                nodeMap.set(n.id, { ...n });
              });

              aiNodes.forEach(aiNode => {
                const nodeId = aiNode.id;
                const existingNode = nodeMap.get(nodeId);
                if (existingNode) {
                  nodeMap.set(nodeId, {
                    ...existingNode,
                    label: aiNode.label || existingNode.label,
                    role: (aiNode.type || existingNode.role)?.toLowerCase() || existingNode.role,
                    type: aiNode.type || existingNode.type
                  });
                } else {
                  nodeMap.set(nodeId, {
                    id: nodeId,
                    label: aiNode.label || nodeId,
                    role: (aiNode.type || "access")?.toLowerCase(),
                    type: aiNode.type || "Switch",
                    model: aiNode.model,
                    mgmtIp: aiNode.ip || aiNode.management_ip
                  });
                }
              });

              const updatedNodes = Array.from(nodeMap.values());
              const convertedEdges = aiEdges.map(edge => ({
                a: edge.from,
                b: edge.to,
                label: edge.label || "",
                evidence: edge.evidence || "",
                type: "trunk"
              }));

              // Update positions for new nodes
              const updatedPositions = { ...positions };
              const roleCounts = {};
              const roleIndices = {};
              updatedNodes.forEach(node => {
                const role = (node.role || "default").toLowerCase();
                roleCounts[role] = (roleCounts[role] || 0) + 1;
              });

              updatedNodes.forEach((node) => {
                if (!updatedPositions[node.id]) {
                  const role = (node.role || "access").toLowerCase();
                  roleIndices[role] = (roleIndices[role] || 0);
                  updatedPositions[node.id] = getDefaultPos(node.id, role, roleIndices[role], roleCounts);
                  roleIndices[role]++;
                }
              });
              const nodeIds = updatedNodes.map(n => n.id);
              const nudgedPositions = nudgePositionsNoOverlap(updatedPositions, nodeIds);

              // Update states
              setTopologyNodes(updatedNodes);
              setLinks(convertedEdges);
              setPositions(nudgedPositions);

              // Update project state
              setProjects(prev => prev.map(p => {
                if ((p.project_id || p.id) === projectId) {
                  return {
                    ...p,
                    topoLinks: convertedEdges,
                    topoNodes: aiNodes,
                    topoPositions: nudgedPositions
                  };
                }
                return p;
              }));

              // Load LLM metrics
              if (topologyData.llm_metrics) {
                setTopologyLLMMetrics(topologyData.llm_metrics);
              }
              // Auto-save layout so nodes don't overlap; user can rearrange later
              const labels = Object.fromEntries(updatedNodes.map(n => [n.id, n.label || n.id]));
              const roles = Object.fromEntries(updatedNodes.map(n => [n.id, n.role || "access"]));
              if (can("edit-topology", project)) {
                api.saveTopologyLayout(projectId, nudgedPositions, convertedEdges, labels, roles).then(() => {
                  setProjects(prev => prev.map(p => (p.project_id || p.id) === projectId ? { ...p, topoPositions: nudgedPositions, topoLinks: convertedEdges, topoNodeLabels: labels, topoNodeRoles: roles, topoUpdatedAt: new Date().toISOString() } : p));
                }).catch(err => console.warn("Failed to auto-save topology layout:", err));
              }
            }

            setGeneratingTopology(false);
            localStorage.removeItem(storageKey);
            onComplete?.();

            // Show notification popup (same as Recommendations); global popup so it shows even on Documents/History tab
            setTopologyNotificationData({
              title: "Topology Generated",
              message: `LLM topology generation completed. Found ${aiNodes.length} nodes and ${aiEdges.length} links.`,
              metrics: topologyData.llm_metrics,
              type: "success"
            });
            setShowTopologyNotification(true);
            setLlmNotification?.({ show: true, type: "success", title: "Topology Generated", message: "LLM analysis completed successfully.", metrics: topologyData.llm_metrics, onRegenerate: () => requestRun?.(doGenerateTopologyRef.current) });
          },
          (errorMsg) => {
            setGeneratingTopology(false);
            setTopologyError(errorMsg);
            localStorage.removeItem(storageKey);
            onComplete?.();
          }
        );
      } else {
        // Resume existing polling with new callbacks
        globalPollingService.resumePolling(
          pollingKey,
          (topologyData) => {
            notifyLLMResultReady("Topology", "LLM topology completed. Open Summary to view.");
            // Process topology result (same as above)
            const aiNodes = topologyData.topology?.nodes || [];
            const aiEdges = topologyData.topology?.edges || [];

            if (aiNodes.length > 0 || aiEdges.length > 0) {
              const nodeMap = new Map();
              const currentNodes = topologyNodes.length > 0 ? topologyNodes : baseNodes;
              currentNodes.forEach(n => {
                nodeMap.set(n.id, { ...n });
              });

              aiNodes.forEach(aiNode => {
                const nodeId = aiNode.id;
                const existingNode = nodeMap.get(nodeId);
                if (existingNode) {
                  nodeMap.set(nodeId, {
                    ...existingNode,
                    label: aiNode.label || existingNode.label,
                    role: (aiNode.type || existingNode.role)?.toLowerCase() || existingNode.role,
                    type: aiNode.type || existingNode.type
                  });
                } else {
                  nodeMap.set(nodeId, {
                    id: nodeId,
                    label: aiNode.label || nodeId,
                    role: (aiNode.type || "access")?.toLowerCase(),
                    type: aiNode.type || "Switch",
                    model: aiNode.model,
                    mgmtIp: aiNode.ip || aiNode.management_ip
                  });
                }
              });

              const updatedNodes = Array.from(nodeMap.values());
              const convertedEdges = aiEdges.map(edge => ({
                a: edge.from,
                b: edge.to,
                label: edge.label || "",
                evidence: edge.evidence || "",
                type: "trunk"
              }));

              const updatedPositions = { ...positions };
              const roleCounts = {};
              const roleIndices = {};
              updatedNodes.forEach(node => {
                const role = (node.role || "default").toLowerCase();
                roleCounts[role] = (roleCounts[role] || 0) + 1;
              });

              updatedNodes.forEach((node) => {
                if (!updatedPositions[node.id]) {
                  const role = (node.role || "access").toLowerCase();
                  roleIndices[role] = (roleIndices[role] || 0);
                  updatedPositions[node.id] = getDefaultPos(node.id, role, roleIndices[role], roleCounts);
                  roleIndices[role]++;
                }
              });
              const nodeIds = updatedNodes.map(n => n.id);
              const nudgedPositions = nudgePositionsNoOverlap(updatedPositions, nodeIds);

              setTopologyNodes(updatedNodes);
              setLinks(convertedEdges);
              setPositions(nudgedPositions);

              setProjects(prev => prev.map(p => {
                if ((p.project_id || p.id) === projectId) {
                  return {
                    ...p,
                    topoLinks: convertedEdges,
                    topoNodes: aiNodes,
                    topoPositions: nudgedPositions
                  };
                }
                return p;
              }));

              if (topologyData.llm_metrics) {
                setTopologyLLMMetrics(topologyData.llm_metrics);
              }
              const labels = Object.fromEntries(updatedNodes.map(n => [n.id, n.label || n.id]));
              const roles = Object.fromEntries(updatedNodes.map(n => [n.id, n.role || "access"]));
              if (can("edit-topology", project)) {
                api.saveTopologyLayout(projectId, nudgedPositions, convertedEdges, labels, roles).then(() => {
                  setProjects(prev => prev.map(p => (p.project_id || p.id) === projectId ? { ...p, topoPositions: nudgedPositions, topoLinks: convertedEdges, topoNodeLabels: labels, topoNodeRoles: roles, topoUpdatedAt: new Date().toISOString() } : p));
                }).catch(err => console.warn("Failed to auto-save topology layout:", err));
              }
            }

            setGeneratingTopology(false);
            localStorage.removeItem(storageKey);
            onComplete?.();

            setTopologyNotificationData({
              title: "Topology Generated",
              message: `LLM topology generation completed. Found ${aiNodes.length} nodes and ${aiEdges.length} links.`,
              metrics: topologyData.llm_metrics,
              type: "success"
            });
            setShowTopologyNotification(true);
            setLlmNotification?.({ show: true, type: "success", title: "Topology Generated", message: "LLM analysis completed successfully.", metrics: topologyData.llm_metrics, onRegenerate: () => requestRun?.(doGenerateTopologyRef.current) });
          },
          (errorMsg) => {
            setGeneratingTopology(false);
            setTopologyError(errorMsg);
            localStorage.removeItem(storageKey);
            onComplete?.();
          }
        );
      }
    } else {
      // Clear generating state if localStorage says not generating
      setGeneratingTopology(false);
    }
  }, [project.project_id || project.id]);

  // Load topology layout from backend on mount
  React.useEffect(() => {
    const loadTopologyLayout = async () => {
      const projectId = project.project_id || project.id;
      if (!projectId) return;

      try {
        const topologyData = await api.getTopology(projectId);
        if (topologyData.layout) {
          if (topologyData.layout.positions && Object.keys(topologyData.layout.positions).length > 0) {
            setPositions(topologyData.layout.positions);
          }
          if (topologyData.layout.links && topologyData.layout.links.length > 0) {
            setLinks(topologyData.layout.links);
          }
          if (topologyData.layout.node_labels) {
            setNodeLabels(topologyData.layout.node_labels);
          }
          if (topologyData.layout.node_roles) {
            setNodeRoles(topologyData.layout.node_roles);
          }
        }
        // Load LLM metrics from database if available (so "has result" is true after refresh/tab switch; button shows popup instead of sending to LLM)
        if (topologyData.llm_metrics) {
          setTopologyLLMMetrics(topologyData.llm_metrics);
          setTopologyNotificationData({
            title: "Topology Generated",
            message: "LLM analysis completed successfully.",
            metrics: topologyData.llm_metrics,
            type: "success"
          });
        }
        // Store last modified date if available
        if (topologyData.updated_at || topologyData.last_modified) {
          setProjects(prev => prev.map(p => {
            if ((p.project_id || p.id) === projectId) {
              return { ...p, topoUpdatedAt: topologyData.updated_at || topologyData.last_modified };
            }
            return p;
          }));
        }
      } catch (error) {
        console.error("Failed to load topology layout:", error);
        // Fallback to project data (already set in useState)
      }
    };

    loadTopologyLayout();
  }, [project.project_id || project.id]);

  // Poll for topology updates when generating (works even when user navigates away)
  React.useEffect(() => {
    const projectId = project.project_id || project.id;
    if (!projectId) return;

    const storageKey = `llm_generating_topology_${projectId}`;
    const pollingKey = `topology_${projectId}`;
    const isGenerating = generatingTopology || localStorage.getItem(storageKey) === "true";

    if (!isGenerating) {
      localStorage.removeItem(storageKey);
      globalPollingService.stopPolling(pollingKey);
      return;
    }

    // Use global polling service (works across page navigation)
    // Resume existing polling if it exists, otherwise start new one
    if (globalPollingService.isPolling(pollingKey)) {
      globalPollingService.resumePolling(
        pollingKey,
        (topologyData) => {
          // Process topology result
          const aiNodes = topologyData.topology?.nodes || [];
          const aiEdges = topologyData.topology?.edges || [];

          if (aiNodes.length > 0 || aiEdges.length > 0) {
            // Convert AI nodes to internal format
            const nodeMap = new Map();
            const currentNodes = topologyNodes.length > 0 ? topologyNodes : baseNodes;
            currentNodes.forEach(n => {
              nodeMap.set(n.id, { ...n });
            });

            aiNodes.forEach(aiNode => {
              const nodeId = aiNode.id;
              const existingNode = nodeMap.get(nodeId);
              if (existingNode) {
                nodeMap.set(nodeId, {
                  ...existingNode,
                  label: aiNode.label || existingNode.label,
                  role: (aiNode.type || existingNode.role)?.toLowerCase() || existingNode.role,
                  type: aiNode.type || existingNode.type
                });
              } else {
                nodeMap.set(nodeId, {
                  id: nodeId,
                  label: aiNode.label || nodeId,
                  role: (aiNode.type || "access")?.toLowerCase(),
                  type: aiNode.type || "Switch",
                  model: aiNode.model,
                  mgmtIp: aiNode.ip || aiNode.management_ip
                });
              }
            });

            const updatedNodes = Array.from(nodeMap.values());
            const convertedEdges = aiEdges.map(edge => ({
              a: edge.from,
              b: edge.to,
              label: edge.label || "",
              evidence: edge.evidence || "",
              type: "trunk"
            }));

            // Update positions for new nodes
            const updatedPositions = { ...positions };
            const roleCounts = {};
            const roleIndices = {};
            updatedNodes.forEach(node => {
              const role = (node.role || "default").toLowerCase();
              roleCounts[role] = (roleCounts[role] || 0) + 1;
            });

            updatedNodes.forEach((node) => {
              if (!updatedPositions[node.id]) {
                const role = (node.role || "access").toLowerCase();
                roleIndices[role] = (roleIndices[role] || 0);
                updatedPositions[node.id] = getDefaultPos(node.id, role, roleIndices[role], roleCounts);
                roleIndices[role]++;
              }
            });
            const nodeIds = updatedNodes.map(n => n.id);
            const nudgedPositions = nudgePositionsNoOverlap(updatedPositions, nodeIds);

            // Update states
            setTopologyNodes(updatedNodes);
            setLinks(convertedEdges);
            setPositions(nudgedPositions);

            // Update project state
            setProjects(prev => prev.map(p => {
              if ((p.project_id || p.id) === projectId) {
                return {
                  ...p,
                  topoLinks: convertedEdges,
                  topoNodes: aiNodes,
                  topoPositions: nudgedPositions
                };
              }
              return p;
            }));

            // Load LLM metrics
            if (topologyData.llm_metrics) {
              setTopologyLLMMetrics(topologyData.llm_metrics);
            }
            const labels = Object.fromEntries(updatedNodes.map(n => [n.id, n.label || n.id]));
            const roles = Object.fromEntries(updatedNodes.map(n => [n.id, n.role || "access"]));
            if (can("edit-topology", project)) {
              api.saveTopologyLayout(projectId, nudgedPositions, convertedEdges, labels, roles).then(() => {
                setProjects(prev => prev.map(p => (p.project_id || p.id) === projectId ? { ...p, topoPositions: nudgedPositions, topoLinks: convertedEdges, topoNodeLabels: labels, topoNodeRoles: roles, topoUpdatedAt: new Date().toISOString() } : p));
              }).catch(err => console.warn("Failed to auto-save topology layout:", err));
            }
          }

          setGeneratingTopology(false);
          localStorage.removeItem(storageKey);
          onComplete?.();

          setTopologyNotificationData({
            title: "Topology Generated",
            message: `LLM topology generation completed. Found ${aiNodes.length} nodes and ${aiEdges.length} links.`,
            metrics: topologyData.llm_metrics,
            type: "success"
          });
          setShowTopologyNotification(true);
          setLlmNotification?.({ show: true, type: "success", title: "Topology Generated", message: "LLM analysis completed successfully.", metrics: topologyData.llm_metrics, onRegenerate: () => requestRun?.(doGenerateTopologyRef.current) });
        },
        (errorMsg) => {
          setGeneratingTopology(false);
          setTopologyError(errorMsg);
          localStorage.removeItem(storageKey);
          onComplete?.();
        }
      );
    } else {
      globalPollingService.startPolling(
        pollingKey,
        projectId,
        api.getTopology,
        (topologyData) => {
          notifyLLMResultReady("Topology", "LLM topology completed. Open Summary to view.");
          // Process topology result
          const aiNodes = topologyData.topology?.nodes || [];
          const aiEdges = topologyData.topology?.edges || [];

          if (aiNodes.length > 0 || aiEdges.length > 0) {
            // Convert AI nodes to internal format
            const nodeMap = new Map();
            const currentNodes = topologyNodes.length > 0 ? topologyNodes : baseNodes;
            currentNodes.forEach(n => {
              nodeMap.set(n.id, { ...n });
            });

            aiNodes.forEach(aiNode => {
              const nodeId = aiNode.id;
              const existingNode = nodeMap.get(nodeId);
              if (existingNode) {
                nodeMap.set(nodeId, {
                  ...existingNode,
                  label: aiNode.label || existingNode.label,
                  role: (aiNode.type || existingNode.role)?.toLowerCase() || existingNode.role,
                  type: aiNode.type || existingNode.type
                });
              } else {
                nodeMap.set(nodeId, {
                  id: nodeId,
                  label: aiNode.label || nodeId,
                  role: (aiNode.type || "access")?.toLowerCase(),
                  type: aiNode.type || "Switch",
                  model: aiNode.model,
                  mgmtIp: aiNode.ip || aiNode.management_ip
                });
              }
            });

            const updatedNodes = Array.from(nodeMap.values());
            const convertedEdges = aiEdges.map(edge => ({
              a: edge.from,
              b: edge.to,
              label: edge.label || "",
              evidence: edge.evidence || "",
              type: "trunk"
            }));

            // Update positions for new nodes
            const updatedPositions = { ...positions };
            const roleCounts = {};
            const roleIndices = {};
            updatedNodes.forEach(node => {
              const role = (node.role || "default").toLowerCase();
              roleCounts[role] = (roleCounts[role] || 0) + 1;
            });

            updatedNodes.forEach((node) => {
              if (!updatedPositions[node.id]) {
                const role = (node.role || "access").toLowerCase();
                roleIndices[role] = (roleIndices[role] || 0);
                updatedPositions[node.id] = getDefaultPos(node.id, role, roleIndices[role], roleCounts);
                roleIndices[role]++;
              }
            });
            const nodeIds = updatedNodes.map(n => n.id);
            const nudgedPositions = nudgePositionsNoOverlap(updatedPositions, nodeIds);

            // Update states
            setTopologyNodes(updatedNodes);
            setLinks(convertedEdges);
            setPositions(nudgedPositions);

            // Update project state
            setProjects(prev => prev.map(p => {
              if ((p.project_id || p.id) === projectId) {
                return {
                  ...p,
                  topoLinks: convertedEdges,
                  topoNodes: aiNodes,
                  topoPositions: nudgedPositions
                };
              }
              return p;
            }));

            // Load LLM metrics
            if (topologyData.llm_metrics) {
              setTopologyLLMMetrics(topologyData.llm_metrics);
            }
            const labels = Object.fromEntries(updatedNodes.map(n => [n.id, n.label || n.id]));
            const roles = Object.fromEntries(updatedNodes.map(n => [n.id, n.role || "access"]));
            if (can("edit-topology", project)) {
              api.saveTopologyLayout(projectId, nudgedPositions, convertedEdges, labels, roles).then(() => {
                setProjects(prev => prev.map(p => (p.project_id || p.id) === projectId ? { ...p, topoPositions: nudgedPositions, topoLinks: convertedEdges, topoNodeLabels: labels, topoNodeRoles: roles, topoUpdatedAt: new Date().toISOString() } : p));
              }).catch(err => console.warn("Failed to auto-save topology layout:", err));
            }
          }

          setGeneratingTopology(false);
          localStorage.removeItem(storageKey);
          onComplete?.();

          setTopologyNotificationData({
            title: "Topology Generated",
            message: "LLM analysis completed successfully.",
            metrics: topologyData.llm_metrics,
            type: "success"
          });
          setShowTopologyNotification(true);
          setLlmNotification?.({ show: true, type: "success", title: "Topology Generated", message: "LLM analysis completed successfully.", metrics: topologyData.llm_metrics, onRegenerate: () => requestRun?.(doGenerateTopologyRef.current) });
        },
        (errorMsg) => {
          setGeneratingTopology(false);
          setTopologyError(errorMsg);
          localStorage.removeItem(storageKey);
          onComplete?.();
        }
      );
    }

    return () => {
      // Don't stop polling on unmount - let it continue in background
      // Only stop if explicitly requested (when generatingTopology is false)
    };
  }, [project.project_id || project.id, generatingTopology]);

  const doGenerateTopologyRef = React.useRef(null);

  const handleRefreshTopology = () => {
    setIsGraphLoading(true);
    setRefreshKey(prev => prev + 1);
  };

  const handleGenerateTopology = () => {
    const projectId = project.project_id || project.id;
    if (!projectId) {
      setTopologyError("Project ID not found");
      return;
    }
    if (!can("run-llm", project)) {
      setTopologyError("You do not have permission to run AI/LLM tasks in this project");
      return;
    }
    // If we already have a result (from this session or loaded from API), show popup only; do not send to LLM until user clicks Regenerate
    const hasResult = topologyNotificationData || topologyLLMMetrics;
    if (hasResult && !generatingTopology && !llmBusy) {
      const data = topologyNotificationData || { title: "Topology Generated", message: "LLM analysis completed successfully.", metrics: topologyLLMMetrics, type: "success" };
      setShowTopologyNotification(true);
      setLlmNotification?.({ show: true, type: "success", title: data.title || "Topology Generated", message: data.message || "LLM analysis completed successfully.", metrics: data.metrics, onRegenerate: () => requestRun?.(doGenerateTopologyRef.current) });
      return;
    }
    // Show "Analyzing..." immediately on first click (fixes regenerate not updating UI)
    flushSync(() => {
      setShowTopologyNotification(false);
      setGeneratingTopology(true);
      setTopologyError(null);
    });
    const fn = doGenerateTopologyRef.current || doGenerateTopology;
    if (typeof requestRun === "function") {
      requestRun(fn);
    } else {
      fn();
    }
  };

  const doGenerateTopology = async () => {
    const projectId = project.project_id || project.id;
    if (!projectId) {
      setTopologyError("Project ID not found");
      return;
    }
    const storageKeyTopo = `llm_generating_topology_${projectId}`;
    if (localStorage.getItem(storageKeyTopo) === "true") return;
    // UI already updated by handleGenerateTopology when from button; ensure state when from modal Regenerate
    flushSync(() => {
      setShowTopologyNotification(false);
      setGeneratingTopology(true);
      setTopologyError(null);
    });
    localStorage.setItem(storageKeyTopo, "true");
    api.generateTopology(projectId)
      .then(() => {
        // Request sent successfully - polling will handle the result
        console.log("Topology generation request sent successfully");
      })
      .catch((err) => {
        console.error("Topology generation request failed:", err);
        // Only set error for immediate failures (not timeout - that's expected for long-running LLM)
        if (err.message && !err.message.includes("timeout") && !err.message.includes("ECONNRESET") && !err.message.includes("socket hang up")) {
          setTopologyError(formatError(err) || "Failed to start topology generation. Check backend/LLM server.");
          setGeneratingTopology(false);
          localStorage.removeItem(storageKeyTopo);
          onComplete?.();
        } else {
          // Timeout or connection reset is expected for long-running LLM - polling will handle it
          console.log("Request timeout/reset (expected for LLM) - polling will continue");
        }
      });
    // Note: We don't set generatingTopology=false here - polling will handle it when result is ready
  };
  doGenerateTopologyRef.current = doGenerateTopology;

  const [dragging, setDragging] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [linkStart, setLinkStart] = useState(null);
  const [selectedLink, setSelectedLink] = useState(null);
  const [showLinkDialog, setShowLinkDialog] = useState(false);
  const [showNodeDialog, setShowNodeDialog] = useState(false);
  const [editingNode, setEditingNode] = useState(null);
  const [linkTooltip, setLinkTooltip] = useState(null); // {x, y, text} for link hover
  const [nodeLabels, setNodeLabels] = useState(() => {
    if (project.topoNodeLabels) {
      return project.topoNodeLabels;
    }
    const labels = {};
    // Use baseNodes initially
    baseNodes.forEach(n => {
      labels[n.id] = n.label;
    });
    return labels;
  });
  const [nodeRoles, setNodeRoles] = useState(() => {
    if (project.topoNodeRoles) {
      return project.topoNodeRoles;
    }
    const roles = {};
    // Use baseNodes initially
    baseNodes.forEach(n => {
      roles[n.id] = n.role;
    });
    return roles;
  });
  const [linkMode, setLinkMode] = useState("none"); // "none", "add", "edit"
  const [reroutingLink, setReroutingLink] = useState(null); // For re-routing link connectors
  const [hiddenNodeIds, setHiddenNodeIds] = useState(() => project.topoHiddenNodes || []);
  const [showRestoreNodeList, setShowRestoreNodeList] = useState(false);

  // Snapshot of last saved/loaded layout — used by Cancel to restore to that state
  const lastSavedLayoutRef = React.useRef(null);

  // Step 1: Fetch fast topology (DB only, no LLM) on mount so graph shows immediately
  React.useEffect(() => {
    const projectId = project.project_id || project.id;
    if (!projectId) {
      setIsGraphLoading(false);
      return;
    }
    // Initialize ref from project so Cancel has something before API returns
    lastSavedLayoutRef.current = {
      positions: project.topoPositions || {},
      links: project.topoLinks || [],
      node_labels: project.topoNodeLabels || null,
      node_roles: project.topoNodeRoles || null,
      hidden_node_ids: project.topoHiddenNodes || [],
    };

    let cancelled = false;
    (async () => {
      try {
        const data = await api.getNetworkTopology(projectId);
        if (cancelled) return;
        const topo = data.topology || {};
        const apiNodes = topo.nodes || [];
        const apiEdges = topo.edges || [];
        const layout = data.layout || {};
        if (apiNodes.length > 0 || apiEdges.length > 0) {
          const roleCounts = {};
          const roleIndices = {};
          apiNodes.forEach(n => {
            const role = (n.type || "access").toLowerCase();
            roleCounts[role] = (roleCounts[role] || 0) + 1;
          });
          const newNodes = apiNodes.map((n, idx) => {
            const role = (n.type || "access").toLowerCase();
            roleIndices[role] = roleIndices[role] ?? 0;
            return {
              id: n.id,
              label: n.label || n.id,
              role,
              type: n.type || "Switch",
              model: n.model,
              mgmtIp: n.ip || n.management_ip,
            };
          });
          const newLinks = apiEdges.map(e => ({
            a: e.from,
            b: e.to,
            label: e.label || "",
            evidence: e.evidence || "",
            type: "trunk",
          }));
          // Merge saved layout links with newly generated links so refresh doesn't lose new connections
          const savedLinks = Array.isArray(layout.links) ? layout.links : [];
          const linkKey = (l) => {
            const a = String(l?.a ?? "").trim();
            const b = String(l?.b ?? "").trim();
            return [a, b].sort().join("|");
          };
          const mergedMap = new Map();
          savedLinks.forEach(l => {
            if (l?.a && l?.b) mergedMap.set(linkKey(l), l);
          });
          newLinks.forEach(l => {
            if (!l?.a || !l?.b) return;
            const k = linkKey(l);
            if (!mergedMap.has(k)) mergedMap.set(k, l);
          });
          const linksToUse = Array.from(mergedMap.values());
          setTopologyNodes(newNodes);
          setLinks(linksToUse);

          let positionsToUse;
          if (layout.positions && Object.keys(layout.positions).length > 0) {
            positionsToUse = layout.positions;
            setPositions(layout.positions);
          } else {
            const pos = {};
            const posRoleIndices = {};
            newNodes.forEach(n => {
              const role = (n.role || "access").toLowerCase();
              posRoleIndices[role] = posRoleIndices[role] ?? 0;
              pos[n.id] = getDefaultPos(n.id, role, posRoleIndices[role], roleCounts);
              posRoleIndices[role]++;
            });
            positionsToUse = nudgePositionsNoOverlap(pos, newNodes.map(n => n.id));
            setPositions(positionsToUse);
          }
          if (layout.node_labels) setNodeLabels(layout.node_labels);
          if (layout.node_roles) setNodeRoles(layout.node_roles);
          if (Array.isArray(layout.hidden_node_ids)) setHiddenNodeIds(layout.hidden_node_ids);

          // Store loaded layout as "last saved" so Cancel restores to this
          lastSavedLayoutRef.current = {
            positions: positionsToUse,
            links: linksToUse,
            node_labels: layout.node_labels || null,
            node_roles: layout.node_roles || null,
            hidden_node_ids: Array.isArray(layout.hidden_node_ids) ? layout.hidden_node_ids : [],
          };
        }
      } catch (err) {
        if (!cancelled) console.warn("Fast topology load failed, using fallback:", err);
      } finally {
        if (!cancelled) setIsGraphLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [project.project_id || project.id, summaryRowsKey, refreshKey]);

  // Handle zoom
  const handleZoomIn = () => {
    setZoom(prev => Math.min(prev + 0.2, 3.0));
  };

  const handleZoomOut = () => {
    setZoom(prev => Math.max(prev - 0.2, 0.5));
  };

  const handleZoomReset = () => {
    setZoom(1.0);
    setPan({ x: 0, y: 0 });
  };

  // Handle pan (drag background) - works in both edit and view mode
  const handlePanStart = (e) => {
    // Don't pan if already dragging a node or starting a link
    if (dragging || linkStart || e.button !== 0) return;

    // Check if clicking on empty space (SVG background, pan area rect, or line, not on nodes)
    const target = e.target;
    const isClickingEmptySpace = target.tagName === 'svg' ||
      target.tagName === 'line' ||
      (target.classList && target.classList.contains('pan-area')) ||
      (target.tagName === 'rect' && target.getAttribute('fill') === 'transparent');

    if (editMode) {
      // In edit mode: Ctrl/Shift/Cmd+drag or drag empty space (but not on nodes)
      if (e.ctrlKey || e.metaKey || e.shiftKey || isClickingEmptySpace) {
        setIsPanning(true);
        setPanStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
        e.preventDefault();
        e.stopPropagation();
      }
    } else {
      // In view mode: always allow panning on empty space (SVG background, pan area, or lines)
      if (isClickingEmptySpace) {
        setIsPanning(true);
        setPanStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
        e.preventDefault();
        e.stopPropagation();
      }
    }
  };

  const handlePanMove = (e) => {
    if (isPanning) {
      // Reduce panning speed by dividing by 1.5
      setPan({
        x: (e.clientX - panStart.x) / 1.5,
        y: (e.clientY - panStart.y) / 1.5
      });
    }
  };

  const handlePanEnd = () => {
    setIsPanning(false);
  };

  // Handle node drag
  const handleMouseDown = (nodeId, e) => {
    if (!editMode) return; // view mode: navigation is handled by the <a> wrapper (click); ctrl/cmd/middle-click opens in new tab

    // In edit mode: Check if panning with modifier keys
    if (editMode && (e.ctrlKey || e.metaKey || e.shiftKey)) {
      handlePanStart(e);
      return;
    }

    // Don't start dragging if we're panning
    if (isPanning) {
      return;
    }

    e.stopPropagation();
    setDragging(nodeId);
    setSelectedNode(nodeId);
  };

  const handleMouseMove = (e) => {
    // Handle panning
    if (isPanning) {
      handlePanMove(e);
      return;
    }

    // Handle node dragging
    if (!dragging || !editMode) return;
    const svg = e.currentTarget;
    const rect = svg.getBoundingClientRect();
    const viewBox = svg.viewBox.baseVal;

    // Calculate position accounting for zoom and pan
    const x = ((e.clientX - rect.left) / rect.width) * viewBox.width / zoom - pan.x / zoom;
    const y = ((e.clientY - rect.top) / rect.height) * viewBox.height / zoom - pan.y / zoom;

    setPositions(prev => ({
      ...prev,
      [dragging]: { x, y } // No position limits - allow free dragging
    }));
  };

  const handleMouseUp = () => {
    setDragging(null);
    handlePanEnd();
  };

  // Handle wheel zoom - works in both edit and view mode
  const handleWheel = (e) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? -0.1 : 0.1;
    setZoom(prev => Math.max(0.5, Math.min(3.0, prev + delta)));
  };

  // Handle link creation and re-routing
  const handleNodeClick = (nodeId, e) => {
    if (!editMode) return;
    e.stopPropagation();

    // Re-route link connector mode
    if (reroutingLink !== null) {
      const linkIndex = reroutingLink;
      const link = links[linkIndex];

      // Determine which end to re-route (closest to clicked node)
      const posA = getPos(link.a);
      const posB = getPos(link.b);
      const posNode = getPos(nodeId);

      const distToA = Math.sqrt(Math.pow(posNode.x - posA.x, 2) + Math.pow(posNode.y - posA.y, 2));
      const distToB = Math.sqrt(Math.pow(posNode.x - posB.x, 2) + Math.pow(posNode.y - posB.y, 2));

      // Re-route the closer end
      setLinks(prev => prev.map((l, i) => {
        if (i === linkIndex) {
          if (distToA < distToB) {
            return { ...l, a: nodeId };
          } else {
            return { ...l, b: nodeId };
          }
        }
        return l;
      }));

      setReroutingLink(null);
      setSelectedLink(null);
      return;
    }

    if (linkMode === "add") {
      if (linkStart === null) {
        setLinkStart(nodeId);
        setSelectedNode(nodeId);
      } else if (linkStart !== nodeId) {
        // Create link if it doesn't exist
        const linkExists = links.some(l =>
          (l.a === linkStart && l.b === nodeId) || (l.a === nodeId && l.b === linkStart)
        );
        if (!linkExists) {
          setLinks(prev => [...prev, { a: linkStart, b: nodeId, type: "trunk", label: "" }]);
        }
        setLinkStart(null);
        setSelectedNode(null);
        setLinkMode("none");
      } else {
        setLinkStart(null);
        setSelectedNode(null);
        setLinkMode("none");
      }
    } else if (linkMode === "edit") {
      // In edit mode, clicking node opens edit dialog
      const node = nodes.find(n => n.id === nodeId);
      if (node) {
        setEditingNode(nodeId);
        setShowNodeDialog(true);
      }
    } else {
      setSelectedNode(nodeId);
      setLinkStart(null);
    }
  };

  // Handle node double-click to edit
  const handleNodeDoubleClick = (nodeId, e) => {
    if (!editMode || linkMode !== "none") return;
    e.stopPropagation();
    const node = nodes.find(n => n.id === nodeId);
    if (node) {
      setEditingNode(nodeId);
      setShowNodeDialog(true);
    }
  };

  // Handle link click
  const handleLinkClick = (linkIndex, e) => {
    if (!editMode) return;
    e.stopPropagation();

    if (linkMode === "edit") {
      setSelectedLink(linkIndex);
      setShowLinkDialog(true);
    } else if (reroutingLink === linkIndex) {
      // Cancel re-routing
      setReroutingLink(null);
      setSelectedLink(null);
    }
  };

  // Start re-routing link connector
  const startRerouteLink = (linkIndex) => {
    setReroutingLink(linkIndex);
    setSelectedLink(linkIndex);
    setLinkMode("none");
  };

  // Handle link deletion
  const handleLinkDelete = (linkIndex, e) => {
    if (!editMode) return;
    e.preventDefault();
    e.stopPropagation();
    setLinks(prev => prev.filter((_, i) => i !== linkIndex));
    setSelectedLink(null);
  };

  // Start add link mode
  const startAddLink = () => {
    setLinkMode("add");
    setSelectedNode(null);
    setLinkStart(null);
  };

  // Cancel link mode
  const cancelLinkMode = () => {
    setLinkMode("none");
    setLinkStart(null);
    setSelectedNode(null);
  };

  // Save node changes
  const handleSaveNode = () => {
    if (editingNode) {
      // Update node labels and roles in project
      setProjects(prev => prev.map(p => {
        if (p.id === project.id) {
          const updatedRows = (p.summaryRows || []).map(row => {
            if (row.device === editingNode) {
              return {
                ...row,
                device: nodeLabels[editingNode] || row.device,
                // Note: role is derived from name, so we might need to update the device name
              };
            }
            return row;
          });
          return { ...p, summaryRows: updatedRows };
        }
        return p;
      }));
    }
    setShowNodeDialog(false);
    setEditingNode(null);
  };

  // Save topology
  const handleSave = async () => {
    const projectId = project.project_id || project.id;
    if (!projectId) {
      alert("❌ Project ID not found");
      return;
    }

    try {
      // Save to backend
      if (!can("edit-topology", project)) {
        setTopologyError("You do not have permission to edit topology in this project");
        return;
      }
      await api.saveTopologyLayout(projectId, positions, links, nodeLabels, nodeRoles, hiddenNodeIds);

      // Update "last saved" snapshot so Cancel restores to this state
      lastSavedLayoutRef.current = {
        positions: { ...positions },
        links: links.map(l => ({ ...l })),
        node_labels: { ...nodeLabels },
        node_roles: { ...nodeRoles },
        hidden_node_ids: [...hiddenNodeIds],
      };

      // Update local state with current timestamp
      const now = new Date().toISOString();
      setProjects(prev => prev.map(p =>
        p.id === project.id
          ? { ...p, topoPositions: positions, topoLinks: links, topoNodeLabels: nodeLabels, topoNodeRoles: nodeRoles, topoHiddenNodes: hiddenNodeIds, topoUpdatedAt: now }
          : p
      ));

      setEditMode(false);
      setLinkStart(null);
      setSelectedNode(null);
      setLinkMode("none");
      setSelectedLink(null);

      alert("Topology layout saved successfully.");
    } catch (error) {
      console.error("Failed to save topology layout:", error);
      alert(`Failed to save: ${formatError(error)}`);
    }
  };

  // Cancel edit — restore to last saved/loaded layout (so Cancel shows the saved topology, not a default)
  const handleCancel = () => {
    const saved = lastSavedLayoutRef.current;
    if (saved) {
      setPositions(saved.positions || {});
      setLinks(saved.links || []);
      if (saved.node_labels != null) setNodeLabels(saved.node_labels);
      else {
        const labels = {};
        nodes.forEach(n => { labels[n.id] = n.label; });
        setNodeLabels(labels);
      }
      if (saved.node_roles != null) setNodeRoles(saved.node_roles);
      else {
        const roles = {};
        nodes.forEach(n => { roles[n.id] = n.role; });
        setNodeRoles(roles);
      }
      setHiddenNodeIds(Array.isArray(saved.hidden_node_ids) ? saved.hidden_node_ids : []);
    } else {
      // Fallback to project when no snapshot (e.g. API never loaded)
      if (project.topoPositions && Object.keys(project.topoPositions).length > 0) {
        setPositions(project.topoPositions);
      } else {
        const pos = {};
        const roleCounts = {};
        const roleIndices = {};
        nodes.forEach(n => {
          const role = (n.role || "default").toLowerCase();
          roleCounts[role] = (roleCounts[role] || 0) + 1;
        });
        nodes.forEach(n => {
          const role = (n.role || "default").toLowerCase();
          roleIndices[role] = (roleIndices[role] || 0);
          pos[n.id] = getDefaultPos(n.id, role, roleIndices[role], roleCounts);
          roleIndices[role]++;
        });
        setPositions(pos);
      }
      setLinks(project.topoLinks && project.topoLinks.length > 0 ? project.topoLinks : deriveLinksFromProject(project));
      setNodeLabels(project.topoNodeLabels || Object.fromEntries(nodes.map(n => [n.id, n.label])));
      setNodeRoles(project.topoNodeRoles || Object.fromEntries(nodes.map(n => [n.id, n.role])));
      setHiddenNodeIds(project.topoHiddenNodes || []);
    }

    setEditMode(false);
    setLinkStart(null);
    setSelectedNode(null);
    setLinkMode("none");
    setSelectedLink(null);
    setReroutingLink(null);
    setZoom(1.0);
    setPan({ x: 0, y: 0 });
    setShowRestoreNodeList(false);
  };

  // Remove node from topology (hide it and remove its links)
  const handleRemoveNode = (nodeId) => {
    setHiddenNodeIds(prev => [...prev, nodeId]);
    setLinks(prev => prev.filter(l => l.a !== nodeId && l.b !== nodeId));
    setSelectedNode(null);
    setShowNodeDialog(false);
    setEditingNode(null);
  };

  // Restore a hidden node to the topology
  const handleRestoreNode = (nodeId) => {
    setHiddenNodeIds(prev => prev.filter(id => id !== nodeId));
    setShowRestoreNodeList(false);
  };

  const getPos = id => positions[id] || { x: 50, y: 50 };
  const getNodeName = id => nodeLabels[id] || nodes.find(n => n.id === id)?.label || id;
  const getNodeRole = id => nodeRoles[id] || nodes.find(n => n.id === id)?.role || "access";

  // Get last modified date from project or topology data
  const lastModified = project.topoUpdatedAt || project.updated_at || project.updated || null;
  const formatShortDate = (dateStr) => {
    if (!dateStr) return null;
    try {
      const date = new Date(dateStr);
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    } catch {
      return dateStr.split(' ')[0] || dateStr;
    }
  };

  return (
    <Card
      headerClassName="py-2.5"
      title={
        <div className="flex items-center justify-between w-full gap-2">
          <span className="text-xs font-semibold text-slate-800 dark:text-slate-400 flex-shrink-0">Topology</span>
          <div className="flex items-center gap-2 flex-1 justify-end min-w-0">
            {/* Topology completion popup - always in DOM so it shows when LLM finishes (even if user was on another tab and came back) */}
            <NotificationModal
              show={showTopologyNotification}
              onClose={() => setShowTopologyNotification(false)}
              title={topologyNotificationData?.title || "Topology Generated"}
              message={topologyNotificationData?.message || "LLM topology generation completed."}
              metrics={topologyNotificationData?.metrics}
              type={topologyNotificationData?.type || "success"}
              onRegenerate={() => {
                setShowTopologyNotification(false);
                const fn = doGenerateTopologyRef.current || doGenerateTopology;
                if (typeof requestRun === "function") requestRun(fn);
                else fn();
              }}
            />
            {/* LLM info and last modified - larger format */}
            {topologyLLMMetrics && (
              <span className="text-[10px] text-slate-700 dark:text-slate-400 whitespace-nowrap">
                {topologyLLMMetrics.model_name?.split(':')[0] || '—'} | {topologyLLMMetrics.inference_time_ms ? `${(topologyLLMMetrics.inference_time_ms / 1000).toFixed(1)}s` : '—'}
              </span>
            )}
            {lastModified && (
              <span className="text-[10px] text-slate-700 dark:text-slate-400 whitespace-nowrap">
                {formatShortDate(lastModified)}
              </span>
            )}
            {/* Edit / Zoom controls - AI button is last (far right) like Network Overview */}
            <div className="flex gap-1 items-center flex-shrink-0">
              {canEdit && (
                <>
                  {!editMode ? (
                    <button
                      className="w-6 h-6 flex items-center justify-center rounded-lg border border-slate-300 dark:border-slate-600 bg-slate-100/80 dark:bg-slate-800/50 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 text-xs transition-colors"
                      onClick={() => setEditMode(true)}
                      title="Edit Graph"
                    >
                      ✏️
                    </button>
                  ) : (
                    <>
                      <button
                        className="w-6 h-6 flex items-center justify-center rounded-lg border border-slate-300 dark:border-slate-600 bg-slate-100/80 dark:bg-slate-800/50 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 text-xs transition-colors"
                        onClick={handleCancel}
                        title="Cancel"
                      >
                        ✕
                      </button>
                      <button
                        className="w-6 h-6 flex items-center justify-center rounded-lg bg-white/90 dark:bg-white/10 backdrop-blur-sm border border-slate-300/80 dark:border-slate-600/80 text-slate-700 dark:text-slate-200 shadow-sm hover:bg-white dark:hover:bg-white/15 text-xs transition-colors"
                        onClick={handleSave}
                        title="Save Layout"
                      >
                        ✓
                      </button>
                    </>
                  )}
                </>
              )}
              {/* Zoom controls */}
              <div className="flex gap-1 border-l border-slate-300 dark:border-slate-700 pl-1">
                <button
                  className="w-6 h-6 flex items-center justify-center rounded-lg border border-slate-300 dark:border-slate-600 bg-slate-100/80 dark:bg-slate-800/50 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 text-xs transition-colors"
                  onClick={handleZoomIn}
                  title="Zoom In"
                >
                  +
                </button>
                <button
                  className="w-6 h-6 flex items-center justify-center rounded-lg border border-slate-300 dark:border-slate-600 bg-slate-100/80 dark:bg-slate-800/50 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 text-xs transition-colors"
                  onClick={handleZoomOut}
                  title="Zoom Out"
                >
                  −
                </button>
                <button
                  className="w-6 h-6 flex items-center justify-center rounded-lg border border-slate-300 dark:border-slate-600 bg-slate-100/80 dark:bg-slate-800/50 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 text-xs transition-colors"
                  onClick={handleZoomReset}
                  title="Reset View"
                >
                  ↻
                </button>
              </div>
            </div>
            {/* Refresh Topology button */}
            {!editMode && (
              <button
                type="button"
                onClick={handleRefreshTopology}
                disabled={isGraphLoading}
                className="w-8 h-8 flex items-center justify-center rounded-xl bg-white/90 dark:bg-white/10 backdrop-blur-sm border border-slate-300/80 dark:border-slate-600/80 text-slate-700 dark:text-slate-200 shadow-sm hover:bg-white dark:hover:bg-white/15 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex-shrink-0 text-lg"
                title="Refresh topology"
                aria-label="Refresh topology"
              >
                {isGraphLoading ? "⏳" : "↻"}
              </button>
            )}
          </div>
        </div>
      }
      className="w-full"
      compact={true}
    >
      {/* Check localStorage for generating state (works even when component remounts) */}
      {(() => {
        const projectId = project.project_id || project.id;
        const storageKey = `llm_generating_topology_${projectId}`;
        const isGeneratingFromStorage = localStorage.getItem(storageKey) === "true";
        const isActuallyGenerating = generatingTopology || isGeneratingFromStorage;

        return (
          <>
            {isActuallyGenerating && (
              <div className="mb-3 p-2 rounded-lg bg-slate-200/90 dark:bg-slate-700/50 border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 text-xs">
                ⏳ Analyzing with LLM... This may take 1–2 minutes. You can switch to Documents or other tabs meanwhile.
              </div>
            )}
            {topologyError && (
              <div className="mb-2 p-2 rounded-lg bg-rose-50 dark:bg-rose-900/20 border border-rose-300 dark:border-rose-700 text-rose-700 dark:text-rose-400 text-xs break-words">
                Error: {topologyError}
              </div>
            )}
          </>
        );
      })()}
      {editMode && (
        <div className="mb-2 px-2 py-1.5 bg-gray-50 dark:bg-gray-800 rounded">
          <div className="flex items-center gap-1.5 flex-wrap">
            <Button
              variant={linkMode === "add" ? "primary" : "secondary"}
              className="text-[10px] px-2 py-0.5 h-6"
              onClick={linkMode === "add" ? cancelLinkMode : startAddLink}
            >
              {linkMode === "add" ? "Cancel" : "Add Link"}
            </Button>
            <Button
              variant={linkMode === "edit" ? "primary" : "secondary"}
              className="text-[10px] px-2 py-0.5 h-6"
              onClick={() => {
                setLinkMode(linkMode === "edit" ? "none" : "edit");
                setReroutingLink(null);
              }}
            >
              {linkMode === "edit" ? "Cancel" : "Edit links"}
            </Button>
            {selectedLink !== null && linkMode === "edit" && (
              <>
                <Button
                  variant="danger"
                  className="text-[10px] px-2 py-0.5 h-6"
                  onClick={() => {
                    handleLinkDelete(selectedLink, { preventDefault: () => { }, stopPropagation: () => { } });
                    setShowLinkDialog(false);
                    setSelectedLink(null);
                  }}
                >
                  Delete link
                </Button>
                <Button
                  variant={reroutingLink === selectedLink ? "primary" : "secondary"}
                  className="text-[10px] px-2 py-0.5 h-6"
                  onClick={() => {
                    if (reroutingLink === selectedLink) {
                      setReroutingLink(null);
                    } else {
                      startRerouteLink(selectedLink);
                    }
                  }}
                >
                  {reroutingLink === selectedLink ? "Cancel" : "Reroute"}
                </Button>
              </>
            )}
            {selectedNode !== null && linkMode === "none" && (
              <Button
                variant="danger"
                className="text-[10px] px-2 py-0.5 h-6"
                onClick={() => {
                  showConfirmModal({
                    title: "Remove Node",
                    message: `Are you sure you want to remove "${getNodeName(selectedNode)}" from topology? Its links will be deleted.`,
                    confirmText: "Remove",
                    cancelText: "Cancel",
                    variant: "danger",
                    onConfirm: () => handleRemoveNode(selectedNode)
                  });
                }}
              >
                Remove node
              </Button>
            )}
            {hiddenNodeIds.length > 0 && (
              <div className="relative">
                <Button
                  variant="secondary"
                  className="text-[10px] px-2 py-0.5 h-6"
                  onClick={() => setShowRestoreNodeList(prev => !prev)}
                >
                  Add node
                </Button>
                {showRestoreNodeList && (
                  <div className="absolute left-0 top-full mt-1 z-50 py-1 bg-white dark:bg-gray-800 border border-slate-200 dark:border-slate-600 rounded-lg shadow-lg min-w-[140px] max-h-48 overflow-y-auto">
                    {hiddenNodeIds.map(id => (
                      <button
                        key={id}
                        type="button"
                        className="w-full text-left px-3 py-1.5 text-xs hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200"
                        onClick={() => handleRestoreNode(id)}
                      >
                        {getNodeName(id)}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
          <p className="text-[10px] text-slate-600 dark:text-slate-400 mt-1.5">
            Node: double-click to edit name/role; select then &quot;Remove node&quot; to hide • Link: click to select, then Delete/Reroute or right-click to delete • Add Link: click two nodes • Add node: show hidden nodes
          </p>
        </div>
      )}
      <div className="relative h-[calc(100vh-380px)] min-h-[450px] rounded-xl bg-slate-100 dark:bg-[#0B1220] overflow-hidden">
        {isGraphLoading ? (
          <div className="absolute inset-0 flex items-center justify-center text-slate-500 dark:text-slate-400 text-sm">
            Loading topology graph...
          </div>
        ) : null}
        <svg
          viewBox="0 0 100 100"
          className="w-full h-full"
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
          onMouseDown={handlePanStart}
          onWheel={handleWheel}
          aria-hidden={isGraphLoading}
          style={{
            cursor: isPanning ? 'grabbing' : (!dragging ? 'grab' : 'default'),
            visibility: isGraphLoading ? 'hidden' : 'visible',
          }}
        >
          <g transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`}>
            {/* Background pan area - unlimited size for dragging */}
            <rect
              x="-10000" y="-10000"
              width="20000" height="20000"
              fill="transparent"
              className="pan-area"
              onMouseDown={handlePanStart}
              style={{ cursor: isPanning ? 'grabbing' : (!dragging ? 'grab' : 'default'), pointerEvents: 'all' }}
            />
            {/* edges */}
            {links.map((e, i) => {
              if (hiddenNodeIds.includes(e.a) || hiddenNodeIds.includes(e.b)) return null;
              const A = getPos(e.a), B = getPos(e.b);
              const isSelected = selectedLink === i;
              const isRerouting = reroutingLink === i;
              const midX = (A.x + B.x) / 2;
              const midY = (A.y + B.y) / 2;
              const linkLabel = e.label || e.evidence || "";
              return (
                <g key={i}>
                  <line
                    x1={A.x} y1={A.y} x2={B.x} y2={B.y}
                    stroke={isRerouting ? "#f59e0b" : (isSelected ? "#10b981" : "#5DA0FF")}
                    strokeWidth={editMode ? (isSelected || isRerouting ? "1.5" : "1.2") : "1.0"}
                    strokeDasharray={isRerouting ? "3,3" : "none"}
                    opacity={isRerouting ? "1" : "0.85"}
                    onClick={(evt) => handleLinkClick(i, evt)}
                    onContextMenu={(evt) => handleLinkDelete(i, evt)}
                    onMouseEnter={(evt) => {
                      if (linkLabel) {
                        const svg = evt.currentTarget.ownerSVGElement;
                        const rect = svg.getBoundingClientRect();
                        const viewBox = svg.viewBox.baseVal;
                        const xPercent = (midX / viewBox.width) * 100;
                        const yPercent = (midY / viewBox.height) * 100;
                        setLinkTooltip({
                          x: (xPercent / 100) * rect.width,
                          y: (yPercent / 100) * rect.height,
                          text: linkLabel
                        });
                      }
                    }}
                    onMouseLeave={() => setLinkTooltip(null)}
                    className={editMode ? "cursor-pointer" : (linkLabel ? "cursor-help" : "")}
                  />
                  {editMode && (
                    <line
                      x1={A.x} y1={A.y} x2={B.x} y2={B.y}
                      stroke="transparent"
                      strokeWidth="8"
                      onClick={(evt) => handleLinkClick(i, evt)}
                      onContextMenu={(evt) => handleLinkDelete(i, evt)}
                      className="cursor-pointer"
                    />
                  )}
                </g>
              );
            })}
            {/* nodes */}
            {nodes.map((n) => {
              if (hiddenNodeIds.includes(n.id)) return null;
              const p = getPos(n.id);
              const isSelected = selectedNode === n.id;
              const isLinkStart = linkStart === n.id;
              const deviceSize = editMode ? (isSelected || isLinkStart ? 5 : 4) : 3.5;

              // Get device image if available
              const deviceImages = project?.device_images || {};
              const deviceImageBase64 = deviceImages[n.id];
              // Detect format: PNG starts with iVBOR, JPEG starts with /9j/
              let deviceImageUrl = null;
              if (deviceImageBase64) {
                const imageFormat = deviceImageBase64.startsWith('iVBOR') ? 'png' : 'jpeg';
                deviceImageUrl = `data:image/${imageFormat};base64,${deviceImageBase64}`;
              }
              // Label always below icon: image height is size*8 (centered), so bottom at +size*4; SVG icon bottom ~+size*0.6
              const labelY = deviceImageUrl ? (deviceSize * 4 + 3.2) : (deviceSize + 3);

              const nodeContent = (
                <g
                  transform={`translate(${p.x}, ${p.y})`}
                  onMouseDown={(e) => handleMouseDown(n.id, e)}
                  onClick={(e) => handleNodeClick(n.id, e)}
                  onDoubleClick={(e) => handleNodeDoubleClick(n.id, e)}
                  className={editMode && linkMode !== "add" ? "cursor-move" : "cursor-pointer"}
                >
                  <NetworkDeviceIcon
                    role={getNodeRole(n.id)}
                    isSelected={isSelected}
                    isLinkStart={isLinkStart}
                    size={deviceSize}
                    imageUrl={deviceImageUrl}
                  />
                  <text
                    x={0}
                    y={labelY}
                    fontSize="2.4"
                    fontWeight="600"
                    fill="var(--topo-label-fill, #1e293b)"
                    textAnchor="middle"
                    pointerEvents="none"
                    className="select-none topology-node-label"
                  >
                    {getNodeName(n.id)}
                  </text>
                  {/* hover tooltip */}
                  <title>{`Role: ${n.role || "-"} • Model: ${n.model || "-"} • Mgmt: ${n.mgmtIp || "-"} • Routing: ${n.routing || "-"} • STP: ${n.stpMode || "-"} • Ctrl+click to open in new tab`}</title>
                </g>
              );
              if (!editMode) {
                return (
                  <a key={n.id} href={deviceDetailHref(n.id)} onClick={(e) => handleNavClick?.(e, () => onOpenDevice?.(n.id))} style={{ cursor: "pointer" }}>
                    {nodeContent}
                  </a>
                );
              }
              return React.cloneElement(nodeContent, { key: n.id });
            })}
          </g>
        </svg>
        {/* Link tooltip */}
        {linkTooltip && (
          <div
            className="absolute z-10 text-xs bg-white dark:bg-[#0F172A] text-slate-800 dark:text-gray-100 border border-slate-300 dark:border-[#1F2937] rounded-lg p-2 whitespace-pre shadow-md"
            style={{
              left: linkTooltip.x + 8,
              top: linkTooltip.y + 8,
              pointerEvents: "none",
              maxWidth: 360
            }}
          >
            {linkTooltip.text}
          </div>
        )}
        <div className="absolute top-2 right-2 text-[10px] font-medium text-slate-800 dark:text-slate-400 bg-white/95 dark:bg-black/30 border border-slate-300 dark:border-transparent px-2 py-1 rounded-lg shadow-sm">
          Zoom: {(zoom * 100).toFixed(0)}%
        </div>
      </div>

      {/* Link Edit Dialog */}
      {showLinkDialog && selectedLink !== null && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-xl p-6 max-w-md w-full mx-4 shadow-xl">
            <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-gray-100">
              Edit link
            </h3>
            <div className="space-y-4">
              <div>
                <span className="text-sm text-gray-600 dark:text-gray-400">From:</span>
                <span className="ml-2 font-medium text-gray-900 dark:text-gray-100">
                  {getNodeName(links[selectedLink].a)}
                </span>
              </div>
              <div>
                <span className="text-sm text-gray-600 dark:text-gray-400">To:</span>
                <span className="ml-2 font-medium text-gray-900 dark:text-gray-100">
                  {getNodeName(links[selectedLink].b)}
                </span>
              </div>
              <Field label="Link type">
                <Select
                  value={links[selectedLink].type || "trunk"}
                  onChange={(value) => {
                    setLinks(prev => prev.map((l, i) =>
                      i === selectedLink ? { ...l, type: value } : l
                    ));
                  }}
                  options={[
                    { value: "trunk", label: "Trunk" },
                    { value: "access", label: "Access" },
                    { value: "uplink", label: "Uplink" }
                  ]}
                />
              </Field>
              <Field label="Label (optional)">
                <Input
                  value={links[selectedLink].label || ""}
                  onChange={(e) => {
                    setLinks(prev => prev.map((l, i) =>
                      i === selectedLink ? { ...l, label: e.target.value } : l
                    ));
                  }}
                  placeholder="e.g. GigabitEthernet0/1"
                />
              </Field>
            </div>
            <div className="flex gap-2 mt-6 justify-end">
              <Button variant="secondary" onClick={() => {
                setShowLinkDialog(false);
                setSelectedLink(null);
              }}>
                Close
              </Button>
              <Button variant="primary" onClick={() => {
                setShowLinkDialog(false);
                setSelectedLink(null);
              }}>
                OK
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Node Edit Dialog */}
      {showNodeDialog && editingNode && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-xl p-6 max-w-md w-full mx-4 shadow-xl">
            <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-gray-100">
              Edit node
            </h3>
            <div className="space-y-4">
              <Field label="Node name">
                <Input
                  value={nodeLabels[editingNode] || ""}
                  onChange={(e) => {
                    setNodeLabels(prev => ({ ...prev, [editingNode]: e.target.value }));
                  }}
                  placeholder="Device name"
                />
              </Field>
              <Field label="Role">
                <Select
                  value={nodeRoles[editingNode] || "access"}
                  onChange={(value) => {
                    setNodeRoles(prev => ({ ...prev, [editingNode]: value }));
                  }}
                  options={[
                    { value: "core", label: "Core" },
                    { value: "distribution", label: "Distribution" },
                    { value: "access", label: "Access" }
                  ]}
                />
              </Field>
            </div>
            <div className="flex gap-2 mt-6 justify-between">
              <Button
                variant="danger"
                onClick={() => {
                  showConfirmModal({
                    title: "Remove Node",
                    message: `Are you sure you want to remove "${getNodeName(editingNode)}" from topology? Its links will be deleted.`,
                    confirmText: "Remove",
                    cancelText: "Cancel",
                    variant: "danger",
                    onConfirm: () => {
                      handleRemoveNode(editingNode);
                      setShowNodeDialog(false);
                      setEditingNode(null);
                    }
                  });
                }}
              >
                Remove from topology
              </Button>
              <div className="flex gap-2">
                <Button variant="secondary" onClick={() => {
                  setShowNodeDialog(false);
                  setEditingNode(null);
                }}>
                  Close
                </Button>
                <Button variant="success" onClick={handleSaveNode}>
                  Save
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </Card>
  );
};

/* ===== Topology helpers (fallback when deriveLinksFromProject not available) ===== */
function deriveLinksFromProject(project) {
  // Fallback: assume core connects to distribution and access
  const names = (project.summaryRows || []).map(r => r.device);
  const core = names.find(n => /core/i.test(n));
  const dist = names.find(n => /dist|distribution/i.test(n));
  const access = names.find(n => /access/i.test(n));
  const links = [];
  if (core && dist) links.push({ a: core, b: dist, type: "trunk" });
  if (core && access) links.push({ a: core, b: access, type: "trunk" });
  return links;
}

/* ===== STP structure summary ===== */
function summarizeStp(project) {
  const rows = project.summaryRows || [];
  const modeByDev = {};
  const rootStatus = {}; // "Yes"/"No"/undefined
  rows.forEach(r => {
    if (r.device) {
      modeByDev[r.device] = r.stpMode || "—";
      rootStatus[r.device] = r.stpRoot; // e.g. "Yes"/"No"/"—"
    }
  });
  const rootCandidates = Object.entries(rootStatus)
    .filter(([, v]) => typeof v === "string" && /yes|root/i.test(v))
    .map(([k]) => k);

  return {
    modeByDev,
    rootCandidates, // If empty, means we don't know who is root yet
  };
}

/* ===== Assign roles by guessing from name (core/distribution/access) ===== */
// Note: classifyRoleByName is now defined before TopologyGraph component (see above)

/* ===== AI-like Device Narrative (focus on relationships + STP) ===== */
function buildDeviceNarrative(project, row) {
  if (!row) return "No device data.";
  const links = deriveLinksFromProject(project);
  const stp = summarizeStp(project);
  const neighbors = links.flatMap(e => (e.a === row.device ? [e.b] : e.b === row.device ? [e.a] : []));
  const uniqNeigh = Array.from(new Set(neighbors));
  const role = classifyRoleByName(row.device);

  const parts = [];
  parts.push(`Device summary: ${row.device}`);
  parts.push([
    `• Model/Platform: ${row.model || "—"} • OS/Version: ${row.osVersion || "—"}`,
    `• Serial: ${row.serial || "—"} • Mgmt IP: ${row.mgmtIp || "—"}`
  ].join("  |  "));
  if (row.ifaces) {
    parts.push(`• Ports total ${row.ifaces.total} (Up ${row.ifaces.up}, Down ${row.ifaces.down}, AdminDown ${row.ifaces.adminDown})`);
    parts.push(`• Access ≈ ${row.accessCount ?? "—"}  |  Trunk ≈ ${row.trunkCount ?? "—"}`);
    if (row.allowedVlansShort) parts.push(`• Allowed VLANs (short): ${row.allowedVlansShort}`);
  }
  parts.push(`• VLANs: ${row.vlanCount ?? "—"}  |  STP: ${row.stpMode || "—"}${row.stpRoot ? ` (Root: ${row.stpRoot})` : ""}`);

  // L3
  const l3 = [];
  if (row.routing) l3.push(row.routing);
  if (row.ospfNeighbors != null) l3.push(`OSPF ${row.ospfNeighbors} neigh`);
  if (row.bgpAsn != null) l3.push(`BGP ${row.bgpAsn}/${row.bgpNeighbors ?? "0"}`);
  if (l3.length) parts.push(`• Routing: ${l3.join(" | ")}`);

  // Mgmt/Health
  parts.push(`• NTP: ${row.ntpStatus || "—"}  |  SNMP: ${row.snmp || "—"}  |  Syslog: ${row.syslog || "—"}  |  CPU ${row.cpu ?? "—"}% / MEM ${row.mem ?? "—"}%`);

  // Relationships from graph
  if (uniqNeigh.length) {
    parts.push(`• System relationships: Connected to ${uniqNeigh.join(", ")} (from graph links)`);
  } else {
    parts.push(`• System relationships: (Not found in graph — recommend uploading show cdp/lldp neighbors)`);
  }

  // STP overview and this device's role
  if (Object.keys(stp.modeByDev).length) {
    const rootTxt = stp.rootCandidates.length
      ? `Root Bridge: ${stp.rootCandidates.join(", ")}`
      : "Root Bridge: (not identified — no device reporting as Root)";
    parts.push(`• STP overview: per-device mode may be ${[...new Set(Object.values(stp.modeByDev))].join(", ")} | ${rootTxt}`);
    if (row.stpRoot && /yes|root/i.test(row.stpRoot)) {
      parts.push(`• This device STP role: Root Bridge`);
    } else if (role === "distribution" || role === "access") {
      parts.push(`• This device STP role: Non-root (likely uplink to ${uniqNeigh[0] ?? "core"}; access ports should be PortFast)`);
    }
  }

  // HSRP/VRRP from VLAN details (if any)
  const hsrpHints = [];
  const vds = project.vlanDetails?.[row.device] || [];
  vds.forEach(v => { if (v.hsrpVip) hsrpHints.push(`VLAN${v.vlanId}→${v.hsrpVip}`); });
  if (hsrpHints.length) parts.push(`• HSRP/VRRP: ${hsrpHints.join(", ")}`);

  // Network role summary
  if (role === "core") parts.push("• Network role: Core — aggregation of uplink/downlink and main paths");
  else if (role === "distribution") parts.push("• Network role: Distribution — aggregates Access links to Core");
  else if (role === "access") parts.push("• Network role: Access — serves end users/devices");

  return parts.join("\n");
}

/* ===== DEPRECATED: Hardcoded Device Recommendations ===== */
/* 
 * This function has been replaced with AI-generated gap analysis from full project analysis.
 * Kept for reference but no longer used.
 * Use api.getFullProjectAnalysis() and filter gap_analysis by device instead.
 */
function buildDeviceRecommendations(project, row) {
  // DEPRECATED: This hardcoded logic has been replaced with AI analysis
  // See DeviceDetailsView component which now uses projectGapAnalysis from api.getFullProjectAnalysis()
  return [];
}
