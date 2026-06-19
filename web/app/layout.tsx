import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "JobHunter — AI-Powered Job Search",
  description:
    "Find your dream job with AI-powered matching. JobHunter crawls 20+ sources, ranks jobs by resume fit, and delivers personalized recommendations.",
  keywords:
    "job search, AI job matching, job board, career, resume analyzer, ATS score",
  openGraph: {
    title: "JobHunter — AI-Powered Job Search",
    description:
      "Find your dream job with AI-powered matching across 20+ sources.",
    type: "website",
  },
};

import { AuthProvider } from "@/components/auth/AuthProvider";
import { ThemeProvider } from "@/components/ThemeProvider";

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-dvh flex flex-col antialiased bg-[var(--color-background)] text-[var(--color-text)]">
        <ThemeProvider
          attribute="class"
          defaultTheme="light"
          enableSystem={false}
        >
          <AuthProvider>{children}</AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
