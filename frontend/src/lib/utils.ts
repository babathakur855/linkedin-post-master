import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import { formatDistanceToNow, format } from "date-fns";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function timeAgo(dateStr: string): string {
  return formatDistanceToNow(new Date(dateStr), { addSuffix: true });
}

export function formatDate(dateStr: string): string {
  return format(new Date(dateStr), "MMM d, yyyy HH:mm");
}

export const STATUS_LABELS: Record<string, string> = {
  draft: "Draft",
  researching: "Researching",
  writing: "Writing",
  review_pending: "Pending Review",
  changes_requested: "Changes Requested",
  approved: "Approved",
  published: "Published",
  failed: "Failed",
};

export const STATUS_COLORS: Record<string, string> = {
  draft: "bg-gray-100 text-gray-700",
  researching: "bg-blue-100 text-blue-700",
  writing: "bg-purple-100 text-purple-700",
  review_pending: "bg-yellow-100 text-yellow-700",
  changes_requested: "bg-orange-100 text-orange-700",
  approved: "bg-green-100 text-green-700",
  published: "bg-linkedin-blue text-white",
  failed: "bg-red-100 text-red-700",
};

export const FORMAT_LABELS: Record<string, string> = {
  post: "Post",
  article: "Article",
};

export const FREQUENCY_OPTIONS = [
  { value: "daily", label: "Daily" },
  { value: "weekly", label: "Weekly" },
  { value: "biweekly", label: "Bi-weekly" },
  { value: "monthly", label: "Monthly" },
];

export const DAY_OPTIONS = [
  { value: 0, label: "Monday" },
  { value: 1, label: "Tuesday" },
  { value: 2, label: "Wednesday" },
  { value: 3, label: "Thursday" },
  { value: 4, label: "Friday" },
  { value: 5, label: "Saturday" },
  { value: 6, label: "Sunday" },
];
