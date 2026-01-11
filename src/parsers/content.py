"""Section content extraction from W3C specifications."""

from typing import Optional

from bs4 import BeautifulSoup

from fetch import html_to_markdown


def extract_section_content(soup: BeautifulSoup, section_id: str) -> Optional[str]:
    """
    Extract content for a specific section from a W3C spec.

    Looks for elements with matching id and extracts until the next same-level heading.
    """
    section = soup.find(id=section_id)

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
            if sibling.name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
                sibling_level = int(sibling.name[1])
                if sibling_level <= heading_level:
                    break
            content_parts.append(str(sibling))

        return html_to_markdown("".join(content_parts))

    # If it's an anchor (common in older specs), find the next heading and extract from there
    if section.name == "a":
        next_heading = section.find_next(["h1", "h2", "h3", "h4", "h5", "h6"])
        if next_heading:
            heading_level = int(next_heading.name[1])
            content_parts = [str(next_heading)]

            for sibling in next_heading.find_next_siblings():
                if sibling.name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
                    sibling_level = int(sibling.name[1])
                    if sibling_level <= heading_level:
                        break
                content_parts.append(str(sibling))

            return html_to_markdown("".join(content_parts))

    return html_to_markdown(str(section))
