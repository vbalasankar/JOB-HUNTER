"use client";

import { useEffect, useState } from "react";
import { fetchNews, type NewsItem, timeAgo } from "@/lib/api";

export default function NewsPage() {
  const [items, setItems] = useState<NewsItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetchNews().then((data) => {
      if (data) setItems(data);
      setLoading(false);
    });
  }, []);

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h1
          className="text-2xl md:text-3xl font-semibold text-[var(--color-text)] tracking-tight"
          style={{ fontFamily: "var(--font-heading)" }}
        >
          Tech News
        </h1>
        <p className="mt-1 text-sm text-[var(--color-text-secondary)]">
          Curated tech news from Hacker News and startup feeds.
        </p>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20 text-[var(--color-accent)]">
          <span className="ml-3 text-sm text-[var(--color-text-secondary)]">
            Loading news...
          </span>
        </div>
      ) : items.length === 0 ? (
        <div className="glass rounded-2xl p-12 text-center">
          <p className="text-[var(--color-text-muted)] mx-auto mb-4 font-bold">
            No News
          </p>
          <p className="text-[var(--color-text-secondary)]">
            No news available yet.
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {items.map((item) => (
            <a
              key={item.id}
              href={item.url}
              target="_blank"
              rel="noopener noreferrer"
              className="glass rounded-xl p-4 hover:border-[var(--color-border-bright)] transition-all group block"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <h3 className="text-sm font-semibold text-[var(--color-text)] group-hover:text-[var(--color-accent-light)] transition-colors">
                    {item.title}
                  </h3>
                  <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-1.5 text-xs text-[var(--color-text-secondary)]">
                    <span className="font-medium text-[var(--color-accent-light)]/80">
                      {item.source}
                    </span>
                    {item.author && (
                      <span className="flex items-center gap-1">
                        Author: {item.author}
                      </span>
                    )}
                    {item.published_at && (
                      <span className="flex items-center gap-1 text-[var(--color-text-muted)]">
                        {timeAgo(item.published_at)}
                      </span>
                    )}
                    {item.points != null && (
                      <span className="flex items-center gap-1">
                        {item.points} pts
                      </span>
                    )}
                    {item.comment_count != null && (
                      <span className="flex items-center gap-1">
                        {item.comment_count} comments
                      </span>
                    )}
                  </div>
                  {item.summary && (
                    <p className="mt-2 text-xs text-[var(--color-text-muted)] line-clamp-2">
                      {item.summary}
                    </p>
                  )}
                  {item.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 mt-2">
                      {item.tags.map((tag) => (
                        <span
                          key={tag}
                          className="px-2 py-0.5 rounded-md bg-[var(--color-accent)]/10 text-[10px] font-medium text-[var(--color-accent-light)]"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
                <span className="text-[var(--color-text-muted)] opacity-0 group-hover:opacity-100 transition-opacity shrink-0 mt-0.5 text-xs">
                  Open ↗
                </span>
              </div>
            </a>
          ))}
        </div>
      )}
    </div>
  );
}
