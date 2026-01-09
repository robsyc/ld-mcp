#!/usr/bin/env python3
"""
ld-mcp: The Linked Data MCP Server

Provides access to linked data specification documentation 
including RDF, RDFS, SHACL, OWL, SPARQL, Turtle, JSON-LD, and other semantic web standards.

Environment variables:
    SPEC_VERSIONS: Comma-separated versions to include (e.g., "1.2" or "1.1,1.2")
    CACHE_DIR: Directory for caching (default: ~/.cache/ld-mcp)
    CACHE_TTL: Cache TTL in seconds (default: 86400)
"""

from typing import Optional, Union

from mcp.server.fastmcp import FastMCP

from config import settings, get_filtered_index, load_index
from models import Specification, SpecFamily


mcp = FastMCP(
    "ld-mcp",
    instructions="""Linked Data MCP Server - Progressively access W3C Semantic Web specifications.

Available tools:
- list_specifications(): Discover spec families (RDF, SPARQL, OWL, SHACL, SKOS, PROV)
- list_sections(spec_key): Get table of contents for a spec document
- get_section(spec_key, section_id): Get markdown content for a section
- list_resources(ns_key): List classes/properties in a namespace
- get_resource(ns_key, resource): Get full definition of a resource"""
)


# --- Helper Functions ---

def _get_spec_by_key(spec_key: str) -> Optional[tuple[str, dict]]:
    """Find a specification by its short key across all families."""
    index = get_filtered_index()
    for family_key, family in index.items():
        for spec in family.get("specifications", []):
            if spec.get("key") == spec_key:
                return family_key, spec
    return None


def _get_namespace_by_key(ns_key: str) -> Optional[tuple[str, dict]]:
    """Find a namespace by its short key across all families."""
    index = get_filtered_index()
    for family_key, family in index.items():
        for ns in family.get("namespaces", []):
            if ns.get("key") == ns_key:
                return family_key, ns
    return None


def _list_all_spec_keys() -> list[str]:
    """Get all available specification keys."""
    index = get_filtered_index()
    keys = []
    for family_key, family in index.items():
        for spec in family.get("specifications", []):
            keys.append(spec.get("key"))
    return sorted(keys)


def _list_all_namespace_keys() -> list[str]:
    """Get all available namespace keys."""
    index = get_filtered_index()
    keys = []
    for family_key, family in index.items():
        for ns in family.get("namespaces", []):
            keys.append(ns.get("key"))
    return sorted(keys)


# --- Tools ---

@mcp.tool()
async def list_specifications(
    family: Optional[str] = None
) -> dict:
    """
    List available specification families or get details for a specific family.
    
    Args:
        family: Optional family key (RDF, SPARQL, OWL, SHACL, SKOS, PROV).
                If not provided, returns overview of all families.
    
    Returns:
        Overview of specs with their short keys for use with other tools.
    """
    index = get_filtered_index()
    
    if family:
        family_upper = family.upper()
        if family_upper not in index:
            available = [k for k in index.keys()]
            return {"error": f"Unknown family '{family}'. Available: {available}"}
        
        family_data = index[family_upper]
        return {
            "family": family_upper,
            "description": family_data.get("comment", ""),
            "specifications": [
                {
                    "key": s["key"], 
                    "label": s["label"], 
                    "comment": s["comment"],
                    "version": s.get("version")
                }
                for s in family_data.get("specifications", [])
            ],
            "namespaces": [
                {
                    "key": n["key"],
                    "label": n["label"],
                    "comment": n["comment"],
                    "version": n.get("version")
                }
                for n in family_data.get("namespaces", [])
            ],
            "usage": "Use list_sections(<spec_key>) for TOC or list_resources(<ns_key>) for resources"
        }
    
    # Return overview of all families
    result = {
        "families": {},
        "usage": "Use list_specifications(<family_key>) for details"
    }
    
    for key, data in index.items():
        spec_count = len(data.get("specifications", []))
        ns_count = len(data.get("namespaces", []))
        result["families"][key] = {
            "description": data.get("comment", ""),
            "spec_count": spec_count,
            "namespace_count": ns_count
        }
    
    return result


@mcp.tool()
async def list_sections(
    spec_key: str,
    depth: int = 2
) -> dict:
    """
    Get the table of contents for a specification document.
    
    Args:
        spec_key: Short key of the specification (e.g., 'rdf12-primer', 'sparql12-query')
        depth: How many levels deep to show (1=top level only, 2+=nested). Default: 2
    
    Returns:
        Hierarchical table of contents with section IDs for use with get_section().
    """
    # TODO: Implement TOC fetching and parsing
    spec_info = _get_spec_by_key(spec_key)
    if not spec_info:
        available = _list_all_spec_keys()
        return {"error": f"Unknown spec key '{spec_key}'. Available keys: {available[:10]}..."}
    
    family_key, spec = spec_info
    return {
        "spec_key": spec_key,
        "label": spec["label"],
        "uri": spec["uri"],
        "sections": [],  # TODO: Parse from cached/fetched HTML
        "note": "TOC parsing not yet implemented"
    }


@mcp.tool()
async def get_section(
    spec_key: str,
    section_id: str
) -> dict:
    """
    Get the markdown content of a specific section from a specification.
    
    Args:
        spec_key: Short key of the specification (e.g., 'rdf12-primer')
        section_id: Section ID from list_sections() output
    
    Returns:
        Markdown content of the section.
    """
    # TODO: Implement section content fetching
    spec_info = _get_spec_by_key(spec_key)
    if not spec_info:
        return {"error": f"Unknown spec key '{spec_key}'"}
    
    family_key, spec = spec_info
    return {
        "spec_key": spec_key,
        "section_id": section_id,
        "content": "",  # TODO: Extract from cached/fetched HTML
        "note": "Section extraction not yet implemented"
    }


@mcp.tool()
async def list_resources(
    ns_key: str
) -> dict:
    """
    List all resources (classes, properties) defined in a namespace.
    
    Args:
        ns_key: Short namespace key (e.g., 'rdf', 'rdfs', 'owl', 'sh', 'skos', 'prov')
    
    Returns:
        List of resources with their types and brief descriptions.
    """
    # TODO: Implement namespace resource listing
    ns_info = _get_namespace_by_key(ns_key)
    if not ns_info:
        available = _list_all_namespace_keys()
        return {"error": f"Unknown namespace key '{ns_key}'. Available: {available}"}
    
    family_key, ns = ns_info
    return {
        "namespace": ns_key,
        "uri": ns["uri"],
        "resources": [],  # TODO: Fetch and parse namespace
        "note": "Namespace resource listing not yet implemented"
    }


@mcp.tool()
async def get_resource(
    ns_key: str,
    resource: str
) -> dict:
    """
    Get the full definition of a resource from a namespace.
    
    Args:
        ns_key: Short namespace key (e.g., 'rdf', 'owl')
        resource: Local name (e.g., 'type', 'Class') or full URI
    
    Returns:
        Complete definition including label, comment, domain, range, etc.
    """
    # TODO: Implement resource detail fetching
    ns_info = _get_namespace_by_key(ns_key)
    if not ns_info:
        return {"error": f"Unknown namespace key '{ns_key}'"}
    
    family_key, ns = ns_info
    return {
        "namespace": ns_key,
        "resource": resource,
        "definition": {},  # TODO: Query namespace for resource details
        "note": "Resource definition fetching not yet implemented"
    }


if __name__ == "__main__":
    mcp.run()
