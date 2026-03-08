# Collaborative Platform

Collaborative Platform is an MVP for enterprise-student co-creation.

It supports project publishing, role decomposition, role application, enterprise review, deliverable feedback, an admin dashboard, and AI-assisted role suggestions.

## Features

- User registration and login
- Public project listing and project detail pages
- Enterprise project publishing and project status management
- Role creation, editing, and AI role suggestion generation
- Student role application, application history, and cancellation
- Enterprise-side application review
- Deliverable submission with text, file upload, and external links
- Admin dashboard for users, projects, applications, and feedback records

## Tech Stack

- Backend: Flask
- Frontend: Vanilla HTML / CSS / JavaScript
- Database: SQLite
- AI: DeepSeek API
- Deployment: Nginx + Gunicorn + Supervisor

## Project Structure

```text
.
├─frontend/              Frontend pages, styles, uploaded files
├─server/                Flask backend
├─scripts/               Utility scripts, including demo data reset
├─docs/                  API and database design docs
├─multi_role_platform.db SQLite database file
├─requirements.txt       Python dependencies
└─README.md
```

## Main Pages

- `/index.html` — landing page
- `/login.html` — login page
- `/register.html` — register page
- `/project_list.html` — public project list
- `/project_detail.html` — public project detail
- `/my_applications.html` — student application history
- `/enterprise_center.html` — enterprise dashboard
- `/enterprise_publish.html` — enterprise project publishing
- `/enterprise_roles.html` — enterprise role management
- `/enterprise_review.html` — enterprise application review
- `/enterprise_project_detail.html?project_id=<id>` — enterprise project detail
- `/enterprise_feedback.html?project_id=<id>` — enterprise feedback management
- `/feedback_submit.html?role_id=<id>&project_id=<id>` — deliverable submission
- `/project_progress.html?project_id=<id>` — project progress / deliverables view
- `/admin_dashboard.html` — admin dashboard

## API Overview

Core API modules:

- `server/auth.py`
- `server/projects.py`
- `server/applications.py`
- `server/admin.py`

Detailed API summary:

- `docs/10.2_api_summary.md`

## Local Development

### 1. Install dependencies

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Windows PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Configure environment variables

Create `.env` in the project root:

```env
DEEPSEEK_API_KEY=your_key
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_TIMEOUT=60
```

Notes:

- `.env.local` has higher priority than `.env`
- If `DEEPSEEK_API_KEY` is missing or invalid, AI role suggestion will fall back to a local stub

### 3. Start the project

Entry point:

- `server/wsgi.py`

Example:

```bash
cd server
python wsgi.py
```

Or package mode:

```bash
python -m server.wsgi
```

## Database and Demo Data

Database file:

- `multi_role_platform.db`

Database initialization logic:

- `server/db.py`

Demo reset script:

- `scripts/reset_demo_data.py`

What it does:

- backs up the current database to `backups/`
- preserves the admin account
- removes old projects, applications, and feedback records
- recreates demo users and demo projects

Run it with:

```bash
python scripts/reset_demo_data.py
```

## AI Role Suggestion

The AI role suggestion endpoint tries to call DeepSeek first.

If any of the following happens, it automatically falls back to a local role suggestion stub:

- missing API key
- timeout
- external API error
- empty or invalid model output

Relevant backend file:

- `server/projects.py`

## File Upload Behavior

Deliverable attachments use a file-on-disk + path-in-database approach.

- Uploaded files are stored in: `frontend/uploads/feedbacks/`
- Database field used for attachment reference: `role_feedback.evidence_url`

If you want to preserve historical uploaded files during deployment or migration, you must keep both:

- `multi_role_platform.db`
- `frontend/uploads/feedbacks/`

## Deployment

Current production-style deployment stack:

- Nginx serves static frontend files
- Gunicorn runs the Flask app
- Supervisor manages Gunicorn

Deployment notes and update commands:

- `DEPLOY.md`

Important note:

- The current frontend is organized around explicit static `.html` pages
- If your Nginx config uses `try_files ... /index.html`, it is safer to link to real static page paths instead of relying on backend page routes

## Documentation

- `docs/10.2_api_summary.md` — API summary
- `docs/10.3_database_design.md` — database design
- `docs/ai_role_split_contract.md` — AI role split contract

## Current Status

This project already covers the main MVP scope needed for a demo or competition presentation.

It is suitable for:

- local demonstration
- cloud deployment demo
- coursework / competition showcase

If the project continues beyond the MVP stage, the next priorities would be:

- improving external model-call stability
- making deployment updates more repeatable
- improving long-term storage strategy for uploaded files and structured data
