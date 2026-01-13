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
from mcp.shared.exceptions import McpError
from mcp.types import ErrorData

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
async def list_specifications(family: Optional[str] = None) -> str:
    """
    List available specification families or get details for a specific family.

    Args:
        family: Optional family key (RDF, SPARQL, OWL, SHACL, SKOS, PROV).
                If not provided, returns overview of all families.

    Returns:
        Markdown formatted list of specifications.
    """
    index = get_filtered_index()

    if family:
        family_upper = family.upper()
        if family_upper not in index:
            available = ", ".join(index.keys())
            raise McpError(
                ErrorData(code=-32602, message=f"Unknown family '{family}'. Available: {available}")
            )

        family_data = index[family_upper]
        lines = [f"# {family_upper}", "", family_data.get("comment", "")]

        specs = family_data.get("specifications", [])
        if specs:
            lines.append("")
            lines.append("## Specifications")
            for s in specs:
                lines.append(f"- `{s['key']}`: {s['comment']}")

        namespaces = family_data.get("namespaces", [])
        if namespaces:
            lines.append("")
            lines.append("## Namespaces")
            for n in namespaces:
                lines.append(f"- `{n['key']}`: {n['comment']}")

        lines.append("\nHint: Use `list_sections(spec_key, depth)` to see available sections for a specification and `list_resources(ns_key)` to see available resources for a namespace.")

        return "\n".join(lines)

    # Overview of all families
    lines = ["# Linked Data Specifications", ""]
    for key, data in index.items():
        spec_count = len(data.get("specifications", []))
        ns_count = len(data.get("namespaces", []))
        ns_part = f", {ns_count} namespace{'s' if ns_count != 1 else ''}" if ns_count else ""
        lines.append(
            f"- {key} ({spec_count} spec{'s' if spec_count != 1 else ''}{ns_part}): {data.get('comment', '')}"
        )

    lines.append("\nHint: Use `list_specifications(family)` to see available specifications and namespaces.")

    return "\n".join(lines)


@mcp.tool()
async def list_sections(spec_key: str, depth: int = 2) -> str:
    """
    Get the table of contents for a specification document.

    Args:
        spec_key: Short key of the specification (e.g., 'rdf12-primer', 'sparql12-query')
        depth: How many levels deep to show (1=top level only, 2+=nested). Default: 2

    Returns:
        Markdown formatted table of contents with section links.
    """
    spec_info = _get_spec_by_key(spec_key)
    if not spec_info:
        available = ", ".join(_list_all_spec_keys())
        raise McpError(
            ErrorData(code=-32602, message=f"Unknown spec '{spec_key}'. Available: {available}")
        )

    family_key, spec = spec_info

    try:
        toc = await _get_spec_toc(spec_key, spec["uri"])
    except Exception as e:
        raise McpError(ErrorData(code=-32603, message=f"Failed to fetch spec: {str(e)}"))

    if not toc:
        raise McpError(ErrorData(code=-32603, message=f"No table of contents found in {spec_key}"))

    # Format as indented markdown links
    flat = flatten_toc(toc, max_depth=depth)
    lines = [f"# {spec_key}", ""]
    for item in flat:
        indent = "\t" * (item["depth"] - 1)
        lines.append(f"{indent}[{item['title']}]({item['id']})")

    lines.append("\nHint: Use `get_section(spec_key, section_id)` to get the markdown content of a specific section.")

    return "\n".join(lines)


@mcp.tool()
async def get_section(spec_key: str, section_id: str) -> str:
    """
    Get the markdown content of a specific section from a specification.

    Args:
        spec_key: Short key of the specification (e.g., 'rdf12-primer')
        section_id: Section ID from list_sections() output (the link target)

    Returns:
        Markdown content of the section.
    """
    spec_info = _get_spec_by_key(spec_key)
    if not spec_info:
        available = ", ".join(_list_all_spec_keys())
        raise McpError(
            ErrorData(code=-32602, message=f"Unknown spec '{spec_key}'. Available: {available}")
        )

    family_key, spec = spec_info

    try:
        soup = await _get_spec_soup(spec_key, spec["uri"])
    except Exception as e:
        raise McpError(ErrorData(code=-32603, message=f"Failed to fetch spec: {str(e)}"))

    content = extract_section_content(soup, section_id)

    if not content:
        toc = await _get_spec_toc(spec_key, spec["uri"])
        flat = flatten_toc(toc, max_depth=3)
        available = ", ".join(item["id"] for item in flat[:10])
        raise McpError(
            ErrorData(
                code=-32602, message=f"Section '{section_id}' not found. Available: {available}..."
            )
        )

    return content


@mcp.tool()
async def list_resources(ns_key: str) -> str:
    """
    List all resources (classes, properties) defined in a namespace.

    Args:
        ns_key: Short namespace key (e.g., 'rdf', 'rdfs', 'owl', 'sh', 'skos', 'prov')

    Returns:
        Markdown formatted list of resources grouped by type.
    """
    ns_info = _get_namespace_by_key(ns_key)
    if not ns_info:
        available = ", ".join(_list_all_namespace_keys())
        raise McpError(
            ErrorData(code=-32602, message=f"Unknown namespace '{ns_key}'. Available: {available}")
        )

    family_key, ns = ns_info

    try:
        graph = _get_namespace_graph(ns_key, ns["uri"])
    except Exception as e:
        raise McpError(ErrorData(code=-32603, message=f"Failed to fetch namespace: {str(e)}"))

    resources = extract_resources(graph, ns["uri"])

    if not resources:
        raise McpError(ErrorData(code=-32603, message=f"No resources found in {ns_key}"))

    # Group by type
    by_type: dict[str, list[str]] = {}
    for r in resources:
        rtype = r.get("a") or "Other"
        by_type.setdefault(rtype, []).append(r["name"])

    lines = [f"# {ns_key}", ""]
    for rtype, names in sorted(by_type.items()):
        lines.append(f"## {rtype}")
        lines.append(", ".join(sorted(names)))
        lines.append("")

    lines.append("\nHint: Use `get_resource(ns_key, resource)` to get the full definition of a resource.")

    return "\n".join(lines).rstrip()


@mcp.tool()
async def get_resource(ns_key: str, resource: str) -> str:
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
        available = ", ".join(_list_all_namespace_keys())
        raise McpError(
            ErrorData(code=-32602, message=f"Unknown namespace '{ns_key}'. Available: {available}")
        )

    family_key, ns = ns_info

    try:
        graph = _get_namespace_graph(ns_key, ns["uri"])
    except Exception as e:
        raise McpError(ErrorData(code=-32603, message=f"Failed to fetch namespace: {str(e)}"))

    turtle = get_resource_turtle(graph, ns["uri"], resource)

    if not turtle:
        resources = extract_resources(graph, ns["uri"])
        available = ", ".join(r["name"] for r in resources[:10])
        raise McpError(
            ErrorData(
                code=-32602,
                message=f"Resource '{resource}' not found in {ns_key}. Available: {available}...",
            )
        )

    return turtle


if __name__ == "__main__":
    mcp.run()
