"""Generate the compact Vilm Lyrics Aligner icon without dependencies."""

from __future__ import annotations

import struct
import zlib
from pathlib import Path


SIZE = 64
CREAM = (242, 233, 210, 255)
GREEN = (4, 61, 32, 255)
LEAF = (62, 90, 46, 255)
AMBER = (246, 197, 34, 255)


def inside_rounded_rect(x: int, y: int, left: int, top: int, right: int, bottom: int, radius: int) -> bool:
    if left + radius <= x <= right - radius or top + radius <= y <= bottom - radius:
        return left <= x <= right and top <= y <= bottom
    cx = left + radius if x < left + radius else right - radius
    cy = top + radius if y < top + radius else bottom - radius
    return (x - cx) ** 2 + (y - cy) ** 2 <= radius**2


def pixel(x: int, y: int) -> tuple[int, int, int, int]:
    if not inside_rounded_rect(x, y, 2, 2, 61, 61, 8):
        return (0, 0, 0, 0)
    color = CREAM
    if (10 <= x <= 15 or 48 <= x <= 53) and any(a <= y <= b for a, b in ((11, 17), (28, 34), (45, 51))):
        color = LEAF
    if 20 <= x <= 44 and any(a <= y <= b for a, b in ((16, 20), (29, 33), (42, 46))):
        color = GREEN
    if 20 <= x <= 24 and 29 <= y <= 33:
        color = AMBER
    return color


def chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)


def png_bytes() -> bytes:
    rows = []
    for y in range(SIZE):
        rows.append(b"\x00" + b"".join(bytes(pixel(x, y)) for x in range(SIZE)))
    header = struct.pack(">IIBBBBB", SIZE, SIZE, 8, 6, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(b"".join(rows), 9)) + chunk(b"IEND", b"")


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    destination = root / "desktop" / "VilmLyricsAligner.Desktop" / "Assets" / "vilm.ico"
    destination.parent.mkdir(parents=True, exist_ok=True)
    png = png_bytes()
    header = struct.pack("<HHH", 0, 1, 1)
    entry = struct.pack("<BBBBHHII", SIZE, SIZE, 0, 0, 1, 32, len(png), 6 + 16)
    destination.write_bytes(header + entry + png)
    print(destination)


if __name__ == "__main__":
    main()
