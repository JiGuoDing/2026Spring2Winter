# -*- coding: utf-8 -*-
"""润色版一致性核验：结构、表格、占位符、禁词、字数。"""
import re, sys

A = r"Q:/workspace/2026Spring2Winter/ThatsNOTMyBusiness/国电南自项目-技术平台/交付物/多租户平台架构设计方案-v0.1.md"
B = r"Q:/workspace/2026Spring2Winter/ThatsNOTMyBusiness/国电南自项目-技术平台/交付物/多租户平台架构设计方案-v0.1-润色版.md"

a = open(A, encoding="utf8").read()
b = open(B, encoding="utf8").read()
la, lb = a.split("\n"), b.split("\n")

print("行数 %d -> %d" % (len(la), len(lb)))
print("表格行 %d -> %d" % (sum(1 for l in la if l.strip().startswith("|")),
                          sum(1 for l in lb if l.strip().startswith("|"))))
ta = [l for l in la if l.strip().startswith("|")]
tb = [l for l in lb if l.strip().startswith("|")]
diff_t = [i for i, (x, y) in enumerate(zip(ta, tb)) if x != y]
print("表格内容差异行:", len(diff_t))

ha = [l for l in la if l.startswith("#")]
hb = [l for l in lb if l.startswith("#")]
print("标题数 %d -> %d  完全一致: %s" % (len(ha), len(hb), ha == hb))

cjk = lambda s: len(re.findall(r"[\u4e00-\u9fa5]", s))
print("汉字总数 %d -> %d (%+.1f%%)" % (cjk(a), cjk(b), (cjk(b) - cjk(a)) / cjk(a) * 100))

for tag, pat in (("占位符", r"【待确认-[TI]\d\d"), ("表号引用", r"表\s*\d+-\d+"),
                 ("节引用", r"§\d+(\.\d+)?"), ("来源编号", r"\[[A-F]-\d+\]")):
    print("%s %d -> %d" % (tag, len(re.findall(pat, a)), len(re.findall(pat, b))))

bad = ["赋能", "抓手", "闭环", "数智化", "新范式", "全方位", "深度融合", "有机统一", "打造",
       "生产控制大区", "管理信息大区", "非控制区", "安全区Ⅰ",
       "值得注意的是", "综上所述", "由此可见", "不难看出", "需要指出的是"]
for w in bad:
    n = b.count(w)
    if n:
        print("!! 禁用/套式词", w, n)

print("破折号 —— 出现次数 %d -> %d" % (a.count("——"), b.count("——")))
print("单段超过 120 汉字的行:", sum(1 for l in lb if cjk(l) > 120))
print("单段最长汉字数:", max(cjk(l) for l in lb))
