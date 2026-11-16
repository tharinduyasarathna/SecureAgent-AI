
import { apiRequest } from "@/lib/api";

export type SeverityThreshold =
  | "low"
  | "medium"
  | "high"
  | "critical";

export type SecuritySettings = {
  enableSecurityAgent: boolean;
  enableRagAgent: boolean;
  enableReportAgent: boolean;
  requireHumanReview: boolean;
  enableAuditLogging: boolean;
  enablePromptInjectionProtection: boolean;
  defaultSeverityThreshold: SeverityThreshold;
  maxInvestigationEvents: number;
  autoGenerateReport: boolean;
};

export const DEFAULT_SETTINGS: SecuritySettings = {
  enableSecurityAgent: true,
  enableRagAgent: true,
  enableReportAgent: true,
  requireHumanReview: true,
  enableAuditLogging: true,
  enablePromptInjectionProtection: true,
  defaultSeverityThreshold: "medium",
  maxInvestigationEvents: 100,
  autoGenerateReport: true,
};

type ApiPreferences = {
  enable_security_agent: boolean;
  enable_rag_agent: boolean;
  enable_report_agent: boolean;
  require_human_review: boolean;
  default_severity_threshold: SeverityThreshold;
  max_investigation_events: number;
  auto_generate_report: boolean;
};

type ApiSecurityPolicy = {
  audit_logging_enabled: true;
  prompt_injection_protection_enabled: true;
  authentication_required: true;
  owner_scoped_data_access: true;
};

export type SettingsApiResponse = {
  preferences: ApiPreferences;
  security_policy: ApiSecurityPolicy;
};

function toFrontendSettings(
  response: SettingsApiResponse
): SecuritySettings {
  const preferences = response.preferences;

  return {
    enableSecurityAgent:
      preferences.enable_security_agent,
    enableRagAgent:
      preferences.enable_rag_agent,
    enableReportAgent:
      preferences.enable_report_agent,
    requireHumanReview:
      preferences.require_human_review,
    enableAuditLogging:
      response.security_policy.audit_logging_enabled,
    enablePromptInjectionProtection:
      response.security_policy
        .prompt_injection_protection_enabled,
    defaultSeverityThreshold:
      preferences.default_severity_threshold,
    maxInvestigationEvents:
      preferences.max_investigation_events,
    autoGenerateReport:
      preferences.auto_generate_report,
  };
}

function toApiPreferences(
  settings: SecuritySettings
): ApiPreferences {
  return {
    enable_security_agent:
      settings.enableSecurityAgent,
    enable_rag_agent:
      settings.enableRagAgent,
    enable_report_agent:
      settings.enableReportAgent,
    require_human_review:
      settings.requireHumanReview,
    default_severity_threshold:
      settings.defaultSeverityThreshold,
    max_investigation_events:
      settings.maxInvestigationEvents,
    auto_generate_report:
      settings.autoGenerateReport,
  };
}

export async function getSettings(
  token: string
): Promise<SecuritySettings> {
  const response = await apiRequest<SettingsApiResponse>(
    "/settings",
    { method: "GET" },
    token
  );

  return toFrontendSettings(response);
}

export async function updateSettings(
  token: string,
  settings: SecuritySettings
): Promise<SecuritySettings> {
  const response = await apiRequest<SettingsApiResponse>(
    "/settings",
    {
      method: "PUT",
      body: JSON.stringify(toApiPreferences(settings)),
    },
    token
  );

  return toFrontendSettings(response);
}
