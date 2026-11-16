
import { apiRequest } from "@/lib/api";

export type InvestigationSummary = {
  investigation_id: string;
  severity: string;
  report_version: string;
  created_at: string;
  title: string;
  review_status: string | null;
};

export type InvestigationReportList = {
  total: number;
  limit: number;
  offset: number;
  items: InvestigationSummary[];
};

export async function getInvestigationReports(
  token: string,
  limit = 100,
  offset = 0
): Promise<InvestigationReportList> {
  return apiRequest<InvestigationReportList>(
    `/investigations/reports?limit=${limit}&offset=${offset}`,
    { method: "GET" },
    token
  );
}
