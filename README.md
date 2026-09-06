# Running Tracker

A small multi-user site that pairs with a Garmin running watch: your watch does the actual
run (start/stop, GPS, heart rate), Garmin Connect gets the synced activity, and this site
pulls it in, lets you tag which shoes you wore, and shows the stats that matter for running
(distance, duration, pace, avg/max heart rate, elevation) alongside per-shoe mileage.

## How Garmin integration works

Garmin has no accessible public API for personal projects (their official Health API requires
business approval). This uses [`garminconnect`](https://github.com/cyberjunky/python-garminconnect),
an actively-maintained unofficial library that logs in as you via Garmin's own mobile-app API.
Concretely:

1. On the Garmin settings page, you enter your Garmin email/password once.
2. If Garmin challenges the login with a verification code (MFA), you're prompted for it.
3. On success, the resulting **session token** (not your password) is encrypted and stored.
   Your password is never persisted - it's only used for that one login request.
4. Every sync (manual "Sync now" button, or the background job every `SYNC_INTERVAL_MINUTES`)
   reuses that stored token. If it ever fully expires, the UI will ask you to reconnect.

This is a real tradeoff: it depends on an unofficial library and Garmin's undocumented backend,
so it can break if Garmin changes something (this has happened before - see `garth`'s
deprecation in early 2026, which is why this project uses `garminconnect` instead, which
maintains its own resilient multi-strategy login rather than depending on `garth`).

**Important deployment constraint**: the MFA step is held in server memory between "enter
password" and "enter code", so this app must run as a **single process/worker**. The provided
Dockerfile already sets `--workers 1`. Don't scale this past one instance without changing that.

## Local setup

```bash
cd running-tracker
python -m venv venv
./venv/Scripts/activate        # on Windows; use `source venv/bin/activate` on macOS/Linux
pip install -r requirements.txt

cp .env.example .env
# Fill in SECRET_KEY and GARMIN_TOKEN_ENC_KEY in .env (commands to generate them are in the file)

uvicorn app.main:app --reload
```

Then open http://127.0.0.1:8000, register an account, add a shoe, and connect Garmin from
the Garmin settings page.

## Deployment (Render free tier + GitHub)

This repo deploys straight from GitHub to Render using the included `render.yaml`. Render's
**free** web service tier has two consequences worth knowing before you rely on it:

- **It spins down after ~15 minutes of no traffic.** The next visit wakes it back up in
  about 30 seconds. It is not literally always-on; it's "always reachable, sometimes slow to
  answer the first request." The background auto-sync job also only runs while the service is
  awake - open the site (or hit "Sync now") to catch it up after it's been idle.
- **It has no persistent disk**, so SQLite would be wiped on every redeploy/restart. This repo
  therefore needs a real external database in production - a free
  [Neon](https://neon.tech) Postgres project works well and never expires.

### One-time setup

1. **Create a free Neon Postgres project** at neon.tech, and copy its connection string. It
   looks like `postgresql://user:password@ep-xxxx.neon.tech/dbname?sslmode=require` - change
   the scheme to `postgresql+psycopg://` (this app uses the psycopg3 driver), so the final
   value looks like:
   `postgresql+psycopg://user:password@ep-xxxx.neon.tech/dbname?sslmode=require`
2. **Push this repo to GitHub** (see below) if you haven't already.
3. On [render.com](https://render.com), **New + → Blueprint**, connect your GitHub repo -
   Render reads `render.yaml` and creates the web service automatically.
4. Render will ask you to fill in the env vars marked `sync: false` in `render.yaml`:
   - `SECRET_KEY` - generate with `python -c "import secrets; print(secrets.token_urlsafe(32))"`
   - `GARMIN_TOKEN_ENC_KEY` - generate with
     `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
   - `DATABASE_URL` - the Neon connection string from step 1
5. Deploy. Every future `git push` to the connected branch auto-redeploys.

Since there's no persistent disk and only one instance, the app's single-worker/in-memory-MFA
design (see above) fits Render's free tier natively - no extra config needed there.

### Pushing to GitHub

```bash
cd running-tracker
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/<you>/<repo>.git
git push -u origin main
```

### Alternative: always-on hosting

If the spin-down behavior becomes annoying, Render's paid Starter plan (~$7/month) removes it
and adds a real persistent disk (so you could go back to SQLite if you wanted). Fly.io's free
allowance and a small VPS are the other options discussed when this app was first scoped - both
work with the same `Dockerfile`, just set `DATABASE_URL`, `SECRET_KEY`, `GARMIN_TOKEN_ENC_KEY`,
and `COOKIE_SECURE=true` as real environment variables there too, and keep it to one instance.

## Project layout

```
app/
  main.py            FastAPI app wiring
  config.py            Environment variables
  database.py            SQLAlchemy engine/session
  models.py                 User, GarminLink, Shoe, Run
  security.py                  Password hashing, session cookies, auth dependency
  crypto.py                       Encrypts the stored Garmin session token
  garmin_client.py                   Garmin login/MFA/sync logic
  scheduler.py                          Background auto-sync job
  routers/                                 auth, garmin, shoes, runs, dashboard
  templates/, static/                        Server-rendered pages, Chart.js dashboard
```
