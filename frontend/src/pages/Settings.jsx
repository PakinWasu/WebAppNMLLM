import React from "react";
import Card from "../components/ui/Card";

/**
 * Settings page placeholder. App.jsx renders the actual SettingPage
 * when route.name === "settings" for full project settings.
 */
export default function Settings({ project }) {
  return (
    <Card title="Project Settings">
      <p className="text-sm text-slate-500">
        Project: {project?.name ?? "—"}. Full settings are rendered by App.
      </p>
    </Card>
  );
}
