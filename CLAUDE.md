# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

A web tool for extracting specific sections from InterSystems IRIS pButtons HTML performance reports. Users upload a pButtons file, select which sections to include, and download a filtered HTML file. Sensitive sections are pre-deselected with explanations.

## Environment

Always use the `venv` virtual environment — never global pip or python.

```bash
# First-time setup
python -m venv venv
./venv/Scripts/pip install -r requirements.txt

# Run the dev server
./venv/Scripts/uvicorn app:app --host 127.0.0.1 --port 8000 --reload
```

The app is then available at http://127.0.0.1:8000.

## Architecture

The app has three layers that must stay in sync:

**[pbuttons_parser.py](pbuttons_parser.py)** — Pure parsing logic, no web framework dependency.
- `parse_sections(html)` → `(header_html, [Section])`: splits the file into a header block (nav table + debug comment) and a list of `Section` dataclasses. Uses two regex patterns: one for `Configuration`/`Profile` which use `<div id="...">` (quoted), and one for all other sections which use `<div id=...>` (unquoted).
- `build_output(header_html, sections, selected_ids)` → `str`: iterates **all** sections — selected ones keep their full content, excluded ones have their `<pre>` data replaced via `_make_excluded_html()`. Every section's header and anchor `<div id=...>` is always preserved so the nav links at the top of the file continue to work.
- `_make_excluded_html(content_html)`: strips all `<pre>…</pre>` blocks then inserts `_EXCLUDED_PLACEHOLDER` at the position of the first `<pre>`. The strip-then-insert order is important — do not replace-then-strip or the placeholder itself gets removed.
- `_EXCLUDED_PLACEHOLDER`: the message shown in place of excluded data, credits the tool and reinforces the local-processing privacy guarantee.
- `SENSITIVE_SECTIONS` dict maps section titles to human-readable reasons — this is what drives the UI warnings and default deselection.

**[app.py](app.py)** — FastAPI backend with two endpoints:
- `POST /upload` — accepts a multipart `.html` file, calls `parse_sections`, stores result in the in-memory `sessions` dict keyed by UUID, returns section metadata (id, title, sensitive flag, reason).
- `POST /export` — accepts `{session_id, selected_ids, output_filename}`, calls `build_output`, writes to `outputs/`, returns as a file download.

Sessions are in-memory only — they are lost on server restart. The `uploads/` directory exists but files are not written there; only `outputs/` gets written.

**[static/index.html](static/index.html)** — Single-file vanilla JS frontend (no build step). Communicates with the backend via `fetch`. Key flow: drag-drop/select file → `POST /upload` → render section checklist → user toggles sections → `POST /export` → trigger browser download via blob URL.

## pButtons HTML format

The file uses `iso-8859-1` encoding. Section boundaries are `<hr size="4" noshade>` followed by a bold font tag containing a `<div id=SECTIONID>` anchor. The first two sections (Configuration, Profile) use quoted IDs (`<div id="Configuration">`) while all subsequent sections use unquoted IDs (`<div id=mgstat>`). Each section ends with a "Back to top" link before the next `<hr>`.

When adding new section types to `SENSITIVE_SECTIONS`, the key must exactly match the `title` field returned by the parser (which is the text content of the section heading).

## .gitignore

`/*.html` (root-level only) excludes pButtons data files while keeping `static/index.html` tracked. Never broaden this to `**/*.html`.

## Reusable skill

A global Claude Code slash command `/iris-report-parser` at `~/.claude/commands/iris-report-parser.md` captures the full recipe for building similar tools for other InterSystems IRIS HTML reports.
