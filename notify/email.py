"""
Email notification — sends HTML digest of matching jobs via SMTP.

Idempotent: only sends jobs where notified_at IS NULL, then marks them as sent.
Re-running the pipeline never re-notifies for the same job.
"""

from __future__ import annotations

import json
import logging
import smtplib
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import get_settings
from sources.manual_urls import format_manual_urls_html
from storage.db import get_total_job_count, get_unnotified_matches, mark_notified
from storage.models import Job

logger = logging.getLogger(__name__)


def send_digest() -> int:
    """
    Send email digest of new matching jobs.
    Returns count of jobs notified.
    """
    settings = get_settings()

    if not settings.notifications_enabled:
        logger.info("Email notifications not configured — skipping")
        return 0

    # Get unnotified jobs above threshold
    matches = get_unnotified_matches(settings.min_match_score)

    if not matches:
        logger.info("No new matches to notify about")
        return 0

    logger.info(f"Found {len(matches)} new matches to notify")

    # Build email
    html = _build_digest_html(matches)

    try:
        _send_email(
            subject=f"🎯 {len(matches)} new job matches found",
            html_body=html,
        )

        # Mark as notified only AFTER successful send
        mark_notified([j.id for j in matches])
        logger.info(f"✅ Notified about {len(matches)} jobs via email")
        return len(matches)

    except Exception as e:
        logger.error(f"❌ Failed to send email: {e}")
        # Don't mark as notified — they'll be retried next run
        return 0


def _build_digest_html(matches: list[Job]) -> str:
    """Build an HTML email digest."""
    settings = get_settings()
    total_db = get_total_job_count()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # Start HTML
    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
           max-width: 800px; margin: 0 auto; padding: 20px; color: #333; }}
    h1 {{ color: #1a73e8; }}
    .stats {{ background: #e8f0fe; padding: 15px; border-radius: 8px; margin-bottom: 20px; }}
    table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
    th {{ background: #1a73e8; color: white; padding: 12px; text-align: left; }}
    td {{ padding: 10px; border-bottom: 1px solid #eee; }}
    tr:hover {{ background: #f5f5f5; }}
    .score {{ font-weight: bold; }}
    .score-high {{ color: #0d652d; }}
    .score-mid {{ color: #b36b00; }}
    .score-low {{ color: #c5221f; }}
    a {{ color: #1a73e8; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .badge {{ display: inline-block; padding: 2px 8px; border-radius: 12px;
              font-size: 0.8em; margin-left: 5px; }}
    .badge-remote {{ background: #e6f4ea; color: #0d652d; }}
    .badge-hybrid {{ background: #fef7e0; color: #b36b00; }}
    .keywords {{ font-size: 0.85em; color: #666; max-width: 200px; }}
    .footer {{ margin-top: 30px; padding-top: 15px; border-top: 1px solid #eee;
               font-size: 0.85em; color: #888; }}
</style>
</head>
<body>
<h1>🎯 Job Matches Digest</h1>
<div class="stats">
    <strong>{len(matches)}</strong> new matches above {settings.min_match_score} threshold
    &nbsp;|&nbsp; <strong>{total_db}</strong> total jobs in database
    &nbsp;|&nbsp; Run at {now}
</div>

<table>
<thead>
<tr>
    <th>Score</th>
    <th>Title</th>
    <th>Company</th>
    <th>Location</th>
    <th>Matching Keywords</th>
    <th>Link</th>
</tr>
</thead>
<tbody>
"""

    for job in matches:
        score = job.match_score or 0
        score_class = (
            "score-high"
            if score >= 0.8
            else "score-mid" if score >= 0.6 else "score-low"
        )

        # Parse match reasons
        keywords_str = ""
        if job.match_reasons:
            try:
                reasons = json.loads(job.match_reasons)
                kw_list = reasons.get("matching_keywords", [])
                keywords_str = ", ".join(kw_list[:5])
            except json.JSONDecodeError:
                keywords_str = ""

        # Remote badge
        badge = ""
        if job.remote_type == "remote":
            badge = '<span class="badge badge-remote">Remote</span>'
        elif job.remote_type == "hybrid":
            badge = '<span class="badge badge-hybrid">Hybrid</span>'

        location_str = (job.location or "—")[:30]

        html += f"""<tr>
    <td class="score {score_class}">{score:.2f}</td>
    <td><a href="{job.url}" target="_blank">{job.title[:60]}</a></td>
    <td>{job.company}</td>
    <td>{location_str}{badge}</td>
    <td class="keywords">{keywords_str}</td>
    <td><a href="{job.url}" target="_blank">Apply →</a></td>
</tr>
"""

    html += "</tbody></table>"

    # Add manual search URLs
    if settings.generate_manual_urls:
        html += format_manual_urls_html()

    html += f"""
<div class="footer">
    <p>Generated by <strong>JobCrawler</strong> • Threshold: {settings.min_match_score} •
       Embedding: {settings.embedding_provider}</p>
    <p>To adjust matching, edit MIN_MATCH_SCORE in your .env file.</p>
</div>
</body>
</html>
"""
    return html


def _send_email(subject: str, html_body: str) -> None:
    """Send an HTML email via SMTP."""
    settings = get_settings()

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.notify_from or settings.smtp_user
    msg["To"] = settings.notify_to

    # Plain text fallback
    plain = (
        f"{subject}\n\n"
        "View this email in an HTML-capable client for the full digest.\n"
    )
    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    # Connect and send
    if settings.smtp_use_tls:
        server = smtplib.SMTP(settings.smtp_host, settings.smtp_port)
        server.ehlo()
        server.starttls()
    else:
        server = smtplib.SMTP(settings.smtp_host, settings.smtp_port)

    if settings.smtp_user and settings.smtp_password:
        server.login(settings.smtp_user, settings.smtp_password)

    server.send_message(msg)
    server.quit()
    logger.info(f"Email sent to {settings.notify_to}")
