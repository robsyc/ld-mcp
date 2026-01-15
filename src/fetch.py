"""HTTP client and fetch utilities."""

import re

import httpx
from html_to_markdown import ConversionOptions, convert

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


# Configure markdown conversion for clean MCP output
_md_options = ConversionOptions(
    heading_style="atx",  # Use # style headings (cleaner)
    code_block_style="fenced",  # Use ``` fenced code blocks
)


def html_to_markdown(html: str) -> str:
    """Convert HTML content to Markdown.

    Sanitizes HTML to work around html-to-markdown library bugs with
    certain Unicode characters (e.g., NBSP) that cause byte boundary panics.
    """
    # Replace non-breaking spaces with regular spaces to avoid Rust panic
    # See: https://github.com/kreuzberg-dev/html-to-markdown/issues
    sanitized = html.replace("\u00a0", " ").replace("&nbsp;", " ")

    md = convert(sanitized, _md_options)
    md = re.sub(r"\n{3,}", "\n\n", md)  # Max 2 consecutive newlines

    return md.strip()
