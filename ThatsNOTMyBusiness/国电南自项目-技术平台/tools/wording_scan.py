# -*- coding: utf-8 -*-
"""口径扫描：检查禁用表述与必守口径。

用途：本项目的技术口径一旦写错（比如把"管理信息区（安全Ⅲ区）"写成"III 区"、
把 109.5 人月写成 110 人月），对外材料就出问题。每次改完 md / slide / html 都跑一遍。

用法：
    python tools/wording_scan.py <文件或目录> [...]
    python tools/wording_scan.py 交付物 --ext .md,.slide,.html

退出码：0 干净；1 有命中。
"""
import sys, os, re, io

# (正则, 说明, 严重度)  BAN=必须为 0；SOFT=提示
RULES = [
    (r"III\s*区|III区", "半角罗马数字，应为全角「Ⅲ区」", "BAN"),
    (r"(?<![\d.])110\s*人月", "人月口径错误，应为 109.5 人月", "BAN"),
    (r"80%\s*租户|约\s*80%\s*的租户", "应为「约 80% 的二级租户」", "BAN"),
    (r"省一半|省掉一半", "成本口径不成立", "BAN"),
    (r"14\s*号令", "只能在沿革/术语对照/参考来源里出现，不得作为现行依据（现行只写 27 号令）", "SOFT"),
    (r"(?<!接入)三区(?!域)", "分区不叫「三区」，写生产控制区/管理信息区", "BAN"),
    (r"一至四级隔离|一到四级隔离|一到四级的隔离", "应为 L0/L1/L2/L3 四档（「L0–L3 四级隔离」是正确用法）", "BAN"),
    (r"生产控制区.{0,12}(部署|运行)平台|平台.{0,8}部署在.{0,6}(Ⅰ区|Ⅱ区|生产控制区)",
     "平台不得进生产控制区", "BAN"),
    (r"回写.{0,6}(控制指令|遥控|遥调)", "平台不回写控制类指令，注意上下文是否表述为禁止", "SOFT"),
    # 文风禁词（润色与对外材料共用）
    (r"赋能|抓手|闭环|数智化|新范式|全方位|深度融合|有机统一|打造", "空话套话", "SOFT"),
    (r"我们公司|甲方|乙方", "自称统一为我方/客户", "SOFT"),
    (r"首先|其次|综上所述|由此可见|不难看出|值得注意的是", "模板化连接词", "SOFT"),
]

DEFAULT_EXT = (".md", ".slide", ".html", ".txt")
SKIP_DIR = {".git", "node_modules", ".cache", ".slidep", "preview", "assets", "in", "out"}
# 交接文档与设计基线里会故意引用"错误写法"作反例，扫它们必然误报
SKIP_FILE = {"HANDOFF.md", "DESIGN.md", "00-任务说明.md"}


def walk(target, exts):
    if os.path.isfile(target):
        yield target
        return
    for root, dirs, files in os.walk(target):
        dirs[:] = [d for d in dirs if d not in SKIP_DIR]
        for f in sorted(files):
            if f in SKIP_FILE:
                continue
            if os.path.splitext(f)[1].lower() in exts:
                yield os.path.join(root, f)


def main():
    args = [a for a in sys.argv[1:]]
    if not args:
        sys.exit(__doc__)
    exts = DEFAULT_EXT
    targets = []
    for a in args:
        if a.startswith("--ext"):
            v = a.split("=", 1)[1] if "=" in a else ""
            if v:
                exts = tuple(x if x.startswith(".") else "." + x for x in v.split(","))
        else:
            targets.append(a)
    if not targets:
        targets = ["."]

    ban = soft = 0
    for t in targets:
        for path in walk(t, exts):
            try:
                lines = io.open(path, encoding="utf-8", errors="ignore").read().splitlines()
            except OSError:
                continue
            hits = []
            for i, line in enumerate(lines, 1):
                for pat, why, sev in RULES:
                    if re.search(pat, line):
                        hits.append((i, sev, why, line.strip()[:110]))
            if hits:
                print("\n=== %s ===" % path.replace("\\", "/"))
                for i, sev, why, txt in hits:
                    mark = "BAN " if sev == "BAN" else "soft"
                    print("  %-4s L%-5d %s\n        %s" % (mark, i, why, txt))
                    if sev == "BAN":
                        ban += 1
                    else:
                        soft += 1

    print("\n—— 汇总：BAN %d 处，soft %d 处 ——" % (ban, soft))
    if ban:
        print("BAN 必须清零后再交付。")
    elif soft:
        print("soft 逐条判断：术语性三连、引用原文、表格内容可保留。")
    else:
        print("干净。")
    sys.exit(1 if ban else 0)


if __name__ == "__main__":
    main()
