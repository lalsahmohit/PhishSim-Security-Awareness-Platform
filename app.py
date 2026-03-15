"""
Phishing Email Simulator - Backend
Security Awareness Training Tool
"""

from flask import Flask, request, jsonify, render_template, redirect, send_file
from flask_cors import CORS
import sqlite3
import smtplib
import uuid
import os
import json
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timezone
from jinja2 import Template
import io
import base64

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "phishing_sim.db")

app = Flask(__name__, template_folder=os.path.join(BASE_DIR, "templates"))
CORS(app)
# DATABASE SETUP
# ─────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS campaigns (
            id          TEXT PRIMARY KEY,
            name        TEXT NOT NULL,
            template    TEXT NOT NULL,
            sender_name TEXT NOT NULL,
            sender_email TEXT NOT NULL,
            subject     TEXT NOT NULL,
            status      TEXT DEFAULT 'draft',
            created_at  TEXT NOT NULL,
            sent_at     TEXT
        );

        CREATE TABLE IF NOT EXISTS targets (
            id          TEXT PRIMARY KEY,
            campaign_id TEXT NOT NULL,
            name        TEXT NOT NULL,
            email       TEXT NOT NULL,
            department  TEXT,
            token       TEXT UNIQUE NOT NULL,
            sent        INTEGER DEFAULT 0,
            opened      INTEGER DEFAULT 0,
            clicked     INTEGER DEFAULT 0,
            reported    INTEGER DEFAULT 0,
            sent_at     TEXT,
            opened_at   TEXT,
            clicked_at  TEXT,
            FOREIGN KEY (campaign_id) REFERENCES campaigns(id)
        );

        CREATE TABLE IF NOT EXISTS events (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            target_id   TEXT NOT NULL,
            campaign_id TEXT NOT NULL,
            event_type  TEXT NOT NULL,
            ip_address  TEXT,
            user_agent  TEXT,
            timestamp   TEXT NOT NULL,
            FOREIGN KEY (target_id) REFERENCES targets(id)
        );

        CREATE TABLE IF NOT EXISTS email_templates (
            id          TEXT PRIMARY KEY,
            name        TEXT NOT NULL,
            category    TEXT NOT NULL,
            subject     TEXT NOT NULL,
            sender_name TEXT NOT NULL,
            sender_email TEXT NOT NULL,
            html_body   TEXT NOT NULL,
            difficulty  TEXT NOT NULL,
            created_at  TEXT NOT NULL
        );
        """)
        _seed_templates(conn)

def _seed_templates(conn):
    existing = conn.execute("SELECT COUNT(*) FROM email_templates").fetchone()[0]
    if existing > 0:
        return

    now = datetime.now(timezone.utc).isoformat()
    templates = [
        {
            "id": str(uuid.uuid4()),
            "name": "IT Password Reset",
            "category": "IT / Helpdesk",
            "subject": "⚠️ Immediate Action Required: Reset Your Password",
            "sender_name": "IT Helpdesk",
            "sender_email": "helpdesk@company-it-support.com",
            "difficulty": "Easy",
            "html_body": open(os.path.join(BASE_DIR, "email_templates/it_password_reset.html"), encoding='utf-8').read()        },
        {
            "id": str(uuid.uuid4()),
            "name": "CEO Wire Transfer",
            "category": "Executive Impersonation",
            "subject": "Urgent - Confidential Wire Transfer Request",
            "sender_name": "CEO Office",
            "sender_email": "ceo@company-exec.net",
            "difficulty": "Medium",
            "html_body": open(os.path.join(BASE_DIR, "email_templates/ceo_wire_transfer.html"), encoding='utf-8').read()

        },
        {
            "id": str(uuid.uuid4()),
            "name": "HR Benefits Update",
            "category": "HR / Benefits",
            "subject": "Action Required: Update Your Benefits Enrollment",
            "sender_name": "HR Department",
            "sender_email": "hr-benefits@company-hr.org",
            "difficulty": "Medium",
            "html_body": open(os.path.join(BASE_DIR, "email_templates/hr_benefits.html"), encoding='utf-8').read()        },
        {
            "id": str(uuid.uuid4()),
            "name": "DocuSign Document",
            "category": "SaaS / Cloud",
            "subject": "You have a document to review and sign",
            "sender_name": "DocuSign",
            "sender_email": "dse@docusign-notifications.com",
            "difficulty": "Hard",
            "html_body": open(os.path.join(BASE_DIR, "email_templates/docusign_fake.html"), encoding='utf-8').read()
        },
    ]
    for t in templates:
        conn.execute("""
            INSERT INTO email_templates (id,name,category,subject,sender_name,sender_email,html_body,difficulty,created_at)
            VALUES (:id,:name,:category,:subject,:sender_name,:sender_email,:html_body,:difficulty,:created_at)
        """, {**t, "created_at": now})

# ─────────────────────────────────────────────
# CAMPAIGN ROUTES
# ─────────────────────────────────────────────

@app.route("/api/campaigns", methods=["GET"])
def list_campaigns():
    with get_db() as conn:
        rows = conn.execute("""
            SELECT c.*,
                COUNT(t.id) as total_targets,
                SUM(t.sent) as sent_count,
                SUM(t.opened) as opened_count,
                SUM(t.clicked) as clicked_count,
                SUM(t.reported) as reported_count
            FROM campaigns c
            LEFT JOIN targets t ON t.campaign_id = c.id
            GROUP BY c.id
            ORDER BY c.created_at DESC
        """).fetchall()
        return jsonify([dict(r) for r in rows])

@app.route("/api/campaigns", methods=["POST"])
def create_campaign():
    data = request.json
    cid = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    # Get template defaults
    with get_db() as conn:
        tmpl = conn.execute("SELECT * FROM email_templates WHERE id=?", (data["template_id"],)).fetchone()
        if not tmpl:
            return jsonify({"error": "Template not found"}), 404

        conn.execute("""
            INSERT INTO campaigns (id,name,template,sender_name,sender_email,subject,status,created_at)
            VALUES (?,?,?,?,?,?,?,?)
        """, (cid, data["name"], data["template_id"],
              data.get("sender_name", tmpl["sender_name"]),
              data.get("sender_email", tmpl["sender_email"]),
              data.get("subject", tmpl["subject"]),
              "draft", now))

        # Insert targets
        for target in data.get("targets", []):
            tid = str(uuid.uuid4())
            token = str(uuid.uuid4()).replace("-", "")
            conn.execute("""
                INSERT INTO targets (id,campaign_id,name,email,department,token)
                VALUES (?,?,?,?,?,?)
            """, (tid, cid, target["name"], target["email"], target.get("department",""), token))

    return jsonify({"id": cid, "message": "Campaign created"}), 201

@app.route("/api/campaigns/<cid>", methods=["GET"])
def get_campaign(cid):
    with get_db() as conn:
        c = conn.execute("SELECT * FROM campaigns WHERE id=?", (cid,)).fetchone()
        if not c:
            return jsonify({"error": "Not found"}), 404
        targets = conn.execute("SELECT * FROM targets WHERE campaign_id=?", (cid,)).fetchall()
        events  = conn.execute("""
            SELECT e.*, t.name as target_name, t.email as target_email
            FROM events e JOIN targets t ON t.id=e.target_id
            WHERE e.campaign_id=? ORDER BY e.timestamp DESC LIMIT 100
        """, (cid,)).fetchall()
        return jsonify({
            **dict(c),
            "targets": [dict(t) for t in targets],
            "events":  [dict(e) for e in events]
        })

@app.route("/api/campaigns/<cid>", methods=["DELETE"])
def delete_campaign(cid):
    with get_db() as conn:
        conn.execute("DELETE FROM events WHERE campaign_id=?", (cid,))
        conn.execute("DELETE FROM targets WHERE campaign_id=?", (cid,))
        conn.execute("DELETE FROM campaigns WHERE id=?", (cid,))
    return jsonify({"message": "Deleted"})

@app.route("/api/campaigns/<cid>/launch", methods=["POST"])
def launch_campaign(cid):
    """Simulate sending emails (Real SMTP unless configured)."""
    data = request.json or {}
    use_real_smtp = data.get("use_smtp", True)
    smtp_config = data.get("smtp", {})
    base_url = data.get("base_url", "http://localhost:5000")

    with get_db() as conn:
        c = conn.execute("SELECT * FROM campaigns WHERE id=?", (cid,)).fetchone()
        if not c:
            return jsonify({"error": "Campaign not found"}), 404
        tmpl = conn.execute("SELECT * FROM email_templates WHERE id=?", (c["template"],)).fetchone()
        if not tmpl:
            return jsonify({"error": "Template not found"}), 404

        targets = conn.execute(
            "SELECT * FROM targets WHERE campaign_id=? AND sent=0", (cid,)
        ).fetchall()

        sent_count = 0
        errors = []
        now = datetime.now(timezone.utc).isoformat()

        for t in targets:
            track_open_url  = f"{base_url}/track/open/{t['token']}"
            track_click_url = f"{base_url}/track/click/{t['token']}"
            pixel_img       = f'<img src="{track_open_url}" width="1" height="1" style="display:none"/>'

            # Render template with target-specific tracking
            html_body = tmpl["html_body"] \
                .replace("{{TRACKING_PIXEL}}", pixel_img) \
                .replace("{{CLICK_URL}}", track_click_url) \
                .replace("{{TARGET_NAME}}", t["name"]) \
                .replace("{{TARGET_EMAIL}}", t["email"])

            if use_real_smtp and smtp_config:
                try:
                    _send_email(
                        smtp_config, c["sender_name"], c["sender_email"],
                        t["email"], c["subject"], html_body
                    )
                except Exception as e:
                    errors.append({"email": t["email"], "error": str(e)})
                    continue

            conn.execute(
                "UPDATE targets SET sent=1, sent_at=? WHERE id=?", (now, t["id"])
            )
            conn.execute("""
                INSERT INTO events (target_id,campaign_id,event_type,timestamp)
                VALUES (?,?,?,?)
            """, (t["id"], cid, "sent", now))
            sent_count += 1

        conn.execute(
            "UPDATE campaigns SET status='active', sent_at=? WHERE id=?",
            (now, cid)
        )

    return jsonify({
        "sent": sent_count,
        "errors": errors,
        "simulated": not use_real_smtp
    })

# ─────────────────────────────────────────────
# TRACKING ROUTES
# ─────────────────────────────────────────────

@app.route("/track/open/<token>")
def track_open(token):
    """1x1 tracking pixel."""
    _record_event(token, "opened", "opened_at")
    # Return transparent 1x1 GIF
    gif = base64.b64decode("R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7")
    return send_file(io.BytesIO(gif), mimetype="image/gif")

@app.route("/track/click/<token>")
def track_click(token):
    """Redirect page for link clicks."""
    _record_event(token, "clicked", "clicked_at")
    return render_template("awareness.html"), 200

@app.route("/api/targets/<tid>/report", methods=["POST"])
def report_phishing(tid):
    with get_db() as conn:
        t = conn.execute("SELECT * FROM targets WHERE id=?", (tid,)).fetchone()
        if not t:
            return jsonify({"error": "Not found"}), 404
        conn.execute("UPDATE targets SET reported=1 WHERE id=?", (tid,))
        conn.execute("""
            INSERT INTO events (target_id,campaign_id,event_type,timestamp)
            VALUES (?,?,?,?)
        """, (tid, t["campaign_id"], "reported",
               datetime.now(timezone.utc).isoformat()))
    return jsonify({"message": "Reported"})

def _record_event(token, event_type, timestamp_col):
    with get_db() as conn:
        t = conn.execute("SELECT * FROM targets WHERE token=?", (token,)).fetchone()
        if not t:
            return
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(f"""
            UPDATE targets SET {event_type}=1, {timestamp_col}=COALESCE({timestamp_col},?)
            WHERE token=?
        """, (now, token))
        conn.execute("""
            INSERT INTO events (target_id,campaign_id,event_type,ip_address,user_agent,timestamp)
            VALUES (?,?,?,?,?,?)
        """, (t["id"], t["campaign_id"], event_type,
              request.remote_addr, request.headers.get("User-Agent",""), now))

# ─────────────────────────────────────────────
# TEMPLATE ROUTES
# ─────────────────────────────────────────────

@app.route("/api/templates", methods=["GET"])
def list_templates():
    with get_db() as conn:
        rows = conn.execute("SELECT id,name,category,subject,sender_name,sender_email,difficulty FROM email_templates").fetchall()
        return jsonify([dict(r) for r in rows])

@app.route("/api/templates/<tid>/preview", methods=["GET"])
def preview_template(tid):
    with get_db() as conn:
        tmpl = conn.execute("SELECT * FROM email_templates WHERE id=?", (tid,)).fetchone()
        if not tmpl:
            return jsonify({"error": "Not found"}), 404
        html = dict(tmpl)["html_body"] \
            .replace("{{TRACKING_PIXEL}}", "") \
            .replace("{{CLICK_URL}}", "#") \
            .replace("{{TARGET_NAME}}", "John Smith") \
            .replace("{{TARGET_EMAIL}}", "john.smith@example.com")
        return html, 200, {"Content-Type": "text/html"}

# ─────────────────────────────────────────────
# STATS
# ─────────────────────────────────────────────

@app.route("/api/stats", methods=["GET"])
def global_stats():
    with get_db() as conn:
        row = conn.execute("""
            SELECT
                COUNT(DISTINCT c.id) as total_campaigns,
                COUNT(t.id) as total_targets,
                SUM(t.sent) as total_sent,
                SUM(t.opened) as total_opened,
                SUM(t.clicked) as total_clicked,
                SUM(t.reported) as total_reported
            FROM campaigns c LEFT JOIN targets t ON t.campaign_id=c.id
        """).fetchone()
        return jsonify(dict(row))

# ─────────────────────────────────────────────
# SMTP HELPER
# ─────────────────────────────────────────────

def _send_email(cfg, sender_name, sender_email, to_email, subject, html_body):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"{sender_name} <{sender_email}>"
    msg["To"]      = to_email
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(cfg["host"], cfg.get("port", 587)) as s:
        s.ehlo()
        s.starttls()
        s.login(cfg["username"], cfg["password"])
        s.sendmail(sender_email, to_email, msg.as_string())

# ─────────────────────────────────────────────
# SERVE DASHBOARD
# ─────────────────────────────────────────────

@app.route("/")
def index():
    return send_file(os.path.join(BASE_DIR, "templates", "dashboard.html"))
if __name__ == "__main__":
    os.makedirs("email_templates", exist_ok=True)
    os.makedirs("templates", exist_ok=True)
    init_db()
    app.run(debug=True, port=5000)
