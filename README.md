# PhishSim — Phishing Email Simulator
## Security Awareness Training Platform

A self-hosted phishing simulation tool for testing and training employees
against social engineering attacks.

---

## ⚠️ Authorized Use Only
This tool is for **security awareness training** in organizations where
you have explicit authorization. Never use against individuals without consent.

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the server
python app.py

# 3. Open the dashboard
open http://localhost:5000
```

---

## Architecture

```
phishing_simulator/
├── app.py                        # Flask backend (REST API)
├── phishing_sim.db               # SQLite database (auto-created)
├── requirements.txt
├── templates/
│   ├── dashboard.html            # Main web UI
│   └── awareness.html            # Page shown after click
└── email_templates/
    ├── it_password_reset.html    # IT Helpdesk scenario
    ├── ceo_wire_transfer.html    # BEC / CEO fraud scenario
    ├── hr_benefits.html          # HR benefits scenario
    └── docusign_fake.html        # SaaS impersonation scenario
```

---

## Database Schema

### `campaigns`
| Field | Type | Description |
|-------|------|-------------|
| id | TEXT (UUID) | Primary key |
| name | TEXT | Campaign display name |
| template | TEXT | FK → email_templates.id |
| sender_name | TEXT | "From" display name |
| sender_email | TEXT | "From" email address |
| subject | TEXT | Email subject line |
| status | TEXT | draft / active / completed |
| created_at | TEXT | ISO timestamp |
| sent_at | TEXT | When launched |

### `targets`
| Field | Type | Description |
|-------|------|-------------|
| id | TEXT (UUID) | Primary key |
| campaign_id | TEXT | FK → campaigns.id |
| name | TEXT | Target full name |
| email | TEXT | Target email |
| department | TEXT | Optional department |
| token | TEXT | Unique tracking token |
| sent | INTEGER | 1 if email sent |
| opened | INTEGER | 1 if tracking pixel loaded |
| clicked | INTEGER | 1 if link clicked |
| reported | INTEGER | 1 if reported as phishing |

### `events`
| Field | Type | Description |
|-------|------|-------------|
| id | INTEGER | Auto-increment PK |
| target_id | TEXT | FK → targets.id |
| campaign_id | TEXT | FK → campaigns.id |
| event_type | TEXT | sent / opened / clicked / reported |
| ip_address | TEXT | Requester IP |
| user_agent | TEXT | Browser/client |
| timestamp | TEXT | ISO timestamp |

### `email_templates`
Stores HTML email bodies with `{{TRACKING_PIXEL}}`, `{{CLICK_URL}}`,
`{{TARGET_NAME}}`, `{{TARGET_EMAIL}}` placeholders.

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/campaigns` | List all campaigns |
| POST | `/api/campaigns` | Create campaign |
| GET | `/api/campaigns/:id` | Get campaign + targets + events |
| DELETE | `/api/campaigns/:id` | Delete campaign |
| POST | `/api/campaigns/:id/launch` | Launch (simulate or send) |
| GET | `/api/templates` | List templates |
| GET | `/api/templates/:id/preview` | Preview rendered HTML |
| GET | `/api/stats` | Global statistics |
| GET | `/track/open/:token` | Tracking pixel (records open) |
| GET | `/track/click/:token` | Click tracker → awareness page |

---

## Sending Real Emails

In the dashboard Settings tab, configure SMTP credentials.
When launching a campaign, set `use_smtp: true` in the request body.

**Recommended:** Use a dedicated test mail account (e.g., Gmail App Password)
and only target accounts you own or have written consent for.

---

## Adding Custom Templates

1. Create an HTML file in `email_templates/`
2. Use placeholders: `{{TARGET_NAME}}`, `{{TARGET_EMAIL}}`,
   `{{CLICK_URL}}`, `{{TRACKING_PIXEL}}`
3. Insert directly into the DB:
   ```sql
   INSERT INTO email_templates (id,name,category,subject,sender_name,sender_email,html_body,difficulty,created_at)
   VALUES ('your-uuid','Template Name','Category','Subject Line','Sender','sender@domain.com','<html>...</html>','Medium','2024-01-01T00:00:00Z');
   ```
