
"use client";

import { useRef, useState } from "react";
import Link from "next/link";
import {
  Activity,
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  FileSearch,
  FileText,
  FileUp,
  LoaderCircle,
  Play,
  RotateCcw,
  ShieldCheck,
  Upload,
  X,
} from "lucide-react";

import Sidebar from "@/components/sidebar";
import ProtectedRoute from "@/components/protected-route";
import InvestigationReport from "@/components/investigation-report";
import { useAuth } from "@/components/auth-provider";
import { apiRequest } from "@/lib/api";

type InvestigationResponse = Record<string, unknown>;
type InputMode = "document" | "json";

type DocumentUploadResponse = {
  document_id: number;
  filename: string;
  owner_id: number;
  file_type?: string;
  chunks_created: number;
  embedding_dimensions: number;
  status: string;
};

type EvidenceReference = {
  event_index: number;
  evidence: string;
};

type RejectedEvent = {
  index: number;
  reason: string;
};

type ExtractionResponse = {
  document_id: number;
  filename: string;
  status: string;
  events: Record<string, unknown>[];
  event_count: number;
  evidence_references: EvidenceReference[];
  rejected_events: RejectedEvent[];
  rejected_count: number;
  requires_analyst_confirmation: boolean;
};

type ProcessingStage =
  | "uploading"
  | "extracting"
  | "investigating"
  | null;

const API_URL =
  process.env.NEXT_PUBLIC_API_URL ??
  "http://127.0.0.1:8765";

const MAX_FILE_SIZE = 5 * 1024 * 1024;

const initialPayload = `{
  "request": "Investigate the supplied security events.",
  "events": [],
  "top_k": 5
}`;

const initialInstructions =
  "Investigate the uploaded document for security threats, suspicious activity, anomalies, and indicators of compromise. Identify relevant evidence, assess potential risks, and provide a structured security report.";

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

async function readApiError(
  response: Response,
  fallback: string
): Promise<string> {
  try {
    const data: unknown = await response.json();
    const error = getObject(data);

    if (typeof error?.detail === "string") {
      return error.detail;
    }

    if (Array.isArray(error?.detail)) {
      return JSON.stringify(error.detail);
    }
  } catch {
    return fallback;
  }

  return fallback;
}

async function uploadInvestigationDocument(
  file: File,
  token: string
): Promise<DocumentUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(
    `${API_URL}/rag/documents/upload`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: formData,
      cache: "no-store",
    }
  );

  if (!response.ok) {
    throw new Error(
      await readApiError(
        response,
        `Document upload failed (${response.status})`
      )
    );
  }

  return (await response.json()) as DocumentUploadResponse;
}

async function extractDocumentEvents(
  documentId: number,
  token: string
): Promise<ExtractionResponse> {
  const response = await fetch(
    `${API_URL}/investigations/documents/${documentId}/extract-events`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
      },
      cache: "no-store",
    }
  );

  if (!response.ok) {
    throw new Error(
      await readApiError(
        response,
        `Event extraction failed (${response.status})`
      )
    );
  }

  return (await response.json()) as ExtractionResponse;
}

function InvestigationWorkspace() {
  const { token } = useAuth();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [inputMode, setInputMode] =
    useState<InputMode>("document");

  const [payload, setPayload] =
    useState(initialPayload);

  const [instructions, setInstructions] =
    useState(initialInstructions);

  const [selectedFile, setSelectedFile] =
    useState<File | null>(null);

  const [uploadedDocument, setUploadedDocument] =
    useState<DocumentUploadResponse | null>(null);

  const [extraction, setExtraction] =
    useState<ExtractionResponse | null>(null);

  const [reviewedEvents, setReviewedEvents] =
    useState("");

  const [analystConfirmed, setAnalystConfirmed] =
    useState(false);

  const [result, setResult] =
    useState<InvestigationResponse | null>(null);

  const [loading, setLoading] = useState(false);

  const [stage, setStage] =
    useState<ProcessingStage>(null);

  const [error, setError] =
    useState<string | null>(null);

  function clearExtraction() {
    setExtraction(null);
    setReviewedEvents("");
    setAnalystConfirmed(false);
  }

  function handleFileSelection(
    event: React.ChangeEvent<HTMLInputElement>
  ) {
    const file = event.target.files?.[0] ?? null;

    setError(null);
    setResult(null);
    setUploadedDocument(null);
    clearExtraction();

    if (!file) {
      setSelectedFile(null);
      return;
    }

    const extension = file.name
      .split(".")
      .pop()
      ?.toLowerCase();

    if (
      extension !== "pdf" &&
      extension !== "txt"
    ) {
      setSelectedFile(null);
      setError(
        "Only PDF and TXT documents are supported."
      );
      event.target.value = "";
      return;
    }

    if (file.size === 0) {
      setSelectedFile(null);
      setError("The selected document is empty.");
      event.target.value = "";
      return;
    }

    if (file.size > MAX_FILE_SIZE) {
      setSelectedFile(null);
      setError(
        "The selected document exceeds the 5 MB limit."
      );
      event.target.value = "";
      return;
    }

    setSelectedFile(file);
  }

  function removeSelectedFile() {
    if (loading) return;

    setSelectedFile(null);
    setUploadedDocument(null);
    setResult(null);
    setError(null);
    clearExtraction();

    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  }

  async function prepareDocument() {
    if (!token || loading || !selectedFile) {
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);
    clearExtraction();

    try {
      let document = uploadedDocument;

      if (!document) {
        setStage("uploading");

        document = await uploadInvestigationDocument(
          selectedFile,
          token
        );

        setUploadedDocument(document);
      }

      setStage("extracting");

      const extracted = await extractDocumentEvents(
        document.document_id,
        token
      );

      if (!Array.isArray(extracted.events)) {
        throw new Error(
          "The extraction service returned invalid events."
        );
      }

      setExtraction(extracted);

      setReviewedEvents(
        JSON.stringify(extracted.events, null, 2)
      );

      if (extracted.events.length === 0) {
        setError(
          "No qualifying security events were extracted. The document may lack explicit timestamps or supported event types. Authentication events also require source IP addresses. Review the document before investigating."
        );
      }
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to prepare the document."
      );
    } finally {
      setLoading(false);
      setStage(null);
    }
  }

  function validateReviewedEvents():
    Record<string, unknown>[] | null {
    let parsed: unknown;

    try {
      parsed = JSON.parse(reviewedEvents);
    } catch {
      setError(
        "Invalid event JSON. Check the extracted events."
      );
      return null;
    }

    if (!Array.isArray(parsed)) {
      setError(
        "Reviewed events must be a JSON array."
      );
      return null;
    }

    if (parsed.length === 0) {
      setError(
        "At least one reviewed security event is required."
      );
      return null;
    }

    if (parsed.length > 100) {
      setError(
        "A maximum of 100 extracted events is supported."
      );
      return null;
    }

    const valid = parsed.every((item) => {
      const event = getObject(item);

      if (
        event === null ||
        typeof event.timestamp !== "string" ||
        !event.timestamp.trim() ||
        typeof event.event_type !== "string" ||
        !event.event_type.trim()
      ) {
        return false;
      }

      const authenticationEvent =
        event.event_type === "login_success" ||
        event.event_type === "login_failure";

      if (authenticationEvent) {
        return (
          typeof event.source_ip === "string" &&
          event.source_ip.trim().length > 0
        );
      }

      return (
        event.source_ip == null ||
        (typeof event.source_ip === "string" &&
          event.source_ip.trim().length > 0)
      );
    });

    if (!valid) {
      setError(
        "Each event requires timestamp and event_type strings; authentication events also require a source_ip string."
      );
      return null;
    }

    return parsed as Record<string, unknown>[];
  }

  async function runInvestigation() {
    if (!token || loading) return;

    setError(null);
    setResult(null);

    let requestBody: Record<string, unknown>;

    if (inputMode === "document") {
      if (!uploadedDocument || !extraction) {
        setError(
          "Extract and review the document events first."
        );
        return;
      }

      if (!instructions.trim()) {
        setError(
          "Please enter investigation instructions."
        );
        return;
      }

      if (!analystConfirmed) {
        setError(
          "Confirm that you have reviewed the extracted events."
        );
        return;
      }

      const events = validateReviewedEvents();

      if (!events) return;

      requestBody = {
        request: instructions.trim(),
        events,
        top_k: 5,
        document_id: uploadedDocument.document_id,
      };
    } else {
      let parsedPayload: unknown;

      try {
        parsedPayload = JSON.parse(payload);
      } catch {
        setError(
          "Invalid JSON. Please check your request body."
        );
        return;
      }

      const parsedObject = getObject(parsedPayload);

      if (!parsedObject) {
        setError(
          "The request body must be a JSON object."
        );
        return;
      }

      requestBody = parsedObject;
    }

    setLoading(true);
    setStage("investigating");

    try {
      const response =
        await apiRequest<InvestigationResponse>(
          "/investigations",
          {
            method: "POST",
            body: JSON.stringify(requestBody),
          },
          token
        );

      // Preserve the exact submitted event order for evidence index lookup.
      // This only enriches the UI response; it does not alter the API request
      // or the server-side saved investigation report.
      const submittedEvents = requestBody.events;
      setResult(
        Array.isArray(submittedEvents) && submittedEvents.length > 0
          ? { ...response, source_events: submittedEvents }
          : response
      );
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Investigation failed. Please try again."
      );
    } finally {
      setLoading(false);
      setStage(null);
    }
  }

  function resetWorkspace() {
    if (loading) return;

    setPayload(initialPayload);
    setInstructions(initialInstructions);
    setSelectedFile(null);
    setUploadedDocument(null);
    setResult(null);
    setError(null);
    setStage(null);
    clearExtraction();

    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  }

  const nestedReport = getObject(result?.report);

  const investigationId =
    result?.investigation_id ??
    nestedReport?.investigation_id ??
    null;

  const canPrepare =
    Boolean(token) &&
    !loading &&
    Boolean(selectedFile) &&
    !extraction;

  const canRun =
    Boolean(token) &&
    !loading &&
    (inputMode === "json"
      ? Boolean(payload.trim())
      : Boolean(
          uploadedDocument &&
          extraction &&
          extraction.events.length > 0 &&
          analystConfirmed &&
          reviewedEvents.trim() &&
          instructions.trim()
        ));

  const statusText =
    stage === "uploading"
      ? "Uploading and indexing document"
      : stage === "extracting"
        ? "Extracting security events"
        : stage === "investigating"
          ? "Processing investigation"
          : result
            ? "Investigation completed"
            : extraction
              ? "Awaiting analyst review"
              : error
                ? "Action unsuccessful"
                : "Ready for investigation";

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
                Analyze security events and uploaded documents
                using the SecureAgent AI multi-agent workflow.
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
                  Upload a security document or submit a
                  structured JSON investigation request.
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

            <div className="mt-6 flex rounded-xl border border-slate-700 bg-[#080d19] p-1">
              <button
                type="button"
                onClick={() => {
                  setInputMode("document");
                  setError(null);
                  setResult(null);
                }}
                disabled={loading}
                className={`flex flex-1 items-center justify-center gap-2 rounded-lg px-4 py-3 text-sm font-medium transition disabled:opacity-50 ${
                  inputMode === "document"
                    ? "bg-blue-600 text-white"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                <FileUp size={17} />
                Upload Document
              </button>

              <button
                type="button"
                onClick={() => {
                  setInputMode("json");
                  setError(null);
                  setResult(null);
                }}
                disabled={loading}
                className={`flex flex-1 items-center justify-center gap-2 rounded-lg px-4 py-3 text-sm font-medium transition disabled:opacity-50 ${
                  inputMode === "json"
                    ? "bg-blue-600 text-white"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                <FileText size={17} />
                JSON Request
              </button>
            </div>

            {inputMode === "document" ? (
              <div className="mt-6 space-y-6">
                <div>
                  <label
                    htmlFor="investigation-document"
                    className="block text-sm font-medium text-slate-300"
                  >
                    Security Document
                  </label>

                  <div className="mt-3 rounded-xl border border-dashed border-slate-600 bg-[#080d19] p-6">
                    <input
                      ref={fileInputRef}
                      id="investigation-document"
                      type="file"
                      accept=".pdf,.txt,application/pdf,text/plain"
                      onChange={handleFileSelection}
                      disabled={loading}
                      className="hidden"
                    />

                    {selectedFile ? (
                      <div className="flex items-center justify-between gap-4">
                        <div className="flex min-w-0 items-center gap-3">
                          <div className="rounded-lg bg-blue-500/10 p-3 text-blue-400">
                            <FileText size={22} />
                          </div>

                          <div className="min-w-0">
                            <p className="truncate text-sm font-medium text-white">
                              {selectedFile.name}
                            </p>

                            <p className="mt-1 text-xs text-slate-400">
                              {(selectedFile.size / 1024).toFixed(1)} KB
                            </p>
                          </div>
                        </div>

                        <button
                          type="button"
                          onClick={removeSelectedFile}
                          disabled={loading}
                          aria-label="Remove selected document"
                          className="rounded-lg p-2 text-slate-400 transition hover:bg-slate-800 hover:text-white disabled:opacity-50"
                        >
                          <X size={19} />
                        </button>
                      </div>
                    ) : (
                      <div className="text-center">
                        <Upload
                          size={30}
                          className="mx-auto text-blue-400"
                        />

                        <p className="mt-3 text-sm font-medium">
                          Select a PDF or TXT document
                        </p>

                        <p className="mt-2 text-xs text-slate-500">
                          Maximum file size: 5 MB
                        </p>

                        <button
                          type="button"
                          onClick={() =>
                            fileInputRef.current?.click()
                          }
                          disabled={loading}
                          className="mt-5 rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-semibold transition hover:bg-blue-500 disabled:opacity-50"
                        >
                          Browse Files
                        </button>
                      </div>
                    )}
                  </div>
                </div>

                <div>
                  <label
                    htmlFor="investigation-instructions"
                    className="block text-sm font-medium text-slate-300"
                  >
                    Investigation Instructions
                  </label>

                  <textarea
                    id="investigation-instructions"
                    value={instructions}
                    onChange={(event) =>
                      setInstructions(event.target.value)
                    }
                    disabled={loading}
                    maxLength={2000}
                    spellCheck={false}
                    className="mt-3 min-h-[160px] w-full resize-y rounded-xl border border-slate-700 bg-[#080d19] p-4 text-sm leading-6 text-slate-200 outline-none transition focus:border-blue-500 disabled:opacity-60"
                    placeholder="Describe what the AI agents should investigate..."
                  />

                  <p className="mt-2 text-xs text-slate-500">
                    The document is indexed for evidence
                    retrieval. Extracted security events must
                    be reviewed before investigation.
                  </p>
                </div>

                {uploadedDocument && (
                  <div className="flex items-start gap-3 rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-4">
                    <CheckCircle2
                      size={19}
                      className="mt-0.5 shrink-0 text-emerald-400"
                    />

                    <div>
                      <p className="text-sm font-semibold text-emerald-300">
                        Document indexed successfully
                      </p>

                      <p className="mt-1 text-xs text-slate-400">
                        Document ID:{" "}
                        {uploadedDocument.document_id}
                        {" · "}
                        {uploadedDocument.chunks_created} chunks
                      </p>
                    </div>
                  </div>
                )}

                {!extraction && (
                  <button
                    type="button"
                    onClick={() => void prepareDocument()}
                    disabled={!canPrepare}
                    className="inline-flex items-center gap-2 rounded-xl border border-blue-500/30 bg-blue-500/10 px-5 py-3 text-sm font-semibold text-blue-300 transition hover:bg-blue-500/20 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {loading &&
                    (stage === "uploading" ||
                      stage === "extracting") ? (
                      <>
                        <LoaderCircle
                          size={18}
                          className="animate-spin"
                        />
                        {stage === "uploading"
                          ? "Uploading and Indexing..."
                          : "Extracting Events..."}
                      </>
                    ) : (
                      <>
                        <FileSearch size={18} />
                        Extract Security Events
                      </>
                    )}
                  </button>
                )}

                {extraction && (
                  <div className="space-y-5 rounded-xl border border-slate-700 bg-[#080d19] p-5">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <h3 className="text-base font-semibold">
                          Extracted Security Events
                        </h3>

                        <p className="mt-1 text-xs text-slate-400">
                          Review and correct the candidate
                          events before starting an investigation.
                        </p>
                      </div>

                      <span className="rounded-lg border border-blue-500/30 bg-blue-500/10 px-3 py-2 text-xs font-semibold text-blue-300">
                        {extraction.event_count} extracted
                      </span>
                    </div>

                    {extraction.rejected_count > 0 && (
                      <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-200">
                        {extraction.rejected_count} candidate
                        event(s) were rejected during validation.

                        {extraction.rejected_events.length > 0 && (
                          <ul className="mt-2 list-disc space-y-1 pl-5 text-xs">
                            {extraction.rejected_events.map(
                              (item, index) => (
                                <li key={index}>
                                  Candidate {item.index + 1}:{" "}
                                  {item.reason}
                                </li>
                              )
                            )}
                          </ul>
                        )}
                      </div>
                    )}

                    {extraction.events.length > 0 && (
                      <>
                        <div>
                          <label
                            htmlFor="reviewed-events"
                            className="block text-sm font-medium text-slate-300"
                          >
                            Review Event JSON
                          </label>

                          <textarea
                            id="reviewed-events"
                            value={reviewedEvents}
                            onChange={(event) => {
                              setReviewedEvents(
                                event.target.value
                              );
                              setAnalystConfirmed(false);
                              setResult(null);
                            }}
                            disabled={loading}
                            spellCheck={false}
                            className="mt-3 min-h-[320px] w-full resize-y rounded-xl border border-slate-700 bg-slate-950 p-4 font-mono text-xs leading-6 text-slate-200 outline-none focus:border-blue-500 disabled:opacity-60"
                          />
                        </div>

                        {extraction.evidence_references.length > 0 && (
                          <div>
                            <h4 className="text-sm font-semibold text-slate-200">
                              Extracted Evidence
                            </h4>

                            <div className="mt-3 max-h-60 space-y-3 overflow-y-auto">
                              {extraction.evidence_references.map(
                                (reference, index) => (
                                  <div
                                    key={index}
                                    className="rounded-lg border border-slate-800 bg-slate-900/60 p-3"
                                  >
                                    <p className="text-xs font-semibold text-blue-300">
                                      Event{" "}
                                      {reference.event_index + 1}
                                    </p>

                                    <p className="mt-2 whitespace-pre-wrap break-words text-xs leading-5 text-slate-400">
                                      {reference.evidence}
                                    </p>
                                  </div>
                                )
                              )}
                            </div>
                          </div>
                        )}

                        <label className="flex cursor-pointer items-start gap-3 rounded-lg border border-slate-700 bg-slate-900/50 p-4">
                          <input
                            type="checkbox"
                            checked={analystConfirmed}
                            onChange={(event) =>
                              setAnalystConfirmed(
                                event.target.checked
                              )
                            }
                            disabled={loading}
                            className="mt-1 h-4 w-4 accent-blue-600"
                          />

                          <span className="text-sm leading-6 text-slate-300">
                            I have reviewed the extracted events
                            and confirm they are appropriate
                            inputs for this investigation.
                          </span>
                        </label>
                      </>
                    )}

                    {extraction.events.length === 0 && (
                      <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-200">
                        No qualifying events were found.
                        The investigation will not start
                        automatically with an empty event list.
                      </div>
                    )}

                    <button
                      type="button"
                      onClick={() => {
                        clearExtraction();
                        setError(null);
                      }}
                      disabled={loading}
                      className="inline-flex items-center gap-2 text-sm text-slate-400 transition hover:text-white disabled:opacity-50"
                    >
                      <RotateCcw size={15} />
                      Extract Again
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <div className="mt-6">
                <label
                  htmlFor="investigation-payload"
                  className="block text-sm font-medium text-slate-300"
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
                  Include a request and optional security
                  events, top_k, and document_id fields.
                </p>
              </div>
            )}

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
                disabled={!canRun}
                className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-6 py-3 text-sm font-semibold text-white transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {stage === "investigating" ? (
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
              A controlled workflow for analyzing security
              events and retrieved evidence.
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
                  <LoaderCircle
                    size={17}
                    className="animate-spin text-blue-400"
                  />
                ) : result ? (
                  <CheckCircle2
                    size={17}
                    className="text-emerald-400"
                  />
                ) : error ? (
                  <AlertCircle
                    size={17}
                    className="text-red-400"
                  />
                ) : (
                  <ShieldCheck
                    size={17}
                    className="text-slate-400"
                  />
                )}

                <span
                  className={
                    result
                      ? "text-emerald-300"
                      : error
                        ? "text-red-300"
                        : loading
                          ? "text-blue-300"
                          : "text-slate-400"
                  }
                >
                  {statusText}
                </span>
              </div>

              <p className="mt-3 text-xs leading-5 text-slate-500">
                Document investigations require event extraction
                and analyst confirmation before execution.
                The API returns the completed investigation
                result without live per-agent progress.
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
