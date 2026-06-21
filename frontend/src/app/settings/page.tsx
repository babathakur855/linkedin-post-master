"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  getSettings, updateSettings, getLinkedInStatus, getLinkedInAuthUrl,
  linkedInCallback, type Settings,
} from "@/lib/api";
import { CheckCircle, Linkedin, Mail, Settings as SettingsIcon, AlertCircle } from "lucide-react";

export default function SettingsPage() {
  const searchParams = useSearchParams();
  const [settings, setSettings] = useState<Settings>({});
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [linkedInStatus, setLinkedInStatus] = useState<{
    connected: boolean; person_id: string; expires_at: string; expired: boolean; client_id_set: boolean;
  } | null>(null);

  const load = async () => {
    const [s, li] = await Promise.all([getSettings(), getLinkedInStatus()]);
    setSettings(s);
    setLinkedInStatus(li);
  };

  // Handle LinkedIn OAuth callback
  useEffect(() => {
    const code = searchParams.get("code");
    const error = searchParams.get("error");
    if (code) {
      getLinkedInAuthUrl().then(({ redirect_uri }) =>
        linkedInCallback(code, redirect_uri).then(() => {
          window.history.replaceState({}, "", "/settings");
          load();
        })
      );
    }
    if (error) alert(`LinkedIn auth failed: ${error}`);
    load();
  }, []);

  const save = async () => {
    setSaving(true);
    try {
      // Don't send masked secrets
      const toSave = { ...settings };
      Object.keys(toSave).forEach((k) => {
        if ((toSave as Record<string, string | undefined>)[k] === "***") {
          delete (toSave as Record<string, string | undefined>)[k];
        }
      });
      await updateSettings(toSave);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
      await load();
    } catch (e) { alert(String(e)); }
    finally { setSaving(false); }
  };

  const connectLinkedIn = async () => {
    try {
      const { url } = await getLinkedInAuthUrl();
      window.location.href = url;
    } catch (e) { alert(String(e)); }
  };

  const set = (k: keyof Settings) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setSettings((s) => ({ ...s, [k]: e.target.value }));

  return (
    <div className="space-y-8 max-w-2xl">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="text-gray-500 text-sm mt-1">Configure email notifications and LinkedIn connection</p>
      </div>

      {/* Email Settings */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
        <div className="flex items-center gap-2 mb-1">
          <Mail className="w-4 h-4 text-[#0077b5]" />
          <h2 className="font-semibold text-gray-900">Email (SMTP / IMAP)</h2>
        </div>
        <p className="text-xs text-gray-500">
          Used to send blog drafts for review and poll for your email replies.
          For Gmail: enable 2FA and generate an App Password.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[
            { key: "review_email", label: "Review Email (send drafts to)", placeholder: "you@example.com", type: "email" },
            { key: "from_email", label: "From Email", placeholder: "Same as SMTP user", type: "email" },
            { key: "smtp_host", label: "SMTP Host", placeholder: "smtp.gmail.com" },
            { key: "smtp_port", label: "SMTP Port", placeholder: "587" },
            { key: "smtp_user", label: "SMTP Username", placeholder: "your@gmail.com" },
            { key: "smtp_password", label: "SMTP Password / App Password", placeholder: "••••••••", type: "password" },
            { key: "imap_host", label: "IMAP Host", placeholder: "imap.gmail.com" },
            { key: "imap_port", label: "IMAP Port", placeholder: "993" },
          ].map(({ key, label, placeholder, type }) => (
            <div key={key}>
              <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
              <input
                type={type || "text"}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#0077b5]"
                value={(settings as Record<string, string>)[key] || ""}
                onChange={set(key as keyof Settings)}
                placeholder={placeholder}
              />
            </div>
          ))}
        </div>
      </div>

      {/* LinkedIn Settings */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
        <div className="flex items-center gap-2 mb-1">
          <Linkedin className="w-4 h-4 text-[#0077b5]" />
          <h2 className="font-semibold text-gray-900">LinkedIn API</h2>
        </div>
        <p className="text-xs text-gray-500">
          Create a LinkedIn app at <strong>developers.linkedin.com</strong> → get Client ID and Secret.
          Add your frontend URL as an Authorized Redirect URL.
        </p>

        {linkedInStatus && (
          <div className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm ${
            linkedInStatus.connected ? "bg-green-50 text-green-700" : "bg-yellow-50 text-yellow-700"
          }`}>
            {linkedInStatus.connected
              ? <CheckCircle className="w-4 h-4" />
              : <AlertCircle className="w-4 h-4" />}
            {linkedInStatus.connected
              ? `Connected (person: ${linkedInStatus.person_id})`
              : "Not connected — add credentials and click Connect"}
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[
            { key: "linkedin_client_id", label: "LinkedIn Client ID", placeholder: "86xxxxx" },
            { key: "linkedin_client_secret", label: "LinkedIn Client Secret", placeholder: "••••••••", type: "password" },
            { key: "frontend_url", label: "Your Frontend URL (for OAuth redirect)", placeholder: "http://localhost:3040" },
          ].map(({ key, label, placeholder, type }) => (
            <div key={key}>
              <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
              <input
                type={type || "text"}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#0077b5]"
                value={(settings as Record<string, string>)[key] || ""}
                onChange={set(key as keyof Settings)}
                placeholder={placeholder}
              />
            </div>
          ))}
        </div>

        <button
          onClick={connectLinkedIn}
          disabled={!linkedInStatus?.client_id_set}
          className="flex items-center gap-2 bg-[#0077b5] text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-[#004182] disabled:opacity-50 transition-colors"
        >
          <Linkedin className="w-4 h-4" />
          Connect LinkedIn Account
        </button>
      </div>

      {/* App Settings */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
        <div className="flex items-center gap-2 mb-1">
          <SettingsIcon className="w-4 h-4 text-gray-500" />
          <h2 className="font-semibold text-gray-900">Application</h2>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Frontend URL</label>
          <input
            type="text"
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#0077b5]"
            value={settings.frontend_url || ""}
            onChange={set("frontend_url")}
            placeholder="http://localhost:3040"
          />
          <p className="text-xs text-gray-400 mt-1">Used to generate preview links in review emails</p>
        </div>
      </div>

      {/* Save */}
      <button
        onClick={save}
        disabled={saving}
        className="flex items-center gap-2 bg-[#0077b5] text-white px-6 py-2.5 rounded-lg font-medium hover:bg-[#004182] disabled:opacity-50 transition-colors"
      >
        {saved ? <CheckCircle className="w-4 h-4" /> : <SettingsIcon className="w-4 h-4" />}
        {saving ? "Saving..." : saved ? "Saved!" : "Save Settings"}
      </button>
    </div>
  );
}
