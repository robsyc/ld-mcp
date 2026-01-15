#!/usr/bin/env python3
"""
ld-mcp: Linked Data MCP Server

Access W3C Semantic Web specifications (RDF, SPARQL, OWL, SHACL, SKOS, PROV).

Env: SPEC_VERSIONS (e.g. "1.2"), CACHE_TTL (default: 86400)
"""

from typing import Annotated

from bs4 import BeautifulSoup
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

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
- get_resource(ns_key, resource, include_references?) → Get Turtle definition of a resource""",
)


# --- Helpers ---


def _get_spec_by_key(spec_key: str) -> tuple[str, dict] | None:
    """Lookup spec by key → (family_key, spec_dict) or None."""
    for fk, fam in get_filtered_index().items():
        for spec in fam.get("specifications", []):
            if spec.get("key") == spec_key:
                return fk, spec
    return None


def _get_namespace_by_key(ns_key: str) -> tuple[str, dict] | None:
    """Lookup namespace by key → (family_key, ns_dict) or None."""
    for fk, fam in get_filtered_index().items():
        for ns in fam.get("namespaces", []):
            if ns.get("key") == ns_key:
                return fk, ns
    return None


def _list_all_spec_keys() -> list[str]:
    """All available spec keys, sorted."""
    return sorted(
        spec.get("key")
        for fam in get_filtered_index().values()
        for spec in fam.get("specifications", [])
    )


def _list_all_namespace_keys() -> list[str]:
    """All available namespace keys, sorted."""
    return sorted(
        ns.get("key")
        for fam in get_filtered_index().values()
        for ns in fam.get("namespaces", [])
    )


async def _get_spec_soup(spec_key: str, uri: str) -> BeautifulSoup:
    """Fetch and cache parsed HTML for a spec."""
    if cached := cache.get(f"soup:{spec_key}"):
        return cached
    soup = BeautifulSoup(await fetch_html(uri), "html.parser")
    cache.set(f"soup:{spec_key}", soup)
    return soup


async def _get_spec_toc(spec_key: str, uri: str) -> list:
    """Fetch and cache TOC for a spec."""
    if cached := cache.get(f"toc:{spec_key}"):
        return cached
    toc = parse_w3c_toc(await _get_spec_soup(spec_key, uri))
    cache.set(f"toc:{spec_key}", toc)
    return toc


def _get_namespace_graph(ns_key: str, uri: str):
    """Fetch and cache RDF graph for a namespace."""
    if cached := cache.get(f"graph:{ns_key}"):
        return cached
    graph = fetch_namespace_graph(uri)
    cache.set(f"graph:{ns_key}", graph)
    return graph


# --- Tools ---


@mcp.tool()
async def list_specifications(
    family: Annotated[
        str | None, "Family key (RDF, SPARQL, OWL, SHACL, SKOS, PROV). Omit for overview."
    ] = None,
) -> str:
    """List available specification families or get details for a specific family."""
    index = get_filtered_index()

    if family:
        family_upper = family.upper()
        if family_upper not in index:
            available = ", ".join(index.keys())
            raise ToolError(f"Unknown family '{family}'. Available: {available}")

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
async def list_sections(
    spec_key: Annotated[str, "Spec key (e.g. 'rdf12-primer', 'sparql12-query')"],
    depth: Annotated[int, "TOC depth (1=top level, 2+=nested)"] = 2,
) -> str:
    """Get the table of contents for a specification document."""
    spec_info = _get_spec_by_key(spec_key)
    if not spec_info:
        available = ", ".join(_list_all_spec_keys())
        raise ToolError(f"Unknown spec '{spec_key}'. Available: {available}")

    family_key, spec = spec_info

    try:
        toc = await _get_spec_toc(spec_key, spec["uri"])
    except Exception as e:
        raise ToolError(f"Failed to fetch spec: {str(e)}")

    if not toc:
        raise ToolError(f"No table of contents found in {spec_key}")

    # Format as indented markdown links
    flat = flatten_toc(toc, max_depth=depth)
    lines = [f"# {spec_key}", ""]
    for item in flat:
        indent = "\t" * (item["depth"] - 1)
        lines.append(f"{indent}[{item['title']}]({item['id']})")

    lines.append("\nHint: Use `get_section(spec_key, section_id)` to get the markdown content of a specific section.")

    return "\n".join(lines)


@mcp.tool()
async def get_section(
    spec_key: Annotated[str, "Spec key (e.g. 'rdf12-primer')"],
    section_id: Annotated[str, "Section ID from list_sections() output"],
) -> str:
    """Get the markdown content of a specific section from a specification."""
    spec_info = _get_spec_by_key(spec_key)
    if not spec_info:
        available = ", ".join(_list_all_spec_keys())
        raise ToolError(f"Unknown spec '{spec_key}'. Available: {available}")

    family_key, spec = spec_info

    try:
        soup = await _get_spec_soup(spec_key, spec["uri"])
    except Exception as e:
        raise ToolError(f"Failed to fetch spec: {str(e)}")

    content = extract_section_content(soup, section_id)

    if not content:
        toc = await _get_spec_toc(spec_key, spec["uri"])
        flat = flatten_toc(toc, max_depth=3)
        available = ", ".join(item["id"] for item in flat[:10])
        raise ToolError(f"Section '{section_id}' not found. Available: {available}...")

    return content


@mcp.tool()
async def list_resources(
    ns_key: Annotated[str, "Namespace key (e.g. 'rdf', 'rdfs', 'owl', 'sh', 'skos', 'prov')"],
) -> str:
    """List all resources (classes, properties) defined in a namespace."""
    ns_info = _get_namespace_by_key(ns_key)
    if not ns_info:
        available = ", ".join(_list_all_namespace_keys())
        raise ToolError(f"Unknown namespace '{ns_key}'. Available: {available}")

    family_key, ns = ns_info

    try:
        graph = _get_namespace_graph(ns_key, ns["uri"])
    except Exception as e:
        raise ToolError(f"Failed to fetch namespace: {str(e)}")

    resources = extract_resources(graph, ns["uri"])

    if not resources:
        raise ToolError(f"No resources found in {ns_key}")

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
async def get_resource(
    ns_key: Annotated[str, "Namespace key (e.g. 'rdf', 'owl')"],
    resource: Annotated[str, "Local name (e.g. 'type', 'Class', 'Property')"],
    include_references: Annotated[
        bool, "Include triples where resource is used as predicate/object"
    ] = False,
) -> str:
    """Get the full definition of a resource from a namespace as Turtle."""
    ns_info = _get_namespace_by_key(ns_key)
    if not ns_info:
        available = ", ".join(_list_all_namespace_keys())
        raise ToolError(f"Unknown namespace '{ns_key}'. Available: {available}")

    family_key, ns = ns_info

    try:
        graph = _get_namespace_graph(ns_key, ns["uri"])
    except Exception as e:
        raise ToolError(f"Failed to fetch namespace: {str(e)}")

    turtle = get_resource_turtle(
        graph, ns["uri"], resource, subject_only=not include_references
    )

    if not turtle:
        resources = extract_resources(graph, ns["uri"])
        available = ", ".join(r["name"] for r in resources[:10])
        raise ToolError(f"Resource '{resource}' not found in {ns_key}. Available: {available}...")

    return turtle


if __name__ == "__main__":
    mcp.run()
