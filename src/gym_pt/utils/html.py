"""Render WorkoutPlan JSON as a standalone HTML document."""

from __future__ import annotations

import copy
import json
from html import escape
from pathlib import Path
from typing import Any, Mapping, Sequence


def _e(text: str | None) -> str:
    return escape(text or "", quote=True)


def _exercise_id_from_catalog_item(ex: Any) -> str | None:
    if isinstance(ex, Mapping):
        eid = ex.get("id")
    else:
        eid = getattr(ex, "id", None)
    return str(eid) if eid is not None else None


def _exercise_catalog_by_id(exercises: Sequence[Any]) -> dict[str, list[str]]:
    """Map catalog ``id`` to instruction lines (from ``Exercise`` or dict)."""
    out: dict[str, list[str]] = {}
    for ex in exercises:
        eid = _exercise_id_from_catalog_item(ex)
        if eid is None:
            continue
        if isinstance(ex, Mapping):
            raw = ex.get("instructions") or []
        else:
            raw = getattr(ex, "instructions", None) or []
        if isinstance(raw, str):
            lines = [raw] if raw.strip() else []
        else:
            lines = [str(x) for x in raw]
        out[eid] = lines
    return out


def enrich_workout_plan_with_instructions(
    plan: Mapping[str, Any], exercises: Sequence[Any]
) -> dict[str, Any]:
    """
    Return a deep copy of ``plan`` with each planned exercise augmented by
    ``instructions`` (list of strings) from the catalog, keyed by ``exercise_id`` → ``id``.
    """
    by_id = _exercise_catalog_by_id(exercises)
    out: dict[str, Any] = copy.deepcopy(dict(plan))
    for day in out.get("days") or []:
        if not isinstance(day, dict):
            continue
        for ex in day.get("exercises") or []:
            if not isinstance(ex, dict):
                continue
            eid = ex.get("exercise_id")
            ex["instructions"] = list(by_id.get(str(eid), [])) if eid is not None else []
    return out


def render_workout_plan_html(plan: Mapping[str, Any]) -> str:
    """Build a full HTML document from a plan dict (e.g. parsed JSON or ``model_dump()``)."""
    title = _e(str(plan.get("title") or "Workout plan"))
    notes = plan.get("notes")
    days = plan.get("days") or []

    day_sections: list[str] = []
    for day in days:
        if not isinstance(day, Mapping):
            continue
        idx = day.get("day_index")
        try:
            day_num = int(idx) + 1 if idx is not None else len(day_sections) + 1
        except (TypeError, ValueError):
            day_num = len(day_sections) + 1
        focus = day.get("focus")
        focus_html = f'<p class="day-focus">{_e(str(focus))}</p>' if focus else ""
        exercises = day.get("exercises") or []

        rows: list[str] = []
        for i, ex in enumerate(exercises, start=1):
            if not isinstance(ex, Mapping):
                continue
            name = _e(str(ex.get("name") or ex.get("exercise_id") or "—"))
            sets = ex.get("sets")
            sets_s = "—" if sets is None else str(sets)
            reps = ex.get("reps")
            reps_s = "—" if reps is None else str(reps)
            raw_instr = ex.get("instructions")
            if isinstance(raw_instr, str):
                instr_lines = [raw_instr] if raw_instr.strip() else []
            elif isinstance(raw_instr, (list, tuple)):
                instr_lines = [str(s) for s in raw_instr if str(s).strip()]
            else:
                instr_lines = []
            if instr_lines:
                steps = "".join(f"<p>{_e(line)}</p>" for line in instr_lines)
                name_cell = (
                    f'<details class="ex-instr">'
                    f'<summary class="ex-summary">{name}</summary>'
                    f'<div class="instr-body">{steps}</div>'
                    f"</details>"
                )
            else:
                name_cell = f'<span class="ex-name-plain">{name}</span>'
            rows.append(
                "<tr>"
                f'<td class="col-num">{i}</td>'
                f'<td class="col-name">{name_cell}</td>'
                f'<td class="col-sets">{_e(sets_s)}</td>'
                f'<td class="col-reps">{_e(reps_s)}</td>'
                "</tr>"
            )

        if not rows:
            rows.append(
                '<tr><td colspan="4" class="empty">No exercises listed.</td></tr>'
            )

        day_sections.append(
            f"""
            <section class="day-card" aria-labelledby="day-{day_num}-heading">
              <header class="day-head">
                <h2 id="day-{day_num}-heading">Day {day_num}</h2>
                {focus_html}
              </header>
              <div class="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th class="col-num" scope="col">#</th>
                      <th scope="col">Exercise</th>
                      <th class="col-sets" scope="col">Sets</th>
                      <th class="col-reps" scope="col">Reps / time</th>
                    </tr>
                  </thead>
                  <tbody>
                    {"".join(rows)}
                  </tbody>
                </table>
              </div>
            </section>
            """
        )

    notes_block = ""
    if notes:
        notes_block = f"""
        <section class="notes" aria-labelledby="notes-heading">
          <h2 id="notes-heading">Notes</h2>
          <p>{_e(str(notes))}</p>
        </section>
        """

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title}</title>
  <style>
    :root {{
      --bg: #0f1419;
      --surface: #1a222d;
      --border: #2d3a4a;
      --text: #e8eaed;
      --muted: #9aa5b1;
      --accent: #3ecf8e;
      --accent-dim: #2a8f5e;
      --radius: 12px;
      --font: "Segoe UI", system-ui, sans-serif;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      font-family: var(--font);
      background: radial-gradient(ellipse 120% 80% at 50% -20%, #1e3a2f 0%, var(--bg) 55%);
      color: var(--text);
      line-height: 1.5;
      padding: 1.5rem clamp(1rem, 4vw, 2.5rem) 3rem;
    }}
    .wrap {{
      max-width: 52rem;
      margin: 0 auto;
    }}
    header.page {{
      margin-bottom: 2rem;
      padding-bottom: 1.25rem;
      border-bottom: 1px solid var(--border);
    }}
    header.page h1 {{
      margin: 0 0 0.35rem;
      font-size: clamp(1.35rem, 3vw, 1.75rem);
      font-weight: 650;
      letter-spacing: -0.02em;
    }}
    header.page .subtitle {{
      margin: 0;
      color: var(--muted);
      font-size: 0.95rem;
    }}
    .days {{
      display: flex;
      flex-direction: column;
      gap: 1.5rem;
    }}
    .day-card {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      overflow: hidden;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.25);
    }}
    .day-head {{
      padding: 1rem 1.25rem;
      background: linear-gradient(135deg, rgba(62, 207, 142, 0.12) 0%, transparent 60%);
      border-bottom: 1px solid var(--border);
    }}
    .day-head h2 {{
      margin: 0;
      font-size: 1.1rem;
      font-weight: 650;
      color: var(--accent);
    }}
    .day-focus {{
      margin: 0.4rem 0 0;
      color: var(--muted);
      font-size: 0.9rem;
    }}
    .table-wrap {{
      overflow-x: auto;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.9rem;
    }}
    th, td {{
      padding: 0.65rem 1rem;
      text-align: left;
      border-bottom: 1px solid var(--border);
    }}
    th {{
      color: var(--muted);
      font-weight: 600;
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 0.06em;
    }}
    tbody tr:last-child td {{
      border-bottom: none;
    }}
    tbody tr:hover td {{
      background: rgba(62, 207, 142, 0.06);
    }}
    .col-num {{ width: 2.5rem; color: var(--muted); vertical-align: top; }}
    .col-sets {{ width: 4rem; vertical-align: top; }}
    .col-reps {{ width: 8rem; vertical-align: top; }}
    .col-name {{ vertical-align: top; }}
    details.ex-instr {{
      margin: 0;
    }}
    details.ex-instr summary.ex-summary {{
      cursor: pointer;
      font-weight: 500;
      list-style: none;
      padding: 0.15rem 0;
    }}
    details.ex-instr summary.ex-summary::-webkit-details-marker {{
      display: none;
    }}
    details.ex-instr summary.ex-summary::before {{
      content: "▸ ";
      color: var(--accent);
      display: inline-block;
      transition: transform 0.15s ease;
    }}
    details.ex-instr[open] summary.ex-summary::before {{
      transform: rotate(90deg);
    }}
    .instr-body {{
      margin: 0.5rem 0 0.35rem 1rem;
      padding: 0.65rem 0.85rem;
      border-left: 2px solid var(--accent-dim);
      background: rgba(0, 0, 0, 0.2);
      border-radius: 0 8px 8px 0;
      font-size: 0.85rem;
      color: var(--muted);
    }}
    .instr-body p {{
      margin: 0 0 0.5rem;
    }}
    .instr-body p:last-child {{
      margin-bottom: 0;
    }}
    .ex-name-plain {{
      display: inline-block;
      padding: 0.15rem 0;
    }}
    td.empty {{
      color: var(--muted);
      font-style: italic;
      text-align: center;
      padding: 1.25rem;
    }}
    .notes {{
      margin-top: 2rem;
      padding: 1.25rem 1.5rem;
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      border-left: 3px solid var(--accent-dim);
    }}
    .notes h2 {{
      margin: 0 0 0.75rem;
      font-size: 1rem;
      color: var(--accent);
    }}
    .notes p {{
      margin: 0;
      color: var(--text);
      font-size: 0.95rem;
      white-space: pre-wrap;
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <header class="page">
      <h1>{title}</h1>
      <p class="subtitle">{len([d for d in days if isinstance(d, Mapping)])} training day(s)</p>
    </header>
    <main class="days">
      {"".join(day_sections)}
    </main>
    {notes_block}
  </div>
</body>
</html>
"""


def workout_plan_json_to_html(path: Path | str) -> str:
    """Load a WorkoutPlan JSON file and return a complete HTML document."""
    p = Path(path)
    with p.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, Mapping):
        raise TypeError(f"Expected JSON object at root, got {type(data).__name__}")
    return render_workout_plan_html(data)
