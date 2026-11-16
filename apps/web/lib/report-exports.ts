
const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_URL ??
  "http://127.0.0.1:8765"
).replace(/\/$/, "");

export type ReportExportFormat = "pdf" | "json";

export type ReportExportStatus =
  | "pending"
  | "approved"
  | "rejected"
  | "not_required";

export function canExportReport(
  status: ReportExportStatus | null | undefined
): boolean {
  return status === "approved" || status === "not_required";
}

function getExportFilename(
  investigationId: string,
  format: ReportExportFormat
): string {
  return `secureagent-report-${investigationId}.${format}`;
}

export async function downloadInvestigationReport(
  investigationId: string,
  token: string,
  format: ReportExportFormat
): Promise<void> {
  if (!investigationId || !token) {
    throw new Error("Authentication or investigation ID missing.");
  }

  const url =
    `${API_BASE_URL}/investigations/` +
    `${encodeURIComponent(investigationId)}/export/${format}`;

  const response = await fetch(url, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
      Accept:
        format === "pdf"
          ? "application/pdf"
          : "application/json",
    },
    cache: "no-store",
  });

  if (!response.ok) {
    let message = `Report export failed (${response.status}).`;

    try {
      const errorData: unknown = await response.json();

      if (
        errorData &&
        typeof errorData === "object" &&
        "detail" in errorData &&
        typeof errorData.detail === "string"
      ) {
        message = errorData.detail;
      }
    } catch {
      // Preserve the HTTP error message.
    }

    throw new Error(message);
  }

  const blob = await response.blob();

  if (blob.size === 0) {
    throw new Error("The exported report is empty.");
  }

  const expectedType =
    format === "pdf"
      ? "application/pdf"
      : "application/json";

  const contentType = response.headers.get("content-type") ?? "";

  if (!contentType.toLowerCase().includes(expectedType)) {
    throw new Error("Unexpected report export response type.");
  }

  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");

  try {
    anchor.href = objectUrl;
    anchor.download = getExportFilename(
      investigationId,
      format
    );

    document.body.appendChild(anchor);
    anchor.click();
  } finally {
    anchor.remove();

    window.setTimeout(() => {
      URL.revokeObjectURL(objectUrl);
    }, 1000);
  }
}
