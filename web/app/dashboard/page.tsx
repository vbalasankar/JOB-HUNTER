"use client";

import { useEffect, useState, useCallback } from "react";
import { Loader2 } from "lucide-react";
import {
  fetchJobs,
  fetchJobStats,
  type JobResponse,
  type StatsResponse,
  timeAgo,
  formatSalary,
} from "@/lib/api";

export default function JobsPage() {
  const [jobs, setJobs] = useState<JobResponse[]>([]);
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [perPage] = useState(25);
  const [search, setSearch] = useState("");
  const [source, setSource] = useState("");
  const [remoteType, setRemoteType] = useState("");
  const [loading, setLoading] = useState(true);

  const loadJobs = useCallback(async () => {
    setLoading(true);
    const data = await fetchJobs({
      page,
      per_page: perPage,
      search: search || undefined,
      source: source || undefined,
      remote_type: remoteType || undefined,
    });
    if (data) {
      setJobs(data.jobs);
      setTotal(data.total);
    }
    setLoading(false);
  }, [page, perPage, search, source, remoteType]);

  useEffect(() => {
    loadJobs();
  }, [loadJobs]);

  useEffect(() => {
    fetchJobStats().then((s) => s && setStats(s));
  }, []);

  const totalPages = Math.ceil(total / perPage);

  return (
    <div className="space-y-6 max-w-5xl">
      {/* Header */}
      <div>
        <h1
          className="text-2xl md:text-3xl font-semibold text-[var(--color-text)] tracking-tight"
          style={{ fontFamily: "var(--font-heading)" }}
        >
          Job Feed
        </h1>
        {stats && (
          <p className="mt-1 text-sm text-[var(--color-text-secondary)]">
            {stats.total_jobs.toLocaleString()} jobs from{" "}
            {Object.keys(stats.by_source).length} sources
            {stats.latest_fetch &&
              ` · Last crawl ${timeAgo(stats.latest_fetch)}`}
          </p>
        )}
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <div className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--color-text-muted)] flex items-center justify-center text-xs">
            Q
          </div>
          <input
            id="jobs-search-input"
            type="text"
            placeholder="Search jobs, companies..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-[var(--color-surface-2)] border border-[var(--color-border)] text-sm text-[var(--color-text)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-accent)]/50 transition-colors"
          />
        </div>
        <select
          id="jobs-source-filter"
          value={source}
          onChange={(e) => {
            setSource(e.target.value);
            setPage(1);
          }}
          className="px-4 py-2.5 rounded-xl bg-[var(--color-surface-2)] border border-[var(--color-border)] text-sm text-[var(--color-text)] focus:outline-none focus:border-[var(--color-accent)]/50 appearance-none cursor-pointer"
        >
          <option value="">All sources</option>
          {stats &&
            Object.entries(stats.by_source)
              .sort(([a], [b]) => a.localeCompare(b))
              .map(([src, count]) => (
                <option key={src} value={src}>
                  {src} ({count})
                </option>
              ))}
        </select>
        <select
          id="jobs-remote-filter"
          value={remoteType}
          onChange={(e) => {
            setRemoteType(e.target.value);
            setPage(1);
          }}
          className="px-4 py-2.5 rounded-xl bg-[var(--color-surface-2)] border border-[var(--color-border)] text-sm text-[var(--color-text)] focus:outline-none focus:border-[var(--color-accent)]/50 appearance-none cursor-pointer"
        >
          <option value="">All types</option>
          <option value="remote">Remote</option>
          <option value="hybrid">Hybrid</option>
          <option value="onsite">On-site</option>
        </select>
      </div>

      {/* Job List */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-6 h-6 text-[var(--color-accent)] animate-spin" />
          <span className="ml-3 text-sm text-[var(--color-text-secondary)]">
            Loading jobs...
          </span>
        </div>
      ) : jobs.length === 0 ? (
        <div className="glass rounded-2xl p-12 text-center">
          <p className="text-[var(--color-text-muted)] mx-auto mb-4 text-center">
            No jobs found
          </p>
          <p className="text-[var(--color-text-secondary)]">
            No jobs found. Try adjusting your filters or run the crawler first.
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {jobs.map((job) => (
            <a
              key={job.id}
              href={job.url}
              target="_blank"
              rel="noopener noreferrer"
              className="glass rounded-xl p-4 flex items-start gap-4 hover:border-[var(--color-border-bright)] transition-all group block"
            >
              <div className="w-10 h-10 rounded-lg bg-[var(--color-surface-3)] flex items-center justify-center shrink-0 group-hover:bg-[var(--color-accent)]/10 transition-colors">
                <span className="text-[var(--color-text-secondary)] font-bold text-lg leading-none">
                  {job.company?.[0]?.toUpperCase() || "?"}
                </span>
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <h3 className="text-sm font-semibold text-[var(--color-text)] group-hover:text-[var(--color-accent-light)] transition-colors truncate">
                      {job.title}
                    </h3>
                    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-1 text-xs text-[var(--color-text-secondary)]">
                      <span className="flex items-center gap-1">
                        {job.company || "Unknown"}
                      </span>
                      {job.location && (
                        <span className="flex items-center gap-1">
                          {job.location}
                        </span>
                      )}
                      {job.remote_type && (
                        <span className="flex items-center gap-1">
                          {job.remote_type}
                        </span>
                      )}
                      <span className="text-[var(--color-text-muted)]">
                        {job.source}
                      </span>
                      {job.posted_date && (
                        <span className="flex items-center gap-1 text-[var(--color-text-muted)]">
                          {timeAgo(job.posted_date)}
                        </span>
                      )}
                      {(job.salary_min || job.salary_max) && (
                        <span className="text-[var(--color-success)] font-medium">
                          {formatSalary(job.salary_min, job.salary_max)}
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <span className="text-[var(--color-text-muted)] opacity-0 group-hover:opacity-100 transition-opacity text-xs">
                      Open ↗
                    </span>
                  </div>
                </div>
              </div>
            </a>
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-3 pt-4">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1}
            className="flex items-center gap-1 px-3 py-2 rounded-lg bg-[var(--color-surface-2)] border border-[var(--color-border)] text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-text)] hover:border-[var(--color-border-bright)] disabled:opacity-30 disabled:cursor-not-allowed transition-all"
          >
            &lt; Prev
          </button>
          <span className="text-sm text-[var(--color-text-secondary)]">
            {page} / {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages}
            className="flex items-center gap-1 px-3 py-2 rounded-lg bg-[var(--color-surface-2)] border border-[var(--color-border)] text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-text)] hover:border-[var(--color-border-bright)] disabled:opacity-30 disabled:cursor-not-allowed transition-all"
          >
            Next &gt;
          </button>
        </div>
      )}
    </div>
  );
}
