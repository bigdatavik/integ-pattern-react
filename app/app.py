"""FastAPI backend for Integration Pattern Accelerator (React edition)."""

import json
import logging
import os
import queue
import threading

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from src.config_models import IntegrationConfig, OracleConfig, VolumeSourceConfig
from src.package_generator import generate_package
from src.pattern_definitions import get_all_patterns
from src.requirements_processor import combine_requirements, extract_text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Integration Pattern Accelerator")

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def root():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/api/patterns")
async def patterns():
    return get_all_patterns()


@app.post("/api/generate")
async def generate_endpoint(
    request: Request,
    config_json: str = Form(...),
    file: UploadFile = File(None),
):
    """Generate a full integration package. Streams SSE progress events."""
    try:
        cfg = json.loads(config_json)
    except json.JSONDecodeError as e:
        return JSONResponse(status_code=400, content={"errors": [f"Invalid JSON: {e}"]})

    volume_source = None
    if cfg.get("volume_source"):
        vs = cfg["volume_source"]
        volume_source = VolumeSourceConfig(
            source_volume=vs.get("source_volume", ""),
            source_path=vs.get("source_path", ""),
            file_format=vs.get("file_format", "csv"),
            file_pattern=vs.get("file_pattern", "*"),
        )

    oracle_config = None
    if cfg.get("oracle_config"):
        oc = cfg["oracle_config"]
        oracle_config = OracleConfig(
            jdbc_url=oc.get("jdbc_url", ""),
            source_table=oc.get("source_table", ""),
            watermark_column=oc.get("watermark_column", ""),
        )

    config = IntegrationConfig(
        pattern_id=cfg.get("pattern_id", ""),
        pattern_name=cfg.get("pattern_name", ""),
        catalog_name=cfg.get("catalog_name", ""),
        schema_name=cfg.get("schema_name", ""),
        target_schema=cfg.get("target_schema", ""),
        target_table=cfg.get("target_table", ""),
        target_description=cfg.get("target_description", ""),
        artifacts_volume=cfg.get("artifacts_volume", ""),
        business_domain=cfg.get("business_domain", ""),
        requirements_text=cfg.get("requirements_text", ""),
        volume_source=volume_source,
        oracle_config=oracle_config,
    )

    errors = config.validate()
    if errors:
        return JSONResponse(status_code=400, content={"errors": errors})

    uploaded_bytes = None
    uploaded_name = None
    if file and file.filename:
        uploaded_bytes = await file.read()
        uploaded_name = file.filename
        extracted, ok = extract_text(uploaded_bytes, uploaded_name)
        if ok:
            config.requirements_text = combine_requirements(
                extracted, config.requirements_text
            )

    # Use the app SP credentials for UC + Claude operations.
    # The SP needs USE CATALOG, USE SCHEMA, volume, and table grants.
    # (User's forwarded token doesn't include the unity-catalog scope.)
    from databricks.sdk import WorkspaceClient as _WC
    sp_client = _WC()
    logger.info("Using app SP credentials for UC operations")

    progress_q: queue.Queue = queue.Queue()
    result_holder: list = [None]
    error_holder: list = [None]

    def _run():
        def _cb(step, total, msg):
            progress_q.put({"type": "progress", "step": step, "total": total, "message": msg})

        try:
            result_holder[0] = generate_package(
                config=config,
                uploaded_file_bytes=uploaded_bytes,
                uploaded_file_name=uploaded_name,
                progress_callback=_cb,
                workspace_client=sp_client,
            )
        except Exception as exc:
            error_holder[0] = str(exc)
        finally:
            progress_q.put(None)

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    async def _stream():
        while True:
            try:
                item = progress_q.get(timeout=0.5)
            except queue.Empty:
                yield ": keepalive\n\n"
                continue
            if item is None:
                break
            yield f"data: {json.dumps(item)}\n\n"

        if error_holder[0]:
            yield f"data: {json.dumps({'type': 'error', 'message': error_holder[0]})}\n\n"
        elif result_holder[0]:
            r = result_holder[0]
            yield f"data: {json.dumps({'type': 'complete', 'result': {'package_id': r['package_id'], 'package_path': r['package_path'], 'artifacts': r['artifacts'], 'prompt': r['prompt'], 'used_llm': r['used_llm'], 'llm_detail': r['llm_detail'], 'volume_status': r['volume_status']}})}\n\n"

    return StreamingResponse(_stream(), media_type="text/event-stream")


@app.post("/api/run-prompt")
async def run_prompt_endpoint(request: Request):
    """Create a Genie Code automation and submit a one-time job run.

    Flow:
      1. Create a scheduled-insight automation (no schedule) with the prompt
      2. Submit a one-shot job run with a genie_task pointing to it
      3. Return the run URL so the user can monitor progress
    """
    body = await request.json()
    prompt = body.get("prompt", "")
    run_name = body.get("run_name", "Integration Pattern - Genie Code")

    if not prompt:
        return JSONResponse(status_code=400, content={"error": "Prompt is required"})

    try:
        from databricks.sdk import WorkspaceClient

        # The /api/2.0/alerts-internal/scheduled-insights endpoint requires
        # the "all-apis" OAuth scope. User-auth tokens (X-Forwarded-Access-Token)
        # only carry the app's declared scopes (genie, sql, etc.) — never
        # all-apis. So we MUST use the SP's M2M credentials here, which get
        # all-apis from the OAuth server automatically.
        host = os.environ.get("DATABRICKS_HOST", "").rstrip("/")
        w = WorkspaceClient(
            host=host,
            client_id=os.environ.get("DATABRICKS_CLIENT_ID", ""),
            client_secret=os.environ.get("DATABRICKS_CLIENT_SECRET", ""),
            auth_type="oauth-m2m",
        )
        logger.info("Using SP M2M credentials for Genie Code API")

        uid = w.current_user.me().id

        # 1. Create a dedicated Genie Code automation (no schedule = job-driven only)
        insight_resp = w.api_client.do(
            "POST",
            "/api/2.0/alerts-internal/scheduled-insights",
            body={
                "parent_asset_name": f"users/{uid}",
                "scheduled_insight": {
                    "insight_type": "GENIE_CODE",
                    "user_prompt": prompt,
                },
            },
        )
        configuration_id = insight_resp["name"]
        logger.info("Created Genie Code automation: %s", configuration_id)

        # 2. Submit a one-time job run with the genie_task
        run_resp = w.api_client.do(
            "POST",
            "/api/2.1/jobs/runs/submit",
            body={
                "run_name": run_name,
                "tasks": [
                    {
                        "task_key": "implement_pattern",
                        "genie_task": {"configuration_id": configuration_id},
                    }
                ],
            },
        )
        run_id = run_resp["run_id"]
        logger.info("Submitted job run %s", run_id)

        # Fetch the run to get the correct run_page_url from the API
        run_detail = w.api_client.do("GET", f"/api/2.1/jobs/runs/get?run_id={run_id}")
        run_url = run_detail.get("run_page_url", f"{host}/#job/runs/{run_id}")

        return {
            "success": True,
            "run_id": run_id,
            "run_url": run_url,
            "configuration_id": configuration_id,
        }
    except Exception as exc:
        logger.exception("Failed to create Genie Code job run")
        return JSONResponse(status_code=500, content={"error": str(exc)})
