"use client";

import { useState } from "react";
import { signInWithPopup, createUserWithEmailAndPassword, updateProfile } from "firebase/auth";
import { auth, googleProvider } from "@/lib/firebase";
import { useRouter } from "next/navigation";
import Link from "next/link";

export default function SignupPage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const router = useRouter();

  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const handleGoogleSignup = async () => {
    if (!auth || !googleProvider) {
      router.push("/dashboard/settings");
      return;
    }

    setLoading(true);
    setError("");
    try {
      await signInWithPopup(auth, googleProvider);
      router.push("/dashboard/settings");
    } catch (err: any) {
      setError(err.message || "Failed to sign up with Google.");
      setLoading(false);
    }
  };

  const handleEmailSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!auth) {
      router.push("/dashboard/settings");
      return;
    }

    if (!firstName || !lastName || !email || !password) {
      setError("Please fill in all fields.");
      return;
    }

    setLoading(true);
    setError("");
    try {
      const userCredential = await createUserWithEmailAndPassword(auth, email, password);
      await updateProfile(userCredential.user, {
        displayName: `${firstName} ${lastName}`
      });
      router.push("/dashboard/settings");
    } catch (err: any) {
      setError(err.message || "Failed to create account.");
      setLoading(false);
    }
  };

  return (
    <div className="min-h-dvh flex items-center justify-center p-4">
      <div className="w-full max-w-md space-y-6 glass rounded-2xl p-8">
        <div className="flex flex-col items-center text-center">
          <Link href="/" className="flex items-center justify-center mb-6">
            <img
              src="/icon.png"
              alt="JH Logo"
              className="w-12 h-12 object-contain"
              onError={(e) => {
                e.currentTarget.src = "/logo.png"; // fallback
              }}
            />
          </Link>
          <h2
            className="text-2xl font-semibold text-[var(--color-text)] tracking-tight"
            style={{ fontFamily: "var(--font-heading)" }}
          >
            Create a new account
          </h2>
          <p className="mt-2 text-sm text-[var(--color-text-secondary)]">
            Get matched with jobs tailored to your skills, passions, and experience and track your applications – all for free.
          </p>
        </div>

        {error && (
          <div className="flex items-center gap-2 p-3 rounded-lg bg-[var(--color-danger)]/10 border border-[var(--color-danger)]/20">
            <p className="text-xs text-[var(--color-danger)]">{error}</p>
          </div>
        )}

        <div className="space-y-4">
          <button
            type="button"
            onClick={handleGoogleSignup}
            disabled={loading}
            className="w-full flex items-center justify-center gap-3 px-4 py-3 rounded-xl bg-white text-black text-sm font-semibold hover:bg-gray-100 transition-colors disabled:opacity-50"
          >
            {loading ? (
              <span className="animate-pulse">Loading...</span>
            ) : (
              <svg className="w-5 h-5" viewBox="0 0 24 24">
                <path
                  fill="currentColor"
                  d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                />
                <path
                  fill="#34A853"
                  d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                />
                <path
                  fill="#FBBC05"
                  d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                />
                <path
                  fill="#EA4335"
                  d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                />
              </svg>
            )}
            Sign up with Google
          </button>
        </div>

        <div className="relative">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-[var(--color-border)]"></div>
          </div>
          <div className="relative flex justify-center text-sm">
            <span className="px-2 bg-[var(--color-surface)] text-[var(--color-text-muted)]">or</span>
          </div>
        </div>

        <form onSubmit={handleEmailSignup} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1">
              <label className="text-xs font-medium text-[var(--color-text-secondary)]">First name</label>
              <input
                type="text"
                placeholder="First name"
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
                className="w-full px-4 py-2.5 rounded-xl bg-[var(--color-surface-3)] border border-[var(--color-border)] text-sm text-[var(--color-text)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-accent)]/50 transition-colors"
                required
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs font-medium text-[var(--color-text-secondary)]">Last name</label>
              <input
                type="text"
                placeholder="Last name"
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
                className="w-full px-4 py-2.5 rounded-xl bg-[var(--color-surface-3)] border border-[var(--color-border)] text-sm text-[var(--color-text)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-accent)]/50 transition-colors"
                required
              />
            </div>
          </div>

          <div className="space-y-1">
            <label className="text-xs font-medium text-[var(--color-text-secondary)]">Email</label>
            <input
              type="email"
              placeholder="Email address"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-4 py-2.5 rounded-xl bg-[var(--color-surface-3)] border border-[var(--color-border)] text-sm text-[var(--color-text)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-accent)]/50 transition-colors"
              required
            />
          </div>

          <div className="space-y-1">
            <label className="text-xs font-medium text-[var(--color-text-secondary)]">Password</label>
            <input
              type="password"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-2.5 rounded-xl bg-[var(--color-surface-3)] border border-[var(--color-border)] text-sm text-[var(--color-text)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-accent)]/50 transition-colors"
              required
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full flex items-center justify-center gap-3 px-4 py-3 rounded-xl bg-[var(--color-accent)] text-white text-sm font-semibold hover:bg-[var(--color-accent-light)] transition-colors disabled:opacity-50"
          >
            Sign up
          </button>
        </form>

        <p className="text-center text-sm text-[var(--color-text-secondary)]">
          Already have an account?{" "}
          <Link
            href="/auth/login"
            className="text-[var(--color-accent-light)] hover:underline font-medium"
          >
            Log in
          </Link>
        </p>

        <p className="text-center text-xs text-[var(--color-text-muted)] px-4">
          By clicking 'Sign up', you acknowledge that you have read and accepted the Terms of Service and Privacy Policy.
        </p>
      </div>
    </div>
  );
}
