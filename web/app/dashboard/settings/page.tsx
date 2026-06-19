"use client";

import { useEffect, useState } from "react";
import { fetchProfile, saveProfile, type ProfileData } from "@/lib/api";
import { ThemeToggle } from "@/components/ThemeToggle";

export default function SettingsPage() {
  const [profile, setProfile] = useState<ProfileData>({
    roles: [],
    skills: [],
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    setLoading(true);
    fetchProfile().then((data) => {
      if (data) setProfile(data);
      setLoading(false);
    });
  }, []);

  const handleSave = async () => {
    setSaving(true);
    setMessage("");
    try {
      await saveProfile(profile);
      setMessage("Preferences saved successfully.");
      setTimeout(() => setMessage(""), 3000);
    } catch (err) {
      setMessage("Failed to save preferences.");
    }
    setSaving(false);
  };

  const updateArray = (field: keyof ProfileData, value: string) => {
    const arr = value
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    setProfile({ ...profile, [field]: arr });
  };

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h1
          className="text-2xl md:text-3xl font-semibold text-[var(--color-text)] tracking-tight"
          style={{ fontFamily: "var(--font-heading)" }}
        >
          Settings
        </h1>
        <p className="mt-1 text-sm text-[var(--color-text-secondary)]">
          Manage your job matching preferences and account details.
        </p>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20 text-[var(--color-accent)]">
          Loading...
        </div>
      ) : (
        <div className="space-y-6 animate-fade-in-up">
          {/* Preferences */}
          <div className="glass rounded-2xl p-6 space-y-6">
            <h2 className="text-lg font-semibold text-[var(--color-text)] flex items-center gap-2">
              Matching Preferences
            </h2>

            <div className="space-y-4">
              <div className="space-y-2">
                <label className="text-sm font-medium text-[var(--color-text-secondary)] flex items-center gap-2">
                  Target Roles
                </label>
                <input
                  type="text"
                  placeholder="e.g. Backend Engineer, Full Stack, Data Scientist (comma separated)"
                  value={profile.roles.join(", ")}
                  onChange={(e) => updateArray("roles", e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl bg-[var(--color-surface-3)] border border-[var(--color-border)] text-sm text-[var(--color-text)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-accent)]/50 transition-colors"
                />
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-[var(--color-text-secondary)] flex items-center gap-2">
                  Core Skills
                </label>
                <input
                  type="text"
                  placeholder="e.g. Python, React, Postgres, AWS (comma separated)"
                  value={profile.skills.join(", ")}
                  onChange={(e) => updateArray("skills", e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl bg-[var(--color-surface-3)] border border-[var(--color-border)] text-sm text-[var(--color-text)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-accent)]/50 transition-colors"
                />
              </div>
            </div>
          </div>

          {/* Appearance */}
          <div className="glass rounded-2xl p-6 space-y-6">
            <h2 className="text-lg font-semibold text-[var(--color-text)] flex items-center justify-between">
              Appearance
              <ThemeToggle />
            </h2>
            <p className="text-sm text-[var(--color-text-muted)]">
              Switch between Light and Dark mode.
            </p>
          </div>

          {/* Account */}
          <div className="glass rounded-2xl p-6 space-y-6">
            <h2 className="text-lg font-semibold text-[var(--color-text)] flex items-center gap-2">
              Account details
            </h2>
            <p className="text-sm text-[var(--color-text-muted)]">
              Account management features (email, password) will be integrated
              with Firebase Auth soon.
            </p>
          </div>

          <div className="flex items-center gap-4">
            <button
              onClick={handleSave}
              disabled={saving}
              className="btn-gradient rounded-xl px-6 py-2.5 text-sm font-semibold text-white disabled:opacity-50 flex items-center gap-2"
            >
              {saving ? "Saving..." : "Save Preferences"}
            </button>
            {message && (
              <span className="text-sm text-[var(--color-success)] animate-fade-in-up">
                {message}
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
