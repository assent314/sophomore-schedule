"""把 assets/icon-512.png 转成安卓各密度图标 + 自适应前景 + 启动图。

用法（用 DSH 捆绑的 python，带 Pillow）：
  python tools/android_icons.py
"""

import io
import os
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, "frontend", "android", "app", "src", "main", "res")
SRC = os.path.join(ROOT, "assets", "icon-512.png")

DENSITIES = {  # 目录后缀: 启动图标像素尺寸
    "mdpi": 48,
    "hdpi": 72,
    "xhdpi": 96,
    "xxhdpi": 144,
    "xxxhdpi": 192,
}
FG_SIZES = {  # 自适应图标前景画布（108dp）
    "mdpi": 108,
    "hdpi": 162,
    "xhdpi": 216,
    "xxhdpi": 324,
    "xxxhdpi": 432,
}


def content_crop(img: Image.Image) -> Image.Image:
    """裁出白色卡片区域（含右下的 AI 星芒）。"""
    w, h = img.size
    px = img.load()
    xs, ys = [], []
    for y in range(0, h, 2):
        for x in range(0, w, 2):
            r, g, b, a = px[x, y]
            if a > 200 and r > 235 and g > 235 and b > 235:
                xs.append(x)
                ys.append(y)
    if not xs:
        return img
    left, right = min(xs), max(xs)
    top, bottom = min(ys), max(ys)
    pad_x = int((right - left) * 0.07)
    pad_y = int((bottom - top) * 0.05)
    box = (
        max(0, left - pad_x),
        max(0, top - pad_y),
        min(w, right + pad_x),
        min(h, bottom + pad_y),
    )
    return img.crop(box)


def rounded(img: Image.Image, size: int, radius_ratio: float = 0.22) -> Image.Image:
    img = img.convert("RGBA").resize((size, size), Image.LANCZOS)
    mask = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(mask)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=int(size * radius_ratio), fill=255)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(img, (0, 0), mask)
    return out


def circular(img: Image.Image, size: int) -> Image.Image:
    img = img.convert("RGBA").resize((size, size), Image.LANCZOS)
    mask = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(mask)
    d.ellipse([0, 0, size - 1, size - 1], fill=255)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(img, (0, 0), mask)
    return out


def main() -> None:
    icon = Image.open(SRC).convert("RGBA")
    crop = content_crop(icon)

    for suffix, size in DENSITIES.items():
        folder = os.path.join(RES, f"mipmap-{suffix}")
        os.makedirs(folder, exist_ok=True)
        rounded(icon, size).save(os.path.join(folder, "ic_launcher.png"))
        circular(icon, size).save(os.path.join(folder, "ic_launcher_round.png"))

        fg_size = FG_SIZES[suffix]
        # 自适应前景：内容占 72/108 的安全区，空白透明边
        inner = int(fg_size * 72 / 108)
        ratio = min(inner / crop.width, inner / crop.height)
        resized = crop.resize((max(1, round(crop.width * ratio)), max(1, round(crop.height * ratio))), Image.LANCZOS)
        fg = Image.new("RGBA", (fg_size, fg_size), (0, 0, 0, 0))
        fg.paste(resized, ((fg_size - resized.width) // 2, (fg_size - resized.height) // 2), resized)
        fg.save(os.path.join(folder, "ic_launcher_foreground.png"))

    # 自适应图标背景：系统青色不对，改成和图标一致的蓝
    bg_path = os.path.join(RES, "drawable", "ic_launcher_background.xml")
    with io.open(bg_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<shape xmlns:android="http://schemas.android.com/apk/res/android" android:shape="rectangle">\n'
            '    <solid android:color="#2E7BF6" />\n'
            "</shape>\n"
        )

    # 启动图：白底 + 居中图标（1024x1024）
    splash = Image.new("RGBA", (1024, 1024), (255, 255, 255, 255))
    logo = rounded(icon, 380)
    splash.paste(logo, ((1024 - 380) // 2, (1024 - 380) // 2), logo)
    splash.convert("RGB").save(os.path.join(RES, "drawable", "splash.png"))

    print("android icons updated under", RES)


if __name__ == "__main__":
    main()
