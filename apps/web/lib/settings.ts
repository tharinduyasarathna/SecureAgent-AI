
export type SecuritySettings = {
  enableSecurityAgent: boolean;
  enableRagAgent: boolean;
  enableReportAgent: boolean;
  requireHumanReview: boolean;
  enableAuditLogging: boolean;
  enablePromptInjectionProtection: boolean;
  defaultSeverityThreshold: "low" | "medium" | "high" | "critical";
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

const STORAGE_KEY = "secureagent_ui_settings";

export function loadSettings(): SecuritySettings {
  if (typeof window === "undefined") {
    return { ...DEFAULT_SETTINGS };
  }

  try {
    const saved = localStorage.getItem(STORAGE_KEY);

    if (!saved) return { ...DEFAULT_SETTINGS };

    const parsed: unknown = JSON.parse(saved);

    if (
      parsed === null ||
      typeof parsed !== "object" ||
      Array.isArray(parsed)
    ) {
      return { ...DEFAULT_SETTINGS };
    }

    const input = parsed as Record<string, unknown>;

    const booleanSetting = (
      key: keyof SecuritySettings,
      fallback: boolean
    ): boolean =>
      typeof input[key] === "boolean"
        ? (input[key] as boolean)
        : fallback;

    const threshold = input.defaultSeverityThreshold;

    const maxEvents = input.maxInvestigationEvents;

    return {
      enableSecurityAgent: booleanSetting(
        "enableSecurityAgent",
        true
      ),
      enableRagAgent: booleanSetting("enableRagAgent", true),
      enableReportAgent: booleanSetting(
        "enableReportAgent",
        true
      ),
      requireHumanReview: booleanSetting(
        "requireHumanReview",
        true
      ),
      enableAuditLogging: booleanSetting(
        "enableAuditLogging",
        true
      ),
      enablePromptInjectionProtection: booleanSetting(
        "enablePromptInjectionProtection",
        true
      ),
      defaultSeverityThreshold:
        typeof threshold === "string" &&
        ["low", "medium", "high", "critical"].includes(threshold)
          ? (threshold as SecuritySettings["defaultSeverityThreshold"])
          : "medium",
      maxInvestigationEvents:
        typeof maxEvents === "number" &&
        Number.isInteger(maxEvents) &&
        maxEvents >= 1 &&
        maxEvents <= 10000
          ? maxEvents
          : 100,
      autoGenerateReport: booleanSetting(
        "autoGenerateReport",
        true
      ),
    };
  } catch {
    return { ...DEFAULT_SETTINGS };
  }
}

export function saveSettings(settings: SecuritySettings): void {
  if (typeof window === "undefined") return;

  localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
}
