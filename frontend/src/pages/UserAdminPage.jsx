import React, { useState, useEffect } from "react";
import * as api from "../api";
import { Card, Field, Input, PasswordInput, Button, Table, ConfirmationModal } from "../components/ui";
import { formatError, formatDateTime, safeDisplay } from "../utils/format";

export default function UserAdminPage({
  indexHref = "#/",
  users,
  setUsers,
  onClose,
  handleNavClick,
}) {
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [phoneNumber, setPhoneNumber] = useState("");
  const [tempPwd, setTempPwd] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  
  // Delete user confirmation modal state
  const [deleteModal, setDeleteModal] = useState({ show: false, username: null });
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    const loadUsers = async () => {
      try {
        const updated = await api.getUsers();
        setUsers(updated);
      } catch (e) {
        console.error("Failed to load users:", e);
      }
    };
    loadUsers();
  }, [setUsers]);

  const create = async () => {
    if (!username || !email) {
      setError("Username and email are required");
      return;
    }
    
    // Check for duplicate email in existing users
    const emailLower = email.toLowerCase().trim();
    const duplicateEmail = users.find(u => u.email && u.email.toLowerCase() === emailLower);
    if (duplicateEmail) {
      setError(`Email "${email}" is already used by user "${duplicateEmail.username}"`);
      return;
    }
    
    // Check for duplicate username
    const usernameLower = username.toLowerCase().trim();
    const duplicateUsername = users.find(u => u.username && u.username.toLowerCase() === usernameLower);
    if (duplicateUsername) {
      setError(`Username "${username}" already exists`);
      return;
    }
    
    setError("");
    setLoading(true);
    try {
      const result = await api.createUser(
        username,
        email,
        phoneNumber || undefined,
        tempPwd || undefined
      );
      const tempPassword = result.temp_password || tempPwd || "123456";
      alert(`User created! Temporary password: ${tempPassword}`);
      const updated = await api.getUsers();
      setUsers(updated);
      setUsername("");
      setEmail("");
      setPhoneNumber("");
      setTempPwd("");
    } catch (e) {
      setError(formatError(e) || "Failed to create user");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="h-full flex flex-col min-h-0 overflow-y-auto">
      <div className="sticky top-0 z-10 flex-shrink-0 flex items-center justify-between py-3 px-1 mb-4 bg-slate-50 dark:bg-slate-950 border-b border-slate-200 dark:border-slate-800 shadow-sm dark:shadow-none">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">User Administration</h2>
        <div className="flex items-center gap-2 flex-wrap justify-end">
          <Button variant="secondary" onClick={(e) => handleNavClick && handleNavClick(e, onClose)}>
            ← Back to Index
          </Button>
        </div>
      </div>
      <div className="flex-1 min-h-0 space-y-6">
      <Card title="Create Account" className="flex-shrink-0">
        <div className="grid gap-4">
          <div className="grid gap-3 md:grid-cols-2">
            <Field label="Username">
              <Input
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                disabled={loading}
                placeholder="Enter username"
              />
            </Field>
            <Field label="Email">
              <Input
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                type="email"
                disabled={loading}
                placeholder="Enter email"
              />
            </Field>
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            <Field label="Password">
              <PasswordInput
                value={tempPwd}
                onChange={(e) => setTempPwd(e.target.value)}
                placeholder="Enter temporary password"
                disabled={loading}
              />
            </Field>
            <Field label="Phone Number">
              <Input
                value={phoneNumber}
                onChange={(e) => setPhoneNumber(e.target.value)}
                type="tel"
                disabled={loading}
                placeholder="Enter phone number"
              />
            </Field>
          </div>
        </div>
        {error && (
          <div className="mt-3 text-sm text-rose-500 dark:text-rose-400 bg-rose-50 dark:bg-rose-900/20 border border-rose-200 dark:border-rose-800 rounded-lg px-3 py-2">
            {formatError(error)}
          </div>
        )}
        <div className="mt-4 flex gap-2">
          <Button onClick={create} disabled={loading}>
            {loading ? "Creating..." : "Create"}
          </Button>
          <Button variant="secondary" onClick={onClose} disabled={loading}>
            Close
          </Button>
        </div>
      </Card>
      <Card title="Existing Users" className="flex-shrink-0">
        <Table
          columns={[
            {
              header: "Username",
              key: "username",
              cell: (row) => (
                <div className="font-medium text-gray-900 dark:text-gray-100">
                  {safeDisplay(row?.username)}
                </div>
              ),
            },
            {
              header: "Email",
              key: "email",
              cell: (row) => (
                <div className="text-gray-700 dark:text-gray-300">
                  {safeDisplay(row?.email) || "-"}
                </div>
              ),
            },
            {
              header: "Phone Number",
              key: "phone_number",
              cell: (row) => (
                <div className="text-gray-700 dark:text-gray-300">
                  {safeDisplay(row?.phone_number) || "-"}
                </div>
              ),
            },
            {
              header: "Last login",
              key: "last_login_at",
              cell: (row) => (
                <div className="text-sm text-gray-600 dark:text-gray-400">
                  {row?.last_login_at != null
                    ? safeDisplay(formatDateTime(row.last_login_at))
                    : "-"}
                </div>
              ),
            },
            {
              header: "Actions",
              key: "actions",
              cell: (row) =>
                row.username !== "admin" ? (
                  <Button 
                    variant="danger" 
                    onClick={() => setDeleteModal({ show: true, username: row.username })}
                    className="text-sm"
                  >
                    Delete
                  </Button>
                ) : (
                  <span className="text-xs text-gray-400 dark:text-gray-500 px-2 py-1 bg-gray-100 dark:bg-gray-800 rounded">
                    Protected
                  </span>
                ),
            },
          ]}
          data={users}
          empty="No users yet"
        />
      </Card>
      </div>
      
      {/* Delete User Confirmation Modal */}
      <ConfirmationModal
        show={deleteModal.show}
        onClose={() => setDeleteModal({ show: false, username: null })}
        onConfirm={async () => {
          if (!deleteModal.username) return;
          setDeleting(true);
          try {
            await api.deleteUser(deleteModal.username);
            const updated = await api.getUsers();
            setUsers(updated);
            setDeleteModal({ show: false, username: null });
          } catch (e) {
            alert("Failed to delete user: " + formatError(e));
          } finally {
            setDeleting(false);
          }
        }}
        title="Delete User"
        message={`Are you sure you want to delete user "${deleteModal.username}"? This action cannot be undone.`}
        confirmText="Delete"
        cancelText="Cancel"
        variant="danger"
        loading={deleting}
      />
    </div>
  );
}
