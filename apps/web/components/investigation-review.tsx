
"use client";

import {
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";

import {
  AlertCircle,
  CheckCircle2,
  Clock3,
  FileCheck2,
  LoaderCircle,
  RefreshCw,
  ShieldCheck,
  XCircle,
  X,
} from "lucide-react";

import {
  getInvestigationReview,
  getInvestigationReviewHistory,
  submitInvestigationReview,
  type InvestigationReview,
  type InvestigationReviewEvent,
  type ReviewDecision,
  type ReviewStatus,
} from "@/lib/reviews";

interface InvestigationReviewProps {
  investigationId: string;
  token: string;
}

interface ReviewState {
  review: InvestigationReview;
  history: InvestigationReviewEvent[];
}

const statusConfig: Record<
  ReviewStatus,
  { label: string; className: string }
> = {
  pending: {
    label: "Pending Review",
    className:
      "border-amber-500/30 bg-amber-500/10 text-amber-300",
  },
  approved: {
    label: "Approved",
    className:
      "border-emerald-500/30 bg-emerald-500/10 text-emerald-300",
  },
  rejected: {
    label: "Rejected",
    className:
      "border-red-500/30 bg-red-500/10 text-red-300",
  },
  not_required: {
    label: "Review Not Required",
    className:
      "border-slate-600 bg-slate-700/30 text-slate-300",
  },
};

function formatDate(value: string | null): string {
  if (!value) return "Not available";

  const date = new Date(value);

  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleString();
}

function StatusIcon({ status }: { status: ReviewStatus }) {
  if (status === "approved")
    return <CheckCircle2 size={18} />;

  if (status === "rejected")
    return <XCircle size={18} />;

  if (status === "pending")
    return <Clock3 size={18} />;

  return <ShieldCheck size={18} />;
}

export default function InvestigationReviewPanel({
  investigationId,
  token,
}: InvestigationReviewProps) {
  const [state, setState] = useState<ReviewState | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [notes, setNotes] = useState("");
  const [confirmDecision, setConfirmDecision] =
    useState<ReviewDecision | null>(null);
  const [submitting, setSubmitting] =
    useState<ReviewDecision | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [actionError, setActionError] =
    useState<string | null>(null);
  const [actionMessage, setActionMessage] =
    useState<string | null>(null);

  const mountedRef = useRef(false);
  const submittingRef = useRef(false);

  const loadReview = useCallback(async () => {
    const [review, history] = await Promise.all([
      getInvestigationReview(investigationId, token),
      getInvestigationReviewHistory(investigationId, token),
    ]);

    return { review, history };
  }, [investigationId, token]);

  useEffect(() => {
    mountedRef.current = true;
    let cancelled = false;

    async function initialize() {
      try {
        const result = await loadReview();

        if (!cancelled) {
          setState(result);
          setLoadError(null);
        }
      } catch (error) {
        if (!cancelled) {
          setLoadError(
            error instanceof Error
              ? error.message
              : "Unable to load review information."
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void initialize();

    return () => {
      cancelled = true;
      mountedRef.current = false;
    };
  }, [loadReview]);

  useEffect(() => {
    if (!confirmDecision) return;

    function handleEscape(event: KeyboardEvent) {
      if (event.key === "Escape" && !submittingRef.current) {
        setConfirmDecision(null);
      }
    }

    window.addEventListener("keydown", handleEscape);

    return () => {
      window.removeEventListener("keydown", handleEscape);
    };
  }, [confirmDecision]);

  async function refreshReview() {
    if (submittingRef.current || refreshing) return;

    setRefreshing(true);
    setActionError(null);

    try {
      const result = await loadReview();

      if (mountedRef.current) {
        setState(result);
        setLoadError(null);
      }
    } catch (error) {
      if (mountedRef.current) {
        setActionError(
          error instanceof Error
            ? error.message
            : "Unable to refresh review."
        );
      }
    } finally {
      if (mountedRef.current) setRefreshing(false);
    }
  }

  function requestDecision(decision: ReviewDecision) {
    if (
      submittingRef.current ||
      refreshing ||
      state?.review.status !== "pending"
    ) {
      return;
    }

    if (!notes.trim()) {
      setActionError(
        "Please enter analyst review notes before continuing."
      );
      return;
    }

    setActionError(null);
    setActionMessage(null);
    setConfirmDecision(decision);
  }

  async function confirmReview() {
    const decision = confirmDecision;

    if (
      !decision ||
      submittingRef.current ||
      state?.review.status !== "pending"
    ) {
      return;
    }

    const trimmedNotes = notes.trim();

    if (!trimmedNotes || trimmedNotes.length > 2000) {
      setActionError("Invalid review notes.");
      setConfirmDecision(null);
      return;
    }

    submittingRef.current = true;
    setSubmitting(decision);
    setActionError(null);

    try {
      const updated = await submitInvestigationReview(
        investigationId,
        token,
        decision,
        trimmedNotes
      );

      if (!mountedRef.current) return;

      setState((previous) =>
        previous
          ? { ...previous, review: updated }
          : previous
      );

      setConfirmDecision(null);
      setNotes("");

      setActionMessage(
        decision === "approved"
          ? "Investigation report approved successfully."
          : "Investigation report rejected successfully."
      );

      // Refresh history independently after approval.
      void getInvestigationReviewHistory(
        investigationId,
        token
      )
        .then((history) => {
          if (!mountedRef.current) return;

          setState((previous) =>
            previous
              ? { ...previous, history }
              : previous
          );
        })
        .catch(() => {
          if (mountedRef.current) {
            setActionMessage(
              "Decision saved. History refresh is unavailable."
            );
          }
        });
    } catch (error) {
      if (mountedRef.current) {
        setConfirmDecision(null);
        setActionError(
          error instanceof Error
            ? error.message
            : "Unable to submit review."
        );

        // Check whether the server committed the decision
        // before a network error occurred.
        void refreshReview();
      }
    } finally {
      submittingRef.current = false;

      if (mountedRef.current) {
        setSubmitting(null);
      }
    }
  }

  if (loading) {
    return (
      <section className="mt-8 rounded-2xl border border-slate-800 bg-[#101827] p-6">
        <div className="flex items-center gap-3 text-slate-300">
          <LoaderCircle
            size={20}
            className="animate-spin text-blue-400"
          />
          Loading human review...
        </div>
      </section>
    );
  }

  if (loadError || !state) {
    return (
      <section
        role="alert"
        className="mt-8 rounded-2xl border border-red-500/30 bg-red-500/10 p-6 text-red-300"
      >
        <div className="flex items-center gap-3">
          <AlertCircle size={20} />
          {loadError ?? "Review information unavailable."}
        </div>
      </section>
    );
  }

  const review = state.review;
  const config = statusConfig[review.status];
  const canReview =
    review.review_required &&
    review.status === "pending";

  return (
    <section className="mt-8 space-y-6">
      <div className="rounded-2xl border border-slate-800 bg-[#101827] p-6 shadow-lg">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="mb-2 flex items-center gap-2 text-blue-400">
              <FileCheck2 size={20} />
              <span className="text-sm font-semibold uppercase tracking-wider">
                Human-in-the-Loop Security
              </span>
            </div>

            <h2 className="text-xl font-semibold text-white">
              Investigation Review
            </h2>

            <p className="mt-2 text-sm text-slate-400">
              Validate the AI-generated findings before
              accepting the investigation report.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <span
              className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-sm font-medium ${config.className}`}
            >
              <StatusIcon status={review.status} />
              {config.label}
            </span>

            <button
              type="button"
              onClick={() => void refreshReview()}
              disabled={refreshing || submitting !== null}
              aria-label="Refresh review status"
              title="Refresh review status"
              className="rounded-lg border border-slate-700 p-2 text-slate-300 transition hover:bg-slate-800 disabled:opacity-50"
            >
              <RefreshCw
                size={17}
                className={refreshing ? "animate-spin" : ""}
              />
            </button>
          </div>
        </div>

        <div className="mt-6 grid gap-4 rounded-xl border border-slate-800 bg-[#080d19] p-4 sm:grid-cols-2">
          <div>
            <p className="text-xs uppercase tracking-wider text-slate-500">
              Review Requirement
            </p>
            <p className="mt-1 text-sm text-slate-200">
              {review.review_required
                ? "Human approval required"
                : "Human approval not required"}
            </p>
          </div>

          <div>
            <p className="text-xs uppercase tracking-wider text-slate-500">
              Reviewed By
            </p>
            <p className="mt-1 text-sm text-slate-200">
              {review.reviewer_id !== null
                ? `User #${review.reviewer_id}`
                : "Not reviewed"}
            </p>
          </div>

          <div>
            <p className="text-xs uppercase tracking-wider text-slate-500">
              Created
            </p>
            <p className="mt-1 text-sm text-slate-200">
              {formatDate(review.created_at)}
            </p>
          </div>

          <div>
            <p className="text-xs uppercase tracking-wider text-slate-500">
              Decision Date
            </p>
            <p className="mt-1 text-sm text-slate-200">
              {formatDate(review.reviewed_at)}
            </p>
          </div>
        </div>

        {canReview ? (
          <div className="mt-6 space-y-4">
            <div>
              <label
                htmlFor="review-notes"
                className="mb-2 block text-sm font-medium text-slate-200"
              >
                Analyst Review Notes
              </label>

              <textarea
                id="review-notes"
                value={notes}
                onChange={(event) => {
                  setNotes(event.target.value);
                  setActionError(null);
                }}
                maxLength={2000}
                rows={5}
                placeholder="Explain your decision based on the investigation findings and evidence..."
                disabled={submitting !== null}
                className="w-full resize-y rounded-xl border border-slate-700 bg-[#080d19] px-4 py-3 text-sm text-white outline-none transition focus:border-blue-500 disabled:opacity-60"
              />

              <p className="mt-2 text-right text-xs text-slate-500">
                {notes.length}/2000 characters
              </p>
            </div>

            <div className="flex flex-wrap gap-3">
              <button
                type="button"
                onClick={() => requestDecision("approved")}
                disabled={
                  submitting !== null ||
                  refreshing ||
                  notes.trim().length === 0
                }
                className="inline-flex items-center justify-center gap-2 rounded-xl bg-emerald-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <CheckCircle2 size={18} />
                Approve Report
              </button>

              <button
                type="button"
                onClick={() => requestDecision("rejected")}
                disabled={
                  submitting !== null ||
                  refreshing ||
                  notes.trim().length === 0
                }
                className="inline-flex items-center justify-center gap-2 rounded-xl border border-red-500/40 bg-red-500/10 px-5 py-3 text-sm font-semibold text-red-300 transition hover:bg-red-500/20 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <XCircle size={18} />
                Reject Report
              </button>
            </div>
          </div>
        ) : (
          <div className="mt-6 rounded-xl border border-slate-800 bg-[#080d19] p-4">
            <p className="text-sm text-slate-300">
              {review.status === "approved"
                ? "This investigation report has been approved."
                : review.status === "rejected"
                  ? "This investigation report has been rejected."
                  : "Human review was not required for this investigation."}
            </p>

            {review.review_notes && (
              <div className="mt-4">
                <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Decision Notes
                </p>

                <p className="whitespace-pre-wrap text-sm leading-6 text-slate-300">
                  {review.review_notes}
                </p>
              </div>
            )}
          </div>
        )}

        {actionError && (
          <div
            role="alert"
            className="mt-4 flex items-start gap-2 rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300"
          >
            <AlertCircle size={17} />
            {actionError}
          </div>
        )}

        {actionMessage && (
          <div
            role="status"
            className="mt-4 rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3 text-sm text-emerald-300"
          >
            {actionMessage}
          </div>
        )}
      </div>

      <div className="rounded-2xl border border-slate-800 bg-[#101827] p-6 shadow-lg">
        <h3 className="text-lg font-semibold text-white">
          Review Decision History
        </h3>

        <p className="mt-2 text-sm text-slate-400">
          Recorded analyst decisions associated with this
          investigation report.
        </p>

        {state.history.length === 0 ? (
          <div className="mt-5 rounded-xl border border-slate-800 bg-[#080d19] p-5 text-sm text-slate-400">
            No review decisions have been recorded yet.
          </div>
        ) : (
          <div className="mt-5 space-y-3">
            {state.history.map((event) => (
              <div
                key={event.id}
                className="rounded-xl border border-slate-800 bg-[#080d19] p-4"
              >
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-center gap-2">
                    {event.action === "approved" ? (
                      <CheckCircle2
                        size={18}
                        className="text-emerald-400"
                      />
                    ) : (
                      <XCircle
                        size={18}
                        className="text-red-400"
                      />
                    )}

                    <span className="font-medium capitalize text-white">
                      {event.action}
                    </span>
                  </div>

                  <span className="text-xs text-slate-500">
                    {formatDate(event.created_at)}
                  </span>
                </div>

                <p className="mt-2 text-xs text-slate-500">
                  Reviewer ID: {event.actor_id}
                </p>

                {event.notes && (
                  <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-slate-300">
                    {event.notes}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {confirmDecision && (
        <div
          className="fixed inset-0 z-[100] flex items-center justify-center bg-black/75 px-4 py-6 backdrop-blur-sm"
          role="presentation"
          onMouseDown={(event) => {
            if (
              event.target === event.currentTarget &&
              !submittingRef.current
            ) {
              setConfirmDecision(null);
            }
          }}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="review-confirm-title"
            aria-describedby="review-confirm-description"
            className="w-full max-w-lg rounded-2xl border border-slate-700 bg-[#101827] p-6 shadow-2xl"
          >
            <div className="flex items-start justify-between gap-4">
              <div
                className={`flex h-12 w-12 items-center justify-center rounded-xl ${
                  confirmDecision === "approved"
                    ? "bg-emerald-500/15 text-emerald-400"
                    : "bg-red-500/15 text-red-400"
                }`}
              >
                {confirmDecision === "approved" ? (
                  <ShieldCheck size={25} />
                ) : (
                  <XCircle size={25} />
                )}
              </div>

              <button
                type="button"
                aria-label="Close confirmation"
                onClick={() => setConfirmDecision(null)}
                disabled={submitting !== null}
                className="rounded-lg p-2 text-slate-400 transition hover:bg-slate-800 hover:text-white disabled:opacity-50"
              >
                <X size={20} />
              </button>
            </div>

            <h3
              id="review-confirm-title"
              className="mt-5 text-xl font-semibold text-white"
            >
              {confirmDecision === "approved"
                ? "Approve Investigation?"
                : "Reject Investigation?"}
            </h3>

            <p
              id="review-confirm-description"
              className="mt-3 text-sm leading-6 text-slate-400"
            >
              {confirmDecision === "approved"
                ? "You are about to approve this AI-generated investigation report."
                : "You are about to reject this AI-generated investigation report."}
              {" "}
              Your decision and analyst notes will be
              recorded in the review history.
            </p>

            <div className="mt-5 rounded-xl border border-slate-800 bg-[#080d19] p-4">
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Analyst Notes
              </p>

              <p className="mt-2 max-h-36 overflow-y-auto whitespace-pre-wrap break-words text-sm leading-6 text-slate-200">
                {notes.trim()}
              </p>
            </div>

            <div className="mt-6 flex flex-wrap justify-end gap-3">
              <button
                type="button"
                onClick={() => setConfirmDecision(null)}
                disabled={submitting !== null}
                className="rounded-xl border border-slate-700 px-5 py-2.5 text-sm font-medium text-slate-200 transition hover:bg-slate-800 disabled:opacity-50"
              >
                Cancel
              </button>

              <button
                type="button"
                onClick={() => void confirmReview()}
                disabled={submitting !== null}
                className={`inline-flex items-center justify-center gap-2 rounded-xl px-5 py-2.5 text-sm font-semibold text-white transition disabled:opacity-50 ${
                  confirmDecision === "approved"
                    ? "bg-emerald-600 hover:bg-emerald-500"
                    : "bg-red-600 hover:bg-red-500"
                }`}
              >
                {submitting ? (
                  <LoaderCircle
                    size={18}
                    className="animate-spin"
                  />
                ) : confirmDecision === "approved" ? (
                  <CheckCircle2 size={18} />
                ) : (
                  <XCircle size={18} />
                )}

                {submitting
                  ? "Submitting..."
                  : confirmDecision === "approved"
                    ? "Confirm Approval"
                    : "Confirm Rejection"}
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
