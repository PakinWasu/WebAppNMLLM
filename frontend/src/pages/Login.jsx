import React, { useState } from "react";
import * as api from "../api";
import { Card, Button, Field, Input, PasswordInput } from "../components/ui";
import { safeDisplay } from "../utils/format";

export default function Login({ onLogin }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e?.preventDefault();
    if (!username.trim() || !password.trim()) {
      setError("Please enter username or email and password");
      return;
    }
    setError("");
    setLoading(true);
    try {
      await onLogin(username.trim(), password);
    } catch (e) {
      let errorMsg = e.message || "Login failed";
      if (errorMsg.includes("Cannot connect")) {
        errorMsg = "Cannot connect to server. Please check if the backend is running.";
      } else if (errorMsg.includes("401") || errorMsg.includes("Invalid")) {
        errorMsg = "Invalid username or password. Please try again.";
      } else if (errorMsg.includes("Request failed")) {
        errorMsg = "Login failed. Please check your credentials and try again.";
      }
      setError(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="grid place-items-center py-16">
      <Card className="w-full max-w-md" title="Sign in">
        <form onSubmit={handleSubmit} className="grid gap-3">
          <Field label="Username or Email">
            <Input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Enter username or email"
              disabled={loading}
              autoComplete="username"
              type="text"
            />
          </Field>
          <Field label="Password">
            <PasswordInput
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter password"
              disabled={loading}
            />
          </Field>
          {error && (
            <div className="text-sm text-rose-500 dark:text-rose-400 bg-rose-50 dark:bg-rose-900/20 border border-rose-200 dark:border-rose-800 rounded-lg px-3 py-2 flex items-start gap-2">
              <svg className="w-5 h-5 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span>{safeDisplay(error)}</span>
            </div>
          )}
          <div className="flex justify-end">
            <Button type="submit" disabled={loading}>
              {loading ? "Signing in..." : "Sign in"}
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}
