
"use client";

import { useState, useSyncExternalStore } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  Bot,
  BrainCircuit,
  Check,
  FileText,
  LockKeyhole,
  RotateCcw,
  Save,
  Settings2,
  ShieldCheck,
  SlidersHorizontal,
} from "lucide-react";

import Sidebar from "@/components/sidebar";
import ProtectedRoute from "@/components/protected-route";

import {
  DEFAULT_SETTINGS,
  loadSettings,
  saveSettings,
  type SecuritySettings,
} from "@/lib/settings";

type BooleanKey = {
  [K in keyof SecuritySettings]:
    SecuritySettings[K] extends boolean ? K : never;
}[keyof SecuritySettings];

type ToggleProps = {
  title: string;
  description: string;
  checked: boolean;
  onChange: (value: boolean) => void;
  disabled?: boolean;
};

const subscribe = () => () => {};

const getClientSnapshot = () => true;
const getServerSnapshot = () => false;

function SettingToggle({
  title,
  description,
  checked,
  onChange,
  disabled = false,
}: ToggleProps) {
  return (
    <div className="flex items-center justify-between gap-5 border-b border-slate-800 py-5 last:border-0">
      <div className="min-w-0">
        <h3 className="text-sm font-semibold text-white">
          {title}
        </h3>

        <p className="mt-1 text-xs leading-5 text-slate-400">
          {description}
        </p>
      </div>

      <button
        type="button"
        role="switch"
        aria-checked={checked}
        aria-label={title}
        disabled={disabled}
        onClick={() => onChange(!checked)}
        className={`relative h-7 w-12 shrink-0 rounded-full transition ${
          checked ? "bg-blue-600" : "bg-slate-700"
        } ${
          disabled
            ? "cursor-not-allowed opacity-50"
            : "cursor-pointer"
        }`}
      >
        <span
          className={`absolute left-1 top-1 h-5 w-5 rounded-full bg-white shadow transition-transform ${
            checked ? "translate-x-5" : ""
          }`}
        />
      </button>
    </div>
  );
}

function SettingsWorkspace() {
  const isClient = useSyncExternalStore(
    subscribe,
    getClientSnapshot,
    getServerSnapshot
  );

  if (!isClient) {
    return (
      <div className="min-h-screen bg-[#080d19] text-white">
        <Sidebar />

        <main className="min-h-screen px-5 pt-20 sm:px-8 lg:ml-64 lg:px-10 lg:pt-8">
          <div className="rounded-2xl border border-slate-800 bg-[#101827] p-8 text-sm text-slate-400">
            Loading system settings...
          </div>
        </main>
      </div>
    );
  }

  return <SettingsContent />;
}

function SettingsContent() {
  const [settings, setSettings] = useState<SecuritySettings>(
    () => loadSettings()
  );

  const [saved, setSaved] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  function updateBoolean(
    key: BooleanKey,
    value: boolean
  ) {
    setSettings((current) => ({
      ...current,
      [key]: value,
    }));

    setSaved(false);
    setSaveError(null);
  }

  function updateSetting<K extends keyof SecuritySettings>(
    key: K,
    value: SecuritySettings[K]
  ) {
    setSettings((current) => ({
      ...current,
      [key]: value,
    }));

    setSaved(false);
    setSaveError(null);
  }

  function handleSave() {
    try {
      saveSettings(settings);
      setSaved(true);
      setSaveError(null);
    } catch {
      setSaveError(
        "Unable to save settings in this browser."
      );
      setSaved(false);
    }
  }

  function handleReset() {
    setSettings({ ...DEFAULT_SETTINGS });
    setSaved(false);
    setSaveError(null);
  }

  return (
    <div className="min-h-screen bg-[#080d19] text-white">
      <Sidebar />

      <main className="min-h-screen px-5 pb-12 pt-20 sm:px-8 lg:ml-64 lg:px-10 lg:pt-8">
        <header className="border-b border-slate-800 pb-7">
          <Link
            href="/"
            className="inline-flex items-center gap-2 text-sm text-slate-400 hover:text-white"
          >
            <ArrowLeft size={16} />
            Back to Dashboard
          </Link>

          <div className="mt-5 flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className="rounded-xl bg-blue-600/15 p-3 text-blue-400">
                <Settings2 size={26} />
              </div>

              <div>
                <h1 className="text-3xl font-bold tracking-tight">
                  System Settings
                </h1>

                <p className="mt-2 text-sm text-slate-400">
                  Configure investigation preferences and review
                  planned agent controls.
                </p>
              </div>
            </div>

            <div className="flex flex-wrap gap-3">
              <button
                type="button"
                onClick={handleReset}
                className="inline-flex items-center gap-2 rounded-xl border border-slate-700 px-4 py-2.5 text-sm text-slate-300 transition hover:bg-slate-800"
              >
                <RotateCcw size={16} />
                Reset
              </button>

              <button
                type="button"
                onClick={handleSave}
                className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-blue-500"
              >
                {saved ? (
                  <Check size={17} />
                ) : (
                  <Save size={17} />
                )}

                {saved
                  ? "Saved Locally"
                  : "Save Preferences"}
              </button>
            </div>
          </div>
        </header>

        <div className="mt-6 rounded-xl border border-blue-500/25 bg-blue-500/5 p-4 text-sm leading-6 text-blue-200">
          Configuration preview: these preferences are stored
          only in this browser. They do not currently enable,
          disable, or enforce backend security features.
        </div>

        {saveError && (
          <p
            role="alert"
            className="mt-4 text-sm text-red-400"
          >
            {saveError}
          </p>
        )}

        <div className="mt-7 grid gap-6 xl:grid-cols-2">
          <section className="rounded-2xl border border-slate-800 bg-[#101827] p-6">
            <div className="flex items-center gap-3 border-b border-slate-800 pb-5">
              <Bot
                size={22}
                className="text-blue-400"
              />

              <div>
                <h2 className="text-lg font-semibold">
                  Agent Configuration
                </h2>

                <p className="mt-1 text-xs text-slate-400">
                  Planned multi-agent orchestration controls
                </p>
              </div>
            </div>

            <SettingToggle
              title="Security Analysis Agent"
              description="Preference for security event analysis and threat correlation."
              checked={settings.enableSecurityAgent}
              onChange={(value) =>
                updateBoolean(
                  "enableSecurityAgent",
                  value
                )
              }
            />

            <SettingToggle
              title="RAG Knowledge Agent"
              description="Preference for retrieval-augmented investigation context."
              checked={settings.enableRagAgent}
              onChange={(value) =>
                updateBoolean(
                  "enableRagAgent",
                  value
                )
              }
            />

            <SettingToggle
              title="Report Generation Agent"
              description="Preference for structured investigation report generation."
              checked={settings.enableReportAgent}
              onChange={(value) =>
                updateBoolean(
                  "enableReportAgent",
                  value
                )
              }
            />
          </section>

          <section className="rounded-2xl border border-slate-800 bg-[#101827] p-6">
            <div className="flex items-center gap-3 border-b border-slate-800 pb-5">
              <ShieldCheck
                size={22}
                className="text-emerald-400"
              />

              <div>
                <h2 className="text-lg font-semibold">
                  Security Controls
                </h2>

                <p className="mt-1 text-xs text-slate-400">
                  Planned backend-enforced protections
                </p>
              </div>
            </div>

            <SettingToggle
              title="Prompt Injection Protection"
              description="Requested protection against untrusted instructions in retrieved content."
              checked={
                settings.enablePromptInjectionProtection
              }
              onChange={(value) =>
                updateBoolean(
                  "enablePromptInjectionProtection",
                  value
                )
              }
            />

            <SettingToggle
              title="Audit Logging"
              description="Requested recording of investigation and agent execution events."
              checked={settings.enableAuditLogging}
              onChange={(value) =>
                updateBoolean(
                  "enableAuditLogging",
                  value
                )
              }
            />

            <SettingToggle
              title="Human Review"
              description="Preference to require analyst review before final approval."
              checked={settings.requireHumanReview}
              onChange={(value) =>
                updateBoolean(
                  "requireHumanReview",
                  value
                )
              }
            />
          </section>

          <section className="rounded-2xl border border-slate-800 bg-[#101827] p-6">
            <div className="flex items-center gap-3 border-b border-slate-800 pb-5">
              <SlidersHorizontal
                size={22}
                className="text-purple-400"
              />

              <div>
                <h2 className="text-lg font-semibold">
                  Investigation Preferences
                </h2>

                <p className="mt-1 text-xs text-slate-400">
                  Defaults for future backend integration
                </p>
              </div>
            </div>

            <div className="space-y-5 pt-5">
              <div>
                <label
                  htmlFor="severity-threshold"
                  className="mb-2 block text-sm font-medium"
                >
                  Default Severity Threshold
                </label>

                <select
                  id="severity-threshold"
                  value={
                    settings.defaultSeverityThreshold
                  }
                  onChange={(event) =>
                    updateSetting(
                      "defaultSeverityThreshold",
                      event.target.value as SecuritySettings["defaultSeverityThreshold"]
                    )
                  }
                  className="w-full rounded-xl border border-slate-700 bg-[#111e31] px-4 py-3 text-sm text-white outline-none focus:border-blue-500"
                >
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                  <option value="critical">
                    Critical
                  </option>
                </select>
              </div>

              <div>
                <label
                  htmlFor="max-events"
                  className="mb-2 block text-sm font-medium"
                >
                  Maximum Investigation Events
                </label>

                <input
                  id="max-events"
                  type="number"
                  min={1}
                  max={10000}
                  value={
                    settings.maxInvestigationEvents
                  }
                  onChange={(event) => {
                    const value = Number(
                      event.target.value
                    );

                    if (
                      Number.isInteger(value) &&
                      value >= 1 &&
                      value <= 10000
                    ) {
                      updateSetting(
                        "maxInvestigationEvents",
                        value
                      );
                    }
                  }}
                  className="w-full rounded-xl border border-slate-700 bg-[#111e31] px-4 py-3 text-sm text-white outline-none focus:border-blue-500"
                />
              </div>

              <SettingToggle
                title="Automatic Report Generation"
                description="Preference to generate reports after an investigation."
                checked={
                  settings.autoGenerateReport
                }
                onChange={(value) =>
                  updateBoolean(
                    "autoGenerateReport",
                    value
                  )
                }
              />
            </div>
          </section>

          <section className="rounded-2xl border border-slate-800 bg-[#101827] p-6">
            <div className="flex items-center gap-3 border-b border-slate-800 pb-5">
              <BrainCircuit
                size={22}
                className="text-blue-400"
              />

              <div>
                <h2 className="text-lg font-semibold">
                  System Information
                </h2>

                <p className="mt-1 text-xs text-slate-400">
                  Development environment
                </p>
              </div>
            </div>

            <div className="mt-5 space-y-4">
              {[
                [
                  "Application",
                  "SecureAgent AI",
                ],
                [
                  "Frontend",
                  "Next.js / React / TypeScript",
                ],
                [
                  "Backend",
                  "FastAPI / Python",
                ],
                [
                  "Database",
                  "PostgreSQL",
                ],
                [
                  "Authentication",
                  "JWT",
                ],
                [
                  "AI Architecture",
                  "Multi-Agent + RAG",
                ],
                [
                  "Environment",
                  "Development",
                ],
              ].map(([label, value]) => (
                <div
                  key={label}
                  className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 pb-3 text-sm last:border-0"
                >
                  <span className="text-slate-400">
                    {label}
                  </span>

                  <span className="font-medium text-slate-200">
                    {value}
                  </span>
                </div>
              ))}
            </div>

            <div className="mt-5 flex items-start gap-3 rounded-xl border border-slate-800 bg-[#111e31] p-4">
              <LockKeyhole
                size={20}
                className="shrink-0 text-emerald-400"
              />

              <p className="text-xs leading-6 text-slate-400">
                Backend authentication and security controls
                remain independent of these browser
                preferences.
              </p>
            </div>
          </section>
        </div>

        <div className="mt-6 flex flex-wrap gap-3">
          <Link
            href="/investigations"
            className="inline-flex items-center gap-2 rounded-xl border border-slate-700 px-4 py-2.5 text-sm text-slate-200 hover:bg-slate-800"
          >
            <FileText size={16} />
            Investigations
          </Link>

          <Link
            href="/analytics"
            className="inline-flex items-center gap-2 rounded-xl border border-slate-700 px-4 py-2.5 text-sm text-slate-200 hover:bg-slate-800"
          >
            <SlidersHorizontal size={16} />
            Security Analytics
          </Link>
        </div>
      </main>
    </div>
  );
}

export default function SettingsPage() {
  return (
    <ProtectedRoute>
      <SettingsWorkspace />
    </ProtectedRoute>
  );
}
