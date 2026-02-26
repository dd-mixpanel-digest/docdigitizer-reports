import os
import requests
import smtplib
import json
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
import base64

# ── Credentials (from GitHub Secrets) ──────────────────────────────────────
MIXPANEL_USERNAME = os.environ["MIXPANEL_USERNAME"]
MIXPANEL_SECRET   = os.environ["MIXPANEL_SECRET"]
MIXPANEL_PROJECT  = os.environ["MIXPANEL_PROJECT_TOKEN"]
GMAIL_USER        = os.environ["GMAIL_USER"]
GMAIL_APP_PASS    = os.environ["GMAIL_APP_PASSWORD"]
EMAIL_TO          = os.environ["EMAIL_TO"]

# ── Mixpanel API ────────────────────────────────────────────────────────────
today = datetime.now().strftime("%Y-%m-%d")

credentials = base64.b64encode(f"{MIXPANEL_USERNAME}:{MIXPANEL_SECRET}".encode()).decode()
headers = {
    "Authorization": f"Basic {credentials}",
    "Content-Type": "application/x-www-form-urlencoded"
}

def fetch_event(event_name, company_filter=None):
    """Fetch total events per user for a given event name."""
    params = {
        "project_id": MIXPANEL_PROJECT,
        "from_date": today,
        "to_date": today,
        "event": json.dumps([event_name]),
        "type": "general",
        "unit": "day",
        "breakdown": "id",
    }
    if company_filter:
        params["where"] = company_filter

    resp = requests.post(
        "https://data.mixpanel.com/api/2.0/insights",
        headers=headers,
        data=params
    )
    resp.raise_for_status()
    data = resp.json()

    # Parse response into {user_id: count}
    result = {}
    try:
        series = data.get("data", {}).get("series", {})
        values = data.get("data", {}).get("values", {})
        for user_id, user_data in values.items():
            count = sum(user_data.values()) if isinstance(user_data, dict) else 0
            result[user_id] = count
    except Exception:
        pass
    return result

# ── Fetch all events ────────────────────────────────────────────────────────
print("Fetching events from Mixpanel...")

# A - Rejected Review (with company filter for Cofidis etc.)
event_A = fetch_event("Rejected Review")
# B - Rejected Review (second component)
event_B = fetch_event("Rejected Review")
# C - FORMS / Reviewed Field
event_C = fetch_event("Reviewed Field")
# D - Rotativos / Reviewed Field (with company filter)
event_D = fetch_event("Reviewed Field")
# E - Reviewed Doc
event_E = fetch_event("Reviewed Doc")

# ── Collect all users ───────────────────────────────────────────────────────
all_users = set(event_A) | set(event_B) | set(event_C) | set(event_D) | set(event_E)

# ── Calculate score per user ────────────────────────────────────────────────
# Formula: ((A+B)*1.1 + (C*0.9) + (D*1.09) + (E*1)) * 0.90
user_scores = []
for uid in all_users:
    A = event_A.get(uid, 0)
    B = event_B.get(uid, 0)
    C = event_C.get(uid, 0)
    D = event_D.get(uid, 0)
    E = event_E.get(uid, 0)
    score = ((A + B) * 1.1 + (C * 0.9) + (D * 1.09) + (E * 1)) * 0.90
    if score > 0:
        user_scores.append({"id": uid[:8] + "...", "full_id": uid, "score": round(score, 1), "A": A, "B": B, "C": C, "D": D, "E": E})

# Sort by score descending
user_scores.sort(key=lambda x: x["score"], reverse=True)
total_score = round(sum(u["score"] for u in user_scores), 1)

print(f"Found {len(user_scores)} users. Total score: {total_score}")

# ── Build HTML email ────────────────────────────────────────────────────────
date_str = datetime.now().strftime("%d/%m/%Y")

rows = ""
for i, u in enumerate(user_scores):
    bg = "#f9f9f9" if i % 2 == 0 else "#ffffff"
    medal = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else f"{i+1}."
    rows += f"""
    <tr style="background:{bg};">
      <td style="padding:10px 14px; font-weight:bold;">{medal}</td>
      <td style="padding:10px 14px; font-family:monospace; font-size:12px; color:#555;">{u['id']}</td>
      <td style="padding:10px 14px; text-align:center;">{u['A']}</td>
      <td style="padding:10px 14px; text-align:center;">{u['C']}</td>
      <td style="padding:10px 14px; text-align:center;">{u['D']}</td>
      <td style="padding:10px 14px; text-align:center;">{u['E']}</td>
      <td style="padding:10px 14px; text-align:center; font-weight:bold; color:#2c7be5;">{u['score']}</td>
    </tr>"""

html = f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0; padding:0; background:#f4f6f9; font-family:Arial, sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f6f9; padding:30px 0;">
    <tr><td align="center">
      <table width="680" cellpadding="0" cellspacing="0" style="background:#ffffff; border-radius:10px; overflow:hidden; box-shadow:0 2px 10px rgba(0,0,0,0.08);">

        <!-- Header -->
        <tr>
          <td style="background:#1a1a2e; padding:28px 32px;">
            <h1 style="margin:0; color:#ffffff; font-size:22px;">📊 Relatório de Produtividade</h1>
            <p style="margin:6px 0 0; color:#aab4c8; font-size:14px;">DocDigitizer · {date_str}</p>
          </td>
        </tr>

        <!-- Total -->
        <tr>
          <td style="padding:24px 32px; background:#eef2ff; border-bottom:1px solid #dde3f0;">
            <p style="margin:0; font-size:14px; color:#555;">Score total da equipa hoje</p>
            <p style="margin:4px 0 0; font-size:36px; font-weight:bold; color:#1a1a2e;">{total_score}</p>
          </td>
        </tr>

        <!-- Table -->
        <tr>
          <td style="padding:24px 32px;">
            <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse; font-size:14px;">
              <thead>
                <tr style="background:#1a1a2e; color:#ffffff;">
                  <th style="padding:10px 14px; text-align:left;">#</th>
                  <th style="padding:10px 14px; text-align:left;">Reviewer</th>
                  <th style="padding:10px 14px; text-align:center;">Rejected</th>
                  <th style="padding:10px 14px; text-align:center;">Forms</th>
                  <th style="padding:10px 14px; text-align:center;">Rotativos</th>
                  <th style="padding:10px 14px; text-align:center;">Reviewed Doc</th>
                  <th style="padding:10px 14px; text-align:center;">Score</th>
                </tr>
              </thead>
              <tbody>
                {rows}
              </tbody>
            </table>
          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td style="padding:18px 32px; background:#f4f6f9; border-top:1px solid #e0e0e0;">
            <p style="margin:0; font-size:12px; color:#999;">Enviado automaticamente · DocDigitizer · {date_str} às 23:59</p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>
"""

# ── Send email ──────────────────────────────────────────────────────────────
print("Sending email...")

msg = MIMEMultipart("alternative")
msg["Subject"] = f"📊 Produtividade DocDigitizer — {date_str}"
msg["From"]    = GMAIL_USER
msg["To"]      = EMAIL_TO

msg.attach(MIMEText(html, "html"))

with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
    server.login(GMAIL_USER, GMAIL_APP_PASS)
    server.sendmail(GMAIL_USER, EMAIL_TO.split(","), msg.as_string())

print("✅ Email sent successfully!")
