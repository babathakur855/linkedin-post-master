"use client";

import { useEffect, useState } from "react";
import { Plus, Pencil, Trash2, Zap, X, Check } from "lucide-react";
import { getNiches, createNiche, updateNiche, deleteNiche, generateBlog, type Niche } from "@/lib/api";
import { FREQUENCY_OPTIONS, DAY_OPTIONS, FORMAT_LABELS } from "@/lib/utils";

const EMPTY: Partial<Niche> = {
  name: "", description: "", keywords: [], frequency: "weekly",
  schedule_day: 1, schedule_time: "09:00", publish_format: "post", active: true,
};

export default function NichesPage() {
  const [niches, setNiches] = useState<Niche[]>([]);
  const [editing, setEditing] = useState<Partial<Niche> | null>(null);
  const [isNew, setIsNew] = useState(false);
  const [saving, setSaving] = useState(false);
  const [kwInput, setKwInput] = useState("");

  const load = async () => setNiches(await getNiches());
  useEffect(() => { load(); }, []);

  const openNew = () => { setEditing({ ...EMPTY }); setIsNew(true); setKwInput(""); };
  const openEdit = (n: Niche) => { setEditing({ ...n }); setIsNew(false); setKwInput(""); };
  const closeForm = () => { setEditing(null); setIsNew(false); };

  const addKeyword = () => {
    const kw = kwInput.trim();
    if (!kw || !editing) return;
    setEditing({ ...editing, keywords: [...(editing.keywords || []), kw] });
    setKwInput("");
  };
  const removeKeyword = (kw: string) =>
    setEditing({ ...editing!, keywords: (editing!.keywords || []).filter((k) => k !== kw) });

  const save = async () => {
    if (!editing) return;
    setSaving(true);
    try {
      if (isNew) {
        await createNiche(editing);
      } else {
        await updateNiche(editing.id!, editing);
      }
      closeForm();
      await load();
    } catch (e) { alert(String(e)); }
    finally { setSaving(false); }
  };

  const remove = async (id: number) => {
    if (!confirm("Delete this niche?")) return;
    await deleteNiche(id);
    await load();
  };

  const generate = async (id: number) => {
    try {
      const { blog_id } = await generateBlog(id);
      window.location.href = `/blogs/${blog_id}`;
    } catch (e) { alert(String(e)); }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Niches</h1>
          <p className="text-gray-500 text-sm mt-1">Configure topics and publishing schedules</p>
        </div>
        <button
          onClick={openNew}
          className="flex items-center gap-2 bg-[#0077b5] text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-[#004182] transition-colors"
        >
          <Plus className="w-4 h-4" /> Add Niche
        </button>
      </div>

      {/* Form */}
      {editing && (
        <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
          <h2 className="font-semibold text-gray-900">{isNew ? "New Niche" : `Edit: ${editing.name}`}</h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Niche Name *</label>
              <input
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#0077b5]"
                value={editing.name || ""}
                onChange={(e) => setEditing({ ...editing, name: e.target.value })}
                placeholder="e.g. Generative AI, Cloud Architecture"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
              <input
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#0077b5]"
                value={editing.description || ""}
                onChange={(e) => setEditing({ ...editing, description: e.target.value })}
                placeholder="Brief description of the niche"
              />
            </div>
          </div>

          {/* Keywords */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Keywords</label>
            <div className="flex gap-2">
              <input
                className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#0077b5]"
                value={kwInput}
                onChange={(e) => setKwInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && addKeyword()}
                placeholder="Add keyword and press Enter"
              />
              <button onClick={addKeyword} className="bg-gray-100 px-3 py-2 rounded-lg text-sm hover:bg-gray-200">
                Add
              </button>
            </div>
            <div className="flex flex-wrap gap-2 mt-2">
              {(editing.keywords || []).map((kw) => (
                <span key={kw} className="flex items-center gap-1 bg-[#e8f4fd] text-[#0077b5] text-xs px-2.5 py-1 rounded-full">
                  {kw}
                  <button onClick={() => removeKeyword(kw)}><X className="w-3 h-3" /></button>
                </span>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Frequency</label>
              <select
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#0077b5]"
                value={editing.frequency}
                onChange={(e) => setEditing({ ...editing, frequency: e.target.value })}
              >
                {FREQUENCY_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>

            {(editing.frequency === "weekly" || editing.frequency === "biweekly") && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Day of Week</label>
                <select
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#0077b5]"
                  value={editing.schedule_day ?? 0}
                  onChange={(e) => setEditing({ ...editing, schedule_day: Number(e.target.value) })}
                >
                  {DAY_OPTIONS.map((d) => (
                    <option key={d.value} value={d.value}>{d.label}</option>
                  ))}
                </select>
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Time (24h)</label>
              <input
                type="time"
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#0077b5]"
                value={editing.schedule_time || "09:00"}
                onChange={(e) => setEditing({ ...editing, schedule_time: e.target.value })}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Default Format</label>
              <select
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#0077b5]"
                value={editing.publish_format}
                onChange={(e) => setEditing({ ...editing, publish_format: e.target.value })}
              >
                <option value="post">LinkedIn Post (short)</option>
                <option value="article">LinkedIn Article (long-form)</option>
                <option value="both">Both Post + Article</option>
              </select>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <label className="flex items-center gap-2 text-sm font-medium text-gray-700">
              <input
                type="checkbox"
                checked={editing.active ?? true}
                onChange={(e) => setEditing({ ...editing, active: e.target.checked })}
                className="rounded"
              />
              Active (auto-schedule enabled)
            </label>
          </div>

          <div className="flex gap-2 pt-2">
            <button
              onClick={save}
              disabled={saving || !editing.name}
              className="flex items-center gap-2 bg-[#0077b5] text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-[#004182] disabled:opacity-50 transition-colors"
            >
              <Check className="w-4 h-4" /> {saving ? "Saving..." : "Save"}
            </button>
            <button onClick={closeForm} className="px-4 py-2 rounded-lg text-sm font-medium text-gray-600 hover:bg-gray-100">
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Niche List */}
      <div className="space-y-3">
        {niches.length === 0 && !editing && (
          <div className="bg-white rounded-xl border border-gray-200 p-12 text-center text-gray-400">
            No niches configured yet. Add one to get started.
          </div>
        )}
        {niches.map((n) => (
          <div key={n.id} className="bg-white rounded-xl border border-gray-200 p-5 flex items-start justify-between">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <h3 className="font-semibold text-gray-900">{n.name}</h3>
                <span className={`w-2 h-2 rounded-full ${n.active ? "bg-green-500" : "bg-gray-300"}`} />
                <span className="text-xs text-gray-500 capitalize">{n.frequency}</span>
                <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">{FORMAT_LABELS[n.publish_format] || n.publish_format}</span>
              </div>
              {n.description && <p className="text-sm text-gray-500 mb-2">{n.description}</p>}
              <div className="flex flex-wrap gap-1">
                {n.keywords.map((kw) => (
                  <span key={kw} className="bg-[#e8f4fd] text-[#0077b5] text-xs px-2 py-0.5 rounded-full">{kw}</span>
                ))}
              </div>
            </div>
            <div className="flex items-center gap-2 ml-4">
              <button
                onClick={() => generate(n.id)}
                className="flex items-center gap-1 text-xs bg-green-50 text-green-700 px-2.5 py-1.5 rounded-lg hover:bg-green-100"
                title="Generate blog now"
              >
                <Zap className="w-3 h-3" /> Generate
              </button>
              <button onClick={() => openEdit(n)} className="p-1.5 text-gray-400 hover:text-gray-700 hover:bg-gray-100 rounded-lg">
                <Pencil className="w-4 h-4" />
              </button>
              <button onClick={() => remove(n.id)} className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg">
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
