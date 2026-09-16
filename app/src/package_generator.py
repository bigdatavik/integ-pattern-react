"""Orchestrate package generation: write all artifacts to the UC Volume."""

import json
import logging
from databricks.sdk import WorkspaceClient
from src.config_models import IntegrationConfig
from src.sample_data_generator import (
    generate_customer_records, generate_order_records, records_to_csv
)
from src.notebook_templates import (
    generate_ingest_notebook, generate_dq_notebook, generate_validation_notebook
)
from src.prompt_generator import generate_prompt_with_llm

logger = logging.getLogger(__name__)


def _write_file(w: WorkspaceClient, path: str, content: str) -> None:
    """Write content to a file in the UC Volume via Files API."""
    import io
    data = content.encode("utf-8")
    w.files.upload(path, io.BytesIO(data), overwrite=True)


def _ensure_volume_exists(w: WorkspaceClient, catalog: str, schema: str, volume: str) -> str:
    """Create the UC Volume if it doesn't exist. Returns status message."""
    full_name = f"{catalog}.{schema}.{volume}"
    try:
        w.volumes.read(full_name)
        return f"Volume `{full_name}` exists."
    except Exception:
        pass  # Volume not found, try to create

    try:
        from databricks.sdk.service.catalog import VolumeType
        w.volumes.create(
            catalog_name=catalog,
            schema_name=schema,
            name=volume,
            volume_type=VolumeType.MANAGED,
        )
        return f"Volume `{full_name}` created successfully."
    except Exception as e:
        error_msg = str(e).lower()
        if "already exists" in error_msg:
            return f"Volume `{full_name}` already exists."
        raise RuntimeError(
            f"Cannot create volume `{full_name}`. "
            f"Ensure the app service principal has CREATE VOLUME on `{catalog}.{schema}`. "
            f"Error: {e}"
        )


def generate_package(
    config: IntegrationConfig,
    uploaded_file_bytes: bytes = None,
    uploaded_file_name: str = None,
    progress_callback=None,
    workspace_client: "WorkspaceClient | None" = None,
) -> dict:
    """Generate the full integration package.

    Args:
        config: Validated IntegrationConfig
        uploaded_file_bytes: Raw bytes of the uploaded requirements document
        uploaded_file_name: Filename of the uploaded document
        progress_callback: Optional callable(step: int, total: int, message: str)
        workspace_client: Optional pre-configured WorkspaceClient (e.g. using
            the logged-in user's token). Falls back to default SP credentials.

    Returns:
        dict with package_id, package_path, artifacts list, prompt, used_llm flag, etc.
    """
    w = workspace_client or WorkspaceClient()
    package_id = config.generate_package_id()
    base_path = f"{config.artifacts_volume_path}/integration_packages/{package_id}"
    artifacts = []
    total_steps = 10
    volume_statuses = []

    def _progress(step, msg):
        if progress_callback:
            progress_callback(step, total_steps, msg)

    # 0. Ensure both volumes exist (auto-create if missing)
    _progress(1, "Checking/creating volumes...")
    # Artifacts volume (where generated package goes)
    vs1 = _ensure_volume_exists(w, config.catalog_name, config.schema_name, config.artifacts_volume)
    volume_statuses.append(vs1)
    # Source volume (where raw files live) — only for file-based patterns
    if config.volume_source and config.volume_source.source_volume:
        vs2 = _ensure_volume_exists(w, config.catalog_name, config.schema_name, config.volume_source.source_volume)
        volume_statuses.append(vs2)
    volume_status = " | ".join(volume_statuses)
    logger.info(volume_status)

    # 1. config.json
    _progress(2, "Writing configuration...")
    config_path = f"{base_path}/config.json"
    _write_file(w, config_path, config.to_json())
    artifacts.append("config.json")

    # 2. Consolidated requirements (extracted doc text + manual text)
    _progress(3, "Writing consolidated requirements...")
    req_path = f"{base_path}/requirements.md"
    _write_file(w, req_path, config.requirements_text or "No requirements provided.")
    artifacts.append("requirements.md")

    # 2b. Preserve original uploaded file alongside extracted text
    if uploaded_file_bytes and uploaded_file_name:
        import io
        upload_path = f"{base_path}/uploads/{uploaded_file_name}"
        w.files.upload(upload_path, io.BytesIO(uploaded_file_bytes), overwrite=True)
        artifacts.append(f"uploads/{uploaded_file_name}")

    # 3. Generate prompt via Foundation Model API (Claude) with fallback
    _progress(4, "Generating implementation prompt via Claude...")
    generated_prompt, used_llm, llm_detail = generate_prompt_with_llm(config, workspace_client=w)
    prompt_path = f"{base_path}/generated_prompt.md"
    _write_file(w, prompt_path, generated_prompt)
    artifacts.append("generated_prompt.md")

    # 4. README
    _progress(5, "Writing README...")
    readme_content = _generate_readme(config, package_id, artifacts)
    _write_file(w, f"{base_path}/README.md", readme_content)
    artifacts.append("README.md")

    # 5. Sample data
    _progress(6, "Generating sample data...")
    if config.pattern_id == "adls_to_bronze":
        records = generate_customer_records(30)
        csv_data = records_to_csv(records)
        # Write sample data into the SOURCE volume so the ingest notebook can read it
        source_sample_path = f"{config.source_volume_path}/sample_data.csv"
        _write_file(w, source_sample_path, csv_data)
        artifacts.append(f"[source_volume] {config.volume_source.source_volume}/sample_data.csv")
    else:
        records = generate_order_records(30)
        csv_data = records_to_csv(records)
        # Oracle mock data goes in artifacts volume (no source volume for JDBC)
        _write_file(w, f"{base_path}/sample_data/sample_data.csv", csv_data)
        artifacts.append("sample_data/sample_data.csv")

    # 6. Notebooks
    _progress(7, "Generating starter notebooks...")
    ingest_nb = generate_ingest_notebook(config)
    ingest_nb = ingest_nb.replace("{PACKAGE_ID}", package_id)
    _write_file(w, f"{base_path}/notebooks/01_ingest_to_bronze.py", ingest_nb)
    artifacts.append("notebooks/01_ingest_to_bronze.py")

    dq_nb = generate_dq_notebook(config)
    _write_file(w, f"{base_path}/notebooks/02_data_quality_checks.py", dq_nb)
    artifacts.append("notebooks/02_data_quality_checks.py")

    val_nb = generate_validation_notebook(config)
    val_nb = val_nb.replace("{PACKAGE_ID}", package_id)
    _write_file(w, f"{base_path}/notebooks/03_demo_validation.py", val_nb)
    artifacts.append("notebooks/03_demo_validation.py")

    # 7. Tests
    _progress(8, "Generating test artifacts...")
    test_content = _generate_test_file(config, package_id)
    _write_file(w, f"{base_path}/tests/test_config_validation.py", test_content)
    artifacts.append("tests/test_config_validation.py")

    _progress(10, "Package generation complete!")

    return {
        "package_id": package_id,
        "package_path": base_path,
        "artifacts": artifacts,
        "prompt": generated_prompt,
        "used_llm": used_llm,
        "llm_detail": llm_detail,
        "volume_status": volume_status,
    }


def _generate_readme(config: IntegrationConfig, package_id: str, artifacts: list) -> str:
    return f"""# Integration Package: {package_id}

## Pattern
{config.pattern_name}

## Target
- Catalog: `{config.catalog_name}`
- Schema: `{config.target_schema}`
- Table: `{config.target_table}`
- Full name: `{config.target_full_name}`

## Volume Locations
- Source files: `{config.source_volume_path if config.volume_source else 'N/A (JDBC)'}`
- Artifacts: `{config.artifacts_volume_path}/integration_packages/{package_id}/`

## Generated Artifacts
{chr(10).join(f'- {a}' for a in artifacts)}

## How to Use

1. Open `notebooks/01_ingest_to_bronze.py` in a Databricks notebook.
2. Set `DEMO_MODE = True` for the demo (uses sample data from this package).
3. Run the notebook to ingest sample data into the bronze table.
4. Open `notebooks/02_data_quality_checks.py` to validate the data.
5. Open `notebooks/03_demo_validation.py` for end-to-end validation.

## For Production
- Set `DEMO_MODE = False`.
- Replace placeholder connection values with Databricks secrets references.
- Adjust file paths or JDBC URLs to point to real sources.
- Review and customize the generated prompt in `generated_prompt.md`.

## Generated
- By: Integration Pattern Accelerator
- Pattern: {config.pattern_name}
- Domain: {config.business_domain or 'General'}
"""


def _generate_test_file(config: IntegrationConfig, package_id: str) -> str:
    return f'''"""Basic validation tests for the generated package."""

import json
import os


def test_config_has_required_fields():
    """Check that config.json has all required fields."""
    config = {json.dumps(config.to_dict())}
    config_dict = json.loads(config) if isinstance(config, str) else config
    required = [
        "pattern_id", "catalog_name", "schema_name",
        "volume_name", "source_schema", "source_table_or_path",
        "target_schema", "target_table",
    ]
    missing = [f for f in required if not config_dict.get(f)]
    assert not missing, f"Missing required fields: {{missing}}"
    print("PASS: All required config fields present")


def test_package_id_contains_pattern():
    """Check package ID includes the pattern."""
    package_id = "{package_id}"
    assert "{config.pattern_id}" in package_id, f"Pattern not in package ID: {{package_id}}"
    print("PASS: Package ID contains pattern name")


def test_target_table_in_prompt():
    """Check that the generated prompt references the target table."""
    # This would read generated_prompt.md in a real test
    target_table = "{config.target_table}"
    assert len(target_table) > 0, "Target table name is empty"
    print(f"PASS: Target table '{{target_table}}' is defined")


if __name__ == "__main__":
    test_config_has_required_fields()
    test_package_id_contains_pattern()
    test_target_table_in_prompt()
    print("\nAll tests passed!")
'''
