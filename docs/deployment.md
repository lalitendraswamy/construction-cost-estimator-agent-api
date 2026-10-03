# Deployment: Render + MongoDB Atlas (free tiers)

```
Next.js (Vercel) ──HTTPS/SSE──▶ Render web service (Docker) ──▶ MongoDB Atlas (M0)
                                        │                         rates · leads · approvals
                                        └──▶ Gemini API           kb_chunks (vector) · checkpoints
```

## 1. MongoDB Atlas (database + vector search)
1. https://cloud.mongodb.com → create a **free M0** cluster (region: Mumbai `ap-south-1`).
2. **Database Access** → add a user with a strong generated password.
3. **Network Access** → add `0.0.0.0/0` (Render's free tier has no static outbound IPs).
4. **Connect → Drivers** → copy the `mongodb+srv://…` string.
5. Put that string in your local `.env` as `MONGODB_URI` (local dev and Render share this one
   database), then prepare it once from your laptop:
   ```powershell
   make indexes seed ingest
   make check-db          # must end with "verdict   : READY"
   ```

## 2. GitHub
Render deploys from a Git repo. `.env` is git-ignored; check with `git status` before the first push.
```powershell
git init; git add .; git commit -m "Initial scaffold"
git branch -M main
git remote add origin https://github.com/<you>/construction-cost-estimator-agent-api.git
git push -u origin main
```

## 3. Render
1. https://dashboard.render.com → **New → Blueprint** → connect the repo. Render reads `render.yaml`.
2. Fill in the prompted secrets: `GOOGLE_API_KEY`, `MONGODB_URI` (Atlas string), `OWNER_EMAIL`, `OWNER_WHATSAPP`.
   `ADMIN_API_KEY` is auto-generated: copy it from **Environment**.
3. Set `CORS_ORIGINS` to your site, e.g. `["https://your-site.vercel.app","https://sadhguruassociates.in"]`.
4. Deploy. Verify:
   ```powershell
   curl.exe https://<service>.onrender.com/health/ready
   curl.exe -X POST "https://<service>.onrender.com/api/v1/chat?stream=false" -H "content-type: application/json" -d '{\"thread_id\":\"prod-test-01\",\"message\":\"hello\"}'
   ```

Every push to `main` redeploys (`autoDeploy: true`). Render only switches traffic once `/health/ready` passes.

## Settings that matter in production

| Variable | Value | Why |
|---|---|---|
| `CHECKPOINTER` | `mongodb` | free instances sleep/redeploy; in-memory threads would be lost |
| `APP_ENV` | `production` | JSON logs, `/docs` hidden (use `staging` to keep Swagger) |
| `CORS_ORIGINS` | your real domains | browsers block the chat widget otherwise |
| `RATE_LIMIT_STORAGE_URI` | `memory://` | fine for 1 instance; use Redis when scaling out |

## Free-tier limits to know
* **Render free** sleeps after 15 min idle; the first request then takes ~1 min. Upgrade to *Starter* for a real launch.
* **Gemini free tier** has low requests/minute; each chat turn is 3–5 calls. Google may use free-tier prompts to improve its products, so use a paid key before collecting real customer names and phone numbers.
* **Atlas M0**: 512 MB storage and up to 3 search indexes; plenty for this app.

## Verify a deployment (no Swagger in production)
```powershell
$U = "https://estimator-agent-api.onrender.com"
curl.exe "$U/health/ready"                      # {"status":"ok"} = app + Atlas reachable
$b = @{ thread_id = "prod-check-01"; message = "G+1 standard house, 200 sq yards, Madhurawada" } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "$U/api/v1/chat?stream=false" -ContentType "application/json" -Body $b
```
Expect `event: final` with an `estimate` (₹61.3 L with placeholder rates). Then ask a knowledge
question on the same thread; the reply should list `sources`.

## Troubleshooting
* Deploy fails on startup → Render **Logs**. A missing `GOOGLE_API_KEY` stops startup with a clear message (fail-fast).
* `/health/ready` = 503 → Atlas Network Access or a wrong `MONGODB_URI`.
* `503 Rates unavailable` or RAG says "the knowledge base does not cover it" with `sources: []`
  → the Atlas DB is empty: run `make indexes seed ingest check-db`.
* Never put `# comments` after values in the Render dashboard; they become part of the value.
