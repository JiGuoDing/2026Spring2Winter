# -*- coding: utf-8 -*-
"""润色结果自检：ID 对应、字数偏差、禁词、标记保真。"""
import re, sys, os

BASE = os.path.dirname(os.path.abspath(__file__))
IN = os.path.join(BASE, "in")
OUT = os.path.join(BASE, "out")

FORBID = ["赋能", "抓手", "闭环", "数智化", "新范式", "全方位", "深度融合", "有机统一", "打造",
          "首先", "其次", "再次", "值得注意的是", "综上所述", "由此可见", "不难看出",
          "需要指出的是", "必须强调的是", "需要特别说明", "在…方面", "从…角度"]
SOFT = ["首先", "其次", "再次", "值得注意的是", "综上所述", "由此可见", "不难看出",
        "需要指出的是", "必须强调的是", "需要特别说明"]

CJK = re.compile(r"[\u4e00-\u9fff]")


def cjk(s):
    return len(CJK.findall(s))


def parse(path):
    txt = open(path, encoding="utf-8").read()
    lines = [l.rstrip("\n") for l in txt.split("\n")]
    items, order, cur = {}, [], None
    for l in lines:
        m = re.fullmatch(r"@@(P\d{3})@@", l.strip())
        if m:
            cur = m.group(1)
            order.append(cur)
            items[cur] = ""
        elif l.strip() == "":
            continue
        else:
            if cur is None:
                raise SystemExit("非条目内容出现在任何 ID 之前: %r" % l[:40])
            items[cur] = (items[cur] + " " + l.strip()).strip()
    return order, items


def tokens(s):
    """需要原样保留的硬标记"""
    out = []
    out += re.findall(r"\*\*", s)
    out += re.findall(r"【[^】]*】", s)
    out += re.findall(r"\[[A-Z]-\d+\]", s)
    out += re.findall(r"§\d+(?:\.\d+)*", s)
    out += re.findall(r"(?:表|图|附录)\s?[0-9A-E]+(?:-\d+)?", s)
    out += re.findall(r"\d+(?:\.\d+)?", s)
    out += re.findall(r"[A-Za-z][A-Za-z0-9_./\-]*", s)
    out += re.findall(r"^> ", s)
    out += re.findall(r"^\d+\. ", s)
    out += re.findall(r"^- ", s)
    return out


def main():
    ok = True
    tot_in = tot_out = 0
    for b in range(1, 7):
        fi = os.path.join(IN, "batch-%d.md" % b)
        fo = os.path.join(OUT, "batch-%d.md" % b)
        if not os.path.exists(fo):
            print("[MISS] batch-%d.md 未生成" % b)
            ok = False
            continue
        oi, ii = parse(fi)
        oo, io = parse(fo)
        print("=" * 70)
        print("batch-%d  条数 in=%d out=%d" % (b, len(oi), len(oo)))
        if oi != oo:
            print("  [FAIL] ID 序列不一致")
            for a, c in zip(oi, oo):
                if a != c:
                    print("    first diff: in=%s out=%s" % (a, c))
                    break
            ok = False
        bi = sum(cjk(ii[k]) for k in oi)
        bo = sum(cjk(io.get(k, "")) for k in oi)
        tot_in += bi
        tot_out += bo
        pct = (bo - bi) / bi * 100
        flag = "OK" if abs(pct) <= 8 else "FAIL"
        if flag == "FAIL":
            ok = False
        print("  汉字数 in=%d out=%d  浮动 %+.1f%%  [%s]" % (bi, bo, pct, flag))
        for k in oi:
            a, c = ii[k], io.get(k, "")
            na, nc = cjk(a), cjk(c)
            d = (nc - na) / na * 100 if na else 0
            if abs(d) > 15:
                print("  [LEN] %s  %d → %d  (%+.1f%%)" % (k, na, nc, d))
                ok = False
            for w in SOFT:
                if w in c:
                    print("  [WORD] %s 含套式词「%s」" % (k, w))
            if "——" in c and c.count("——") > 1:
                print("  [DASH] %s 破折号 %d 处" % (k, c.count("——")))
            if c.count("——") > 1:
                ok = False
            # 硬标记保真
            ta, tc = tokens(a), tokens(c)
            from collections import Counter
            ca, cc = Counter(ta), Counter(tc)
            miss = ca - cc
            if miss:
                print("  [TOKEN] %s 丢失: %s" % (k, dict(miss)))
                ok = False
            add = cc - ca
            if add:
                print("  [TOKEN+] %s 新增: %s" % (k, dict(add)))
            # 引号字符一致性（原文用直引号）
            if c.count('"') != a.count('"') or c.count("\u201c") or c.count("\u201d"):
                print("  [QUOTE] %s 引号字符不符：直引号 %d→%d，弯引号 %d" %
                      (k, a.count('"'), c.count('"'), c.count("\u201c") + c.count("\u201d")))
                ok = False
    print("=" * 70)
    print("总汉字 in=%d out=%d  浮动 %+.1f%%" % (tot_in, tot_out, (tot_out - tot_in) / tot_in * 100))
    print("结果:", "PASS" if ok else "有问题")


main()
