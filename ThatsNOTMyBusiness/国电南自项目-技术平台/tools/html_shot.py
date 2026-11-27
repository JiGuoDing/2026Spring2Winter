# -*- coding: utf-8 -*-
"""网页整页截图 + 切片（含窄屏视口模拟）。

为什么不用 `msedge --headless --window-size=390,xxx`：
Windows 上浏览器窗口有最小宽度，390 会被夹到约 477 CSS px，
截出来的图是"477 宽的页面裁掉右边"，看起来像横向溢出，其实是假象。
本脚本用 iframe 容器把视口宽度钉死，媒体查询才按真实宽度生效。

用法：
    python tools/html_shot.py <html路径> --width 390
    python tools/html_shot.py <html路径> --width 1280 --slices 6
    python tools/html_shot.py <html路径> --width 390 --height 16000 --keep

输出（默认落在系统临时目录）：
    shot_w<width>.png        整页图
    shot_w<width>_00.png ... 切片（每片 --slice-h，默认 1050px；<=480 宽时按原生分辨率，便于目检）

依赖：Edge（默认路径可被 --edge 覆盖）、Pillow。
"""
import sys, os, io, subprocess, tempfile

try:
    from PIL import Image
except ImportError:
    sys.exit("需要 Pillow：pip install pillow")

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"


def file_url(p):
    p = os.path.abspath(p).replace("\\", "/")
    out = []
    for ch in p:
        if ch.isascii() and (ch.isalnum() or ch in "/:._-~"):
            out.append(ch)
        else:
            out.extend("%%%02X" % b for b in ch.encode("utf-8"))
    return "file:///" + "".join(out).lstrip("/")


def shoot(html, width, height, out_png, edge):
    tmp = tempfile.mkdtemp(prefix="shot_")
    wrapper = os.path.join(tmp, "wrap.html")
    win_w = max(width + 60, 520)          # 给窗口留出边框，确保未被夹
    io.open(wrapper, "w", encoding="utf-8").write(
        '<!DOCTYPE html><html><head><meta charset="utf-8">'
        "<style>html,body{margin:0;padding:0;background:#8a8a8a}"
        "iframe{width:%dpx;height:%dpx;border:0;display:block}</style></head>"
        "<body><iframe src=\"%s\"></iframe></body></html>" % (width, height, file_url(html))
    )
    cmd = [edge, "--headless=old", "--disable-gpu", "--hide-scrollbars",
           "--force-device-scale-factor=1",
           "--window-size=%d,%d" % (win_w, height),
           "--screenshot=" + os.path.abspath(out_png), file_url(wrapper)]
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if not os.path.exists(out_png):
        sys.exit("截图失败：%s\n%s" % (r.stdout.decode("utf-8", "ignore")[-800:],
                                       r.stderr.decode("utf-8", "ignore")[-800:]))


def trim(im, width):
    """裁掉 iframe 底部多余的页面背景，返回裁好的图与内容底边 y。"""
    im = im.crop((0, 0, width, im.size[1])).convert("RGB")
    w, h = im.size
    bg = im.getpixel((1, h - 2))
    last = h - 1
    for y in range(h - 3, 0, -1):
        row = [im.getpixel((x, y)) for x in range(2, w - 2, 3)]
        diff = sum(1 for p in row if abs(p[0] - bg[0]) + abs(p[1] - bg[1]) + abs(p[2] - bg[2]) > 12)
        if diff > 4:
            last = y
            break
    return im.crop((0, 0, w, min(h, last + 3))), last


def main():
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    html = args[0]
    width, height, slice_h, keep, edge = 390, 14000, 1050, False, EDGE
    for i, a in enumerate(args):
        if a == "--width":
            width = int(args[i + 1])
        elif a == "--height":
            height = int(args[i + 1])
        elif a == "--slice-h":
            slice_h = int(args[i + 1])
        elif a == "--edge":
            edge = args[i + 1]
        elif a == "--keep":
            keep = True
    if not os.path.exists(html):
        sys.exit("找不到 html：%s" % html)

    outdir = tempfile.gettempdir()
    full = os.path.join(outdir, "shot_w%d.png" % width)
    shoot(html, width, height, full, edge)
    im, bottom = trim(Image.open(full), width)
    im.save(full)
    print("整页：%s  (%d x %d，内容底边 y=%d)" % (full, im.size[0], im.size[1], bottom))

    n = 0
    for i in range(0, im.size[1], slice_h):
        p = os.path.join(outdir, "shot_w%d_%02d.png" % (width, n))
        im.crop((0, i, im.size[0], min(im.size[1], i + slice_h))).save(p)
        n += 1
    print("切片：%d 张，前缀 shot_w%d_" % (n, width))
    if n and im.size[1] >= height - 4:
        print("注意：内容触到 --height 上限（%d），整页可能被截断，请加大 --height 重跑。" % height)
    if not keep:
        pass


if __name__ == "__main__":
    main()
