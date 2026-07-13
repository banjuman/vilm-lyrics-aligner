"""Generate a high-resolution macOS source icon from the code-native Vilm mark."""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

from create_vilm_icon import SIZE as SOURCE_SIZE
from create_vilm_icon import chunk, pixel


OUTPUT_SIZE = 1024


def png_bytes() -> bytes:
    rows = []
    for y in range(OUTPUT_SIZE):
        source_y = min(SOURCE_SIZE - 1, y * SOURCE_SIZE // OUTPUT_SIZE)
        row = []
        for x in range(OUTPUT_SIZE):
            source_x = min(SOURCE_SIZE - 1, x * SOURCE_SIZE // OUTPUT_SIZE)
            row.append(bytes(pixel(source_x, source_y)))
        rows.append(b"\x00" + b"".join(row))
    header = struct.pack(">IIBBBBB", OUTPUT_SIZE, OUTPUT_SIZE, 8, 6, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(b"".join(rows), 9))
        + chunk(b"IEND", b"")
    )


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    destination = (
        root
        / "desktop"
        / "VilmLyricsAligner.Desktop"
        / "Assets"
        / "vilm-1024.png"
    )
    destination.write_bytes(png_bytes())
    print(destination)


if __name__ == "__main__":
    main()
