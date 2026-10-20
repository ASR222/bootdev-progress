"""Fetch public Boot.dev progress and regenerate the history, card and README.

Uses only the standard library so the GitHub Action needs no installs.
Usage: python scripts/update.py
"""
import csv
import datetime as dt
import json
import os
import urllib.request
from html import escape

HANDLE = os.environ.get("BOOTDEV_HANDLE", "unlawfulform24")
API = f"https://api.boot.dev/v1/users/public/{HANDLE}"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HISTORY = os.path.join(ROOT, "data", "history.csv")
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
FIELDS = ["date", "level", "xp", "lessons", "percentile", "achievements"]


def get(path=""):
    req = urllib.request.Request(API + path, headers={"User-Agent": "bootdev-progress"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)["data"]


def load_history():
    if not os.path.exists(HISTORY):
        return []
    with open(HISTORY, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save_history(rows):
    os.makedirs(os.path.dirname(HISTORY), exist_ok=True)
    with open(HISTORY, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


def card(p, s, unlocked):
    pct = max(0.0, min(1.0, p["xpForLevel"] / p["xpTotalForLevel"])) if p["xpTotalForLevel"] else 0
    bar = 395 * pct
    top = round(100 - s["leaderboardXPPercentileAlltime"], 1)
    stats = [
        (f"{p['xp']:,}", "Total XP"),
        (str(s["lessonsCompleted"]), "Lessons"),
        (f"Top {top:g}%", "All-time"),
        (str(len(unlocked)), "Achievements"),
    ]
    cells = "".join(
        f'<text x="{27 + 99 * (i + 0.5):.0f}" y="168" class="v">{escape(v)}</text>'
        f'<text x="{27 + 99 * (i + 0.5):.0f}" y="186" class="l">{escape(l)}</text>'
        for i, (v, l) in enumerate(stats)
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="450" height="205" viewBox="0 0 450 205" role="img" aria-label="Boot.dev progress for {escape(HANDLE)}">
<style>
text{{font-family:'Segoe UI',Ubuntu,'Helvetica Neue',sans-serif;fill:#e6edf3}}
.h{{font-size:18px;font-weight:700}}.s{{font-size:12px;fill:#8b949e}}
.lv{{font-size:30px;font-weight:800;fill:#ffffff}}.r{{font-size:13px;fill:#9fb0ff;font-weight:600}}
.v{{font-size:17px;font-weight:700;text-anchor:middle}}.l{{font-size:11px;fill:#8b949e;text-anchor:middle}}
</style>
<rect x="0.5" y="0.5" width="449" height="204" rx="10" fill="#161616"/>
<text x="27" y="36" class="h">Boot.dev</text>
<text x="423" y="36" class="s" text-anchor="end">@{escape(HANDLE)}</text>
<text x="27" y="82" class="lv">Level {p['level']}</text>
<text x="{27 + 17 * len(f"Level {p['level']}") + 14}" y="80" class="r">{escape(p['role'])}</text>
<rect x="27" y="98" width="395" height="10" rx="5" fill="#21262d"/>
<rect x="27" y="98" width="{bar:.1f}" height="10" rx="5" fill="#4F6BFF"/>
<text x="27" y="126" class="s">{p['xpForLevel']:,} / {p['xpTotalForLevel']:,} XP to level {p['level'] + 1}</text>
<line x1="27" y1="140" x2="423" y2="140" stroke="#21262d"/>
{cells}
</svg>
"""


def readme(p, s, unlocked, history):
    top = round(100 - s["leaderboardXPPercentileAlltime"], 1)
    recent = history[-30:]
    chart = ""
    if len(recent) >= 2:
        labels = ", ".join(f'"{r["date"][5:]}"' for r in recent)
        xs = ", ".join(r["xp"] for r in recent)
        chart = f"""
## 📈 XP over time

```mermaid
xychart-beta
    title "Total XP (last {len(recent)} days tracked)"
    x-axis [{labels}]
    y-axis "XP"
    line [{xs}]
```
"""
    ach = "\n".join(
        f'| <img src="{a["thumbnailURL"]}" width="28" /> | **{escape(a["title"])}** | {escape(a["description"])} | {a["unlockedAt"][:10]} |'
        for a in sorted(unlocked, key=lambda a: a["unlockedAt"])
    ) or "| | _None yet_ | | |"
    rows = "\n".join(
        f'| {r["date"]} | {r["level"]} | {int(r["xp"]):,} | {r["lessons"]} |' for r in reversed(history[-14:])
    )
    return f"""# 🐉 Boot.dev progress

My backend-development practice on [Boot.dev](https://www.boot.dev/u/{HANDLE}), tracked automatically.
A GitHub Action reads my public Boot.dev profile every day and updates this page, [`card.svg`](card.svg) and [`data/history.csv`](data/history.csv).

<p align="center"><img src="card.svg" alt="Boot.dev stats card" /></p>

| Level | Rank | Total XP | Lessons completed | All-time leaderboard |
|:-:|:-:|:-:|:-:|:-:|
| **{p['level']}** | {escape(p['role'])} | {p['xp']:,} | {s['lessonsCompleted']} | Top {top:g}% |
{chart}
## 🏆 Achievements unlocked

| | Achievement | Requirement | Unlocked |
|:-:|---|---|---|
{ach}

## 🗓️ Recent history

| Date | Level | XP | Lessons |
|---|:-:|--:|:-:|
{rows}

## 💻 Solutions & projects

Code I write for Boot.dev courses and guided projects lives in [`solutions/`](solutions/), one folder per course.

<sub>Last updated {dt.datetime.now(IST):%Y-%m-%d %H:%M} IST · stats from the public Boot.dev API</sub>
"""


def main():
    p, s, ach = get(), get("/stats"), get("/achievements")
    unlocked = [a for a in ach if a.get("unlockedAt")]
    today = dt.datetime.now(IST).date().isoformat()
    row = {
        "date": today,
        "level": p["level"],
        "xp": p["xp"],
        "lessons": s["lessonsCompleted"],
        "percentile": s["leaderboardXPPercentileAlltime"],
        "achievements": len(unlocked),
    }
    history = [r for r in load_history() if r["date"] != today] + [{k: str(v) for k, v in row.items()}]
    history.sort(key=lambda r: r["date"])
    save_history(history)
    with open(os.path.join(ROOT, "card.svg"), "w", encoding="utf-8") as f:
        f.write(card(p, s, unlocked))
    with open(os.path.join(ROOT, "README.md"), "w", encoding="utf-8") as f:
        f.write(readme(p, s, unlocked, history))
    print(f"Level {p['level']} · {p['xp']} XP · {s['lessonsCompleted']} lessons · {len(unlocked)} achievements")


if __name__ == "__main__":
    main()
