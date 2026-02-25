import React from "react";

export default function NotificationModal({
  show,
  onClose,
  title,
  message,
  metrics,
  type = "success",
  onRegenerate,
}) {
  if (!show) return null;

  let generatedAt = null;
  if (metrics && metrics.timestamp) {
    try {
      const d = new Date(metrics.timestamp);
      if (!Number.isNaN(d.getTime())) {
        generatedAt = d.toLocaleString(undefined, {
          year: "numeric",
          month: "2-digit",
          day: "2-digit",
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        });
      }
    } catch (_e) {
      generatedAt = null;
    }
  }

  const handleRegenerate = () => {
    if (onRegenerate) onRegenerate();
    onClose();
  };
  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="notification-modal-title"
    >
      <div className="absolute inset-0 bg-black/50" onClick={onClose} aria-hidden="true" />
      <div className="relative z-10 bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-md w-full p-6 border border-slate-300 dark:border-gray-700">
        <div className="flex items-start justify-between mb-4">
          <h3
            id="notification-modal-title"
            className={`text-lg font-semibold ${
              type === "success"
                ? "text-green-600 dark:text-green-400"
                : type === "error"
                  ? "text-red-600 dark:text-red-400"
                  : "text-slate-700 dark:text-slate-300"
            }`}
          >
            {title}
          </h3>
          <button
            type="button"
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
            aria-label="Close"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <div className="text-sm text-gray-700 dark:text-gray-300 mb-4">{message}</div>
        {metrics && (
          <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-3 mb-4 text-xs">
            <div className="font-semibold text-gray-700 dark:text-gray-300 mb-2">Generation Metrics:</div>
            <div className="space-y-1 text-gray-600 dark:text-gray-400">
              {metrics.inference_time_ms !== undefined && (
                <div>⏱️ Time: {(metrics.inference_time_ms / 1000).toFixed(1)}s</div>
              )}
              {generatedAt && (
                <div>📅 Generated at: {generatedAt}</div>
              )}
              {metrics.token_usage && (
                <div>
                  📊 Tokens:{" "}
                  {metrics.token_usage.total_tokens ||
                    (metrics.token_usage.prompt_tokens || 0) +
                      (metrics.token_usage.completion_tokens || 0) ||
                    0}
                  {metrics.token_usage.prompt_tokens !== undefined &&
                    ` (Prompt: ${metrics.token_usage.prompt_tokens}, Completion: ${metrics.token_usage.completion_tokens || 0})`}
                </div>
              )}
              {metrics.model_name && <div>🤖 Model: {metrics.model_name}</div>}
            </div>
          </div>
        )}
        <div className="flex justify-end gap-2">
          {onRegenerate && (
            <button
              onClick={handleRegenerate}
              className="px-4 py-2 text-sm font-medium rounded-lg bg-slate-600 text-white hover:bg-slate-500 transition-colors"
            >
              Regenerate
            </button>
          )}
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium rounded-xl bg-white/90 dark:bg-white/10 backdrop-blur-sm border border-slate-300/80 dark:border-slate-600/80 text-slate-800 dark:text-slate-100 shadow-sm hover:bg-white dark:hover:bg-white/15 transition-colors"
          >
            OK
          </button>
        </div>
      </div>
    </div>
  );
}
