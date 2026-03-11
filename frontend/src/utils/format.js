import React from "react";

/** Thailand timezone (ICT, UTC+7) for all displayed times */
export const DISPLAY_TIMEZONE = null;

/**
 * Format date/time for display (Thailand time, DD/MM/YYYY).
 */
export function formatDateTime(dateString) {
  if (!dateString) return "—";
  try {
    const date = new Date(dateString);
    // Use en-GB for DD/MM/YYYY format
    const options = {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    };
    if (DISPLAY_TIMEZONE) options.timeZone = DISPLAY_TIMEZONE;
    return date.toLocaleString("en-GB", options).replace(/\//g, '/'); // Ensure / separator
  } catch (e) {
    return dateString;
  }
}

/**
 * Convert dotted decimal mask to CIDR prefix
 */
export function dottedToCidr(dottedMask) {
  if (!dottedMask) return null;
  
  // If it's already a number (CIDR), return as is
  if (/^\d+$/.test(dottedMask)) {
    const cidr = parseInt(dottedMask);
    return cidr >= 0 && cidr <= 32 ? cidr : null;
  }
  
  // Convert dotted decimal to CIDR
  const parts = dottedMask.split('.');
  if (parts.length !== 4) return null;
  
  let cidr = 0;
  for (const part of parts) {
    const num = parseInt(part);
    if (isNaN(num) || num < 0 || num > 255) return null;
    cidr += num.toString(2).padStart(8, '0').split('1').length - 1;
  }
  
  return cidr <= 32 ? cidr : null;
}

/**
 * Convert CIDR prefix to dotted decimal mask
 */
export function cidrToDotted(cidr) {
  if (!cidr) return null;
  
  // If it's already dotted decimal, return as is
  if (/^\d+\.\d+\.\d+\.\d+$/.test(cidr)) {
    return cidr;
  }
  
  // Convert CIDR to dotted decimal
  const prefix = parseInt(cidr);
  if (isNaN(prefix) || prefix < 0 || prefix > 32) return null;
  
  const mask = [];
  for (let i = 0; i < 4; i++) {
    const octet = Math.min(8, Math.max(0, prefix - (i * 8)));
    mask.push((255 << (8 - octet)) & 255);
  }
  
  return mask.join('.');
}

/**
 * Format subnet mask to show both dotted decimal and CIDR
 */
export function formatSubnetMask(mask) {
  if (!mask || mask === "—") return "—";
  
  const cidr = dottedToCidr(mask);
  const dotted = cidrToDotted(mask);
  
  if (cidr !== null && dotted !== null) {
    // If both formats are valid and different, show both
    if (mask !== dotted && mask !== cidr.toString()) {
      return `${dotted} (${cidr})`;
    }
    // If input is already in one format, show both
    return `${dotted} (${cidr})`;
  }
  
  // Fallback to original value
  return mask;
}

/**
 * Format date for filename (Thailand YYYY-MM-DD).
 */
export function formatFilenameDate(dateInput) {
  try {
    const date = dateInput ? new Date(dateInput) : new Date();
    const options = {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    };
    if (DISPLAY_TIMEZONE) options.timeZone = DISPLAY_TIMEZONE;
    const parts = date.toLocaleDateString("en-GB", options).split('/');
    // en-GB gives DD/MM/YYYY -> return YYYY-MM-DD
    return `${parts[2]}-${parts[1]}-${parts[0]}`;
  } catch (e) {
    return new Date().toISOString().slice(0, 10);
  }
}

/**
 * Format date only (Thailand time, en-US).
 */
export function formatDate(dateString) {
  if (!dateString) return "—";
  try {
    const date = new Date(dateString);
    const options = {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    };
    if (DISPLAY_TIMEZONE) options.timeZone = DISPLAY_TIMEZONE;
    return date.toLocaleDateString("en-US", options);
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
