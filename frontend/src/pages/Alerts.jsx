import React from "react";
import Card from "../components/ui/Card";
import Badge from "../components/ui/Badge";

const MOCK_ALERTS = [
  { id: 1, timestamp: new Date().toISOString(), message: "High CPU on CORE2", severity: "warning" },
  { id: 2, timestamp: new Date(Date.now() - 3600000).toISOString(), message: "Interface GE0/0/1 down on ACC1", severity: "critical" },
  { id: 3, timestamp: new Date(Date.now() - 7200000).toISOString(), message: "BGP session flapped on DIST2", severity: "warning" },
  { id: 4, timestamp: new Date(Date.now() - 10800000).toISOString(), message: "STP topology change detected", severity: "warning" },
  { id: 5, timestamp: new Date(Date.now() - 14400000).toISOString(), message: "NTP sync lost on ACC3", severity: "warning" },
];

function formatTime(iso) {
  try {
    const d = new Date(iso);
    return d.toLocaleString("en-US", { hour12: false });
  }
  return iso;
}

export default function Alerts({ project }) {
  return (
    <Card title="Alerts">
      <ul className="space-y-2">
        {MOCK_ALERTS.map((a) => (
          <li
            key={a.id}
            className="flex items-center gap-4 rounded border border-slate-800 bg-slate-800/50 px-4 py-3 text-sm"
          >
            <span className="shrink-0 text-xs text-slate-500">
              {formatTime(a.timestamp)}
            </span>
            <span className="flex-1 text-slate-200">{a.message}</span>
            <Badge variant={a.severity === "critical" ? "critical" : "warning"}>
              {a.severity}
            </Badge>
          </li>
        ))}
      </ul>
    </Card>
  );
}
