"use client";

import { useEffect } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { linkedInCallback, getLinkedInAuthUrl } from "@/lib/api";

export default function LinkedInCallbackPage() {
  const searchParams = useSearchParams();
  const router = useRouter();

  useEffect(() => {
    const code = searchParams.get("code");
    const error = searchParams.get("error");

    if (error) {
      alert(`LinkedIn auth error: ${error}`);
      router.replace("/settings");
      return;
    }

    if (code) {
      getLinkedInAuthUrl()
        .then(({ redirect_uri }) => linkedInCallback(code, redirect_uri))
        .then(() => router.replace("/settings"))
        .catch((e) => {
          alert(String(e));
          router.replace("/settings");
        });
    }
  }, []);

  return (
    <div className="flex items-center justify-center h-64">
      <div className="text-center">
        <div className="w-8 h-8 border-2 border-[#0077b5] border-t-transparent rounded-full animate-spin mx-auto mb-3" />
        <p className="text-gray-500">Connecting LinkedIn account...</p>
      </div>
    </div>
  );
}
