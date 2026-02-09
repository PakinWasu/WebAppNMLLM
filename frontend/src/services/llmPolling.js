/**
 * Global polling service for LLM results (persists across page navigation).
 */

if (typeof window !== "undefined" && !window.llmPollingService) {
  window.llmPollingService = {
    intervals: new Map(),
    callbacks: new Map(),

    startPolling(key, projectId, endpoint, onUpdate, onError) {
      this.stopPolling(key);
      let pollCount = 0;
      const maxPolls = 120;
      let lastGeneratedAt = null;

      const checkForUpdates = async () => {
        pollCount++;
        if (pollCount > maxPolls) {
          this.stopPolling(key);
          if (onError) onError("Analysis timeout. Please try again.");
          return;
        }
        try {
          const result = await endpoint(projectId);
          const currentGeneratedAt =
            result.generated_at != null ? String(result.generated_at) : null;
          const lastStr = lastGeneratedAt != null ? String(lastGeneratedAt) : null;
          const isNewResult =
            currentGeneratedAt &&
            (lastStr === null || currentGeneratedAt !== lastStr);
          if (result.overview_text && isNewResult) {
            this.stopPolling(key);
            if (onUpdate) onUpdate(result);
            return;
          }
          if (
            result.recommendations &&
            Array.isArray(result.recommendations) &&
            isNewResult
          ) {
            this.stopPolling(key);
            if (onUpdate) onUpdate(result);
            return;
          }
          const hasTopology =
            result.topology &&
            (result.topology.nodes?.length > 0 || result.topology.edges?.length > 0);
          if (hasTopology && isNewResult) {
            this.stopPolling(key);
            if (onUpdate) onUpdate(result);
            return;
          }
          if (
            currentGeneratedAt &&
            (lastStr === null || currentGeneratedAt !== lastStr)
          ) {
            const hasContent =
              result.overview_text ||
              (result.recommendations && result.recommendations.length >= 0) ||
              hasTopology;
            if (hasContent) {
              this.stopPolling(key);
              if (onUpdate) onUpdate(result);
              return;
            }
          }
          if (currentGeneratedAt) lastGeneratedAt = currentGeneratedAt;
        } catch (err) {
          if (err.message && !err.message.includes("404")) {
            console.warn(`Polling error for ${key}:`, err);
          }
        }
      };
      const runPoll = () => checkForUpdates();
      runPoll();
      const interval = setInterval(runPoll, 4000);
      const onVisible = () => {
        if (document.visibilityState === "visible") runPoll();
      };
      document.addEventListener("visibilitychange", onVisible);
      if (!this._visibilityCleanup) this._visibilityCleanup = new Map();
      this._visibilityCleanup.set(key, () =>
        document.removeEventListener("visibilitychange", onVisible)
      );
      this.intervals.set(key, interval);
      this.callbacks.set(key, { onUpdate, onError, projectId, endpoint });
    },

    stopPolling(key) {
      const cleanup = this._visibilityCleanup?.get(key);
      if (cleanup) {
        cleanup();
        this._visibilityCleanup.delete(key);
      }
      const interval = this.intervals.get(key);
      if (interval) {
        clearInterval(interval);
        this.intervals.delete(key);
        this.callbacks.delete(key);
      }
    },

    isPolling(key) {
      return this.intervals.has(key);
    },

    resumePolling(key, onUpdate, onError) {
      const callback = this.callbacks.get(key);
      if (callback) {
        this.callbacks.set(key, { ...callback, onUpdate, onError });
      }
    },
  };
}

export const globalPollingService =
  typeof window !== "undefined" ? window.llmPollingService : null;

export function notifyLLMResultReady(title, body) {
  const fullTitle = title || "LLM Analysis Complete";
  const fullBody = body || "Result is ready. Switch to Summary to view.";
  try {
    if (typeof Notification !== "undefined") {
      if (Notification.permission === "granted") {
        const n = new Notification(fullTitle, { body: fullBody });
        n.onclick = () => {
          window.focus();
          n.close();
        };
      } else if (Notification.permission === "default") {
        Notification.requestPermission().then((p) => {
          if (p === "granted") {
            const n = new Notification(fullTitle, { body: fullBody });
            n.onclick = () => {
              window.focus();
              n.close();
            };
          }
        });
      }
    }
  } catch (e) {
    console.warn("Browser notification failed:", e);
  }
  const baseTitle = (document.title || "").replace(/^\[.*?\]\s*/, "");
  document.title = `[Done] ${fullTitle} – ${baseTitle}`;
  setTimeout(() => {
    document.title =
      document.title.replace(/^\[Done\]\s.*?\s–\s/, "") || baseTitle;
  }, 8000);
}
