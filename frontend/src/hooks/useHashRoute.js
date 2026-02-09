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
  useEffect(() => {
    const want = routeToHash(route);
    const cur = (window.location.hash || "#/").replace(/^#\/?/, "") || "";
    const wantNorm = want.replace(/^#\/?/, "") || "";
    if (wantNorm !== cur) {
      window.history.pushState(null, "", want);
    }
  }, [route.name, route.projectId, route.tab, route.device, route.username, route.fromIndex]);

  // Browser back/forward: update route from hash
  useEffect(() => {
    const onHashChange = () => setRoute(parseHash(window.location.hash));
    const onPopState = () => setRoute(parseHash(window.location.hash));
    window.addEventListener("hashchange", onHashChange);
    window.addEventListener("popstate", onPopState);
    return () => {
      window.removeEventListener("hashchange", onHashChange);
      window.removeEventListener("popstate", onPopState);
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
