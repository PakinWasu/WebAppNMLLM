import React, { useState, useEffect } from "react";
import * as api from "../api";
import { Card, Button, Field, Input, PasswordInput } from "../components/ui";
import { safeDisplay, formatError } from "../utils/format";

export default function ChangePassword({
  initialUsername = "",
  isLoggedIn = false,
  goBack,
}) {
  const [username, setUsername] = useState(initialUsername);
  const [email, setEmail] = useState("");
  const [phoneNumber, setPhoneNumber] = useState("");
  const [oldPw, setOldPw] = useState("");
  const [newPw, setNewPw] = useState("");
  const [cf, setCf] = useState("");
  const [msg, setMsg] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isLoggedIn && api.getToken()) {
      api.getMe()
        .then((me) => {
          setUsername(me.username || initialUsername);
          setEmail(me.email || "");
          setPhoneNumber(me.phone_number ?? "");
        })
        .catch(() => {});
    } else {
      setUsername(initialUsername);
    }
  }, [isLoggedIn, initialUsername]);

  const submit = async () => {
    // Current password is always required for saving
    if (!oldPw) {
      setMsg("❌ Current password is required to save changes");
      return;
    }

    // If changing password, both New password and Confirm must be filled
    const wantPasswordChange = !!(newPw || cf);
    if (wantPasswordChange) {
      if (!newPw || !cf) {
        setMsg("❌ Both New password and Confirm new password are required to change password");
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
    }

    setMsg("");
    setLoading(true);
    try {
      const token = api.getToken();
      if (!token && !isLoggedIn) {
        setMsg("❌ Please login first");
        setLoading(false);
        return;
      }

      // Verify current password first (always required)
      await api.verifyPassword(oldPw);

      // Update profile if logged in
      if (isLoggedIn) {
        await api.updateMyProfile(email, phoneNumber);
      }

      // Change password if both new password fields are filled
      if (wantPasswordChange) {
        await api.changePassword(oldPw, newPw);
      }

      const done = [];
      if (isLoggedIn) done.push("Profile updated");
      if (wantPasswordChange) done.push("Password changed");
      setMsg("✅ " + (done.length ? done.join(". ") : "Saved") + (isLoggedIn ? "" : " You can sign in now."));
      setTimeout(() => goBack(), 2000);
    } catch (e) {
      let errorMsg = formatError(e) || "Failed to save.";
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
      <Card className="w-full max-w-md" title="Change Password & Information">
        <div className="grid gap-3">
          <Field label="Username">
            <Input
              value={username}
              readOnly
              placeholder="Username"
              disabled
              className="bg-slate-100 dark:bg-slate-800 cursor-not-allowed"
            />
          </Field>
          <Field label="Email">
            <Input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Enter email"
              disabled={loading || !isLoggedIn}
            />
          </Field>
          <Field label="Phone number">
            <Input
              value={phoneNumber}
              onChange={(e) => setPhoneNumber(e.target.value)}
              placeholder="Enter phone number"
              disabled={loading || !isLoggedIn}
            />
          </Field>
          <Field label="New password">
            <PasswordInput
              value={newPw}
              onChange={(e) => setNewPw(e.target.value)}
              placeholder="Enter new password (min 6 characters) - leave blank if not changing"
              disabled={loading}
            />
          </Field>
          <Field label="Confirm new password">
            <PasswordInput
              value={cf}
              onChange={(e) => setCf(e.target.value)}
              placeholder="Confirm new password - leave blank if not changing"
              disabled={loading}
            />
          </Field>
          <Field label="Current password (required to save)">
            <PasswordInput
              value={oldPw}
              onChange={(e) => setOldPw(e.target.value)}
              placeholder="Enter current password (required)"
              disabled={loading}
              className="!border-2 !border-blue-500 dark:!border-blue-400 focus:!ring-2 focus:!ring-blue-500 dark:focus:!ring-blue-400 bg-blue-50/50 dark:bg-blue-900/20 font-medium"
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
              {loading ? "Saving..." : "Save"}
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
