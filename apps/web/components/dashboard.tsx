
"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";

import {
  Activity,
  ArrowRight,
  BrainCircuit,
  CheckCircle2,
  Clock3,
  FileSearch,
  FileText,
  LockKeyhole,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
} from "lucide-react";

import Sidebar from "@/components/sidebar";
import StatCard from "@/components/stat-card";
import { useAuth } from "@/components/auth-provider";

import {
  getInvestigationReports,
  type InvestigationReportList,
  type InvestigationSummary,
} from "@/lib/investigations";

const capabilities = [
  {
    title: "Security Analysis",
    description:
      "Analyze authentication events and detect suspicious activity.",
    icon: ShieldAlert,
    color: "text-blue-400",
  },
  {
    title: "Evidence Retrieval",
    description:
      "Retrieve relevant context from authorized security documents.",
    icon: BrainCircuit,
    color: "text-purple-400",
  },
  {
    title: "Report Generation",
    description:
      "Generate structured findings, risk assessments and recommendations.",
    icon: FileText,
    color: "text-emerald-400",
  },
];

function severityStyle(severity: string) {
  switch (severity.toLowerCase()) {
    case "critical":
      return "bg-red-500/15 text-red-300";
    case "high":
      return "bg-orange-500/15 text-orange-300";
    case "medium":
      return "bg-yellow-500/15 text-yellow-300";
    case "low":
      return "bg-emerald-500/15 text-emerald-300";
    default:
      return "bg-slate-700 text-slate-300";
  }
}

function isPendingReview(status: string | null | undefined) {
  return status === "pending" || status === "pending_analyst_review";
}

function displayReviewStatus(status: string | null | undefined) {
  return isPendingReview(status) ? "Pending review" : status ?? "—";
}

function formatDate(value: string) {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "Unknown date";
  }

  return (
    date.toISOString().replace("T", " ").slice(0, 16) +
    " UTC"
  );
}

export default function Dashboard() {
  const { token, user } = useAuth();

  const [data, setData] =
    useState<InvestigationReportList | null>(null);

  const [loadedToken, setLoadedToken] = useState<string | null>(
    null
  );

  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loading = Boolean(
    token && loadedToken !== token
  );

  const currentData =
    token && loadedToken === token ? data : null;

  const loadReports = useCallback(async () => {
    if (!token) {
      return;
    }

    setRefreshing(true);
    setError(null);

    try {
      const response = await getInvestigationReports(
        token,
        100,
        0
      );

      setData(response);
      setLoadedToken(token);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to load investigation reports"
      );
    } finally {
      setRefreshing(false);
    }
  }, [token]);

  useEffect(() => {
    if (!token) {
      return;
    }

    let cancelled = false;

    async function fetchInitialReports() {
      try {
        const response = await getInvestigationReports(
          token as string,
          100,
          0
        );

        if (!cancelled) {
          setData(response);
          setLoadedToken(token);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setLoadedToken(token);
          setError(
            err instanceof Error
              ? err.message
              : "Unable to load investigation reports"
          );
        }
      }
    }

    void fetchInitialReports();

    return () => {
      cancelled = true;
    };
  }, [token]);

  const reports = currentData?.items ?? [];

  const highRisk = reports.filter(
    (report) =>
      report.severity.toLowerCase() === "high" ||
      report.severity.toLowerCase() === "critical"
  ).length;

  const pendingReviews = reports.filter((report) =>
    isPendingReview(report.review_status)
  ).length;

  const recentReports = reports.slice(0, 5);

  const sampleLimited =
    currentData !== null &&
    currentData.total > reports.length;

  return (
    <div className="min-h-screen bg-[#080d19]">
      <Sidebar />

      <main className="min-h-screen px-5 pb-12 pt-20 sm:px-8 lg:ml-64 lg:px-10 lg:pt-8">
        <header className="flex flex-wrap items-center justify-between gap-5 border-b border-slate-800 pb-7">
          <div>
            <div className="flex items-center gap-2 text-sm text-blue-400">
              <Activity size={16} />
              Security Operations Workspace
            </div>

            <h1 className="mt-2 text-3xl font-bold tracking-tight text-white">
              Dashboard
            </h1>

            <p className="mt-2 text-sm text-slate-400">
              Your AI-powered cybersecurity investigation workspace.
            </p>

            {user && (
              <p className="mt-2 text-xs text-slate-500">
                Signed in as {user.email}
              </p>
            )}
          </div>

          <button
            type="button"
            onClick={() => void loadReports()}
            disabled={loading || refreshing || !token}
            className="flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-sm text-slate-300 transition hover:bg-slate-800 disabled:opacity-50"
          >
            <RefreshCw
              size={17}
              className={
                refreshing ? "animate-spin" : ""
              }
            />
            Refresh
          </button>
        </header>

        <div className="mt-8 flex flex-wrap items-center justify-between gap-4">
          <div>
            <h2 className="text-xl font-semibold text-white">
              Security Overview
            </h2>

            <p className="mt-1 text-sm text-slate-500">
              {loading
                ? "Loading investigation data..."
                : "Statistics from your saved investigation reports."}
            </p>
          </div>

          <Link
            href="/investigations"
            className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-blue-500"
          >
            <FileSearch size={17} />
            New Investigation
            <ArrowRight size={16} />
          </Link>
        </div>

        {error && (
          <div
            role="alert"
            className="mt-6 rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-300"
          >
            {error}
          </div>
        )}

        <div className="mt-6 grid gap-5 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard
            title="Saved Reports"
            value={
              currentData ? currentData.total : "—"
            }
            description="Total saved investigation reports"
            icon={FileSearch}
            color="blue"
          />

          <StatCard
            title="High-Risk Incidents"
            value={currentData ? highRisk : "—"}
            description={
              sampleLimited
                ? "High or critical severity in latest 100 reports"
                : "High or critical severity reports"
            }
            icon={ShieldAlert}
            color="red"
          />

          <StatCard
            title="Completed Reports"
            value={
              currentData ? currentData.total : "—"
            }
            description="Successfully saved reports"
            icon={CheckCircle2}
            color="green"
          />

          <StatCard
            title="Pending Reviews"
            value={
              currentData ? pendingReviews : "—"
            }
            description={
              sampleLimited
                ? "Pending reviews in latest 100 reports"
                : "Awaiting analyst review"
            }
            icon={Clock3}
            color="purple"
          />
        </div>

        <div className="mt-8 grid gap-6 xl:grid-cols-3">
          <section className="rounded-2xl border border-slate-800 bg-[#101827] p-6 xl:col-span-2">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <h2 className="text-lg font-semibold text-white">
                  Recent Investigations
                </h2>

                <p className="mt-1 text-sm text-slate-500">
                  Latest saved security investigation reports.
                </p>
              </div>

              <FileSearch
                size={22}
                className="text-blue-400"
              />
            </div>

            {loading ? (
              <div className="py-16 text-center text-sm text-slate-400">
                Loading reports...
              </div>
            ) : recentReports.length === 0 ? (
              <div className="mt-7 rounded-xl border border-dashed border-slate-700 bg-slate-900/40 px-5 py-12 text-center">
                <Activity
                  size={28}
                  className="mx-auto text-blue-400"
                />

                <h3 className="mt-4 font-semibold text-white">
                  No saved investigations yet
                </h3>

                <p className="mt-2 text-sm text-slate-400">
                  Completed investigations will appear here
                  after their reports are saved.
                </p>
              </div>
            ) : (
              <div className="mt-6 space-y-3">
                {recentReports.map(
                  (report: InvestigationSummary) => (
                    <div
                      key={report.investigation_id}
                      className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-slate-800 bg-slate-900/40 p-4"
                    >
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-semibold text-white">
                          {report.title}
                        </p>

                        <p className="mt-1 text-xs text-slate-500">
                          {formatDate(report.created_at)}
                        </p>

                        <p className="mt-1 truncate font-mono text-xs text-slate-600">
                          {report.investigation_id}
                        </p>
                      </div>

                      <div className="flex items-center gap-3">
                        <span
                          className={`rounded-lg px-3 py-1 text-xs font-semibold capitalize ${severityStyle(
                            report.severity
                          )}`}
                        >
                          {report.severity}
                        </span>

                        <span
                          className="text-xs text-slate-400"
                          title={
                            report.review_status ?? ""
                          }
                        >
                          {displayReviewStatus(report.review_status)}
                        </span>
                      </div>
                    </div>
                  )
                )}
              </div>
            )}

            <div className="mt-6 flex justify-end">
              <Link
                href="/reports"
                className="flex items-center gap-2 text-sm font-semibold text-blue-400 hover:text-blue-300"
              >
                View all reports
                <ArrowRight size={16} />
              </Link>
            </div>
          </section>

          <section className="rounded-2xl border border-slate-800 bg-[#101827] p-6">
            <div className="flex items-center gap-3">
              <BrainCircuit
                size={22}
                className="text-purple-400"
              />

              <h2 className="text-lg font-semibold text-white">
                Investigation Workflow
              </h2>
            </div>

            <div className="mt-7 rounded-xl border border-blue-500/20 bg-blue-500/10 p-4 text-center">
              <p className="text-sm font-semibold text-blue-300">
                Supervisor Agent
              </p>

              <p className="mt-1 text-xs text-slate-400">
                Authorized workflow orchestration
              </p>
            </div>

            <div className="mx-auto h-7 w-px bg-slate-700" />

            <div className="space-y-3">
              {capabilities.map((agent) => {
                const Icon = agent.icon;

                return (
                  <div
                    key={agent.title}
                    className="flex items-start gap-3 rounded-xl border border-slate-800 bg-slate-900/50 p-4"
                  >
                    <Icon
                      size={19}
                      className={`mt-0.5 shrink-0 ${agent.color}`}
                    />

                    <div>
                      <p className="text-sm font-semibold text-white">
                        {agent.title}
                      </p>

                      <p className="mt-1 text-xs leading-5 text-slate-400">
                        {agent.description}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        </div>

        <section className="mt-8 grid gap-5 md:grid-cols-3">
          <Link
            href="/settings"
            className="group flex items-center gap-4 rounded-2xl border border-slate-800 bg-[#101827] p-5 transition hover:border-blue-500/50 hover:bg-slate-900 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-400"
          >
            <LockKeyhole size={23} className="shrink-0 text-blue-400" />
            <div className="min-w-0 flex-1">
              <p className="font-semibold">Permission Controls</p>
              <p className="mt-1 text-xs text-slate-500">Authorized specialist delegation</p>
            </div>
            <ArrowRight size={17} className="shrink-0 text-slate-500 transition group-hover:translate-x-1 group-hover:text-blue-400" />
          </Link>

          <Link
            href="/history"
            className="group flex items-center gap-4 rounded-2xl border border-slate-800 bg-[#101827] p-5 transition hover:border-emerald-500/50 hover:bg-slate-900 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-400"
          >
            <ShieldCheck size={23} className="shrink-0 text-emerald-400" />
            <div className="min-w-0 flex-1">
              <p className="font-semibold">Audit Logging</p>
              <p className="mt-1 text-xs text-slate-500">Investigation execution history</p>
            </div>
            <ArrowRight size={17} className="shrink-0 text-slate-500 transition group-hover:translate-x-1 group-hover:text-emerald-400" />
          </Link>

          <Link
            href="/reports"
            className="group flex items-center gap-4 rounded-2xl border border-slate-800 bg-[#101827] p-5 transition hover:border-purple-500/50 hover:bg-slate-900 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-purple-400"
          >
            <FileText size={23} className="shrink-0 text-purple-400" />
            <div className="min-w-0 flex-1">
              <p className="font-semibold">Structured Reports</p>
              <p className="mt-1 text-xs text-slate-500">Findings and evidence references</p>
            </div>
            <ArrowRight size={17} className="shrink-0 text-slate-500 transition group-hover:translate-x-1 group-hover:text-purple-400" />
          </Link>
        </section>
      </main>
    </div>
  );
}
