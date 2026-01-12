# Linked Data MCP

MCP server for AI agents to progressively access W3C Semantic Web specifications.

## Supported Standards

| Family | Specifications | Namespace |
|--------|---------------|-----------|
| **RDF** | RDF 1.1/1.2 Primer, Concepts, Semantics, Turtle, TriG, N-Triples, N-Quads, JSON-LD | `rdf:`, `rdfs:` |
| **SPARQL** | SPARQL 1.1/1.2 Query, Update, Overview | - |
| **OWL** | OWL 2 Primer, Overview, Syntax, Profiles, RDF Mapping | `owl:` |
| **SHACL** | SHACL 1.1/1.2 Core, Advanced Features, SPARQL, Node Expressions, Rules, UI | `sh:` |
| **SKOS** | SKOS Primer, Reference | `skos:` |
| **PROV** | PROV Primer, Data Model, Ontology | `prov:` |

## Installation

```bash
git clone https://github.com/robsyc/ld-mcp
cd ld-mcp
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -e ".[dev]"
```

## Usage

### Run Server Locally

```bash
# stdio transport is the traditional way to connect MCP servers to clients
python src/main.py

# the HTTP transport enables remote connections
fastmcp run src/main.py:mcp --transport http --port 8000
```

### With Claude Desktop

Add to your Claude Desktop MCP configuration:

```json
{
  "mcpServers": {
    "ld-mcp": {
      "command": "python",
      "args": ["/path/to/ld-mcp/src/main.py"]
    }
  }
}
```

### Available Tools

| Tool | Description |
|------|-------------|
| `list_specifications(family?)` | Browse spec families (RDF, SPARQL, OWL, SHACL, SKOS, PROV) |
| `list_sections(spec_key, depth?)` | Get TOC with section IDs in `[brackets]` |
| `get_section(spec_key, section_id)` | Get markdown content for a section |
| `list_resources(ns_key)` | List classes/properties in a namespace |
| `get_resource(ns_key, resource)` | Get Turtle definition of a resource |

## Development

```bash
# Run tests (fast, core functionality)
pytest tests/test_specs.py -v -m "not slow"

# Run full validation (all 42 specs + 6 namespaces)
python tests/validate_all.py

# Lint
ruff check src/ tests/
```

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `SPEC_VERSIONS` | Filter specs by version (e.g., `"1.2"` or `"1.1,1.2"`) | All versions |
| `CACHE_TTL` | Cache TTL in seconds | `86400` (24h) |

## Architecture

```
src/
├── main.py       # MCP server and tools
├── config.py     # Settings and index
├── models.py     # Data models
├── cache.py      # In-memory TTL cache
├── fetch.py      # HTTP client
├── parsers/      # HTML/RDF parsing
│   ├── toc.py    # TOC extraction (W3C + ReSpec)
│   ├── content.py
│   └── namespace.py
└── index.json    # Spec metadata
```
