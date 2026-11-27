"""按对象折算缓存收益（只做算术，不跑实验）。"""
import csv
import json
import statistics
from pathlib import Path

CAL = Path("dataset/events/real_calibration_300.csv")
rows = list(csv.DictReader(CAL.open(encoding="utf-8")))
st = {k: [float(r[k]) for r in rows] for k in
      ("t_plan_ms", "t_rag_ms", "t_act_ms", "t_resp_ms", "t_total_ms")}
p50 = {k: sorted(v)[len(v) // 2] for k, v in st.items()}
mean = {k: statistics.fmean(v) for k, v in st.items()}

print("阶段  p50(s)  mean(s)  占总时长(mean)")
for k in ("t_plan_ms", "t_rag_ms", "t_act_ms", "t_resp_ms"):
    print(f"{k:12s} {p50[k]/1000:8.3f} {mean[k]/1000:8.3f}  {100*mean[k]/mean['t_total_ms']:8.4f}%")
print(f"{'total':12s} {p50['t_total_ms']/1000:8.3f} {mean['t_total_ms']/1000:8.3f}  100%")

print("\n命中单个阶段能省多少（按 p50 口径）：")
for k in ("t_plan_ms", "t_resp_ms", "t_rag_ms", "t_act_ms"):
    print(f"  只省 {k:12s} = {p50[k]/1000:8.3f} s = {100*p50[k]/p50['t_total_ms']:7.3f}% of total")

print("\n按 M2 各基线的有效命中率折算的期望节省（全链路复用，p50 total 口径）：")
pol = [("ttl_short", 0.462, 0.837), ("ttl_mid", 0.766, 0.685),
       ("ttl_long", 0.905, 0.403), ("semantic", 0.982, 0.646),
       ("oracle", 0.801, 1.0)]
T = p50["t_total_ms"] / 1000
for name, hit, valid in pol:
    eff = hit * valid
    print(f"  {name:9s} 命中{hit:6.1%} 有效率{valid:6.1%} -> 有效复用{eff:6.1%}  "
          f"期望省 {eff*T:6.1f} s/请求  误用 {hit*(1-valid):6.1%}")

print("\ntoken 折算（p50 token_cost=3686）：")
toks = [int(r["token_cost"]) for r in rows]
tp50 = sorted(toks)[len(toks)//2]
for name, hit, valid in pol:
    eff = hit * valid
    print(f"  {name:9s} 期望省 token ≈ {eff*tp50:6.0f}/请求")
