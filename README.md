# Integration Pattern Accelerator (React)

A Databricks App that helps data developers select a predefined ingestion
pattern, provide configuration, upload requirements, and generate a reusable
implementation package in Unity Catalog Volumes — then execute it via Genie
Code.

React (JSX) frontend + FastAPI backend, deployed to Databricks Apps via
**Databricks Asset Bundles (DABs)**.

## What It Does

1. **Pattern Selection** — Choose from ADLS-to-Bronze or Oracle-to-Bronze
2. **Configuration** — Enter catalog, schema, volume, source, and target details
3. **Requirements** — Upload a requirements doc or enter requirements manually
4. **Package Generation** — Generates config, an LLM-powered prompt, starter
   notebooks, sample data, and test artifacts in a UC Volume
5. **Execute with Genie Code** — Submits the generated prompt as a Genie Code
   job task that autonomously generates and runs the implementation

## Project Structure

```
.
├── databricks.yml                       # Bundle config + dev/prod targets
├── resources/
│   └── integ-pattern-react.app.yml      # Databricks App resource (name, scopes, source)
├── app/                                 # App source (source_code_path)
│   ├── app.py                           # FastAPI backend (generate, run-prompt)
│   ├── app.yaml                         # App runtime command (uvicorn)
│   ├── requirements.txt                 # fastapi, uvicorn, databricks-sdk
│   ├── src/                             # Package generator, patterns, prompt gen
│   └── static/                          # index.html + app.jsx (React UI)
└── scripts/
    └── grant_uc_permissions.sql         # One-time UC grants for the app SP
```

## Deploy with DABs

Prerequisites: Databricks CLI (`databricks -v`) and an authenticated profile
(`fevm` is the default target profile — change it in `databricks.yml` if needed).

```bash
# 1. Validate the bundle
databricks bundle validate --target dev

# 2. Deploy (uploads app source + creates/updates the app)
databricks bundle deploy --target dev

# 3. Start / run the app
databricks bundle run integ_pattern_react --target dev
```

`databricks bundle deploy` creates the app on first run, which auto-provisions a
service principal (SP). The OAuth scopes the app needs are declared in
`resources/integ-pattern-react.app.yml` and applied automatically.

### One-time UC grants (catalog admin)

The app's SP is only minted once the app is created, so its Unity Catalog
grants can't be set in the bundle up front. After the first deploy, grant them:

```bash
# Find the app's SP client id
databricks apps get integ-pattern-react --target dev -o json \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['service_principal_client_id'])"
```

Then run `scripts/grant_uc_permissions.sql` as a catalog admin (substitute the
SP client id for `:sp`). This grants `USE CATALOG`, `USE SCHEMA`, and
`READ`/`WRITE`/`CREATE VOLUME` on `humana_payer.integration_pattern`.

### Targets

`databricks.yml` defines `dev` (development mode, per-user isolated app name)
and `prod` (production mode). Catalog/schema defaults are set per target via
bundle variables.

## Genie Code Integration

The **Execute with Genie Code** button (`/api/run-prompt`) works by:

1. Creating a Genie Code automation via
   `POST /api/2.0/alerts-internal/scheduled-insights`
   (`insight_type: "GENIE_CODE"`) with the generated prompt
2. Getting a `configuration_id` from the response
3. Submitting a one-time job run via `POST /api/2.1/jobs/runs/submit`
   with `genie_task: {configuration_id}`
4. Returning the job run URL so the user can monitor progress

**Auth requirement:** `/api/run-prompt` uses `auth_type="oauth-m2m"` with the
app's SP credentials. The `scheduled-insights` API requires the `all-apis`
OAuth scope, which is only available on M2M tokens — not on the scope-restricted
user-auth token the platform injects when `user_api_scopes` is set. Do **not**
change this endpoint to user-token auth.

The Genie Code job task is in **Beta** — a workspace admin must enable it under
**Settings → Previews** before the button works.

## Pitfalls & Lessons Learned

- **`all-apis` is not a valid app scope.** Databricks Apps accept only named
  scopes (`sql`, `files`, `genie`, `catalog.*`, `workspace.workspace`, …).
- **Genie Code endpoint must use M2M auth** — the injected user token is scope
  restricted and lacks `all-apis`.
- **Genie Code task is Beta** — enable it in workspace previews first.
- **UC grants need catalog admin** and can't be automated inside the app.

## Known Limitations

- **Prototype** — not production-hardened for multi-user concurrent use.
- **No live ADLS/Oracle** — demo mode uses generated sample data.
- **PDF/DOCX extraction** — requires optional `PyPDF2` / `python-docx`.
- **LLM availability** — falls back to a deterministic template if the
  Foundation Model endpoints are unreachable.
