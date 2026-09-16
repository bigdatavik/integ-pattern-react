"""Configuration models for the Integration Pattern Accelerator."""

from dataclasses import dataclass, field
from typing import Optional, List
import json
from datetime import datetime


@dataclass
class VolumeSourceConfig:
    """Source configuration for file-based patterns (files in a UC Volume)."""
    source_volume: str = ""         # Volume name containing source files
    source_path: str = ""           # Subfolder within the volume (optional)
    file_format: str = "csv"        # csv or json
    file_pattern: str = "*"


@dataclass
class OracleConfig:
    """Oracle-specific configuration."""
    jdbc_url: str = "jdbc:oracle:thin:@//<host>:<port>/<service_name>"
    source_table: str = ""
    watermark_column: str = ""


@dataclass
class IntegrationConfig:
    """Main configuration for an integration package.

    Two-volume model:
      - source volume: contains the raw files to ingest
      - artifacts volume: where the generated package (prompt, notebooks, etc.) is written
    Both live under the same catalog.schema for the demo; can be split later.
    """
    pattern_id: str = ""
    pattern_name: str = ""
    catalog_name: str = ""
    schema_name: str = ""
    # Target
    target_schema: str = ""
    target_table: str = ""
    target_description: str = ""
    artifacts_volume: str = ""      # Volume for generated package output
    # Optional
    business_domain: str = ""
    requirements_text: str = ""
    # Pattern-specific
    volume_source: Optional[VolumeSourceConfig] = None
    oracle_config: Optional[OracleConfig] = None

    def validate(self) -> List[str]:
        """Validate required fields. Returns list of error messages."""
        errors = []
        if not self.pattern_id:
            errors.append("Integration pattern must be selected.")
        if not self.catalog_name:
            errors.append("Catalog name is required.")
        if not self.schema_name:
            errors.append("Schema name is required.")
        if not self.target_schema:
            errors.append("Target schema is required.")
        if not self.target_table:
            errors.append("Target bronze table name is required.")
        if not self.artifacts_volume:
            errors.append("Artifacts volume name is required.")
        # Pattern-specific
        if self.pattern_id == "adls_to_bronze":
            if not self.volume_source or not self.volume_source.source_volume:
                errors.append("Source volume name is required.")
        if self.pattern_id == "oracle_to_bronze":
            if not self.oracle_config or not self.oracle_config.source_table:
                errors.append("Oracle source table is required.")
        return errors

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        d = {
            "pattern_id": self.pattern_id,
            "pattern_name": self.pattern_name,
            "catalog_name": self.catalog_name,
            "schema_name": self.schema_name,
            "target_schema": self.target_schema,
            "target_table": self.target_table,
            "target_description": self.target_description,
            "artifacts_volume": self.artifacts_volume,
            "business_domain": self.business_domain,
            "requirements_text": self.requirements_text,
            "source_volume_path": self.source_volume_path,
            "artifacts_volume_path": self.artifacts_volume_path,
            "target_full_name": self.target_full_name,
        }
        if self.volume_source:
            d["volume_source"] = {
                "source_volume": self.volume_source.source_volume,
                "source_path": self.volume_source.source_path,
                "file_format": self.volume_source.file_format,
                "file_pattern": self.volume_source.file_pattern,
            }
        if self.oracle_config:
            d["oracle_config"] = {
                "jdbc_url": self.oracle_config.jdbc_url,
                "source_table": self.oracle_config.source_table,
                "watermark_column": self.oracle_config.watermark_column,
            }
        return d

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    @property
    def source_volume_path(self) -> str:
        """Full path to the source volume (where files live)."""
        if self.volume_source and self.volume_source.source_volume:
            base = f"/Volumes/{self.catalog_name}/{self.schema_name}/{self.volume_source.source_volume}"
            if self.volume_source.source_path:
                return f"{base}/{self.volume_source.source_path.strip('/')}"
            return base
        return ""

    @property
    def artifacts_volume_path(self) -> str:
        """Full path to the artifacts volume (where generated package goes)."""
        return f"/Volumes/{self.catalog_name}/{self.schema_name}/{self.artifacts_volume}"

    @property
    def target_full_name(self) -> str:
        """Fully qualified target table name."""
        return f"{self.catalog_name}.{self.target_schema}.{self.target_table}"

    def generate_package_id(self) -> str:
        """Generate a unique package ID."""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{self.pattern_id}_{ts}"
