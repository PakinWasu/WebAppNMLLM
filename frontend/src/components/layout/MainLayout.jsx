import React, { useState } from "react";

/**
 * Single-Pane layout: top navbar, left sidebar (collapsible; drawer on small screens), main content.
 * Supports light/dark via Tailwind dark: and responsive breakpoints.
 */
export default function MainLayout({ topBar, leftSidebar, children, mainClassName = "" }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="h-screen flex flex-col overflow-hidden bg-slate-50 text-slate-800 dark:bg-slate-950 dark:text-slate-200">
      {/* Top bar */}
      {topBar && (
        <header className="flex-shrink-0 h-12 sm:h-14 border-b border-slate-300 dark:border-slate-800 bg-white/90 dark:bg-slate-900/90 backdrop-blur-sm relative z-20 shadow-sm dark:shadow-none" style={{ pointerEvents: 'auto' }}>
          {topBar}
        </header>
      )}

      <div className="flex flex-1 min-h-0">
        {/* Sidebar: overlay on mobile, inline on md+ */}
        {leftSidebar && (
          <>
            {/* Backdrop on mobile when open */}
            <div
              className={`fixed inset-0 z-30 bg-black/30 dark:bg-black/50 md:hidden transition-opacity ${
                sidebarOpen ? "opacity-100" : "opacity-0 pointer-events-none"
              }`}
              onClick={() => setSidebarOpen(false)}
              aria-hidden="true"
            />
            <aside
              className={`
                flex-shrink-0 flex flex-col
                border-r border-slate-300 dark:border-slate-800
                bg-white dark:bg-slate-900/80
                transition-[transform,width] duration-200 ease-out
                fixed md:relative inset-y-0 left-0 z-40
                w-52
                ${sidebarOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"}
                ${sidebarOpen ? "md:w-52" : "md:w-16"}
              `}
            >
              <div className="flex items-center justify-between h-11 px-3 border-b border-slate-300 dark:border-slate-800 flex-shrink-0">
                {sidebarOpen && <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 truncate">Menu</span>}
                <button
                  type="button"
                  onClick={() => setSidebarOpen((o) => !o)}
                  className="p-2 rounded-lg text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                  aria-label={sidebarOpen ? "Collapse sidebar" : "Expand sidebar"}
                >
                  {sidebarOpen ? "◀" : "▶"}
                </button>
              </div>
              <div className="flex-1 min-h-0 overflow-y-auto py-2">
                {React.isValidElement(leftSidebar)
                  ? React.cloneElement(leftSidebar, { sidebarOpen })
                  : leftSidebar}
              </div>
            </aside>
          </>
        )}

        <main className={`flex-1 min-h-0 overflow-hidden flex flex-col ${mainClassName}`}>
          {children}
        </main>
      </div>
    </div>
  );
}
