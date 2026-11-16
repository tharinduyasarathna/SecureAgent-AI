
"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  Activity,
  AlertCircle,
  ArrowLeft,
  ArrowRight,
  CalendarClock,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Clock3,
  FileSearch,
  History,
  LoaderCircle,
  RefreshCw,
} from "lucide-react";

import Sidebar from "@/components/sidebar";
import ProtectedRoute from "@/components/protected-route";
import { useAuth } from "@/components/auth-provider";
import { apiRequest } from "@/lib/api";
import {
  getInvestigationReports,
  type InvestigationSummary,
} from "@/lib/investigations";

type JsonObject = Record<string, unknown>;

type AuditEvent = {
  id: string;
  timestamp: string | null;
  agent: string;
  action: string;
  status: string | null;
  details: JsonObject;
};

function asObject(value: unknown): JsonObject | null {
  if (
    value !== null &&
    typeof value === "object" &&
    !Array.isArray(value)
  ) {
    return value as JsonObject;
  }
  return null;
}

function field(
  object: JsonObject | null,
  keys: string[]
): unknown {
  if (!object) return null;

  for (const key of keys) {
    if (object[key] !== undefined && object[key] !== null) {
      return object[key];
    }
  }
  return null;
}

function display(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return JSON.stringify(value);
}

function dateLabel(value: unknown): string {
  if (typeof value !== "string") return display(value);

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;

  return date.toLocaleString("en-IE", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    timeZone: "UTC",
    timeZoneName: "short",
  });
}

function severityClass(severity: string): string {
  switch (severity.toLowerCase()) {
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

function normalizeAudit(response: unknown): AuditEvent[] {
  const root = asObject(response);

  const nested = asObject(
    field(root, ["investigation", "audit_history", "data"])
  );

  const candidates = [
    field(root, ["audit_events", "events", "history", "audit_logs"]),
    field(nested, ["audit_events", "events", "history", "audit_logs"]),
  ];

  const rawEvents = candidates.find(Array.isArray);

  if (!Array.isArray(rawEvents)) return [];

  return rawEvents
    .map((item, index): AuditEvent | null => {
      const event = asObject(item);
      if (!event) return null;

      const timestamp = field(event, [
        "created_at",
        "timestamp",
        "event_time",
        "time",
      ]);

      return {
        id: display(
          field(event, ["id", "event_id", "audit_id"]) ?? index
        ),
        timestamp:
          typeof timestamp === "string" ? timestamp : null,
        agent: display(
          field(event, [
            "agent_name",
            "agent",
            "actor",
            "component",
            "specialist",
          ]) ?? "System"
        ),
        action: display(
          field(event, [
            "action",
            "event_type",
            "operation",
            "message",
            "step",
          ]) ?? "Audit event"
        ),
        status:
          field(event, ["status", "result", "outcome"]) === null
            ? null
            : display(field(event, ["status", "result", "outcome"])),
        details: event,
      };
    })
    .filter((event): event is AuditEvent => event !== null)
    .sort((a, b) => {
      if (!a.timestamp || !b.timestamp) return 0;

      const aTime = Date.parse(a.timestamp);
      const bTime = Date.parse(b.timestamp);

      if (Number.isNaN(aTime) || Number.isNaN(bTime)) return 0;
      return aTime - bTime;
    });
}

function statusIcon(status: string | null) {
  const normalized = status?.toLowerCase() ?? "";

  if (
    normalized === "failed" ||
    normalized === "error" ||
    normalized === "denied"
  ) {
    return <AlertCircle size={18} className="text-red-400" />;
  }

  if (
    normalized === "success" ||
    normalized === "completed" ||
    normalized === "ok"
  ) {
    return (
      <CheckCircle2 size={18} className="text-emerald-400" />
    );
  }

  return <Activity size={18} className="text-blue-400" />;
}

function AuditTimeline({ events }: { events: AuditEvent[] }) {
  const [expanded, setExpanded] = useState<string | null>(null);

  if (events.length === 0) {
    return (
      <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-6 text-sm text-slate-400">
        No audit events were found in the returned response.
      </div>
    );
  }

  return (
    <div className="relative space-y-4">
      {events.map((event, index) => {
        const key = `${event.id}-${index}`;
        const open = expanded === key;

        return (
          <div
            key={key}
            className="relative rounded-xl border border-slate-800 bg-[#111e31] p-5"
          >
            <div className="flex items-start gap-4">
              <div className="rounded-lg border border-slate-700 bg-slate-900 p-2">
                {statusIcon(event.status)}
              </div>

              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-xs font-medium uppercase tracking-wide text-blue-400">
                      {event.agent}
                    </p>

                    <h4 className="mt-1 break-words font-semibold text-white">
                      {event.action}
                    </h4>
                  </div>

                  {event.status && (
                    <span className="rounded-lg border border-slate-700 px-3 py-1 text-xs capitalize text-slate-300">
                      {event.status}
                    </span>
                  )}
                </div>

                <div className="mt-3 flex items-center gap-2 text-xs text-slate-400">
                  <Clock3 size={14} />
                  {event.timestamp
                    ? dateLabel(event.timestamp)
                    : "Timestamp unavailable"}
                </div>

                <button
                  type="button"
                  onClick={() => setExpanded(open ? null : key)}
                  aria-expanded={open}
                  className="mt-4 inline-flex items-center gap-2 text-sm text-blue-400 hover:text-blue-300"
                >
                  {open ? "Hide Event Details" : "View Event Details"}
                  {open ? (
                    <ChevronUp size={16} />
                  ) : (
                    <ChevronDown size={16} />
                  )}
                </button>

                {open && (
                  <pre className="mt-4 max-h-[400px] overflow-auto rounded-xl border border-slate-800 bg-[#080d19] p-4 font-mono text-xs leading-6 text-slate-300">
                    {JSON.stringify(event.details, null, 2)}
                  </pre>
                )}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function HistoryWorkspace() {
  const { token } = useAuth();

  const [reports, setReports] = useState<InvestigationSummary[]>([]);
  const [loadedToken, setLoadedToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [audit, setAudit] = useState<{
    token: string;
    id: string;
    response: unknown;
  } | null>(null);
  const [auditLoading, setAuditLoading] = useState(false);
  const [auditError, setAuditError] = useState<string | null>(null);

  const loadReports = useCallback(async () => {
    if (!token) return;

    setLoading(true);
    setError(null);

    try {
      const all: InvestigationSummary[] = [];
      let offset = 0;

      while (true) {
        const response = await getInvestigationReports(
          token,
          100,
          offset
        );

        all.push(...response.items);
        offset += response.items.length;

        if (
          response.items.length === 0 ||
          offset >= response.total
        ) {
          break;
        }
      }

      all.sort(
        (a, b) =>
          Date.parse(b.created_at) - Date.parse(a.created_at)
      );

      setReports(all);
      setLoadedToken(token);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to load investigation history."
      );
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    if (!token) return;

    let cancelled = false;

    async function initialLoad() {
      try {
        const all: InvestigationSummary[] = [];
        let offset = 0;

        while (!cancelled) {
          const response = await getInvestigationReports(
            token as string,
            100,
            offset
          );

          if (cancelled) return;

          all.push(...response.items);
          offset += response.items.length;

          if (
            response.items.length === 0 ||
            offset >= response.total
          ) {
            break;
          }
        }

        if (cancelled) return;

        all.sort(
          (a, b) =>
            Date.parse(b.created_at) - Date.parse(a.created_at)
        );

        setReports(all);
        setLoadedToken(token as string);
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error
              ? err.message
              : "Unable to load investigation history."
          );
        }
      }
    }

    void initialLoad();

    return () => {
      cancelled = true;
    };
  }, [token]);

  const currentReports =
    loadedToken === token ? reports : [];

  const currentAudit =
    audit?.token === token && audit.id === selectedId
      ? audit.response
      : null;

  const events = normalizeAudit(currentAudit);

  async function selectInvestigation(id: string) {
    setSelectedId(id);
    setAuditError(null);
    setAuditLoading(true);

    if (!token) {
      setAuditLoading(false);
      return;
    }

    try {
      const response = await apiRequest<unknown>(
        `/investigations/${encodeURIComponent(id)}`,
        { method: "GET" },
        token
      );

      setAudit({
        token,
        id,
        response,
      });
    } catch (err) {
      setAuditError(
        err instanceof Error
          ? err.message
          : "Unable to retrieve audit events."
      );
    } finally {
      setAuditLoading(false);
    }
  }

  const selectedReport = currentReports.find(
    (report) => report.investigation_id === selectedId
  );

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
              <div className="rounded-xl bg-purple-500/10 p-3 text-purple-400">
                <History size={26} />
              </div>

              <div>
                <h1 className="text-3xl font-bold tracking-tight">
                  Investigation History
                </h1>
                <p className="mt-2 text-sm text-slate-400">
                  Explore saved investigations and audited agent activity.
                </p>
              </div>
            </div>

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
          </div>
        </header>

        {error && (
          <div
            role="alert"
            className="mt-6 rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-300"
          >
            {error}
          </div>
        )}

        <div className="mt-7 grid gap-6 xl:grid-cols-[340px_minmax(0,1fr)]">
          <section className="rounded-2xl border border-slate-800 bg-[#101827] p-5">
            <div className="mb-5 flex items-center justify-between">
              <h2 className="font-semibold">
                Saved Investigations
              </h2>
              <span className="text-xs text-slate-500">
                {currentReports.length} total
              </span>
            </div>

            {loading && currentReports.length === 0 ? (
              <div className="flex items-center gap-3 text-sm text-slate-400">
                <LoaderCircle size={18} className="animate-spin" />
                Loading investigations...
              </div>
            ) : currentReports.length === 0 ? (
              <div className="py-10 text-center">
                <FileSearch
                  size={30}
                  className="mx-auto text-slate-600"
                />
                <p className="mt-4 text-sm text-slate-400">
                  No saved investigations yet.
                </p>
                <Link
                  href="/investigations"
                  className="mt-4 inline-flex items-center gap-2 text-sm text-blue-400"
                >
                  Start Investigation
                  <ArrowRight size={16} />
                </Link>
              </div>
            ) : (
              <div className="max-h-[720px] space-y-3 overflow-y-auto pr-1">
                {currentReports.map((report) => {
                  const active =
                    selectedId === report.investigation_id;

                  return (
                    <button
                      key={report.investigation_id}
                      type="button"
                      onClick={() =>
                        void selectInvestigation(
                          report.investigation_id
                        )
                      }
                      className={`w-full rounded-xl border p-4 text-left transition ${
                        active
                          ? "border-blue-500/50 bg-blue-500/10"
                          : "border-slate-800 bg-[#111e31] hover:border-slate-600"
                      }`}
                    >
                      <div className="flex items-center justify-between gap-3">
                        <span
                          className={`rounded-md border px-2 py-1 text-xs font-semibold capitalize ${severityClass(
                            report.severity
                          )}`}
                        >
                          {report.severity}
                        </span>

                        <ArrowRight
                          size={15}
                          className={
                            active
                              ? "text-blue-400"
                              : "text-slate-500"
                          }
                        />
                      </div>

                      <h3 className="mt-3 line-clamp-2 text-sm font-semibold">
                        {report.title || "Security Investigation"}
                      </h3>

                      <p className="mt-2 truncate font-mono text-xs text-slate-500">
                        {report.investigation_id}
                      </p>

                      <div className="mt-3 flex items-center gap-2 text-xs text-slate-400">
                        <CalendarClock size={14} />
                        {dateLabel(report.created_at)}
                      </div>
                    </button>
                  );
                })}
              </div>
            )}
          </section>

          <section className="min-w-0 rounded-2xl border border-slate-800 bg-[#101827] p-6">
            {!selectedId ? (
              <div className="flex min-h-[400px] flex-col items-center justify-center text-center">
                <History size={42} className="text-slate-600" />

                <h2 className="mt-5 text-xl font-semibold">
                  Select an Investigation
                </h2>

                <p className="mt-3 max-w-md text-sm leading-6 text-slate-400">
                  Choose an investigation from the list to inspect
                  its execution history and agent audit records.
                </p>
              </div>
            ) : (
              <>
                <div className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-800 pb-5">
                  <div>
                    <h2 className="text-xl font-semibold">
                      Agent Execution Timeline
                    </h2>

                    <p className="mt-2 break-all font-mono text-xs text-slate-500">
                      {selectedId}
                    </p>
                  </div>

                  {selectedReport && (
                    <Link
                      href={`/reports/${encodeURIComponent(
                        selectedReport.investigation_id
                      )}`}
                      className="inline-flex items-center gap-2 rounded-lg border border-blue-500/30 bg-blue-500/10 px-4 py-2 text-sm text-blue-300 hover:bg-blue-500/20"
                    >
                      <FileTextIcon />
                      Open Report
                    </Link>
                  )}
                </div>

                <div className="mt-6">
                  {auditLoading ? (
                    <div className="flex items-center gap-3 text-sm text-slate-400">
                      <LoaderCircle
                        size={20}
                        className="animate-spin"
                      />
                      Loading agent audit history...
                    </div>
                  ) : auditError ? (
                    <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-300">
                      {auditError}
                    </div>
                  ) : (
                    <>
                      <div className="mb-6 flex items-center gap-3 rounded-xl border border-slate-800 bg-[#111e31] p-4">
                        <Activity
                          size={20}
                          className="text-blue-400"
                        />

                        <div>
                          <p className="text-xs text-slate-400">
                            Recorded Audit Events
                          </p>
                          <p className="mt-1 text-xl font-semibold">
                            {events.length}
                          </p>
                        </div>
                      </div>

                      <AuditTimeline
                        key={selectedId}
                        events={events}
                      />
                    </>
                  )}
                </div>
              </>
            )}
          </section>
        </div>
      </main>
    </div>
  );
}

function FileTextIcon() {
  return <FileSearch size={16} />;
}

export default function HistoryPage() {
  return (
    <ProtectedRoute>
      <HistoryWorkspace />
    </ProtectedRoute>
  );
}
