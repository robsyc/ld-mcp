"""
Configuration for the Linked Data MCP server.
"""

import json
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    MCP server configuration loaded from environment variables.

    Environment variables:
        SPEC_VERSIONS: Comma-separated list of versions to include (e.g., "1.1,1.2")
                       If not set, all versions are included.
        CACHE_TTL: Cache TTL in seconds. Default: 86400 (24 hours)
    """

    spec_versions: Optional[str] = Field(
        default=None,
        alias="SPEC_VERSIONS",
        description="Comma-separated versions to include (e.g., '1.2' or '1.1,1.2')"
    )

    cache_ttl: int = Field(
        default=86400,  # 24 hours
        alias="CACHE_TTL",
        description="Cache TTL in seconds (for in-memory cache)"
    )

    @property
    def allowed_versions(self) -> Optional[set[str]]:
        """Parse spec_versions into a set, or None if all versions allowed."""
        if self.spec_versions is None:
            return None
        return {v.strip() for v in self.spec_versions.split(",") if v.strip()}

    def version_allowed(self, version: Optional[str]) -> bool:
        """Check if a specification version should be included."""
        if self.allowed_versions is None:
            return True
        if version is None:
            return True
        return version in self.allowed_versions


settings = Settings()


def get_index_path() -> Path:
    """Get path to the index.json file."""
    return Path(__file__).parent / "index.json"


def load_index() -> dict:
    """Load the specification index from index.json."""
    with open(get_index_path()) as f:
        return json.load(f)


def get_filtered_index() -> dict:
    """
    Load index.json and filter specifications based on SPEC_VERSIONS.

    Returns the index with specs filtered according to the version setting.
    Specs without a version field are always included.
    """
    index = load_index()

    result = {}
    for family_key, family_data in index.items():
        if not isinstance(family_data, dict):
            continue

        filtered_family = {
            "comment": family_data.get("comment", ""),
        }

        if "specifications" in family_data:
            filtered_specs = [
                spec for spec in family_data["specifications"]
                if settings.version_allowed(spec.get("version"))
            ]
            filtered_family["specifications"] = filtered_specs

        if "namespaces" in family_data:
            filtered_family["namespaces"] = family_data["namespaces"]

        result[family_key] = filtered_family

    return result
