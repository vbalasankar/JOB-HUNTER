"use client";

import Link from "next/link";

const FEATURES = [
  {
    title: "AI-Powered Matching",
    description:
      "Semantic embeddings compare your resume against job descriptions to surface truly relevant roles — not just keyword matches.",
  },
  {
    title: "ATS Score Analyzer",
    description:
      "Upload your resume and any job description. Instantly see your compatibility score, missing keywords, and actionable suggestions.",
  },
  {
    title: "20+ Job Sources",
    description:
      "Greenhouse, Lever, Ashby, RemoteOK, Y Combinator, Hacker News, and more — all crawled and deduplicated automatically.",
  },
  {
    title: "Tech News Feed",
    description:
      "Stay ahead with curated tech news from Hacker News, TechCrunch, and startup RSS feeds — filtered to your skills.",
  },
  {
    title: "Smart Ranking",
    description:
      "Jobs are scored using a weighted blend of semantic similarity and keyword overlap, giving you a single match percentage.",
  },
  {
    title: "Privacy First",
    description:
      "Everything runs locally. Your resume data never leaves your machine. No tracking, no data selling, ever.",
  },
];

const STEPS = [
  {
    step: "01",
    title: "Set Your Preferences",
    description:
      "Tell us your target roles, skills, and preferred locations. Upload your resume for AI-powered matching.",
  },
  {
    step: "02",
    title: "We Crawl Everything",
    description:
      "Our pipeline fetches from 20+ sources, deduplicates listings, and filters by your criteria automatically.",
  },
  {
    step: "03",
    title: "Get Matched Results",
    description:
      "See your personalized job feed ranked by match score. Check ATS compatibility before you apply.",
  },
];

const STATS = [
  { value: "6,000+", label: "Jobs Crawled" },
  { value: "20+", label: "Data Sources" },
  { value: "4x", label: "Faster Than Manual" },
  { value: "98%", label: "Dedup Accuracy" },
];

export default function LandingPage() {
  return (
    <div className="flex flex-col">
      {/* Navigation */}
      <header className="fixed top-0 z-50 w-full">
        <nav className="mx-auto flex max-w-6xl items-center justify-between px-5 py-4 md:px-8">
          <Link href="/" className="flex items-center gap-2">
            <img
              src="/logo.png"
              alt="JH Logo"
              className="w-8 h-8 object-contain dark:invert rounded-md"
            />
            <span
              className="text-xl font-semibold text-[var(--color-text)] tracking-tight"
              style={{ fontFamily: "var(--font-heading)" }}
            >
              JobHunter
            </span>
          </Link>
          <div className="hidden md:flex items-center gap-6">
            <a
              href="#features"
              className="text-sm font-medium text-[var(--color-text-secondary)] hover:text-[var(--color-text)] transition-colors"
            >
              Features
            </a>
            <a
              href="#how-it-works"
              className="text-sm font-medium text-[var(--color-text-secondary)] hover:text-[var(--color-text)] transition-colors"
            >
              How It Works
            </a>
            <Link
              href="/auth/login"
              className="text-sm font-medium text-[var(--color-text)] hover:opacity-80 transition-opacity"
            >
              Log in
            </Link>
            <Link
              href="/auth/signup"
              className="btn-gradient rounded-lg px-4 py-2 text-sm font-medium text-white"
            >
              Sign up
            </Link>
          </div>
          <Link
            href="/auth/signup"
            className="md:hidden btn-gradient rounded-lg px-4 py-2 text-sm font-medium text-white"
          >
            Sign up
          </Link>
        </nav>
      </header>

      {/* Hero */}
      <section className="hero-gradient min-h-dvh flex items-center justify-center px-4 pt-20">
        <div className="relative z-10 flex flex-col items-center gap-8 text-center max-w-3xl">
          <h1
            className="animate-fade-in-up animate-delay-100 text-5xl md:text-7xl lg:text-8xl font-medium tracking-tight text-[var(--color-text)] leading-[0.95]"
            style={{ fontFamily: "var(--font-heading)" }}
          >
            Your AI-Powered
            <br />
            <span className="bg-gradient-to-r from-[var(--color-accent-light)] to-[var(--color-accent)] bg-clip-text text-transparent">
              Job Hunt
            </span>{" "}
            Starts Here
          </h1>

          <div className="animate-fade-in-up animate-delay-200 w-48 h-px bg-gradient-to-r from-transparent via-[var(--color-text)]/20 to-transparent" />

          <p className="animate-fade-in-up animate-delay-200 text-base md:text-lg text-[var(--color-text-secondary)] max-w-xl leading-relaxed">
            JobHunter crawls thousands of jobs from 20+ sources, matches them
            against your resume with AI, and delivers a ranked feed of your best
            opportunities.
          </p>

          <div className="animate-fade-in-up animate-delay-300 flex flex-col sm:flex-row items-center gap-3">
            <Link
              href="/dashboard"
              className="btn-gradient rounded-xl px-8 py-3.5 text-base font-semibold text-white flex items-center gap-2 group"
            >
              Get Started Free
            </Link>
            <a
              href="#features"
              className="rounded-xl px-8 py-3.5 text-base font-medium text-[var(--color-text-secondary)] border border-[var(--color-border)] hover:border-[var(--color-border-bright)] hover:text-[var(--color-text)] transition-all"
            >
              See How It Works
            </a>
          </div>

          {/* Hero visual: floating job cards */}
          <div className="animate-fade-in-up animate-delay-500 mt-8 w-full max-w-2xl">
            <div className="glass-bright rounded-2xl p-6 space-y-3">
              {[
                {
                  title: "Senior Backend Engineer",
                  company: "Stripe",
                  score: 94,
                  loc: "Remote",
                },
                {
                  title: "Platform Engineer",
                  company: "Datadog",
                  score: 89,
                  loc: "New York",
                },
                {
                  title: "Data Engineer",
                  company: "Databricks",
                  score: 85,
                  loc: "Remote",
                },
              ].map((job, i) => (
                <div
                  key={i}
                  className="flex items-center justify-between rounded-xl bg-white/[0.03] border border-white/[0.06] px-4 py-3 hover:bg-white/[0.06] transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <div>
                      <p className="text-sm font-medium text-[var(--color-text)]">
                        {job.title}
                      </p>
                      <p className="text-xs text-[var(--color-text-muted)]">
                        {job.company} · {job.loc}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-16 h-1.5 rounded-full bg-white/10 overflow-hidden">
                      <div
                        className="h-full rounded-full bg-gradient-to-r from-[var(--color-accent)] to-[var(--color-success)]"
                        style={{ width: `${job.score}%` }}
                      />
                    </div>
                    <span className="text-xs font-semibold text-[var(--color-success)]">
                      {job.score}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Stats */}
      <section className="py-16 px-4 border-y border-[var(--color-border)]">
        <div className="mx-auto max-w-5xl grid grid-cols-2 md:grid-cols-4 gap-8">
          {STATS.map((stat, i) => (
            <div key={i} className="text-center">
              <p
                className="text-3xl md:text-4xl font-semibold text-[var(--color-text)] tracking-tight"
                style={{ fontFamily: "var(--font-heading)" }}
              >
                {stat.value}
              </p>
              <p className="text-sm text-[var(--color-text-muted)] mt-1">
                {stat.label}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section id="features" className="py-24 px-4">
        <div className="mx-auto max-w-6xl">
          <div className="text-center mb-16">
            <h2
              className="text-4xl md:text-5xl font-medium text-[var(--color-text)] tracking-tight"
              style={{ fontFamily: "var(--font-heading)" }}
            >
              Everything You Need
            </h2>
            <p className="mt-4 text-[var(--color-text-secondary)] max-w-lg mx-auto">
              A complete job hunting toolkit — from intelligent sourcing to
              resume optimization.
            </p>
          </div>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {FEATURES.map((feature, i) => (
              <div
                key={i}
                className="glass rounded-2xl p-6 hover:border-[var(--color-border-bright)] transition-all group"
              >
                <h3 className="text-base font-semibold text-[var(--color-text)] mb-2 mt-2">
                  {feature.title}
                </h3>
                <p className="text-sm text-[var(--color-text-secondary)] leading-relaxed">
                  {feature.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section
        id="how-it-works"
        className="py-24 px-4 border-t border-[var(--color-border)]"
      >
        <div className="mx-auto max-w-4xl">
          <div className="text-center mb-16">
            <h2
              className="text-4xl md:text-5xl font-medium text-[var(--color-text)] tracking-tight"
              style={{ fontFamily: "var(--font-heading)" }}
            >
              How It Works
            </h2>
            <p className="mt-4 text-[var(--color-text-secondary)]">
              Three steps to your personalized job feed.
            </p>
          </div>
          <div className="space-y-6">
            {STEPS.map((step, i) => (
              <div
                key={i}
                className="glass rounded-2xl p-6 md:p-8 flex gap-6 items-start hover:border-[var(--color-border-bright)] transition-all"
              >
                <div
                  className="text-3xl font-semibold text-[var(--color-accent)]/40 shrink-0"
                  style={{ fontFamily: "var(--font-heading)" }}
                >
                  {step.step}
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-[var(--color-text)] mb-2">
                    {step.title}
                  </h3>
                  <p className="text-sm text-[var(--color-text-secondary)] leading-relaxed">
                    {step.description}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-24 px-4 gradient-bg">
        <div className="mx-auto max-w-2xl text-center">
          <h2
            className="text-4xl md:text-5xl font-medium text-[var(--color-text)] tracking-tight"
            style={{ fontFamily: "var(--font-heading)" }}
          >
            Ready to Hunt Smarter?
          </h2>
          <p className="mt-4 text-[var(--color-text-secondary)] mb-8">
            Stop scrolling through endless job boards. Let AI find the roles
            that actually match your skills.
          </p>
          <Link
            href="/dashboard"
            className="btn-gradient rounded-xl px-10 py-4 text-base font-semibold text-white inline-flex items-center gap-2 group"
          >
            Launch Dashboard
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 px-4 border-t border-[var(--color-border)]">
        <div className="mx-auto max-w-6xl flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <img
              src="/logo.png"
              alt="JH Logo"
              className="w-6 h-6 object-contain dark:invert rounded-md"
            />
            <span
              className="text-sm font-semibold text-[var(--color-text)]"
              style={{ fontFamily: "var(--font-heading)" }}
            >
              JobHunter
            </span>
          </div>
        </div>
      </footer>
    </div>
  );
}
