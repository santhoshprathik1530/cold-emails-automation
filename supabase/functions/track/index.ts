/**
 * Supabase Edge Function — email open pixel + link click tracker
 *
 * Routes (all public, no JWT required):
 *   GET .../track/open/{email_id}.gif  → 1×1 transparent GIF + updates email_sends
 *   GET .../track/link/{email_id}?url={dest}&type={resume|linkedin|website}
 *                                      → 302 redirect + updates email_sends
 *   GET .../track                      → health check
 */

import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

// 1×1 transparent GIF
const GIF = Uint8Array.from(
  atob("R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"),
  (c) => c.charCodeAt(0),
);

Deno.serve(async (req: Request) => {
  const url = new URL(req.url);
  const pathname = url.pathname;

  // ── Supabase client (service role for DB writes) ──────────────────────────
  const supabase = createClient(
    Deno.env.get("SUPABASE_URL") ?? "",
    Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? "",
    { auth: { persistSession: false } },
  );

  // ── Route: open pixel ─────────────────────────────────────────────────────
  // Matches: .../open/{email_id}.gif  or  .../open/{email_id}
  const openMatch = pathname.match(/\/open\/([^/]+?)(?:\.gif)?$/);
  if (openMatch) {
    const emailId = openMatch[1];
    try {
      const { data } = await supabase
        .from("email_sends")
        .select("email_opened_count")
        .eq("email_id", emailId)
        .single();

      const count = (data?.email_opened_count ?? 0) + 1;

      await supabase
        .from("email_sends")
        .update({
          email_opened: true,
          email_opened_count: count,
          last_opened_at: new Date().toISOString(),
        })
        .eq("email_id", emailId);
    } catch (_) {
      // Never block pixel delivery on DB errors
    }

    return new Response(GIF, {
      headers: {
        "Content-Type": "image/gif",
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        "Pragma": "no-cache",
      },
    });
  }

  // ── Route: link click ─────────────────────────────────────────────────────
  // Matches: .../link/{email_id}?url={dest}&type={resume|linkedin|website}
  const linkMatch = pathname.match(/\/link\/([^/]+)$/);
  if (linkMatch) {
    const emailId = linkMatch[1];
    const destUrl = url.searchParams.get("url") ?? "/";
    const type = url.searchParams.get("type") ?? "";

    const fieldMap: Record<string, string> = {
      resume: "resume_opened",
      linkedin: "linkedin_opened",
      website: "website_opened",
    };
    const countMap: Record<string, string> = {
      resume: "resume_opened_count",
      linkedin: "linkedin_opened_count",
      website: "website_opened_count",
    };
    const field = fieldMap[type];
    const countField = countMap[type];

    if (field && countField) {
      try {
        const { data } = await supabase
          .from("email_sends")
          .select(countField)
          .eq("email_id", emailId)
          .single();

        const currentCount = ((data as Record<string, number> | null)?.[countField] ?? 0) + 1;

        await supabase
          .from("email_sends")
          .update({ [field]: true, [countField]: currentCount })
          .eq("email_id", emailId);
      } catch (_) {
        // Never block redirect on DB errors
      }
    }

    return new Response(null, {
      status: 302,
      headers: { Location: destUrl },
    });
  }

  // ── Health check ──────────────────────────────────────────────────────────
  return new Response(
    JSON.stringify({ status: "ok", ts: new Date().toISOString() }),
    { headers: { "Content-Type": "application/json" } },
  );
});
