#!/usr/bin/env python3
"""Generate the Open Graph preview image (1200x630) for link cards.

Deterministic and on-brand: the same dark + brand-gradient language as
DemoLanding, so a shared link looks like the product, not a placeholder.

Usage: python3 frontend/scripts/make_og_image.py [output.png]
Requires Pillow. macOS system Arial is used (Cyrillic coverage).
"""

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1200, 630
OUT = sys.argv[1] if len(sys.argv) > 1 else "frontend/public/og.png"

FONT_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
FONT_REG = "/System/Library/Fonts/Supplemental/Arial.ttf"

BRAND = (53, 99, 233)      # #3563e9
ACCENT = (139, 92, 246)    # #8b5cf6
BG = (10, 18, 40)          # near slate-950
WHITE = (255, 255, 255)
MUTED = (203, 213, 225)    # slate-300


def radial_glow(color, cx, cy, radius, strength):
    """A soft glow: tiny alpha map, blurred and upscaled — cheap and smooth."""
    size = 96
    img = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(img)
    d.ellipse([size * 0.15, size * 0.15, size * 0.85, size * 0.85], fill=int(255 * strength))
    img = img.filter(ImageFilter.GaussianBlur(size * 0.18))
    img = img.resize((radius * 2, radius * 2), Image.LANCZOS)
    glow = Image.new("RGB", (radius * 2, radius * 2), color)
    return img, glow


def diagonal_gradient(size, start, end):
    """Diagonal two-stop gradient via a 2x2 upscale."""
    tiny = Image.new("RGB", (2, 2))
    tiny.putdata([start, end, end, start])
    return tiny.resize((size, size), Image.LANCZOS)


def rounded_mask(size, radius):
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=255)
    return mask


def text_center(draw, text, font, fill, cx, y):
    bbox = draw.textbbox((0, 0), text, font=font)
    draw.text((cx - (bbox[2] - bbox[0]) / 2, y), text, font=font, fill=fill)
    return bbox[3] - bbox[1]


def make_og_image(out: str = OUT) -> None:
    img = Image.new("RGB", (W, H), BG)

    # Ambient glows
    for color, cx, cy, radius, strength in [
        (BRAND, int(W * 0.28), int(H * 0.08), 620, 0.55),
        (ACCENT, int(W * 0.92), int(H * 0.18), 560, 0.45),
    ]:
        mask, glow = radial_glow(color, cx, cy, radius, strength)
        img.paste(glow, (cx - radius, cy - radius), mask)

    # Subtle grid
    grid = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grid)
    step = 40
    for x in range(0, W, step):
        gd.line([(x, 0), (x, H)], fill=(148, 163, 184, 16), width=1)
    for y in range(0, H, step):
        gd.line([(0, y), (W, y)], fill=(148, 163, 184, 16), width=1)
    img = Image.alpha_composite(img.convert("RGBA"), grid).convert("RGB")

    draw = ImageDraw.Draw(img)

    # Logo tile: gradient rounded square + white launch arrow (matches favicon)
    tile = 96
    tx, ty = 72, 66
    grad = diagonal_gradient(tile, BRAND, ACCENT)
    img.paste(grad, (tx, ty), rounded_mask(tile, 24))
    td = ImageDraw.Draw(img)
    pad = 26
    td.line([(tx + pad, ty + tile - pad), (tx + tile - pad, ty + pad)],
            fill=WHITE, width=8, joint="curve")
    td.line([(tx + pad, ty + pad), (tx + tile - pad, ty + pad)], fill=WHITE, width=8)
    td.line([(tx + tile - pad, ty + pad), (tx + tile - pad, ty + pad + tile - 2 * pad)],
            fill=WHITE, width=8)

    # Wordmark
    f_word = ImageFont.truetype(FONT_BOLD, 44)
    draw.text((tx + tile + 22, ty + tile // 2 - 26), "СТАРТ", font=f_word, fill=WHITE)

    # Headline
    f_head = ImageFont.truetype(FONT_BOLD, 66)
    text_center(draw, "Первый проект —", f_head, WHITE, W // 2, 250)
    text_center(draw, "для каждого студента", f_head, MUTED, W // 2, 326)

    # Tagline
    f_sub = ImageFont.truetype(FONT_REG, 30)
    text_center(draw, "AI-подбор проектов · команда в один клик · портфолио собирается само",
                f_sub, (148, 163, 184), W // 2, 424)

    # Feature pills
    pills = ["AI-подбор", "Сбор команды", "Подтверждённое портфолио"]
    f_pill = ImageFont.truetype(FONT_BOLD, 24)
    widths = [draw.textbbox((0, 0), p, font=f_pill) for p in pills]
    pw = [w[2] - w[0] + 48 for w in widths]
    gap = 20
    total = sum(pw) + gap * (len(pills) - 1)
    x = (W - total) // 2
    for text, w in zip(pills, pw):
        overlay = Image.new("RGBA", (w, 56), (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        od.rounded_rectangle([0, 0, w - 1, 55], radius=28, fill=(255, 255, 255, 14),
                             outline=(255, 255, 255, 45), width=1)
        img.paste(overlay, (x, 486), overlay)
        bbox = draw.textbbox((0, 0), text, font=f_pill)
        draw.text((x + (w - (bbox[2] - bbox[0])) / 2, 500), text, font=f_pill, fill=WHITE)
        x += w + gap

    # Footer
    f_foot = ImageFont.truetype(FONT_REG, 22)
    text_center(draw, "Хакатон 2026 · мессенджер MAX · первый проект для каждого",
                f_foot, (100, 116, 139), W // 2, 578)

    img.save(out, optimize=True)
    print(f"wrote {out} ({W}x{H})")




def make_icon(path: str, size: int) -> None:
    """App icon (PNG): brand-gradient rounded square + white launch arrow.

    Chrome requires PNG 192/512 for the install prompt; SVG alone isn't
    enough, so these are generated next to the existing vector icons.
    """
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    grad = diagonal_gradient(size, BRAND, ACCENT).convert("RGBA")
    radius = int(size * 0.22)
    img.paste(grad, (0, 0), rounded_mask(size, radius))

    d = ImageDraw.Draw(img)
    pad = int(size * 0.27)
    w = max(6, size // 16)
    d.line([(pad, size - pad), (size - pad, pad)], fill=WHITE, width=w, joint="curve")
    d.line([(pad, pad), (size - pad, pad)], fill=WHITE, width=w)
    d.line([(size - pad, pad), (size - pad, size - pad)], fill=WHITE, width=w)

    img.save(path)
    print(f"wrote {path} ({size}x{size})")


# Output paths resolve from the repo root, so the script works from anywhere.
_ROOT = Path(__file__).resolve().parent.parent
_PUBLIC = _ROOT / "public"


def main() -> None:
    args = sys.argv[1:]
    if args == ["--icons"]:
        make_icon(_PUBLIC / "icon-192.png", 192)
        make_icon(_PUBLIC / "icon-512.png", 512)
        return
    # Default: the OG image, with an optional explicit output path.
    out = Path(args[0]) if args else _PUBLIC / "og.png"
    make_og_image(str(out))


if __name__ == "__main__":
    main()
