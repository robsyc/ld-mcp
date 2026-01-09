"""
Data models for the Linked Data MCP server.
"""

from typing import Optional, Literal
from pydantic import BaseModel, Field


# --- Index Models ---

class Specification(BaseModel):
    """A single specification document."""
    key: str = Field(description="Short identifier for the spec (e.g., 'rdf12-primer')")
    label: str = Field(description="Human-readable title")
    comment: str = Field(description="Brief description of the specification")
    uri: str = Field(description="URL to the specification document")
    version: Optional[str] = Field(default=None, description="Version string (e.g., '1.1', '1.2')")


class Namespace(BaseModel):
    """A vocabulary namespace with defined resources."""
    key: str = Field(description="Short prefix (e.g., 'rdf', 'rdfs', 'owl')")
    label: str = Field(description="Human-readable name")
    comment: str = Field(description="Description of what the namespace defines")
    uri: str = Field(description="Namespace URI")
    version: Optional[str] = Field(default=None, description="Version string (e.g., '1.1', '1.2')")


class SpecFamily(BaseModel):
    """A family of related specifications (e.g., RDF, SPARQL, OWL)."""
    comment: str = Field(description="Description of the specification family")
    specifications: list[Specification] = Field(default_factory=list)
    namespaces: list[Namespace] = Field(default_factory=list)

# --- TOC / Content Cache Models ---

class TOCItem(BaseModel):
    """A single item in a specification's table of contents."""
    id: str = Field(description="Section identifier (used for get_section)")
    title: str = Field(description="Section title")
    depth: int = Field(description="Nesting depth (1 = top level)")
    anchor: Optional[str] = Field(default=None, description="HTML anchor/fragment")
    children: list["TOCItem"] = Field(default_factory=list)


class CachedSpec(BaseModel):
    """Cached specification with TOC and content sections."""
    key: str
    uri: str
    fetched_at: str = Field(description="ISO timestamp of when content was fetched")
    toc: list[TOCItem] = Field(default_factory=list)
    sections: dict[str, str] = Field(
        default_factory=dict, 
        description="Section ID -> markdown content mapping"
    )


# --- Namespace Resource Models ---

class NamespaceResource(BaseModel):
    """A resource (class, property, etc.) defined in a namespace."""
    uri: str = Field(description="Full URI of the resource")
    local_name: str = Field(description="Local name (e.g., 'type' from rdf:type)")
    types: list[str] = Field(default_factory=list, description="rdf:type values")
    label: Optional[str] = Field(default=None, description="rdfs:label if available")
    comment: Optional[str] = Field(default=None, description="rdfs:comment if available")
    # should we keep a subgraph of the resource's use as s, p, or o in triples?


# Enable forward references for recursive TOCItem
TOCItem.model_rebuild()
