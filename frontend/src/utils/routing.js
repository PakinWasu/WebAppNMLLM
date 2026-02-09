/**
 * Hash-based routing utilities for SPA navigation.
 * Keeps route in URL for refresh, open-in-new-tab, and browser back/forward.
 */

export function routeToHash(route) {
  if (!route || route.name === "index") return "#/";
  if (route.name === "login") return "#/login";
  if (route.name === "newProject") return "#/newProject";
  if (route.name === "userAdmin") return "#/userAdmin";
  if (route.name === "changePassword") return "#/changePassword" + (route.username ? "/" + encodeURIComponent(route.username) : "");
  if (route.name === "project" && route.projectId) {
    const tab = route.tab || "setting";
    return "#/project/" + encodeURIComponent(route.projectId) + "/tab/" + encodeURIComponent(tab);
  }
  if (route.name === "device" && route.projectId && route.device) {
    return "#/project/" + encodeURIComponent(route.projectId) + "/device/" + encodeURIComponent(route.device);
  }
  return "#/";
}

export function parseHash(hash) {
  const raw = (hash != null ? hash : typeof window !== "undefined" ? window.location.hash : "").replace(/^#\/?/, "").trim();
  const parts = raw ? raw.split("/").map((p) => decodeURIComponent(p)).filter(Boolean) : [];
  if (parts[0] === "login") return { name: "login" };
  if (parts[0] === "newProject") return { name: "newProject" };
  if (parts[0] === "userAdmin") return { name: "userAdmin" };
  if (parts[0] === "changePassword") return { name: "changePassword", username: parts[1] || undefined, fromIndex: true };
  if (parts[0] === "project" && parts[1]) {
    const projectId = parts[1];
    if (parts[2] === "tab" && parts[3]) return { name: "project", projectId, tab: parts[3] };
    if (parts[2] === "device" && parts[3]) return { name: "device", projectId, device: parts[3] };
    return { name: "project", projectId, tab: "setting" };
  }
  return { name: "index" };
}

/**
 * Call from link onClick: allow ctrl/cmd/middle-click to open in new tab; normal click runs callback (SPA nav).
 */
export function handleNavClick(e, callback) {
  if (e.ctrlKey || e.metaKey || e.button === 1) return;
  e.preventDefault();
  if (typeof callback === "function") callback();
}

/**
 * Initial route for useState: respects hash and auth token.
 * @param { () => string | null } getToken - e.g. () => api.getToken()
 */
export function getInitialRoute(getToken) {
  if (typeof window === "undefined") return { name: "login" };
  const parsed = parseHash(window.location.hash);
  if (!getToken()) return parsed.name === "login" ? parsed : { name: "login" };
  return parsed.name ? parsed : { name: "index" };
}
