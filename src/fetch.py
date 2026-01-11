"""HTTP client and fetch utilities."""

import httpx
from html_to_markdown import convert

http_client = httpx.AsyncClient(
    timeout=30.0,
    follow_redirects=True,
    headers={"User-Agent": "ld-mcp/1.0 (Linked Data MCP Server)"},
)


async def fetch_html(url: str) -> str:
    """Fetch HTML content from a URL."""
    try:
        response = await http_client.get(url)
        response.raise_for_status()
        return response.text
    except httpx.HTTPStatusError as e:
        raise Exception(f"HTTP error {e.response.status_code} fetching {url}")
    except httpx.TimeoutException:
        raise Exception(f"Timeout fetching {url}")
    except Exception as e:
        raise Exception(f"Error fetching {url}: {str(e)}")


def html_to_markdown(html: str) -> str:
    """Convert HTML content to Markdown."""
    return convert(html)
