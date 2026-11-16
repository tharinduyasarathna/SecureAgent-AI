
"use client";

import {
  Activity,
  BrainCircuit,
  ChevronRight,
  ClipboardList,
  FileSearch,
  History,
  LayoutDashboard,
  LogOut,
  Menu,
  Settings,
  ShieldCheck,
  X,
  BarChart3,
} from "lucide-react";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";

import { useAuth } from "@/components/auth-provider";

const navigation = [
  {
    name: "Dashboard",
    href: "/",
    icon: LayoutDashboard,
  },
  {
    name: "Investigations",
    href: "/investigations",
    icon: FileSearch,
  },
  {
    name: "Reports",
    href: "/reports",
    icon: ClipboardList,
  },
  {
    name: "History",
    href: "/history",
    icon: History,
  },
  {
    name: "Settings",
    href: "/settings",
    icon: Settings,
  },
  {
  name: "Analytics",
  href: "/analytics",
  icon: BarChart3,
},
];

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const { user, logout } = useAuth();

  function handleLogout() {
    logout();
    setOpen(false);
    router.replace("/login");
  }

  return (
    <>
      <button
        type="button"
        aria-label="Open navigation"
        onClick={() => setOpen(true)}
        className="fixed left-4 top-4 z-30 rounded-xl border border-slate-700 bg-slate-900 p-3 text-white lg:hidden"
      >
        <Menu size={20} />
      </button>

      {open && (
        <button
          type="button"
          aria-label="Close navigation"
          className="fixed inset-0 z-40 bg-black/70 lg:hidden"
          onClick={() => setOpen(false)}
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-50 flex w-64 flex-col overflow-y-auto overscroll-contain border-r border-slate-800 bg-[#0b1220] transition-transform lg:translate-x-0 ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex h-20 shrink-0 items-center justify-between border-b border-slate-800 px-5">
          <Link
            href="/"
            className="flex items-center gap-3"
            onClick={() => setOpen(false)}
          >
            <div className="rounded-xl bg-blue-600/20 p-2 text-blue-400">
              <ShieldCheck size={27} />
            </div>

            <div>
              <div className="text-lg font-bold tracking-tight">
                SecureAgent
                <span className="text-blue-400"> AI</span>
              </div>

              <div className="text-xs text-slate-500">
                Security Intelligence
              </div>
            </div>
          </Link>

          <button
            type="button"
            aria-label="Close navigation"
            className="text-slate-400 lg:hidden"
            onClick={() => setOpen(false)}
          >
            <X size={20} />
          </button>
        </div>

        <div className="shrink-0 px-4 pt-7">
          <p className="px-3 text-xs font-semibold uppercase tracking-widest text-slate-500">
            Workspace
          </p>

          <nav className="mt-4 space-y-1">
            {navigation.map((item) => {
              const Icon = item.icon;

              const active =
                pathname === item.href ||
                (item.href !== "/" &&
                  pathname.startsWith(`${item.href}/`));

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={() => setOpen(false)}
                  className={`flex items-center gap-3 rounded-xl px-3 py-3 text-sm transition ${
                    active
                      ? "bg-blue-600/15 font-semibold text-blue-400"
                      : "text-slate-400 hover:bg-slate-800 hover:text-white"
                  }`}
                >
                  <Icon size={19} />

                  <span className="flex-1">
                    {item.name}
                  </span>

                  {active && (
                    <ChevronRight size={16} />
                  )}
                </Link>
              );
            })}
          </nav>
        </div>

        <div className="mt-9 shrink-0 px-4">
          <p className="px-3 text-xs font-semibold uppercase tracking-widest text-slate-500">
            AI Platform
          </p>

          <div className="mt-4 space-y-3 rounded-xl border border-slate-800 bg-slate-900/50 p-4">
            <div className="flex items-center gap-3 text-sm text-slate-300">
              <BrainCircuit
                size={17}
                className="text-blue-400"
              />
              Multi-Agent System
            </div>

            <div className="flex items-center gap-3 text-sm text-slate-300">
              <Activity
                size={17}
                className="text-emerald-400"
              />
              Threat Analysis
            </div>

            <div className="flex items-center gap-3 text-sm text-slate-300">
              <ShieldCheck
                size={17}
                className="text-purple-400"
              />
              Security Controls
            </div>
          </div>
        </div>

        <div className="mt-auto shrink-0 pt-8">
          <div className="border-t border-slate-800 p-5">
            <div className="rounded-xl bg-slate-900 p-4">
              <div className="flex items-center gap-2 text-sm font-semibold">
                <ShieldCheck
                  size={17}
                  className="text-emerald-400"
                />
                SecureAgent AI
              </div>

              <p className="mt-2 text-xs leading-5 text-slate-500">
                AI-assisted security investigation platform
              </p>
            </div>
          </div>

          <div className="border-t border-slate-800 px-4 pb-6 pt-5">
            <div className="mb-4 flex items-center gap-3 rounded-xl bg-slate-900 p-3">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-blue-600/20 text-sm font-bold text-blue-400">
                {user?.email?.charAt(0).toUpperCase() ?? "U"}
              </div>

              <div className="min-w-0 flex-1">
                <p className="text-xs text-slate-500">
                  Signed in as
                </p>

                <p
                  className="truncate text-sm font-medium text-slate-200"
                  title={user?.email ?? ""}
                >
                  {user?.email ?? "User"}
                </p>
              </div>
            </div>

            <button
              type="button"
              onClick={handleLogout}
              className="flex w-full items-center gap-3 rounded-xl px-3 py-3 text-sm font-medium text-red-400 transition hover:bg-red-500/10 hover:text-red-300"
            >
              <LogOut size={19} />
              Sign Out
            </button>
          </div>
        </div>
      </aside>
    </>
  );
}
