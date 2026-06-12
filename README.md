## newsstore collector (Step 1)

Polls free RSS feeds (`config/feeds.yaml`) and stores deduplicated raw items in SQLite. No LLM (that is Step 2).

### Run (Docker only — host has no Python)

```
docker build -f infra/Dockerfile -t newsstore .
# one collection pass (office = behind corporate ePrism proxy)
docker run --rm -e APP_ENV=office -v ${PWD}:/app newsstore python -m newsstore.run --force
# tests
docker run --rm -v ${PWD}:/app newsstore pytest -q
```

`APP_ENV=home` skips the ePrism cert. Data persists in `data/newsstore.db` (volume-mounted).
Scheduling (every 5 min) is external (Cloud Scheduler / cron) — the runner does one pass per invocation.

### Storage backend

Default is SQLite (`data/newsstore.db`). To write to Firestore instead, build with the `[gcp]` extra and set env vars — the collector code is identical:

```
# local/tests: SQLite (default), nothing to set
# cloud: Firestore
NEWSSTORE_BACKEND=firestore
GOOGLE_CLOUD_PROJECT=<your-gcp-project>
```

Firestore auth uses Application Default Credentials (on Cloud Run, the job's service account — no key file). See the GCP deploy plan.
