#!/usr/bin/env python3
import json
import os
import sys
import urllib.request
from datetime import date

TOKEN = os.environ.get("GITHUB_TOKEN")
USERNAME = os.environ.get("GH_USERNAME", "Lcos-000")
OUTPUT = os.environ.get("OUTPUT_PATH", "heatmap.svg")

CELL = 11
GAP = 3
PITCH = CELL + GAP
LEFT = 28
TOP = 20
LEGEND_H = 22

PALETTE = ["#EBEDF0", "#BAE6FD", "#7DD3FC", "#38BDF8", "#0EA5E9"]
TEXT = "#57606A"

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
          }
        }
      }
    }
  }
}
"""


def graphql(query, variables):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={
            "Authorization": "bearer %s" % TOKEN,
            "Content-Type": "application/json",
            "User-Agent": "heatmap-generator",
        },
    )
    with urllib.request.urlopen(req) as resp:
        payload = json.load(resp)
    if "errors" in payload:
        raise SystemExit(payload["errors"])
    return payload["data"]


def level(count, max_count):
    if count == 0:
        return 0
    if max_count <= 4:
        return 1 if count == 1 else 4
    return max(1, min(4, (count * 4 + max_count - 1) // max_count))


def month_name(idx):
    return ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
            "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][idx - 1]


def main():
    data = graphql(QUERY, {"login": USERNAME})
    cal = data["user"]["contributionsCollection"]["contributionCalendar"]
    weeks = cal["weeks"]
    total = cal["totalContributions"]

    all_days = [d for w in weeks for d in w["contributionDays"]]
    max_count = max((d["contributionCount"] for d in all_days), default=1)

    width = LEFT + len(weeks) * PITCH + 2
    height = TOP + 7 * PITCH + LEGEND_H

    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
        'viewBox="0 0 %d %d" font-family="-apple-system,BlinkMacSystemFont,'
        'Segoe UI,Helvetica,Arial,sans-serif">' % (width, height, width, height)
    ]

    last_month = None
    for col, week in enumerate(weeks):
        for day in week["contributionDays"]:
            d = date.fromisoformat(day["date"])
            row = (d.weekday() + 1) % 7
            x = LEFT + col * PITCH
            y = TOP + row * PITCH
            fill = PALETTE[level(day["contributionCount"], max_count)]
            parts.append(
                '<rect x="%d" y="%d" width="%d" height="%d" rx="2" ry="2" '
                'fill="%s"><title>%s: %d</title></rect>'
                % (x, y, CELL, CELL, fill, day["date"], day["contributionCount"])
            )
            if row == 0 and d.month != last_month and (d.day <= 7 or col == 0):
                last_month = d.month
                parts.append(
                    '<text x="%d" y="14" font-size="10" fill="%s">%s</text>'
                    % (x, TEXT, month_name(d.month))
                )

    lx = width - 2 - 5 * PITCH - 30
    ly = TOP + 7 * PITCH + 10
    parts.append('<text x="%d" y="%d" font-size="10" fill="%s">Less</text>'
                 % (lx, ly + 9, TEXT))
    for i in range(5):
        parts.append(
            '<rect x="%d" y="%d" width="%d" height="%d" rx="2" ry="2" fill="%s"/>'
            % (lx + 28 + i * PITCH, ly, CELL, CELL, PALETTE[i])
        )
    parts.append('<text x="%d" y="%d" font-size="10" fill="%s">More</text>'
                 % (lx + 28 + 5 * PITCH + 2, ly + 9, TEXT))
    parts.append("</svg>")

    with open(OUTPUT, "w", encoding="utf-8") as fh:
        fh.write("".join(parts))
    print("wrote %s (%d contributions, max/day=%d)" % (OUTPUT, total, max_count))


if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit("GITHUB_TOKEN is required")
    main()
