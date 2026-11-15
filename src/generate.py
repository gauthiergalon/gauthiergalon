#!/usr/bin/env python3
"""Generate the animated SVGs shown in README.md.

    python3 src/generate.py             # writes assets/
    python3 src/generate.py --at 3      # fast-forward every animation by 3s (handy for screenshots)

Standard library only. Edit the data below, re-run, commit assets/.

Every image exists in a light and a dark variant; README.md picks one with <picture>,
which GitHub maps to the visitor's theme. Backgrounds are transparent.

GitHub shows these through <img>, so everything has to live inside each file:
no scripts, no external fonts or images, only CSS animations. Text is drawn from
glyph outlines (src/fonts/*.json, see extract_glyphs.py) instead of fonts.
"""

import argparse
import json
import os
import re
from datetime import date
from html import escape
from pathlib import Path

SRC = Path(__file__).resolve().parent

# ── content ──────────────────────────────────────────────────────────────────

NAME = "gauthier"


def age(today=None):
    """Age today. The birth date stays out of the repository: it is read from the
    BIRTHDATE environment variable or from the git-ignored file src/birthdate.txt (YYYY-MM-DD)."""
    file = SRC / "birthdate.txt"
    raw = os.environ.get("BIRTHDATE") or (file.read_text().strip() if file.exists() else "")
    if not raw:
        raise SystemExit("birth date missing: set BIRTHDATE=YYYY-MM-DD or write it to src/birthdate.txt")
    birth, today = date.fromisoformat(raw), today or date.today()
    return today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))


META = [f"french, {age()}yo", "studying @ 42paris"]

# Brand colours for the icons. False draws every icon in the text colour instead.
ICON_COLOURS = True

# Each entry is (label, icon file in src/icons, colour, colour on dark if it differs);
# a colour of None means "the accent blue", for icons that have no brand colour of their own.
# A category is drawn on two columns; inside a column, each inner list is a group of
# related entries, and groups are set apart by a little space.
SKILLS = [
    ("languages", [
        [[("c", "c", "#6e86a6", "#a8b9cc"), ("c++", "cplusplus", "#00599c", "#659ad2"), ("rust", "rust", "#f75708")],
         [("c#", "csharp", "#512bd4", "#9478f0"), ("python", "python", "#3776ab", "#5a9fd4"), ("php", "php", "#777bb4")]],
        [[("html", "html5", "#e34f26"), ("css", "css3", "#1572b6", "#3a9be0"),
          ("js", "javascript", "#e6c700", "#f7df1e"), ("ts", "typescript", "#3178c6", "#4f97e6")],
         [("sql", "sql", None), ("nosql", "nosql", None)]],
    ]),
    ("data", [
        [[("postgres", "postgresql", "#4169e1", "#6f8ff0"), ("mysql", "mysql", "#00618a", "#5aa7d0"),
          ("sql server", "microsoftsqlserver", "#cc2927", "#e8504e")],
         [("mongodb", "mongodb", "#47a248")],
         [("snowflake", "snowflake", "#29b5e8")]],
        [[("airbyte", "airbyte", "#615eff", "#8b89ff"), ("dbt", "dbt", "#ff694b"), ("kestra", "kestra", "#a950ff")],
         [("openmetadata", "openmetadata", "#8d6af1")]],
    ]),
    ("ops", [
        [[("git", "git", "#f05032"), ("github actions", "github", None)],
         [("azure", "microsoftazure", "#0078d4", "#3a9bf0")]],
        [[("docker", "docker", "#2496ed"), ("k8s", "kubernetes", "#326ce5", "#5b8ff0")],
         [("grafana", "grafana", "#f46800")]],
    ]),
    ("ai", [
        [[("claude code", "claudecode", "#d97757"), ("mcp", "mcp", None)],
         [("machine learning", "ml", None)]],
        [[("custom skills", "skill", None), ("custom plugins", "plugin", None)],
         [("rag", "rag", None)]],
    ]),
]

LINKS = ["LinkedIn", "Mail"]      # -> assets/links/<name>-<theme>.svg, URLs live in README.md

# The accent is #2a55a9; on GitHub's dark background that blue is too dim for small text,
# so the dark variant uses a lighter tint of the same hue.
THEMES = {
    "light": {"fg": "#0a0a0a", "accent": "#2a55a9", "glow": 0.2},
    "dark": {"fg": "#f0f3f6", "accent": "#6390e3", "glow": 0.26},
}

# Soft circles of the accent blue drifting slowly behind the content. False removes them.
HALOS = True

# ── layout ───────────────────────────────────────────────────────────────────

W = 640                 # viewBox width; the README shows it at this width, not stretched
COL = W / len(SKILLS)   # one grid column per skill category; the links sit on the same grid
TEXT = 14               # small text size (header)
SKILL = 16              # text size in the skills block
RULE = 3                # thickness of every rule, in the header and around the skills
LEAD = 20               # small text line height
SHIFT = 0.0             # set by --at


def num(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


def at(t):
    """Animation delay for something that should happen `t` seconds in."""
    return f"{num(t - SHIFT)}s"


def icon(name):
    """Path attributes of a 24×24 icon from src/icons.

    A few need the even-odd fill rule; a thin logo can ask to be thickened with a stroke-width.
    """
    svg = (SRC / "icons" / f"{name}.svg").read_text()
    attrs = 'd="' + re.search(r'\sd="([^"]+)"', svg).group(1) + '"'
    if 'fill-rule="evenodd"' in svg:
        attrs += ' fill-rule="evenodd"'
    bold = re.search(r'stroke-width="([^"]+)"', svg)
    if bold:
        attrs += f' stroke-width="{bold.group(1)}" stroke-linejoin="round"'
    return attrs


class Font:
    def __init__(self, key, file):
        data = json.loads((SRC / "fonts" / file).read_text())
        self.key, self.upm, self.glyphs = key, data["unitsPerEm"], data["glyphs"]

    def width(self, s, size, tracking=0):
        return sum(self.glyphs[c][0] for c in s) * size / self.upm + tracking * (len(s) - 1)

    def left(self, ch, size):
        """Blank space on the left of a glyph, so big text can sit flush with the grid."""
        xs, x = [], 0.0
        for cmd, args in re.findall(r"([MLHVQCZ])([^MLHVQCZ]*)", self.glyphs[ch][1]):
            v = [float(n) for n in args.split()]
            if cmd == "H":
                xs += v
            elif cmd != "V":
                xs += v[0::2]
        return min(xs) * size / self.upm


BOLD = Font("b", "inter-tight-extrabold.json")
TEXTFONT = Font("m", "inter-tight-medium.json")

CSS = """
.g{transform:scaleX(0);animation:n .9s cubic-bezier(.7,0,.2,1) forwards}.l{transform:translateY(124px);animation:n .9s cubic-bezier(.2,.8,.2,1) forwards}
.f{opacity:0;animation:f .7s cubic-bezier(.2,.8,.2,1) forwards}
.q{transform-box:fill-box;transform-origin:center;transform:scale(0);animation:n .5s cubic-bezier(.3,1.5,.5,1) forwards,q 6s cubic-bezier(.7,0,.3,1) infinite}
.a{animation:a 6s ease-in-out infinite}
.h{animation:h ease-in-out infinite alternate}
.z{transform-box:fill-box;transform-origin:center;animation:z ease-in-out infinite alternate}
@keyframes n{to{transform:none}}
@keyframes f{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
@keyframes q{0%,82%{transform:rotate(0)}to{transform:rotate(90deg)}}
@keyframes h{from{transform:translate(calc(var(--dx)*-1),calc(var(--dy)*-1))}to{transform:translate(var(--dx),var(--dy))}}
@keyframes z{from{transform:scale(.86)}to{transform:scale(1.16)}}
@keyframes a{0%,84%,to{transform:none}92%{transform:translate(3px,-3px)}}
@media (prefers-reduced-motion:reduce){*{animation:none!important}.g,.l,.q{transform:none}.f{opacity:1}}
"""


class Sheet:
    """One SVG file. Collects the glyph outlines it uses so each is defined once."""

    def __init__(self):
        self.glyphs = {}

    def glyph(self, font, ch):
        gid = f"{font.key}{ord(ch):x}"
        self.glyphs[gid] = font.glyphs[ch][1]
        return gid

    def text(self, s, x, y, font, size, fill, tracking=0):
        k = size / font.upm
        out, cx = "", 0
        for ch in s:
            adv, d = font.glyphs[ch]
            if d:
                out += f'<use href="#{self.glyph(font, ch)}" x="{num(cx)}"/>'
            cx += adv + tracking / k
        return f'<g transform="translate({num(x)} {num(y)}) scale({k:.5f} -{k:.5f})" fill="{fill}">{out}</g>'

    def render(self, w, h, label, body, defs=""):
        glyphs = "".join(f'<path id="{gid}" d="{d}"/>' for gid, d in sorted(self.glyphs.items()))
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{num(w)}" height="{num(h)}" '
                f'viewBox="0 0 {num(w)} {num(h)}" role="img" aria-label="{escape(label)}">\n'
                f"<title>{escape(label)}</title>\n<style>{CSS}</style>\n<defs>{glyphs}{defs}</defs>\n{body}\n</svg>\n")


def halos(theme, spots):
    """(defs, svg) for halos given as (cx, cy, radius, drift x, drift y, drift seconds, breathing seconds).

    Each is a circle of the accent colour that fades to nothing at its edge, so nothing is
    cut off where the image ends. It drifts back and forth and slowly swells and shrinks;
    the two rhythms differ, so the motion never looks like a loop.
    """
    if not HALOS:
        return "", ""
    colour, peak = THEMES[theme]["accent"], THEMES[theme]["glow"]
    defs = (f'<radialGradient id="halo"><stop offset="0" stop-color="{colour}" stop-opacity="{peak}"/>'
            f'<stop offset="1" stop-color="{colour}" stop-opacity="0"/></radialGradient>')
    body = ""
    for i, (cx, cy, r, dx, dy, drift, breathe) in enumerate(spots):
        body += (f'<g class="h" style="--dx:{dx}px;--dy:{dy}px;animation-duration:{drift}s;animation-delay:{at(-4 * i)}">'
                 f'<circle class="z" cx="{num(cx)}" cy="{num(cy)}" r="{num(r)}" fill="url(#halo)" '
                 f'style="animation-duration:{breathe}s;animation-delay:{at(-3 * i)}"/></g>')
    return defs, f'<g class="f" style="animation-duration:2.5s;animation-delay:{at(0.2)}">{body}</g>'


def rule(y, height, fill, t):
    """A full-width line that draws itself from the left at time t."""
    return f'<rect class="g" y="{num(y)}" width="{W}" height="{num(height)}" fill="{fill}" style="animation-delay:{at(t)}"/>'


def fade(content, t):
    return f'<g class="f" style="animation-delay:{at(t)}">{content}</g>'


# ── header-<theme>.svg ───────────────────────────────────────────────────────

def header(theme):
    fg, accent = THEMES[theme]["fg"], THEMES[theme]["accent"]
    sheet = Sheet()
    out = rule(0, RULE, fg, 0.1)

    # name: letters rise one by one from behind a mask, flush with the left edge
    size, base = 104, 100
    k, tracking = size / BOLD.upm, -0.03 * size
    x = -BOLD.left(NAME[0], size)
    letters = ""
    for i, ch in enumerate(NAME):
        letters += (f'<g transform="translate({num(x)} {base})"><g class="l" style="animation-delay:{at(0.35 + i * 0.05)}">'
                    f'<use href="#{sheet.glyph(BOLD, ch)}" transform="scale({k:.5f} -{k:.5f})" fill="{fg}"/></g></g>')
        x += BOLD.glyphs[ch][0] * k + tracking
    out += f'<g clip-path="url(#name)">{letters}</g>'
    # the one accent: a square that pops in after the name, then turns now and then
    out += (f'<rect class="q" x="{num(x + tracking + 14)}" y="{base - 17}" width="17" height="17" fill="{accent}" '
            f'style="animation-delay:{at(1.1)},{at(4)}"/>')

    # meta block, flush with the right edge, bottom line sharing the name's baseline
    meta_x = W - max(TEXTFONT.width(line, TEXT) for line in META)
    for i, line in enumerate(META):
        y = base - (len(META) - 1 - i) * LEAD
        out += fade(sheet.text(line, meta_x, y, TEXTFONT, TEXT, fg), 1.0 + i * 0.08)

    drop = 28                               # room under the baseline for descenders
    glow_defs, glow = halos(theme, [(W - 140, (base + drop) / 2 + 2, 58, 70, 0, 15, 7)])
    out = glow + out
    defs = glow_defs + f'<clipPath id="name"><rect y="{base - 92}" width="{W}" height="{92 + drop}"/></clipPath>'
    return sheet.render(W, base + drop, f"{NAME} — {', '.join(META)}", out, defs)


# ── skills-<theme>.svg ───────────────────────────────────────────────────────

def skills(theme):
    fg, accent = THEMES[theme]["fg"], THEMES[theme]["accent"]
    sheet = Sheet()
    row, first, ico, gap = 26, 88, 17, 12   # row height, first item baseline, icon size, space between groups
    cell, half = W / 2, W / 4               # categories sit two by two, each on two columns
    out, top = rule(0, RULE, fg, 0.2), 0

    for i in range(0, len(SKILLS), 2):
        depth = 0
        for c, (title, columns) in enumerate(SKILLS[i:i + 2]):
            x = c * cell
            block = sheet.text(f"{i + c + 1:02d}", x, top + 30, BOLD, SKILL, accent)
            block += sheet.text(title, x, top + 52, BOLD, SKILL, fg)
            for k, groups in enumerate(columns):
                ix, y = x + k * half, top + first
                for n, group in enumerate(groups):
                    y += gap if n else 0
                    for label, file, *colours in group:
                        colour = (colours[-1] if theme == "dark" else colours[0]) if ICON_COLOURS else None
                        shape, paint = icon(file), colour or accent
                        stroke = f' stroke="{paint}"' if "stroke-width" in shape else ""
                        block += (f'<path transform="translate({num(ix)} {num(y - 0.364 * SKILL - ico / 2)}) scale({ico / 24})" '
                                  f'fill="{paint}"{stroke} {shape}/>')
                        block += sheet.text(label, ix + ico + 9, y, TEXTFONT, SKILL, fg)
                        y += row
                depth = max(depth, y - row - top)
            out += fade(block, 0.5 + (i + c) * 0.09)
        top += depth + 20

    out += rule(top, RULE, fg, 0.9)
    label = " ".join(f"{title}: {', '.join(e[0] for groups in columns for group in groups for e in group)}."
                     for title, columns in SKILLS)
    h = top + RULE
    glow_defs, glow = halos(theme, [(180, 0.32 * h, 150, 60, 40, 19, 8),
                                    (450, 0.68 * h, 125, -70, -36, 23, 11)])
    return sheet.render(W, h, label, glow + out, glow_defs)


# ── links/<name>-<theme>.svg ─────────────────────────────────────────────────

def link(label, theme, index):
    fg, accent = THEMES[theme]["fg"], THEMES[theme]["accent"]
    sheet, size, h, base = Sheet(), 20, 36, 25
    tracking = -0.02 * size
    arrow_x = BOLD.width(label, size, tracking) + 7
    body = fade(sheet.text(label, 0, base, BOLD, size, fg, tracking)
                + f'<g transform="translate({num(arrow_x)} {base - 14})"><path class="a" style="animation-delay:{at(3 + index * 0.5)}" '
                  f'd="M0 12 12 0M2.5 0H12V9.5" fill="none" stroke="{accent}" stroke-width="2.6"/></g>',
                1.1 + index * 0.09)
    return sheet.render(COL, h, label, body)


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    global SHIFT
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--at", type=float, default=0.0, metavar="SECONDS",
                    help="fast-forward the animations (for previews; don't commit the result)")
    ap.add_argument("--out", type=Path, default=SRC.parent / "assets")
    args = ap.parse_args()
    SHIFT = args.at

    files = {}
    for theme in THEMES:
        files[f"header-{theme}.svg"] = header(theme)
        files[f"skills-{theme}.svg"] = skills(theme)
        for i, label in enumerate(LINKS):
            files[f"links/{label.lower()}-{theme}.svg"] = link(label, theme, i)
    for name, content in files.items():
        path = args.out / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        print(f"{path}  {len(content) / 1024:.1f} kB")


if __name__ == "__main__":
    main()
