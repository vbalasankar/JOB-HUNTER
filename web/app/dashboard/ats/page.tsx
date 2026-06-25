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
  const [showDetails, setShowDetails] = useState(false);
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
    setShowDetails(false);
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

  const bgScoreColor = (score: number) => {
    if (score >= 0.8) return "bg-[var(--color-success)]";
    if (score >= 0.6) return "bg-[var(--color-warning)]";
    return "bg-[var(--color-danger)]";
  };

  const borderScoreColor = (score: number) => {
    if (score >= 0.8) return "border-[var(--color-success)]";
    if (score >= 0.6) return "border-[var(--color-warning)]";
    return "border-[var(--color-danger)]";
  };

  return (
    <div className="space-y-8 max-w-5xl mx-auto pb-12">
      <div className="text-center animate-fade-in-up">
        <h1
          className="text-3xl md:text-4xl font-bold text-[var(--color-text)] tracking-tight mb-3"
          style={{ fontFamily: "var(--font-heading)" }}
        >
          Enterprise ATS Engine
        </h1>
        <p className="text-sm md:text-base text-[var(--color-text-secondary)] max-w-2xl mx-auto">
          Recruiter-grade analysis of your resume against the job description.
          Checks semantics, consistency, impact, and parseability.
        </p>
      </div>

      <div className="grid md:grid-cols-2 gap-6 animate-fade-in-up" style={{ animationDelay: "100ms" }}>
        {/* Resume input */}
        <div className="glass rounded-2xl p-6 space-y-4 hover:border-[var(--color-accent)]/20 transition-colors">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-semibold text-[var(--color-text)]">
              Your Resume
            </h3>
            <span className="text-xs px-2 py-1 rounded bg-[var(--color-surface-3)] text-[var(--color-text-muted)]">
              PDF, TXT, or Paste
            </span>
          </div>
          <div
            className="border-2 border-dashed border-[var(--color-border)] rounded-xl p-5 text-center cursor-pointer hover:bg-[var(--color-surface-3)] transition-colors group"
            onClick={() => fileRef.current?.click()}
          >
            <div className="w-10 h-10 mx-auto rounded-full bg-[var(--color-surface)] flex items-center justify-center mb-3 group-hover:scale-110 transition-transform">
              <svg className="w-5 h-5 text-[var(--color-accent)]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
              </svg>
            </div>
            <p className="text-sm font-medium text-[var(--color-text)]">
              {resumeFile ? resumeFile.name : "Click to upload file"}
            </p>
            <input
              ref={fileRef}
              type="file"
              accept=".pdf,.txt"
              className="hidden"
              onChange={(e) => setResumeFile(e.target.files?.[0] || null)}
            />
          </div>
          <div className="flex items-center gap-3">
            <div className="h-px flex-1 bg-[var(--color-border)]"></div>
            <span className="text-xs text-[var(--color-text-muted)] font-medium uppercase tracking-wider">or paste</span>
            <div className="h-px flex-1 bg-[var(--color-border)]"></div>
          </div>
          <textarea
            placeholder="Paste your resume text here..."
            value={resumeText}
            onChange={(e) => setResumeText(e.target.value)}
            className="w-full h-32 px-4 py-3 rounded-xl bg-[var(--color-surface-3)] border border-[var(--color-border)] text-sm text-[var(--color-text)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-accent)]/50 resize-none transition-all"
          />
        </div>

        {/* Job Description input */}
        <div className="glass rounded-2xl p-6 space-y-4 hover:border-[var(--color-accent)]/20 transition-colors">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-semibold text-[var(--color-text)]">
              Job Description
            </h3>
            <span className="text-xs px-2 py-1 rounded bg-[var(--color-surface-3)] text-[var(--color-text-muted)]">
              Paste Text
            </span>
          </div>
          <textarea
            placeholder="Paste the full job description here..."
            value={jobDescription}
            onChange={(e) => setJobDescription(e.target.value)}
            className="w-full h-[280px] px-4 py-3 rounded-xl bg-[var(--color-surface-3)] border border-[var(--color-border)] text-sm text-[var(--color-text)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-accent)]/50 resize-none transition-all"
          />
        </div>
      </div>

      <div className="flex justify-center animate-fade-in-up" style={{ animationDelay: "200ms" }}>
        <button
          onClick={handleAnalyze}
          disabled={loading}
          className="btn-gradient rounded-full px-10 py-4 text-sm font-bold text-white shadow-lg shadow-[var(--color-accent)]/20 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 hover:scale-105 transition-transform"
        >
          {loading ? (
            <>
              <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Analyzing Profile...
            </>
          ) : (
            <>
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              Generate Intelligence Report
            </>
          )}
        </button>
      </div>

      {error && (
        <div className="flex items-center gap-3 p-4 rounded-xl bg-[var(--color-danger)]/10 border border-[var(--color-danger)]/20 animate-fade-in-up">
          <svg className="w-5 h-5 text-[var(--color-danger)] shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p className="text-sm font-medium text-[var(--color-danger)]">{error}</p>
        </div>
      )}

      {/* Results Section */}
      {result && (
        <div className="space-y-8 animate-fade-in-up mt-8">
          
          {/* Main Score Hero */}
          <div className="glass-bright rounded-3xl p-8 md:p-12 text-center relative overflow-hidden">
            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-[var(--color-accent)] to-transparent opacity-50"></div>
            
            <div className="flex flex-col items-center justify-center space-y-4 relative z-10">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[var(--color-surface-3)] border border-[var(--color-border)] mb-2">
                <span className="w-2 h-2 rounded-full bg-[var(--color-accent)]"></span>
                <span className="text-xs font-medium text-[var(--color-text-secondary)]">
                  Analysis Confidence: {Math.round(result.confidence_score * 100)}%
                </span>
              </div>
              
              <div className="relative">
                <svg className="w-40 h-40 transform -rotate-90">
                  <circle cx="80" cy="80" r="70" fill="transparent" stroke="var(--color-border)" strokeWidth="8" />
                  <circle 
                    cx="80" cy="80" r="70" fill="transparent" 
                    stroke="currentColor" 
                    strokeWidth="8" 
                    strokeDasharray={440} 
                    strokeDashoffset={440 - (440 * result.overall_fit_score) / 100} 
                    strokeLinecap="round"
                    className={`${scoreColor(result.overall_fit_score / 100).replace('text-', 'text-')} transition-all duration-1000 ease-out`}
                  />
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <span className={`text-5xl font-bold ${scoreColor(result.overall_fit_score / 100)}`} style={{ fontFamily: "var(--font-heading)" }}>
                    {Math.round(result.overall_fit_score)}
                  </span>
                </div>
              </div>
              
              <h2 className="text-xl font-bold text-[var(--color-text)]">ATS Fit Score</h2>
              <p className="text-sm text-[var(--color-text-secondary)] max-w-md">
                Based on semantic matching, skill gaps, quantified impact, and resume structural parseability.
              </p>
            </div>
          </div>

          {/* Strengths and Gaps */}
          <div className="grid md:grid-cols-2 gap-6">
            <div className="glass rounded-2xl p-6 border-t-4 border-t-[var(--color-success)]">
              <h3 className="text-base font-bold text-[var(--color-text)] mb-4 flex items-center gap-2">
                <svg className="w-5 h-5 text-[var(--color-success)]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Top Strengths
              </h3>
              <ul className="space-y-3">
                {result.top_strengths.length > 0 ? (
                  result.top_strengths.map((s, i) => (
                    <li key={i} className="flex items-start gap-3 text-sm text-[var(--color-text-secondary)]">
                      <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-success)] mt-1.5 shrink-0"></span>
                      <span>{s}</span>
                    </li>
                  ))
                ) : (
                  <p className="text-sm text-[var(--color-text-muted)] italic">No significant strengths detected.</p>
                )}
              </ul>
            </div>

            <div className="glass rounded-2xl p-6 border-t-4 border-t-[var(--color-danger)]">
              <h3 className="text-base font-bold text-[var(--color-text)] mb-4 flex items-center gap-2">
                <svg className="w-5 h-5 text-[var(--color-danger)]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
                Critical Gaps
              </h3>
              <ul className="space-y-3">
                {result.top_gaps.length > 0 ? (
                  result.top_gaps.map((s, i) => (
                    <li key={i} className="flex items-start gap-3 text-sm text-[var(--color-text-secondary)]">
                      <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-danger)] mt-1.5 shrink-0"></span>
                      <span>{s}</span>
                    </li>
                  ))
                ) : (
                  <p className="text-sm text-[var(--color-text-muted)] italic">No significant gaps detected!</p>
                )}
              </ul>
            </div>
          </div>

          {/* Actionable Suggestions */}
          {result.rewrite_suggestions && result.rewrite_suggestions.length > 0 && (
            <div className="space-y-4">
              <h3 className="text-lg font-bold text-[var(--color-text)] px-2">Actionable Suggestions</h3>
              <div className="grid gap-4">
                {result.rewrite_suggestions.map((s, i) => (
                  <div key={i} className="glass rounded-2xl p-5 border-l-4 border-l-[var(--color-warning)] hover:bg-[var(--color-surface-3)] transition-colors">
                    <div className="flex flex-col md:flex-row gap-4">
                      <div className="flex-1 space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-bold uppercase tracking-wide text-[var(--color-warning)]">
                            {s.priority}
                          </span>
                          <span className="text-xs text-[var(--color-text-muted)] bg-[var(--color-surface)] px-2 py-1 rounded">
                            {s.category.replace(/_/g, ' ')}
                          </span>
                        </div>
                        <p className="text-sm font-medium text-[var(--color-text)]">
                          {s.suggestion}
                        </p>
                        <p className="text-xs text-[var(--color-text-secondary)] pt-2 border-t border-[var(--color-border)]">
                          <span className="font-semibold">Why:</span> {s.reasoning}
                        </p>
                      </div>
                      {s.current_text && (
                        <div className="md:w-1/3 bg-[var(--color-surface)] rounded-xl p-3 text-xs border border-[var(--color-border)] self-start mt-2 md:mt-0">
                          <div className="text-[var(--color-text-muted)] font-medium mb-1">Found in Resume:</div>
                          <div className="text-[var(--color-text-secondary)] font-mono opacity-80 break-words line-clamp-3">
                            "{s.current_text}"
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Progressive Disclosure: Details */}
          <div className="flex justify-center pt-4">
            <button
              onClick={() => setShowDetails(!showDetails)}
              className="text-sm font-medium text-[var(--color-accent)] hover:text-white transition-colors flex items-center gap-1"
            >
              {showDetails ? "Hide Detailed Metrics" : "View Detailed Metrics"}
              <svg className={`w-4 h-4 transform transition-transform ${showDetails ? "rotate-180" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
          </div>

          {showDetails && (
            <div className="glass rounded-3xl p-6 md:p-8 animate-fade-in-up">
              <h3 className="text-lg font-bold text-[var(--color-text)] mb-6">Deep Dive Metrics</h3>
              
              <div className="grid md:grid-cols-2 gap-x-12 gap-y-6">
                {[
                  { label: "Hard Skills Alignment", score: result.hard_skills_score },
                  { label: "Soft Skills Alignment", score: result.soft_skills_score },
                  { label: "Semantic Chunk Match", score: result.semantic_fit_score || 0.0 },
                  { label: "Quantified Impact", score: result.impact_score },
                  { label: "Leadership Signals", score: result.leadership_score },
                  { label: "Domain Overlap", score: result.domain_match_score },
                  { label: "Resume Consistency", score: result.consistency_score },
                  { label: "Parseability (Structure)", score: result.parseability_score },
                ].map((item, idx) => (
                  <div key={idx} className="space-y-2">
                    <div className="flex justify-between items-end">
                      <span className="text-sm font-medium text-[var(--color-text)]">{item.label}</span>
                      <span className={`text-xs font-bold ${scoreColor(item.score)}`}>
                        {Math.round(item.score * 100)}%
                      </span>
                    </div>
                    <div className="h-2 rounded-full bg-white/5 overflow-hidden">
                      <div
                        className={`h-full rounded-full ${bgScoreColor(item.score)}`}
                        style={{ width: `${Math.max(2, Math.round(item.score * 100))}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

        </div>
      )}
    </div>
  );
}
