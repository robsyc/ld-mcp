#!/usr/bin/env python3
"""
Full validation of all specifications and namespaces in index.json.

Run with: python tests/validate_all.py
"""

import sys
from pathlib import Path

import httpx
from bs4 import BeautifulSoup
from rdflib import Graph

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config import load_index
from parsers import NAMESPACES, extract_section_content, flatten_toc, parse_w3c_toc


def validate_specs():
    """Validate all specifications can be fetched and parsed."""
    index = load_index()

    client = httpx.Client(
        timeout=30.0, follow_redirects=True, headers={"User-Agent": "ld-mcp-validate/1.0"}
    )

    results = {"passed": [], "failed": []}

    print("=" * 60)
    print("SPECIFICATION VALIDATION")
    print("=" * 60)

    for family_key, family_data in index.items():
        specs = family_data.get("specifications", [])
        if not specs:
            continue

        print(f"\n{family_key} ({len(specs)} specs)")
        print("-" * 40)

        for spec in specs:
            key = spec["key"]
            uri = spec["uri"]

            try:
                response = client.get(uri)
                if response.status_code != 200:
                    print(f"  ✗ {key}: HTTP {response.status_code}")
                    results["failed"].append((key, f"HTTP {response.status_code}"))
                    continue

                soup = BeautifulSoup(response.text, "html.parser")
                toc = parse_w3c_toc(soup)

                if not toc:
                    print(f"  ✗ {key}: No TOC found")
                    results["failed"].append((key, "No TOC found"))
                    continue

                # Test section extraction on first section
                flat = flatten_toc(toc, max_depth=2)
                if flat:
                    first_section = flat[0]["id"]
                    content = extract_section_content(soup, first_section)
                    if content and len(content) > 50:
                        print(f"  ✓ {key}: {len(toc)} sections, content OK")
                        results["passed"].append(key)
                    else:
                        print(f"  ⚠ {key}: {len(toc)} sections, but content extraction failed")
                        results["failed"].append((key, "Content extraction failed"))
                else:
                    print(f"  ⚠ {key}: TOC found but empty after flatten")
                    results["failed"].append((key, "Empty TOC"))

            except Exception as e:
                print(f"  ✗ {key}: {str(e)[:50]}")
                results["failed"].append((key, str(e)[:50]))

    client.close()
    return results


def validate_namespaces():
    """Validate all namespaces can be fetched and parsed."""
    index = load_index()

    results = {"passed": [], "failed": []}

    print("\n" + "=" * 60)
    print("NAMESPACE VALIDATION")
    print("=" * 60)

    for family_key, family_data in index.items():
        namespaces = family_data.get("namespaces", [])
        if not namespaces:
            continue

        print(f"\n{family_key} ({len(namespaces)} namespaces)")
        print("-" * 40)

        for ns in namespaces:
            key = ns["key"]
            uri = ns["uri"]

            try:
                g = Graph()
                for prefix, ns_uri in NAMESPACES.items():
                    g.bind(prefix, ns_uri)
                g.parse(uri)

                if len(g) == 0:
                    print(f"  ✗ {key}: No triples found")
                    results["failed"].append((key, "No triples"))
                else:
                    # Count resources in namespace
                    uri_variants = [
                        uri,
                        uri.replace("https://", "http://"),
                        uri.replace("http://", "https://"),
                    ]
                    resources = set()
                    for s in g.subjects():
                        s_str = str(s)
                        for u in uri_variants:
                            if s_str.startswith(u) and len(s_str) > len(u):
                                resources.add(s_str[len(u) :])
                                break

                    print(f"  ✓ {key}: {len(g)} triples, {len(resources)} resources")
                    results["passed"].append(key)

            except Exception as e:
                print(f"  ✗ {key}: {str(e)[:50]}")
                results["failed"].append((key, str(e)[:50]))

    return results


def main():
    spec_results = validate_specs()
    ns_results = validate_namespaces()

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    total_specs = len(spec_results["passed"]) + len(spec_results["failed"])
    total_ns = len(ns_results["passed"]) + len(ns_results["failed"])

    print(f"\nSpecifications: {len(spec_results['passed'])}/{total_specs} passed")
    print(f"Namespaces: {len(ns_results['passed'])}/{total_ns} passed")

    if spec_results["failed"]:
        print("\nFailed specifications:")
        for key, reason in spec_results["failed"]:
            print(f"  - {key}: {reason}")

    if ns_results["failed"]:
        print("\nFailed namespaces:")
        for key, reason in ns_results["failed"]:
            print(f"  - {key}: {reason}")

    # Exit with error if any failures
    if spec_results["failed"] or ns_results["failed"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
