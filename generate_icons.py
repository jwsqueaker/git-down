"""Generate PWA icons for the portfolio management app."""
import struct
import zlib


def create_png(width, height, bg_color, text_lines):
    """Create a simple PNG icon with a colored background and text-like pattern."""

    def make_pixel(r, g, b, a=255):
        return bytes([r, g, b, a])

    # Create image data
    raw_data = b""
    for y in range(height):
        raw_data += b"\x00"  # filter byte
        for x in range(width):
            # Background
            r, g, b = bg_color

            # Draw a simple chart icon in the center
            cx, cy = width // 2, height // 2
            size = width // 3

            # White rounded rectangle background
            margin = width // 6
            if margin < x < width - margin and margin < y < height - margin:
                r, g, b = 255, 255, 255

            # Simple bar chart bars
            bar_w = size // 5
            bars = [
                (cx - size // 2, 0.4),
                (cx - size // 6, 0.7),
                (cx + size // 6, 0.5),
                (cx + size // 2, 0.9),
            ]
            for bx, bh in bars:
                bar_top = int(cy + size // 2 - size * bh)
                bar_bottom = cy + size // 2
                if bx - bar_w // 2 <= x <= bx + bar_w // 2 and bar_top <= y <= bar_bottom:
                    r, g, b = bg_color

            raw_data += make_pixel(r, g, b, 255)

    # PNG encoding
    def chunk(chunk_type, data):
        c = chunk_type + data
        crc = zlib.crc32(c) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + c + struct.pack(">I", crc)

    signature = b"\x89PNG\r\n\x1a\n"

    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    ihdr = chunk(b"IHDR", ihdr_data)

    compressed = zlib.compress(raw_data)
    idat = chunk(b"IDAT", compressed)

    iend = chunk(b"IEND", b"")

    return signature + ihdr + idat + iend


if __name__ == "__main__":
    theme_color = (31, 119, 180)  # #1f77b4

    for size in [192, 512]:
        png_data = create_png(size, size, theme_color, [])
        with open(f".streamlit/static/icon-{size}.png", "wb") as f:
            f.write(png_data)
        print(f"Generated icon-{size}.png")
