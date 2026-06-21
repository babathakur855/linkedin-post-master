"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  getBlog, approveBlog, reviseBlog, deleteBlog, createBlogWebSocket, type Blog,
} from "@/lib/api";
import { formatDate, FORMAT_LABELS } from "@/lib/utils";
import StatusBadge from "@/components/StatusBadge";
import BlogContent from "@/components/BlogContent";
import GenerationLog from "@/components/GenerationLog";
import {
  ArrowLeft, CheckCircle, MessageSquare, RefreshCw, Trash2, ExternalLink, Copy, Check,
} from "lucide-react";

export default function BlogDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const blogId = Number(id);

  const [blog, setBlog] = useState<Blog | null>(null);
  const [tab, setTab] = useState<"preview" | "linkedin_post" | "article" | "logs">("preview");
  const [revisionText, setRevisionText] = useState("");
  const [showRevisionBox, setShowRevisionBox] = useState(false);
  const [loading, setLoading] = useState(true);
  const [actionBusy, setActionBusy] = useState(false);
  const [copied, setCopied] = useState(false);
  const [streamingLogs, setStreamingLogs] = useState<Blog["logs"]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  const load = async () => {
    setLoading(true);
    const b = await getBlog(blogId);
    setBlog(b);
    setLoading(false);
  };

  useEffect(() => {
    load();
  }, [blogId]);

  // Connect WebSocket when blog is in an active generation state
  useEffect(() => {
    if (!blog) return;
    const activeStatuses = ["researching", "writing", "changes_requested"];
    if (!activeStatuses.includes(blog.status)) return;

    setIsStreaming(true);
    const ws = createBlogWebSocket(blogId, (data) => {
      if (data.type === "log" && data.phase && data.message) {
        setStreamingLogs((prev) => [
          ...(prev || []),
          { phase: data.phase!, message: data.message!, created_at: new Date().toISOString() },
        ]);
      }
      if (data.type === "log" && (data.phase === "done" || data.phase === "error")) {
        setIsStreaming(false);
        setTimeout(load, 1500);
      }
    });
    wsRef.current = ws;

    // Poll for updates every 10s as fallback
    const poll = setInterval(load, 10_000);

    return () => {
      ws.close();
      clearInterval(poll);
      setIsStreaming(false);
    };
  }, [blog?.status]);

  const handleApprove = async () => {
    setActionBusy(true);
    try {
      await approveBlog(blogId);
      await load();
    } catch (e) { alert(String(e)); }
    finally { setActionBusy(false); }
  };

  const handleRevise = async () => {
    if (!revisionText.trim()) return;
    setActionBusy(true);
    try {
      await reviseBlog(blogId, revisionText);
      setRevisionText("");
      setShowRevisionBox(false);
      await load();
    } catch (e) { alert(String(e)); }
    finally { setActionBusy(false); }
  };

  const handleDelete = async () => {
    if (!confirm("Delete this blog permanently?")) return;
    await deleteBlog(blogId);
    router.push("/blogs");
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (loading) {
    return (
      <div className="animate-pulse space-y-4">
        <div className="h-8 bg-gray-200 rounded w-1/3" />
        <div className="h-4 bg-gray-100 rounded w-1/4" />
        <div className="h-64 bg-gray-100 rounded" />
      </div>
    );
  }

  if (!blog) return <div className="text-gray-500">Blog not found</div>;

  const allLogs = [...(blog.logs || []), ...(streamingLogs || [])];

  return (
    <div className="space-y-6 max-w-5xl">
      {/* Back + Header */}
      <div>
        <button
          onClick={() => router.back()}
          className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-4"
        >
          <ArrowLeft className="w-4 h-4" /> Back
        </button>

        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-2">
              <StatusBadge status={blog.status} />
              <span className="text-xs text-gray-400 bg-gray-100 px-2 py-0.5 rounded capitalize">
                {FORMAT_LABELS[blog.publish_format] || blog.publish_format}
              </span>
              {blog.revision_count > 0 && (
                <span className="text-xs text-orange-600 bg-orange-50 px-2 py-0.5 rounded">
                  Rev #{blog.revision_count}
                </span>
              )}
            </div>
            <h1 className="text-2xl font-bold text-gray-900">{blog.title || blog.topic || "Generating..."}</h1>
            <p className="text-sm text-gray-500 mt-1">Created {formatDate(blog.created_at)}</p>
            {blog.research_summary && (
              <p className="text-xs text-gray-400 mt-1">Research: {blog.research_summary}</p>
            )}
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2 shrink-0">
            {blog.published_url && (
              <a
                href={blog.published_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 text-sm text-[#0077b5] bg-[#e8f4fd] px-3 py-2 rounded-lg hover:bg-[#0077b5] hover:text-white transition-colors"
              >
                <ExternalLink className="w-4 h-4" /> View on LinkedIn
              </a>
            )}
            {["review_pending", "draft", "changes_requested"].includes(blog.status) && (
              <>
                <button
                  onClick={handleApprove}
                  disabled={actionBusy}
                  className="flex items-center gap-1 text-sm bg-green-600 text-white px-3 py-2 rounded-lg hover:bg-green-700 disabled:opacity-50 transition-colors"
                >
                  <CheckCircle className="w-4 h-4" />
                  {actionBusy ? "Publishing..." : "Approve & Publish"}
                </button>
                <button
                  onClick={() => setShowRevisionBox(!showRevisionBox)}
                  className="flex items-center gap-1 text-sm bg-orange-100 text-orange-700 px-3 py-2 rounded-lg hover:bg-orange-200 transition-colors"
                >
                  <MessageSquare className="w-4 h-4" /> Request Changes
                </button>
              </>
            )}
            <button
              onClick={handleDelete}
              className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Revision Box */}
      {showRevisionBox && (
        <div className="bg-orange-50 border border-orange-200 rounded-xl p-4 space-y-3">
          <label className="block text-sm font-medium text-orange-800">
            Describe the changes you want:
          </label>
          <textarea
            className="w-full border border-orange-200 rounded-lg px-3 py-2 text-sm resize-none h-24 focus:outline-none focus:ring-2 focus:ring-orange-400"
            placeholder="e.g. Add more statistics, change the tone to be more technical, include a comparison table of top tools..."
            value={revisionText}
            onChange={(e) => setRevisionText(e.target.value)}
          />
          <div className="flex gap-2">
            <button
              onClick={handleRevise}
              disabled={actionBusy || !revisionText.trim()}
              className="flex items-center gap-1 text-sm bg-orange-600 text-white px-4 py-2 rounded-lg hover:bg-orange-700 disabled:opacity-50"
            >
              <RefreshCw className="w-4 h-4" /> Submit for Revision
            </button>
            <button onClick={() => setShowRevisionBox(false)} className="text-sm text-gray-500 px-4 py-2 hover:bg-gray-100 rounded-lg">
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Streaming log during generation */}
      {isStreaming && (
        <GenerationLog logs={streamingLogs || []} streaming={isStreaming} />
      )}

      {/* Content Tabs */}
      {blog.content_markdown && (
        <div className="bg-white rounded-xl border border-gray-200">
          {/* Tab Headers */}
          <div className="flex border-b border-gray-200 overflow-x-auto">
            {([
              { key: "preview", label: "Full Blog Preview" },
              { key: "linkedin_post", label: "LinkedIn Post" },
              { key: "article", label: "LinkedIn Article" },
              { key: "logs", label: `Logs (${allLogs.length})` },
            ] as const).map(({ key, label }) => (
              <button
                key={key}
                onClick={() => setTab(key)}
                className={`px-4 py-3 text-sm font-medium whitespace-nowrap border-b-2 transition-colors ${
                  tab === key
                    ? "border-[#0077b5] text-[#0077b5]"
                    : "border-transparent text-gray-500 hover:text-gray-700"
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          {/* Tab Content */}
          <div className="p-6">
            {tab === "preview" && (
              <BlogContent markdown={blog.content_markdown} />
            )}

            {tab === "linkedin_post" && (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <p className="text-sm text-gray-500">LinkedIn Post ({blog.linkedin_post?.length || 0} chars)</p>
                  <button
                    onClick={() => copyToClipboard(blog.linkedin_post || "")}
                    className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700"
                  >
                    {copied ? <Check className="w-3 h-3 text-green-600" /> : <Copy className="w-3 h-3" />}
                    {copied ? "Copied!" : "Copy"}
                  </button>
                </div>
                <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                  <pre className="whitespace-pre-wrap text-sm text-gray-800 font-sans">{blog.linkedin_post}</pre>
                </div>
              </div>
            )}

            {tab === "article" && (
              <div className="space-y-3">
                <div className="bg-[#e8f4fd] rounded-lg p-4">
                  <p className="text-xs text-[#0077b5] font-medium mb-1">Article Title</p>
                  <p className="font-semibold text-gray-900">{blog.linkedin_article_title || blog.title}</p>
                </div>
                {blog.linkedin_article_body && (
                  <BlogContent markdown={blog.linkedin_article_body} />
                )}
              </div>
            )}

            {tab === "logs" && (
              <GenerationLog logs={allLogs} streaming={isStreaming} />
            )}
          </div>
        </div>
      )}

      {/* Revision History */}
      {blog.revisions && blog.revisions.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="font-semibold text-gray-900 mb-3">Revision History</h2>
          <div className="space-y-2">
            {blog.revisions.map((r) => (
              <div key={r.id} className="flex items-start gap-3 text-sm py-2 border-b last:border-0 border-gray-100">
                <span className="text-xs text-gray-400 whitespace-nowrap mt-0.5">{formatDate(r.created_at)}</span>
                <span className="text-orange-600 font-medium">Rev #{r.revision_number}</span>
                <span className="text-gray-600">{r.changes_requested}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
