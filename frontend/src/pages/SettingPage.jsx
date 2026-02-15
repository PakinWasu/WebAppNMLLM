import React, { useState, useEffect, useMemo } from "react";
import * as api from "../api";
import { fileToDataURL } from "../utils/file";
import { safeDisplay, formatError } from "../utils/format";
import { Card, Button, Field, Input, Select, Table } from "../components/ui";

export default function SettingPage({ project, setProjects, authedUser, goIndex }) {
  const [name, setName] = useState(project.name);
  const [desc, setDesc] = useState(project.desc || project.description || "");
  const [status, setStatus] = useState(project.status || "Planning");
  const [visibility, setVisibility] = useState(project.visibility || "Private");
  const [backupInterval, setBackupInterval] = useState(project.backupInterval || project.backup_interval || "Daily");
  const [topoUrl, setTopoUrl] = useState(project.topoUrl || project.topo_url || "");
  const [error, setError] = useState("");
  const [members, setMembers] = useState(project.members || []);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState("");
  const [availableUsers, setAvailableUsers] = useState([]);
  const [newMemberUsername, setNewMemberUsername] = useState("");
  const [newMemberRole, setNewMemberRole] = useState("viewer");

  // Current user's role in this project (admin = project admin, manager/engineer/viewer)
  const currentUserProjectRole = useMemo(() => {
    return members.find((m) => m.username === authedUser?.username)?.role;
  }, [members, authedUser?.username]);
  
  const isProjectAdmin = useMemo(() => currentUserProjectRole === "admin", [currentUserProjectRole]);
  const isProjectManager = useMemo(() => currentUserProjectRole === "manager", [currentUserProjectRole]);
  
  // When platform admin opens settings, they have full control (treat as project admin for UI)
  const canManageManagers = useMemo(() => {
    return isProjectAdmin || authedUser?.role === "admin";
  }, [isProjectAdmin, authedUser?.role]);
  
  // Role options when adding: only admin can assign manager; manager can only assign engineer/viewer
  const addMemberRoleOptions = useMemo(() => {
    return canManageManagers
      ? [
          { value: "manager", label: "Manager" },
          { value: "engineer", label: "Engineer" },
          { value: "viewer", label: "Viewer" },
        ]
      : [
          { value: "engineer", label: "Engineer" },
          { value: "viewer", label: "Viewer" },
        ];
  }, [canManageManagers]);
  
  // Users available to add (exclude already in members; project admin: exclude none by role, list is from API)
  const usersAvailableToAdd = useMemo(() => {
    return (availableUsers || []).filter(
      (u) => !members.some((m) => m.username === u.username)
    );
  }, [availableUsers, members]);
  
  // Can delete/edit this member: not project admin; and if manager viewing, cannot touch other managers
  const canEditMember = useMemo(() => {
    return (member) => {
      if (member.role === "admin") return false;
      if (isProjectManager && member.role === "manager") return false;
      return true;
    };
  }, [isProjectManager]);

  const refetchUsers = async () => {
    try {
      const usersData = await api.getUsernames().catch(() => []);
      setAvailableUsers(Array.isArray(usersData) ? usersData : []);
    } catch (e) {
      console.error("Failed to refetch users:", e);
    }
  };

  useEffect(() => {
    const loadData = async () => {
      try {
        const projectId = project.project_id || project.id;
        if (projectId) {
          const [membersData, projectData, usersData] = await Promise.all([
            api.getProjectMembers(projectId).catch(() => []),
            api.getProject(projectId).catch(() => null),
            api.getUsernames().catch(() => []),
          ]);
          setMembers(membersData.map((m) => ({ username: m.username, role: m.role })));
          setAvailableUsers(Array.isArray(usersData) ? usersData : []);
          if (projectData) {
            if (projectData.topo_url) setTopoUrl(projectData.topo_url);
            if (projectData.visibility) setVisibility(projectData.visibility);
            if (projectData.status) setStatus(projectData.status);
            if (projectData.backup_interval) setBackupInterval(projectData.backup_interval);
          }
        }
      } catch (e) {
        console.error("Failed to load data:", e);
      }
    };
    loadData();
  }, [project.project_id, project.id]);

  // When current user is manager, don't allow "manager" as new member role
  useEffect(() => {
    if (!canManageManagers && newMemberRole === "manager") {
      setNewMemberRole("viewer");
    }
  }, [canManageManagers, newMemberRole]);

  const handleFile = async (file) => {
    setError("");
    if (!file) return;
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

  const save = async () => {
    setError("");
    try {
      await api.updateProject(project.project_id || project.id, name, desc, topoUrl, visibility, backupInterval, status);
      const currentMembers = await api.getProjectMembers(project.project_id || project.id);
      const currentUsernames = currentMembers.map((m) => m.username);
      const newUsernames = members.map((m) => m.username);
      for (const currentMember of currentMembers) {
        if (!newUsernames.includes(currentMember.username)) {
          await api.removeProjectMember(project.project_id || project.id, currentMember.username);
        }
      }
      for (const member of members) {
        if (!currentUsernames.includes(member.username)) {
          await api.addProjectMember(project.project_id || project.id, member.username, member.role);
        } else {
          const currentMember = currentMembers.find((m) => m.username === member.username);
          if (currentMember && currentMember.role !== member.role) {
            await api.updateProjectMemberRole(project.project_id || project.id, member.username, member.role);
          }
        }
      }
      const updatedProject = await api.getProject(project.project_id || project.id);
      const updatedMembers = await api.getProjectMembers(project.project_id || project.id);
      setProjects((prev) =>
        prev.map((p) => {
          if ((p.project_id || p.id) === (project.project_id || project.id)) {
            return {
              ...p,
              name: updatedProject.name,
              desc: updatedProject.description || "",
              description: updatedProject.description || "",
              members: updatedMembers.map((m) => ({ username: m.username, role: m.role })),
              visibility: updatedProject.visibility || visibility,
              status: updatedProject.status || status,
              backupInterval: updatedProject.backup_interval || backupInterval,
              topoUrl: updatedProject.topo_url || topoUrl,
              topo_url: updatedProject.topo_url || topoUrl,
              updated_at: updatedProject.updated_at || updatedProject.created_at,
            };
          }
          return p;
        })
      );
      alert("✅ Project saved successfully");
    } catch (e) {
      setError("Failed to save: " + formatError(e));
    }
  };

  const changeRole = async (username, role) => {
    const member = members.find((m) => m.username === username);
    if (member && member.role === "admin") {
      setError("Cannot change admin role in project");
      return;
    }
    try {
      await api.updateProjectMemberRole(project.project_id || project.id, username, role);
      setMembers(members.map((m) => (m.username === username ? { ...m, role } : m)));
      setError("");
    } catch (e) {
      setError("Failed to update role: " + formatError(e));
    }
  };

  const remove = async (username) => {
    const member = members.find((m) => m.username === username);
    if (member && member.role === "admin") {
      setError("Cannot remove admin from project");
      return;
    }
    try {
      await api.removeProjectMember(project.project_id || project.id, username);
      setMembers(members.filter((m) => m.username !== username));
      setError("");
    } catch (e) {
      setError("Failed to remove member: " + e.message);
    }
  };

  const handleDeleteProject = async () => {
    if (deleteConfirm !== "Confirm Delete") {
      alert("Please type 'Confirm Delete' to proceed");
      return;
    }
    try {
      await api.deleteProject(project.project_id || project.id);
      setProjects((prev) => prev.filter((p) => (p.project_id || p.id) !== (project.project_id || project.id)));
      alert("✅ Project deleted successfully");
      goIndex();
    } catch (e) {
      setError("Failed to delete project: " + formatError(e));
    }
  };

  return (
    <div className="h-full flex flex-col min-h-0 overflow-y-auto">
      {/* Sticky header: title + action buttons (stays visible when scrolling) */}
      <div className="sticky top-0 z-10 flex-shrink-0 flex items-center justify-between py-3 px-1 mb-4 bg-slate-50 dark:bg-slate-950 border-b border-slate-200 dark:border-slate-800 shadow-sm dark:shadow-none">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">Project Settings</h2>
        <div className="flex items-center gap-2 flex-wrap justify-end">
          <Button 
            onClick={save} 
            className="bg-green-600 hover:bg-green-700 text-white border-green-600 focus:ring-green-500"
          >
            Save Changes
          </Button>
          {authedUser?.role === "admin" && (
            <Button variant="danger" onClick={() => setShowDeleteModal(true)}>
              Delete Project
            </Button>
          )}
        </div>
      </div>

      <div className="flex-1 min-h-0 space-y-6">
        <Card title="Project Information" className="flex-shrink-0">
          {/* Row 1: Project Name, Status, Visibility */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <Field label="Project Name">
              <Input 
                value={name} 
                onChange={(e) => setName(e.target.value)} 
                placeholder="Enter project name" 
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
                />
              </Field>
            </div>
          </div>

          {/* Row 2: Description */}
          <div className="mb-6">
            <Field label="Description">
              <textarea
                value={desc}
                onChange={(e) => setDesc(e.target.value)}
                placeholder="Enter project description..."
                rows={6}
                className="w-full px-3 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-200 placeholder-slate-500 dark:placeholder-slate-400 focus:border-blue-500 dark:focus:border-blue-400 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:focus:ring-blue-400 transition-colors resize-y"
              />
            </Field>
          </div>

          {/* Row 3: Topology Image */}
          <div>
            <Field label="Topology Image">
              <div className="space-y-4">
                <div className="flex items-center gap-3">
                  <label className="flex items-center justify-center px-4 py-2.5 text-sm font-medium rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 cursor-pointer transition-colors">
                    <span className="mr-2">📷</span>
                    Choose Image
                    <input
                      type="file"
                      accept="image/*"
                      onChange={(e) => handleFile(e.target.files?.[0])}
                      className="hidden"
                    />
                  </label>
                  {topoUrl && (
                    <span className="text-sm text-green-600 dark:text-green-400 flex items-center gap-1">
                      ✓ Image uploaded
                    </span>
                  )}
                </div>
                {error && (
                  <div className="text-sm text-rose-500 dark:text-rose-400 bg-rose-50 dark:bg-rose-900/20 border border-rose-200 dark:border-rose-800 rounded-lg px-3 py-2">
                    {safeDisplay(error)}
                  </div>
                )}
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
            <div className="flex flex-wrap items-center gap-2 w-full sm:w-auto sm:min-w-[280px]">
              <div className="flex-1 min-w-[180px] max-w-[280px]">
                <Select
                  value={newMemberUsername}
                  onChange={setNewMemberUsername}
                  onFocus={refetchUsers}
                  options={[
                    { value: "", label: "Add member..." },
                    ...usersAvailableToAdd.map((u) => ({ value: u.username, label: u.username })),
                  ]}
                  className="w-full text-sm"
                />
              </div>
              <div className="w-[100px] min-w-[90px] flex-shrink-0">
                <Select
                  value={addMemberRoleOptions.some((o) => o.value === newMemberRole) ? newMemberRole : "viewer"}
                  onChange={setNewMemberRole}
                  options={addMemberRoleOptions}
                  className="w-full text-sm"
                />
              </div>
              <Button
                onClick={async () => {
                  if (!newMemberUsername) return;
                  const role = addMemberRoleOptions.some((o) => o.value === newMemberRole) ? newMemberRole : "viewer";
                  try {
                    await api.addProjectMember(project.project_id || project.id, newMemberUsername, role);
                    setMembers([...members, { username: newMemberUsername, role }]);
                    setNewMemberUsername("");
                    setNewMemberRole("viewer");
                    setError("");
                  } catch (e) {
                    setError("Failed to add member: " + formatError(e));
                  }
                }}
                disabled={!newMemberUsername}
                className="text-xs px-3 flex-shrink-0"
              >
                Add
              </Button>
            </div>
          }
        >
          <div className="space-y-4">
            {error && (
              <div className="text-sm text-rose-500 dark:text-rose-400 bg-rose-50 dark:bg-rose-900/20 border border-rose-200 dark:border-rose-800 rounded-lg px-3 py-2">
                {safeDisplay(error)}
              </div>
            )}

            {/* Members list: each row has name, role (edit if allowed), delete (if allowed) */}
            <div>
              {members.length === 0 ? (
                <div className="text-center py-8 text-sm text-slate-500 dark:text-slate-400">
                  No members yet
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
                        {member.role === "admin" ? (
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
                            Admin
                          </span>
                        ) : canEditMember(member) ? (
                          <>
                            <Select
                              value={member.role}
                              onChange={(val) => changeRole(member.username, val)}
                              options={addMemberRoleOptions}
                              className="min-w-[100px]"
                            />
                            <Button
                              variant="danger"
                              onClick={() => remove(member.username)}
                              className="text-xs px-2 py-1"
                              title="Remove member"
                            >
                              Remove
                            </Button>
                          </>
                        ) : (
                          <>
                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300">
                              {member.role}
                            </span>
                            <span className="text-xs text-slate-400 dark:text-slate-500" title="Only admin can manage this role">
                              —
                            </span>
                          </>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </Card>
      </div>

      {showDeleteModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/50" onClick={() => setShowDeleteModal(false)} />
          <div className="relative z-10 w-full max-w-md">
            <Card
              title="Delete Project"
              actions={
                <Button variant="secondary" onClick={() => setShowDeleteModal(false)}>
                  Close
                </Button>
              }
            >
              <div className="grid gap-4">
                <div className="text-sm text-red-600 dark:text-red-400">
                  ⚠️ This action cannot be undone. All project data will be permanently deleted.
                </div>
                <Field label="Type 'Confirm Delete' to proceed">
                  <Input
                    value={deleteConfirm}
                    onChange={(e) => setDeleteConfirm(e.target.value)}
                    placeholder="Confirm Delete"
                  />
                </Field>
                <div className="flex gap-2 justify-end">
                  <Button variant="secondary" onClick={() => setShowDeleteModal(false)}>
                    Cancel
                  </Button>
                  <Button variant="danger" onClick={handleDeleteProject}>
                    Delete Project
                  </Button>
                </div>
              </div>
            </Card>
          </div>
        </div>
      )}
    </div>
  );
}
