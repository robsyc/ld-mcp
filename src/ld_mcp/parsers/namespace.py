"""RDF namespace parsing utilities using rdflib."""

from rdflib import RDF, Graph, URIRef

# Standard namespace prefixes
NAMESPACES = {
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "owl": "http://www.w3.org/2002/07/owl#",
    "sh": "http://www.w3.org/ns/shacl#",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "prov": "http://www.w3.org/ns/prov#",
    "time": "http://www.w3.org/2006/time#",
}


def fetch_namespace_graph(uri: str) -> Graph:
    """Fetch and parse namespace RDF with standard prefix bindings."""
    g = Graph()
    for prefix, ns in NAMESPACES.items():
        g.bind(prefix, ns)
    g.parse(uri)  # rdflib auto-detects format
    return g


def _normalize_uri_variants(ns_uri: str) -> list[str]:
    """Return list of URI variants (http/https) for matching."""
    variants = [ns_uri]
    if ns_uri.startswith("https://"):
        variants.append(ns_uri.replace("https://", "http://"))
    elif ns_uri.startswith("http://"):
        variants.append(ns_uri.replace("http://", "https://"))
    return variants


def extract_resources(graph: Graph, ns_uri: str) -> list[dict]:
    """Extract resources defined in namespace, sorted by name."""
    uri_variants = _normalize_uri_variants(ns_uri)

    resources = []
    for s in set(graph.subjects()):
        s_str = str(s)
        for uri in uri_variants:
            if s_str.startswith(uri):
                local = s_str[len(uri) :]
                if not local:  # Skip the namespace itself (e.g., owl:Ontology)
                    break
                types = [graph.qname(t) for t in graph.objects(s, RDF.type)]
                resources.append({"name": local, "a": types[0] if types else None})
                break
    return sorted(resources, key=lambda r: r["name"])


def get_resource_turtle(
    graph: Graph, ns_uri: str, local_name: str, subject_only: bool = True
) -> str:
    """Extract triples for a resource as Turtle.

    Args:
        graph: RDF graph to extract from
        ns_uri: Namespace URI
        local_name: Local name of the resource
        subject_only: If True, only return triples where resource is subject.
                      If False, include triples where resource appears as predicate or object.
    """
    uri_variants = _normalize_uri_variants(ns_uri)
    uris = set(URIRef(uri_base + local_name) for uri_base in uri_variants)

    subgraph = Graph()
    for prefix, ns in NAMESPACES.items():
        subgraph.bind(prefix, ns)

    for uri in uris:
        # Resource as subject (always included)
        for p, o in graph.predicate_objects(subject=uri):
            subgraph.add((uri, p, o))

        if not subject_only:
            # Resource as predicate
            for s, o in graph.subject_objects(predicate=uri):
                subgraph.add((s, uri, o))
            # Resource as object
            for s, p in graph.subject_predicates(object=uri):
                subgraph.add((s, p, uri))

    if len(subgraph) == 0:
        return ""

    turtle = subgraph.serialize(format="turtle")
    lines = [line for line in turtle.splitlines() if not line.startswith("@prefix")]
    return "\n".join(lines).strip()
