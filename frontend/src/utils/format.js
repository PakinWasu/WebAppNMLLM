import React from "react";

/** Thailand timezone (ICT, UTC+7) for all displayed times */
export const DISPLAY_TIMEZONE = "Asia/Bangkok";

/**
 * Format date/time for display (Thailand time, en-US).
 */
export function formatDateTime(dateString) {
  if (!dateString) return "—";
  try {
    const date = new Date(dateString);
    return date.toLocaleString("en-US", {
      timeZone: DISPLAY_TIMEZONE,
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    });
  } catch (e) {
    return dateString;
  }
}

/**
 * Format date only (Thailand time, en-US).
 */
export function formatDate(dateString) {
  if (!dateString) return "—";
  try {
    const date = new Date(dateString);
    return date.toLocaleDateString("en-US", {
      timeZone: DISPLAY_TIMEZONE,
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    });
  } catch (e) {
    return dateString;
  }
}

/**
 * Safe string for display (avoid rendering raw object/array as React child).
 */
export function safeDisplay(val) {
  if (val === null || val === undefined) return "—";
  if (typeof val === "string" || typeof val === "number" || typeof val === "boolean")
    return String(val);
  if (React.isValidElement(val)) return val;
  if (Array.isArray(val)) return val.length ? val.map(safeDisplay).join(", ") : "—";
  if (typeof val === "object") return JSON.stringify(val);
  return String(val);
}

/**
 * Safe child for React (object → string for display).
 */
export function safeChild(val) {
  if (val === null || val === undefined) return null;
  if (React.isValidElement(val)) return val;
  if (Array.isArray(val)) return val;
  if (typeof val === "object") return safeDisplay(val);
  return val;
}

/**
 * Normalize any error (Error, API response, string) to a single string for display.
 * Prevents [object Object] and handles FastAPI-style detail (string or array of { msg }).
 */
export function formatError(err) {
  if (err === null || err === undefined) return "An error occurred.";
  if (typeof err === "string") return err;
  if (err instanceof Error) {
    const msg = err.message;
    if (msg && typeof msg === "string" && msg !== "[object Object]") return msg;
    return "An error occurred.";
  }
  if (typeof err === "object") {
    const objMsg = err.message;
    if (typeof objMsg === "string" && objMsg && objMsg !== "[object Object]") return objMsg;
    const d = err.detail;
    if (typeof d === "string") return d;
    if (Array.isArray(d) && d.length) {
      return d.map((e) => (e && typeof e.msg === "string" ? e.msg : JSON.stringify(e))).join(". ");
    }
    if (d && typeof d === "object" && typeof d.message === "string" && d.message !== "[object Object]") return d.message;
  }
  return "An error occurred.";
}
