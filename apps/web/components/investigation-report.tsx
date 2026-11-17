
"use client";

import { useEffect, useState } from "react";
import {
  Activity,
  AlertCircle,
  AlertTriangle,
  CalendarClock,
  Check,
  ChevronDown,
  ChevronUp,
  Clipboard,
  Code2,
  Download,
  FileText,
  Fingerprint,
  History,
  ListChecks,
  LoaderCircle,
  LockKeyhole,
  RefreshCw,
  ShieldAlert,
  UserRound,
  X,
} from "lucide-react";

import { useAuth } from "@/components/auth-provider";
import { apiRequest } from "@/lib/api";
import {
  canExportReport,
  downloadInvestigationReport,
  type ReportExportFormat,
  type ReportExportStatus,
} from "@/lib/report-exports";
import { getInvestigationReview, submitInvestigationReview, type ReviewDecision } from "@/lib/reviews";

type JsonObject = Record<string, unknown>;

type Props = {
  data: JsonObject;
};

function objectOf(value: unknown): JsonObject | null {
  return value !== null &&
    typeof value === "object" &&
    !Array.isArray(value)
    ? (value as JsonObject)
    : null;
}

function pick(
  obj: JsonObject | null,
  keys: string[]
): unknown {
  if (!obj) return null;

  for (const key of keys) {
    const value = obj[key];
    if (value !== undefined && value !== null) {
      return value;
    }
  }

  return null;
}

function textOf(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "string") return value;

  if (
    typeof value === "number" ||
    typeof value === "boolean"
  ) {
    return String(value);
  }

  return JSON.stringify(value, null, 2);
}

function listOf(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

function formattedDate(value: unknown): string {
  if (typeof value !== "string") return textOf(value);

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

function severityClass(severity: string): string {
  switch (severity.toLowerCase()) {
    case "critical":
      return "border-red-500/40 bg-red-500/15 text-red-300";
    case "high":
      return "border-orange-500/40 bg-orange-500/15 text-orange-300";
    case "medium":
      return "border-amber-500/40 bg-amber-500/15 text-amber-300";
    case "low":
      return "border-emerald-500/40 bg-emerald-500/15 text-emerald-300";
    default:
      return "border-slate-700 bg-slate-800 text-slate-300";
  }
}

function Detail({ value }: { value: unknown }) {
  if (Array.isArray(value)) {
    return (
      <div className="space-y-2">
        {value.map((item, index) => (
          <div
            key={index}
            className="rounded-lg border border-slate-700/60 bg-slate-950/40 p-3"
          >
            <Detail value={item} />
          </div>
        ))}
      </div>
    );
  }

  const object = objectOf(value);

  if (object) {
    return (
      <dl className="space-y-3">
        {Object.entries(object).map(([key, item]) => (
          <div key={key}>
            <dt className="mb-1 text-xs capitalize text-slate-500">
              {key.replaceAll("_", " ")}
            </dt>
            <dd>
              <Detail value={item} />
            </dd>
          </div>
        ))}
      </dl>
    );
  }

  return (
    <p className="whitespace-pre-wrap break-words text-sm leading-6 text-slate-200">
      {textOf(value)}
    </p>
  );
}

function Metric({
  label,
  value,
  icon: Icon,
}: {
  label: string;
  value: string;
  icon: typeof UserRound;
}) {
  return (
    <div className="rounded-xl border border-slate-700/70 bg-[#111e31] p-4">
      <div className="flex items-center gap-2 text-slate-400">
        <Icon size={17} className="text-blue-400" />
        <span className="text-xs">{label}</span>
      </div>
      <p className="mt-3 break-words text-base font-semibold text-white">
        {value}
      </p>
    </div>
  );
}

function isReviewStatus(
  value: unknown
): value is ReportExportStatus {
  return (
    value === "pending" ||
    value === "approved" ||
    value === "rejected" ||
    value === "not_required"
  );
}

function reviewStatusClass(
  status: ReportExportStatus | null
): string {
  switch (status) {
    case "approved":
      return "border-emerald-500/30 bg-emerald-500/10 text-emerald-300";
    case "not_required":
      return "border-blue-500/30 bg-blue-500/10 text-blue-300";
    case "rejected":
      return "border-red-500/30 bg-red-500/10 text-red-300";
    case "pending":
      return "border-amber-500/30 bg-amber-500/10 text-amber-300";
    default:
      return "border-slate-700 bg-slate-800 text-slate-400";
  }
}

export default function InvestigationReport({ data }: Props) {
  const { token } = useAuth();

  const [showRaw, setShowRaw] = useState(false);
  const [showAdditionalFindings, setShowAdditionalFindings] = useState(true);
  const [showRecommendations, setShowRecommendations] = useState(true);
  const [copied, setCopied] = useState<string | null>(null);
  const [selectedEvidence, setSelectedEvidence] =
    useState<number | null>(null);

  const [audit, setAudit] = useState<{
    key: string;
    data: unknown;
  } | null>(null);
  const [auditLoading, setAuditLoading] = useState(false);
  const [auditError, setAuditError] = useState<string | null>(null);
  const [auditOpen, setAuditOpen] = useState(false);

  const [reviewStatus, setReviewStatus] =
    useState<ReportExportStatus | null>(null);
  const [reviewLoading, setReviewLoading] = useState(true);
  const [reviewError, setReviewError] = useState<string | null>(
    null
  );
  const [exporting, setExporting] =
    useState<ReportExportFormat | null>(null);
  const [exportError, setExportError] = useState<string | null>(
    null
  );
  const [exportMessage, setExportMessage] =
    useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [reviewNotes, setReviewNotes] = useState("");
  const [submittingDecision, setSubmittingDecision] =
    useState<ReviewDecision | null>(null);
  const [decisionError, setDecisionError] = useState<string | null>(null);
  const [decisionMessage, setDecisionMessage] = useState<string | null>(null);

  const nestedReport = objectOf(data.report);
  const report =
    objectOf(data.structured_report) ??
    objectOf(nestedReport?.structured_report) ??
    nestedReport ??
    data;

  const rawId =
    pick(data, ["investigation_id", "id"]) ??
    pick(report, ["investigation_id", "id"]);

  const id = typeof rawId === "string" ? rawId : null;
  const overview = objectOf(report.overview);
  const authentication =
    objectOf(report.authentication_details) ??
    objectOf(overview?.authentication_details);
  const eventCounts = objectOf(overview?.event_counts);
  const statistics = objectOf(overview?.authentication_statistics);

  const severity = textOf(
    pick(objectOf(report.risk_assessment), ["severity"]) ??
      pick(report, ["overall_severity", "severity", "risk_level"]) ??
      pick(data, ["overall_severity", "severity", "risk_level"])
  );

  const findings = listOf(
    pick(report, ["findings", "security_findings"]) ??
      pick(data, ["findings", "security_findings"])
  );

  const recommendations = listOf(
    pick(report, ["recommendations", "recommended_actions"]) ??
      pick(data, ["recommendations", "recommended_actions"])
  );

  const reportEvidence = objectOf(report.evidence);
  const evidence = listOf(
    reportEvidence?.supplementary_sources ??
      pick(report, ["evidence_items"]) ??
      pick(data, ["evidence", "evidence_items"])
  );

  const primaryFinding = objectOf(findings[0]);
  const correlatedFinding = findings
    .map(objectOf)
    .find((finding) => finding?.type === "successful_login_after_failures") ??
    primaryFinding;

  const username =
    pick(authentication, ["username"]) ??
    pick(correlatedFinding, ["username", "user", "account"]) ??
    pick(report, ["username", "user"]);

  const failedAttempts =
    pick(authentication, ["failed_attempts"]) ??
    pick(statistics, ["failed_login_attempts"]) ??
    pick(correlatedFinding, ["failed_attempts", "failure_count"]) ??
    pick(report, ["failed_attempts"]) ??
    pick(eventCounts, ["login_failure"]);

  const successfulLoginCount =
    pick(authentication, ["successful_login_count"]) ??
    pick(eventCounts, ["login_success"]);

  const successfulLogin =
    pick(authentication, ["successful_login"]) ??
    (typeof successfulLoginCount === "number"
      ? successfulLoginCount > 0
      : null);

  const timestamp =
    pick(correlatedFinding, [
      "successful_login_timestamp",
      "timestamp",
      "event_time",
    ]) ??
    pick(report, ["successful_login_timestamp"]);

  const successfulLoginDisplay =
    successfulLogin === true
      ? timestamp !== null
        ? formattedDate(timestamp)
        : "Yes"
      : successfulLogin === false
        ? "No"
        : timestamp !== null
          ? formattedDate(timestamp)
          : "—";

  const sourceIp =
    pick(authentication, ["source_ip"]) ??
    pick(correlatedFinding, ["source_ip", "src_ip", "ip_address"]) ??
    pick(report, ["source_ip"]);

  const description = pick(primaryFinding, ["description", "summary"]);

  const summary =
    pick(report, ["executive_summary", "summary", "analysis_summary"]) ??
    pick(data, ["executive_summary", "summary", "analysis_summary"]) ??
    description;

  const title = textOf(
    pick(report, ["title", "report_title"]) ??
      "Security Investigation Report"
  );

  const evidenceIndices = Array.from(
    new Set(
      findings.flatMap((finding) =>
        listOf(
          pick(objectOf(finding), [
            "evidence_event_indices",
            "event_indices",
          ])
        )
      ).filter((index): index is number =>
        typeof index === "number" &&
        Number.isInteger(index) &&
        index >= 0
      )
    )
  ).sort((a, b) => a - b);

  const findingRecommendations = listOf(
    pick(primaryFinding, ["recommended_actions", "recommendations"])
  );

  const visibleRecommendations =
    recommendations.length > 0
      ? recommendations
      : findingRecommendations;

  const sourceEvents = listOf(
    pick(data, ["events", "source_events", "input_events"]) ??
      pick(report, ["events", "source_events", "input_events"])
  );

  const auditKey = `${token ?? ""}:${id ?? ""}`;
  const currentAudit =
    audit?.key === auditKey ? audit.data : null;

  useEffect(() => {
    let cancelled = false;

    if (!id || !token) {
      return;
    }

    async function loadStatus() {
      try {
        const result = await getInvestigationReview(
          id!,
          token!
        );

        if (!cancelled) {
          setReviewStatus(
            isReviewStatus(result.status)
              ? result.status
              : null
          );
          setReviewError(null);
        }
      } catch (error) {
        if (!cancelled) {
          setReviewStatus(null);
          setReviewError(
            error instanceof Error
              ? error.message
              : "Unable to verify review status."
          );
        }
      } finally {
        if (!cancelled) {
          setReviewLoading(false);
        }
      }
    }

    void loadStatus();

    return () => {
      cancelled = true;
    };
  }, [id, token]);

  async function refreshReviewStatus() {
    if (!id || !token || refreshing) return;

    setRefreshing(true);
    setReviewError(null);
    setExportError(null);

    try {
      const result = await getInvestigationReview(
        id,
        token
      );

      setReviewStatus(
        isReviewStatus(result.status)
          ? result.status
          : null
      );
    } catch (error) {
      setReviewStatus(null);
      setReviewError(
        error instanceof Error
          ? error.message
          : "Unable to refresh review status."
      );
    } finally {
      setRefreshing(false);
    }
  }

  async function submitDecision(decision: ReviewDecision) {
    if (!id || !token || submittingDecision || reviewStatus !== "pending") return;

    setSubmittingDecision(decision);
    setDecisionError(null);
    setDecisionMessage(null);
    setExportError(null);

    try {
      const updated = await submitInvestigationReview(
        id,
        token,
        decision,
        reviewNotes.trim()
      );
      if (!isReviewStatus(updated.status)) {
        throw new Error("The review API returned an invalid status.");
      }
      setReviewStatus(updated.status);
      setReviewNotes("");
      setDecisionMessage(
        updated.status === "approved"
          ? "Report approved successfully. Export is now available."
          : updated.status === "rejected"
            ? "Report rejected. Export remains disabled."
            : `Review status updated: ${updated.status}.`
      );
    } catch (error) {
      setDecisionError(
        error instanceof Error ? error.message : "Unable to submit review decision."
      );
    } finally {
      setSubmittingDecision(null);
    }
  }

  async function exportReport(
    format: ReportExportFormat
  ) {
    if (!id || !token || exporting) return;

    setExporting(format);
    setExportError(null);
    setExportMessage(null);

    try {
      const review = await getInvestigationReview(
        id,
        token
      );

      const status = isReviewStatus(review.status)
        ? review.status
        : null;

      setReviewStatus(status);

      if (!canExportReport(status)) {
        throw new Error(
          "This report requires approval before export."
        );
      }

      await downloadInvestigationReport(
        id,
        token,
        format
      );

      setExportMessage(
        `${format.toUpperCase()} export requested successfully.`
      );
    } catch (error) {
      setExportError(
        error instanceof Error
          ? error.message
          : "Report export failed."
      );
    } finally {
      setExporting(null);
    }
  }

  async function copy(
    value: string,
    label: string
  ) {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(label);
    } catch {
      setCopied(null);
    }
  }

  async function openAudit() {
    if (!id || !token) return;

    setAuditOpen(true);

    if (currentAudit !== null) return;

    setAuditLoading(true);
    setAuditError(null);

    try {
      const response = await apiRequest<unknown>(
        `/investigations/${encodeURIComponent(id)}`,
        { method: "GET" },
        token
      );

      setAudit({
        key: auditKey,
        data: response,
      });
    } catch (error) {
      setAuditError(
        error instanceof Error
          ? error.message
          : "Unable to load audit history."
      );
    } finally {
      setAuditLoading(false);
    }
  }

  const selectedReference =
    selectedEvidence !== null
      ? evidenceIndices[selectedEvidence]
      : null;

  const selectedIndex =
    typeof selectedReference === "number" &&
    Number.isInteger(selectedReference)
      ? selectedReference
      : null;

  const selectedEvent =
    selectedIndex !== null &&
    selectedIndex >= 0 &&
    selectedIndex < sourceEvents.length
      ? sourceEvents[selectedIndex]
      : null;

  const details = primaryFinding
    ? Object.entries(primaryFinding).filter(
        ([key]) =>
          ![
            "username",
            "user",
            "account",
            "failed_attempts",
            "failure_count",
            "successful_login_timestamp",
            "timestamp",
            "event_time",
            "source_ip",
            "src_ip",
            "ip_address",
            "severity",
            "description",
            "summary",
            "evidence_event_indices",
            "event_indices",
            "recommended_actions",
            "recommendations",
          ].includes(key)
      )
    : [];

  const exportAllowed =
    canExportReport(reviewStatus) &&
    !reviewLoading &&
    !reviewError;

  return (
    <div className="space-y-6 text-white">
      <section className="rounded-2xl border border-slate-800 bg-[#101827] p-6">
        <div className="flex flex-wrap items-start justify-between gap-5">
          <div className="min-w-0">
            <div className="flex items-center gap-2 text-emerald-400">
              <Check size={19} />
              <span className="text-sm font-semibold">
                Investigation Report
              </span>
            </div>

            <h2 className="mt-3 text-2xl font-bold tracking-tight">
              {title}
            </h2>

            <div className="mt-3 flex flex-wrap items-center gap-2">
              <span className="break-all font-mono text-xs text-slate-400">
                ID: {id ?? "Unavailable"}
              </span>

              {id && (
                <button
                  type="button"
                  onClick={() => void copy(id, "id")}
                  title="Copy investigation ID"
                  className="rounded-md p-1 text-slate-400 transition hover:bg-slate-800 hover:text-white"
                >
                  {copied === "id" ? (
                    <Check size={15} />
                  ) : (
                    <Clipboard size={15} />
                  )}
                </button>
              )}
            </div>
          </div>

          <span
            className={`inline-flex items-center gap-2 rounded-xl border px-4 py-2 text-sm font-semibold capitalize ${severityClass(
              severity
            )}`}
          >
            <ShieldAlert size={18} />
            {severity} Severity
          </span>
        </div>

        <div className="mt-7 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <Metric
            label="Username"
            value={textOf(username)}
            icon={UserRound}
          />
          <Metric
            label="Failed Attempts"
            value={textOf(failedAttempts)}
            icon={AlertTriangle}
          />
          <Metric
            label="Successful Login"
            value={successfulLoginDisplay}
            icon={CalendarClock}
          />
          <Metric
            label="Source IP"
            value={textOf(sourceIp)}
            icon={Fingerprint}
          />
        </div>

        <div className="mt-6 rounded-xl border border-slate-700/70 bg-[#080d19] p-4 print:hidden">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              {exportAllowed ? (
                <Check
                  size={19}
                  className="text-emerald-400"
                />
              ) : (
                <LockKeyhole
                  size={19}
                  className="text-amber-400"
                />
              )}

              <div>
                <p className="text-sm font-semibold text-white">
                  Secure Report Export
                </p>
                <p className="mt-1 text-xs text-slate-400">
                  Authorized PDF and JSON downloads
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <span
                className={`rounded-full border px-3 py-1 text-xs font-medium capitalize ${reviewStatusClass(
                  reviewStatus
                )}`}
              >
                {reviewLoading
                  ? "Checking..."
                  : reviewStatus
                    ? reviewStatus.replaceAll("_", " ")
                    : "Unavailable"}
              </span>

              <button
                type="button"
                onClick={() =>
                  void refreshReviewStatus()
                }
                disabled={
                  refreshing ||
                  exporting !== null ||
                  !id ||
                  !token
                }
                title="Refresh review status"
                aria-label="Refresh review status"
                className="rounded-lg border border-slate-700 p-2 text-slate-300 transition hover:bg-slate-800 disabled:opacity-50"
              >
                <RefreshCw
                  size={16}
                  className={
                    refreshing ? "animate-spin" : ""
                  }
                />
              </button>
            </div>
          </div>

          <div className="mt-4 flex flex-wrap gap-3">
            <button
              type="button"
              onClick={() => void exportReport("pdf")}
              disabled={
                !exportAllowed ||
                exporting !== null ||
                !id ||
                !token
              }
              className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {exporting === "pdf" ? (
                <LoaderCircle
                  size={17}
                  className="animate-spin"
                />
              ) : (
                <Download size={17} />
              )}
              Download PDF
            </button>

            <button
              type="button"
              onClick={() => void exportReport("json")}
              disabled={
                !exportAllowed ||
                exporting !== null ||
                !id ||
                !token
              }
              className="inline-flex items-center gap-2 rounded-lg border border-slate-700 px-4 py-2.5 text-sm font-medium text-slate-200 transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {exporting === "json" ? (
                <LoaderCircle
                  size={17}
                  className="animate-spin"
                />
              ) : (
                <Download size={17} />
              )}
              Download JSON
            </button>

            {id && token && (
              <button
                type="button"
                onClick={() => void openAudit()}
                className="inline-flex items-center gap-2 rounded-lg border border-blue-500/30 bg-blue-500/10 px-4 py-2.5 text-sm text-blue-300 transition hover:bg-blue-500/20"
              >
                <History size={17} />
                View Audit History
              </button>
            )}
          </div>

          {!exportAllowed && !reviewLoading && (
            <p className="mt-3 flex items-center gap-2 text-xs text-amber-300">
              <LockKeyhole size={14} />
              {reviewStatus === "pending"
                ? "Analyst approval is required before exporting."
                : reviewStatus === "rejected"
                  ? "This report was rejected and cannot be exported."
                  : "Export authorization could not be verified."}
            </p>
          )}

          {reviewError && (
            <p
              role="alert"
              className="mt-3 flex items-center gap-2 text-sm text-red-300"
            >
              <AlertCircle size={16} />
              {reviewError}
            </p>
          )}

          {exportError && (
            <p
              role="alert"
              className="mt-3 flex items-center gap-2 text-sm text-red-300"
            >
              <AlertCircle size={16} />
              {exportError}
            </p>
          )}

          {exportMessage && (
            <p
              role="status"
              className="mt-3 text-sm text-emerald-300"
            >
              {exportMessage}
            </p>
          )}
        </div>
      </section>

      {id && token && (
        <section className="rounded-2xl border border-slate-800 bg-[#101827] p-6 print:hidden">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h3 className="text-lg font-semibold text-white">Human Analyst Review</h3>
            <span className={`rounded-full border px-3 py-1 text-xs font-semibold capitalize ${reviewStatusClass(reviewStatus)}`}>
              {reviewLoading ? "Checking..." : reviewStatus?.replaceAll("_", " ") ?? "Unavailable"}
            </span>
          </div>
          {reviewStatus === "pending" && !reviewLoading && !reviewError ? (
            <div className="mt-4 space-y-4">
              <p className="text-sm text-slate-400">
                Review the findings and evidence before approving or rejecting this report.
                Your decision is recorded by the authenticated review service.
              </p>
              <div>
                <label htmlFor="analyst-review-notes" className="mb-2 block text-sm font-medium text-slate-300">
                  Analyst notes (optional)
                </label>
                <textarea
                  id="analyst-review-notes"
                  value={reviewNotes}
                  onChange={(event) => setReviewNotes(event.target.value)}
                  disabled={submittingDecision !== null}
                  rows={3}
                  maxLength={2000}
                  placeholder="Record the rationale for your review decision..."
                  className="w-full resize-y rounded-xl border border-slate-700 bg-[#080d19] p-3 text-sm text-slate-200 outline-none focus:border-blue-500 disabled:opacity-50"
                />
              </div>
              <div className="flex flex-wrap gap-3">
                <button
                  type="button"
                  onClick={() => void submitDecision("approved")}
                  disabled={submittingDecision !== null}
                  className="inline-flex items-center gap-2 rounded-lg bg-emerald-700 px-4 py-2.5 text-sm font-semibold text-white hover:bg-emerald-600 disabled:opacity-50"
                >
                  {submittingDecision === "approved" ? <LoaderCircle size={17} className="animate-spin" /> : <Check size={17} />}
                  Approve Report
                </button>
                <button
                  type="button"
                  onClick={() => void submitDecision("rejected")}
                  disabled={submittingDecision !== null}
                  className="inline-flex items-center gap-2 rounded-lg border border-red-500/50 bg-red-500/10 px-4 py-2.5 text-sm font-semibold text-red-300 hover:bg-red-500/20 disabled:opacity-50"
                >
                  {submittingDecision === "rejected" ? <LoaderCircle size={17} className="animate-spin" /> : <X size={17} />}
                  Reject Report
                </button>
              </div>
            </div>
          ) : reviewStatus === "approved" ? (
            <p className="mt-3 text-sm text-emerald-300">This report has been approved. Authorized exports are available.</p>
          ) : reviewStatus === "rejected" ? (
            <p className="mt-3 text-sm text-red-300">This report has been rejected. Exports are blocked.</p>
          ) : reviewStatus === "not_required" ? (
            <p className="mt-3 text-sm text-blue-300">This report does not require analyst approval.</p>
          ) : (
            <p className="mt-3 text-sm text-slate-400">Review status is being checked or could not be verified. No decision can be submitted yet.</p>
          )}
          {decisionError && <p role="alert" className="mt-3 text-sm text-red-300">{decisionError}</p>}
          {decisionMessage && <p role="status" className="mt-3 text-sm text-emerald-300">{decisionMessage}</p>}
        </section>
      )}

      {summary !== null && (
        <section className="rounded-2xl border border-orange-500/25 bg-orange-500/[0.06] p-6">
          <div className="mb-3 flex items-center gap-3">
            <FileText
              size={20}
              className="text-orange-400"
            />
            <h3 className="text-lg font-semibold">
              Executive Summary
            </h3>
          </div>
          <Detail value={summary} />
        </section>
      )}

      <div className="grid gap-6 xl:grid-cols-2">
        <section className="rounded-2xl border border-slate-800 bg-[#101827] p-6">
          <div className="mb-5 flex items-center gap-3">
            <FileText
              size={21}
              className="text-blue-400"
            />
            <h3 className="text-lg font-semibold">
              Investigation Details
            </h3>
          </div>

          <div className="divide-y divide-slate-800">
            {(
              [
                ["Username", username],
                ["Failed Attempts", failedAttempts],
                [
                  "Successful Login",
                  successfulLoginDisplay,
                ],
                ["Source IP", sourceIp],
                ["Severity", severity],
              ] as [string, unknown][]
            ).map(([label, value]) => (
              <div
                key={label}
                className="grid grid-cols-2 gap-3 py-3 text-sm"
              >
                <span className="text-slate-400">
                  {label}
                </span>
                <span className="break-words font-medium text-slate-200">
                  {textOf(value)}
                </span>
              </div>
            ))}

            {details.map(([key, value]) => (
              <div
                key={key}
                className="grid grid-cols-2 gap-3 py-3 text-sm"
              >
                <span className="capitalize text-slate-400">
                  {key.replaceAll("_", " ")}
                </span>
                <Detail value={value} />
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-2xl border border-slate-800 bg-[#101827] p-6">
          <div className="mb-5 flex items-center gap-3">
            <Fingerprint
              size={21}
              className="text-blue-400"
            />
            <h3 className="text-lg font-semibold">
              Evidence References
            </h3>
          </div>

          {evidenceIndices.length > 0 ? (
            <>
              <p className="mb-5 text-sm text-slate-400">
                Select an event index to inspect its
                available evidence.
              </p>

              <div className="flex flex-wrap gap-3">
                {evidenceIndices.map(
                  (reference, index) => (
                    <button
                      key={index}
                      type="button"
                      onClick={() =>
                        setSelectedEvidence(index)
                      }
                      className={`flex h-11 min-w-11 items-center justify-center rounded-xl border px-3 font-mono text-sm font-semibold transition ${
                        selectedEvidence === index
                          ? "border-blue-400 bg-blue-600 text-white"
                          : "border-blue-500/30 bg-blue-500/10 text-blue-300 hover:bg-blue-500/25"
                      }`}
                    >
                      {textOf(reference)}
                    </button>
                  )
                )}
              </div>

              {selectedEvidence !== null && (
                <div className="mt-6 rounded-xl border border-blue-500/25 bg-[#0b1424] p-5">
                  <div className="flex items-center justify-between gap-3">
                    <h4 className="font-semibold">
                      Event Reference{" "}
                      {textOf(selectedReference)}
                    </h4>

                    <button
                      type="button"
                      onClick={() =>
                        setSelectedEvidence(null)
                      }
                      aria-label="Close evidence details"
                      className="rounded-lg p-1 text-slate-400 hover:bg-slate-800 hover:text-white"
                    >
                      <X size={18} />
                    </button>
                  </div>

                  <div className="mt-4">
                    {selectedEvent !== null ? (
                      <Detail value={selectedEvent} />
                    ) : (
                      <p className="text-sm leading-6 text-slate-400">
                        This finding references event index{" "}
                        {textOf(selectedReference)}, but the
                        original event payload is not included
                        in this report response. Detailed
                        evidence cannot be displayed yet.
                      </p>
                    )}
                  </div>
                </div>
              )}
            </>
          ) : evidence.length > 0 ? (
            <div className="space-y-3">
              {evidence.map((item, index) => (
                <details
                  key={index}
                  className="rounded-xl border border-slate-800 bg-slate-900/40"
                >
                  <summary className="cursor-pointer p-4 text-sm font-medium text-blue-300">
                    Evidence Item {index + 1}
                  </summary>
                  <div className="border-t border-slate-800 p-4">
                    <Detail value={item} />
                  </div>
                </details>
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-500">
              No separately indexed evidence was provided.
            </p>
          )}
        </section>
      </div>

      {findings.length > 1 && (
        <section className="rounded-2xl border border-slate-800 bg-[#101827] p-6">
          <button
            type="button"
            onClick={() => setShowAdditionalFindings((value) => !value)}
            aria-expanded={showAdditionalFindings}
            aria-controls="additional-security-findings-content"
            className={`flex w-full items-center justify-between gap-3 text-left ${showAdditionalFindings ? "mb-5" : ""}`}
          >
            <span className="flex items-center gap-3">
              <ShieldAlert size={21} className="text-orange-400" />
              <span className="text-lg font-semibold">Additional Security Findings</span>
            </span>
            {showAdditionalFindings ? (
              <ChevronUp size={20} className="shrink-0 text-slate-400" />
            ) : (
              <ChevronDown size={20} className="shrink-0 text-slate-400" />
            )}
          </button>

          {showAdditionalFindings && (
            <div id="additional-security-findings-content" className="grid gap-4 lg:grid-cols-2">
              {findings.slice(1).map((finding, index) => (
                <div
                  key={index}
                  className="rounded-xl border border-slate-800 bg-slate-900/40 p-5"
                >
                  <h4 className="mb-3 font-semibold">Finding {index + 2}</h4>
                  <Detail value={finding} />
                </div>
              ))}
            </div>
          )}
        </section>
      )}

      {visibleRecommendations.length > 0 && (
        <section className="rounded-2xl border border-slate-800 bg-[#101827] p-6">
          <button
            type="button"
            onClick={() => setShowRecommendations((value) => !value)}
            aria-expanded={showRecommendations}
            aria-controls="recommended-actions-content"
            className={`flex w-full items-center justify-between gap-3 text-left ${showRecommendations ? "mb-5" : ""}`}
          >
            <span className="flex items-center gap-3">
              <ListChecks size={22} className="text-blue-400" />
              <span className="text-lg font-semibold">Recommended Actions</span>
            </span>
            {showRecommendations ? (
              <ChevronUp size={20} className="shrink-0 text-slate-400" />
            ) : (
              <ChevronDown size={20} className="shrink-0 text-slate-400" />
            )}
          </button>

          {showRecommendations && (
            <div id="recommended-actions-content" className="grid gap-3 lg:grid-cols-2">
              {visibleRecommendations.map((action, index) => (
                <div
                  key={index}
                  className="flex items-start gap-3 rounded-xl border border-slate-700/70 bg-[#111e31] p-4"
                >
                  <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-blue-500/30 bg-blue-600/20 text-sm font-semibold text-blue-300">
                    {index + 1}
                  </span>
                  <div className="min-w-0 pt-1">
                    <Detail value={action} />
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      )}

      {auditOpen && (
        <section className="rounded-2xl border border-slate-800 bg-[#101827] p-6 print:hidden">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <Activity
                size={21}
                className="text-purple-400"
              />
              <h3 className="text-lg font-semibold">
                Investigation Activity & Audit History
              </h3>
            </div>

            <button
              type="button"
              onClick={() => setAuditOpen(false)}
              aria-label="Close audit history"
              className="rounded-lg p-2 text-slate-400 hover:bg-slate-800"
            >
              <X size={18} />
            </button>
          </div>

          {auditLoading ? (
            <p className="mt-5 text-sm text-slate-400">
              Loading audit history...
            </p>
          ) : auditError ? (
            <p className="mt-5 text-sm text-red-400">
              {auditError}
            </p>
          ) : currentAudit !== null ? (
            <div className="mt-5 max-h-[550px] overflow-auto rounded-xl border border-slate-800 bg-[#080d19] p-5">
              <Detail value={currentAudit} />
            </div>
          ) : null}
        </section>
      )}

      <section className="rounded-2xl border border-slate-800 bg-[#101827] p-5 print:hidden">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <button
            type="button"
            onClick={() =>
              setShowRaw((value) => !value)
            }
            aria-expanded={showRaw}
            className="flex items-center gap-3 text-left"
          >
            <Code2
              size={20}
              className="text-blue-400"
            />
            <span className="font-semibold">
              Raw Response Data
            </span>

            {showRaw ? (
              <ChevronUp size={17} />
            ) : (
              <ChevronDown size={17} />
            )}
          </button>

          <button
            type="button"
            onClick={() =>
              void copy(
                JSON.stringify(data, null, 2),
                "json"
              )
            }
            className="flex items-center gap-2 rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-300 hover:bg-slate-800"
          >
            <Clipboard size={16} />
            {copied === "json"
              ? "Copied"
              : "Copy JSON"}
          </button>
        </div>

        {showRaw && (
          <pre className="mt-5 max-h-[600px] overflow-auto rounded-xl border border-slate-800 bg-[#080d19] p-5 font-mono text-xs leading-6 text-slate-300">
            {JSON.stringify(data, null, 2)}
          </pre>
        )}
      </section>
    </div>
  );
}
