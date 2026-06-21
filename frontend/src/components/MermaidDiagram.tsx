"use client";

import { useEffect, useRef, useState } from "react";

interface Props {
  code: string;
}

export default function MermaidDiagram({ code }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [rendered, setRendered] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function render() {
      try {
        const mermaid = (await import("mermaid")).default;
        mermaid.initialize({
          startOnLoad: false,
          theme: "base",
          themeVariables: { primaryColor: "#0077b5", primaryTextColor: "#fff" },
        });

        const id = `mermaid-${Math.random().toString(36).slice(2)}`;
        const { svg } = await mermaid.render(id, code.trim());
        if (!cancelled && ref.current) {
          ref.current.innerHTML = svg;
          setRendered(true);
        }
      } catch (e: unknown) {
        if (!cancelled) setError(String(e));
      }
    }

    render();
    return () => { cancelled = true; };
  }, [code]);

  if (error) {
    return (
      <pre className="bg-red-50 border border-red-200 rounded p-3 text-xs text-red-700 overflow-x-auto">
        {code}
        {"\n// Render error: "}{error}
      </pre>
    );
  }

  return (
    <div
      ref={ref}
      className="mermaid-container my-4 flex justify-center bg-white border border-gray-100 rounded-lg p-4 overflow-x-auto"
    >
      {!rendered && (
        <pre className="text-xs text-gray-400 bg-gray-50 p-4 rounded w-full">{code}</pre>
      )}
    </div>
  );
}
