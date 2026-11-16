
"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowRight,
  ShieldCheck,
  UserPlus,
} from "lucide-react";

import { useAuth } from "@/components/auth-provider";

export default function RegisterPage() {
  const router = useRouter();
  const { register, user, loading } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!loading && user) {
      router.replace("/");
    }
  }, [loading, user, router]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");

    if (password.length < 12) {
      setError("Password must contain at least 12 characters.");
      return;
    }

    if (password.length > 128) {
      setError("Password must not exceed 128 characters.");
      return;
    }

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setSubmitting(true);

    try {
      await register(email.trim(), password);
      router.replace("/");
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to create account"
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-[#080d19] px-5 py-12">
      <div className="w-full max-w-md">
        <div className="mb-9 text-center">
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-blue-600/15 text-blue-400">
            <ShieldCheck size={35} />
          </div>

          <h1 className="mt-5 text-3xl font-bold text-white">
            SecureAgent <span className="text-blue-400">AI</span>
          </h1>

          <p className="mt-2 text-sm text-slate-400">
            Create your secure investigation account.
          </p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="rounded-2xl border border-slate-800 bg-[#101827] p-7"
        >
          <div className="mb-7 flex items-center gap-3">
            <UserPlus size={21} className="text-blue-400" />
            <h2 className="text-xl font-semibold">
              Create Account
            </h2>
          </div>

          <label
            htmlFor="email"
            className="block text-sm font-medium text-slate-300"
          >
            Email address
          </label>

          <input
            id="email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="name@company.com"
            className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-white outline-none focus:border-blue-500"
          />

          <label
            htmlFor="password"
            className="mt-5 block text-sm font-medium text-slate-300"
          >
            Password
          </label>

          <input
            id="password"
            type="password"
            autoComplete="new-password"
            minLength={12}
            maxLength={128}
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="Create a password"
            className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-white outline-none focus:border-blue-500"
          />

          <label
            htmlFor="confirmPassword"
            className="mt-5 block text-sm font-medium text-slate-300"
          >
            Confirm password
          </label>

          <input
            id="confirmPassword"
            type="password"
            autoComplete="new-password"
            required
            value={confirmPassword}
            onChange={(event) =>
              setConfirmPassword(event.target.value)
            }
            placeholder="Re-enter your password"
            className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-white outline-none focus:border-blue-500"
          />

          {error && (
            <p
              role="alert"
              className="mt-5 rounded-lg border border-red-500/20 bg-red-500/10 p-3 text-sm text-red-400"
            >
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={submitting || loading}
            className="mt-7 flex w-full items-center justify-center gap-2 rounded-xl bg-blue-600 px-5 py-3 font-semibold text-white transition hover:bg-blue-500 disabled:opacity-60"
          >
            {submitting ? "Creating account..." : "Create Account"}
            {!submitting && <ArrowRight size={18} />}
          </button>

          <p className="mt-6 text-center text-sm text-slate-400">
            Already registered?{" "}
            <Link
              href="/login"
              className="font-semibold text-blue-400"
            >
              Sign in
            </Link>
          </p>
        </form>
      </div>
    </main>
  );
}
