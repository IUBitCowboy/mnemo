#!/usr/bin/env python3
"""Convert mermaid-cli SVG to Keynote-safe SVG: foreignObject labels -> <text>.

Keynote does not support foreignObject; mermaid-cli emits node labels as
foreignObject HTML even with flowchart.htmlLabels=false (v11 quirk).
mmdc positions each foreignObject via ancestor <g transform="translate(...)">
— the FO itself carries only width/height. This walks the real XML tree,
accumulates ancestor translations, extracts each FO's text, and swaps in a
plain <text> element centered on the FO box.

Usage: python3 fo_to_text.py <in.svg> <out.svg> [fill] [font_size]
Defaults: fill=#FFFFFF font_size=16
"""
import re
import sys
import xml.etree.ElementTree as ET

SVG_NS = "http://www.w3.org/2000/svg"


def register_namespaces(raw: str):
    """Register every xmlns prefix found in the file so ET.tostring keeps them."""
    for m in re.finditer(r'xmlns:([A-Za-z0-9_-]+)="([^"]+)"', raw):
        ET.register_namespace(m.group(1), m.group(2))
    ET.register_namespace("", SVG_NS)


def translate_of(elem):
    """Return (dx, dy) from an element's transform if it's a plain translate."""
    t = elem.get("transform")
    if not t:
        return 0.0, 0.0
    m = re.match(r"translate\(\s*([-\d.]+)[ ,]+([-\d.]+)\s*\)", t)
    if m:
        return float(m.group(1)), float(m.group(2))
    return 0.0, 0.0


def convert(in_path: str, out_path: str, fill: str, font_size: float):
    raw = open(in_path).read()
    register_namespaces(raw)
    root = ET.fromstring(raw)

    def walk_with_parents(elem, ancestors):
        for child in list(elem):
            yield child, ancestors + [elem]
            yield from walk_with_parents(child, ancestors + [elem])

    converted = 0
    dropped = 0
    for elem, ancestors in list(walk_with_parents(root, [])):
        if not elem.tag.endswith("foreignObject"):
            continue
        # cumulative offset: sum of ancestor translates
        dx = dy = 0.0
        for a in ancestors:
            ax, ay = translate_of(a)
            dx += ax
            dy += ay
        label = re.sub(r"\s+", " ", "".join(elem.itertext())).strip()
        parent = ancestors[-1]
        if not label:
            parent.remove(elem)
            dropped += 1
            continue
        w = float(elem.get("width", "0") or 0)
        h = float(elem.get("height", "0") or 0)
        fx = float(elem.get("x", "0") or 0)
        fy = float(elem.get("y", "0") or 0)
        # COORDINATE FRAME: the <text> replaces the FO inside the SAME
        # parent, so it inherits the FO's frame — ancestor translates
        # above the parent apply to it exactly as they applied to the FO.
        # Centering = FO's own x/y + half size. Do NOT add ancestor dx/dy
        # here: those transforms still apply on render, and adding them
        # double-offsets the text out of the viewBox (verified bug on the
        # wk08 slide-4 diagram: server label rendered at x=761, viewBox
        # ends at 494 -> invisible).
        cx = fx + w / 2.0
        cy = fy + h / 2.0

        # WRAP SPLIT: a single centered line wider than the node box
        # overflows it (and can leave the viewBox). Mermaid's original
        # foreignObject wrapped; flatten-to-one-line loses that. If the
        # estimated line width exceeds the box, split at a space —
        # preferring one OUTSIDE parentheses so a parenthetical phrase
        # stays intact (e.g. "Server" / "(your Flask app)", never
        # "Server (your" / "Flask app)").
        # FIT BASIS: the FO width is mermaid's padded label area, not the
        # visible box — node rects are the FO + 16px padding each side.
        # Text may legitimately use that padding (mermaid's own wrapped
        # labels do), so fit checks use effective_w = w + 32.
        eff_w = w + 32.0
        est = len(label) * font_size * 0.55
        halves = None
        if est > eff_w and " " in label:
            mid = len(label) // 2
            depth = 0
            spaces = {}
            for i, ch in enumerate(label):
                if ch == "(":
                    depth += 1
                elif ch == ")":
                    depth = max(0, depth - 1)
                elif ch == " " and i not in spaces:
                    spaces[i] = depth
            outside = [i for i, d in spaces.items() if d == 0]
            pool = outside if outside else list(spaces)

            def cost(i):
                return abs(i - mid) + (100 if i in spaces and spaces[i] > 0 else 0)

            best = min(pool, key=cost)
            a, b = label[:best].strip(), label[best:].strip()
            if a and b and len(a) * font_size * 0.55 <= eff_w and len(b) * font_size * 0.55 <= eff_w:
                halves = (a, b)

        def emit(x, y, txt):
            t = ET.SubElement(parent, f"{{{SVG_NS}}}text")
            t.set("x", f"{x:.1f}")
            t.set("y", f"{y:.1f}")
            t.set("text-anchor", "middle")
            t.set("dominant-baseline", "central")
            t.set("font-family", "Helvetica, Arial, sans-serif")
            t.set("font-size", str(font_size))
            t.set("fill", fill)
            t.text = txt
            return t

        if halves:
            emit(cx, fy + h / 3.0, halves[0])
            emit(cx, fy + 2.0 * h / 3.0, halves[1])
            converted += 1
        else:
            emit(cx, cy, label)
            converted += 1
        parent.remove(elem)

    out = ET.tostring(root, encoding="unicode")
    open(out_path, "w").write(out)
    fo_left = len(re.findall(r"foreignObject", out))
    texts = re.findall(r"<text[^>]*>([^<]*)<", out)
    print(f"{out_path}: converted {converted}, dropped {dropped} empty, "
          f"foreignObject remaining: {fo_left}")
    print(f"  text nodes now: {texts}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    in_path, out_path = sys.argv[1], sys.argv[2]
    fill = sys.argv[3] if len(sys.argv) > 3 else "#FFFFFF"
    size = float(sys.argv[4]) if len(sys.argv) > 4 else 16.0
    convert(in_path, out_path, fill, size)