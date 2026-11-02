"""生成 skill-forge 专家头像（与 aquilair-fde 头像同族风格：深蓝底、蓝线网络、琥珀节点、底部白字）。

输出：plugins/skill-forge/avatars/expert.png（512x512）
"""

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SIZE = 512
BG = (31, 42, 68)        # 深蓝底（同族 #1F2A44）
LINE = (91, 121, 201)    # 蓝色连线
NODE = (240, 185, 90)    # 琥珀节点
WHITE = (245, 247, 252)

OUT = Path(__file__).resolve().parent.parent / "plugins" / "skill-forge" / "avatars" / "expert.png"


def hex_points(cx: float, cy: float, r: float) -> list[tuple[float, float]]:
    """正六边形顶点（顶点朝上）。"""
    return [(cx + r * math.sin(math.radians(a)), cy - r * math.cos(math.radians(a))) for a in range(0, 360, 60)]


def main() -> None:
    img = Image.new("RGB", (SIZE, SIZE), BG)
    d = ImageDraw.Draw(img)
    cx, cy, r = SIZE / 2, SIZE / 2 - 40, 130
    pts = hex_points(cx, cy, r)

    # 外六边形 + 三条主对角线（家族网络母题）
    for i in range(6):
        d.line([pts[i], pts[(i + 1) % 6]], fill=LINE, width=7)
    for i in (0, 1, 2):
        d.line([pts[i], pts[i + 3]], fill=LINE, width=5)
    # 顶点琥珀节点
    for p in pts:
        d.ellipse([p[0] - 16, p[1] - 16, p[0] + 16, p[1] + 16], fill=NODE)

    # 中央锻造锤（白柄 + 琥珀锤头），斜 45 度
    ang = math.radians(-40)
    dx, dy = math.cos(ang), math.sin(ang)
    hx, hy = cx + 14, cy - 2         # 锤头中心
    # 柄：从锤头向右下延伸的粗线
    d.line([hx, hy, hx + dx * 118, hy + dy * 118], fill=WHITE, width=13)
    # 锤头：沿柄法向的圆角矩形（用旋转多边形近似）
    nx, ny = -dy, dx
    hw, hh = 26, 40                  # 半宽 / 半高
    head = [
        (hx - nx * hw - dx * hh, hy - ny * hw - dy * hh),
        (hx + nx * hw - dx * hh, hy + ny * hw - dy * hh),
        (hx + nx * hw + dx * hh, hy + ny * hw + dy * hh),
        (hx - nx * hw + dx * hh, hy - ny * hw + dy * hh),
    ]
    d.polygon(head, fill=NODE)
    # 锤击火花：锤头左上（击打面）三颗小琥珀点
    for sx, sy, sr in ((hx - 52, hy - 46, 6), (hx - 74, hy - 24, 5), (hx - 38, hy - 70, 4)):
        d.ellipse([sx - sr, sy - sr, sx + sr, sy + sr], fill=NODE)

    # 底部标题
    font = ImageFont.truetype(r"C:\Windows\Fonts\msyhbd.ttc", 68)
    text = "技能锻造"
    box = d.textbbox((0, 0), text, font=font)
    d.text(((SIZE - box[2] + box[0]) / 2 - box[0], SIZE - 118), text, font=font, fill=WHITE)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT)
    print(f"[写入] {OUT}")


if __name__ == "__main__":
    main()
