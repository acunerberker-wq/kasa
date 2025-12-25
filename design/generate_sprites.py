from __future__ import annotations

from pathlib import Path

ACCENT = "#7c5cff"
NEUTRAL = "#9ba3b8"

SPRITE_DIR = Path(__file__).parent / "sprites"
SPRITE_DIR.mkdir(parents=True, exist_ok=True)


def svg_header(width: int, height: int) -> list[str]:
    return [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" fill="none">',
    ]


def svg_footer() -> list[str]:
    return ["</svg>"]


def spinner_sprite() -> str:
    frames = []
    width = 24 * 12
    height = 24
    frames.extend(svg_header(width, height))

    for i in range(12):
        x = i * 24
        angle = i * 30
        frames.append(f'<g transform="translate({x} 0)">')
        frames.append(f'<circle cx="12" cy="12" r="8" stroke="{NEUTRAL}" stroke-width="2" opacity="0.35" />')
        frames.append(
            f'<line x1="12" y1="3.5" x2="12" y2="7" stroke="{ACCENT}" stroke-width="2" stroke-linecap="round" '
            f'transform="rotate({angle} 12 12)" />'
        )
        frames.append("</g>")

    frames.extend(svg_footer())
    return "\n".join(frames)


def bell_sprite() -> str:
    frames = []
    width = 24 * 12
    height = 24
    frames.extend(svg_header(width, height))

    offsets = [0, -1, -2, -3, -2, -1, 0, 1, 0, -1, 0, 0]
    for i, offset in enumerate(offsets):
        x = i * 24
        y = 4 + offset
        frames.append(f'<g transform="translate({x} 0)">')
        frames.append(
            f'<path d="M7 {y+6}c0-3 2.5-5.5 5-6 2.5.5 5 3 5 6v4l2 2H5l2-2v-4z" '
            f'stroke="{NEUTRAL}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" />'
        )
        frames.append(
            f'<circle cx="12" cy="{y+16}" r="1.4" fill="{ACCENT}" />'
        )
        frames.append("</g>")

    frames.extend(svg_footer())
    return "\n".join(frames)


def check_sprite() -> str:
    frames = []
    width = 24 * 12
    height = 24
    frames.extend(svg_header(width, height))

    scales = [0.6, 0.7, 0.8, 0.9, 1.0, 1.05, 1.1, 1.05, 1.0, 0.95, 0.9, 0.85]
    for i, scale in enumerate(scales):
        x = i * 24
        frames.append(f'<g transform="translate({x} 0)">')
        frames.append(
            f'<circle cx="12" cy="12" r="8" stroke="{NEUTRAL}" stroke-width="1.6" opacity="0.3" />'
        )
        frames.append(
            f'<g transform="translate(12 12) scale({scale}) translate(-12 -12)">'
            f'<path d="M8 12.5l2.2 2.3L16 9.5" stroke="{ACCENT}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />'
            f'</g>'
        )
        frames.append("</g>")

    frames.extend(svg_footer())
    return "\n".join(frames)


def write_svg(filename: str, content: str) -> None:
    (SPRITE_DIR / filename).write_text(content, encoding="utf-8")


if __name__ == "__main__":
    write_svg("sync-spinner.svg", spinner_sprite())
    write_svg("notification-bell-bounce.svg", bell_sprite())
    write_svg("success-check-pop.svg", check_sprite())
