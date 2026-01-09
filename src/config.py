"""
Configuration for the Linked Data MCP server.
"""

import os
import json
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    MCP server configuration loaded from environment variables.
    
    Environment variables:
        SPEC_VERSIONS: Comma-separated list of versions to include (e.g., "1.1,1.2")
                       If not set, all versions are included.
        CACHE_DIR: Directory for caching fetched specifications.
                 Defaults to ~/.cache/ld-mcp
        CACHE_TTL: Cache TTL in seconds. Default: 86400 (24 hours)
    """
    
    spec_versions: Optional[str] = Field(
        default=None,
        alias="SPEC_VERSIONS",
        description="Comma-separated versions to include (e.g., '1.2' or '1.1,1.2')"
    )
    
    cache_dir: Path = Field(
        default=Path.home() / ".cache" / "ld-mcp",
        alias="CACHE_DIR",
        description="Directory for caching fetched specifications"
    )
    
    cache_ttl: int = Field(
        default=86400,  # 24 hours
        alias="CACHE_TTL",
        description="Cache TTL in seconds"
    )
    
    @property
    def allowed_versions(self) -> Optional[set[str]]:
        """Parse spec_versions into a set, or None if all versions allowed."""
        if self.spec_versions is None:
            return None
        return {v.strip() for v in self.spec_versions.split(",") if v.strip()}
    
    def version_allowed(self, version: Optional[str]) -> bool:
        """Check if a specification version should be included."""
        # If no version filter set, allow everything
        if self.allowed_versions is None:
            return True
        # If spec has no version, always include (e.g., OWL, SKOS, PROV)
        if version is None:
            return True
        # Check if version matches
        return version in self.allowed_versions


# Global settings instance
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
        
        # Filter specifications by version
        if "specifications" in family_data:
            filtered_specs = [
                spec for spec in family_data["specifications"]
                if settings.version_allowed(spec.get("version"))
            ]
            filtered_family["specifications"] = filtered_specs
        
        # Namespaces don't have versions, include as-is
        if "namespaces" in family_data:
            filtered_family["namespaces"] = family_data["namespaces"]
        
        result[family_key] = filtered_family
    
    return result


def ensure_cache_dir() -> Path:
    """Ensure cache directory exists and return its path."""
    settings.cache_dir.mkdir(parents=True, exist_ok=True)
    return settings.cache_dir


def get_toc_cache_path(spec_key: str) -> Path:
    """Get path to cached TOC for a specification."""
    cache_dir = ensure_cache_dir()
    return cache_dir / "toc" / f"{spec_key}.json"


def get_content_cache_path(spec_key: str, section_id: str) -> Path:
    """Get path to cached content for a specification section."""
    cache_dir = ensure_cache_dir()
    return cache_dir / "content" / spec_key / f"{section_id}.md"
