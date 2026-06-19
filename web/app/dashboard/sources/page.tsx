"use client";

import { useEffect, useState } from "react";
import { fetchSources, type SourceInfo } from "@/lib/api";

export default function SourcesPage() {
  const [sources, setSources] = useState<SourceInfo[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetchSources().then((data) => {
      if (data) setSources(data);
      setLoading(false);
    });
  }, []);

  const atsSources = sources.filter((s) => s.type === "ats");
  const aggregators = sources.filter((s) => s.type === "aggregator");

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h1
          className="text-2xl md:text-3xl font-semibold text-[var(--color-text)] tracking-tight"
          style={{ fontFamily: "var(--font-heading)" }}
        >
          Data Sources
        </h1>
        <p className="mt-1 text-sm text-[var(--color-text-secondary)]">
          {sources.length} sources configured ·{" "}
          {sources.filter((s) => s.enabled).length} active
        </p>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20 text-[var(--color-accent)]">
          <span className="ml-3 text-sm text-[var(--color-text-secondary)]">
            Loading sources...
          </span>
        </div>
      ) : (
        <>
          {atsSources.length > 0 && (
            <div>
              <h2 className="text-sm font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider mb-3">
                ATS Platforms
              </h2>
              <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {atsSources.map((src) => (
                  <SourceCard key={src.name} source={src} />
                ))}
              </div>
            </div>
          )}

          {aggregators.length > 0 && (
            <div>
              <h2 className="text-sm font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider mb-3">
                Aggregators & Job Boards
              </h2>
              <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {aggregators.map((src) => (
                  <SourceCard key={src.name} source={src} />
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function SourceCard({ source }: { source: SourceInfo }) {
  return (
    <div className="glass rounded-xl p-4 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-[var(--color-surface-3)] flex items-center justify-center font-bold text-[var(--color-text-secondary)]">
          {source.name.charAt(0).toUpperCase()}
        </div>
        <div>
          <p className="text-sm font-medium text-[var(--color-text)]">
            {source.name}
            {source.count != null && (
              <span className="text-[var(--color-text-muted)] font-normal">
                {" "}
                · {source.count}
              </span>
            )}
          </p>
          <p className="text-xs text-[var(--color-text-muted)] capitalize">
            {source.type}
          </p>
        </div>
      </div>
      {source.enabled ? (
        <span className="text-[var(--color-success)] text-xs font-bold">
          ON
        </span>
      ) : (
        <span className="text-[var(--color-text-muted)] text-xs font-bold">
          OFF
        </span>
      )}
    </div>
  );
}
