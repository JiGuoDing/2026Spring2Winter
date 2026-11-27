# -*- coding: utf-8 -*-
"""幻灯片纵向留白检测。

用途：PPT 页面内容不足时，下方会出现大片空白（slidep 用 justifyContent:'space-between' 分布，
内容一少就露白）。本脚本逐行统计墨迹，找出内容区内的最大连续空白段。

用法：
    python tools/slide_gap.py <deck目录或png目录> [--thresh 70] [--lo 0.40] [--hi 0.92]

    例：python tools/slide_gap.py "交付物/PPT/客户交流版/preview"
        python tools/slide_gap.py "交付物/PPT/决策汇报版/preview" --thresh 70

判据：幻灯片像素阈值为 --thresh（默认 70）。脚本按 图片宽/1280 自动换算缩放，
      所以 1920 宽的预览图（1.5 倍）与 1280 宽的图用同一阈值。
输出：每页一行；超过阈值的页尾标 [WARN]，末尾给汇总。
"""
import sys, os, glob

try:
    from PIL import Image
except ImportError:
    sys.exit("需要 Pillow：pip install pillow")


def scan(path, thresh=70.0, lo=0.40, hi=0.92):
    im = Image.open(path).convert("L")
    w, h = im.size
    scale = w / 1280.0                      # 1920 宽 => 1.5
    px = im.load()
    # 每行墨迹像素数（灰度 < 235 视为墨迹；白底页面适用，深底页面天然无空白段）
    ink = []
    step = 2                                # 隔列采样，快 2 倍
    for y in range(h):
        c = 0
        for x in range(0, w, step):
            if px[x, y] < 235:
                c += 1
        ink.append(c)

    y0, y1 = int(h * lo), int(h * hi)
    best = cur = 0
    best_at = y0
    for y in range(y0, y1):
        if ink[y] == 0:
            cur += 1
            if cur > best:
                best, best_at = cur, y - cur + 1
        else:
            cur = 0
    return best / scale, best_at / scale, scale


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        sys.exit(__doc__)
    target = args[0]
    thresh = 70.0
    lo, hi = 0.40, 0.92
    for a in sys.argv[1:]:
        if a.startswith("--thresh"):
            thresh = float(a.split("=")[-1] if "=" in a else sys.argv[sys.argv.index(a) + 1])
        if a.startswith("--lo"):
            lo = float(a.split("=")[-1] if "=" in a else sys.argv[sys.argv.index(a) + 1])
        if a.startswith("--hi"):
            hi = float(a.split("=")[-1] if "=" in a else sys.argv[sys.argv.index(a) + 1])

    files = sorted(glob.glob(os.path.join(target, "*.png"))) if os.path.isdir(target) else [target]
    if not files:
        sys.exit("没找到 png：%s" % target)

    bad = []
    print("%-14s %10s %10s" % ("page", "gap(px)", "start(y)"))
    for f in files:
        gap, at, scale = scan(f, thresh, lo, hi)
        flag = ""
        if gap > thresh:
            flag = "  [WARN]"
            bad.append((os.path.basename(f), round(gap)))
        print("%-14s %10.0f %10.0f%s" % (os.path.basename(f)[:-4], gap, at, flag))

    print("\n缩放比 %.2f，阈值 %.0f 幻灯片像素（40%%–92%% 区间）" % (scale, thresh))
    if bad:
        print("需加高的页 %d 张：%s" % (len(bad), ", ".join("%s(%d)" % b for b in bad)))
        print("修法：SVG 页按 k 倍纵向拉伸 y/y1/y2/cy/height 与 viewBox 高；表格页加高 height；列表页加大 paddingTop/Bottom")
    else:
        print("全部通过")


if __name__ == "__main__":
    main()
