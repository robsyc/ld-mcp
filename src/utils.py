"""
Utilities for fetching and parsing W3C specification documents.
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx
from bs4 import BeautifulSoup, Tag
from html_to_markdown import convert

from models import TOCItem, CachedSpec


# Shared HTTP client for async requests
http_client = httpx.AsyncClient(
    timeout=30.0, 
    follow_redirects=True,
    headers={"User-Agent": "ld-mcp/1.0 (Linked Data MCP Server)"}
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
    # See:https://github.com/kreuzberg-dev/html-to-markdown/blob/main/packages/python/README.md
    return convert(html)


def parse_w3c_toc(soup: BeautifulSoup) -> list[TOCItem]:
    """
    Parse Table of Contents from a W3C specification.
    
    W3C specs typically use:
    - <nav id="toc"> or <div class="toc"> or <table class="toc" id="toc"> for TOC container
    - Nested <ol>/<ul> lists for structure
    - <a href="#section-id"> links with section titles
    """
    toc_items: list[TOCItem] = []
    
    # Try to find TOC container (W3C specs use various conventions)
    toc_container = (
        soup.find("nav", id="toc") or
        soup.find("table", id="toc") or
        soup.find("div", id="toc") or
        soup.find("div", class_="toc") or
        soup.find("section", id="toc")
    )
    
    if not toc_container:
        # Might want to raise an error here
        return toc_items
    
    def parse_toc_list(ol_or_ul: Tag, depth: int = 1) -> list[TOCItem]:
        """Recursively parse a TOC list."""
        items = []
        for li in ol_or_ul.find_all("li", recursive=False):
            # Find the link in this list item
            link = li.find("a", recursive=False) or li.find("a")
            if not link:
                continue
            
            href = link.get("href", "")
            anchor = href.lstrip("#") if href.startswith("#") else None
            title = link.get_text(strip=True)
            
            # Generate a clean ID from anchor or title
            section_id = anchor or re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
            
            item = TOCItem(
                id=section_id,
                title=title,
                depth=depth,
                anchor=anchor,
                children=[]
            )
            
            # Look for nested list (children)
            nested = li.find(["ol", "ul"], recursive=False)
            if nested:
                item.children = parse_toc_list(nested, depth + 1)
            
            items.append(item)
        
        return items
    
    # Find the main TOC list
    main_list = toc_container.find(["ol", "ul"])
    if main_list:
        toc_items = parse_toc_list(main_list)
    
    return toc_items


def extract_section_content(soup: BeautifulSoup, section_id: str) -> Optional[str]:
    """
    Extract content for a specific section from a W3C spec.
    
    Looks for elements with matching id and extracts until the next same-level heading.
    """
    # Find the section by ID
    section = soup.find(id=section_id)
    if not section:
        # Try finding by anchor name
        section = soup.find("a", attrs={"name": section_id})
        if section:
            section = section.parent
    
    if not section:
        return None
    
    # If it's a section/div element, get its content directly
    if section.name in ["section", "div"]:
        return html_to_markdown(str(section))
    
    # If it's a heading, collect content until next same-level heading
    if section.name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
        heading_level = int(section.name[1])
        content_parts = [str(section)]
        
        for sibling in section.find_next_siblings():
            # Stop at next same-level or higher heading
            if sibling.name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
                sibling_level = int(sibling.name[1])
                if sibling_level <= heading_level:
                    break
            content_parts.append(str(sibling))
        
        return html_to_markdown("".join(content_parts))
    
    return html_to_markdown(str(section))


def flatten_toc(toc: list[TOCItem], max_depth: Optional[int] = None) -> list[dict]:
    """
    Flatten a nested TOC into a list of items with depth info.
    
    Args:
        toc: Nested TOC items
        max_depth: Maximum depth to include (None = all)
    
    Returns:
        List of dicts with id, title, depth
    """
    result = []
    
    def collect(items: list[TOCItem], current_depth: int = 1):
        for item in items:
            if max_depth is None or current_depth <= max_depth:
                result.append({
                    "id": item.id,
                    "title": item.title,
                    "depth": item.depth
                })
                if item.children:
                    collect(item.children, current_depth + 1)
    
    collect(toc)
    return result


# --- Cache Management ---

def save_to_cache(path: Path, data: dict | str) -> None:
    """Save data to cache file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    
    if isinstance(data, str):
        path.write_text(data, encoding="utf-8")
    else:
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_from_cache(path: Path, max_age_seconds: int) -> Optional[dict | str]:
    """
    Load data from cache if it exists and isn't expired.
    
    Returns None if cache miss or expired.
    """
    if not path.exists():
        return None
    
    # Check age
    mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    age = (datetime.now(timezone.utc) - mtime).total_seconds()
    
    if age > max_age_seconds:
        return None
    
    content = path.read_text(encoding="utf-8")
    
    # Try to parse as JSON, otherwise return as string
    if path.suffix == ".json":
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return content
    
    return content


def now_iso() -> str:
    """Get current time as ISO format string."""
    return datetime.now(timezone.utc).isoformat()
