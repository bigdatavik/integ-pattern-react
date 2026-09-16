# Integration Pattern Accelerator (React)

A Databricks App that helps data developers select a predefined ingestion
pattern, provide configuration, upload requirements, and generate a reusable
implementation package in Unity Catalog Volumes — then execute it via Genie
Code.

React (JSX) frontend + FastAPI backend, deployed to **Databricks Apps** via
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

---

## Deploy to a New Workspace

Anyone can deploy this to their own Databricks workspace. Nothing in the repo is
tied to a specific workspace — you supply the workspace (via a CLI profile) and
the target catalog/schema.

### Prerequisites

- **Databricks CLI ≥ v1.0** — `databricks -v` ([install](https://docs.databricks.com/dev-tools/cli/install.html))
- **An authenticated CLI profile** for the target workspace:
  ```bash
  databricks auth login --host https://<your-workspace>.cloud.databricks.com --profile <profile>
  ```
- **A Unity Catalog schema** the app can write into (any catalog + schema you
  have `CREATE VOLUME` on). Create one if needed:
  ```bash
  databricks schemas create integration_pattern <catalog> --profile <profile>
  ```
- **Foundation Model access** — the app calls `databricks-claude-sonnet-*`
  endpoints for prompt generation. If they aren't available it falls back to a
  deterministic template (still works).
- **Permission** to create Databricks Apps in the workspace.

### Step 1 — Point the bundle at your catalog/schema

Either edit the `catalog` / `schema` defaults in `databricks.yml`, or pass them
at deploy time with `--var` (shown below). Defaults are `main` /
`integration_pattern`.

### Step 2 — Deploy (creates the app + uploads source)

```bash
databricks bundle validate -t dev -p <profile>

databricks bundle deploy   -t dev -p <profile> \
  --var="catalog=<catalog>" --var="schema=<schema>"
```

This creates the app `integ-pattern-react`, which auto-provisions a **service
principal (SP)**. The OAuth scopes it needs (`sql`, `files`, `genie`, `apps`,
`catalog.*`, `workspace.workspace`) are declared in
`resources/integ-pattern-react.app.yml` and applied automatically.

### Step 3 — Start / run the app

```bash
databricks bundle run integ_pattern_react -t dev -p <profile>
```

The app URL is printed at the end. (First start provisions compute — allow a
few minutes.)

### Step 4 — Grant the app SP Unity Catalog access (one-time, catalog admin)

The SP only exists after Step 2, so its UC grants can't be set in the bundle up
front. Find its client id, then run the grant script:

```bash
# Get the app's SP client id
databricks apps get integ-pattern-react -p <profile> -o json \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['service_principal_client_id'])"
```

Then run the five `GRANT` statements in `scripts/grant_uc_permissions.sql`
(substitute `<catalog>`, `<schema>`, and `<sp>`) from a SQL editor or:

```bash
databricks sql query --profile <profile> ...   # or paste into the SQL editor
```

These grant `USE CATALOG`, `USE SCHEMA`, and `READ`/`WRITE`/`CREATE VOLUME`.

### Step 5 — Verify

```bash
databricks apps get integ-pattern-react -p <profile> -o json \
  | python3 -c "import sys,json;d=json.load(sys.stdin);print('state:',d['app_status']['state'],'| url:',d['url'])"
```

State should be `RUNNING`. Open the URL — the pattern cards should load.

### Production target

`databricks.yml` also defines a `prod` target (production mode, single deployed
copy under your workspace user path). Deploy it the same way with `-t prod`.

### Redeploying after changes

```bash
databricks bundle deploy -t dev -p <profile> && \
databricks bundle run integ_pattern_react -t dev -p <profile>
```

---

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

### Enable the Genie Code Job Task preview (required for this button)

The Genie Code job task is in **Beta**. Before the **Execute with Genie Code**
button works, a workspace admin must turn on the preview:

**Settings → Developer → Previews → "Genie Code Job Task" → On**

> **Genie Code Job Task** `Beta` — *Enables genie code as a task type in jobs.*

Docs: https://docs.databricks.com/aws/en/jobs/tasks/genie-code

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
