import React, { useState } from "react";

/**
 * Single-Pane-of-Glass layout: fixed viewport, no outer scroll.
 * - Top navbar (fixed height)
 * - Left sidebar (collapsible)
 * - Main content (fills remaining height, overflow controlled by children)
 * Target: 1920x1080, above-the-fold density.
 */
export default function MainLayout({ topBar, leftSidebar, children, mainClassName = "" }) {
  const [sidebarOpen, setSidebarOpen] = useState(true);

  return (
    <div className="h-screen flex flex-col overflow-hidden bg-slate-950 text-slate-200">
      {/* Top bar */}
      {topBar && (
        <header className="flex-shrink-0 h-12 border-b border-slate-800 bg-slate-900/80 relative z-20" style={{ pointerEvents: 'auto' }}>
          {topBar}
        </header>
      )}

      <div className="flex flex-1 min-h-0">
        {/* Left sidebar */}
        {leftSidebar && (
          <aside
            className={`flex-shrink-0 border-r border-slate-800 bg-slate-900/50 transition-[width] duration-200 flex flex-col ${
              sidebarOpen ? "w-52" : "w-16"
            }`}
          >
            <div className="flex items-center justify-between h-11 px-3 border-b border-slate-800">
              {sidebarOpen && <span className="text-xs font-medium text-slate-400 truncate">Menu</span>}
              <button
                type="button"
                onClick={() => setSidebarOpen((o) => !o)}
                className="p-1.5 rounded text-slate-400 hover:text-slate-200 hover:bg-slate-800"
                aria-label={sidebarOpen ? "Collapse sidebar" : "Expand sidebar"}
              >
                {sidebarOpen ? "◀" : "▶"}
              </button>
            </div>
            <div className="flex-1 min-h-0 overflow-y-auto">
              {React.isValidElement(leftSidebar)
                ? React.cloneElement(leftSidebar, { sidebarOpen })
                : leftSidebar}
            </div>
          </aside>
        )}

        {/* Main content: no scroll on container so children can use overflow-auto where needed */}
        <main className={`flex-1 min-h-0 overflow-hidden flex flex-col ${mainClassName}`}>
          {children}
        </main>
      </div>
    </div>
  );
}
