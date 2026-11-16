
"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";

import {
  AlertCircle,
  ArrowLeft,
  ArrowRight,
  CalendarDays,
  ChevronLeft,
  ChevronRight,
  FileSearch,
  FileText,
  Filter,
  LoaderCircle,
  RefreshCw,
  Search,
  ShieldAlert,
} from "lucide-react";

import Sidebar from "@/components/sidebar";
import ProtectedRoute from "@/components/protected-route";
import { useAuth } from "@/components/auth-provider";

import {
  getInvestigationReports,
  type InvestigationSummary,
} from "@/lib/investigations";

const PAGE_SIZE = 12;
const FETCH_LIMIT = 100;

type SortOption = "newest" | "oldest" | "severity";
type SeverityFilter =
  | "all"
  | "critical"
  | "high"
  | "medium"
  | "low";
type StatusFilter = "all" | "reviewed" | "pending";

type ReportsData = {
  token: string;
  reports: InvestigationSummary[];
};

const severityOrder: Record<string, number> = {
  critical: 4,
  high: 3,
  medium: 2,
  low: 1,
};

function severityStyle(value: string) {
  switch (value.toLowerCase()) {
    case "critical":
      return "border-red-500/30 bg-red-500/10 text-red-300";
    case "high":
      return "border-orange-500/30 bg-orange-500/10 text-orange-300";
    case "medium":
      return "border-amber-500/30 bg-amber-500/10 text-amber-300";
    case "low":
      return "border-emerald-500/30 bg-emerald-500/10 text-emerald-300";
    default:
      return "border-slate-700 bg-slate-800 text-slate-300";
  }
}

function formatDate(value: string) {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) return value;

  return date.toLocaleString("en-IE", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "UTC",
    timeZoneName: "short",
  });
}

function isReviewed(status: string | null) {
  return status?.toLowerCase() === "reviewed";
}

function ReportsLibrary() {
  const { token } = useAuth();

  const [data, setData] = useState<ReportsData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [search, setSearch] = useState("");
  const [severity, setSeverity] =
    useState<SeverityFilter>("all");
  const [status, setStatus] =
    useState<StatusFilter>("all");
  const [sort, setSort] = useState<SortOption>("newest");
  const [page, setPage] = useState(1);

  const loadReports = useCallback(async () => {
    if (!token) return;

    setLoading(true);
    setError(null);

    try {
      const allReports: InvestigationSummary[] = [];
      let offset = 0;

      while (true) {
        const response = await getInvestigationReports(
          token,
          FETCH_LIMIT,
          offset
        );

        allReports.push(...response.items);
        offset += response.items.length;

        if (
          response.items.length === 0 ||
          offset >= response.total
        ) {
          break;
        }
      }

      setData({
        token,
        reports: allReports,
      });
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to load investigation reports."
      );
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    if (!token) return;

    let cancelled = false;

    async function fetchInitialReports() {
      try {
        const allReports: InvestigationSummary[] = [];
        let offset = 0;

        while (!cancelled) {
          const response = await getInvestigationReports(
            token as string,
            FETCH_LIMIT,
            offset
          );

          if (cancelled) return;

          allReports.push(...response.items);
          offset += response.items.length;

          if (
            response.items.length === 0 ||
            offset >= response.total
          ) {
            break;
          }
        }

        if (!cancelled) {
          setData({
            token: token as string,
            reports: allReports,
          });
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error
              ? err.message
              : "Unable to load investigation reports."
          );
        }
      }
    }

    void fetchInitialReports();

    return () => {
      cancelled = true;
    };
  }, [token]);

  const currentReports = useMemo(
  () => (data?.token === token ? data.reports : []),
  [data, token]
);

  const filteredReports = useMemo(() => {
    const query = search.trim().toLowerCase();

    return currentReports
      .filter((report) => {
        const matchesSearch =
          !query ||
          report.title.toLowerCase().includes(query) ||
          report.investigation_id.toLowerCase().includes(query) ||
          report.severity.toLowerCase().includes(query);

        const matchesSeverity =
          severity === "all" ||
          report.severity.toLowerCase() === severity;

        const reviewed = isReviewed(report.review_status);

        const matchesStatus =
          status === "all" ||
          (status === "reviewed" && reviewed) ||
          (status === "pending" && !reviewed);

        return matchesSearch && matchesSeverity && matchesStatus;
      })
      .sort((a, b) => {
        if (sort === "severity") {
          const severityDifference =
            (severityOrder[b.severity.toLowerCase()] ?? 0) -
            (severityOrder[a.severity.toLowerCase()] ?? 0);

          if (severityDifference !== 0) {
            return severityDifference;
          }
        }

        const dateA = new Date(a.created_at).getTime();
        const dateB = new Date(b.created_at).getTime();

        return sort === "oldest"
          ? dateA - dateB
          : dateB - dateA;
      });
  }, [currentReports, search, severity, status, sort]);

  const totalPages = Math.max(
    1,
    Math.ceil(filteredReports.length / PAGE_SIZE)
  );

  const activePage = Math.min(page, totalPages);

  const visibleReports = filteredReports.slice(
    (activePage - 1) * PAGE_SIZE,
    activePage * PAGE_SIZE
  );

  const highRiskCount = currentReports.filter(
    (report) =>
      report.severity.toLowerCase() === "high" ||
      report.severity.toLowerCase() === "critical"
  ).length;

  const pendingCount = currentReports.filter(
    (report) => !isReviewed(report.review_status)
  ).length;

  const initialLoading = Boolean(token && data?.token !== token);

  return (
    <div className="min-h-screen bg-[#080d19] text-white">
      <Sidebar />

      <main className="min-h-screen px-5 pb-12 pt-20 sm:px-8 lg:ml-64 lg:px-10 lg:pt-8">
        <header className="border-b border-slate-800 pb-7">
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
                <FileSearch size={26} />
              </div>

              <div>
                <h1 className="text-3xl font-bold tracking-tight">
                  Reports Library
                </h1>

                <p className="mt-2 text-sm text-slate-400">
                  Browse and review saved AI security investigations.
                </p>
              </div>
            </div>

            <div className="flex flex-wrap gap-3">
              <button
                type="button"
                onClick={() => void loadReports()}
                disabled={loading || !token}
                className="inline-flex items-center gap-2 rounded-xl border border-slate-700 px-4 py-2.5 text-sm text-slate-300 hover:bg-slate-800 disabled:opacity-50"
              >
                <RefreshCw
                  size={16}
                  className={loading ? "animate-spin" : ""}
                />
                Refresh
              </button>

              <Link
                href="/investigations"
                className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-semibold hover:bg-blue-500"
              >
                <FileSearch size={17} />
                New Investigation
              </Link>
            </div>
          </div>
        </header>

        <div className="mt-8 grid gap-4 sm:grid-cols-3">
          {[
            {
              label: "Total Reports",
              value: currentReports.length,
              icon: FileText,
              color: "text-blue-400",
            },
            {
              label: "High-Risk Reports",
              value: highRiskCount,
              icon: ShieldAlert,
              color: "text-orange-400",
            },
            {
              label: "Pending Reviews",
              value: pendingCount,
              icon: AlertCircle,
              color: "text-amber-400",
            },
          ].map((metric) => (
            <div
              key={metric.label}
              className="rounded-2xl border border-slate-800 bg-[#101827] p-5"
            >
              <div className="flex items-center gap-2 text-sm text-slate-400">
                <metric.icon
                  size={18}
                  className={metric.color}
                />
                {metric.label}
              </div>

              <p className="mt-3 text-3xl font-bold">
                {metric.value}
              </p>
            </div>
          ))}
        </div>

        <section className="mt-7 rounded-2xl border border-slate-800 bg-[#101827] p-5">
          <div className="mb-5 flex items-center gap-2">
            <Filter size={18} className="text-blue-400" />
            <h2 className="font-semibold">
              Search & Filter Reports
            </h2>
          </div>

          <div className="grid gap-4 lg:grid-cols-4">
            <div className="relative lg:col-span-2">
              <Search
                size={17}
                className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500"
              />

              <input
                value={search}
                onChange={(event) => {
                  setSearch(event.target.value);
                  setPage(1);
                }}
                placeholder="Search title, ID, or severity..."
                aria-label="Search reports"
                className="w-full rounded-xl border border-slate-700 bg-[#080d19] py-3 pl-11 pr-4 text-sm text-white outline-none focus:border-blue-500"
              />
            </div>

            <select
              value={severity}
              onChange={(event) => {
                setSeverity(event.target.value as SeverityFilter);
                setPage(1);
              }}
              aria-label="Filter by severity"
              className="rounded-xl border border-slate-700 bg-[#080d19] px-4 py-3 text-sm text-slate-200 outline-none focus:border-blue-500"
            >
              <option value="all">All Severities</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>

            <select
              value={status}
              onChange={(event) => {
                setStatus(event.target.value as StatusFilter);
                setPage(1);
              }}
              aria-label="Filter by review status"
              className="rounded-xl border border-slate-700 bg-[#080d19] px-4 py-3 text-sm text-slate-200 outline-none focus:border-blue-500"
            >
              <option value="all">All Review Statuses</option>
              <option value="reviewed">Reviewed</option>
              <option value="pending">Pending / Unreviewed</option>
            </select>
          </div>

          <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-slate-800 pt-5">
            <p className="text-sm text-slate-400">
              Showing {filteredReports.length} matching reports
            </p>

            <select
              value={sort}
              onChange={(event) => {
                setSort(event.target.value as SortOption);
                setPage(1);
              }}
              aria-label="Sort reports"
              className="rounded-lg border border-slate-700 bg-[#080d19] px-3 py-2 text-sm text-slate-300"
            >
              <option value="newest">Newest First</option>
              <option value="oldest">Oldest First</option>
              <option value="severity">Highest Severity</option>
            </select>
          </div>
        </section>

        {error && (
          <div
            role="alert"
            className="mt-6 flex items-center gap-3 rounded-xl border border-red-500/30 bg-red-500/10 p-5 text-sm text-red-300"
          >
            <AlertCircle size={19} />
            {error}
          </div>
        )}

        {initialLoading && !error ? (
          <div className="mt-7 flex items-center gap-3 rounded-2xl border border-slate-800 bg-[#101827] p-8 text-slate-400">
            <LoaderCircle
              size={20}
              className="animate-spin text-blue-400"
            />
            Loading saved reports...
          </div>
        ) : visibleReports.length === 0 ? (
          <div className="mt-7 rounded-2xl border border-slate-800 bg-[#101827] px-6 py-16 text-center">
            <FileSearch
              size={36}
              className="mx-auto text-slate-600"
            />

            <h3 className="mt-4 text-lg font-semibold">
              No reports found
            </h3>

            <p className="mt-2 text-sm text-slate-400">
              {currentReports.length === 0
                ? "Run an investigation to generate your first saved report."
                : "Try changing your search or filter settings."}
            </p>

            <Link
              href="/investigations"
              className="mt-6 inline-flex items-center gap-2 rounded-xl bg-blue-600 px-5 py-3 text-sm font-semibold hover:bg-blue-500"
            >
              New Investigation
              <ArrowRight size={17} />
            </Link>
          </div>
        ) : (
          <div className="mt-7 grid gap-4 xl:grid-cols-2">
            {visibleReports.map((report) => (
              <Link
                key={report.investigation_id}
                href={`/reports/${encodeURIComponent(
                  report.investigation_id
                )}`}
                className="group rounded-2xl border border-slate-800 bg-[#101827] p-6 transition hover:border-blue-500/50 hover:bg-[#142036]"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="rounded-xl bg-blue-600/10 p-3 text-blue-400">
                    <FileText size={21} />
                  </div>

                  <span
                    className={`rounded-lg border px-3 py-1 text-xs font-semibold capitalize ${severityStyle(
                      report.severity
                    )}`}
                  >
                    {report.severity}
                  </span>
                </div>

                <h3 className="mt-5 line-clamp-2 text-lg font-semibold group-hover:text-blue-300">
                  {report.title || "Security Investigation"}
                </h3>

                <p className="mt-2 break-all font-mono text-xs text-slate-500">
                  {report.investigation_id}
                </p>

                <div className="mt-5 flex flex-wrap items-center gap-4 text-xs text-slate-400">
                  <span className="inline-flex items-center gap-2">
                    <CalendarDays size={15} />
                    {formatDate(report.created_at)}
                  </span>

                  <span
                    className={
                      isReviewed(report.review_status)
                        ? "text-emerald-400"
                        : "text-amber-400"
                    }
                  >
                    {isReviewed(report.review_status)
                      ? "Reviewed"
                      : report.review_status || "Unreviewed"}
                  </span>

                  <span className="text-slate-500">
                    Version {report.report_version}
                  </span>
                </div>

                <div className="mt-5 flex items-center justify-between border-t border-slate-800 pt-4 text-sm font-medium text-blue-400">
                  View Investigation Report
                  <ArrowRight
                    size={17}
                    className="transition group-hover:translate-x-1"
                  />
                </div>
              </Link>
            ))}
          </div>
        )}

        {filteredReports.length > PAGE_SIZE && (
          <div className="mt-7 flex flex-wrap items-center justify-between gap-4 rounded-xl border border-slate-800 bg-[#101827] p-4">
            <p className="text-sm text-slate-400">
              Page {activePage} of {totalPages}
            </p>

            <div className="flex items-center gap-2">
              <button
                type="button"
                disabled={activePage <= 1}
                onClick={() => setPage(activePage - 1)}
                className="rounded-lg border border-slate-700 p-2 text-slate-300 hover:bg-slate-800 disabled:opacity-40"
                aria-label="Previous page"
              >
                <ChevronLeft size={18} />
              </button>

              <button
                type="button"
                disabled={activePage >= totalPages}
                onClick={() => setPage(activePage + 1)}
                className="rounded-lg border border-slate-700 p-2 text-slate-300 hover:bg-slate-800 disabled:opacity-40"
                aria-label="Next page"
              >
                <ChevronRight size={18} />
              </button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default function ReportsPage() {
  return (
    <ProtectedRoute>
      <ReportsLibrary />
    </ProtectedRoute>
  );
}
