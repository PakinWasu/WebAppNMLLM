import React, { useState } from "react";
import * as api from "../api";
import { Card, Button, Field, Input, PasswordInput } from "../components/ui";
import { safeDisplay, formatError } from "../utils/format";

const STEPS = {
  EMAIL: "email",
  OTP: "otp",
  RESET: "reset",
  SUCCESS: "success",
};

export default function ForgotPassword({ goBack }) {
  const [step, setStep] = useState(STEPS.EMAIL);
  const [email, setEmail] = useState("");
  const [otp, setOtp] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [username, setUsername] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  const handleRequestOTP = async (e) => {
    e?.preventDefault();
    if (!email.trim()) {
      setError("Please enter your email address");
      return;
    }
    if (!email.includes("@")) {
      setError("Please enter a valid email address");
      return;
    }

    setError("");
    setLoading(true);
    try {
      const result = await api.forgotPassword(email.trim());
      setMessage(result.message || "Verification code sent to your email.");
      setStep(STEPS.OTP);
    } catch (e) {
      setError(formatError(e) || "Failed to send verification code");
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyOTP = async (e) => {
    e?.preventDefault();
    if (!otp.trim()) {
      setError("Please enter the verification code");
      return;
    }
    if (otp.trim().length !== 6) {
      setError("Verification code must be 6 digits");
      return;
    }

    setError("");
    setLoading(true);
    try {
      const result = await api.verifyOTP(email.trim(), otp.trim());
      setUsername(result.username || "");
      setMessage("Code verified successfully!");
      setStep(STEPS.RESET);
    } catch (e) {
      setError(formatError(e) || "Invalid verification code");
    } finally {
      setLoading(false);
    }
  };

  const handleResetPassword = async (e) => {
    e?.preventDefault();
    if (!newPassword.trim()) {
      setError("Please enter a new password");
      return;
    }
    if (newPassword.length < 4) {
      setError("Password must be at least 4 characters");
      return;
    }
    if (newPassword !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }

    setError("");
    setLoading(true);
    try {
      await api.resetPassword(email.trim(), newPassword);
      setMessage("Password reset successfully!");
      setStep(STEPS.SUCCESS);
    } catch (e) {
      setError(formatError(e) || "Failed to reset password");
    } finally {
      setLoading(false);
    }
  };

  const handleResendOTP = async () => {
    setError("");
    setLoading(true);
    try {
      await api.forgotPassword(email.trim());
      setMessage("New verification code sent to your email.");
      setOtp("");
    } catch (e) {
      setError(formatError(e) || "Failed to resend code");
    } finally {
      setLoading(false);
    }
  };

  const renderEmailStep = () => (
    <form onSubmit={handleRequestOTP} className="grid gap-4">
      <p className="text-sm text-slate-600 dark:text-slate-400">
        Enter your email address and we'll send you a verification code to reset your password.
      </p>
      <Field label="Email Address">
        <Input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="Enter your email"
          disabled={loading}
          autoComplete="email"
          autoFocus
        />
      </Field>
      {error && <ErrorMessage message={error} />}
      <div className="flex gap-3 justify-end">
        <Button type="button" variant="secondary" onClick={goBack} disabled={loading}>
          Back to Login
        </Button>
        <Button type="submit" disabled={loading}>
          {loading ? "Sending..." : "Send Code"}
        </Button>
      </div>
    </form>
  );

  const renderOTPStep = () => (
    <form onSubmit={handleVerifyOTP} className="grid gap-4">
      <div className="text-center">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-blue-100 dark:bg-blue-900/30 mb-4">
          <svg className="w-8 h-8 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
          </svg>
        </div>
        <p className="text-sm text-slate-600 dark:text-slate-400">
          We've sent a 6-digit verification code to<br />
          <span className="font-medium text-slate-800 dark:text-slate-200">{email}</span>
        </p>
      </div>
      <Field label="Verification Code">
        <Input
          type="text"
          value={otp}
          onChange={(e) => setOtp(e.target.value.replace(/\D/g, "").slice(0, 6))}
          placeholder="Enter 6-digit code"
          disabled={loading}
          autoComplete="one-time-code"
          autoFocus
          className="text-center text-2xl tracking-widest font-mono"
          maxLength={6}
        />
      </Field>
      {message && <SuccessMessage message={message} />}
      {error && <ErrorMessage message={error} />}
      <div className="flex gap-3 justify-between items-center">
        <button
          type="button"
          onClick={handleResendOTP}
          disabled={loading}
          className="text-sm text-blue-600 dark:text-blue-400 hover:underline disabled:opacity-50"
        >
          Resend code
        </button>
        <div className="flex gap-3">
          <Button type="button" variant="secondary" onClick={() => setStep(STEPS.EMAIL)} disabled={loading}>
            Back
          </Button>
          <Button type="submit" disabled={loading || otp.length !== 6}>
            {loading ? "Verifying..." : "Verify"}
          </Button>
        </div>
      </div>
    </form>
  );

  const renderResetStep = () => (
    <form onSubmit={handleResetPassword} className="grid gap-4">
      <div className="text-center mb-2">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-green-100 dark:bg-green-900/30 mb-4">
          <svg className="w-8 h-8 text-green-600 dark:text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <p className="text-sm text-slate-600 dark:text-slate-400">
          Code verified! Set a new password for<br />
          <span className="font-medium text-slate-800 dark:text-slate-200">{username || email}</span>
        </p>
      </div>
      <Field label="New Password">
        <PasswordInput
          value={newPassword}
          onChange={(e) => setNewPassword(e.target.value)}
          placeholder="Enter new password"
          disabled={loading}
          autoFocus
        />
      </Field>
      <Field label="Confirm Password">
        <PasswordInput
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
          placeholder="Confirm new password"
          disabled={loading}
        />
      </Field>
      {error && <ErrorMessage message={error} />}
      <div className="flex gap-3 justify-end">
        <Button type="submit" disabled={loading}>
          {loading ? "Resetting..." : "Reset Password"}
        </Button>
      </div>
    </form>
  );

  const renderSuccessStep = () => (
    <div className="text-center py-4">
      <div className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-green-100 dark:bg-green-900/30 mb-6">
        <svg className="w-10 h-10 text-green-600 dark:text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
        </svg>
      </div>
      <h3 className="text-lg font-semibold text-slate-800 dark:text-slate-200 mb-2">
        Password Reset Successfully!
      </h3>
      <p className="text-sm text-slate-600 dark:text-slate-400 mb-6">
        Your password has been reset. You can now sign in with your new password.
      </p>
      <Button onClick={goBack}>
        Back to Sign In
      </Button>
    </div>
  );

  const getTitle = () => {
    switch (step) {
      case STEPS.EMAIL:
        return "Forgot Password";
      case STEPS.OTP:
        return "Enter Verification Code";
      case STEPS.RESET:
        return "Set New Password";
      case STEPS.SUCCESS:
        return "Success";
      default:
        return "Forgot Password";
    }
  };

  return (
    <div className="grid place-items-center py-16">
      <Card className="w-full max-w-md" title={getTitle()}>
        {step === STEPS.EMAIL && renderEmailStep()}
        {step === STEPS.OTP && renderOTPStep()}
        {step === STEPS.RESET && renderResetStep()}
        {step === STEPS.SUCCESS && renderSuccessStep()}
      </Card>
    </div>
  );
}

function ErrorMessage({ message }) {
  return (
    <div className="text-sm text-rose-500 dark:text-rose-400 bg-rose-50 dark:bg-rose-900/20 border border-rose-200 dark:border-rose-800 rounded-lg px-3 py-2 flex items-start gap-2">
      <svg className="w-5 h-5 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <span>{safeDisplay(message)}</span>
    </div>
  );
}

function SuccessMessage({ message }) {
  return (
    <div className="text-sm text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg px-3 py-2 flex items-start gap-2">
      <svg className="w-5 h-5 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <span>{safeDisplay(message)}</span>
    </div>
  );
}
