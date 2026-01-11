"""
Validation tests for W3C specification accessibility and parsing.

Run with: pytest tests/test_specs.py -v
"""

import sys
from pathlib import Path

import httpx
import pytest
from bs4 import BeautifulSoup
from rdflib import Graph

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config import load_index
from parsers import NAMESPACES, extract_section_content, parse_w3c_toc

# --- Fixtures ---


@pytest.fixture(scope="module")
def http_client():
    """Shared HTTP client for all tests."""
    client = httpx.Client(
        timeout=30.0, follow_redirects=True, headers={"User-Agent": "ld-mcp-test/1.0"}
    )
    yield client
    client.close()


@pytest.fixture(scope="module")
def spec_index():
    """Load the specification index."""
    return load_index()


# --- Helpers ---


def get_all_specs(index: dict) -> list[tuple[str, str]]:
    """Extract all (spec_key, uri) pairs from index."""
    specs = []
    for family_data in index.values():
        for spec in family_data.get("specifications", []):
            specs.append((spec["key"], spec["uri"]))
    return specs


def get_all_namespaces(index: dict) -> list[tuple[str, str]]:
    """Extract all (ns_key, uri) pairs from index."""
    namespaces = []
    for family_data in index.values():
        for ns in family_data.get("namespaces", []):
            namespaces.append((ns["key"], ns["uri"]))
    return namespaces


# --- Specification Tests ---


class TestSpecifications:
    """Test that all specifications can be fetched and parsed."""

    def test_all_specs_listed(self, spec_index):
        """Verify index contains specifications."""
        specs = get_all_specs(spec_index)
        assert len(specs) > 0, "No specifications found in index"
        print(f"\nFound {len(specs)} specifications")

    @pytest.mark.parametrize(
        "spec_key,spec_uri",
        [
            # Test a subset of key specs for faster CI
            ("rdf12-primer", "https://www.w3.org/TR/rdf12-primer/"),
            ("sparql12-query", "https://www.w3.org/TR/sparql12-query/"),
            ("owl2-primer", "https://www.w3.org/TR/owl2-primer/"),
            ("shacl11", "https://www.w3.org/TR/shacl/"),
            ("skos-reference", "https://www.w3.org/TR/skos-reference/"),
            ("prov-o", "https://www.w3.org/TR/prov-o/"),
        ],
    )
    def test_spec_toc_parsing(self, http_client, spec_key, spec_uri):
        """Verify spec can be fetched and TOC parsed."""
        response = http_client.get(spec_uri)
        assert response.status_code == 200, f"Failed to fetch {spec_key}: {response.status_code}"

        soup = BeautifulSoup(response.text, "html.parser")
        toc = parse_w3c_toc(soup)

        assert len(toc) > 0, f"No TOC found for {spec_key}"
        print(f"\n{spec_key}: {len(toc)} top-level sections")

    @pytest.mark.parametrize(
        "spec_key,spec_uri,section_id",
        [
            ("rdf12-primer", "https://www.w3.org/TR/rdf12-primer/", "section-Introduction"),
            ("sparql12-query", "https://www.w3.org/TR/sparql12-query/", "introduction"),
            ("owl2-primer", "https://www.w3.org/TR/owl2-primer/", "What_is_OWL_2.3F"),
        ],
    )
    def test_section_extraction(self, http_client, spec_key, spec_uri, section_id):
        """Verify section content can be extracted."""
        response = http_client.get(spec_uri)
        soup = BeautifulSoup(response.text, "html.parser")

        content = extract_section_content(soup, section_id)
        assert content is not None, f"Section {section_id} not found in {spec_key}"
        assert len(content) > 100, f"Section content too short for {spec_key}/{section_id}"
        print(f"\n{spec_key}/{section_id}: {len(content)} chars")


# --- Namespace Tests ---


class TestNamespaces:
    """Test that all namespaces can be fetched and parsed."""

    def test_all_namespaces_listed(self, spec_index):
        """Verify index contains namespaces."""
        namespaces = get_all_namespaces(spec_index)
        assert len(namespaces) > 0, "No namespaces found in index"
        print(f"\nFound {len(namespaces)} namespaces")

    @pytest.mark.parametrize(
        "ns_key,ns_uri",
        [
            ("rdf", "http://www.w3.org/1999/02/22-rdf-syntax-ns#"),
            ("rdfs", "http://www.w3.org/2000/01/rdf-schema#"),
            ("owl", "http://www.w3.org/2002/07/owl#"),
            ("skos", "http://www.w3.org/2004/02/skos/core#"),
            ("prov", "http://www.w3.org/ns/prov#"),
        ],
    )
    def test_namespace_parsing(self, ns_key, ns_uri):
        """Verify namespace RDF can be fetched and parsed."""
        g = Graph()
        for prefix, ns in NAMESPACES.items():
            g.bind(prefix, ns)

        try:
            g.parse(ns_uri)
        except Exception as e:
            pytest.fail(f"Failed to parse {ns_key}: {e}")

        assert len(g) > 0, f"No triples found for {ns_key}"
        print(f"\n{ns_key}: {len(g)} triples")


# --- Full Validation (optional, slow) ---


@pytest.mark.slow
class TestFullValidation:
    """Full validation of all specs (run with pytest -m slow)."""

    def test_all_specs_accessible(self, http_client, spec_index):
        """Test all specs can be fetched."""
        specs = get_all_specs(spec_index)
        results = {"passed": [], "failed": []}

        for spec_key, spec_uri in specs:
            try:
                response = http_client.get(spec_uri)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, "html.parser")
                    toc = parse_w3c_toc(soup)
                    if len(toc) > 0:
                        results["passed"].append(spec_key)
                    else:
                        results["failed"].append((spec_key, "No TOC found"))
                else:
                    results["failed"].append((spec_key, f"HTTP {response.status_code}"))
            except Exception as e:
                results["failed"].append((spec_key, str(e)))

        print(f"\n\nPassed: {len(results['passed'])}/{len(specs)}")
        if results["failed"]:
            print("Failed:")
            for key, reason in results["failed"]:
                print(f"  - {key}: {reason}")

        # Allow some failures (specs may be temporarily unavailable)
        assert len(results["passed"]) >= len(specs) * 0.8, "Too many specs failed"
