# Analytics & Admin Dashboard — Plan

A pragmatic plan for adding usage tracking + an admin dashboard to SchematoAIO. Goal: see who's using the tool, what URLs they're analyzing, which models cost what, and whether the funnel is healthy. Self-hosted on Zo, SQLite-backed, no third-party trackers.

---

## 1. What we want to see

Three pillars:

1. **Reports** — every `/analyze` request: URL, timestamp, GEO score, schema count, model used, success/failure, latency.
2. **Site traffic** — page views, unique visitors (per day), tab interactions, PDF exports, model selection clicks.
3. **Token usage & cost** — per-call input/output tokens, dollar estimate per model, daily/weekly totals.

The dashboard should answer:
- How many analyses today / this week / all-time?
- Which URLs get analyzed most? (same URL repeatedly = potential customer)
- Which model do users pick most?
- What's our average GEO score across analyses? (signals the kind of sites coming in)
- What % of requests fall back to canned content because of LLM failures?
- How much have we spent in LLM credits this billing period?
- What's the rate-limit / 403 / error breakdown?

---

## 2. Storage

**Pick:** SQLite, single file at `data/analytics.db` inside the project.

**Why:** Zero ops, queryable with standard SQL, holds millions of rows comfortably at this scale, no extra services to manage. Backup is `cp analytics.db analytics-2026-05-03.db`.

**Tables:**

```sql
-- One row per /analyze call (success or failure)
CREATE TABLE analyses (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at      TEXT NOT NULL,           -- ISO 8601 UTC
  url             TEXT NOT NULL,           -- the analyzed URL
  url_host        TEXT NOT NULL,           -- extracted hostname (for grouping)
  model_tier      TEXT NOT NULL,           -- 'gemini', 'minimax', etc.
  status          TEXT NOT NULL,           -- 'success' | 'fetch_blocked' | 'rate_limited' | 'llm_out_of_credits' | 'error'
  geo_score       REAL,                    -- nullable on failure
  schema_count    INTEGER,                 -- nullable on failure
  fell_back       INTEGER NOT NULL DEFAULT 0,  -- 1 if LLM tier fallback kicked in
  latency_ms      INTEGER,
  client_ip_hash  TEXT,                    -- SHA-256 of IP (privacy)
  user_agent      TEXT,
  error_message   TEXT
);
CREATE INDEX idx_analyses_created ON analyses(created_at);
CREATE INDEX idx_analyses_host    ON analyses(url_host);

-- One row per LLM call (multiple per /analyze)
CREATE TABLE llm_calls (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  analysis_id     INTEGER REFERENCES analyses(id),
  created_at      TEXT NOT NULL,
  provider        TEXT NOT NULL,           -- 'gemini' | 'zo'
  model_id        TEXT NOT NULL,           -- 'gemini-2.5-flash', etc.
  prompt_kind     TEXT NOT NULL,           -- 'schema_improvements' | 'issues'
  input_tokens    INTEGER,
  output_tokens   INTEGER,
  cost_usd        REAL,                    -- estimated, see § Token accounting
  status          TEXT NOT NULL,           -- 'ok' | 'credits' | 'error'
  latency_ms      INTEGER
);
CREATE INDEX idx_llm_calls_created ON llm_calls(created_at);

-- One row per frontend event (page view, tab click, PDF export, model change)
CREATE TABLE events (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at      TEXT NOT NULL,
  event_type      TEXT NOT NULL,           -- 'page_view' | 'tab_click' | 'pdf_export' | 'model_change'
  payload         TEXT,                    -- JSON blob, schema-free
  client_ip_hash  TEXT,
  session_id      TEXT                     -- random UUID stored in localStorage
);
CREATE INDEX idx_events_created ON events(created_at);
```

Privacy: hash IPs with SHA-256 + a random salt stored in Zo Secrets. We only need IPs for "approximate unique visitors" — never the raw value.

---

## 3. Where to instrument

### Backend (`app/api/routes.py`, `app/services/llm_service.py`)

1. **`/analyze` route** — wrap the handler; on entry record start time + URL + tier; on exit (success or known exception) write one row to `analyses`. Failure path needs to write the right `status` value (the exception type already tells us).

2. **`LLMService._call_gemini` / `_call_zo_ask`** — every call writes one row to `llm_calls`. This is the only place we know the model_id, the response, and whether it was a credits error. Hook it after `resp.raise_for_status()` succeeds, and in the error branch.

3. **Token counting:**
   - **Gemini:** the API response includes `usageMetadata` with `promptTokenCount` and `candidatesTokenCount`. Read directly.
   - **Zo `/ask`:** the response shape isn't documented for us yet. Best-effort: count chars/4 as a rough estimate, OR call Zo's billing endpoint if one exists. Mark `cost_usd` as `NULL` when we can't compute reliably and label it "estimated" in the dashboard.

4. **Cost estimation:** maintain a small `MODEL_PRICING` dict in `app/config.py`:
   ```python
   MODEL_PRICING = {
       "gemini-2.5-flash": {"input": 0.075, "output": 0.30},  # per 1M tokens
       "deepseek-r1-0528": {"input": ..., "output": ...},
       # ...
   }
   ```
   Computed at write time → stored in `cost_usd`. Lets us re-price historical data later if the dict's wrong.

### Frontend (`app/static/app.js`)

Add a thin `track(eventType, payload)` helper that POSTs to a new `/events` endpoint. Fire on:
- Page load → `page_view`
- Tab click → `tab_click` (which tab)
- PDF export → `pdf_export`
- Model dropdown change → `model_change` (which model)

Store a `session_id` in `localStorage` so we can group events per browser session.

---

## 4. Auth — keep the dashboard private

The dashboard is admin-only. Two options:

- **Option A (quick & private):** bearer-token auth. Generate `ADMIN_DASHBOARD_TOKEN` in Zo Secrets, accept `Authorization: Bearer ...` header on `/admin/*` routes. Bookmark the dashboard URL with `?token=...` for convenience (acceptable for a personal tool, not great for shared admins).

- **Option B (more polish):** a single password login that issues an HTTP-only cookie. Slightly more code but feels real. Use `passlib[bcrypt]` to hash the password, store bcrypt hash in Zo Secrets, set a cookie on success.

Recommend A for v1, migrate to B if we onboard a co-admin.

---

## 5. The dashboard UI

Single page at `/admin/dashboard`, server-rendered HTML (Jinja2 — already a FastAPI go-to) with a few small charts. **No SPA framework, no build step.** Use [uPlot](https://github.com/leeoniya/uPlot) (5KB, no deps) or just inline `<canvas>` with Chart.js from CDN.

**Cards (top row):**
- Analyses today / this week / total
- Unique visitors (by `client_ip_hash`) today
- Total LLM cost this month
- Failure rate (last 7 days)

**Charts:**
- Daily analysis count, last 30 days (line)
- Model breakdown, last 7 days (donut)
- Top 10 analyzed hostnames, last 30 days (bar)
- Daily token spend, last 30 days (line, stacked by provider)

**Tables:**
- Recent analyses (last 50): timestamp, URL, model, score, status — clickable to expand error details
- Recent LLM errors (last 20): timestamp, provider, model, status, message

Built with FastAPI + Jinja2 + a single `dashboard.html` + ~200 lines of inline JS for the charts. Probably one weekend of work.

**Bonus endpoints (cheap extras):**
- `/admin/export.csv?table=analyses&from=2026-04-01` — download raw rows for spreadsheet drill-down
- `/admin/health` — simple JSON for uptime monitoring

---

## 6. Rollout phases

**Phase 1 — Logging only (½ day):**
- Create `analytics.db` and tables on app startup
- Instrument `/analyze` and LLM calls
- Verify rows appear via `sqlite3 data/analytics.db ".tables"` — no UI yet

**Phase 2 — Bare-bones dashboard (1 day):**
- Auth-protected `/admin/dashboard`
- Cards + recent-analyses table
- Hostname leaderboard

**Phase 3 — Frontend events + charts (½–1 day):**
- `/events` endpoint + `track()` in app.js
- Daily count chart, model donut, token-spend chart

**Phase 4 — Polish (ongoing):**
- CSV export
- Email digest (weekly summary via `send_email_to_user`)
- Retention policy (e.g., truncate `events` after 90 days to keep DB lean)

---

## 7. Privacy & compliance notes

- **No third-party trackers** (no GA, no Mixpanel) → no cookie-banner needed beyond a one-line note.
- **IP hashing with rotating salt** so the database isn't a goldmine for someone who steals the file.
- **No PII stored** — we don't ask users for emails or names. The `url` field can leak intent, but that's the analyzed URL, not user identity.
- **Robots.txt note:** the dashboard URL should be `Disallow:`'d.

---

## 8. Open questions / decisions for later

- **Where does the SQLite file live?** Local to the service (lost if the container is rebuilt) vs. mounted to a persistent path. Persistent is the right call — make sure `data/analytics.db` is in a directory that survives restarts.
- **Backups?** Daily `cp` to a Zo backup folder is enough for v1. Move to S3 / Dropbox later if data matters.
- **Multi-tenant view?** Right now you're the only admin. If you add a co-founder or contractor, swap bearer-token auth for password auth.
- **Historical token cost accuracy:** Zo `/ask` token reporting is unclear. Worth a small spike to inspect a real response and decide whether to trust it or fall back to char-based estimation.

---

## 9. Cost & effort estimate

| Phase | Effort | Risk |
|---|---|---|
| 1. Logging | ½ day | Low — pure backend instrumentation |
| 2. Dashboard v1 | 1 day | Low — Jinja2 page, simple SQL |
| 3. Events + charts | ½–1 day | Medium — Chart.js + new endpoint |
| 4. Polish | drip | Low |

**Total to v1:** ~2 days of focused dev. No new monthly costs (SQLite is free, FastAPI/Jinja2 already in use).

---

## 10. Files this would touch / create

```
schematoaio/
├── app/
│   ├── analytics/                       # NEW
│   │   ├── __init__.py
│   │   ├── db.py                        # SQLite connection + schema migration
│   │   ├── recorder.py                  # write helpers (record_analysis, record_llm_call, record_event)
│   │   └── queries.py                   # read helpers used by dashboard
│   ├── api/
│   │   ├── routes.py                    # MODIFIED — wrap /analyze
│   │   └── admin_routes.py              # NEW — /admin/* + /events
│   ├── services/
│   │   └── llm_service.py               # MODIFIED — record llm_calls
│   ├── templates/                       # NEW (Jinja2)
│   │   └── dashboard.html
│   └── static/
│       └── app.js                       # MODIFIED — add track() calls
├── data/                                # NEW (gitignored)
│   └── analytics.db
└── PLAN.md                              # this file
```
