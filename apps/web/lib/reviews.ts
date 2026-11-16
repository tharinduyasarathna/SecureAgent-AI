
import { apiRequest } from "@/lib/api";

export type ReviewStatus =
  | "pending"
  | "approved"
  | "rejected"
  | "not_required";

export type ReviewDecision = "approved" | "rejected";

export interface InvestigationReview {
  investigation_id: string;
  user_id: number;
  review_required: boolean;
  status: ReviewStatus;
  reviewer_id: number | null;
  review_notes: string | null;
  reviewed_at: string | null;
  created_at: string | null;
}

export interface InvestigationReviewEvent {
  id: number;
  investigation_id: string;
  actor_id: number;
  action: ReviewDecision;
  notes: string | null;
  created_at: string;
}

export interface InvestigationReviewHistory {
  items: InvestigationReviewEvent[];
}

export async function getInvestigationReview(
  investigationId: string,
  token: string
): Promise<InvestigationReview> {
  return apiRequest<InvestigationReview>(
    `/investigations/${encodeURIComponent(investigationId)}/review`,
    { method: "GET" },
    token
  );
}

export async function submitInvestigationReview(
  investigationId: string,
  token: string,
  decision: ReviewDecision,
  notes: string
): Promise<InvestigationReview> {
  return apiRequest<InvestigationReview>(
    `/investigations/${encodeURIComponent(investigationId)}/review`,
    {
      method: "POST",
      body: JSON.stringify({
        decision,
        notes,
      }),
    },
    token
  );
}

export async function getInvestigationReviewHistory(
  investigationId: string,
  token: string
): Promise<InvestigationReviewEvent[]> {
  const response =
    await apiRequest<InvestigationReviewHistory>(
      `/investigations/${encodeURIComponent(investigationId)}/review/history`,
      { method: "GET" },
      token
    );

  return response.items;
}
