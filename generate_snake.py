#!/usr/bin/env python3
"""Generate an animated GitHub contribution snake as SVG (light + dark).

Usage:
    GITHUB_TOKEN=xxx python generate_snake.py iitking
    python generate_snake.py iitking          # no token -> scrapes public page

Output:
    dist/github-snake.svg
    dist/github-snake-dark.svg
"""
import json
import os
import re
import sys
import urllib.request
from datetime import date, timedelta
from pathlib import Path

CELL = 14          # cell size (px)
GAP = 3            # gap between cells
PAD = 16           # outer padding
STEP = 0.12        # seconds per move
SNAKE_LEN = 5

THEMES = {
    "light": {
        "bg": "#ffffff",
        "empty": "#ebedf0",
        "levels": ["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"],
        "snake": "#8250df",
        "head": "#6639ba",
    },
    "dark": {
        "bg": "#0d1117",
        "empty": "#161b22",
        "levels": ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"],
        "snake": "#a371f7",
        "head": "#d2a8ff",
    },
}

GQL_LEVELS = {
    "NONE": 0, "FIRST_QUARTER": 1, "SECOND_QUARTER": 2,
    "THIRD_QUARTER": 3, "FOURTH_QUARTER": 4,
}


def fetch_graphql(user, token):
    query = """
    query($login:String!){
      user(login:$login){
        contributionsCollection{
          contributionCalendar{
            weeks{ contributionDays{ date contributionLevel } }
          }
        }
      }
    }"""
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": {"login": user}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    return {
        date.fromisoformat(d["date"]): GQL_LEVELS.get(d["contributionLevel"], 0)
        for w in weeks for d in w["contributionDays"]
    }


def fetch_scrape(user):
    req = urllib.request.Request(
        f"https://github.com/users/{user}/contributions",
        headers={"User-Agent": "Mozilla/5.0"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        html = r.read().decode("utf-8", "ignore")
    out = {}
    for tag in re.findall(r"<td[^>]*ContributionCalendar-day[^>]*>", html):
        d = re.search(r'data-date="(\d{4}-\d{2}-\d{2})"', tag)
        l = re.search(r'data-level="(\d)"', tag)
        if d and l:
            out[date.fromisoformat(d.group(1))] = int(l.group(1))
    return out


def build_grid(days):
    """Return (cols, cells) where cells = {(col,row): level}. Sunday = row 0."""
    first = min(days)
    start = first - timedelta(days=(first.weekday() + 1) % 7)
    cells = {}
    for d, lvl in days.items():
        col = (d - start).days // 7
        row = (d.weekday() + 1) % 7
        cells[(col, row)] = lvl
    cols = max(c for c, _ in cells) + 1
    return cols, cells


def snake_path(cols):
    """Zig-zag over every column: down, up, down, ..."""
    path = []
    for c in range(cols):
        rows = range(7) if c % 2 == 0 else range(6, -1, -1)
        path.extend((c, r) for r in rows)
    return path


def pos(col, row):
    return PAD + col * (CELL + GAP), PAD + row * (CELL + GAP)


def render(cols, cells, theme):
    t = THEMES[theme]
    path = snake_path(cols)
    n = len(path)
    total = n * STEP
    width = PAD * 2 + cols * (CELL + GAP) - GAP
    height = PAD * 2 + 7 * (CELL + GAP) - GAP

    # index at which the head reaches each cell
    reach = {cell: i for i, cell in enumerate(path)}

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}">',
        f'<rect width="100%" height="100%" fill="{t["bg"]}" rx="6"/>',
    ]

    # contribution cells (eaten when the head passes)
    for (c, r), lvl in sorted(cells.items()):
        x, y = pos(c, r)
        color = t["levels"][lvl]
        rect = f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="3" fill="{color}"'
        if lvl > 0 and (c, r) in reach:
            p = reach[(c, r)] / n
            p = min(max(p, 0.0001), 0.9999)
            rect += (
                f'><animate attributeName="fill" calcMode="discrete" dur="{total:.2f}s" '
                f'repeatCount="indefinite" keyTimes="0;{p:.5f};1" '
                f'values="{color};{t["empty"]};{t["empty"]}"/></rect>'
            )
        else:
            rect += "/>"
        out.append(rect)

    # snake segments: segment k is the head's position k steps ago
    key_times = ";".join(f"{i / n:.5f}" for i in range(n))
    for k in range(SNAKE_LEN - 1, -1, -1):  # draw head last (on top)
        xs, ys = [], []
        for i in range(n):
            cx, cy = path[max(i - k, 0)]
            x, y = pos(cx, cy)
            xs.append(str(x))
            ys.append(str(y))
        color = t["head"] if k == 0 else t["snake"]
        size = CELL if k == 0 else CELL - 2
        off = 0 if k == 0 else 1
        x0, y0 = xs[0], ys[0]
        out.append(
            f'<rect width="{size}" height="{size}" rx="4" fill="{color}" '
            f'x="{int(x0) + off}" y="{int(y0) + off}">'
            f'<animate attributeName="x" calcMode="discrete" dur="{total:.2f}s" '
            f'repeatCount="indefinite" keyTimes="{key_times}" '
            f'values="{";".join(str(int(v) + off) for v in xs)}"/>'
            f'<animate attributeName="y" calcMode="discrete" dur="{total:.2f}s" '
            f'repeatCount="indefinite" keyTimes="{key_times}" '
            f'values="{";".join(str(int(v) + off) for v in ys)}"/>'
            f"</rect>"
        )

    out.append("</svg>")
    return "\n".join(out)


def main():
    user = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("GITHUB_USER", "iitking")
    token = os.environ.get("GITHUB_TOKEN")

    try:
        days = fetch_graphql(user, token) if token else fetch_scrape(user)
    except Exception as e:  # fall back to scraping if API fails
        print(f"Primary fetch failed ({e}), trying scrape...", file=sys.stderr)
        days = fetch_scrape(user)

    if not days:
        sys.exit("No contribution data found.")

    cols, cells = build_grid(days)
    out_dir = Path("dist")
    out_dir.mkdir(exist_ok=True)
    (out_dir / "github-snake.svg").write_text(render(cols, cells, "light"), encoding="utf-8")
    (out_dir / "github-snake-dark.svg").write_text(render(cols, cells, "dark"), encoding="utf-8")
    print(f"Done: {len(days)} days, {cols} weeks -> dist/")


if __name__ == "__main__":
    main()
