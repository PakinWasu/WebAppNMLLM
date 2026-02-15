/**
 * Network Interface Details — Dashboard-style component for a single interface.
 * Requirements 2.3.2.2.1–2.3.2.2.16. Bento/card layout, badges, icons.
 *
 * @typedef {Object} InterfaceData
 * @property {string} interfaceName - 2.3.2.2.1 Interface Name
 * @property {string} [description] - 2.3.2.2.6 Description
 * @property {string} [interfaceType] - 2.3.2.2.2 e.g. GigabitEthernet, Fiber
 * @property {'up'|'down'} [administrativeStatus] - 2.3.2.2.3
 * @property {'up'|'down'} [operationalStatus] - 2.3.2.2.4
 * @property {'up'|'down'} [lineProtocolStatus] - 2.3.2.2.5
 * @property {string} [ipv4Address] - 2.3.2.2.7
 * @property {string} [ipv6Address] - 2.3.2.2.8
 * @property {string} [macAddress] - 2.3.2.2.9
 * @property {string} [speed] - 2.3.2.2.10
 * @property {string} [duplexMode] - 2.3.2.2.11 full | half | auto
 * @property {number|string} [mtu] - 2.3.2.2.12
 * @property {'access'|'trunk'|'routed'|string} [portMode] - 2.3.2.2.13
 * @property {string|number} [accessVlan] - 2.3.2.2.14 (when access)
 * @property {string|number} [nativeVlan] - 2.3.2.2.15 (when trunk)
 * @property {string|number[]} [allowedVlans] - 2.3.2.2.16 (when trunk) e.g. "10,20,30-50" or [10,20,30,31,...,50]
 */

import React, { useState, useCallback } from "react";
import {
  Activity,
  Gauge,
  Copy,
  Network,
  Layers,
  Cable,
  Hash,
  Check,
  Wifi,
  WifiOff,
  Minus,
  Info,
} from "lucide-react";

const EMPTY_LABEL = "—";
const NOT_CONFIGURED = "Not Configured";

// --- Status Badge (2.3.2.2.3, 2.3.2.2.4, 2.3.2.2.5) ---
function StatusBadge({ label, status, variant = "operational" }) {
  const isUp = (status || "").toString().toLowerCase() === "up";
  const isAdminDown = variant === "admin" && !isUp;

  const styles = isAdminDown
    ? "bg-slate-200 text-slate-700 dark:bg-slate-600 dark:text-slate-200"
    : isUp
    ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300"
    : "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300";

  const Icon = variant === "admin" ? (isUp ? Wifi : Minus) : isUp ? Wifi : WifiOff;

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${styles}`}
      title={`${label}: ${status || EMPTY_LABEL}`}
    >
      <Icon className="h-3.5 w-3.5 shrink-0" aria-hidden />
      <span>{status || EMPTY_LABEL}</span>
    </span>
  );
}

// --- Copy button for MAC (2.3.2.2.9) ---
function CopyButton({ value, label = "Copy" }) {
  const [copied, setCopied] = useState(false);
  const copy = useCallback(() => {
    if (!value) return;
    navigator.clipboard.writeText(value).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }, [value]);
  if (!value || value === EMPTY_LABEL || value === NOT_CONFIGURED) return null;
  return (
    <button
      type="button"
      onClick={copy}
      className="inline-flex items-center gap-1 rounded-md p-1.5 text-slate-500 hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-slate-700 dark:hover:text-slate-300 transition-colors"
      title={label}
      aria-label={label}
    >
      {copied ? (
        <Check className="h-4 w-4 text-emerald-500" aria-hidden />
      ) : (
        <Copy className="h-4 w-4" aria-hidden />
      )}
    </button>
  );
}

// --- Row helper for card content ---
function DetailRow({ icon: Icon, label, value, emptyState = EMPTY_LABEL, hideIfEmpty = false }) {
  const isEmpty = value == null || String(value).trim() === "";
  const display = isEmpty ? emptyState : String(value);
  if (hideIfEmpty && isEmpty) return null;
  return (
    <div className="flex items-center justify-between gap-2 py-1.5 border-b border-slate-100 dark:border-slate-700/60 last:border-0">
      <div className="flex items-center gap-2 min-w-0">
        {Icon && <Icon className="h-4 w-4 shrink-0 text-slate-400 dark:text-slate-500" aria-hidden />}
        <span className="text-xs text-slate-500 dark:text-slate-400">{label}</span>
      </div>
      <span className={`text-xs font-medium text-slate-800 dark:text-slate-200 truncate ${isEmpty ? "italic text-slate-400" : ""}`} title={display}>
        {display}
      </span>
    </div>
  );
}

// --- Physical Details Card (2.3.2.2.9–2.3.2.2.12) ---
function PhysicalDetailsCard({ data }) {
  const mac = data.macAddress;
  return (
    <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900/50 p-4 shadow-sm">
      <div className="flex items-center gap-2 mb-3">
        <Cable className="h-4 w-4 text-slate-500 dark:text-slate-400" aria-hidden />
        <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200">Physical Details</h3>
      </div>
      <div className="space-y-0">
        <div className="flex items-center justify-between gap-2 py-1.5 border-b border-slate-100 dark:border-slate-700/60">
          <div className="flex items-center gap-2 min-w-0">
            <Network className="h-4 w-4 shrink-0 text-slate-400 dark:text-slate-500" aria-hidden />
            <span className="text-xs text-slate-500 dark:text-slate-400">MAC Address</span>
          </div>
          <div className="flex items-center gap-1 min-w-0">
            <span className="text-xs font-medium text-slate-800 dark:text-slate-200 truncate" title={mac || EMPTY_LABEL}>
              {mac || EMPTY_LABEL}
            </span>
            <CopyButton value={mac} label="Copy MAC" />
          </div>
        </div>
        <DetailRow icon={Gauge} label="Speed" value={data.speed} />
        <DetailRow icon={Activity} label="Duplex" value={data.duplexMode} />
        <DetailRow icon={Hash} label="MTU" value={data.mtu != null ? String(data.mtu) : null} />
      </div>
    </div>
  );
}

// --- IP Configuration Card (2.3.2.2.7, 2.3.2.2.8) ---
function IpConfigCard({ data }) {
  const empty = NOT_CONFIGURED;
  return (
    <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900/50 p-4 shadow-sm">
      <div className="flex items-center gap-2 mb-3">
        <Layers className="h-4 w-4 text-slate-500 dark:text-slate-400" aria-hidden />
        <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200">IP Configuration</h3>
      </div>
      <div className="space-y-0">
        <DetailRow icon={Network} label="IPv4 Address" value={data.ipv4Address} emptyState={empty} />
        <DetailRow icon={Network} label="IPv6 Address" value={data.ipv6Address} emptyState={empty} />
      </div>
    </div>
  );
}

// --- VLAN & Switching Card (2.3.2.2.13–2.3.2.2.16) ---
function VlanSwitchingCard({ data }) {
  const mode = (data.portMode || "").toString().toLowerCase();
  const isAccess = mode === "access";
  const isTrunk = mode === "trunk";

  const allowedRaw = data.allowedVlans;
  const allowedStr = Array.isArray(allowedRaw)
    ? allowedRaw.join(", ")
    : allowedRaw != null
    ? String(allowedRaw).trim()
    : "";
  const allowedDisplay = allowedStr.length > 32 ? `${allowedStr.slice(0, 32)}…` : allowedStr;
  const hasLongAllowed = allowedStr.length > 32;

  return (
    <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900/50 p-4 shadow-sm">
      <div className="flex items-center gap-2 mb-3">
        <Layers className="h-4 w-4 text-slate-500 dark:text-slate-400" aria-hidden />
        <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200">VLAN & Switching</h3>
      </div>
      <div className="space-y-0">
        <DetailRow icon={null} label="Port Mode" value={data.portMode || EMPTY_LABEL} />
        {isAccess && <DetailRow icon={null} label="Access VLAN" value={data.accessVlan} />}
        {isTrunk && <DetailRow icon={null} label="Native VLAN" value={data.nativeVlan} />}
        {isTrunk && (
          <div className="flex items-center justify-between gap-2 py-1.5 border-b border-slate-100 dark:border-slate-700/60 last:border-0">
            <span className="text-xs text-slate-500 dark:text-slate-400">Allowed VLANs</span>
            <span
              className="text-xs font-medium text-slate-800 dark:text-slate-200 truncate max-w-[180px]"
              title={hasLongAllowed ? allowedStr : undefined}
            >
              {allowedDisplay || EMPTY_LABEL}
            </span>
          </div>
        )}
      </div>
      {!isAccess && !isTrunk && mode !== "routed" && (
        <p className="text-xs text-slate-400 dark:text-slate-500 mt-2 italic">No VLAN info for this mode</p>
      )}
    </div>
  );
}

// --- Main component ---
export default function NetworkInterfaceDetails({ data }) {
  const d = data || {};
  const name = d.interfaceName || "Unknown Interface";
  const desc = d.description;
  const ifType = d.interfaceType;
  const adminStatus = (d.administrativeStatus || "").toString().toLowerCase() || "down";
  const operStatus = (d.operationalStatus || "").toString().toLowerCase() || "down";
  const lineProtocol = (d.lineProtocolStatus || "").toString().toLowerCase();

  return (
    <div className="rounded-2xl border border-slate-200 dark:border-slate-700 bg-slate-50/80 dark:bg-slate-900/30 overflow-hidden shadow-sm">
      {/* Group 1: Header & Identity + Group 2: Critical Status */}
      <div className="p-4 sm:p-5 border-b border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900/50">
        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
          <div className="min-w-0">
            <h2 className="text-lg font-bold text-slate-900 dark:text-white truncate" title={name}>
              {name}
            </h2>
            {desc && (
              <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5 truncate" title={desc}>
                {desc}
              </p>
            )}
            {ifType && (
              <p className="flex items-center gap-1.5 mt-1.5 text-xs text-slate-600 dark:text-slate-300">
                <Info className="h-3.5 w-3.5 shrink-0" aria-hidden />
                <span>{ifType}</span>
              </p>
            )}
          </div>
          <div className="flex flex-wrap gap-2 shrink-0">
            <StatusBadge label="Admin" status={adminStatus === "up" ? "Up" : "Down"} variant="admin" />
            <StatusBadge label="Operational" status={operStatus === "up" ? "Up" : "Down"} variant="operational" />
            {lineProtocol && (
              <StatusBadge label="Line Protocol" status={lineProtocol === "up" ? "Up" : "Down"} variant="operational" />
            )}
          </div>
        </div>
      </div>

      {/* Bento Grid: Physical | IP | VLAN */}
      <div className="p-4 sm:p-5 grid grid-cols-1 md:grid-cols-3 gap-4">
        <PhysicalDetailsCard data={d} />
        <IpConfigCard data={d} />
        <VlanSwitchingCard data={d} />
      </div>
    </div>
  );
}

// --- Mock data for demo (2.3.2.2.x) ---
export const mockInterfaceData = {
  interfaceName: "Gi1/0/1",
  description: "Uplink to Core",
  interfaceType: "GigabitEthernet",
  administrativeStatus: "up",
  operationalStatus: "up",
  lineProtocolStatus: "up",
  ipv4Address: null,
  ipv6Address: null,
  macAddress: "a4:b1:c1:00:11:22",
  speed: "1000Mbps",
  duplexMode: "Full",
  mtu: 1500,
  portMode: "trunk",
  accessVlan: null,
  nativeVlan: 1,
  allowedVlans: "10,20,30-50",
};

// Additional mock: access port with IP (for empty-state and access demo)
export const mockInterfaceDataAccess = {
  interfaceName: "Gi1/0/24",
  description: "Access to PC",
  interfaceType: "GigabitEthernet",
  administrativeStatus: "up",
  operationalStatus: "up",
  lineProtocolStatus: "up",
  ipv4Address: "192.168.1.1/24",
  ipv6Address: null,
  macAddress: "a4:b1:c1:00:11:33",
  speed: "100Mbps",
  duplexMode: "Full",
  mtu: 1500,
  portMode: "access",
  accessVlan: 10,
  nativeVlan: null,
  allowedVlans: null,
};

// Demo: render with mock data (use <NetworkInterfaceDetailsDemo /> in a page to preview)
export function NetworkInterfaceDetailsDemo() {
  return (
    <div className="space-y-6 p-4 max-w-4xl mx-auto">
      <NetworkInterfaceDetails data={mockInterfaceData} />
      <NetworkInterfaceDetails data={mockInterfaceDataAccess} />
    </div>
  );
}

// Helper to map backend interface row to InterfaceData (for use in App)
export function mapBackendInterfaceToInterfaceData(row) {
  if (!row) return null;
  const allowed = row.allowedShort != null && row.allowedShort !== EMPTY_LABEL
    ? row.allowedShort
    : Array.isArray(row.allowed_vlans)
    ? row.allowed_vlans.join(", ")
    : null;
  return {
    interfaceName: row.port ?? row.name ?? row.interface ?? "",
    description: row.desc ?? row.description ?? "",
    interfaceType: row.type ?? "",
    administrativeStatus: (row.admin ?? row.admin_status ?? "").toLowerCase() || undefined,
    operationalStatus: (row.oper ?? row.oper_status ?? "").toLowerCase() || undefined,
    lineProtocolStatus: (row.lineProto ?? row.line_protocol ?? row.oper ?? "").toLowerCase() || undefined,
    ipv4Address: row.ipv4 ?? row.ipv4_address ?? null,
    ipv6Address: row.ipv6 ?? row.ipv6_address ?? null,
    macAddress: row.mac ?? row.mac_address ?? null,
    speed: row.speed ?? null,
    duplexMode: row.duplex ?? null,
    mtu: row.mtu != null ? row.mtu : null,
    portMode: (row.mode ?? row.port_mode ?? "").toLowerCase() || null,
    accessVlan: row.accessVlan ?? row.access_vlan ?? null,
    nativeVlan: row.nativeVlan ?? row.native_vlan ?? null,
    allowedVlans: allowed,
  };
}
