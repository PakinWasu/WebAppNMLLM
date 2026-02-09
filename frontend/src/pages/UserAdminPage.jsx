import React, { useState, useEffect } from "react";
import * as api from "../api";
import { Card, Field, Input, PasswordInput, Button, Table } from "../components/ui";
import { safeDisplay, formatDateTime } from "../utils/format";

function PasswordDisplayCell({ tempPassword }) {
  const [showPassword, setShowPassword] = useState(false);
  if (!tempPassword) {
    return (
      <span className="text-xs text-gray-400 dark:text-gray-500 italic">
        Not available
      </span>
    );
  }
  return (
    <div className="flex items-center gap-0.5">
      <span className="font-mono text-sm text-gray-700 dark:text-gray-300">
        {showPassword ? tempPassword : "••••••••"}
      </span>
      <button
        type="button"
        onClick={() => setShowPassword(!showPassword)}
        className="p-0.5 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500 rounded transition-colors"
        aria-label={showPassword ? "Hide password" : "Show password"}
      >
        {showPassword ? (
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
          </svg>
        ) : (
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
          </svg>
        )}
      </button>
    </div>
  );
}

function DeleteUserButton({ username, onDelete }) {
  const [showConfirm, setShowConfirm] = useState(false);
  const [confirmText, setConfirmText] = useState("");
  const [deleting, setDeleting] = useState(false);

  const handleDelete = async () => {
    if (confirmText.toLowerCase() !== "delete") {
      alert('Please type "delete" to confirm');
      return;
    }
    setDeleting(true);
    try {
      await onDelete();
      setShowConfirm(false);
      setConfirmText("");
    } catch (e) {
      // Error handled in onDelete
    } finally {
      setDeleting(false);
    }
  };

  if (!showConfirm) {
    return (
      <Button variant="danger" onClick={() => setShowConfirm(true)} className="text-sm">
        Delete
      </Button>
    );
  }
  return (
    <div className="flex items-center gap-2">
      <Input
        value={confirmText}
        onChange={(e) => setConfirmText(e.target.value)}
        placeholder='Type "delete"'
        className="w-32 text-sm"
        disabled={deleting}
        onKeyDown={(e) => {
          if (e.key === "Enter" && confirmText.toLowerCase() === "delete") {
            handleDelete();
          } else if (e.key === "Escape") {
            setShowConfirm(false);
            setConfirmText("");
          }
        }}
      />
      <Button
        variant="danger"
        onClick={handleDelete}
        disabled={confirmText.toLowerCase() !== "delete" || deleting}
        className="text-sm"
      >
        {deleting ? "Deleting..." : "Confirm"}
      </Button>
      <Button
        variant="secondary"
        onClick={() => {
          setShowConfirm(false);
          setConfirmText("");
        }}
        disabled={deleting}
        className="text-sm"
      >
        Cancel
      </Button>
    </div>
  );
}

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
      setError(e.message || "Failed to create user");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="grid gap-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">User Administration</h2>
        <a
          href={indexHref}
          onClick={(e) => handleNavClick(e, onClose)}
          className="inline-flex items-center justify-center rounded-lg px-3 py-1.5 text-xs font-medium shadow-sm transition focus:outline-none focus:ring-2 focus:ring-offset-2 bg-white text-gray-900 ring-1 ring-gray-300 hover:bg-gray-50 focus:ring-blue-500 dark:bg-gray-800 dark:text-gray-100 dark:ring-gray-600 dark:hover:bg-gray-700"
        >
          ← Back to Index
        </a>
      </div>
      <Card title="Create Account">
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
            {safeDisplay(error)}
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
      <Card title="Existing Users">
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
              header: "Password",
              key: "temp_password",
              cell: (row) => (
                <PasswordDisplayCell tempPassword={row.temp_password} />
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
                  <DeleteUserButton
                    username={row.username}
                    onDelete={async () => {
                      try {
                        await api.deleteUser(row.username);
                        const updated = await api.getUsers();
                        setUsers(updated);
                        alert(`User "${row.username}" deleted successfully`);
                      } catch (e) {
                        alert("Failed to delete user: " + e.message);
                      }
                    }}
                  />
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
  );
}
