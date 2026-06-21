"use client";

import { useEffect, useRef } from "react";
import { formatDate } from "@/lib/utils";

interface LogEntry {
  phase: string;
  message: string;
  created_at: string;
}

interface Props {
  logs: LogEntry[];
  streaming?: boolean;
}

const PHASE_ICONS: Record<string, string> = {
  research: "🔍",
  writing: "✍️",
  visuals: "📊",
  email: "📧",
  revision: "🔄",
  publish: "🚀",
  done: "✅",
  error: "❌",
  warning: "⚠️",
};

export default function GenerationLog({ logs, streaming }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  if (!logs?.length && !streaming) return null;

  return (
    <div className="bg-gray-900 rounded-lg p-4 font-mono text-sm max-h-64 overflow-y-auto">
      {logs.map((log, i) => (
        <div key={i} className="flex gap-3 py-1 border-b border-gray-800 last:border-0">
          <span className="text-gray-500 text-xs whitespace-nowrap mt-0.5">
            {formatDate(log.created_at)}
          </span>
          <span className="text-blue-400">[{log.phase}]</span>
          <span className="text-green-300 flex-1">
            {PHASE_ICONS[log.phase] || "→"} {log.message}
          </span>
        </div>
      ))}
      {streaming && (
        <div className="flex gap-2 py-1 text-yellow-400 animate-pulse">
          <span>⟳</span>
          <span>Processing...</span>
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  );
}
