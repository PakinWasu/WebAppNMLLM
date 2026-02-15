import React, { useState, useEffect } from "react";
import * as api from "../api";
import { fileToDataURL } from "../utils/file";
import { safeDisplay, formatError } from "../utils/format";
import { Card, Button, Field, Input, Select } from "../components/ui";

export default function NewProjectPage({
  indexHref = "#/",
  authedUser,
  onCancel,
  onCreate,
  handleNavClick,
}) {
  const [name, setName] = useState("");
  const [desc, setDesc] = useState("");
  const [status, setStatus] = useState("Planning");
  const [members, setMembers] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [availableUsers, setAvailableUsers] = useState([]);
  const [visibility, setVisibility] = useState("Private");
  const [topoUrl, setTopoUrl] = useState("");
  const [newMemberUsername, setNewMemberUsername] = useState("");
  const [newMemberRole, setNewMemberRole] = useState("viewer");

  const addMemberRoleOptions = [
    { value: "manager", label: "Manager" },
    { value: "engineer", label: "Engineer" },
    { value: "viewer", label: "Viewer" },
  ];

  const usersAvailableToAdd = (availableUsers || []).filter((u) => {
    const uname = typeof u === "string" ? u : u?.username;
    if (!uname) return false;
    if (authedUser?.username && uname === authedUser.username) return false;
    return !members.some((m) => m.username === uname);
  });

  const refetchUsers = async () => {
    try {
      const data = await api.getUsernames().catch(() => []);
      const list = Array.isArray(data) ? data : [];
      setAvailableUsers(list.map((u) => (typeof u === "string" ? { username: u } : u)));
    } catch (e) {
      console.error("Failed to refetch users:", e);
    }
  };

  useEffect(() => {
    refetchUsers();
  }, []);

  const addMember = () => {
    if (!newMemberUsername) return;
    const username = typeof newMemberUsername === "string" ? newMemberUsername : newMemberUsername?.username ?? newMemberUsername;
    if (members.some((m) => m.username === username)) return;
    const role = addMemberRoleOptions.some((o) => o.value === newMemberRole) ? newMemberRole : "viewer";
    setMembers([...members, { username, role }]);
    setNewMemberUsername("");
    setNewMemberRole("viewer");
    setError("");
  };

  const remove = (username) => {
    setMembers(members.filter((m) => m.username !== username));
  };

  const changeRole = (username, role) => {
    setMembers(members.map((m) => (m.username === username ? { ...m, role } : m)));
  };

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
        "Daily"
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
      setError(formatError(e) || "Failed to create project");
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
    try {
      const data = await fileToDataURL(file);
      const img = new Image();
      img.onload = () => {
        setTopoUrl(data);
        setError("");
      };
      img.onerror = () => {
        setError("Failed to load image. Please try another file.");
      };
      img.src = data;
    } catch (e) {
      setError("Failed to process image: " + formatError(e));
    }
  };

  const getUsernameForOption = (u) => (typeof u === "string" ? u : u.username);

  return (
    <div className="h-full flex flex-col min-h-0 overflow-y-auto">
      {/* Sticky header: same style as Project Settings */}
      <div className="sticky top-0 z-10 flex-shrink-0 flex items-center justify-between py-3 px-1 mb-4 bg-slate-50 dark:bg-slate-950 border-b border-slate-200 dark:border-slate-800 shadow-sm dark:shadow-none">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">Create New Project</h2>
        <div className="flex items-center gap-2 flex-wrap justify-end">
          <Button
            onClick={save}
            disabled={!name.trim() || loading}
            className="bg-green-600 hover:bg-green-700 text-white border-green-600 focus:ring-green-500"
          >
            {loading ? "Creating..." : "Create Project"}
          </Button>
          <Button
            variant="secondary"
            onClick={() => !loading && onCancel?.()}
            disabled={loading}
          >
            Cancel
          </Button>
        </div>
      </div>

      <div className="flex-1 min-h-0 space-y-6">
        {error && (
          <div className="flex-shrink-0 rounded-lg border border-rose-300 dark:border-rose-700 bg-rose-50 dark:bg-rose-900/20 px-4 py-3 text-sm text-rose-700 dark:text-rose-400">
            {safeDisplay(error)}
          </div>
        )}
        <Card title="Project Information" className="flex-shrink-0">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <Field label="Project Name">
              <Input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Enter project name"
                disabled={loading}
              />
            </Field>
            <Field label="Status">
              <Select
                value={status}
                onChange={setStatus}
                options={[
                  { value: "Planning", label: "Planning" },
                  { value: "Design", label: "Design" },
                  { value: "Implementation", label: "Implementation" },
                  { value: "Testing", label: "Testing" },
                  { value: "Production", label: "Production" },
                  { value: "Maintenance", label: "Maintenance" },
                ]}
                disabled={loading}
              />
            </Field>
            <div>
              <Field
                label={
                  <span className="inline-flex items-center gap-1.5">
                    Visibility
                    <span
                      title="Private: only members see this project. Shared: everyone can see it in the list, but only members can open and view content."
                      className="inline-flex items-center justify-center w-4 h-4 rounded-full bg-slate-200 dark:bg-slate-600 text-slate-600 dark:text-slate-300 text-xs font-bold cursor-help"
                      aria-label="Visibility info"
                    >
                      i
                    </span>
                  </span>
                }
              >
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
            </div>
          </div>

          <div className="mb-6">
            <Field label="Description">
              <textarea
                value={desc}
                onChange={(e) => setDesc(e.target.value)}
                placeholder="Enter project description..."
                rows={6}
                disabled={loading}
                className="w-full px-3 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-200 placeholder-slate-500 dark:placeholder-slate-400 focus:border-blue-500 dark:focus:border-blue-400 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:focus:ring-blue-400 transition-colors resize-y disabled:opacity-50"
              />
            </Field>
          </div>

          <div>
            <Field label="Topology Image">
              <div className="space-y-4">
                <div className="flex items-center gap-3">
                  <label className="flex items-center justify-center px-4 py-2.5 text-sm font-medium rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 cursor-pointer transition-colors disabled:opacity-50">
                    <span className="mr-2">📷</span>
                    Choose Image
                    <input
                      type="file"
                      accept="image/*"
                      onChange={(e) => handleFile(e.target.files?.[0])}
                      disabled={loading}
                      className="hidden"
                    />
                  </label>
                  {topoUrl && (
                    <span className="text-sm text-green-600 dark:text-green-400 flex items-center gap-1">
                      ✓ Image uploaded
                    </span>
                  )}
                </div>
                {topoUrl && (
                  <div className="mt-4">
                    <p className="text-xs font-medium text-gray-700 dark:text-gray-300 mb-2">Preview:</p>
                    <div className="relative rounded-xl border-2 border-slate-300 dark:border-gray-700 overflow-hidden bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800 p-4">
                      <img
                        src={topoUrl}
                        alt="Topology preview"
                        className="w-full max-w-full h-auto max-h-96 object-contain mx-auto rounded-lg shadow-sm"
                        style={{ imageRendering: "auto" }}
                      />
                    </div>
                  </div>
                )}
              </div>
            </Field>
          </div>
        </Card>

        <Card
          title="Team Members"
          className="flex-shrink-0"
          actions={
            <div className="flex flex-wrap items-center gap-2 w-full sm:w-auto sm:min-w-[320px]">
              <div className="flex-1 min-w-[240px] max-w-[360px]">
                <Select
                  value={typeof newMemberUsername === "string" ? newMemberUsername : newMemberUsername?.username ?? ""}
                  onChange={(val) => setNewMemberUsername(val)}
                  onFocus={refetchUsers}
                  options={[
                    { value: "", label: "Add member..." },
                    ...usersAvailableToAdd.map((u) => ({
                      value: getUsernameForOption(u),
                      label: getUsernameForOption(u),
                    })),
                  ]}
                  className="w-full text-sm"
                  disabled={loading}
                />
              </div>
              <div className="w-[100px] min-w-[90px] flex-shrink-0">
                <Select
                  value={addMemberRoleOptions.some((o) => o.value === newMemberRole) ? newMemberRole : "viewer"}
                  onChange={setNewMemberRole}
                  options={addMemberRoleOptions}
                  className="w-full text-sm"
                  disabled={loading}
                />
              </div>
              <Button
                onClick={addMember}
                disabled={!newMemberUsername || loading}
                className="text-xs px-3 flex-shrink-0"
              >
                Add
              </Button>
            </div>
          }
        >
          <div className="space-y-4">
            {members.length === 0 ? (
              <div className="text-center py-8 text-sm text-slate-500 dark:text-slate-400">
                No members yet. You can add members after creating the project, or add them now.
              </div>
            ) : (
              <div className="space-y-2">
                {members.map((member) => (
                  <div
                    key={member.username}
                    className="flex items-center justify-between gap-2 p-3 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800/30 hover:bg-slate-100/50 dark:hover:bg-slate-800/50 transition-colors"
                  >
                    <div className="flex items-center gap-3 flex-1 min-w-0">
                      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-indigo-100 dark:bg-indigo-900/30 flex items-center justify-center text-sm font-semibold text-indigo-700 dark:text-indigo-300">
                        {member.username.charAt(0).toUpperCase()}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="font-medium text-sm text-gray-900 dark:text-gray-100 truncate">
                          {member.username}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      <Select
                        value={member.role}
                        onChange={(val) => changeRole(member.username, val)}
                        options={addMemberRoleOptions}
                        className="min-w-[100px]"
                        disabled={loading}
                      />
                      <Button
                        variant="danger"
                        onClick={() => remove(member.username)}
                        className="text-xs px-2 py-1"
                        title="Remove member"
                        disabled={loading}
                      >
                        Remove
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </Card>
      </div>
    </div>
  );
}
