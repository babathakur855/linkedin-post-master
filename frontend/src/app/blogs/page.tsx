"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getBlogs, getNiches, generateBlog, type Blog, type Niche } from "@/lib/api";
import { timeAgo, STATUS_LABELS } from "@/lib/utils";
import StatusBadge from "@/components/StatusBadge";
import { ExternalLink, RefreshCw, Zap } from "lucide-react";

const STATUS_FILTERS = ["all", "review_pending", "published", "writing", "researching", "failed"];

export default function BlogsPage() {
  const [blogs, setBlogs] = useState<Blog[]>([]);
  const [niches, setNiches] = useState<Niche[]>([]);
  const [filter, setFilter] = useState("all");
  const [nicheFilter, setNicheFilter] = useState<number | undefined>();
  const [generating, setGenerating] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    const [b, n] = await Promise.all([
      getBlogs({ status: filter !== "all" ? filter : undefined, niche_id: nicheFilter }),
      getNiches(),
    ]);
    setBlogs(b);
    setNiches(n);
    setLoading(false);
  };

  useEffect(() => { load(); }, [filter, nicheFilter]);

  const handleGenerate = async (nicheId: number) => {
    setGenerating(nicheId);
    try {
      const { blog_id } = await generateBlog(nicheId);
      window.location.href = `/blogs/${blog_id}`;
    } catch (e) { alert(String(e)); }
    finally { setGenerating(null); }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Blogs & Articles</h1>
          <p className="text-gray-500 text-sm mt-1">All generated content and their status</p>
        </div>
        <div className="flex gap-2">
          {niches.slice(0, 3).map((n) => (
            <button
              key={n.id}
              onClick={() => handleGenerate(n.id)}
              disabled={generating === n.id}
              className="flex items-center gap-1 text-sm bg-[#0077b5] text-white px-3 py-2 rounded-lg hover:bg-[#004182] disabled:opacity-50 transition-colors"
            >
              {generating === n.id ? <RefreshCw className="w-3 h-3 animate-spin" /> : <Zap className="w-3 h-3" />}
              {n.name}
            </button>
          ))}
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 items-center">
        <div className="flex gap-1 bg-gray-100 p-1 rounded-lg">
          {STATUS_FILTERS.map((s) => (
            <button
              key={s}
              onClick={() => setFilter(s)}
              className={`px-3 py-1 rounded-md text-sm font-medium transition-colors ${
                filter === s ? "bg-white shadow-sm text-gray-900" : "text-gray-500 hover:text-gray-700"
              }`}
            >
              {s === "all" ? "All" : STATUS_LABELS[s] || s}
            </button>
          ))}
        </div>

        {niches.length > 0 && (
          <select
            className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm bg-white"
            value={nicheFilter ?? ""}
            onChange={(e) => setNicheFilter(e.target.value ? Number(e.target.value) : undefined)}
          >
            <option value="">All Niches</option>
            {niches.map((n) => <option key={n.id} value={n.id}>{n.name}</option>)}
          </select>
        )}

        <button onClick={load} className="ml-auto text-gray-400 hover:text-gray-600">
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {/* Blog List */}
      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="bg-white rounded-xl border border-gray-200 p-5 animate-pulse">
              <div className="h-4 bg-gray-200 rounded w-1/2 mb-2" />
              <div className="h-3 bg-gray-100 rounded w-1/4" />
            </div>
          ))}
        </div>
      ) : blogs.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
          <p className="text-gray-400">No blogs found for the current filter</p>
        </div>
      ) : (
        <div className="space-y-3">
          {blogs.map((b) => (
            <Link
              key={b.id}
              href={`/blogs/${b.id}`}
              className="block bg-white rounded-xl border border-gray-200 p-5 hover:border-[#0077b5] hover:shadow-sm transition-all"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <StatusBadge status={b.status} />
                    <span className="text-xs text-gray-400 bg-gray-100 px-2 py-0.5 rounded capitalize">
                      {b.publish_format}
                    </span>
                  </div>
                  <h3 className="font-semibold text-gray-900 truncate">{b.title || b.topic || "Generating..."}</h3>
                  <p className="text-xs text-gray-500 mt-1">{timeAgo(b.created_at)}</p>
                </div>
                {b.published_url && (
                  <a
                    href={b.published_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={(e) => e.stopPropagation()}
                    className="flex items-center gap-1 text-xs text-[#0077b5] hover:underline shrink-0"
                  >
                    <ExternalLink className="w-3 h-3" />
                    View on LinkedIn
                  </a>
                )}
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
