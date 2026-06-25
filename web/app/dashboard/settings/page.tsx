"use client";

import { useEffect, useState } from "react";
import { fetchProfile, saveProfile, type ProfileData } from "@/lib/api";
import { ThemeToggle } from "@/components/ThemeToggle";

export default function SettingsPage() {
  const [profile, setProfile] = useState<ProfileData>({
    roles: [],
    skills: [],
    locations: [],
    firstName: "",
    lastName: "",
    email: "",
    experienceLevel: "",
    minSalary: "",
    resumeFileName: ""
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    setLoading(true);
    fetchProfile().then((data) => {
      if (data) setProfile({ ...profile, ...data });
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

  const updateField = (field: keyof ProfileData, value: string) => {
    setProfile({ ...profile, [field]: value });
  };

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h1
          className="text-2xl md:text-3xl font-semibold text-[var(--color-text)] tracking-tight"
          style={{ fontFamily: "var(--font-heading)" }}
        >
          Profile & Settings
        </h1>
        <p className="mt-1 text-sm text-[var(--color-text-secondary)]">
          Manage your job matching preferences, resume, and account details.
        </p>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20 text-[var(--color-accent)]">
          Loading...
        </div>
      ) : (
        <div className="space-y-6 animate-fade-in-up">
          
          {/* Account Details */}
          <div className="glass rounded-2xl p-6 space-y-6">
            <h2 className="text-lg font-semibold text-[var(--color-text)] flex items-center gap-2">
              Personal Details
            </h2>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-sm font-medium text-[var(--color-text-secondary)]">
                  First Name
                </label>
                <input
                  type="text"
                  placeholder="First Name"
                  value={profile.firstName || ""}
                  onChange={(e) => updateField("firstName", e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl bg-[var(--color-surface-3)] border border-[var(--color-border)] text-sm text-[var(--color-text)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-accent)]/50 transition-colors"
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium text-[var(--color-text-secondary)]">
                  Last Name
                </label>
                <input
                  type="text"
                  placeholder="Last Name"
                  value={profile.lastName || ""}
                  onChange={(e) => updateField("lastName", e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl bg-[var(--color-surface-3)] border border-[var(--color-border)] text-sm text-[var(--color-text)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-accent)]/50 transition-colors"
                />
              </div>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium text-[var(--color-text-secondary)]">
                Email Address
              </label>
              <input
                type="email"
                placeholder="Email Address"
                value={profile.email || ""}
                onChange={(e) => updateField("email", e.target.value)}
                className="w-full px-4 py-2.5 rounded-xl bg-[var(--color-surface-3)] border border-[var(--color-border)] text-sm text-[var(--color-text)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-accent)]/50 transition-colors"
              />
            </div>
          </div>

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
                  value={(profile.roles || []).join(", ")}
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
                  value={(profile.skills || []).join(", ")}
                  onChange={(e) => updateArray("skills", e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl bg-[var(--color-surface-3)] border border-[var(--color-border)] text-sm text-[var(--color-text)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-accent)]/50 transition-colors"
                />
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-[var(--color-text-secondary)] flex items-center gap-2">
                  Locations / Remote
                </label>
                <input
                  type="text"
                  placeholder="e.g. Remote, New York, San Francisco (comma separated)"
                  value={(profile.locations || []).join(", ")}
                  onChange={(e) => updateArray("locations", e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl bg-[var(--color-surface-3)] border border-[var(--color-border)] text-sm text-[var(--color-text)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-accent)]/50 transition-colors"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium text-[var(--color-text-secondary)]">
                    Experience Level
                  </label>
                  <select
                    value={profile.experienceLevel || ""}
                    onChange={(e) => updateField("experienceLevel", e.target.value)}
                    className="w-full px-4 py-2.5 rounded-xl bg-[var(--color-surface-3)] border border-[var(--color-border)] text-sm text-[var(--color-text)] focus:outline-none focus:border-[var(--color-accent)]/50 transition-colors"
                  >
                    <option value="">Any</option>
                    <option value="junior">Entry Level / Junior</option>
                    <option value="mid">Mid Level</option>
                    <option value="senior">Senior</option>
                    <option value="lead">Lead / Manager</option>
                    <option value="executive">Director / VP / Exec</option>
                  </select>
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium text-[var(--color-text-secondary)]">
                    Minimum Salary (USD)
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. 120000"
                    value={profile.minSalary || ""}
                    onChange={(e) => updateField("minSalary", e.target.value)}
                    className="w-full px-4 py-2.5 rounded-xl bg-[var(--color-surface-3)] border border-[var(--color-border)] text-sm text-[var(--color-text)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-accent)]/50 transition-colors"
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Resume Upload */}
          <div className="glass rounded-2xl p-6 space-y-6">
            <h2 className="text-lg font-semibold text-[var(--color-text)] flex items-center gap-2">
              Resume
            </h2>
            <div className="border-2 border-dashed border-[var(--color-border)] rounded-xl p-8 flex flex-col items-center justify-center text-center space-y-3 hover:border-[var(--color-accent)]/50 hover:bg-[var(--color-surface-3)] transition-colors cursor-pointer" onClick={() => alert("Upload feature coming soon! Place resume.txt in root to enable parsing.")}>
              <svg className="w-8 h-8 text-[var(--color-text-muted)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
              <div className="text-sm text-[var(--color-text)] font-medium">Click to upload your resume (PDF or TXT)</div>
              <div className="text-xs text-[var(--color-text-muted)]">This will be used to auto-score your match against job listings.</div>
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

          <div className="flex items-center gap-4 pt-4">
            <button
              onClick={handleSave}
              disabled={saving}
              className="btn-gradient rounded-xl px-6 py-2.5 text-sm font-semibold text-white disabled:opacity-50 flex items-center gap-2"
            >
              {saving ? "Saving..." : "Save Profile"}
            </button>
            {message && (
              <span className="text-sm text-[var(--color-success)] animate-fade-in-up font-medium">
                {message}
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
