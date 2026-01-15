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
| **TIME** | OWL-Time | `time:` |

## Quick Start

### Option 1: FastMCP Cloud (Recommended)

Fork the repo, configure the `index.yaml` and deploy to your own [fastmcp.cloud](https://fastmcp.cloud) instance (free for personal use). Afterwards, you can use their web ui to connect your agentic coding tool (e.g. Cursor, Claude Desktop, etc.) to the MCP server.

### Option 2: Run Locally

```bash
git clone https://github.com/robsyc/ld-mcp && cd ld-mcp
python -m venv venv && source venv/bin/activate
pip install -e .

# Run with stdio (for MCP clients)
python src/main.py
```

**Cursor/Claude Desktop** (local stdio):
```json
{
  "mcpServers": {
    "ld-mcp": {
      "command": "/home/user/path/to/ld-mcp/venv/bin/python",
      "args": ["/home/user/path/to/ld-mcp/src/main.py"]
    }
  }
}
```

## Available Tools

| Tool | Description |
|------|-------------|
| `list_specifications(family?)` | Browse spec families (RDF, SPARQL, OWL, SHACL, SKOS, PROV) |
| `list_sections(spec_key, depth?)` | Get TOC with section IDs |
| `get_section(spec_key, section_id)` | Get markdown content for a section |
| `list_resources(ns_key)` | List classes/properties in a namespace |
| `get_resource(ns_key, resource)` | Get Turtle definition of a resource |

## Development

```bash
pip install -e ".[dev]"

# Validate all specs/namespaces
pytest tests/test_index.py -v

# Lint
ruff check src/ tests/

# Local HTTP server (for testing)
fastmcp run src/main.py:mcp --transport http --port 8000
```

### Adding Specifications

1. Add entry to `src/index.yaml`
2. Run `pytest tests/test_index.py -v -k "your_spec_key"`
3. Push to main — CI validates automatically

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `SPEC_VERSIONS` | Filter by version (e.g., `"1.2"`) | All |
| `CACHE_TTL` | Cache TTL in seconds | `86400` (24 hours) |
