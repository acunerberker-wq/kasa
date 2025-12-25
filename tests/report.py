# -*- coding: utf-8 -*-
"""Report helpers for UI smoke tests."""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any, Dict, List


def _format_duration(seconds: float) -> str:
    return f"{seconds:.2f}s"


def write_report(results: Dict[str, Any], artifacts_dir: Path, md_path: Path, html_path: Path) -> None:
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    md_path.write_text(_build_markdown(results), encoding="utf-8")
    html_path.write_text(_build_html(results), encoding="utf-8")


def _build_markdown(results: Dict[str, Any]) -> str:
    lines: List[str] = []
    status = results.get("status", "UNKNOWN")
    duration = _format_duration(float(results.get("duration_s", 0.0)))
    lines.append(f"# UI Smoke Test Report")
    lines.append("")
    lines.append(f"**Status:** {status}")
    lines.append(f"**Duration:** {duration}")
    lines.append("")

    errors = results.get("errors") or []
    if errors:
        lines.append("## Unhandled Errors")
        for err in errors:
            lines.append("```\n" + str(err) + "\n```")
        lines.append("")

    lines.append("## Screens")
    for step in results.get("steps", []):
        name = step.get("name")
        key = step.get("key")
        lines.append(f"### {name} ({key})")
        lines.append(f"- Status: {step.get('status')}")
        lines.append(f"- Duration: {_format_duration(float(step.get('duration_s', 0.0)))}")
        heading = step.get("heading")
        if heading:
            lines.append(f"- Heading: {heading}")
        table_headers = step.get("table_headers") or []
        if table_headers:
            lines.append(f"- Table headers: {', '.join(table_headers)}")
        if step.get("table_rows") is not None:
            lines.append(f"- Table rows: {step.get('table_rows')}")
        if step.get("empty_state"):
            lines.append("- Empty state: yes")
        tabs = step.get("tabs") or []
        if tabs:
            lines.append("- Tabs:")
            for tab in tabs:
                lines.append(f"  - {tab.get('text')} (state={tab.get('state')}, content={tab.get('has_content')})")
        buttons = step.get("buttons") or []
        if buttons:
            lines.append("- Buttons:")
            for btn in buttons:
                text = btn.get("text") or ""
                status_info = btn.get("status") or btn.get("state") or ""
                lines.append(f"  - {text} {status_info}".rstrip())
        disabled = step.get("disabled_widgets") or []
        if disabled:
            lines.append(f"- Disabled widgets: {', '.join(disabled)}")
        screenshot = step.get("screenshot")
        if screenshot:
            lines.append(f"- Screenshot: {screenshot}")
        error = step.get("error")
        if error:
            lines.append(f"- Error: {error}")
        lines.append("")

    return "\n".join(lines)


def _build_html(results: Dict[str, Any]) -> str:
    status = html.escape(str(results.get("status", "UNKNOWN")))
    duration = _format_duration(float(results.get("duration_s", 0.0)))
    parts = [
        "<html><head><meta charset='utf-8'>",
        "<style>",
        "body { font-family: Arial, sans-serif; margin: 20px; }",
        ".status { font-weight: bold; }",
        ".pass { color: #0a0; }",
        ".fail { color: #a00; }",
        ".screen { margin-bottom: 20px; padding: 10px; border: 1px solid #ddd; }",
        "</style></head><body>",
        f"<h1>UI Smoke Test Report</h1>",
        f"<p>Status: <span class='status {status.lower()}'> {status}</span></p>",
        f"<p>Duration: {html.escape(duration)}</p>",
    ]

    errors = results.get("errors") or []
    if errors:
        parts.append("<h2>Unhandled Errors</h2>")
        for err in errors:
            parts.append(f"<pre>{html.escape(str(err))}</pre>")

    parts.append("<h2>Screens</h2>")
    for step in results.get("steps", []):
        name = html.escape(str(step.get("name")))
        key = html.escape(str(step.get("key")))
        parts.append("<div class='screen'>")
        parts.append(f"<h3>{name} ({key})</h3>")
        parts.append(f"<p>Status: {html.escape(str(step.get('status')))}</p>")
        parts.append(f"<p>Duration: {html.escape(_format_duration(float(step.get('duration_s', 0.0))))}</p>")
        if step.get("heading"):
            parts.append(f"<p>Heading: {html.escape(str(step.get('heading')))}</p>")
        table_headers = step.get("table_headers") or []
        if table_headers:
            headers = ", ".join(html.escape(str(h)) for h in table_headers)
            parts.append(f"<p>Table headers: {headers}</p>")
        if step.get("table_rows") is not None:
            parts.append(f"<p>Table rows: {html.escape(str(step.get('table_rows')))}</p>")
        if step.get("empty_state"):
            parts.append("<p>Empty state: yes</p>")
        tabs = step.get("tabs") or []
        if tabs:
            parts.append("<ul>")
            for tab in tabs:
                parts.append(
                    f"<li>{html.escape(str(tab.get('text')))} (state={html.escape(str(tab.get('state')))}, content={html.escape(str(tab.get('has_content')))} )</li>"
                )
            parts.append("</ul>")
        buttons = step.get("buttons") or []
        if buttons:
            parts.append("<ul>")
            for btn in buttons:
                text = html.escape(str(btn.get("text") or ""))
                status_info = html.escape(str(btn.get("status") or btn.get("state") or ""))
                parts.append(f"<li>{text} {status_info}</li>")
            parts.append("</ul>")
        disabled = step.get("disabled_widgets") or []
        if disabled:
            parts.append(f"<p>Disabled widgets: {', '.join(html.escape(str(x)) for x in disabled)}</p>")
        screenshot = step.get("screenshot")
        if screenshot:
            parts.append(f"<p>Screenshot: {html.escape(str(screenshot))}</p>")
        if step.get("error"):
            parts.append(f"<p>Error: {html.escape(str(step.get('error')))}</p>")
        parts.append("</div>")

    parts.append("</body></html>")
    return "".join(parts)


if __name__ == "__main__":
    sample_path = Path("test_artifacts/results.json")
    if sample_path.exists():
        data = json.loads(sample_path.read_text(encoding="utf-8"))
        write_report(data, sample_path.parent, Path("test_artifacts/report.md"), Path("test_artifacts/report.html"))
