"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useEffect, useState } from "react";

import { changePassword, getSession, updateProfile } from "@/lib/auth-api";
import { ApiRequestError } from "@/lib/api";
import type { AuthUser } from "@/types/auth";

function initials(fullName: string): string {
  return fullName
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("") || "U";
}

export function UserSettings() {
  const router = useRouter();
  const [user, setUser] = useState<AuthUser | null>(null);
  const [fullName, setFullName] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [profileMessage, setProfileMessage] = useState<string | null>(null);
  const [passwordMessage, setPasswordMessage] = useState<string | null>(null);
  const [profileError, setProfileError] = useState<string | null>(null);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [savingProfile, setSavingProfile] = useState(false);
  const [savingPassword, setSavingPassword] = useState(false);

  useEffect(() => {
    getSession()
      .then(({ user: sessionUser }) => {
        if (sessionUser.role === "admin") {
          router.replace("/admin");
          return;
        }
        setUser(sessionUser);
        setFullName(sessionUser.full_name);
      })
      .catch((requestError: unknown) => {
        if (requestError instanceof ApiRequestError && requestError.status === 401) {
          router.replace("/login");
          return;
        }
        setProfileError(requestError instanceof Error ? requestError.message : "Unable to load settings.");
      });
  }, [router]);

  async function handleProfileSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSavingProfile(true);
    setProfileError(null);
    setProfileMessage(null);
    try {
      const { user: updatedUser } = await updateProfile(fullName);
      setUser(updatedUser);
      setFullName(updatedUser.full_name);
      setProfileMessage("Your profile name was updated.");
    } catch (requestError) {
      setProfileError(requestError instanceof Error ? requestError.message : "Unable to update profile.");
    } finally {
      setSavingProfile(false);
    }
  }

  async function handlePasswordSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPasswordError(null);
    setPasswordMessage(null);
    if (newPassword !== confirmPassword) {
      setPasswordError("The new passwords do not match.");
      return;
    }

    setSavingPassword(true);
    try {
      await changePassword(currentPassword, newPassword);
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setPasswordMessage("Your password was changed successfully.");
    } catch (requestError) {
      setPasswordError(requestError instanceof Error ? requestError.message : "Unable to change password.");
    } finally {
      setSavingPassword(false);
    }
  }

  if (!user) {
    return <main className="portal-loading">{profileError ?? "Loading account settings…"}</main>;
  }

  return (
    <main className="settings-page">
      <nav className="settings-nav" aria-label="Settings navigation">
        <Link className="portal-brand" href="/dashboard">StockAI <small>Account settings</small></Link>
        <Link className="settings-back" href="/dashboard">← Back to dashboard</Link>
      </nav>

      <section className="settings-content">
        <header className="settings-header">
          <span className="settings-avatar" aria-hidden="true">{initials(user.full_name)}</span>
          <div>
            <span className="kicker">PERSONAL ACCOUNT</span>
            <h1>Profile &amp; security.</h1>
            <p>Keep your identity current and protect access to your portfolio.</p>
          </div>
        </header>

        <div className="settings-grid">
          <section className="settings-card">
            <div className="settings-card-heading">
              <span>01</span>
              <div><h2>Profile information</h2><p>This name appears in your StockAI workspace.</p></div>
            </div>
            <form className="settings-form" onSubmit={handleProfileSubmit}>
              <label>Full name<input value={fullName} onChange={(event) => setFullName(event.target.value)} minLength={2} maxLength={100} autoComplete="name" required /></label>
              <label>Email address<input type="email" value={user.email} readOnly aria-readonly="true" /></label>
              <p className="settings-help">Email changes stay locked until verified-email and account-recovery protections are implemented.</p>
              {profileError && <p className="settings-error" role="alert">{profileError}</p>}
              {profileMessage && <p className="settings-success" role="status">{profileMessage}</p>}
              <button className="primary-action" type="submit" disabled={savingProfile || fullName.trim() === user.full_name}>{savingProfile ? "Saving…" : "Save profile"}</button>
            </form>
          </section>

          <section className="settings-card">
            <div className="settings-card-heading">
              <span>02</span>
              <div><h2>Change password</h2><p>Confirm the current password before creating a new one.</p></div>
            </div>
            <form className="settings-form" onSubmit={handlePasswordSubmit}>
              <label>Current password<input type="password" value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} autoComplete="current-password" required /></label>
              <label>New password<input type="password" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} minLength={8} maxLength={128} autoComplete="new-password" required /></label>
              <label>Confirm new password<input type="password" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} minLength={8} maxLength={128} autoComplete="new-password" required /></label>
              <p className="settings-help">Use at least 8 characters. Do not reuse your current password.</p>
              {passwordError && <p className="settings-error" role="alert">{passwordError}</p>}
              {passwordMessage && <p className="settings-success" role="status">{passwordMessage}</p>}
              <button className="primary-action" type="submit" disabled={savingPassword}>{savingPassword ? "Changing…" : "Change password"}</button>
            </form>
          </section>
        </div>
      </section>
    </main>
  );
}
