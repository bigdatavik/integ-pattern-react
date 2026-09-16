"""Integration pattern definitions."""

PATTERNS = {
    "adls_to_bronze": {
        "id": "adls_to_bronze",
        "name": "ADLS to Databricks Bronze",
        "short_description": "Ingest files from Azure Data Lake Storage into a Delta bronze table.",
        "source_system": "Azure Data Lake Storage (ADLS Gen2)",
        "target_layer": "Bronze (Raw Ingestion)",
        "icon": "\u2601\ufe0f",
        "details": [
            "Read CSV or JSON files from ADLS",
            "Ingest into Delta bronze table",
            "Add metadata: ingestion timestamp, source file, load date",
            "Support file pattern filtering",
        ],
        "supported_formats": ["csv", "json"],
    },
    "oracle_to_bronze": {
        "id": "oracle_to_bronze",
        "name": "Oracle to Databricks Bronze",
        "short_description": "Read data from Oracle via JDBC and ingest into a Delta bronze table.",
        "source_system": "Oracle Database (JDBC)",
        "target_layer": "Bronze (Raw Ingestion)",
        "icon": "\U0001f5c4\ufe0f",
        "details": [
            "Read from Oracle table via JDBC",
            "Ingest into Delta bronze table",
            "Add metadata: ingestion timestamp, source system, load date",
            "Support incremental watermark column",
        ],
        "supported_formats": [],
    },
}


def get_pattern(pattern_id: str) -> dict:
    """Get a pattern definition by ID."""
    return PATTERNS.get(pattern_id, {})


def get_all_patterns() -> dict:
    """Get all pattern definitions."""
    return PATTERNS
