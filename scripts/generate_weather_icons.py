#!/usr/bin/env python3
"""
Generate 52x52 1-bit monochrome weather condition icons for Badger 2350 / Badger 2040.

Generates PNG icons for all WMO weather codes used in pc_sender.py:
  0:  Clear sky
  1:  Mainly clear
  2:  Partly cloudy
  3:  Overcast
  45: Foggy
  48: Rime fog
  51: Light drizzle
  53: Drizzle
  55: Dense drizzle
  61: Light rain
  63: Rain
  65: Heavy rain
  71: Light snow
  73: Snow
  75: Heavy snow
  77: Snow grains
  80: Rain showers
  81: Mod. showers
  82: Heavy showers
  85: Snow showers
  86: Heavy snow shw
  95: Thunderstorm
  default: Default weather icon (sun behind cloud)

The icons are 52x52 1-bit grayscale PNGs (0 = black, 1 = white), matching
the BadgerOS icon dimensions and format decoded by pngdec on MicroPython.
"""

import argparse
import math
from pathlib import Path
import struct
import zlib


class Bitmap:
    """A 1-bit 2D monochrome canvas (0 = black foreground, 1 = white background)."""

    def __init__(self, width=52, height=52):
        self.w = width
        self.h = height
        self.pixels = [[1] * width for _ in range(height)]

    def set(self, x, y, col=0):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.pixels[y][x] = col

    def fill_rect(self, x, y, w, h, col=0):
        for cy in range(y, y + h):
            for cx in range(x, x + w):
                self.set(cx, cy, col)

    def line(self, x0, y0, x1, y1, width=1, col=0):
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        x, y = x0, y0
        r = (width - 1) / 2.0
        while True:
            for wy in range(int(math.floor(-r)), int(math.ceil(r)) + 1):
                for wx in range(int(math.floor(-r)), int(math.ceil(r)) + 1):
                    if math.hypot(wx, wy) <= r + 0.5:
                        self.set(x + wx, y + wy, col)
            if x == x1 and y == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x += sx
            if e2 < dx:
                err += dx
                y += sy

    def circle(self, cx, cy, r, width=1, fill=False, col=0):
        for y in range(max(0, int(cy - r - width - 1)), min(self.h, int(cy + r + width + 2))):
            for x in range(max(0, int(cx - r - width - 1)), min(self.w, int(cx + r + width + 2))):
                d = math.hypot(x - cx, y - cy)
                if fill:
                    if d <= r + 0.5:
                        self.set(x, y, col)
                else:
                    if abs(d - r) <= (width / 2.0):
                        self.set(x, y, col)

    def fill_poly(self, pts, col=0):
        min_y = max(0, min(p[1] for p in pts))
        max_y = min(self.h - 1, max(p[1] for p in pts))
        for y in range(min_y, max_y + 1):
            nodes = []
            j = len(pts) - 1
            for i in range(len(pts)):
                p1, p2 = pts[i], pts[j]
                if (p1[1] < y <= p2[1]) or (p2[1] < y <= p1[1]):
                    x = int(p1[0] + (y - p1[1]) / (p2[1] - p1[1]) * (p2[0] - p1[0]))
                    nodes.append(x)
                j = i
            nodes.sort()
            for k in range(0, len(nodes), 2):
                if k + 1 < len(nodes):
                    for x in range(nodes[k], nodes[k + 1] + 1):
                        self.set(x, y, col)

    def to_png(self) -> bytes:
        raw = bytearray()
        for y in range(self.h):
            raw.append(0)  # Filter byte: None
            byte = 0
            bit_count = 0
            for x in range(self.w):
                bit = 1 if self.pixels[y][x] else 0
                byte = (byte << 1) | bit
                bit_count += 1
                if bit_count == 8:
                    raw.append(byte)
                    byte = 0
                    bit_count = 0
            if bit_count > 0:
                byte <<= (8 - bit_count)
                raw.append(byte)

        compressed = zlib.compress(bytes(raw), 9)
        png = bytearray(b"\x89PNG\r\n\x1a\n")

        # IHDR chunk
        ihdr = struct.pack(">IIBBBBB", self.w, self.h, 1, 0, 0, 0, 0)
        png.extend(struct.pack(">I4s", len(ihdr), b"IHDR"))
        png.extend(ihdr)
        png.extend(struct.pack(">I", zlib.crc32(b"IHDR" + ihdr)))

        # IDAT chunk
        png.extend(struct.pack(">I4s", len(compressed), b"IDAT"))
        png.extend(compressed)
        png.extend(struct.pack(">I", zlib.crc32(b"IDAT" + compressed)))

        # IEND chunk
        png.extend(struct.pack(">I4s", 0, b"IEND"))
        png.extend(struct.pack(">I", zlib.crc32(b"IEND")))

        return bytes(png)


# ---------------------------------------------------------------------------
# Shape primitives
# ---------------------------------------------------------------------------

def draw_sun(bm: Bitmap, cx=26, cy=26, r=10, ray_len=5, ray_dist=3, width=2, angles=None):
    """Draw a round sun with radiating rays."""
    bm.circle(cx, cy, r, width=width, fill=False, col=0)
    if angles is None:
        angles = [i * 45 for i in range(8)]
    for deg in angles:
        rad = math.radians(deg)
        x0 = int(cx + (r + ray_dist) * math.cos(rad))
        y0 = int(cy + (r + ray_dist) * math.sin(rad))
        x1 = int(cx + (r + ray_dist + ray_len) * math.cos(rad))
        y1 = int(cy + (r + ray_dist + ray_len) * math.sin(rad))
        bm.line(x0, y0, x1, y1, width=width, col=0)


def draw_cloud(bm: Bitmap, ox=0, oy=0, r_scale=1.0, fill_white=True):
    """Draw a fluffy cloud with a 2-pixel outline and clean white interior."""
    circles = [
        (16 + ox, 26 + oy, 7 * r_scale),
        (24 + ox, 18 + oy, 9 * r_scale),
        (33 + ox, 21 + oy, 7 * r_scale),
        (38 + ox, 27 + oy, 5 * r_scale),
    ]
    bx0 = int(14 + ox)
    bx1 = int(38 + ox)
    by0 = int(24 + oy)
    by1 = int(32 + oy)

    def inside(x, y):
        if bx0 <= x <= bx1 and by0 <= y <= by1:
            return True
        for cx, cy, r in circles:
            if math.hypot(x - cx, y - cy) <= r:
                return True
        return False

    for y in range(bm.h):
        for x in range(bm.w):
            if inside(x, y):
                is_edge = False
                for dy in range(-2, 3):
                    for dx in range(-2, 3):
                        if dx * dx + dy * dy <= 4:
                            if not inside(x + dx, y + dy):
                                is_edge = True
                                break
                    if is_edge:
                        break
                if is_edge:
                    bm.set(x, y, 0)
                elif fill_white:
                    bm.set(x, y, 1)


def draw_raindrop(bm: Bitmap, x, y, length=6, width=2):
    """Draw a diagonal rain streak."""
    bm.line(x, y, x - 2, y + length, width=width, col=0)


def draw_snowflake(bm: Bitmap, cx, cy, size=3):
    """Draw a crisp asterisk-style snowflake."""
    bm.line(cx - size, cy, cx + size, cy, width=1, col=0)
    bm.line(cx, cy - size, cx, cy + size, width=1, col=0)
    bm.line(cx - size + 1, cy - size + 1, cx + size - 1, cy + size - 1, width=1, col=0)
    bm.line(cx - size + 1, cy + size - 1, cx + size - 1, cy - size + 1, width=1, col=0)


def draw_snow_grain(bm: Bitmap, cx, cy, size=1):
    """Draw a compact snow grain pellet."""
    for dy in range(-size, size + 1):
        for dx in range(-size, size + 1):
            if abs(dx) + abs(dy) <= size + 1:
                bm.set(cx + dx, cy + dy, 0)


def draw_drizzle_dot(bm: Bitmap, cx, cy):
    """Draw a small 2x2 drizzle drop."""
    bm.set(cx, cy, 0)
    bm.set(cx + 1, cy, 0)
    bm.set(cx, cy + 1, 0)
    bm.set(cx + 1, cy + 1, 0)


def draw_lightning(bm: Bitmap, cx=25, cy=25):
    """Draw a bold zigzag lightning bolt."""
    pts = [
        (cx + 3, cy),
        (cx - 5, cy + 11),
        (cx + 1, cy + 11),
        (cx - 6, cy + 24),
        (cx + 5, cy + 10),
        (cx - 1, cy + 10),
        (cx + 5, cy),
    ]
    bm.fill_poly(pts, col=0)


def draw_fog_line(bm: Bitmap, y, x0=10, x1=42, width=2):
    """Draw a horizontal fog bar."""
    bm.line(x0, y, x1, y, width=width, col=0)


# ---------------------------------------------------------------------------
# Icon generators for each WMO code
# ---------------------------------------------------------------------------

def gen_icon_0():
    """Code 0: Clear sky (full sun with rays)."""
    bm = Bitmap()
    draw_sun(bm, cx=26, cy=26, r=10, ray_len=5, ray_dist=3, width=2)
    return bm


def gen_icon_1():
    """Code 1: Mainly clear (sun with small cloud)."""
    bm = Bitmap()
    draw_sun(bm, cx=23, cy=22, r=9, ray_len=5, ray_dist=3, width=2)
    draw_cloud(bm, ox=10, oy=11, r_scale=0.68)
    return bm


def gen_icon_2():
    """Code 2: Partly cloudy (sun behind prominent cloud)."""
    bm = Bitmap()
    draw_sun(bm, cx=35, cy=17, r=8, ray_len=5, ray_dist=3, angles=[-135, -90, -45, 0, 45])
    draw_cloud(bm, ox=-2, oy=5)
    return bm


def gen_icon_3():
    """Code 3: Overcast (dense cloud cover)."""
    bm = Bitmap()
    # Background cloud puff
    draw_cloud(bm, ox=6, oy=-2, r_scale=0.88, fill_white=False)
    # Foreground cloud
    draw_cloud(bm, ox=-2, oy=6, fill_white=True)
    return bm


def gen_icon_45():
    """Code 45: Foggy (cloud above 3 horizontal fog lines)."""
    bm = Bitmap()
    draw_cloud(bm, ox=0, oy=-7)
    draw_fog_line(bm, y=34, x0=12, x1=40, width=2)
    draw_fog_line(bm, y=40, x0=8, x1=44, width=2)
    draw_fog_line(bm, y=46, x0=14, x1=38, width=2)
    return bm


def gen_icon_48():
    """Code 48: Rime fog (fog lines with frost crystals)."""
    bm = Bitmap()
    draw_cloud(bm, ox=0, oy=-7)
    draw_fog_line(bm, y=34, x0=10, x1=42, width=2)
    draw_fog_line(bm, y=44, x0=10, x1=42, width=2)
    draw_snowflake(bm, cx=17, cy=39, size=2)
    draw_snowflake(bm, cx=35, cy=39, size=2)
    return bm


def gen_icon_51():
    """Code 51: Light drizzle."""
    bm = Bitmap()
    draw_cloud(bm, ox=0, oy=-4)
    draw_drizzle_dot(bm, 21, 38)
    draw_drizzle_dot(bm, 31, 41)
    return bm


def gen_icon_53():
    """Code 53: Drizzle."""
    bm = Bitmap()
    draw_cloud(bm, ox=0, oy=-4)
    draw_drizzle_dot(bm, 17, 37)
    draw_drizzle_dot(bm, 24, 43)
    draw_drizzle_dot(bm, 31, 38)
    draw_drizzle_dot(bm, 38, 44)
    return bm


def gen_icon_55():
    """Code 55: Dense drizzle."""
    bm = Bitmap()
    draw_cloud(bm, ox=0, oy=-4)
    for cx, cy in [(16, 36), (24, 37), (32, 36), (40, 37), (20, 43), (28, 44), (36, 43)]:
        draw_drizzle_dot(bm, cx, cy)
    return bm


def gen_icon_61():
    """Code 61: Light rain."""
    bm = Bitmap()
    draw_cloud(bm, ox=0, oy=-4)
    draw_raindrop(bm, 22, 35, length=6)
    draw_raindrop(bm, 32, 35, length=6)
    return bm


def gen_icon_63():
    """Code 63: Rain."""
    bm = Bitmap()
    draw_cloud(bm, ox=0, oy=-4)
    draw_raindrop(bm, 18, 35, length=7)
    draw_raindrop(bm, 27, 35, length=7)
    draw_raindrop(bm, 36, 35, length=7)
    return bm


def gen_icon_65():
    """Code 65: Heavy rain."""
    bm = Bitmap()
    draw_cloud(bm, ox=0, oy=-5)
    draw_raindrop(bm, 16, 34, length=8)
    draw_raindrop(bm, 25, 34, length=8)
    draw_raindrop(bm, 34, 34, length=8)
    draw_raindrop(bm, 21, 42, length=7)
    draw_raindrop(bm, 30, 42, length=7)
    return bm


def gen_icon_71():
    """Code 71: Light snow."""
    bm = Bitmap()
    draw_cloud(bm, ox=0, oy=-4)
    draw_snowflake(bm, cx=21, cy=38, size=3)
    draw_snowflake(bm, cx=33, cy=42, size=3)
    return bm


def gen_icon_73():
    """Code 73: Snow."""
    bm = Bitmap()
    draw_cloud(bm, ox=0, oy=-4)
    draw_snowflake(bm, cx=17, cy=39, size=3)
    draw_snowflake(bm, cx=27, cy=42, size=3)
    draw_snowflake(bm, cx=37, cy=38, size=3)
    return bm


def gen_icon_75():
    """Code 75: Heavy snow."""
    bm = Bitmap()
    draw_cloud(bm, ox=0, oy=-5)
    draw_snowflake(bm, cx=17, cy=35, size=3)
    draw_snowflake(bm, cx=27, cy=35, size=3)
    draw_snowflake(bm, cx=37, cy=35, size=3)
    draw_snowflake(bm, cx=22, cy=43, size=3)
    draw_snowflake(bm, cx=32, cy=43, size=3)
    return bm


def gen_icon_77():
    """Code 77: Snow grains."""
    bm = Bitmap()
    draw_cloud(bm, ox=0, oy=-4)
    draw_snow_grain(bm, cx=17, cy=37)
    draw_snow_grain(bm, cx=24, cy=43)
    draw_snow_grain(bm, cx=31, cy=38)
    draw_snow_grain(bm, cx=38, cy=44)
    return bm


def gen_icon_80():
    """Code 80: Rain showers (sun + cloud + rain drops)."""
    bm = Bitmap()
    draw_sun(bm, cx=35, cy=17, r=8, ray_len=5, ray_dist=3, angles=[-135, -90, -45, 0, 45])
    draw_cloud(bm, ox=-2, oy=4)
    draw_raindrop(bm, 20, 40, length=6)
    draw_raindrop(bm, 30, 40, length=6)
    return bm


def gen_icon_81():
    """Code 81: Moderate showers."""
    bm = Bitmap()
    draw_sun(bm, cx=35, cy=17, r=8, ray_len=5, ray_dist=3, angles=[-135, -90, -45, 0, 45])
    draw_cloud(bm, ox=-2, oy=4)
    draw_raindrop(bm, 16, 40, length=7)
    draw_raindrop(bm, 25, 40, length=7)
    draw_raindrop(bm, 34, 40, length=7)
    return bm


def gen_icon_82():
    """Code 82: Heavy showers."""
    bm = Bitmap()
    draw_cloud(bm, ox=0, oy=-5)
    draw_raindrop(bm, 15, 34, length=9)
    draw_raindrop(bm, 23, 34, length=9)
    draw_raindrop(bm, 31, 34, length=9)
    draw_raindrop(bm, 39, 34, length=9)
    draw_raindrop(bm, 19, 42, length=8)
    draw_raindrop(bm, 27, 42, length=8)
    draw_raindrop(bm, 35, 42, length=8)
    return bm


def gen_icon_85():
    """Code 85: Snow showers (sun + cloud + snowflakes)."""
    bm = Bitmap()
    draw_sun(bm, cx=35, cy=17, r=8, ray_len=5, ray_dist=3, angles=[-135, -90, -45, 0, 45])
    draw_cloud(bm, ox=-2, oy=4)
    draw_snowflake(bm, cx=20, cy=41, size=3)
    draw_snowflake(bm, cx=32, cy=41, size=3)
    return bm


def gen_icon_86():
    """Code 86: Heavy snow showers."""
    bm = Bitmap()
    draw_cloud(bm, ox=0, oy=-5)
    draw_snowflake(bm, cx=16, cy=36, size=3)
    draw_snowflake(bm, cx=27, cy=35, size=3)
    draw_snowflake(bm, cx=38, cy=36, size=3)
    draw_snowflake(bm, cx=22, cy=44, size=3)
    draw_snowflake(bm, cx=33, cy=44, size=3)
    return bm


def gen_icon_95():
    """Code 95: Thunderstorm (cloud + lightning bolt + rain drop)."""
    bm = Bitmap()
    draw_cloud(bm, ox=0, oy=-6)
    draw_lightning(bm, cx=25, cy=25)
    draw_raindrop(bm, 38, 36, length=6)
    return bm


GENERATORS = {
    0: gen_icon_0,
    1: gen_icon_1,
    2: gen_icon_2,
    3: gen_icon_3,
    45: gen_icon_45,
    48: gen_icon_48,
    51: gen_icon_51,
    53: gen_icon_53,
    55: gen_icon_55,
    61: gen_icon_61,
    63: gen_icon_63,
    65: gen_icon_65,
    71: gen_icon_71,
    73: gen_icon_73,
    75: gen_icon_75,
    77: gen_icon_77,
    80: gen_icon_80,
    81: gen_icon_81,
    82: gen_icon_82,
    85: gen_icon_85,
    86: gen_icon_86,
    95: gen_icon_95,
}


def generate_all(output_dir: Path):
    """Generate all icons into the target directory."""
    output_dir.mkdir(parents=True, exist_ok=True)
    count = 0

    for code, generator in sorted(GENERATORS.items()):
        bm = generator()
        png_data = bm.to_png()
        target = output_dir / f"{code}.png"
        target.write_bytes(png_data)
        count += 1

    # Default fallback icon (partly cloudy)
    default_bm = gen_icon_2()
    (output_dir / "default.png").write_bytes(default_bm.to_png())
    count += 1

    print(f"Generated {count} icons in {output_dir}")


def main():
    parser = argparse.ArgumentParser(description="Generate 52x52 weather icons for Badger 2350")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "preload" / "examples" / "weather_icons",
        help="Target folder for icons",
    )
    args = parser.parse_args()
    generate_all(args.out_dir)


if __name__ == "__main__":
    main()
