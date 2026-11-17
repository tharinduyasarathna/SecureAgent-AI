"use client";

import { useMemo } from "react";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  CheckCircle2,
  Clock3,
  ShieldAlert,
} from "lucide-react";

import type { InvestigationSummary } from "@/lib/investigations";

type Props = {
  reports: InvestigationSummary[];
};

const severityLevels = [
  { name: "Critical", key: "critical", color: "bg-red-500", text: "text-red-400" },
  { name: "High", key: "high", color: "bg-orange-500", text: "text-orange-400" },
  { name: "Medium", key: "medium", color: "bg-amber-500", text: "text-amber-400" },
  { name: "Low", key: "low", color: "bg-emerald-500", text: "text-emerald-400" },
];

function normalizeReviewStatus(status: string | null | undefined): string {
  return (status ?? "").trim().toLowerCase();
}

function dateKey(value: string): string | null {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return date.toISOString().slice(0, 10);
}

export default function SecurityAnalytics({ reports }: Props) {
  const analytics = useMemo(() => {
    const severityCounts: Record<string, number> = {
      critical: 0,
      high: 0,
      medium: 0,
      low: 0,
    };

    let reviewed = 0;
    let pending = 0;

    for (const report of reports) {
      const severity = report.severity.toLowerCase();
      if (severity in severityCounts) {
        severityCounts[severity] += 1;
      }

      const reviewStatus = normalizeReviewStatus(report.review_status);
      if (
        reviewStatus === "approved" ||
        reviewStatus === "rejected" ||
        reviewStatus === "reviewed"
      ) {
        reviewed += 1;
      } else if (
        reviewStatus === "pending" ||
        reviewStatus === "pending_analyst_review"
      ) {
        pending += 1;
      }
    }

    const today = new Date();
    const lastSevenDays = Array.from({ length: 7 }, (_, index) => {
      const date = new Date(
        Date.UTC(
          today.getUTCFullYear(),
          today.getUTCMonth(),
          today.getUTCDate() - (6 - index)
        )
      );
      const key = date.toISOString().slice(0, 10);
      const count = reports.filter(
        (report) => dateKey(report.created_at) === key
      ).length;
      return {
        key,
        label: date.toLocaleDateString("en-IE", {
          weekday: "short",
          timeZone: "UTC",
        }),
        count,
      };
    });

    return { severityCounts, reviewed, pending, lastSevenDays };
  }, [reports]);

  const maxSeverity = Math.max(1, ...Object.values(analytics.severityCounts));
  const maxDaily = Math.max(1, ...analytics.lastSevenDays.map((day) => day.count));

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[
          {
            label: "Total Investigations",
            value: reports.length,
            icon: Activity,
            color: "text-blue-400",
          },
          {
            label: "Critical & High",
            value: analytics.severityCounts.critical + analytics.severityCounts.high,
            icon: ShieldAlert,
            color: "text-red-400",
          },
          {
            label: "Reviewed Reports",
            value: analytics.reviewed,
            icon: CheckCircle2,
            color: "text-emerald-400",
          },
          {
            label: "Pending Reviews",
            value: analytics.pending,
            icon: Clock3,
            color: "text-amber-400",
          },
        ].map((metric) => (
          <div
            key={metric.label}
            className="rounded-2xl border border-slate-800 bg-[#101827] p-5"
          >
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-400">{metric.label}</span>
              <metric.icon size={20} className={metric.color} />
            </div>
            <p className="mt-4 text-3xl font-bold text-white">{metric.value}</p>
          </div>
        ))}
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <section className="rounded-2xl border border-slate-800 bg-[#101827] p-6">
          <div className="mb-7 flex items-center gap-3">
            <ShieldAlert size={21} className="text-orange-400" />
            <div>
              <h3 className="text-lg font-semibold text-white">Severity Distribution</h3>
              <p className="mt-1 text-xs text-slate-400">
                Saved investigations by severity level
              </p>
            </div>
          </div>

          <div className="space-y-6">
            {severityLevels.map((level) => {
              const count = analytics.severityCounts[level.key] ?? 0;
              const percentage = reports.length > 0
                ? (count / reports.length) * 100
                : 0;

              return (
                <div key={level.key}>
                  <div className="mb-2 flex items-center justify-between">
                    <span className={`text-sm font-medium ${level.text}`}>
                      {level.name}
                    </span>
                    <span className="text-sm text-slate-300">
                      {count} ({percentage.toFixed(0)}%)
                    </span>
                  </div>
                  <div className="h-3 overflow-hidden rounded-full bg-slate-800">
                    <div
                      className={`h-full rounded-full ${level.color}`}
                      style={{ width: `${(count / maxSeverity) * 100}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>

          {reports.length === 0 && (
            <p className="mt-6 text-sm text-slate-500">
              No investigation data available yet.
            </p>
          )}
        </section>

        <section className="rounded-2xl border border-slate-800 bg-[#101827] p-6">
          <div className="mb-7 flex items-center gap-3">
            <BarChart3 size={21} className="text-blue-400" />
            <div>
              <h3 className="text-lg font-semibold text-white">Investigation Activity</h3>
              <p className="mt-1 text-xs text-slate-400">
                Reports created over the last seven days (UTC)
              </p>
            </div>
          </div>

          <div className="flex h-64 items-end justify-between gap-3 border-b border-slate-700 pb-2">
            {analytics.lastSevenDays.map((day) => {
              const height = day.count === 0
                ? 4
                : Math.max(8, (day.count / maxDaily) * 100);

              return (
                <div
                  key={day.key}
                  className="flex h-full flex-1 flex-col items-center justify-end gap-2"
                >
                  <span className="text-xs text-slate-400">{day.count}</span>
                  <div
                    title={`${day.key}: ${day.count} reports`}
                    className="w-full max-w-12 rounded-t-lg bg-blue-500/80 transition hover:bg-blue-400"
                    style={{ height: `${height}%` }}
                  />
                  <span className="text-xs text-slate-400">{day.label}</span>
                </div>
              );
            })}
          </div>
        </section>
      </div>

      <section className="rounded-2xl border border-slate-800 bg-[#101827] p-6">
        <div className="mb-5 flex items-center gap-3">
          <AlertTriangle size={21} className="text-amber-400" />
          <h3 className="text-lg font-semibold text-white">
            Security Operations Summary
          </h3>
        </div>

        <div className="grid gap-4 sm:grid-cols-3">
          <div className="rounded-xl border border-slate-800 bg-[#111e31] p-4">
            <p className="text-xs text-slate-400">High-Risk Percentage</p>
            <p className="mt-3 text-2xl font-bold text-orange-400">
              {reports.length > 0
                ? (
                    ((analytics.severityCounts.critical +
                      analytics.severityCounts.high) /
                      reports.length) * 100
                  ).toFixed(1)
                : "0.0"}
              %
            </p>
          </div>

          <div className="rounded-xl border border-slate-800 bg-[#111e31] p-4">
            <p className="text-xs text-slate-400">Review Completion Rate</p>
            <p className="mt-3 text-2xl font-bold text-emerald-400">
              {reports.length > 0
                ? ((analytics.reviewed / reports.length) * 100).toFixed(1)
                : "0.0"}
              %
            </p>
          </div>

          <div className="rounded-xl border border-slate-800 bg-[#111e31] p-4">
            <p className="text-xs text-slate-400">Reports in Last 7 Days</p>
            <p className="mt-3 text-2xl font-bold text-blue-400">
              {analytics.lastSevenDays.reduce((sum, day) => sum + day.count, 0)}
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
