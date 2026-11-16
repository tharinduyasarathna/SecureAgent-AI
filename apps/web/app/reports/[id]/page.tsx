
"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";

import {
  ArrowLeft,
  AlertCircle,
  LoaderCircle,
} from "lucide-react";

import Sidebar from "@/components/sidebar";
import ProtectedRoute from "@/components/protected-route";
import InvestigationReport from "@/components/investigation-report";
import InvestigationReviewPanel from "@/components/investigation-review";

import { useAuth } from "@/components/auth-provider";
import { apiRequest } from "@/lib/api";


type ReportData = Record<string, unknown>;


function SavedReportPage() {
  const { token } = useAuth();

  const params = useParams<{ id: string }>();
  const id = params.id;

  const [reportState, setReportState] = useState<{
    token: string;
    id: string;
    data: ReportData | null;
    error: string | null;
  } | null>(null);


  useEffect(() => {
    if (!token || !id) {
      return;
    }

    let cancelled = false;

    async function loadReport() {
      try {
        const response = await apiRequest<ReportData>(
          `/investigations/${encodeURIComponent(id)}/report`,
          { method: "GET" },
          token as string
        );

        if (!cancelled) {
          setReportState({
            token: token as string,
            id,
            data: response,
            error: null,
          });
        }
      } catch (err) {
        if (!cancelled) {
          setReportState({
            token: token as string,
            id,
            data: null,
            error:
              err instanceof Error
                ? err.message
                : "Unable to load investigation report.",
          });
        }
      }
    }

    void loadReport();

    return () => {
      cancelled = true;
    };
  }, [token, id]);


  const current =
    reportState?.token === token &&
    reportState?.id === id
      ? reportState
      : null;


  return (
    <div className="min-h-screen bg-[#080d19] text-white">
      <Sidebar />

      <main className="min-h-screen px-5 pb-12 pt-20 sm:px-8 lg:ml-64 lg:px-10 lg:pt-8">
        <Link
          href="/"
          className="inline-flex items-center gap-2 text-sm text-slate-400 transition hover:text-white"
        >
          <ArrowLeft size={16} />
          Back to Dashboard
        </Link>


        <div className="mt-7">
          {!current ? (
            <div className="flex items-center gap-3 rounded-xl border border-slate-800 bg-[#101827] p-6 text-slate-300">
              <LoaderCircle
                size={20}
                className="animate-spin text-blue-400"
              />
              Loading investigation report...
            </div>
          ) : current.error ? (
            <div
              role="alert"
              className="flex items-center gap-3 rounded-xl border border-red-500/30 bg-red-500/10 p-6 text-red-300"
            >
              <AlertCircle size={20} />
              {current.error}
            </div>
          ) : current.data ? (
            <>
              <InvestigationReport data={current.data} />

              {token && id && (
                <InvestigationReviewPanel
                  key={`${id}:${token}`}
                  investigationId={id}
                  token={token}
                />
              )}
            </>
          ) : null}
        </div>
      </main>
    </div>
  );
}


export default function ReportPage() {
  return (
    <ProtectedRoute>
      <SavedReportPage />
    </ProtectedRoute>
  );
}
