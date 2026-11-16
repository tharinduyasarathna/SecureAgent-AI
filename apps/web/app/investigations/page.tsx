
"use client";

import { useState } from "react";
import Link from "next/link";

import {
  Activity,
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  FileSearch,
  LoaderCircle,
  Play,
  RotateCcw,
  ShieldCheck,
} from "lucide-react";

import Sidebar from "@/components/sidebar";
import ProtectedRoute from "@/components/protected-route";
import InvestigationReport from "@/components/investigation-report";
import { useAuth } from "@/components/auth-provider";
import { apiRequest } from "@/lib/api";

type InvestigationResponse = Record<string, unknown>;

const initialPayload = `{
  "events": []
}`;

function getObject(
  value: unknown
): Record<string, unknown> | null {
  if (
    value !== null &&
    typeof value === "object" &&
    !Array.isArray(value)
  ) {
    return value as Record<string, unknown>;
  }

  return null;
}

function InvestigationWorkspace() {
  const { token } = useAuth();

  const [payload, setPayload] = useState(initialPayload);
  const [result, setResult] =
    useState<InvestigationResponse | null>(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function runInvestigation() {
    if (!token || loading) return;

    setError(null);
    setResult(null);

    let parsedPayload: unknown;

    try {
      parsedPayload = JSON.parse(payload);
    } catch {
      setError("Invalid JSON. Please check your request body.");
      return;
    }

    if (
      !parsedPayload ||
      typeof parsedPayload !== "object" ||
      Array.isArray(parsedPayload)
    ) {
      setError("The request body must be a JSON object.");
      return;
    }

    setLoading(true);

    try {
      const response = await apiRequest<InvestigationResponse>(
        "/investigations",
        {
          method: "POST",
          body: JSON.stringify(parsedPayload),
        },
        token
      );

      setResult(response);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Investigation failed. Please try again."
      );
    } finally {
      setLoading(false);
    }
  }

  function resetWorkspace() {
    if (loading) return;

    setPayload(initialPayload);
    setResult(null);
    setError(null);
  }

  const nestedReport = getObject(result?.report);

  const investigationId =
    result?.investigation_id ??
    nestedReport?.investigation_id ??
    null;

  return (
    <div className="min-h-screen bg-[#080d19] text-white">
      <Sidebar />

      <main className="min-h-screen px-5 pb-12 pt-20 sm:px-8 lg:ml-64 lg:px-10 lg:pt-8">
        <header className="border-b border-slate-800 pb-7">
          <Link
            href="/"
            className="inline-flex items-center gap-2 text-sm text-slate-400 transition hover:text-white"
          >
            <ArrowLeft size={16} />
            Back to Dashboard
          </Link>

          <div className="mt-5 flex items-center gap-3">
            <div className="rounded-xl bg-blue-600/15 p-3 text-blue-400">
              <FileSearch size={25} />
            </div>

            <div>
              <h1 className="text-3xl font-bold tracking-tight">
                Investigation Workspace
              </h1>

              <p className="mt-2 text-sm text-slate-400">
                Analyze security events using the SecureAgent AI
                multi-agent workflow.
              </p>
            </div>
          </div>
        </header>

        <div className="mt-8 grid gap-6 xl:grid-cols-3">
          <section className="rounded-2xl border border-slate-800 bg-[#101827] p-6 xl:col-span-2">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <h2 className="text-lg font-semibold">
                  Investigation Input
                </h2>

                <p className="mt-1 text-sm text-slate-400">
                  Enter the JSON request used to start an
                  investigation.
                </p>
              </div>

              <button
                type="button"
                onClick={resetWorkspace}
                disabled={loading}
                className="inline-flex items-center gap-2 rounded-xl border border-slate-700 px-4 py-2 text-sm text-slate-300 transition hover:bg-slate-800 disabled:opacity-50"
              >
                <RotateCcw size={16} />
                Reset
              </button>
            </div>

            <label
              htmlFor="investigation-payload"
              className="mt-6 block text-sm font-medium text-slate-300"
            >
              Security Event Payload
            </label>

            <textarea
              id="investigation-payload"
              value={payload}
              onChange={(event) =>
                setPayload(event.target.value)
              }
              disabled={loading}
              spellCheck={false}
              className="mt-3 min-h-[380px] w-full resize-y rounded-xl border border-slate-700 bg-[#080d19] p-5 font-mono text-sm leading-6 text-slate-200 outline-none transition focus:border-blue-500 disabled:opacity-60"
              placeholder="Enter a JSON request payload..."
            />

            <p className="mt-3 text-xs text-slate-500">
              The service validates your request and enforces
              investigation permissions before processing it.
            </p>

            {error && (
              <div
                role="alert"
                className="mt-5 flex items-start gap-3 rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-300"
              >
                <AlertCircle
                  size={18}
                  className="mt-0.5 shrink-0"
                />
                <span>{error}</span>
              </div>
            )}

            <div className="mt-6 flex flex-wrap items-center justify-between gap-4">
              <div className="flex items-center gap-2 text-xs text-slate-500">
                <ShieldCheck
                  size={16}
                  className="text-emerald-400"
                />
                Authenticated and audited workflow
              </div>

              <button
                type="button"
                onClick={() => void runInvestigation()}
                disabled={loading || !token || !payload.trim()}
                className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-6 py-3 text-sm font-semibold text-white transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {loading ? (
                  <>
                    <LoaderCircle
                      size={18}
                      className="animate-spin"
                    />
                    Running Investigation...
                  </>
                ) : (
                  <>
                    <Play size={18} />
                    Run Investigation
                  </>
                )}
              </button>
            </div>
          </section>

          <section className="rounded-2xl border border-slate-800 bg-[#101827] p-6">
            <div className="flex items-center gap-3">
              <Activity
                size={22}
                className="text-purple-400"
              />

              <h2 className="text-lg font-semibold">
                Investigation Pipeline
              </h2>
            </div>

            <p className="mt-2 text-sm text-slate-400">
              A controlled workflow for analyzing security events.
            </p>

            <div className="mt-7 rounded-xl border border-blue-500/20 bg-blue-500/10 p-4 text-center">
              <p className="font-semibold text-blue-300">
                Investigation Coordinator
              </p>

              <p className="mt-1 text-xs text-slate-400">
                Delegation policy and orchestration
              </p>
            </div>

            <div className="mx-auto h-7 w-px bg-slate-700" />

            <div className="space-y-3">
              {[
                {
                  name: "Security Analysis",
                  description:
                    "Event correlation and threat detection",
                },
                {
                  name: "Evidence Retrieval",
                  description:
                    "Authorized contextual retrieval",
                },
                {
                  name: "Report Generation",
                  description:
                    "Structured security assessment",
                },
              ].map((agent) => (
                <div
                  key={agent.name}
                  className="rounded-xl border border-slate-800 bg-slate-900/50 p-4"
                >
                  <p className="text-sm font-semibold text-white">
                    {agent.name}
                  </p>

                  <p className="mt-1 text-xs text-slate-400">
                    {agent.description}
                  </p>
                </div>
              ))}
            </div>

            <div className="mt-7 rounded-xl border border-slate-800 bg-slate-900/50 p-4">
              <p className="text-sm font-semibold">
                Execution Status
              </p>

              <div className="mt-3 flex items-center gap-2 text-sm">
                {loading ? (
                  <>
                    <LoaderCircle
                      size={17}
                      className="animate-spin text-blue-400"
                    />
                    <span className="text-blue-300">
                      Processing request
                    </span>
                  </>
                ) : result ? (
                  <>
                    <CheckCircle2
                      size={17}
                      className="text-emerald-400"
                    />
                    <span className="text-emerald-300">
                      Response received
                    </span>
                  </>
                ) : error ? (
                  <>
                    <AlertCircle
                      size={17}
                      className="text-red-400"
                    />
                    <span className="text-red-300">
                      Request unsuccessful
                    </span>
                  </>
                ) : (
                  <span className="text-slate-400">
                    Ready for investigation
                  </span>
                )}
              </div>

              <p className="mt-3 text-xs leading-5 text-slate-500">
                The API returns the completed result. This page
                does not yet provide live per-agent progress.
              </p>
            </div>
          </section>
        </div>

        {result && (
          <section className="mt-8 space-y-5">
            <InvestigationReport data={result} />

            {typeof investigationId === "string" && (
              <div className="flex justify-end">
                <Link
                  href={`/reports/${encodeURIComponent(
                    investigationId
                  )}`}
                  className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-blue-500"
                >
                  <FileSearch size={17} />
                  Open Saved Report
                </Link>
              </div>
            )}
          </section>
        )}
      </main>
    </div>
  );
}

export default function InvestigationsPage() {
  return (
    <ProtectedRoute>
      <InvestigationWorkspace />
    </ProtectedRoute>
  );
}
