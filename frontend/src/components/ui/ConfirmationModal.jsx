import React from "react";

export default function ConfirmationModal({
  show,
  onClose,
  onConfirm,
  title,
  message,
}) {
  if (!show) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="relative bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-md w-full p-6 border border-slate-300 dark:border-gray-700">
        <div className="flex items-start justify-between mb-4">
          <h3 className="text-lg font-semibold text-yellow-600 dark:text-yellow-400">{title}</h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <div className="text-sm text-gray-700 dark:text-gray-300 mb-6">{message}</div>
        <div className="flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium rounded-lg bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={() => {
              onConfirm();
              onClose();
            }}
            className="px-4 py-2 text-sm font-medium rounded-xl bg-white/90 dark:bg-white/10 backdrop-blur-sm border border-slate-300/80 dark:border-slate-600/80 text-slate-800 dark:text-slate-100 shadow-sm hover:bg-white dark:hover:bg-white/15 transition-colors"
          >
            Generate Again
          </button>
        </div>
      </div>
    </div>
  );
}
