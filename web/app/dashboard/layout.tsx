"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { ThemeToggle } from "@/components/ThemeToggle";
import { Menu } from "lucide-react";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Jobs" },
  { href: "/dashboard/news", label: "News" },
  { href: "/dashboard/ats", label: "ATS Analyzer" },
  { href: "/dashboard/sources", label: "Sources" },
  { href: "/dashboard/settings", label: "Settings" },
];

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="flex h-dvh overflow-hidden bg-[var(--color-background)]">
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 w-60 flex flex-col border-r border-[var(--color-border)] bg-[var(--color-surface)] transition-transform duration-200 lg:static lg:translate-x-0 ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        {/* Logo */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-[var(--color-border)]">
          <Link href="/" className="flex items-center gap-2">
            <img
              src="/logo.png"
              alt="JH Logo"
              className="w-8 h-8 object-contain dark:invert rounded-md"
            />
            <span
              className="text-lg font-semibold text-[var(--color-text)] tracking-tight"
              style={{ fontFamily: "var(--font-heading)" }}
            >
              JobHunter
            </span>
          </Link>
          <button
            onClick={() => setSidebarOpen(false)}
            className="lg:hidden text-[var(--color-text-muted)] hover:text-white"
          >
            ✕
          </button>
        </div>

        {/* Nav links */}
        <nav className="flex-1 px-3 py-4 space-y-1">
          {NAV_ITEMS.map((item) => {
            const isActive =
              item.href === "/dashboard"
                ? pathname === "/dashboard"
                : pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setSidebarOpen(false)}
                className={`sidebar-link flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium ${
                  isActive ? "active" : "text-[var(--color-text-secondary)]"
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>

        {/* Footer */}
        <div className="px-5 py-4 border-t border-[var(--color-border)] flex items-center justify-between">
          <p className="text-xs text-[var(--color-text-muted)]">JobHunter</p>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Mobile header */}
        <div className="lg:hidden flex items-center gap-3 px-4 py-3 border-b border-[var(--color-border)] bg-[var(--color-surface)]">
          <button
            onClick={() => setSidebarOpen(true)}
            className="text-[var(--color-text-secondary)] hover:text-white"
          >
            <Menu className="w-5 h-5" />
          </button>
          <span
            className="text-base font-semibold text-[var(--color-text)]"
            style={{ fontFamily: "var(--font-heading)" }}
          >
            JobHunter
          </span>
        </div>

        <div className="flex-1 overflow-y-auto p-4 md:p-6 lg:p-8">
          {children}
        </div>
      </main>
    </div>
  );
}
