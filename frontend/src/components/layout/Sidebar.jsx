import React from "react";
import { 
  LayoutDashboard, 
  Settings, 
  FileText, 
  History, 
  Zap,
  FolderKanban,
  Users,
  ChevronRight,
  Network
} from "lucide-react";

const Sidebar = ({ sidebarOpen, project, projectTabs, route, onNavigate }) => {
  const iconMap = {
    setting: Settings,
    summary: LayoutDashboard,
    documents: FileText,
    history: History,
    "script-generator": Zap,
  };

  const getIcon = (tabId) => {
    const Icon = iconMap[tabId] || Network;
    return <Icon className="w-4 h-4" />;
  };

  if (!project) return null;

  return (
    <nav className="flex flex-col gap-1 px-2">
      {projectTabs.map((tab) => {
        const isActive = (route.tab || "setting") === tab.id;
        const Icon = getIcon(tab.id);

        return (
          <a
            key={tab.id}
            href={`#/project/${encodeURIComponent(project.project_id || project.id)}/tab/${encodeURIComponent(tab.id)}`}
            onClick={(e) => {
              e.preventDefault();
              onNavigate({ ...route, tab: tab.id });
            }}
            className={`
              flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all
              ${isActive
                ? "bg-indigo-50 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 shadow-sm"
                : "text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-slate-900 dark:hover:text-slate-200"
              }
            `}
            title={sidebarOpen ? undefined : tab.label}
          >
            <span className={`flex-shrink-0 ${isActive ? "text-indigo-600 dark:text-indigo-400" : ""}`}>
              {Icon}
            </span>
            {sidebarOpen && (
              <>
                <span className="flex-1 truncate">{tab.label}</span>
                {isActive && (
                  <ChevronRight className="w-4 h-4 flex-shrink-0 text-indigo-600 dark:text-indigo-400" />
                )}
              </>
            )}
          </a>
        );
      })}
    </nav>
  );
};

export default Sidebar;
