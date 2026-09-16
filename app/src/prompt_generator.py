"""Generate code-generation prompts using Databricks Foundation Model API (Claude) with fallback."""

import os
import json
from src.config_models import IntegrationConfig


def _build_system_prompt() -> str:
    return (
        "You are an expert Databricks data engineer. Generate a detailed, structured "
        "implementation prompt that another AI assistant (Genie Code) can use to produce "
        "a complete, runnable Databricks notebook for a data ingestion pipeline. "
        "Be specific about PySpark code, Delta Lake operations, Unity Catalog usage, "
        "error handling, and data quality checks."
    )


def _build_user_prompt(config: IntegrationConfig) -> str:
    parts = [
        f"## Integration Pattern: {config.pattern_name}",
        "",
        "### Source Configuration",
    ]

    if config.volume_source:
        parts.extend([
            f"- Source type: UC Volume (files)",
            f"- Source volume path: `{config.source_volume_path}`",
            f"- File format: {config.volume_source.file_format}",
            f"- File pattern: {config.volume_source.file_pattern}",
        ])
    if config.oracle_config:
        parts.extend([
            f"- Source type: Oracle JDBC",
            f"- JDBC URL: {config.oracle_config.jdbc_url}",
            f"- Oracle source table: {config.oracle_config.source_table}",
            f"- Watermark column: {config.oracle_config.watermark_column or 'N/A'}",
        ])

    parts.extend([
        "",
        "### Target Configuration",
        f"- Unity Catalog: {config.catalog_name}",
        f"- Target schema: {config.target_schema}",
        f"- Target bronze table: {config.target_table}",
        f"- Full table name: {config.target_full_name}",
        f"- Table description: {config.target_description or 'N/A'}",
        f"- Business domain: {config.business_domain or 'N/A'}",
        "",
        "### Volume Locations",
        f"- Source volume: `{config.source_volume_path}`" if config.volume_source else "- Source: Oracle JDBC (no volume)",
        f"- Artifacts volume: `{config.artifacts_volume_path}`",
        "",
        "### Requirements",
        config.requirements_text or "No additional requirements provided.",
        "",
        "### Requested Output",
        "Generate a detailed implementation prompt for Genie Code that covers:",
        "1. Complete ingestion notebook with PySpark code and a COPY INTO alternative",
        "2. Metadata columns: _ingestion_timestamp, _source_file (Volume) or _source_system (Oracle), _load_date",
        "3. Delta table creation with OVERWRITE mode",
        "4. Data quality checks: null counts, duplicate detection, schema validation",
        "5. Error handling and logging",
        "6. Demo mode using sample data from Volume",
        "7. Production mode configuration with proper secret references",
        "8. Testing instructions for the demo",
        "",
        "### Constraints",
        "- Use PySpark (not pandas) for all data operations",
        "- Use Unity Catalog three-level namespace",
        "- Use Delta format for all target tables",
        "- Reference Databricks secrets for credentials, never hardcode",
        "- For file sources, include both a COPY INTO command and a spark.read alternative",
        "- Source files are in a UC Volume path, NOT external ADLS",
        "- Include clear comments for configuration values that need replacement",
    ])

    return "\n".join(parts)


# Foundation Model endpoints to try, in priority order.
# Each tuple: (endpoint_name, supports_temperature)
_LLM_ENDPOINTS = [
    ("databricks-claude-sonnet-4-6", True),
    ("databricks-claude-sonnet-5", False),   # does not support temperature
    ("databricks-claude-sonnet-4-5", True),
    ("databricks-meta-llama-3-3-70b-instruct", True),
]


def generate_prompt_with_llm(config: IntegrationConfig, workspace_client=None) -> tuple:
    """Generate prompt using Databricks Foundation Model API with fallback.

    Tries multiple Claude/LLM endpoints in priority order using the SDK's
    ChatMessage objects. Falls back to a deterministic template if no
    endpoint is reachable.

    Returns:
        Tuple of (generated_prompt: str, used_llm: bool, detail: str)
    """
    user_prompt = _build_user_prompt(config)
    system_prompt = _build_system_prompt()
    errors = []

    try:
        from databricks.sdk import WorkspaceClient
        from databricks.sdk.service.serving import ChatMessage, ChatMessageRole
        w = workspace_client or WorkspaceClient()
    except Exception as e:
        return _generate_fallback_prompt(config), False, f"SDK init failed: {e}"

    messages = [
        ChatMessage(role=ChatMessageRole.SYSTEM, content=system_prompt),
        ChatMessage(role=ChatMessageRole.USER, content=user_prompt),
    ]

    for endpoint, supports_temp in _LLM_ENDPOINTS:
        try:
            kwargs = dict(name=endpoint, messages=messages, max_tokens=4000)
            if supports_temp:
                kwargs["temperature"] = 0.3
            response = w.serving_endpoints.query(**kwargs)
            generated = response.choices[0].message.content
            return generated, True, f"Generated via {endpoint}"
        except Exception as e:
            errors.append(f"{endpoint}: {e}")
            continue

    # All endpoints failed — use deterministic fallback
    detail = "All Foundation Model endpoints unavailable. " + " | ".join(errors)
    print(detail)
    return _generate_fallback_prompt(config), False, detail


def _generate_fallback_prompt(config: IntegrationConfig) -> str:
    """Generate a deterministic fallback prompt when LLM is unavailable."""
    source_type = "ADLS Gen2" if config.pattern_id == "adls_to_bronze" else "Oracle JDBC"

    if config.pattern_id == "adls_to_bronze":
        vs = config.volume_source
        source_details = f"""### Source Details (UC Volume)
- Source volume path: `{config.source_volume_path}`
- File format: {vs.file_format if vs else 'csv'}
- File pattern: {vs.file_pattern if vs else '*'}
- Read option A (COPY INTO — recommended for production):
  ```sql
  COPY INTO {config.target_full_name}
  FROM '{config.source_volume_path}'
  FILEFORMAT = {(vs.file_format if vs else 'CSV').upper()}
  FORMAT_OPTIONS ('header' = 'true', 'inferSchema' = 'true')
  COPY_OPTIONS ('mergeSchema' = 'true')
  ```
- Read option B (spark.read): `spark.read.format("{vs.file_format if vs else 'csv'}").option("header", "true").option("inferSchema", "true").load("{config.source_volume_path}")`
"""
    else:
        oc = config.oracle_config
        source_details = f"""### Source Details (Oracle JDBC)
- JDBC URL: {oc.jdbc_url if oc else 'jdbc:oracle:thin:@//<host>:<port>/<service>'}
- Source table: {oc.source_table if oc else 'SCHEMA.TABLE'}
- Watermark column: {oc.watermark_column if oc else 'N/A'}
- Read using: `spark.read.format("jdbc").option("url", url).option("dbtable", table).option("user", user).option("password", pw).option("driver", "oracle.jdbc.driver.OracleDriver").load()`
- Credentials: Use `dbutils.secrets.get(scope="oracle", key="...")` for all connection values
"""

    return f"""# Genie Code Implementation Prompt
## Integration Pattern: {config.pattern_name}

Generate a complete, runnable Databricks notebook that implements the following {source_type} to Delta Bronze ingestion pipeline.

### Target Configuration
- Unity Catalog: `{config.catalog_name}`
- Target schema: `{config.target_schema}`
- Target table: `{config.target_table}`
- Full name: `{config.target_full_name}`
- Description: {config.target_description or 'Bronze ingestion table'}
- Business domain: {config.business_domain or 'General'}

{source_details}

### Volume Locations
- Source volume: `{config.source_volume_path if config.volume_source else 'N/A (JDBC source)'}`
- Artifacts volume: `{config.artifacts_volume_path}`
- Package artifacts location: `{config.artifacts_volume_path}/integration_packages/`

### Required Metadata Columns
- `_ingestion_timestamp` (TIMESTAMP): `current_timestamp()`
- `_source_file` (STRING): `input_file_name()` for Volume files, or `_source_system` (STRING): literal source name for Oracle
- `_load_date` (DATE): `current_date()`

### Requirements from User
{config.requirements_text or 'No additional requirements specified.'}

### Implementation Instructions

1. **Setup**: Create catalog/schema if not exists. Use `USE CATALOG` and `CREATE SCHEMA IF NOT EXISTS`.

2. **Read**: Read source data from the UC Volume path. Include a COPY INTO option and a spark.read option.

3. **Transform**: Add all metadata columns. Do not alter source columns.

4. **Write**: Write as Delta table using `overwrite` mode: `df.write.format("delta").mode("overwrite").saveAsTable(full_table_name)`

5. **Validate**: Query the target table to confirm row count and schema.

6. **Data Quality Checks** (separate notebook):
   - Table existence check
   - Row count > 0
   - Required metadata columns present
   - Null count per column
   - Duplicate check on primary key

7. **Demo Validation** (separate notebook):
   - Read sample data
   - Run ingestion in demo mode
   - Display results
   - Run quality checks
   - Print pass/fail summary

### Constraints
- PySpark only (no pandas for main operations)
- Delta format for all tables
- Unity Catalog three-level namespace
- Never hardcode credentials; use `dbutils.secrets.get()`
- Include clear TODO comments for production configuration
- Include `DEMO_MODE = True` flag with toggle instructions
"""
