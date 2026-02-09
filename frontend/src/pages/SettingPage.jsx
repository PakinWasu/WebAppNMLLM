import React, { useState, useEffect } from "react";
import * as api from "../api";
import { fileToDataURL } from "../utils/file";
import { safeDisplay } from "../utils/format";
import { Card, Button, Field, Input, Select, Table } from "../components/ui";
import AddMemberInline from "../components/AddMemberInline";

export default function SettingPage({ project, setProjects, authedUser, goIndex }) {
  const [name, setName] = useState(project.name);
  const [desc, setDesc] = useState(project.desc || project.description || "");
  const [backupInterval, setBackupInterval] = useState(
    project.backupInterval || project.backup_interval || "Daily"
  );
  const [visibility, setVisibility] = useState(project.visibility || "Private");
  const [topoUrl, setTopoUrl] = useState(project.topoUrl || project.topo_url || "");
  const [error, setError] = useState("");
  const [members, setMembers] = useState(project.members || []);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState("");
  const [availableUsers, setAvailableUsers] = useState([]);

  useEffect(() => {
    const loadData = async () => {
      try {
        const projectId = project.project_id || project.id;
        if (projectId) {
          const [membersData, projectData, usersData] = await Promise.all([
            api.getProjectMembers(projectId).catch(() => []),
            api.getProject(projectId).catch(() => null),
            api.getUsers().catch(() => []),
          ]);
          setMembers(membersData.map((m) => ({ username: m.username, role: m.role })));
          setAvailableUsers(usersData);
          if (projectData) {
            if (projectData.topo_url) setTopoUrl(projectData.topo_url);
            if (projectData.visibility) setVisibility(projectData.visibility);
            if (projectData.backup_interval) setBackupInterval(projectData.backup_interval);
          }
        }
      } catch (e) {
        console.error("Failed to load data:", e);
      }
    };
    loadData();
  }, [project.project_id, project.id]);

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
      setError("Failed to process image: " + (e.message || "Unknown error"));
    }
  };

  const save = async () => {
    setError("");
    try {
      await api.updateProject(project.project_id || project.id, name, desc, topoUrl, visibility, backupInterval);
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
      setError("Failed to save: " + e.message);
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
      const errorMessage =
        e && typeof e === "object"
          ? e.message || e.detail || (typeof e.detail !== "string" ? JSON.stringify(e) : e.detail)
          : typeof e === "string"
            ? e
            : "Failed to update role";
      setError("Failed to update role: " + errorMessage);
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
      setError("Failed to delete project: " + e.message);
    }
  };

  return (
    <div className="h-full flex flex-col min-h-0 overflow-hidden">
      <div className="flex-shrink-0 mb-6">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">Project Settings</h2>
        <p className="text-sm text-gray-500 dark:text-gray-400">Manage your project configuration and team members</p>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto overflow-x-hidden pr-2 space-y-6">
        <Card title="Project Information" className="flex-shrink-0">
          <div className="grid gap-6 md:grid-cols-2">
            <Field label="Project Name">
              <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Enter project name" />
            </Field>
            <Field label="Visibility">
              <Select
                value={visibility}
                onChange={setVisibility}
                options={[
                  { value: "Private", label: "Private" },
                  { value: "Shared", label: "Shared" },
                ]}
              />
            </Field>
            <Field label="Description">
              <Input value={desc} onChange={(e) => setDesc(e.target.value)} placeholder="Enter project description" />
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
              />
            </Field>
            <div className="md:col-span-2">
              <Field label="Topology Image">
                <div className="space-y-3">
                  <input
                    type="file"
                    accept="image/*"
                    onChange={(e) => handleFile(e.target.files?.[0])}
                    className="block w-full text-sm text-gray-500 dark:text-gray-400
                      file:mr-4 file:py-2 file:px-4
                      file:rounded-lg file:border-0
                      file:text-sm file:font-semibold
                      file:bg-slate-100 file:text-slate-800 file:border file:border-slate-300 file:rounded-lg file:px-3 file:py-1.5
                      hover:file:bg-slate-200
                      dark:file:bg-slate-700 dark:file:text-slate-100 dark:file:border-slate-600
                      dark:hover:file:bg-slate-600
                      cursor-pointer transition-colors"
                  />
                  {error && (
                    <div className="text-sm text-rose-500 dark:text-rose-400 bg-rose-50 dark:bg-rose-900/20 border border-rose-200 dark:border-rose-800 rounded-lg px-3 py-2">
                      {safeDisplay(error)}
                    </div>
                  )}
                  {topoUrl && (
                    <div className="mt-3">
                      <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">Preview:</p>
                      <div className="relative rounded-lg border border-slate-300 dark:border-gray-700 overflow-hidden bg-gray-50 dark:bg-gray-900/50">
                        <img
                          src={topoUrl}
                          alt="Topology preview"
                          className="w-full max-w-full h-auto max-h-96 object-contain"
                          style={{ imageRendering: "auto" }}
                        />
                      </div>
                    </div>
                  )}
                </div>
              </Field>
            </div>
          </div>
        </Card>

        <Card title="Team Members" className="flex-shrink-0">
          <div className="space-y-4">
            <div className="p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-slate-300 dark:border-gray-700">
              <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">Add New Member</h3>
              <AddMemberInline
                members={members}
                availableUsers={availableUsers}
                onAdd={async (u, role) => {
                  try {
                    await api.addProjectMember(project.project_id || project.id, u, role);
                    setMembers([...members, { username: u, role }]);
                    setError("");
                  } catch (e) {
                    setError("Failed to add member: " + e.message);
                  }
                }}
              />
            </div>
            {error && (
              <div className="text-sm text-rose-500 dark:text-rose-400 bg-rose-50 dark:bg-rose-900/20 border border-rose-200 dark:border-rose-800 rounded-lg px-3 py-2">
                {safeDisplay(error)}
              </div>
            )}
            <div>
              <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">Current Members</h3>
              <Table
                columns={[
                  {
                    header: "Username",
                    key: "username",
                    cell: (r) => (
                      <div className="font-medium text-gray-900 dark:text-gray-100">{r.username}</div>
                    ),
                  },
                  {
                    header: "Role",
                    key: "role",
                    cell: (r) => {
                      const isAdmin = r.role === "admin";
                      if (isAdmin) {
                        return (
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
                            {r.role}
                          </span>
                        );
                      }
                      return (
                        <Select
                          value={r.role}
                          onChange={(val) => changeRole(r.username, val)}
                          options={[
                            { value: "manager", label: "Manager" },
                            { value: "engineer", label: "Engineer" },
                            { value: "viewer", label: "Viewer" },
                          ]}
                          className="min-w-[120px]"
                        />
                      );
                    },
                  },
                  {
                    header: "Actions",
                    key: "x",
                    cell: (r) =>
                      r.role === "admin" ? (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400">
                          Protected
                        </span>
                      ) : (
                        <Button variant="danger" onClick={() => remove(r.username)} className="text-xs">
                          Remove
                        </Button>
                      ),
                  },
                ]}
                data={members}
                empty="No members added yet"
              />
            </div>
          </div>
        </Card>
      </div>

      <div className="flex-shrink-0 flex items-center justify-between pt-4 border-t border-slate-300 dark:border-gray-700 mt-6">
        <div className="flex gap-3">
          <Button onClick={save} variant="primary">
            Save Changes
          </Button>
        </div>
        {authedUser?.role === "admin" && (
          <Button variant="danger" onClick={() => setShowDeleteModal(true)}>
            Delete Project
          </Button>
        )}
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
