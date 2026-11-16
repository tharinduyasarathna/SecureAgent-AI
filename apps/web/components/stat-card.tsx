
import type { LucideIcon } from "lucide-react";

type StatCardProps = {
  title: string;
  value: string | number;
  description: string;
  icon: LucideIcon;
  color?: "blue" | "green" | "red" | "purple";
};

const colors = {
  blue: "bg-blue-500/10 text-blue-400",
  green: "bg-emerald-500/10 text-emerald-400",
  red: "bg-red-500/10 text-red-400",
  purple: "bg-purple-500/10 text-purple-400",
};

export default function StatCard({
  title,
  value,
  description,
  icon: Icon,
  color = "blue",
}: StatCardProps) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-[#101827] p-5">
      <div className="flex items-start justify-between">
        <p className="text-sm font-medium text-slate-400">
          {title}
        </p>

        <div className={`rounded-xl p-3 ${colors[color]}`}>
          <Icon size={20} />
        </div>
      </div>

      <div className="mt-5 text-3xl font-bold tracking-tight text-white">
        {value}
      </div>

      <p className="mt-2 text-xs text-slate-500">
        {description}
      </p>
    </div>
  );
}
