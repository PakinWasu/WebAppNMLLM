import React from "react";

/**
 * Format date/time for display (local timezone, en-US).
 */
export function formatDateTime(dateString) {
  if (!dateString) return "—";
  try {
    const date = new Date(dateString);
    return date.toLocaleString("en-US", {
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
 * Format date only (local timezone, en-US).
 */
export function formatDate(dateString) {
  if (!dateString) return "—";
  try {
    const date = new Date(dateString);
    return date.toLocaleDateString("en-US", {
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
