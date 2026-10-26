"""生成应用图标：蓝色圆角日历 + AI 星芒，输出 assets/icon.ico 与 assets/icon-512.png。

用 PIL 在 4 倍超采样下绘制再缩采样，保证 16px 下依然清晰。
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

S = 4                      # 超采样倍数
BASE = 256                 # 设计尺寸
C = BASE * S

BLUE_TOP = (66, 133, 244)
BLUE_BOTTOM = (21, 101, 192)
PAGE = (255, 255, 255)
PAGE_EDGE = (232, 240, 254)
BAR_COLORS = [
    (66, 133, 244),    # 学习 蓝
    (52, 168, 83),     # 运动 绿
    (251, 188, 4),     # 事务 黄
    (234, 67, 53),     # 提醒 红
]
SPARKLE = (255, 255, 255)
SPARKLE_EDGE = (251, 188, 4)


def px(v: float) -> int:
    return int(round(v * S))


def rounded(size: tuple[int, int], radius: float, fill) -> Image.Image:
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle([0, 0, size[0] - 1, size[1] - 1], radius=px(radius), fill=fill)
    return layer


def vertical_gradient(size: tuple[int, int], top, bottom) -> Image.Image:
    w, h = size
    grad = Image.new("RGB", (1, h))
    for y in range(h):
        t = y / max(1, h - 1)
        grad.putpixel(
            (0, y),
            (
                int(top[0] + (bottom[0] - top[0]) * t),
                int(top[1] + (bottom[1] - top[1]) * t),
                int(top[2] + (bottom[2] - top[2]) * t),
            ),
        )
    return grad.resize((w, h), Image.BILINEAR)


def star_points(cx: float, cy: float, outer: float, inner: float) -> list[tuple[int, int]]:
    """四角星芒（尖角朝上下左右，腰线收进去）。"""
    o, i = outer, inner
    pts = [
        (cx, cy - o),
        (cx + i, cy - i),
        (cx + o, cy),
        (cx + i, cy + i),
        (cx, cy + o),
        (cx - i, cy + i),
        (cx - o, cy),
        (cx - i, cy - i),
    ]
    return [(px(x), px(y)) for x, y in pts]


def build() -> Image.Image:
    img = Image.new("RGBA", (C, C), (0, 0, 0, 0))

    # 1) 蓝色圆角底板 + 渐变
    bg = vertical_gradient((C, C), BLUE_TOP, BLUE_BOTTOM).convert("RGBA")
    mask = rounded((C, C), 56, (255, 255, 255, 255)).split()[3]
    img.paste(bg, (0, 0), mask)

    # 2) 白色日历纸
    page_box = (px(46), px(52), px(210), px(206))
    page_w = page_box[2] - page_box[0]
    page_h = page_box[3] - page_box[1]
    page = rounded((page_w, page_h), 24, PAGE)
    img.paste(page, (page_box[0], page_box[1]), page)

    d = ImageDraw.Draw(img)

    # 3) 顶部装订环
    for cx in (px(88), px(168)):
        d.rounded_rectangle(
            [cx - px(9), px(38), cx + px(9), px(70)], radius=px(9), fill=PAGE
        )

    # 4) 日历头（浅蓝）+ 圆点
    header = rounded((page_w - px(20), px(30)), 12, PAGE_EDGE)
    img.paste(header, (page_box[0] + px(10), page_box[1] + px(10)), header)
    for i, color in enumerate(BAR_COLORS[:3]):
        cx = page_box[0] + px(30) + i * px(18)
        d.ellipse([cx - px(3), page_box[1] + px(21), cx + px(3), page_box[1] + px(27)], fill=color)

    # 5) 日程条：长短错落，颜色对应任务类别
    bars = [
        (0.30, 0.62, BAR_COLORS[0]),
        (0.46, 0.86, BAR_COLORS[1]),
        (0.62, 0.55, BAR_COLORS[2]),
        (0.78, 0.74, BAR_COLORS[3]),
    ]
    for y_ratio, width_ratio, color in bars:
        top = page_box[1] + page_h * y_ratio
        left = page_box[0] + px(22)
        bar_w = (page_w - px(44)) * width_ratio
        d.rounded_rectangle(
            [left, top, left + bar_w, top + px(18)], radius=px(9), fill=color
        )

    # 6) AI 星芒（右下压角，白芯黄边），最后统一裁到圆角底板内
    d.polygon(star_points(188, 186, 44, 15), fill=SPARKLE_EDGE)
    d.polygon(star_points(188, 186, 34, 12), fill=SPARKLE)

    out = Image.new("RGBA", (C, C), (0, 0, 0, 0))
    out.paste(img, (0, 0), mask)
    return out


def main() -> None:
    out_dir = Path(__file__).resolve().parent.parent / "assets"
    out_dir.mkdir(parents=True, exist_ok=True)
    big = build()
    icon_512 = big.resize((512, 512), Image.LANCZOS)
    icon_512.save(out_dir / "icon-512.png")
    big.resize((1024, 1024), Image.LANCZOS).save(out_dir / "icon-1024.png")

    sizes = [16, 24, 32, 48, 64, 128, 256]
    icon_512.save(out_dir / "icon.ico", format="ICO", sizes=[(s, s) for s in sizes])
    print("saved:", out_dir / "icon.ico", out_dir / "icon-512.png")


if __name__ == "__main__":
    main()
