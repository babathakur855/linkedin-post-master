"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import dynamic from "next/dynamic";
import type { Components } from "react-markdown";

const MermaidDiagram = dynamic(() => import("./MermaidDiagram"), { ssr: false });

interface Props {
  markdown: string;
}

export default function BlogContent({ markdown }: Props) {
  const components: Components = {
    // Intercept code blocks — render mermaid ones as diagrams
    code({ className, children }) {
      const lang = /language-(\w+)/.exec(className || "")?.[1];
      const code = String(children).replace(/\n$/, "");

      if (lang === "mermaid") {
        return <MermaidDiagram code={code} />;
      }

      return (
        <code className="bg-gray-100 rounded px-1 py-0.5 text-sm font-mono">{code}</code>
      );
    },
    pre({ children }) {
      return <div className="my-4">{children}</div>;
    },
    // Strip visual placeholder comments — they render as text in MD
    p({ children }) {
      const text = typeof children === "string" ? children : "";
      if (text.startsWith("<!-- VISUAL:")) return null;
      return <p className="mb-3 leading-relaxed">{children}</p>;
    },
  };

  return (
    <div className="blog-content">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {markdown}
      </ReactMarkdown>
    </div>
  );
}
