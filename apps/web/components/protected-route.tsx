
"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { ShieldCheck } from "lucide-react";

import { useAuth } from "./auth-provider";

export default function ProtectedRoute({
  children,
}: {
  children: React.ReactNode;
}) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      router.replace("/login");
    }
  }, [loading, user, router]);

  if (loading || !user) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#080d19]">
        <div className="text-center">
          <ShieldCheck
            size={38}
            className="mx-auto animate-pulse text-blue-400"
          />
          <p className="mt-4 text-sm text-slate-400">
            Verifying your session...
          </p>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
