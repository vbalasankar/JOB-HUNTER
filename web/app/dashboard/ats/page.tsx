"use client";

import { useState, useRef } from "react";
import { analyzeAts, type AtsScoreResponse } from "@/lib/api";

export default function AtsPage() {
  const [resumeText, setResumeText] = useState("");
  const [jobDescription, setJobDescription] = useState("");
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AtsScoreResponse | null>(null);
  const [error, setError] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  const handleAnalyze = async () => {
    if (!jobDescription.trim() || (!resumeText.trim() && !resumeFile)) {
      setError(
        "Please provide a job description and your resume (paste or upload).",
      );
      return;
    }
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const data = await analyzeAts(
        resumeText,
        jobDescription,
        resumeFile || undefined,
      );
      setResult(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Analysis failed.");
    }
    setLoading(false);
  };

  const scoreColor = (score: number) => {
    if (score >= 0.8) return "text-[var(--color-success)]";
    if (score >= 0.6) return "text-[var(--color-warning)]";
    return "text-[var(--color-danger)]";
  };

  const barColor = (score: number) => {
    if (score >= 0.8) return "bg-[var(--color-success)]";
    if (score >= 0.6) return "bg-[var(--color-warning)]";
    return "bg-[var(--color-danger)]";
  };

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h1
          className="text-2xl md:text-3xl font-semibold text-[var(--color-text)] tracking-tight"
          style={{ fontFamily: "var(--font-heading)" }}
        >
          ATS Score Analyzer
        </h1>
        <p className="mt-1 text-sm text-[var(--color-text-secondary)]">
          Check how well your resume matches a job description before applying.
        </p>
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        {/* Resume input */}
        <div className="glass rounded-2xl p-5 space-y-3">
          <h3 className="text-sm font-semibold text-[var(--color-text)]">
            Your Resume
          </h3>
          <div
            className="border-2 border-dashed border-[var(--color-border)] rounded-xl p-4 text-center cursor-pointer hover:border-[var(--color-accent)]/30 transition-colors"
            onClick={() => fileRef.current?.click()}
          >
            <p className="text-xs text-[var(--color-text-secondary)] mt-2">
              {resumeFile ? resumeFile.name : "Click to upload PDF or TXT"}
            </p>
            <input
              ref={fileRef}
              type="file"
              accept=".pdf,.txt"
              className="hidden"
              onChange={(e) => setResumeFile(e.target.files?.[0] || null)}
            />
          </div>
          <div className="text-xs text-center text-[var(--color-text-muted)]">
            — or paste below —
          </div>
          <textarea
            id="ats-resume-input"
            placeholder="Paste your resume text here..."
            value={resumeText}
            onChange={(e) => setResumeText(e.target.value)}
            className="w-full h-40 px-4 py-3 rounded-xl bg-[var(--color-surface-3)] border border-[var(--color-border)] text-sm text-[var(--color-text)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-accent)]/50 resize-none transition-colors"
          />
        </div>

        {/* Job Description input */}
        <div className="glass rounded-2xl p-5 space-y-3">
          <h3 className="text-sm font-semibold text-[var(--color-text)]">
            Job Description
          </h3>
          <textarea
            id="ats-jd-input"
            placeholder="Paste the job description here..."
            value={jobDescription}
            onChange={(e) => setJobDescription(e.target.value)}
            className="w-full h-64 px-4 py-3 rounded-xl bg-[var(--color-surface-3)] border border-[var(--color-border)] text-sm text-[var(--color-text)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-accent)]/50 resize-none transition-colors"
          />
        </div>
      </div>

      <button
        id="ats-analyze-btn"
        onClick={handleAnalyze}
        disabled={loading}
        className="btn-gradient rounded-xl px-8 py-3 text-sm font-semibold text-white disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 mx-auto"
      >
        {loading ? <>Analyzing...</> : <>Analyze Match</>}
      </button>

      {error && (
        <div className="flex items-center gap-2 p-4 rounded-xl bg-[var(--color-danger)]/10 border border-[var(--color-danger)]/20">
          <p className="text-sm text-[var(--color-danger)]">{error}</p>
        </div>
      )}

      {/* Results */}
      {result && (
        <div className="space-y-4 animate-fade-in-up">
          {/* Overall score */}
          <div className="glass-bright rounded-2xl p-6 text-center">
            <p
              className={`text-5xl font-bold ${scoreColor(result.overall_score)}`}
              style={{ fontFamily: "var(--font-heading)" }}
            >
              {Math.round(result.overall_score * 100)}%
            </p>
            <p className="text-sm text-[var(--color-text-secondary)] mt-1">
              ATS Compatibility Score
            </p>
            <div className="mt-4 h-2 rounded-full bg-white/10 overflow-hidden max-w-xs mx-auto">
              <div
                className={`h-full rounded-full ${barColor(result.overall_score)} score-bar-fill`}
                style={{ width: `${Math.round(result.overall_score * 100)}%` }}
              />
            </div>
          </div>

          {/* Breakdown */}
          <div className="glass rounded-2xl p-5">
            <h3 className="text-sm font-semibold text-[var(--color-text)] mb-4">
              Score Breakdown
            </h3>
            <div className="space-y-3">
              {[
                { label: "Hard Skills", score: result.hard_skills_score },
                { label: "Soft Skills", score: result.soft_skills_score },
                { label: "Role Match", score: result.role_match_score },
                { label: "Experience", score: result.experience_score },
                { label: "Education", score: result.education_score },
              ].map((item) => (
                <div key={item.label} className="flex items-center gap-3">
                  <span className="text-xs text-[var(--color-text-secondary)] w-24 shrink-0">
                    {item.label}
                  </span>
                  <div className="flex-1 h-1.5 rounded-full bg-white/10 overflow-hidden">
                    <div
                      className={`h-full rounded-full ${barColor(item.score)} score-bar-fill`}
                      style={{ width: `${Math.round(item.score * 100)}%` }}
                    />
                  </div>
                  <span
                    className={`text-xs font-bold w-10 text-right ${scoreColor(item.score)}`}
                  >
                    {Math.round(item.score * 100)}%
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Keywords */}
          <div className="grid md:grid-cols-2 gap-4">
            {result.matched_keywords.length > 0 && (
              <div className="glass rounded-2xl p-5">
                <h3 className="text-sm font-semibold text-[var(--color-text)] mb-3 flex items-center gap-2">
                  Matched Keywords
                </h3>
                <div className="flex flex-wrap gap-1.5">
                  {result.matched_keywords.map((kw) => (
                    <span
                      key={kw}
                      className="px-2.5 py-1 rounded-lg bg-[var(--color-success)]/10 text-xs font-medium text-[var(--color-success)]"
                    >
                      {kw}
                    </span>
                  ))}
                </div>
              </div>
            )}
            {result.missing_keywords.length > 0 && (
              <div className="glass rounded-2xl p-5">
                <h3 className="text-sm font-semibold text-[var(--color-text)] mb-3 flex items-center gap-2">
                  Missing Keywords
                </h3>
                <div className="flex flex-wrap gap-1.5">
                  {result.missing_keywords.map((kw) => (
                    <span
                      key={kw}
                      className="px-2.5 py-1 rounded-lg bg-[var(--color-danger)]/10 text-xs font-medium text-[var(--color-danger)]"
                    >
                      {kw}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Suggestions */}
          {result.suggestions.length > 0 && (
            <div className="glass rounded-2xl p-5">
              <h3 className="text-sm font-semibold text-[var(--color-text)] mb-3 flex items-center gap-2">
                Suggestions
              </h3>
              <ul className="space-y-2">
                {result.suggestions.map((s, i) => (
                  <li
                    key={i}
                    className="text-xs text-[var(--color-text-secondary)] flex items-start gap-2"
                  >
                    <span className="text-[var(--color-warning)] mt-0.5">
                      •
                    </span>
                    {s}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
