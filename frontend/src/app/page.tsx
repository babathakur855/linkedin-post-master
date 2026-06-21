"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { BookText, CheckCircle, Clock, FileText, Plus, RefreshCw, Zap } from "lucide-react";
import { getBlogStats, getBlogs, getNiches, generateBlog, type Blog, type Stats, type Niche } from "@/lib/api";
import { timeAgo, FORMAT_LABELS } from "@/lib/utils";
import StatusBadge from "@/components/StatusBadge";

export default function Dashboard() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [recentBlogs, setRecentBlogs] = useState<Blog[]>([]);
  const [niches, setNiches] = useState<Niche[]>([]);
  const [generating, setGenerating] = useState<number | null>(null);

  const load = async () => {
    const [s, b, n] = await Promise.all([getBlogStats(), getBlogs({ }), getNiches()]);
    setStats(s);
    setRecentBlogs(b.slice(0, 5));
    setNiches(n);
  };

  useEffect(() => { load(); }, []);

  const handleGenerate = async (nicheId: number) => {
    setGenerating(nicheId);
    try {
      const { blog_id } = await generateBlog(nicheId);
      window.location.href = `/blogs/${blog_id}`;
    } catch (e) {
      alert(String(e));
    } finally {
      setGenerating(null);
    }
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-500 text-sm mt-1">AI-powered LinkedIn content pipeline</p>
        </div>
        <Link
          href="/niches"
          className="flex items-center gap-2 bg-[#0077b5] text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-[#004182] transition-colors"
        >
          <Plus className="w-4 h-4" />
          New Niche
        </Link>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[
            { label: "Total Blogs", value: stats.total, icon: BookText, color: "text-blue-600" },
            { label: "Published", value: stats.published, icon: CheckCircle, color: "text-green-600" },
            { label: "Pending Review", value: stats.pending_review, icon: Clock, color: "text-yellow-600" },
            { label: "In Progress", value: stats.drafts, icon: FileText, color: "text-purple-600" },
          ].map(({ label, value, icon: Icon, color }) => (
            <div key={label} className="bg-white rounded-xl border border-gray-200 p-5">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs text-gray-500 font-medium uppercase tracking-wide">{label}</span>
                <Icon className={`w-4 h-4 ${color}`} />
              </div>
              <p className="text-3xl font-bold text-gray-900">{value}</p>
            </div>
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Active Niches */}
        <div className="bg-white rounded-xl border border-gray-200">
          <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
            <h2 className="font-semibold text-gray-900">Active Niches</h2>
            <Link href="/niches" className="text-xs text-[#0077b5] hover:underline">Manage →</Link>
          </div>
          <div className="divide-y divide-gray-100">
            {niches.length === 0 && (
              <div className="px-5 py-8 text-center text-gray-400 text-sm">
                No niches yet — <Link href="/niches" className="text-[#0077b5] hover:underline">add one</Link>
              </div>
            )}
            {niches.slice(0, 5).map((n) => (
              <div key={n.id} className="flex items-center justify-between px-5 py-3">
                <div>
                  <p className="text-sm font-medium text-gray-900">{n.name}</p>
                  <p className="text-xs text-gray-500 capitalize">{n.frequency} · {n.schedule_time} · {FORMAT_LABELS[n.publish_format]}</p>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`w-2 h-2 rounded-full ${n.active ? "bg-green-500" : "bg-gray-300"}`} />
                  {n.active && (
                    <button
                      onClick={() => handleGenerate(n.id)}
                      disabled={generating === n.id}
                      className="flex items-center gap-1 text-xs bg-[#e8f4fd] text-[#0077b5] px-2.5 py-1 rounded-md hover:bg-[#0077b5] hover:text-white transition-colors disabled:opacity-50"
                    >
                      {generating === n.id ? (
                        <RefreshCw className="w-3 h-3 animate-spin" />
                      ) : (
                        <Zap className="w-3 h-3" />
                      )}
                      Generate
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Recent Blogs */}
        <div className="bg-white rounded-xl border border-gray-200">
          <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
            <h2 className="font-semibold text-gray-900">Recent Blogs</h2>
            <Link href="/blogs" className="text-xs text-[#0077b5] hover:underline">View all →</Link>
          </div>
          <div className="divide-y divide-gray-100">
            {recentBlogs.length === 0 && (
              <div className="px-5 py-8 text-center text-gray-400 text-sm">
                No blogs yet — generate one above
              </div>
            )}
            {recentBlogs.map((b) => (
              <Link key={b.id} href={`/blogs/${b.id}`} className="flex items-center justify-between px-5 py-3 hover:bg-gray-50 transition-colors">
                <div className="min-w-0 flex-1 mr-3">
                  <p className="text-sm font-medium text-gray-900 truncate">{b.title || b.topic || "Untitled"}</p>
                  <p className="text-xs text-gray-500">{timeAgo(b.created_at)}</p>
                </div>
                <StatusBadge status={b.status} />
              </Link>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
