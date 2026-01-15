"""
Validate all specifications and namespaces defined in index.yaml.

Run with: pytest tests/test_index.py -v
"""

import sys
from pathlib import Path

import httpx
import pytest
from bs4 import BeautifulSoup
from rdflib import Graph

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config import load_index
from parsers import NAMESPACES, extract_section_content, flatten_toc, parse_w3c_toc

# --- Dynamic test generation from index.yaml ---


def _get_all_specs():
    """Generate (spec_key, uri) pairs from index.yaml."""
    index = load_index()
    for family_data in index.values():
        for spec in family_data.get("specifications", []):
            yield pytest.param(spec["key"], spec["uri"], id=spec["key"])


def _get_all_namespaces():
    """Generate (ns_key, uri) pairs from index.yaml."""
    index = load_index()
    for family_data in index.values():
        for ns in family_data.get("namespaces", []):
            yield pytest.param(ns["key"], ns["uri"], id=ns["key"])


# --- Fixtures ---


@pytest.fixture(scope="module")
def http_client():
    """Shared HTTP client for all tests."""
    client = httpx.Client(
        timeout=30.0, follow_redirects=True, headers={"User-Agent": "ld-mcp-test/1.0"}
    )
    yield client
    client.close()


# --- Tests ---


@pytest.mark.parametrize("spec_key,spec_uri", list(_get_all_specs()))
def test_spec(http_client, spec_key, spec_uri):
    """Validate spec: fetch, parse TOC, extract first section."""
    response = http_client.get(spec_uri)
    assert response.status_code == 200, f"HTTP {response.status_code}"

    soup = BeautifulSoup(response.text, "html.parser")
    toc = parse_w3c_toc(soup)
    assert toc, "No TOC found"

    flat = flatten_toc(toc, max_depth=2)
    assert flat, "TOC empty after flatten"

    content = extract_section_content(soup, flat[0]["id"])
    assert content and len(content) > 50, "Content extraction failed"


@pytest.mark.parametrize("ns_key,ns_uri", list(_get_all_namespaces()))
def test_namespace(ns_key, ns_uri):
    """Validate namespace: fetch and parse RDF."""
    g = Graph()
    for prefix, ns in NAMESPACES.items():
        g.bind(prefix, ns)
    g.parse(ns_uri)
    assert len(g) > 0, "No triples found"
