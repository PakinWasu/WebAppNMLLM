import React, { useState, useEffect } from "react";

/**
 * Single-Pane layout: top navbar, responsive side navigation (drawer on small screens), main content.
 * Supports light/dark via Tailwind dark: and responsive breakpoints.
 * Side navigation appears as drawer on mobile/tablet (lg-), hidden on desktop (lg+) where tabs are shown in top bar.
 */
export default function MainLayout({ topBar, sideNavigation, children, mainClassName = "" }) {
  const [sideNavOpen, setSideNavOpen] = useState(false);

  // Listen for custom events to toggle/close side nav
  useEffect(() => {
    const handleToggleSideNav = () => setSideNavOpen(prev => !prev);
    const handleCloseSideNav = () => setSideNavOpen(false);
    
    window.addEventListener('toggleSideNav', handleToggleSideNav);
    window.addEventListener('closeSideNav', handleCloseSideNav);
    
    return () => {
      window.removeEventListener('toggleSideNav', handleToggleSideNav);
      window.removeEventListener('closeSideNav', handleCloseSideNav);
    };
  }, []);

  return (
    <div className="h-screen flex flex-col overflow-hidden bg-slate-50 text-slate-800 dark:bg-slate-950 dark:text-slate-200">
      {/* Top bar */}
      {topBar && (
        <header className="flex-shrink-0 h-12 sm:h-14 border-b border-slate-300 dark:border-slate-800 bg-white/90 dark:bg-slate-900/90 backdrop-blur-sm relative z-20 shadow-sm dark:shadow-none" style={{ pointerEvents: 'auto' }}>
          {topBar}
        </header>
      )}

      <div className="flex flex-1 min-h-0 overflow-hidden">
        {/* Responsive Side Navigation: drawer on mobile/tablet (lg-), hidden on desktop (lg+) */}
        {sideNavigation && (
          <>
            {/* Backdrop on mobile/tablet when open */}
            <div
              className={`fixed inset-0 z-30 bg-black/30 dark:bg-black/50 lg:hidden transition-opacity ${
                sideNavOpen ? "opacity-100" : "opacity-0 pointer-events-none"
              }`}
              onClick={() => setSideNavOpen(false)}
              aria-hidden="true"
            />
            <aside
              className={`
                flex-shrink-0 flex flex-col
                border-r border-slate-300 dark:border-slate-800
                bg-white dark:bg-slate-900/80
                transition-transform duration-200 ease-out
                fixed lg:hidden inset-y-0 left-0 z-40
                w-64
                ${sideNavOpen ? "translate-x-0" : "-translate-x-full"}
              `}
            >
              <div className="flex items-center justify-between h-11 px-4 border-b border-slate-300 dark:border-slate-800 flex-shrink-0">
                <span className="text-sm font-semibold text-slate-700 dark:text-slate-300">Navigation</span>
                <button
                  type="button"
                  onClick={() => setSideNavOpen(false)}
                  className="p-2 rounded-lg text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                  aria-label="Close navigation"
                >
                  ✕
                </button>
              </div>
              <div className="flex-1 min-h-0 overflow-y-auto py-2">
                {React.isValidElement(sideNavigation)
                  ? React.cloneElement(sideNavigation, { 
                      sideNavOpen,
                      onNavigate: () => setSideNavOpen(false)
                    })
                  : sideNavigation}
              </div>
            </aside>
          </>
        )}

        <main className={`flex-1 min-h-0 overflow-y-auto flex flex-col ${mainClassName}`}>
          {children}
        </main>
      </div>
    </div>
  );
}
