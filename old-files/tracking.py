"""
FastAPI tracking server — email open pixel + link click tracker.
Runs as a background thread from app.py on port 8000.
"""
import base64
import datetime
import os

import requests as http
from fastapi import FastAPI
from fastapi.responses import RedirectResponse, Response

# 1×1 transparent GIF
_GIF = base64.b64decode("R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7")

tracking_app = FastAPI(docs_url=None, redoc_url=None)


# ─── Supabase helpers ─────────────────────────────────────────────────────────

def _sb_url() -> str:
    return os.getenv("SUPABASE_URL", "")

def _sb_key() -> str:
    return os.getenv("SUPABASE_KEY", "")

def _hdr(prefer: str = "return=minimal") -> dict:
    return {
        "apikey": _sb_key(),
        "Authorization": f"Bearer {_sb_key()}",
        "Content-Type": "application/json",
        "Prefer": prefer,
    }


# ─── Routes ───────────────────────────────────────────────────────────────────

@tracking_app.get("/track/open/{email_id}.gif")
async def track_open(email_id: str):
    """Record an email open and return a 1×1 transparent tracking pixel."""
    url = _sb_url()
    if url:
        try:
            # Fetch current open count
            r = http.get(
                f"{url}/rest/v1/email_sends"
                f"?email_id=eq.{email_id}&select=email_opened_count",
                headers=_hdr(""),
                timeout=5,
            )
            count = 0
            if r.status_code == 200 and r.json():
                count = r.json()[0].get("email_opened_count") or 0

            # Patch record
            http.patch(
                f"{url}/rest/v1/email_sends?email_id=eq.{email_id}",
                headers=_hdr(),
                json={
                    "email_opened": True,
                    "email_opened_count": count + 1,
                    "last_opened_at": datetime.datetime.utcnow().isoformat() + "Z",
                },
                timeout=5,
            )
        except Exception:
            pass  # Never fail the pixel delivery

    return Response(
        content=_GIF,
        media_type="image/gif",
        headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"},
    )


@tracking_app.get("/track/link/{email_id}")
async def track_link(email_id: str, url: str, type: str = "link"):
    """Record a link click then redirect to the destination URL."""
    field = {
        "resume":   "resume_opened",
        "linkedin": "linkedin_opened",
        "website":  "website_opened",
    }.get(type)

    sb_url = _sb_url()
    if field and sb_url:
        try:
            http.patch(
                f"{sb_url}/rest/v1/email_sends?email_id=eq.{email_id}",
                headers=_hdr(),
                json={field: True},
                timeout=5,
            )
        except Exception:
            pass

    return RedirectResponse(url=url, status_code=302)


@tracking_app.get("/health")
async def health():
    return {"status": "ok", "ts": datetime.datetime.utcnow().isoformat()}
