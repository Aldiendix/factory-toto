"""Create a bright dock icon and hero banner for the plant forecast app."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from factory_toto.config import PROJECT_ROOT

ASSETS_DIR = PROJECT_ROOT / "assets"
HERO_PATH = ASSETS_DIR / "hero.png"
HERO_BG_PATH = ASSETS_DIR / "hero_bg.png"
ICON_PATH = ASSETS_DIR / "icon.png"
TITLE = "Predict factaroy variable"


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    names = (
        ("segoeuib.ttf", "arialbd.ttf", "calibrib.ttf")
        if bold
        else ("segoeui.ttf", "arial.ttf", "calibri.ttf")
    )
    for name in names:
        path = Path(r"C:\Windows\Fonts") / name
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def _rounded_rect(draw: ImageDraw.ImageDraw, box, fill, radius: int) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill)


def write_icon(path: Path = ICON_PATH, size: int = 256) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    _rounded_rect(draw, (8, 8, size - 8, size - 8), "#0F766E", 56)
    _rounded_rect(draw, (22, 22, size - 22, size - 22), "#F0FDFA", 44)

    # Factory blocks
    draw.rectangle((58, 128, 108, 188), fill="#0F766E")
    draw.rectangle((118, 98, 168, 188), fill="#0D9488")
    draw.rectangle((178, 138, 208, 188), fill="#115E59")
    draw.rectangle((70, 108, 96, 128), fill="#F97316")
    draw.polygon([(118, 98), (143, 72), (168, 98)], fill="#134E4A")

    # Forecast line
    pts = [(54, 198), (88, 186), (118, 190), (148, 168), (178, 154), (208, 146)]
    draw.line(pts, fill="#EA580C", width=8, joint="curve")
    for x, y in pts[::2]:
        draw.ellipse((x - 6, y - 6, x + 6, y + 6), fill="#F97316")

    img.save(path)
    return path


def write_hero(path: Path = HERO_PATH, size: tuple[int, int] = (1600, 420)) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if HERO_BG_PATH.exists():
        photo = Image.open(HERO_BG_PATH).convert("RGB")
        photo.save(path, quality=95)
        return path
    w, h = size
    img = Image.new("RGB", size, "#E8F4F8")
    draw = ImageDraw.Draw(img)

    for y in range(h):
        t = y / max(h - 1, 1)
        r = int(232 - 18 * t)
        g = int(244 - 8 * t)
        b = int(248 - 4 * t)
        draw.line((0, y, w, y), fill=(r, g, b))

    glow = Image.new("RGB", size, "#E8F4F8")
    gdraw = ImageDraw.Draw(glow)
    gdraw.ellipse((-80, -120, 520, 360), fill="#99F6E4")
    gdraw.ellipse((980, -40, 1720, 480), fill="#FED7AA")
    img = Image.blend(img, glow.filter(ImageFilter.GaussianBlur(48)), 0.45)
    draw = ImageDraw.Draw(img)

    _rounded_rect(draw, (28, 28, w - 28, h - 28), "#FFFFFF", 32)
    draw.rounded_rectangle((28, 28, w - 28, h - 28), radius=32, outline="#99F6E4", width=3)

    # Left factory art
    base_x, base_y = 78, 268
    draw.rectangle((base_x, base_y - 90, base_x + 70, base_y), fill="#0F766E")
    draw.rectangle((base_x + 84, base_y - 140, base_x + 168, base_y), fill="#0D9488")
    draw.rectangle((base_x + 182, base_y - 70, base_x + 232, base_y), fill="#115E59")
    draw.polygon(
        [(base_x + 84, base_y - 140), (base_x + 126, base_y - 178), (base_x + 168, base_y - 140)],
        fill="#134E4A",
    )
    draw.rectangle((base_x + 18, base_y - 118, base_x + 48, base_y - 90), fill="#F97316")
    for wx in (base_x + 14, base_x + 38):
        draw.rectangle((wx, base_y - 70, wx + 16, base_y - 48), fill="#CCFBF1")
    for wx in (base_x + 102, base_x + 128):
        draw.rectangle((wx, base_y - 110, wx + 18, base_y - 84), fill="#CCFBF1")

    title_font = _font(54, bold=True)
    sub_font = _font(22, bold=False)
    kicker_font = _font(16, bold=True)

    draw.text((360, 78), "LOCAL PLANT FORECAST  ·  TOTO 2.0", font=kicker_font, fill="#0F766E")
    draw.text((360, 118), TITLE, font=title_font, fill="#134E4A")
    draw.text(
        (360, 196),
        "See the next shift for temperature, vibration, power, and output.",
        font=sub_font,
        fill="#334155",
    )
    draw.text(
        (360, 236),
        "Runs on this computer. Upload a CSV or use the sample line.",
        font=sub_font,
        fill="#475569",
    )

    # Forecast card on the right
    card = (1120, 78, 1520, 342)
    _rounded_rect(draw, card, "#F0FDFA", 24)
    draw.rounded_rectangle(card, radius=24, outline="#5EEAD4", width=3)
    band = [(1160, 250), (1240, 230), (1320, 236), (1400, 200), (1480, 176), (1480, 300), (1160, 300)]
    draw.polygon(band, fill="#FED7AA")
    line = [(1160, 250), (1240, 230), (1320, 236), (1400, 200), (1480, 176)]
    draw.line(line, fill="#0F766E", width=8, joint="curve")
    draw.text((1160, 96), "Next-shift outlook", font=_font(18, bold=True), fill="#0F766E")

    img.save(path, quality=95)
    return path


def write_brand_assets(force: bool = False) -> tuple[Path, Path]:
    hero = HERO_PATH if HERO_PATH.exists() and not force else write_hero()
    icon = ICON_PATH if ICON_PATH.exists() and not force else write_icon()
    return hero, icon


if __name__ == "__main__":
    hero, icon = write_brand_assets()
    print(hero)
    print(icon)
