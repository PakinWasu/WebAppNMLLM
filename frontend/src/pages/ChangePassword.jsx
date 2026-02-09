import React, { useState } from "react";
import * as api from "../api";
import { Card, Button, Field, Input, PasswordInput } from "../components/ui";
import { safeDisplay } from "../utils/format";

export default function ChangePassword({
  initialUsername = "",
  isLoggedIn = false,
  goBack,
}) {
  const [username, setUsername] = useState(initialUsername);
  const [oldPw, setOldPw] = useState("");
  const [newPw, setNewPw] = useState("");
  const [cf, setCf] = useState("");
  const [msg, setMsg] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async () => {
    if (!oldPw || !newPw || !cf) {
      setMsg("❌ Please fill in all fields");
      return;
    }
    if (newPw.length < 6) {
      setMsg("❌ New password must be at least 6 characters");
      return;
    }
    if (newPw !== cf) {
      setMsg("❌ Password confirmation does not match");
      return;
    }
    setMsg("");
    setLoading(true);
    try {
      const token = api.getToken();
      if (!token && !isLoggedIn) {
        setMsg("❌ Please login first to change password");
        setLoading(false);
        return;
      }
      await api.changePassword(oldPw, newPw);
      setMsg("✅ Password changed successfully." + (isLoggedIn ? "" : " You can sign in now."));
      setTimeout(() => goBack(), 2000);
    } catch (e) {
      let errorMsg = e.message || "Failed to change password. Please check your current password.";
      if (errorMsg.includes("401") || errorMsg.includes("Unauthorized")) {
        errorMsg = "Session expired. Please login again.";
      } else if (errorMsg.includes("400") || errorMsg.includes("Wrong")) {
        errorMsg = "Current password is incorrect. Please try again.";
      }
      setMsg("❌ " + errorMsg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="grid place-items-center py-12">
      <Card className="w-full max-w-md" title="Change Password">
        <div className="grid gap-3">
          <Field label="Username">
            <Input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Enter username"
              disabled={loading || isLoggedIn}
            />
          </Field>
          <Field label="Current password">
            <PasswordInput
              value={oldPw}
              onChange={(e) => setOldPw(e.target.value)}
              placeholder="Enter current password"
              disabled={loading}
            />
          </Field>
          <Field label="New password">
            <PasswordInput
              value={newPw}
              onChange={(e) => setNewPw(e.target.value)}
              placeholder="Enter new password (min 6 characters)"
              disabled={loading}
            />
          </Field>
          <Field label="Confirm new password">
            <PasswordInput
              value={cf}
              onChange={(e) => setCf(e.target.value)}
              placeholder="Confirm new password"
              disabled={loading}
            />
          </Field>
          {msg && (
            <div
              className={`text-sm ${
                msg.startsWith("✅") ? "text-green-600 dark:text-green-400" : "text-rose-400"
              }`}
            >
              {safeDisplay(msg)}
            </div>
          )}
          <div className="flex gap-2">
            <Button onClick={submit} disabled={loading}>
              {loading ? "Updating..." : "Update"}
            </Button>
            <Button variant="secondary" onClick={goBack} disabled={loading}>
              Back
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
}
