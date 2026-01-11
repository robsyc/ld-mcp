#!/usr/bin/env python3
"""
ld-mcp: The Linked Data MCP Server

Provides access to linked data specification documentation
including RDF, RDFS, SHACL, OWL, SPARQL, Turtle, JSON-LD, and other semantic web standards.

Environment variables:
    SPEC_VERSIONS: Comma-separated versions to include (e.g., "1.2" or "1.1,1.2")
    CACHE_TTL: Cache TTL in seconds (default: 86400)
"""

from typing import Optional

from bs4 import BeautifulSoup
from mcp.server.fastmcp import FastMCP

from cache import cache
from config import get_filtered_index
from fetch import fetch_html
from parsers import (
    extract_resources,
    extract_section_content,
    fetch_namespace_graph,
    flatten_toc,
    get_resource_turtle,
    parse_w3c_toc,
)

mcp = FastMCP(
    "ld-mcp",
    instructions="""Linked Data MCP Server - Access W3C Semantic Web specifications.

Tools:
- list_specifications(family?) → Browse spec families (RDF, SPARQL, OWL, SHACL, SKOS, PROV)
- list_sections(spec_key, depth?) → Get TOC with section IDs in [brackets]
- get_section(spec_key, section_id) → Get markdown content for a section
- list_resources(ns_key) → List classes/properties in a namespace (rdf, rdfs, owl, sh, skos, prov)
- get_resource(ns_key, resource) → Get Turtle definition of a resource""",
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
    for family in index.values():
        for spec in family.get("specifications", []):
            keys.append(spec.get("key"))
    return sorted(keys)


def _list_all_namespace_keys() -> list[str]:
    """Get all available namespace keys."""
    index = get_filtered_index()
    keys = []
    for family in index.values():
        for ns in family.get("namespaces", []):
            keys.append(ns.get("key"))
    return sorted(keys)


async def _get_spec_soup(spec_key: str, uri: str) -> BeautifulSoup:
    """Get BeautifulSoup for a spec, using cache if available."""
    cache_key = f"soup:{spec_key}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    html = await fetch_html(uri)
    soup = BeautifulSoup(html, "html.parser")
    cache.set(cache_key, soup)
    return soup


async def _get_spec_toc(spec_key: str, uri: str) -> list:
    """Get TOC for a spec, using cache if available."""
    cache_key = f"toc:{spec_key}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    soup = await _get_spec_soup(spec_key, uri)
    toc = parse_w3c_toc(soup)
    cache.set(cache_key, toc)
    return toc


def _get_namespace_graph(ns_key: str, uri: str):
    """Get rdflib Graph for a namespace, using cache if available."""
    cache_key = f"graph:{ns_key}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    graph = fetch_namespace_graph(uri)
    cache.set(cache_key, graph)
    return graph


# --- Tools ---


@mcp.tool()
async def list_specifications(family: Optional[str] = None) -> dict:
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
            available = list(index.keys())
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
                    "version": s.get("version"),
                }
                for s in family_data.get("specifications", [])
            ],
            "namespaces": [
                {
                    "key": n["key"],
                    "label": n["label"],
                    "comment": n["comment"],
                    "version": n.get("version"),
                }
                for n in family_data.get("namespaces", [])
            ],
            "hint": "Use list_sections(spec_key) or list_resources(ns_key)",
        }

    # Overview of all families
    result = {"families": {}}
    for key, data in index.items():
        result["families"][key] = {
            "description": data.get("comment", ""),
            "specs": len(data.get("specifications", [])),
            "namespaces": len(data.get("namespaces", [])),
        }
    result["hint"] = "Use list_specifications(family) for details"
    return result


@mcp.tool()
async def list_sections(spec_key: str, depth: int = 2) -> dict:
    """
    Get the table of contents for a specification document.

    Args:
        spec_key: Short key of the specification (e.g., 'rdf12-primer', 'sparql12-query')
        depth: How many levels deep to show (1=top level only, 2+=nested). Default: 2

    Returns:
        Table of contents with section IDs in [brackets] for use with get_section().
    """
    spec_info = _get_spec_by_key(spec_key)
    if not spec_info:
        available = _list_all_spec_keys()
        return {"error": f"Unknown spec '{spec_key}'. Examples: {available}"}

    family_key, spec = spec_info

    try:
        toc = await _get_spec_toc(spec_key, spec["uri"])
    except Exception as e:
        return {"error": f"Failed to fetch spec: {str(e)}"}

    if not toc:
        return {"spec": spec_key, "error": "No table of contents found in this specification"}

    # Format as indented text with section IDs
    flat = flatten_toc(toc, max_depth=depth)
    sections = []
    for item in flat:
        indent = "  " * (item["depth"] - 1)
        sections.append(f"{indent}{item['title']} [{item['id']}]")

    return {
        "spec": spec_key,
        "sections": sections,
        "hint": "Use get_section(spec_key, section_id) with ID from brackets",
    }


@mcp.tool()
async def get_section(spec_key: str, section_id: str) -> dict:
    """
    Get the markdown content of a specific section from a specification.

    Args:
        spec_key: Short key of the specification (e.g., 'rdf12-primer')
        section_id: Section ID from list_sections() output (value in brackets)

    Returns:
        Markdown content of the section.
    """
    spec_info = _get_spec_by_key(spec_key)
    if not spec_info:
        return {"error": f"Unknown spec '{spec_key}'"}

    family_key, spec = spec_info

    try:
        soup = await _get_spec_soup(spec_key, spec["uri"])
    except Exception as e:
        return {"error": f"Failed to fetch spec: {str(e)}"}

    content = extract_section_content(soup, section_id)

    if not content:
        # Try to help with available sections
        toc = await _get_spec_toc(spec_key, spec["uri"])
        flat = flatten_toc(toc, max_depth=3)
        available = [item["id"] for item in flat]
        return {"error": f"Section '{section_id}' not found", "available": available}

    return {"spec": spec_key, "section": section_id, "content": content}


@mcp.tool()
async def list_resources(ns_key: str) -> dict:
    """
    List all resources (classes, properties) defined in a namespace.

    Args:
        ns_key: Short namespace key (e.g., 'rdf', 'rdfs', 'owl', 'sh', 'skos', 'prov')

    Returns:
        List of resources with their types.
    """
    ns_info = _get_namespace_by_key(ns_key)
    if not ns_info:
        available = _list_all_namespace_keys()
        return {"error": f"Unknown namespace '{ns_key}'. Available: {available}"}

    family_key, ns = ns_info

    try:
        graph = _get_namespace_graph(ns_key, ns["uri"])
    except Exception as e:
        return {"error": f"Failed to fetch namespace: {str(e)}"}

    resources = extract_resources(graph, ns["uri"])

    if not resources:
        return {"namespace": ns_key, "error": "No resources found in namespace"}

    return {
        "namespace": ns_key,
        "resources": resources,
        "hint": "Use get_resource(ns_key, name) for full Turtle definition",
    }


@mcp.tool()
async def get_resource(ns_key: str, resource: str) -> dict:
    """
    Get the full definition of a resource from a namespace as Turtle.

    Args:
        ns_key: Short namespace key (e.g., 'rdf', 'owl')
        resource: Local name (e.g., 'type', 'Class', 'Property')

    Returns:
        Turtle serialization of all triples defining this resource.
    """
    ns_info = _get_namespace_by_key(ns_key)
    if not ns_info:
        return {"error": f"Unknown namespace '{ns_key}'"}

    family_key, ns = ns_info

    try:
        graph = _get_namespace_graph(ns_key, ns["uri"])
    except Exception as e:
        return {"error": f"Failed to fetch namespace: {str(e)}"}

    turtle = get_resource_turtle(graph, ns["uri"], resource)

    if not turtle:
        # Help with available resources
        resources = extract_resources(graph, ns["uri"])
        available = [r["name"] for r in resources]
        return {"error": f"Resource '{resource}' not found in {ns_key}", "available": available}

    return {"resource": f"{ns_key}:{resource}", "turtle": turtle}


if __name__ == "__main__":
    mcp.run()
