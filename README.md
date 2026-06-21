# PostForge

> AI-powered LinkedIn blog and article publishing — from idea to inbox to live post.

PostForge automates your entire LinkedIn content pipeline:

1. **Research** — DuckDuckGo scans trending topics in your niche
2. **Generate** — Claude AI writes a full blog with Mermaid diagrams, tables, and infographics
3. **Review** — Draft lands in your email; reply `ok` to publish or describe changes
4. **Publish** — Auto-posts to LinkedIn as a Post or long-form Article

---

## Stack

| Layer | Tech |
|-------|------|
| Backend | Python 3.12 · FastAPI · SQLite · APScheduler |
| AI | Anthropic Claude (sonnet-4-6 · haiku-4-5) |
| Research | DuckDuckGo (no API key needed) |
| Email | SMTP send + IMAP polling |
| LinkedIn | OAuth 2.0 · UGC Posts API |
| Frontend | Next.js 14 · TypeScript · Tailwind CSS |
| Containers | Docker Compose |

**Ports:** Backend `8040` · Frontend `3040`

---

## Quick Start

```bash
cp .env.example .env
# Fill in ANTHROPIC_API_KEY

# Backend
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload --port 8040

# Frontend (new terminal)
cd frontend && npm install && npm run dev
```

Open `http://localhost:3040` → **Settings** → configure SMTP and LinkedIn → **Niches** → add a niche → **Generate**.

---

## Email Review Flow

PostForge emails you a formatted draft. Reply to it:

| Reply | Action |
|-------|--------|
| `ok` / `approve` / `looks good` | Auto-publishes to LinkedIn |
| Anything else | Treated as revision instructions → revised + resent |

---

## CI Pipeline

GitHub Actions (`.github/workflows/linkedin-post-master.yml`) runs on every push:

- **Backend** — ruff lint + format, pyright type-check, pytest, import smoke-test
- **Frontend** — TypeScript check + Next.js production build
- **Compose** — `docker compose config` validation

---

## Environment Variables

See `.env.example` for the full list. Key variables:

```bash
ANTHROPIC_API_KEY=          # Required
SMTP_HOST=smtp.gmail.com    # Gmail recommended
SMTP_PASSWORD=              # Use a Gmail App Password
REVIEW_EMAIL=               # Where drafts are sent for review
LINKEDIN_CLIENT_ID=         # From developers.linkedin.com
LINKEDIN_CLIENT_SECRET=
```
