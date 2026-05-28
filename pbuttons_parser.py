import re
from dataclasses import dataclass, field
from typing import Optional

# Sections known to contain potentially sensitive information
SENSITIVE_SECTIONS = {
    "Configuration": "Contains instance name, machine name, GUID, license number, and product version.",
    "Profile": "Contains username/email of the person who ran the report and directory paths.",
    "License": "Contains license type, user counts, and feature codes.",
    "CPF file": "Contains full filesystem paths for all databases and namespaces.",
    "IRIS ALL": "Lists all IRIS instances on the machine with their ports and directories.",
    "Windows info": "Contains detailed OS, hardware, and network configuration.",
    "tasklist": "Lists all running processes on the machine.",
}

@dataclass
class Section:
    id: str
    title: str
    content_html: str
    sensitive: bool = False
    sensitive_reason: Optional[str] = None


def parse_sections(html: str) -> tuple[str, list[Section]]:
    """
    Parse a pButtons HTML file into its header and individual sections.
    Returns (header_html, [Section, ...]).
    """
    # The header is everything before the first <hr> separator that precedes a section
    # Sections are delimited by <hr size="4" noshade> followed by a div id=...
    # Pattern: find each section start
    section_pattern = re.compile(
        r'(<hr size="4" noshade>|<hr size="4" noshade/>)'
        r'(<b>.*?<div id=["\']?([^"\'>\s]+)["\']?></div>'
        r'(.*?)</font></b>.*?<pre>(.*?)</pre>)'
        r'(?=<p align="right">.*?Back to top|$)',
        re.DOTALL | re.IGNORECASE
    )

    # Simpler approach: split on the hr+section pattern
    # Find all section anchors with their positions
    anchor_pattern = re.compile(
        r'<hr size="4" noshade>\s*<b><font[^>]*>'
        r'<div id=["\']?([^"\'>\s]+)["\']?></div>'
        r'([^<]+)</font></b>',
        re.IGNORECASE
    )

    matches = list(anchor_pattern.finditer(html))

    if not matches:
        return html, []

    # Everything before the first section anchor is the header
    # (includes the nav table and debug comment and Configuration/Profile sections
    #  which use a slightly different pattern)
    header_end = matches[0].start()

    # Also grab Configuration and Profile which use <p>...<div id="..."> pattern
    config_pattern = re.compile(
        r'(<p>\s*<b><font[^>]*><div id=["\']([^"\'>\s]+)["\']></div>'
        r'([^<]+)</font></b></p>)(.*?)'
        r'(?=<hr size="4" noshade>)',
        re.DOTALL | re.IGNORECASE
    )

    sections: list[Section] = []

    # Parse Configuration / Profile (pre-section area)
    for m in config_pattern.finditer(html[:header_end + 5000]):
        section_id = m.group(2)
        title = m.group(3).strip()
        # grab pre content
        pre_match = re.search(r'<pre>(.*?)</pre>', m.group(0), re.DOTALL)
        content = m.group(0)
        sections.append(Section(
            id=section_id,
            title=title,
            content_html=content,
            sensitive=title in SENSITIVE_SECTIONS,
            sensitive_reason=SENSITIVE_SECTIONS.get(title),
        ))

    # Parse main sections
    for i, m in enumerate(matches):
        section_id = m.group(1)
        title = m.group(2).strip()

        # Content runs from this match to the next match (or end)
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(html)
        content_html = html[start:end]

        sections.append(Section(
            id=section_id,
            title=title,
            content_html=content_html,
            sensitive=title in SENSITIVE_SECTIONS,
            sensitive_reason=SENSITIVE_SECTIONS.get(title),
        ))

    # Build header: nav table + debug comment (before first config section or first hr section)
    # Use the raw html up to the first <p> config block or first hr section
    first_config = config_pattern.search(html)
    if first_config:
        header_html = html[:first_config.start()]
    else:
        header_html = html[:header_end]

    return header_html, sections


_EXCLUDED_PLACEHOLDER = (
    '<pre>\n'
    '    [ This section was excluded by the report author. ]\n'
    '    [ Filtered using pButtons Parser - a free tool that redacts InterSystems IRIS\n'
    '      pButtons files locally, without uploading any data to the cloud. ]\n'
    '</pre>'
)


def _make_excluded_html(content_html: str) -> str:
    """Replace all <pre> content blocks with a single exclusion placeholder."""
    # Remove all pre blocks first, then insert one placeholder at the first position
    first_pre = re.search(r'<pre>', content_html, re.IGNORECASE)
    if not first_pre:
        return content_html
    stripped = re.sub(r'<pre>.*?</pre>', '', content_html, flags=re.DOTALL | re.IGNORECASE)
    return stripped[:first_pre.start()] + _EXCLUDED_PLACEHOLDER + stripped[first_pre.start():]


def build_output(header_html: str, sections: list[Section], selected_ids: list[str]) -> str:
    """Reconstruct an HTML file. Selected sections keep their content; excluded
    sections retain their header and anchor (so nav links still work) but their
    data is replaced with a placeholder message."""
    selected_set = set(selected_ids)
    body_parts = [header_html]
    for s in sections:
        if s.id in selected_set:
            body_parts.append(s.content_html)
        else:
            body_parts.append(_make_excluded_html(s.content_html))

    body_parts.append(
        '\n<hr size="4" noshade>\n'
        '<p><font face="Arial, Helvetica, sans-serif" size="4" color="#0000FF">'
        '<b>End of Performance Data Report</b></font>\n</p>\n</body>\n</html>'
    )
    return "".join(body_parts)
