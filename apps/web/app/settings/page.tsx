
"use client";

import {
  useEffect,
  useRef,
  useState,
} from "react";
import Link from "next/link";
import {
  ArrowLeft,
  Bot,
  BrainCircuit,
  Check,
  FileText,
  Loader2,
  LockKeyhole,
  RefreshCw,
  RotateCcw,
  Save,
  Settings2,
  ShieldCheck,
  SlidersHorizontal,
} from "lucide-react";

import Sidebar from "@/components/sidebar";
import ProtectedRoute from "@/components/protected-route";
import { useAuth } from "@/components/auth-provider";

import {
  DEFAULT_SETTINGS,
  getSettings,
  updateSettings,
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
  onChange?: (value: boolean) => void;
  disabled?: boolean;
};

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
        onClick={() => onChange?.(!checked)}
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

function SettingsContent() {
  const { token } = useAuth();

  const [settings, setSettings] =
    useState<SecuritySettings>(DEFAULT_SETTINGS);

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const requestId = useRef(0);

  useEffect(() => {
    if (!token) return;

    const id = ++requestId.current;
    let active = true;

    getSettings(token)
      .then((result) => {
        if (!active || id !== requestId.current) return;
        setSettings(result);
        setSaved(false);
        setError(null);
      })
      .catch((err: unknown) => {
        if (!active || id !== requestId.current) return;
        setError(
          err instanceof Error
            ? err.message
            : "Unable to load settings."
        );
      })
      .finally(() => {
        if (active && id === requestId.current) {
          setLoading(false);
        }
      });

    return () => {
      active = false;
      requestId.current += 1;
    };
  }, [token]);

  async function handleRefresh() {
    if (!token) return;

    const id = ++requestId.current;
    setLoading(true);
    setError(null);

    try {
      const result = await getSettings(token);
      if (id !== requestId.current) return;
      setSettings(result);
      setSaved(false);
    } catch (err) {
      if (id !== requestId.current) return;
      setError(
        err instanceof Error
          ? err.message
          : "Unable to load settings."
      );
    } finally {
      if (id === requestId.current) {
        setLoading(false);
      }
    }
  }

  function updateBoolean(
    key: BooleanKey,
    value: boolean
  ) {
    if (
      key === "enableAuditLogging" ||
      key === "enablePromptInjectionProtection"
    ) {
      return;
    }

    setSettings((current) => ({
      ...current,
      [key]: value,
    }));

    setSaved(false);
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
  }

  async function handleSave() {
    if (!token) {
      setError("You must be logged in.");
      return;
    }

    setSaving(true);
    setError(null);
    setSaved(false);

    try {
      const result = await updateSettings(
        token,
        settings
      );

      setSettings(result);
      setSaved(true);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to save settings."
      );
    } finally {
      setSaving(false);
    }
  }

  function handleReset() {
    setSettings({ ...DEFAULT_SETTINGS });
    setSaved(false);
    setError(null);
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-[#080d19] text-white">
        <Sidebar />
        <main className="min-h-screen px-5 pt-20 sm:px-8 lg:ml-64 lg:px-10 lg:pt-8">
          <div className="flex items-center gap-3 rounded-2xl border border-slate-800 bg-[#101827] p-8 text-slate-400">
            <Loader2
              size={20}
              className="animate-spin text-blue-400"
            />
            Loading settings from PostgreSQL...
          </div>
        </main>
      </div>
    );
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
                  Manage investigation preferences stored
                  securely in your account.
                </p>
              </div>
            </div>

            <div className="flex flex-wrap gap-3">
              <button
                type="button"
                onClick={() => void handleRefresh()}
                disabled={saving}
                className="inline-flex items-center gap-2 rounded-xl border border-slate-700 px-4 py-2.5 text-sm text-slate-300 hover:bg-slate-800 disabled:opacity-50"
              >
                <RefreshCw size={16} />
                Refresh
              </button>

              <button
                type="button"
                onClick={handleReset}
                disabled={saving}
                className="inline-flex items-center gap-2 rounded-xl border border-slate-700 px-4 py-2.5 text-sm text-slate-300 hover:bg-slate-800 disabled:opacity-50"
              >
                <RotateCcw size={16} />
                Reset
              </button>

              <button
                type="button"
                onClick={() => void handleSave()}
                disabled={saving || !token || loading}
                className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-50"
              >
                {saving ? (
                  <Loader2
                    size={17}
                    className="animate-spin"
                  />
                ) : saved ? (
                  <Check size={17} />
                ) : (
                  <Save size={17} />
                )}

                {saving
                  ? "Saving..."
                  : saved
                    ? "Saved"
                    : "Save Preferences"}
              </button>
            </div>
          </div>
        </header>

        <div className="mt-6 rounded-xl border border-blue-500/25 bg-blue-500/5 p-4 text-sm leading-6 text-blue-200">
          Preferences are saved in PostgreSQL for your
          authenticated account. Mandatory security controls
          cannot be changed from this page.
        </div>

        {error && (
          <div
            role="alert"
            className="mt-5 rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-300"
          >
            {error}
            <button
              type="button"
              onClick={() => void handleRefresh()}
              className="ml-3 font-semibold underline"
            >
              Retry
            </button>
          </div>
        )}

        <div className="mt-7 grid gap-6 xl:grid-cols-2">
          <section className="rounded-2xl border border-slate-800 bg-[#101827] p-6">
            <div className="flex items-center gap-3 border-b border-slate-800 pb-5">
              <Bot size={22} className="text-blue-400" />
              <div>
                <h2 className="text-lg font-semibold">
                  Agent Configuration
                </h2>
                <p className="mt-1 text-xs text-slate-400">
                  Investigation agent preferences
                </p>
              </div>
            </div>

            <SettingToggle
              title="Security Analysis Agent"
              description="Enable the security analysis agent preference."
              checked={settings.enableSecurityAgent}
              onChange={(value) =>
                updateBoolean("enableSecurityAgent", value)
              }
            />

            <SettingToggle
              title="RAG Knowledge Agent"
              description="Enable retrieval-augmented investigation context."
              checked={settings.enableRagAgent}
              onChange={(value) =>
                updateBoolean("enableRagAgent", value)
              }
            />

            <SettingToggle
              title="Report Generation Agent"
              description="Enable structured report generation preference."
              checked={settings.enableReportAgent}
              onChange={(value) =>
                updateBoolean("enableReportAgent", value)
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
                  Mandatory protections and review preferences
                </p>
              </div>
            </div>

            <SettingToggle
              title="Prompt Injection Protection"
              description="Mandatory backend security policy. Cannot be disabled."
              checked={
                settings.enablePromptInjectionProtection
              }
              disabled
            />

            <SettingToggle
              title="Audit Logging"
              description="Mandatory backend security policy. Cannot be disabled."
              checked={settings.enableAuditLogging}
              disabled
            />

            <SettingToggle
              title="Human Review"
              description="Require analyst review before final approval (preference)."
              checked={settings.requireHumanReview}
              onChange={(value) =>
                updateBoolean("requireHumanReview", value)
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
                  Saved configuration for future investigations
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
                  value={settings.defaultSeverityThreshold}
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
                  <option value="critical">Critical</option>
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
                  value={settings.maxInvestigationEvents}
                  onChange={(event) => {
                    const value = Number(event.target.value);
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
                description="Automatically generate a report after investigation (preference)."
                checked={settings.autoGenerateReport}
                onChange={(value) =>
                  updateBoolean("autoGenerateReport", value)
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
                  SecureAgent AI development environment
                </p>
              </div>
            </div>

            <div className="mt-5 space-y-4">
              {[
                ["Application", "SecureAgent AI"],
                ["Frontend", "Next.js / React / TypeScript"],
                ["Backend", "FastAPI / Python"],
                ["Database", "PostgreSQL"],
                ["Authentication", "JWT"],
                ["AI Architecture", "Multi-Agent + RAG"],
                ["Configuration", "Authenticated PostgreSQL API"],
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
                Settings are scoped to the authenticated user.
                Security-critical protections are not
                user-configurable.
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
      <SettingsContent />
    </ProtectedRoute>
  );
}
