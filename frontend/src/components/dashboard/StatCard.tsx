import type { LucideIcon } from "lucide-react";
export function StatCard({
  label,
  value,
  icon: Icon,
  color,
}: {
  label: string;
  value: string | number;
  icon: LucideIcon;
  color: string;
}) {
  return (
    <div className="stat-card">
      <span className={`stat-icon ${color}`}>
        <Icon size={20} />
      </span>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
