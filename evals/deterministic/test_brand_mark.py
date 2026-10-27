"""The brand mark ships in the shapes the UI needs, and the README offers both.

The dashboard paints the mark through a CSS mask (gogo-mark-mask.png), so its
colour comes from the page; the tab icon is a colored PNG with a transparent
ground (gogo-mark.png) plus a favicon.ico. GitHub gives an <img> no way to read
the page theme, so the README ships two PNG variants picked by <picture>.
These checks keep the files present and the references honest.

PNG/ICO headers are parsed with the stdlib only — no image dependency.
"""

import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATIC = ROOT / "gogo" / "ops" / "static"
BRAND = ROOT / "docs" / "brand"


def _png(path: Path) -> tuple[int, int, int]:
    """(width, height, colour type) from a PNG's IHDR; errors if it is not one."""
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", f"{path} is not a PNG"
    (width, height, bit_depth, color_type) = struct.unpack(">IIBB", data[16:26])
    assert bit_depth == 8, f"{path} should be 8-bit"
    return width, height, color_type


def _png_has_alpha(path: Path) -> bool:
    """Decode IDAT and report whether any pixel has alpha < 255."""
    data = path.read_bytes()
    pos, width, height, color_type = 8, 0, 0, 0
    chunks = []
    while pos < len(data):
        length = struct.unpack(">I", data[pos:pos + 4])[0]
        ctype = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + length]
        if ctype == b"IHDR":
            width, height, _, color_type = struct.unpack(">IIBB", body[:10])
        elif ctype == b"IDAT":
            chunks.append(body)
        pos += 12 + length
    raw = zlib.decompress(b"".join(chunks))
    channels = {6: 4, 2: 3, 0: 1, 4: 2}[color_type]
    stride = width * channels
    out = bytearray()
    prev = bytearray(stride)
    i = 0
    for _ in range(height):
        filt = raw[i]; i += 1
        line = bytearray(raw[i:i + stride]); i += stride
        for x in range(stride):
            a = line[x - channels] if x >= channels else 0
            b = prev[x]
            c = prev[x - channels] if x >= channels else 0
            if filt == 1:
                line[x] = (line[x] + a) & 255
            elif filt == 2:
                line[x] = (line[x] + b) & 255
            elif filt == 3:
                line[x] = (line[x] + ((a + b) // 2)) & 255
            elif filt == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pr = a if pa <= pb and pa <= pc else b if pb <= pc else c
                line[x] = (line[x] + pr) & 255
        out.extend(line)
        prev = line
    if channels == 4:
        return any(out[3 + k * 4] < 255 for k in range(width * height))
    return False


def test_the_static_mark_assets_exist():
    w, h, color_type = _png(STATIC / "gogo-mark.png")
    assert w == h, "the tab mark is square"
    assert color_type == 6, "the tab mark needs an alpha channel (RGBA)"
    assert _png_has_alpha(STATIC / "gogo-mark-mask.png"), "the mask needs transparent pixels"
    ico = (STATIC / "favicon.ico").read_bytes()
    assert ico[:4] == b"\x00\x00\x01\x00", "favicon.ico is not an ICO"


def test_the_dashboard_serves_the_mark_types():
    from gogo.ops.dashboard import STATIC_TYPES

    assert STATIC_TYPES[".png"] == "image/png"
    assert STATIC_TYPES[".ico"] == "image/x-icon"


def test_the_html_links_a_png_or_ico_icon():
    for page in ("index.html", "embed.html"):
        html = (STATIC / page).read_text()
        assert "gogo-mark.svg" not in html, f"{page} still links the removed SVG"
        assert "/static/gogo-mark.png" in html or "/static/favicon.ico" in html


def test_the_readme_offers_both_themes():
    readme = (ROOT / "README.md").read_text()
    assert 'media="(prefers-color-scheme: dark)"' in readme
    for name in ("gogo-mark-on-light.png", "gogo-mark-on-dark.png"):
        assert (BRAND / name).is_file(), f"missing {name}"
        assert f"docs/brand/{name}" in readme, f"README never references {name}"
