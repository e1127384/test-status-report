#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
from datetime import datetime, timezone
from pathlib import Path

try:
    import pandas as pd
except ImportError:  # pragma: no cover - runtime dependency guidance
    pd = None


REQUIRED_COLUMNS = [
    "defect_id",
    "story_name",
    "bug_created_date",
    "bug_title",
    "last_updated_date",
    "last_updated_by",
    "bug_status",
    "assigned_to",
    "priority",
    "severity",
]

PRESENTATION_COLUMNS = [
    "defect_id",
    "story_name",
    "bug_title",
    "bug_status",
    "priority",
    "severity",
    "assigned_to",
    "bug_created_date",
    "last_updated_date",
    "last_updated_by",
]


def normalize_columns(frame: pd.DataFrame) -> pd.DataFrame:
    column_map = {col: col.strip().lower() for col in frame.columns}
    frame = frame.rename(columns=column_map)
    missing = [col for col in REQUIRED_COLUMNS if col not in frame.columns]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")
    return frame


def to_datetime(frame: pd.DataFrame) -> pd.DataFrame:
    for col in ("bug_created_date", "last_updated_date"):
        frame[col] = pd.to_datetime(frame[col], errors="coerce")
    return frame


def aggregate_counts(frame: pd.DataFrame, column: str, limit: int = 8) -> pd.DataFrame:
    result = (
        frame[column]
        .fillna("Unknown")
        .astype(str)
        .str.strip()
        .replace("", "Unknown")
        .value_counts()
        .head(limit)
        .reset_index()
    )
    result.columns = [column, "count"]
    return result


def render_bar_rows(frame: pd.DataFrame, label_col: str) -> str:
    if frame.empty:
        return '<tr><td colspan="3">No data available</td></tr>'
    max_value = frame["count"].max() if not frame.empty else 1
    rows = []
    for _, row in frame.iterrows():
        label = html.escape(str(row[label_col]))
        count = int(row["count"])
        width = int((count / max_value) * 100) if max_value else 0
        rows.append(
            f"<tr><td>{label}</td><td>{count}</td>"
            f'<td><div class="bar"><span style="width:{width}%"></span></div></td></tr>'
        )
    return "\n".join(rows)


def render_defect_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "<p>No defects to display.</p>"
    safe = frame.copy()
    safe["bug_created_date"] = safe["bug_created_date"].dt.strftime("%Y-%m-%d")
    safe["last_updated_date"] = safe["last_updated_date"].dt.strftime("%Y-%m-%d")
    safe = safe.fillna("")

    header = "".join(f"<th>{html.escape(col.replace('_', ' ').title())}</th>" for col in safe.columns)
    rows = []
    for _, row in safe.iterrows():
        row_html = []
        for col in safe.columns:
            value = html.escape(str(row[col]))
            if col == "bug_status":
                row_html.append(f'<td><span class="status">{value}</span></td>')
            else:
                row_html.append(f"<td>{value}</td>")
        rows.append(f"<tr>{''.join(row_html)}</tr>")
    return f'<table><thead><tr>{header}</tr></thead><tbody>{"".join(rows)}</tbody></table>'


def build_html(frame: pd.DataFrame, title: str) -> str:
    closed_statuses = {"closed", "done", "resolved", "verified", "completed"}
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    status_values = frame["bug_status"].fillna("").astype(str).str.strip().str.lower()
    open_mask = ~status_values.isin(closed_statuses)
    open_count = int(open_mask.sum())
    total = len(frame)
    closed_count = total - open_count

    ages = (now - frame.loc[open_mask, "bug_created_date"]).dt.days
    avg_age = round(float(ages.dropna().mean()), 1) if not ages.dropna().empty else 0
    stale_count = int((now - frame["last_updated_date"]).dt.days.gt(14).fillna(False).sum())
    updated_last_7_days = int((now - frame["last_updated_date"]).dt.days.le(7).fillna(False).sum())

    by_status = aggregate_counts(frame, "bug_status")
    by_priority = aggregate_counts(frame, "priority")
    by_severity = aggregate_counts(frame, "severity")
    by_assigned = aggregate_counts(frame, "assigned_to")
    detail_table = render_defect_table(
        frame.sort_values(["priority", "severity", "last_updated_date"], ascending=[True, True, False])[
            PRESENTATION_COLUMNS
        ]
    )

    generated = datetime.now().strftime("%Y-%m-%d %H:%M")
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{html.escape(title)}</title>
<style>
body {{font-family: Arial, sans-serif; margin: 24px; color: #1f2937; background: #f8fafc;}}
h1 {{margin-bottom: 4px;}}
.subtitle {{color: #64748b; margin-top: 0;}}
.grid {{display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 14px; margin: 18px 0 24px;}}
.card {{background: #fff; border-radius: 10px; padding: 14px 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.08);}}
.kpi {{font-size: 28px; font-weight: 700; margin: 6px 0 0;}}
.kpi-label {{font-size: 13px; color: #64748b;}}
.section {{background: #fff; border-radius: 10px; padding: 16px; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.08);}}
table {{width: 100%; border-collapse: collapse;}}
th, td {{border-bottom: 1px solid #e2e8f0; padding: 9px; text-align: left; vertical-align: top;}}
th {{background: #f1f5f9; font-size: 13px;}}
.bar {{background: #e2e8f0; border-radius: 999px; height: 10px; width: 100%;}}
.bar span {{display: block; height: 100%; border-radius: 999px; background: linear-gradient(90deg, #0ea5e9, #6366f1);}}
.status {{padding: 3px 8px; border-radius: 999px; background: #e0f2fe; color: #075985; font-size: 12px;}}
</style>
</head>
<body>
<h1>{html.escape(title)}</h1>
<p class="subtitle">Generated on {generated}</p>
<div class="grid">
  <div class="card"><div class="kpi-label">Total Defects</div><div class="kpi">{total}</div></div>
  <div class="card"><div class="kpi-label">Open Defects</div><div class="kpi">{open_count}</div></div>
  <div class="card"><div class="kpi-label">Closed Defects</div><div class="kpi">{closed_count}</div></div>
  <div class="card"><div class="kpi-label">Avg Open Age (days)</div><div class="kpi">{avg_age}</div></div>
  <div class="card"><div class="kpi-label">Stale Defects (&gt;14d)</div><div class="kpi">{stale_count}</div></div>
  <div class="card"><div class="kpi-label">Updated Last 7 Days</div><div class="kpi">{updated_last_7_days}</div></div>
</div>
<div class="section">
  <h2>Status Breakdown</h2>
  <table><thead><tr><th>Status</th><th>Count</th><th>Distribution</th></tr></thead><tbody>{render_bar_rows(by_status, "bug_status")}</tbody></table>
</div>
<div class="section">
  <h2>Priority Breakdown</h2>
  <table><thead><tr><th>Priority</th><th>Count</th><th>Distribution</th></tr></thead><tbody>{render_bar_rows(by_priority, "priority")}</tbody></table>
</div>
<div class="section">
  <h2>Severity Breakdown</h2>
  <table><thead><tr><th>Severity</th><th>Count</th><th>Distribution</th></tr></thead><tbody>{render_bar_rows(by_severity, "severity")}</tbody></table>
</div>
<div class="section">
  <h2>Top Assignees by Defect Load</h2>
  <table><thead><tr><th>Assignee</th><th>Count</th><th>Distribution</th></tr></thead><tbody>{render_bar_rows(by_assigned, "assigned_to")}</tbody></table>
</div>
<div class="section">
  <h2>Defect Detail</h2>
  {detail_table}
</div>
</body>
</html>"""


def main() -> None:
    if pd is None:
        raise SystemExit("Missing dependency: pandas. Install with `pip install pandas openpyxl`.")

    parser = argparse.ArgumentParser(
        description="Convert an Excel defect tracker into an executive-friendly HTML report."
    )
    parser.add_argument("input_excel", type=Path, help="Path to source Excel file")
    parser.add_argument("-o", "--output", type=Path, default=Path("defect_report.html"), help="Output HTML path")
    parser.add_argument("--title", default="Defect Executive Status Report", help="Report title")
    args = parser.parse_args()

    frame = pd.read_excel(args.input_excel)
    frame = normalize_columns(frame)
    frame = to_datetime(frame)
    html_report = build_html(frame, args.title)

    args.output.write_text(html_report, encoding="utf-8")
    print(f"Report written: {args.output}")


if __name__ == "__main__":
    main()
