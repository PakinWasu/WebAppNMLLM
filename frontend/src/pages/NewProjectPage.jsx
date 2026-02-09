import React, { useState, useEffect } from "react";
import * as api from "../api";
import { fileToDataURL } from "../utils/file";
import { Card, Field, Input, Select, Button, Table } from "../components/ui";
import AddMemberInline from "../components/AddMemberInline";
import { safeDisplay } from "../utils/format";

export default function NewProjectPage({
  indexHref = "#/",
  onCancel,
  onCreate,
  handleNavClick,
}) {
  const [name, setName] = useState("");
  const [desc, setDesc] = useState("");
  const [members, setMembers] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [availableUsers, setAvailableUsers] = useState([]);
  const [backupInterval, setBackupInterval] = useState("Daily");
  const [visibility, setVisibility] = useState("Private");
  const [topoUrl, setTopoUrl] = useState("");

  useEffect(() => {
    const loadUsers = async () => {
      try {
        const data = await api.getUsers();
        setAvailableUsers(data);
      } catch (e) {
        console.error("Failed to load users:", e);
      }
    };
    loadUsers();
  }, []);

  const addMember = (username, role) => {
    if (!username) return;
    if (members.find((m) => m.username === username)) return;
    setMembers([...members, { username, role }]);
  };
  const remove = (u) => setMembers(members.filter((m) => m.username !== u));

  const save = async () => {
    if (!name.trim()) {
      setError("Project name is required");
      return;
    }
    setError("");
    setLoading(true);
    try {
      const project = await api.createProject(
        name,
        desc || "",
        topoUrl,
        visibility,
        backupInterval
      );
      for (const member of members) {
        try {
          await api.addProjectMember(
            project.project_id,
            member.username,
            member.role
          );
        } catch (e) {
          console.error(`Failed to add member ${member.username}:`, e);
        }
      }
      onCreate(project);
    } catch (e) {
      setError(e.message || "Failed to create project");
    } finally {
      setLoading(false);
    }
  };

  const handleFile = async (file) => {
    setError("");
    if (!file) {
      setTopoUrl("");
      return;
    }
    const data = await fileToDataURL(file);
    const img = new Image();
    img.onload = () => {
      setTopoUrl(data);
      setError("");
    };
    img.src = data;
  };

  return (
    <div className="grid gap-6">
      <h2 className="text-xl font-semibold">Create New Project</h2>
      <Card title="Project Info">
        <div className="grid gap-4 md:grid-cols-2">
          <Field label="Project Name">
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Enter project name"
              disabled={loading}
            />
          </Field>
          <Field label="Visibility">
            <Select
              value={visibility}
              onChange={setVisibility}
              options={[
                { value: "Private", label: "Private" },
                { value: "Shared", label: "Shared" },
              ]}
              disabled={loading}
            />
          </Field>
          <Field label="Description">
            <Input
              value={desc}
              onChange={(e) => setDesc(e.target.value)}
              placeholder="Enter project description"
              disabled={loading}
            />
          </Field>
          <Field label="Backup Interval">
            <Select
              value={backupInterval}
              onChange={setBackupInterval}
              options={[
                { value: "Hourly", label: "Hourly" },
                { value: "Daily", label: "Daily" },
                { value: "Weekly", label: "Weekly" },
              ]}
              disabled={loading}
            />
          </Field>
          <div className="md:col-span-2 grid gap-2">
            <Field label="Topology Image">
              <input
                type="file"
                accept="image/*"
                onChange={(e) => handleFile(e.target.files?.[0])}
                disabled={loading}
                className="block w-full text-sm text-gray-500 dark:text-gray-400
                  file:mr-4 file:py-2 file:px-4
                  file:rounded-lg file:border-0
                  file:text-sm file:font-semibold
                  file:bg-slate-100 file:text-slate-800 file:border file:border-slate-300 file:rounded-lg file:px-3 file:py-1.5 file:text-sm
                  hover:file:bg-slate-200
                  dark:file:bg-slate-800 dark:file:text-slate-200 dark:file:border-slate-600
                  dark:hover:file:bg-slate-700
                  cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
              />
            </Field>
            {error && (
              <div className="text-sm text-rose-500 dark:text-rose-400">
                {safeDisplay(error)}
              </div>
            )}
            {topoUrl && (
              <img
                src={topoUrl}
                alt="topology preview"
                className="w-full max-w-md h-48 object-contain rounded-xl border border-slate-300 dark:border-[#1F2937]"
              />
            )}
          </div>
        </div>
      </Card>
      <Card title="Members">
        <AddMemberInline
          members={members}
          onAdd={addMember}
          availableUsers={availableUsers}
        />
        <div className="mt-3">
          <Table
            columns={[
              { header: "Username", key: "username" },
              { header: "Role", key: "role" },
              {
                header: "",
                key: "x",
                cell: (r) => (
                  <Button variant="danger" onClick={() => remove(r.username)}>
                    Remove
                  </Button>
                ),
              },
            ]}
            data={members}
            empty="No members yet"
          />
        </div>
      </Card>
      <div className="flex gap-2">
        <Button onClick={save} disabled={!name || loading}>
          {loading ? "Creating..." : "Create"}
        </Button>
        <a
          href={indexHref}
          onClick={(e) =>
            handleNavClick(e, () => {
              if (!loading) onCancel();
            })
          }
          className={`inline-flex items-center justify-center rounded-lg px-3 py-1.5 text-xs font-medium shadow-sm transition focus:outline-none focus:ring-2 focus:ring-offset-2 bg-white text-gray-900 ring-1 ring-gray-300 hover:bg-gray-50 focus:ring-blue-500 dark:bg-gray-800 dark:text-gray-100 dark:ring-gray-600 dark:hover:bg-gray-700 ${
            loading ? "opacity-50 pointer-events-none" : ""
          }`}
        >
          Cancel
        </a>
      </div>
    </div>
  );
}
