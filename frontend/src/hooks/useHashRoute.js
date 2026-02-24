/**
 * Hash-based route state with URL sync and browser back/forward support.
 * Uses pushState so Back goes to previous screen (e.g. Device -> Summary).
 */
import { useState, useEffect } from "react";
import {
  getInitialRoute,
  routeToHash,
  parseHash,
  handleNavClick as handleNavClickUtil,
} from "../utils/routing";

/**
 * @param { () => string | null } getToken - e.g. () => api.getToken()
 * @param { { username: string, role: string } | null } authedUser
 * @returns {{ route, setRoute, routeToHash, handleNavClick }}
 */
export function useHashRoute(getToken, authedUser) {
  const [route, setRoute] = useState(() => getInitialRoute(getToken));

  // Sync route -> URL hash; use pushState so browser back/forward works
  // Exception: changePassword uses replaceState to prevent back/forward navigation to it
  useEffect(() => {
    const want = routeToHash(route);
    const cur = (window.location.hash || "#/").replace(/^#\/?/, "") || "";
    const wantNorm = want.replace(/^#\/?/, "") || "";
    if (wantNorm !== cur) {
      // Use replaceState for changePassword to prevent it from appearing in browser history
      if (route.name === "changePassword") {
        window.history.replaceState(null, "", want);
      } else {
        window.history.pushState(null, "", want);
      }
    }
  }, [route.name, route.projectId, route.tab, route.device, route.username, route.fromIndex]);

  // Browser back/forward: update route from hash
  // Block navigation to changePassword via back/forward - redirect to index instead
  useEffect(() => {
    const handleHistoryNav = () => {
      const parsed = parseHash(window.location.hash);
      // If user tries to navigate to changePassword via back/forward, redirect to index
      if (parsed.name === "changePassword") {
        window.history.replaceState(null, "", "#/");
        setRoute({ name: "index" });
      } else {
        setRoute(parsed);
      }
    };
    window.addEventListener("hashchange", handleHistoryNav);
    window.addEventListener("popstate", handleHistoryNav);
    return () => {
      window.removeEventListener("hashchange", handleHistoryNav);
      window.removeEventListener("popstate", handleHistoryNav);
    };
  }, []);

  // Logged in but URL is #/login -> go to index (fix routing inconsistency)
  useEffect(() => {
    if (authedUser && route.name === "login") {
      setRoute({ name: "index" });
    }
  }, [authedUser, route.name]);

  const handleNavClick = (e, callback) => handleNavClickUtil(e, callback);

  return { route, setRoute, routeToHash, handleNavClick };
}
