"""Parsers for W3C specifications and RDF namespaces."""

from parsers.content import extract_section_content
from parsers.namespace import (
    NAMESPACES,
    extract_resources,
    fetch_namespace_graph,
    get_resource_turtle,
)
from parsers.toc import (
    flatten_toc,
    parse_headings_as_toc,
    parse_sections_as_toc,
    parse_w3c_toc,
    toc_to_markdown,
)

__all__ = [
    # TOC parsing
    "parse_w3c_toc",
    "parse_sections_as_toc",
    "parse_headings_as_toc",
    "flatten_toc",
    "toc_to_markdown",
    # Content extraction
    "extract_section_content",
    # Namespace parsing
    "NAMESPACES",
    "fetch_namespace_graph",
    "extract_resources",
    "get_resource_turtle",
]
