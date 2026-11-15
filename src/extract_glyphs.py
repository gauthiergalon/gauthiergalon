#!/usr/bin/env python3
"""Turn a font into the glyph-outline JSON that generate.py draws text with.

    pip install fonttools brotli
    python3 src/extract_glyphs.py Font.woff2 src/fonts/name.json [wght]

Only needed to add or change a font: generate.py itself reads the JSON and has no dependencies.
Text is drawn as outlines so the SVGs look the same everywhere, without embedding font files.
"""

import json
import sys

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

CHARS = "".join(chr(i) for i in range(32, 127)) + "é·"

src, out = sys.argv[1], sys.argv[2]
font = TTFont(src)
if "fvar" in font and len(sys.argv) > 3:
    font = instantiateVariableFont(font, {"wght": float(sys.argv[3])})

cmap, glyph_set = font.getBestCmap(), font.getGlyphSet()
glyphs = {}
for ch in CHARS:
    name = cmap.get(ord(ch))
    if name is None:
        continue
    pen = SVGPathPen(glyph_set, ntos=lambda v: str(round(v)))
    glyph_set[name].draw(pen)
    glyphs[ch] = [round(glyph_set[name].width), pen.getCommands()]

with open(out, "w") as f:
    json.dump({"unitsPerEm": font["head"].unitsPerEm, "glyphs": glyphs}, f,
              ensure_ascii=False, separators=(",", ":"))
print(f"{out}: {len(glyphs)} glyphs")
