import { cn, STATUS_COLORS, STATUS_LABELS } from "@/lib/utils";

interface Props {
  status: string;
  className?: string;
}

export default function StatusBadge({ status, className }: Props) {
  return (
    <span
      className={cn(
        "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium",
        STATUS_COLORS[status] || "bg-gray-100 text-gray-700",
        className
      )}
    >
      {STATUS_LABELS[status] || status}
    </span>
  );
}
