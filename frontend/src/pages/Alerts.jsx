import React from "react";
import Card from "../components/ui/Card";
import Badge from "../components/ui/Badge";

function formatTime(iso) {
  try {
    const d = new Date(iso);
    return d.toLocaleString("en-US", { hour12: false });
  } catch {
    return iso;
  }
}

export default function Alerts({ project, alerts = [] }) {
  return (
    <Card title="Alerts">
      {alerts.length === 0 ? (
        <div className="rounded border border-slate-800 bg-slate-800/30 px-4 py-6 text-center text-sm text-slate-400">
          No alerts. Alerts will appear here when available.
        </div>
      ) : (
        <ul className="space-y-2">
          {alerts.map((a) => (
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
      )}
    </Card>
  );
}
