
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  BarChart3,
  LoaderCircle,
  RefreshCw,
} from "lucide-react";

import Sidebar from "@/components/sidebar";
import ProtectedRoute from "@/components/protected-route";
import SecurityAnalytics from "@/components/security-analytics";
import { useAuth } from "@/components/auth-provider";

import {
  getInvestigationReports,
  type InvestigationSummary,
} from "@/lib/investigations";

async function fetchAllReports(token: string) {
  const reports: InvestigationSummary[] = [];
  let offset = 0;

  while (true) {
    const response = await getInvestigationReports(
      token,
      100,
      offset
    );

    reports.push(...response.items);
    offset += response.items.length;

    if (
      response.items.length === 0 ||
      offset >= response.total
    ) {
      break;
    }
  }

  return reports;
}

function AnalyticsWorkspace() {
  const { token } = useAuth();

  const [data, setData] = useState<{
    token: string;
    reports: InvestigationSummary[];
  } | null>(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;

    let cancelled = false;

    async function load() {
      try {
        const reports = await fetchAllReports(token as string);

        if (!cancelled) {
          setData({
            token: token as string,
            reports,
          });
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error
              ? err.message
              : "Failed to load analytics."
          );
        }
      }
    }

    void load();

    return () => {
      cancelled = true;
    };
  }, [token]);

  async function refresh() {
    if (!token) return;

    setLoading(true);
    setError(null);

    try {
      const reports = await fetchAllReports(token);

      setData({
        token,
        reports,
      });
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Failed to refresh analytics."
      );
    } finally {
      setLoading(false);
    }
  }

  const reports =
    data?.token === token ? data.reports : [];

  const initialLoading = Boolean(token && data?.token !== token);

  return (
    <div className="min-h-screen bg-[#080d19] text-white">
      <Sidebar />

      <main className="min-h-screen px-5 pb-12 pt-20 sm:px-8 lg:ml-64 lg:px-10 lg:pt-8">
        <header className="mb-8 border-b border-slate-800 pb-7">
          <Link
            href="/"
            className="inline-flex items-center gap-2 text-sm text-slate-400 hover:text-white"
          >
            <ArrowLeft size={16} />
            Back to Dashboard
          </Link>

          <div className="mt-5 flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className="rounded-xl bg-blue-600/15 p-3 text-blue-400">
                <BarChart3 size={26} />
              </div>

              <div>
                <h1 className="text-3xl font-bold">
                  Security Analytics
                </h1>
                <p className="mt-2 text-sm text-slate-400">
                  Investigation metrics and security operations insights.
                </p>
              </div>
            </div>

            <button
              type="button"
              onClick={() => void refresh()}
              disabled={loading || !token}
              className="inline-flex items-center gap-2 rounded-xl border border-slate-700 px-4 py-2.5 text-sm text-slate-300 hover:bg-slate-800 disabled:opacity-50"
            >
              <RefreshCw
                size={17}
                className={loading ? "animate-spin" : ""}
              />
              Refresh Analytics
            </button>
          </div>
        </header>

        {error && (
          <div className="mb-6 rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-300">
            {error}
          </div>
        )}

        {initialLoading && !error ? (
          <div className="flex items-center gap-3 rounded-2xl border border-slate-800 bg-[#101827] p-8 text-slate-400">
            <LoaderCircle
              size={20}
              className="animate-spin text-blue-400"
            />
            Loading security analytics...
          </div>
        ) : (
          <SecurityAnalytics reports={reports} />
        )}
      </main>
    </div>
  );
}

export default function AnalyticsPage() {
  return (
    <ProtectedRoute>
      <AnalyticsWorkspace />
    </ProtectedRoute>
  );
}
