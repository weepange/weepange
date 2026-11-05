#!/usr/bin/env python3
"""Generate stats.svg and langs.svg for the profile README from the GitHub REST API.

Usage: gen_stats.py <username> <output_dir>
Optional env: GITHUB_TOKEN (raises rate limits, used inside GitHub Actions).
"""
import json
import os
import sys
import urllib.request
from collections import Counter
from datetime import datetime
from html import escape

API = "https://api.github.com"
FONT = "'JetBrains Mono','SFMono-Regular',Consolas,'Liberation Mono',monospace"
CARD_W, CARD_H = 470, 190


def get(path):
    req = urllib.request.Request(API + path, headers={"User-Agent": "profile-stats"})
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def collect(user):
    profile = get(f"/users/{user}")
    repos = [r for r in get(f"/users/{user}/repos?per_page=100&type=owner") if not r["fork"]]
    langs = Counter()
    for r in repos:
        try:
            langs.update(get(f"/repos/{user}/{r['name']}/languages"))
        except Exception:
            pass
    try:
        commits = get(f"/search/commits?q=author:{user}")["total_count"]
    except Exception:
        commits = 0
    try:
        prs = get(f"/search/issues?q=author:{user}+type:pr")["total_count"]
    except Exception:
        prs = 0
    return {
        "repos": profile["public_repos"],
        "followers": profile["followers"],
        "since": datetime.fromisoformat(profile["created_at"].replace("Z", "+00:00")).year,
        "stars": sum(r["stargazers_count"] for r in repos),
        "commits": commits,
        "prs": prs,
        "langs": langs,
    }


def card(inner, title):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{CARD_W}" height="{CARD_H}" viewBox="0 0 {CARD_W} {CARD_H}" role="img" aria-label="{escape(title)}">
  <defs>
    <linearGradient id="a" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#00e5ff"/>
      <stop offset="1" stop-color="#ff2bd6"/>
    </linearGradient>
  </defs>
  <rect width="{CARD_W}" height="{CARD_H}" rx="8" fill="#0d1117"/>
  <rect x="0.5" y="0.5" width="{CARD_W - 1}" height="{CARD_H - 1}" rx="8" fill="none" stroke="#30363d"/>
  <path d="M16 30V16H30" stroke="#00e5ff" stroke-width="2" fill="none"/>
  <g font-family="{FONT}">
    <text x="42" y="30" font-size="14" fill="#00e5ff">{escape(title)}</text>
{inner}
  </g>
</svg>
"""


def stats_svg(d):
    rows = [
        ("repositories", d["repos"]),
        ("stars earned", d["stars"]),
        ("commits", d["commits"]),
        ("pull requests", d["prs"]),
        ("followers", d["followers"]),
        ("on github since", d["since"]),
    ]
    out = []
    for i, (label, value) in enumerate(rows):
        y = 64 + i * 22
        out.append(f'    <text x="32" y="{y}" font-size="13" fill="#8b949e">{escape(label)}</text>')
        out.append(
            f'    <text x="{CARD_W - 32}" y="{y}" font-size="13" font-weight="700" '
            f'fill="#e6edf3" text-anchor="end">{value}</text>'
        )
    return card("\n".join(out), "weepange@github:~$ stats")


def langs_svg(d):
    total = sum(d["langs"].values()) or 1
    top = d["langs"].most_common(5)
    out = []
    bar_x, bar_w = 150, CARD_W - 150 - 80
    for i, (name, size) in enumerate(top):
        y = 64 + i * 25
        pct = size / total * 100
        fill_w = max(2, bar_w * pct / 100)
        out.append(f'    <text x="32" y="{y}" font-size="13" fill="#e6edf3">{escape(name)}</text>')
        out.append(f'    <rect x="{bar_x}" y="{y - 10}" width="{bar_w}" height="8" rx="4" fill="#161b22"/>')
        out.append(f'    <rect x="{bar_x}" y="{y - 10}" width="{fill_w:.1f}" height="8" rx="4" fill="url(#a)"/>')
        out.append(
            f'    <text x="{CARD_W - 32}" y="{y}" font-size="12" fill="#8b949e" '
            f'text-anchor="end">{pct:.1f}%</text>'
        )
    if not top:
        out.append('    <text x="32" y="70" font-size="13" fill="#8b949e">no language data yet</text>')
    return card("\n".join(out), "weepange@github:~$ top-langs")


def main():
    user, out_dir = sys.argv[1], sys.argv[2]
    data = collect(user)
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "stats.svg"), "w", encoding="utf-8") as f:
        f.write(stats_svg(data))
    with open(os.path.join(out_dir, "langs.svg"), "w", encoding="utf-8") as f:
        f.write(langs_svg(data))
    print("ok:", {k: v for k, v in data.items() if k != "langs"}, data["langs"].most_common(5))


if __name__ == "__main__":
    main()
