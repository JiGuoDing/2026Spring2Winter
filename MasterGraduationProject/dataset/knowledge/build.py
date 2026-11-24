"""P2 版本化知识文档层生成器。

产出：
  docs.jsonl            2,000 篇文档 x 3 个版本 = 6,000 行
  version_changes.jsonl 版本间块级变更（下游事件层输入）
  MANIFEST.json         文件 sha256 与行数

约束：
  * 只读 dataset/{schema,config,contracts,common}，只写 dataset/knowledge/。
  * 所有随机来自 common.seeds.rng("knowledge", <doc_id>)；同参数重跑字节一致。
  * 块 ID 由 common.ids.block_id 生成，跨版本稳定。
  * version_changes 由三个版本的块哈希逐块 diff 得出，不另写规则，保证与 docs 自洽。
    其中 modify_* 的块在 from/to 两版都存在且 hash 不同；add_chunk 只在 to 版存在；
    delete_chunk 只在 from 版存在（块已删除，不可能在两版都有 hash）。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from common import ids, io, seeds  # noqa: E402

KN = ROOT / "knowledge"
PARAMS = io.read_json(ROOT / "config" / "params.json")
KN_PARAMS = PARAMS["knowledge"]
TABLES = io.read_json(ROOT / "contracts" / "tables.json")["tables"]
LINEAGE = io.read_json(ROOT / "contracts" / "lineage.json")
EDGES = sorted(LINEAGE["edges"], key=lambda e: (e["from"], e["to"], e["kind"]))
CHAIN = LINEAGE["three_hop_chain"]
TB_BY_ID = {t["table_id"]: t for t in TABLES}

VERSION_AT = {
    1: "2024-05-15T00:00:00Z",
    2: "2024-05-15T06:00:00Z",
    3: "2024-05-15T12:00:00Z",
}

DOMAINS = ("sales", "supply", "finance", "ops", "meta")
DOMAIN_ZH = {
    "sales": "销售",
    "supply": "供应链",
    "finance": "财务",
    "ops": "运营",
    "meta": "元数据",
}

KIND_ZH = {"dim": "维度表", "fact": "事实表", "agg": "汇总表", "log": "日志表"}
GRAIN_ZH = {
    "实体": "一行一个实体",
    "事件": "一行一个业务事件",
    "业务周期": "一行一个统计周期",
    "调用": "一行一次系统调用",
}

SUBJECT = {
    "t01": "日期维", "t02": "区域维", "t03": "渠道维", "t04": "客户维",
    "t05": "商品维", "t06": "门店维", "t07": "员工维", "t08": "促销活动维",
    "t09": "订单", "t10": "订单明细", "t11": "日销售", "t12": "退货",
    "t13": "退款", "t14": "支付", "t15": "发票", "t16": "发货",
    "t17": "配送", "t18": "库存", "t19": "库存快照", "t20": "库存移动",
    "t21": "变价", "t22": "促销核销", "t23": "营销触达", "t24": "点击",
    "t25": "会话", "t26": "线索", "t27": "报价", "t28": "合同",
    "t29": "订阅", "t30": "续费", "t31": "流失", "t32": "工单",
    "t33": "SLA 事件", "t34": "用量", "t35": "互动", "t36": "预算",
    "t37": "目标", "t38": "预测", "t39": "回款", "t40": "采购订单",
    "t41": "质检", "t42": "成本", "t43": "日销售汇总",
    "t44": "月度 GMV 汇总", "t45": "区域份额", "t46": "渠道结构",
    "t47": "商品排名", "t48": "客户 LTV", "t49": "队列留存",
    "t50": "转化漏斗", "t51": "SLA 汇总", "t52": "成本拆解",
    "t53": "预测误差", "t54": "库存周转", "t55": "查询审计",
    "t56": "ETL 运行", "t57": "访问审计", "t58": "指标变更",
    "t59": "结构变更", "t60": "回填",
}

DOMAIN = {
    "t01": "meta", "t02": "sales", "t03": "sales", "t04": "sales",
    "t05": "supply", "t06": "ops", "t07": "ops", "t08": "sales",
    "t09": "sales", "t10": "sales", "t11": "sales", "t12": "sales",
    "t13": "finance", "t14": "finance", "t15": "finance", "t16": "supply",
    "t17": "supply", "t18": "supply", "t19": "supply", "t20": "supply",
    "t21": "sales", "t22": "sales", "t23": "sales", "t24": "sales",
    "t25": "sales", "t26": "sales", "t27": "sales", "t28": "sales",
    "t29": "sales", "t30": "sales", "t31": "sales", "t32": "ops",
    "t33": "ops", "t34": "ops", "t35": "ops", "t36": "finance",
    "t37": "finance", "t38": "finance", "t39": "finance", "t40": "supply",
    "t41": "supply", "t42": "finance", "t43": "sales", "t44": "sales",
    "t45": "sales", "t46": "sales", "t47": "sales", "t48": "sales",
    "t49": "sales", "t50": "sales", "t51": "ops", "t52": "finance",
    "t53": "finance", "t54": "supply", "t55": "meta", "t56": "meta",
    "t57": "meta", "t58": "meta", "t59": "meta", "t60": "meta",
}

# ---------------------------------------------------------------- 字段语义词典
# cat: num 度量 / text 文本 / time 时间 / flag 标记 / key 关联 / code 码值 / log 审计
FIELD_SPEC = {
    "quantity": dict(zh="数量", unit="件", cat="num",
        meaning="该业务事件记录的计量数量，允许小数以兼容称重或计时口径",
        boundary="赠品与退货行同样计数，按件汇总前先确认是否含赠品；与金额指标联动时按行金额加权"),
    "amount": dict(zh="金额", unit="元", cat="num",
        meaning="该业务事件对应的应计金额，含税与否以表级约定为准",
        boundary="多币种行不能直接相加，需先按 currency_code 折算；退款冲减在退款表单独记录"),
    "gross_amount": dict(zh="毛金额", unit="元", cat="num",
        meaning="折让与优惠前的原始金额，通常为含税口径",
        boundary="只反映让利前水平，不能与净额混用；跨币种比较前统一折算并锁定汇率日期"),
    "net_amount": dict(zh="净金额", unit="元", cat="num",
        meaning="扣除折扣并加回税额后的应收金额",
        boundary="与毛金额、折扣额、税额满足恒等式，容差 0.01 元；负数表示冲销行，不能取绝对值"),
    "discount_amount": dict(zh="折扣额", unit="元", cat="num",
        meaning="订单级优惠按行分摊后的折扣金额",
        boundary="券与活动叠加时按分摊比例计入，不可在订单与明细两层重复求和"),
    "tax_amount": dict(zh="税额", unit="元", cat="num",
        meaning="按适用税率计算的销项税额",
        boundary="税率随品类变化，不能用平均税率反推；跨境零税率行税额为 0 而非空值"),
    "unit_price": dict(zh="单价", unit="元/件", cat="num",
        meaning="成交时点的单位价格，含税口径与表级约定一致",
        boundary="历史价格不随变价回写；含税与不含税单价不能直接比较，先统一口径"),
    "cost_amount": dict(zh="成本", unit="元", cat="num",
        meaning="该行对应的结转成本或标准成本",
        boundary="成本版本必须与毛利口径一致；仅财务与供应链授权角色可见，禁止进入公开报表"),
    "currency_code": dict(zh="币种", unit="ISO 4217 代码", cat="code",
        meaning="记账币种",
        boundary="同表可能多币种，聚合前统一折算；未知币种按加载拒绝而非置空"),
    "order_no": dict(zh="业务单号", unit="单号", cat="text",
        meaning="外部可读的业务单号，供人工核对与跨系统对齐",
        boundary="同一单号可对应多行明细，不能当主键；单号可被业务系统重用，跨年比对需带日期"),
    "customer_key": dict(zh="客户键", unit="代理键", cat="key",
        meaning="指向 dim_customer 的代理键，用于把事实行归到客户",
        boundary="含个人信息，仅授权角色可见；SCD 下同一自然人多键，跨期客户数需按自然人去重"),
    "product_key": dict(zh="商品键", unit="代理键", cat="key",
        meaning="指向 dim_product 的代理键，用于归到商品",
        boundary="商品改版会生成新键，跨版本汇总需先映射到商品族；空键行不可静默丢弃"),
    "store_key": dict(zh="门店键", unit="代理键", cat="key",
        meaning="指向 dim_store 的代理键，用于归到门店",
        boundary="闭店门店仍保留键，按在营门店统计时需过滤 is_active=1"),
    "channel_key": dict(zh="渠道键", unit="代理键", cat="key",
        meaning="指向 dim_channel 的代理键，用于归到渠道",
        boundary="线上与线下渠道口径不同，跨渠道汇总前先确认是否含分销"),
    "status_code": dict(zh="状态码", unit="码值", cat="code",
        meaning="业务状态",
        boundary="状态随时间推进，历史快照要按 updated_at 还原；已取消状态是否计收入需在指标卡确认"),
    "is_deleted": dict(zh="删除标记", unit="0/1", cat="flag",
        meaning="该行是否已逻辑删除，1 表示已删除但保留行",
        boundary="查询必须过滤 1，否则重复计数；物理删除不回写该标记"),
    "date_key": dict(zh="日期键", unit="YYYYMMDD 整数", cat="time",
        meaning="业务日期键，关联 dim_date",
        boundary="按业务发生时区落库，不用服务器时间；跨时区订单可能落在相邻两天"),
    "updated_at": dict(zh="更新时间", unit="UTC 时间戳", cat="time",
        meaning="该行最近一次写入的 UTC 时间",
        boundary="同一业务键多行时取最大值；回填会改写该值，版本比对需结合 etl_batch_id"),
    "etl_batch_id": dict(zh="ETL 批次", unit="批次号", cat="text",
        meaning="产生该行的 ETL 批次标识",
        boundary="回填批次可能覆盖可见性，追踪需查 log_backfill；批次号不保证全局唯一"),
    "owner": dict(zh="责任人", unit="账号", cat="text",
        meaning="数据责任人或业务归属人",
        boundary="人员变动不回写历史行；权限申请以此字段为准"),
    "comment": dict(zh="备注", unit="文本", cat="text",
        meaning="自由文本备注",
        boundary="不保证非空，也不含结构化信息，不能作为口径依据或过滤条件"),
    "status": dict(zh="状态", unit="码值", cat="code",
        meaning="实体当前状态",
        boundary="新旧码值可能并存，统计前先映射到统一码表；停用不等于删除"),
    "metric_value": dict(zh="指标值", unit="由 unit_label 指定", cat="num",
        meaning="该周期该维度的聚合指标值",
        boundary="is_partial=1 的周期不能与完整周期直接比较；不同 version_tag 的值不可混用"),
    "metric_delta": dict(zh="指标增量", unit="同指标值", cat="num",
        meaning="与上一周期相比的指标增量",
        boundary="首周期没有基期，增量为空而不是 0；口径变更期需重算基期"),
    "metric_ratio": dict(zh="指标比率", unit="小数 0-1", cat="num",
        meaning="同周期内的占比或比率",
        boundary="分母为 0 时置空；比率不能跨周期直接相加，需回到分子分母重算"),
    "window_start": dict(zh="窗口起点", unit="UTC 时间戳", cat="time",
        meaning="统计窗口起点，左闭",
        boundary="与 window_end 组成左闭右开区间；跨月窗口不能按自然月拆分"),
    "window_end": dict(zh="窗口终点", unit="UTC 时间戳", cat="time",
        meaning="统计窗口终点，右开",
        boundary="终点不包含在窗口内；与明细 date_key 对齐时注意时区偏移"),
    "dimension_key": dict(zh="维度键", unit="代理键", cat="key",
        meaning="汇总行对应的维度代理键",
        boundary="一个汇总行只对应一个维度，混合维度需回到明细重算"),
    "sample_size": dict(zh="样本量", unit="行", cat="num",
        meaning="参与聚合的明细行数",
        boundary="样本量过小时比率不稳定；低于 30 行不建议对外发布"),
    "is_partial": dict(zh="周期完整性", unit="0/1", cat="flag",
        meaning="该周期是否为部分周期，1 表示不完整",
        boundary="部分周期只能与同长度窗口比较；发布前必须显式标注"),
    "version_tag": dict(zh="口径版本", unit="版本号", cat="code",
        meaning="汇总口径版本标签",
        boundary="跨版本对比要先统一口径；旧版本值保留用于审计，不再更新"),
    "source_table": dict(zh="来源表", unit="表名", cat="text",
        meaning="汇总值的来源明细表",
        boundary="来源表结构变更会导致重算失败；血缘以本字段与 lineage 双查"),
    "calc_expr": dict(zh="计算表达式", unit="表达式文本", cat="text",
        meaning="该指标的计算表达式",
        boundary="表达式仅供审计阅读，执行以物化结果为准；修改表达式必须升 version_tag"),
    "refresh_mode": dict(zh="刷新方式", unit="枚举", cat="code",
        meaning="刷新方式，取值为全量或增量",
        boundary="增量刷新依赖水位线，水位回退会造成重复；全量刷新期间禁止下游读取"),
    "unit_label": dict(zh="单位标签", unit="文本", cat="text",
        meaning="指标值单位标签",
        boundary="单位随指标口径变化，跨表比较前先核对；缺失单位时按源表默认值处理"),
    "rounding": dict(zh="舍入规则", unit="规则文本", cat="text",
        meaning="展示层舍入规则",
        boundary="只在展示层生效，聚合计算保留原始精度；四舍五入与银行家舍入不可混用"),
    "name": dict(zh="名称", unit="文本", cat="text",
        meaning="实体或业务对象的可读名称",
        boundary="名称可重复且允许改名，不能当业务主键；检索时同时匹配 code"),
    "code": dict(zh="编码", unit="码值", cat="code",
        meaning="跨系统对齐用的稳定编码",
        boundary="编码一经发布不复用；历史编码保留在码表，停用编码不删除"),
    "short_name": dict(zh="简称", unit="文本", cat="text",
        meaning="报表展示用简称",
        boundary="仅用于展示，不参与关联或过滤；简称可能重名"),
    "category": dict(zh="分类", unit="码值", cat="code",
        meaning="业务分类",
        boundary="分类随码表版本调整，历史行不自动回填；跨版本分析需固定码表版本"),
    "valid_from": dict(zh="生效时间", unit="UTC 时间戳", cat="time",
        meaning="SCD 记录的生效时间，闭区间起点",
        boundary="与 valid_to 配合使用；同一业务键的区间不得重叠"),
    "valid_to": dict(zh="失效时间", unit="UTC 时间戳", cat="time",
        meaning="SCD 记录的失效时间，开区间终点",
        boundary="空值表示当前有效；按历史时点关联时用 valid_from <= t < valid_to"),
    "region_code": dict(zh="区域编码", unit="码值", cat="code",
        meaning="区域编码，与 dim_region.code 对齐",
        boundary="区域调整会产生新编码，历史事实保留旧编码；跨年区域对比需先映射"),
    "channel_code": dict(zh="渠道编码", unit="码值", cat="code",
        meaning="渠道编码，与 dim_channel.code 对齐",
        boundary="渠道合并后旧编码仍可查询；线上线下的退款归属渠道不同"),
    "description": dict(zh="描述", unit="文本", cat="text",
        meaning="自由文本描述",
        boundary="非结构化，不能用于过滤或聚合；内容可能为空或过期"),
    "level": dict(zh="层级", unit="整数", cat="num",
        meaning="层级深度，根节点从 1 开始",
        boundary="层级调整会改变汇总路径；递归查询需限制深度防止环"),
    "parent_id": dict(zh="父节点", unit="代理键", cat="key",
        meaning="父节点代理键，根节点为空",
        boundary="根节点为空而非 0；递归展开前先校验环"),
    "sort_order": dict(zh="排序号", unit="整数", cat="num",
        meaning="展示排序号，不保证连续",
        boundary="排序号可重复，不能用于分页游标；调整不影响业务口径"),
    "is_active": dict(zh="有效标记", unit="0/1", cat="flag",
        meaning="该实体当前是否有效，0 表示停用",
        boundary="停用实体仍可能被历史事实引用；按当前口径统计时才过滤"),
    "ext_attr": dict(zh="扩展属性", unit="JSON 文本", cat="text",
        meaning="扩展属性，JSON 文本",
        boundary="结构不固定，不能作为稳定字段查询；解析失败按空对象处理并告警"),
    "event_type": dict(zh="事件类型", unit="码值", cat="code",
        meaning="事件类型，取值为 query、export、ddl 等",
        boundary="新增事件类型先改码表；枚举值大小写敏感"),
    "actor": dict(zh="操作主体", unit="账号", cat="text",
        meaning="发起操作的主体账号或服务名",
        boundary="含账号标识，对外输出需脱敏；服务账号与自然人账号分开统计"),
    "object_id": dict(zh="对象键", unit="代理键", cat="key",
        meaning="被操作对象的代理键",
        boundary="不同事件类型指向的对象表不同，需结合 event_type 解释"),
    "before_value": dict(zh="变更前值", unit="数值", cat="num",
        meaning="变更前数值",
        boundary="仅数值型变更记录该字段，结构变更用 before_value 为空"),
    "after_value": dict(zh="变更后值", unit="数值", cat="num",
        meaning="变更后数值",
        boundary="与 before_value 成对读取；缺失一侧视为记录不完整"),
    "duration_ms": dict(zh="耗时", unit="毫秒", cat="num",
        meaning="调用耗时，单位毫秒",
        boundary="含排队时间，不能直接当计算耗时；P99 比均值更能暴露长尾"),
    "error_code": dict(zh="错误码", unit="码值", cat="code",
        meaning="错误码，成功时为空",
        boundary="空值表示成功而非缺失；错误码文本随版本调整，统计按码值前缀归类"),
    "statement_hash": dict(zh="语句哈希", unit="哈希", cat="text",
        meaning="语句归一化后的哈希，用于聚类",
        boundary="哈希不可逆，不能还原原文；同一语义的不同写法可能得到不同哈希"),
    "ip_hash": dict(zh="IP 哈希", unit="哈希", cat="text",
        meaning="来源 IP 的加盐哈希",
        boundary="加盐值定期轮换，跨期不可比；禁止反查原始 IP"),
    "user_agent": dict(zh="客户端标识", unit="文本", cat="text",
        meaning="客户端标识字符串",
        boundary="可伪造且格式松散，只能做粗粒度分类；含版本号需截断"),
    "trace_id": dict(zh="链路 ID", unit="十六进制", cat="key",
        meaning="链路追踪 ID",
        boundary="一次请求一个 ID，跨服务可关联；日志采样时可能缺失"),
    "span_id": dict(zh="Span ID", unit="十六进制", cat="key",
        meaning="链路内 span ID",
        boundary="只在单条链路内唯一；与 trace_id 联合使用"),
    "payload_size": dict(zh="负载大小", unit="字节", cat="num",
        meaning="请求或响应体大小，单位字节",
        boundary="压缩前后口径不同，统计前确认；大字段截断会低估"),
    "retry_count": dict(zh="重试次数", unit="次", cat="num",
        meaning="重试次数",
        boundary="首次调用记 0；重试成功仍保留次数，用于稳定性分析"),
}

CAT_ZH = {
    "num": "度量值", "text": "文本属性", "time": "时间属性", "flag": "布尔标记",
    "key": "键值", "code": "码值", "log": "审计字段",
}
CAT_USE = {
    "num": "度量与汇总（如 SUM、AVG）",
    "text": "展示、检索与人工核对",
    "time": "时间过滤、分区裁剪与版本定位",
    "flag": "过滤、有效性判断与质量校验",
    "key": "维表关联与粒度对齐",
    "code": "码值映射与跨系统对齐",
    "log": "审计追踪与变更回放",
}

MEASURE_FIELDS = (
    "quantity", "amount", "gross_amount", "net_amount", "discount_amount",
    "tax_amount", "unit_price", "cost_amount", "metric_value",
    "metric_delta", "metric_ratio",
)
MEASURE_SHORT = {
    "quantity": "数量", "amount": "金额", "gross_amount": "毛金额",
    "net_amount": "净金额", "discount_amount": "折扣额", "tax_amount": "税额",
    "unit_price": "单价", "cost_amount": "成本", "metric_value": "指标值",
    "metric_delta": "指标增量", "metric_ratio": "指标比率",
}
MEASURE_SEM = {
    "quantity": "业务量规模",
    "amount": "应计金额规模",
    "gross_amount": "让利前收入规模",
    "net_amount": "净收入规模",
    "discount_amount": "让利力度",
    "tax_amount": "税负规模",
    "unit_price": "成交价格水平",
    "cost_amount": "成本规模",
    "metric_value": "预聚合指标水平",
    "metric_delta": "环比变化幅度",
    "metric_ratio": "结构占比",
}

# ---------------------------------------------------------------- 小工具
PARAM_RE = re.compile(
    r"(默认聚合窗口|取值长度上限|默认回溯|抽样校验比例|码表取值上限|建议按|默认统计窗口|单次返回上限|计划覆盖|影响下游表数)"
    r" (\d+)( 天| 字符|%| 个| 行| 张)"
)
BUMP = {
    2: 3, 3: 5, 5: 10, 7: 14, 8: 12, 10: 20, 14: 21, 20: 30, 30: 45,
    32: 64, 45: 60, 60: 90, 64: 128, 90: 120, 120: 180, 128: 256,
    180: 240, 256: 512, 500: 800, 1000: 2000, 2000: 5000, 5000: 8000,
}


def _next_number(n: int) -> int:
    if n in BUMP:
        return BUMP[n]
    return n + max(1, n // 4)


def _bump_number(text: str) -> str:
    m = PARAM_RE.search(text)
    if not m:
        raise AssertionError(f"p01 缺少可修改的数字参数：{text[:40]}")
    old = int(m.group(2))
    new = _next_number(old)
    if new == old:
        new += 1
    return text[: m.start(2)] + str(new) + text[m.end(2):]


def _rephrase(text: str, r, salt: int) -> str:
    """改写表述但保持语义；保证返回文本与入参不同且在长度上限内。"""
    opts = [
        lambda t: "现行口径：" + t,
        lambda t: t + "以上说明以 2024-05 口径评审记录为准。",
        lambda t: t.replace("，", "；", 1) if "，" in t else "口径备注：" + t,
        lambda t: t.replace("默认", "当前默认", 1) if "默认" in t else "口径备注：" + t,
        lambda t: t.replace("该字段", "本字段", 1) if "该字段" in t else "（2024-05 复核）" + t,
    ]
    order = list(range(len(opts)))
    r.shuffle(order)
    for i in order:
        cand = opts[i](text)
        if cand != text and len(cand) <= 220:
            return cand
    raise AssertionError(f"salt={salt} 无法改写：{text[:40]}")


def _chk(doc_id: str, p: int, text: str) -> str:
    if not 60 <= len(text) <= 220:
        raise AssertionError(f"{doc_id}#p{p:02d} 长度 {len(text)} 越界: {text}")
    return text


def _p(*texts) -> str:
    return "".join(texts)


def _list(items, limit: int = 3) -> str:
    items = list(items)
    if not items:
        return "无"
    head = "、".join(items[:limit])
    if len(items) > limit:
        head += "等"
    return head


def _pk(tb) -> str:
    for f in tb["fields"]:
        if f["pk"]:
            return f["name"]
    return tb["fields"][0]["name"]


def _date_field(tb) -> str:
    for f in tb["fields"]:
        if f["name"] == "date_key":
            return "date_key"
    return _pk(tb)


def _fk_names(tb) -> list[str]:
    return [f["name"] for f in tb["fields"] if f["name"].endswith("_key") and not f["pk"]]


DIM_KEY = {
    "t01": "date_key", "t02": "region_code", "t03": "channel_key",
    "t04": "customer_key", "t05": "product_key", "t06": "store_key",
    "t07": "employee_key", "t08": "promotion_key",
}


def _edge_key(a: str, b: str) -> str:
    """取 a -> b 这条血缘边在 b 侧实际存在的连接键。"""
    cand = DIM_KEY.get(a)
    names = {x["name"] for x in TB_BY_ID[b]["fields"]}
    if cand and cand in names:
        return cand
    fks = _fk_names(TB_BY_ID[b])
    return fks[0] if fks else "date_key"


def _sample_fields(tb, n: int = 4) -> str:
    names = []
    for f in tb["fields"]:
        if f["name"] not in names:
            names.append(f["name"])
        if len(names) >= n:
            break
    return "、".join(names)


def _up(tid: str) -> list[dict]:
    return [e for e in EDGES if e["to"] == tid]


def _down(tid: str) -> list[dict]:
    return [e for e in EDGES if e["from"] == tid]


def _tb_name(tid: str) -> str:
    return TB_BY_ID[tid]["name"]


def _tb_subject(tid: str) -> str:
    return SUBJECT[tid]


def _grain(tb) -> str:
    return GRAIN_ZH.get(tb["grain"], "一行一条记录")


def _field_spec(f: dict) -> dict:
    if f["pk"]:
        return dict(zh="主键", unit="代理键", cat="key",
                    meaning="该行的代理主键，按加载批次单调生成",
                    boundary="仅用于行定位，不承载业务含义；跨快照不保证连续，禁止用于业务排序")
    if f["name"] in FIELD_SPEC:
        return FIELD_SPEC[f["name"]]
    if f["name"].endswith("_id"):
        return dict(zh="代理键", unit="代理键", cat="key",
                    meaning="指向父级对象的代理键",
                    boundary="关联前先确认父表粒度；空键行需单独计入质量报表")
    return dict(zh=f["name"], unit="依业务定义", cat="text",
                meaning=f"该表的 {f['name']} 属性，取值以加载校验为准",
                boundary="非核心字段，口径以表级说明为准；变更时不影响主指标")


# ---------------------------------------------------------------- 文案：字段卡
def _field_num_phrase(doc_id: str, cat: str) -> str:
    r = seeds.rng("knowledge", "param|" + doc_id)
    if cat == "num":
        return f"默认聚合窗口 {r.choice((7, 14, 30, 45, 60, 90))} 天"
    if cat in ("flag", "key"):
        return f"抽样校验比例 {r.choice((5, 10, 20))}%"
    if cat == "code":
        return f"码表取值上限 {r.choice((8, 12, 16, 24))} 个"
    if cat in ("time", "log"):
        return f"默认回溯 {r.choice((30, 60, 90, 180))} 天"
    return f"取值长度上限 {r.choice((32, 64, 128, 256))} 字符"


def _field_sentence(spec: dict) -> str:
    cat, meaning, unit = spec["cat"], spec["meaning"], spec["unit"]
    if cat == "num":
        return f"数值含义是{meaning}，单位{unit}"
    if cat == "time":
        return f"记录{meaning}"
    if cat == "flag":
        return f"以{unit}标记{meaning}"
    if cat == "key":
        return f"保存{meaning}"
    if cat == "code":
        return f"以{unit}形式保存{meaning}"
    if cat == "log":
        return f"记录{meaning}，单位{unit}"
    return f"保存{meaning}，以{unit}形式存储"


def _field_p01(spec: dict, form: int, doc_id: str) -> str:
    tb, f = spec["table"], spec["field"]
    s = _field_spec(f)
    param = _field_num_phrase(doc_id, s["cat"])
    null_txt = "允许为空" if f["nullable"] else "非空约束"
    key_hint = _pk(tb)
    subject = _tb_subject(tb["table_id"])
    base = {
        "doc": f"{doc_id} 是{subject}（{tb['name']}）的 {f['name']} 字段",
        "type": f"物理类型 {f['type']}",
        "sent": _field_sentence(s),
        "grain": f"表粒度按{_grain(tb)}",
        "key": f"以 {key_hint} 对齐",
        "param": param,
    }
    if form == 0:
        return _p(base["doc"], "，", base["type"], "，", null_txt, "。该字段",
                  base["sent"], "。", base["grain"], "，取值是单行属性，跨行比较前先",
                  base["key"], "。", base["param"], "。")
    if form == 1:
        return _p("在", subject, "中，", f["name"], "（", doc_id, "）用于",
                  CAT_USE[s["cat"]], "，", base["sent"], "。字段", base["type"], "，",
                  null_txt, "；空值可能携带业务含义，读取时不要默认补零。",
                  base["grain"], "，关联时", base["key"], "。", base["param"], "。")
    if form == 2:
        return _p(f["name"], " 字段（", doc_id, "）位于", subject, "，", base["sent"],
                  "。", null_txt, "，", base["type"], "。该表", _grain(tb),
                  "，同一业务键出现多行时取 updated_at 最大者。", base["param"], "。")
    return _p("字段 ", doc_id, "（", tb["name"], ".", f["name"], "）属于",
              CAT_ZH[s["cat"]], "，", base["sent"], "。", base["type"], "，", null_txt,
              "。按", _grain(tb), "读数，不能跨粒度直接累加。", base["param"], "。")


def _field_p02(spec: dict, form: int) -> str:
    tb, f = spec["table"], spec["field"]
    s = _field_spec(f)
    null_txt = "允许为空" if f["nullable"] else "非空"
    null_use = ("空值表示未采集或不适用，聚合时单独计数"
                if f["nullable"] else "加载层已做非空校验，出现空值视为批次异常")
    key_hint = _pk(tb)
    subject = _tb_subject(tb["table_id"])
    if form == 0:
        return _p("边界与陷阱：", s["boundary"], "。跨表关联前先确认 ", key_hint,
                  " 的基数，避免一对多放大；", null_use,
                  "。对账保留原始精度，只在展示层按业务约定舍入；本段按", subject, "的加载口径复核。")
    if form == 1:
        return _p("使用注意：", s["boundary"], "。该字段", null_txt, "，", null_use,
                  "；用 COALESCE 补默认值会改变统计结果。与其他字段联读时，先按 "
                  "date_key 限定业务日期，再按 ", key_hint, " 关联；本段以", subject,
                  "当前分区为样本复核。")
    return _p(s["boundary"], "。若与下游汇总对账，先按 date_key 与维度键聚合到同一粒度；",
              null_use, "。历史差异通过 updated_at 与 log_backfill 追溯，不直接改历史行；",
              "以上规则适用于", subject, "的全部历史分区。")


# ---------------------------------------------------------------- 文案：白皮书
def _wp_table_p01(tb, wkind: str, form: int) -> str:
    tid = tb["table_id"]
    pk = _pk(tb)
    part = seeds.rng("knowledge", "param|wp_" + tid).choice((7, 14, 30, 60))
    subject = SUBJECT[tid]
    if wkind == "join":
        fks = "、".join(_fk_names(tb)) if _fk_names(tb) else "date_key"
        return _p("《", subject, "关联说明》。该表主键 ", pk, "，外键为 ", fks, "；上游 ",
                  str(len(_up(tid))), " 张、下游 ", str(len(_down(tid))),
                  " 张。建议按 ", str(part), " 天分区扫描，连接前先聚合到本表粒度，避免一对多放大。")
    if wkind == "pitfall":
        return _p("《", subject, "口径陷阱》。该表属于", KIND_ZH[tb["kind"]], "，", _grain(tb),
                  "，主键 ", pk, "，共 ", str(len(tb["fields"])), " 个字段。金额与计数默认不含税、",
                  "不重复计数。建议按 ", str(part), " 天分区扫描，并固定 version_tag 后再跨期比较。")
    if form == 0:
        return _p("《", subject, "表（", tb["name"], "）使用说明》。该表属于",
                  KIND_ZH[tb["kind"]], "，", _grain(tb), "，主键为 ", pk, "，共 ",
                  str(len(tb["fields"])), " 个字段。建议按 ", str(part),
                  " 天分区扫描；读取时先按 date_key 限定日期，再按主键去重。")
    return _p(subject, "（", tb["name"], "）是", KIND_ZH[tb["kind"]], "，",
              _grain(tb), "，主键 ", pk, "。表内保留 ", str(len(tb["fields"])),
              " 个字段，维度外键与度量字段需分开理解。建议按 ", str(part),
              " 天分区扫描，跨分区汇总前先锁定口径版本。")


def _wp_table_p02(tb, wkind: str) -> str:
    tid = tb["table_id"]
    subject = SUBJECT[tid]
    if wkind == "grain":
        pk = _pk(tb)
        return _p(subject, "的行数与分区：按 date_key 做日分区，目标行数约 ", str(tb["rows"]),
                  " 行，主键 ", pk, " 在分区内唯一。读取时先裁剪分区，再按主键去重；",
                  "跨分区汇总要固定 version_tag，不能把不同口径的行直接相加。")
    if wkind == "pitfall":
        msg = {
            "fact": "用 created_at 代替 date_key 归属日期，对明细直接 SUM 金额重复计算优惠，把退款行当正向收入",
            "dim": "不做 valid_from/valid_to 过滤导致重复关联，把 is_active=0 当删除，用 name 代替 code 关联",
            "agg": "汇总后再 join 明细重复计数，混用 version_tag，把 is_partial=1 当完整周期",
            "log": "把 updated_at 当业务时间，用日志表统计业务量，忽略 actor 与 ip_hash 的脱敏边界",
        }[tb["kind"]]
        return _p(subject, "上的高频错误：", msg, "。出现其中任意一条时，先冻结下游汇总并",
                  "回到明细复算，确认后再恢复发布。")
    ups = [e["from"] for e in _up(tid)]
    downs = [e["to"] for e in _down(tid)]
    fks = _fk_names(tb)
    up_txt = _list([f"{_tb_subject(x)}（{x}）" for x in ups]) if ups else "加载任务（无血缘上游）"
    down_txt = _list([f"{_tb_subject(x)}（{x}）" for x in downs]) if downs else "即席查询（无血缘下游）"
    fk_txt = "、".join(fks) if fks else "date_key"
    return _p("本表（", tid, "）的关联关系：上游为", up_txt, "；下游为", down_txt,
              "。维表按 ", fk_txt, " 与 dim_* 关联，事实表之间按 date_key 与业务单号对齐。",
              "若一条维表记录对应多条事实行，先聚合事实再关联，避免行数放大。")


def _wp_table_p03(tb, wkind: str) -> str:
    subject = SUBJECT[tb["table_id"]]
    if wkind == "grain":
        return _p(subject, "的粒度误用：把", _grain(tb), "的行直接与更细粒度明细相加会重复计数；",
                  "需要明细时回到来源事实表，不要从本表下钻。按主键去重后再聚合，并核对 date_key 覆盖率。")
    if wkind == "pitfall":
        return _p(subject, "的对账方法：按 date_key 与主键聚合到同粒度，比对行数、金额恒等式与空值率；",
                  "差异超过 0.5% 时回查上游批次与码表版本，禁止直接改历史行。")
    return _p(subject, "的连接风险：一条维表记录对应多条事实行时，先聚合事实再关联；连接后行数",
              "超过本表 1.05 倍即停止，回查维表历史版本与过滤条件，确认基数后再重跑。")


def _wp_domain(dom: str, angle: str) -> list[str]:
    tabs = [t for t in TABLES if DOMAIN[t["table_id"]] == dom]
    n = len(tabs)
    names = _list([f"{SUBJECT[t['table_id']]}（{t['table_id']}）" for t in tabs], 4)
    part = seeds.rng("knowledge", f"param|wp_domain|{dom}|{angle}").choice((7, 14, 30, 60))
    zh = DOMAIN_ZH[dom]
    if angle == "overview":
        p01 = _p("《", zh, "数据域总览》覆盖 ", str(n), " 张表，包括", names,
                 "。域内主线是把业务事件落到统一日期键与维度键，再向上汇总。建议按 ",
                 str(part), " 天分区扫描，跨表分析先确认粒度再连接。")
        p02 = _p(zh, "域的关联主线是 日期维 → 业务事件 → 汇总表。日期维提供统一的 date_key，",
                 "业务表通过 customer_key、product_key、channel_key 等外键补齐属性；汇总表只读，",
                 "不再回写明细。跨域连接只允许通过日期维与客户维，禁止直接拼两张事实表。")
        p03 = _p("口径与权限：域内指标以 metric 卡为准，金额默认不含税，退款在财务域单独冲减。",
                 "对外交付只给聚合结果，明细需登记用途；", zh,
                 "域的公开字段可进自助报表，客户标识与成本字段按权限分级开放。")
        return [p01, p02, p03]
    if angle == "metrics":
        zh_metrics = {
            "sales": "GMV、净收入、客单价、转化率",
            "supply": "库存周转天数、缺货率、履约时效、采购到货率",
            "finance": "毛利率、回款率、预算执行率、预测偏差",
            "ops": "工单解决时长、SLA 达成率、活跃率、留存率",
            "meta": "血缘覆盖率、码表一致率、快照行数偏差、审计覆盖率",
        }[dom]
        p01 = _p("《", zh, "域关键指标》列出 ", zh_metrics,
                 " 等核心指标。每个指标都绑定来源表、统计窗口与口径版本，建议按 ",
                 str(part), " 天分区扫描后重算，避免直接引用过期汇总。")
        p02 = _p(zh, "域的计算与对账：金额类指标先按业务键去重再 SUM，比率类指标回到分子分母重算，",
                 "不能对已算好的比率取平均。与 agg 表对账时允许 0.5% 差异，超出后回查明细")
        p02 += "。"
        p03 = _p(zh, "域常见误用：把不同 version_tag 的汇总值拼在同一张趋势图；用部分周期与完整周期",
                 "比较；对含退款与不含退款的口径混用。发布前在指标卡登记口径边界与责任人。")
        return [p01, p02, p03]
    if angle == "joins":
        p01 = _p("《", zh, "域关联陷阱》梳理域内 ", str(n), " 张表的连接路径。事实表先按 date_key "
                 "过滤，再按外键关联维表；汇总表只与日期维连接。建议按 ", str(part),
                 " 天分区扫描，连接前先聚合到同一粒度。")
        p02 = _p(zh, "域的多对多放大：订单与明细、退货与退款、发货与配送之间都可能一对多。连接前先按",
                 "业务单号聚合，或给维表加 valid_from/valid_to 条件；连接后行数超过事实表 1.05 倍时",
                 "立即停止并回查基数。")
        p03 = _p(zh, "域的过滤顺序：先过滤事实表的 is_deleted 与日期，再关联维表，最后过滤维表属性。",
                 "把维表过滤条件写在 WHERE 里会把外连接退化为内连接，历史维度行也会被误删。")
        return [p01, p02, p03]
    p01 = _p("《", zh, "域权限与合规》说明域内 ", str(n), " 张表的可见范围。公开字段限于",
             "非敏感业务属性，客户标识、成本与审计字段分级开放。建议按 ", str(part),
             " 天复核一次授权清单。")
    p02 = _p(zh, "域脱敏规则：客户键、IP 哈希、账号在明细层脱敏后再出域；金额字段按角色决定是否",
             "展示到分。导出文件必须带水印与用途登记，禁止把 restricted 字段写入公开报表。")
    p03 = _p(zh, "域审计要求：所有查询写入 log_query_audit，越权访问写入 log_access；权限变更需",
             "在事件层留痕。离职或转岗后 24 小时内回收权限，历史导出文件按保留策略清理。")
    return [p01, p02, p03]


# ---------------------------------------------------------------- 文案：指标卡
def _group_dims(tb) -> str:
    names = {x["name"] for x in tb["fields"]}
    picks = [x for x in ("date_key", "channel_key", "customer_key",
                         "dimension_key", "product_key") if x in names][:3]
    return "、".join(picks) if picks else "date_key"


def _metric_parts(tb, f) -> tuple[str, str, str, str]:
    """返回 (指标名, 聚合式, 去重键, 时间语义)。"""
    if tb["kind"] == "agg":
        name = f"{MEASURE_SHORT[f['name']]}（{_tb_subject(tb['table_id'])}）"
    else:
        name = _tb_subject(tb["table_id"]) + MEASURE_SHORT[f["name"]]
    pk = _pk(tb)
    if f["name"] == "unit_price":
        expr = "SUM(amount) / NULLIF(SUM(quantity), 0)"
    elif f["name"] == "metric_ratio":
        expr = "SUM(metric_ratio * sample_size) / NULLIF(SUM(sample_size), 0)"
    else:
        expr = f"SUM({f['name']})"
    if tb["kind"] == "agg":
        time_sem = "按汇总周期归属，window_start 左闭、window_end 右开"
    else:
        time_sem = "按业务发生时间归属，不按下单时间或入账时间二次调整"
    return name, expr, pk, time_sem


def _metric_p01(spec, form: int) -> str:
    tb, f = spec["table"], spec["field"]
    name, expr, dedup, _ = _metric_parts(tb, f)
    sem = MEASURE_SEM[f["name"]]
    window = seeds.rng("knowledge", "param|" + spec["doc_id"]).choice((7, 30, 90, 180))
    if f["name"] == "unit_price":
        obj = "由 amount 除以 quantity 推导的加权成交单价"
    else:
        obj = FIELD_SPEC.get(f["name"], {}).get("meaning", f["name"])
    if tb["kind"] == "agg":
        return _p("指标 ", spec["doc_id"], "：", name, "。用于衡量",
                  _tb_subject(tb["table_id"]), "的", sem, "，取 ", tb["name"], ".",
                  f["name"], " 按统计周期聚合，字段含义为", obj,
                  "。默认统计窗口 ", str(window), " 天，跨周期比较需重算基期。")
    if form == 0:
        if f["name"] == "unit_price":
            field_txt = "amount 与 quantity 字段"
        else:
            field_txt = f["name"] + " 字段"
        return _p("指标 ", spec["doc_id"], "：", name, "。定义为", _tb_subject(tb["table_id"]),
                  "在统计周期内", sem, "的聚合，度量对象是 ", field_txt, "（",
                  f["type"], "），字段含义为", obj, "。默认统计窗口 ", str(window), " 天。")
    return _p(spec["doc_id"], "（", name, "）衡量", _tb_subject(tb["table_id"]), "的", sem,
              "，取 ", tb["name"], ".", f["name"], " 按周期聚合。该字段口径为", obj,
              "，默认统计窗口 ", str(window), " 天，跨周期比较需重算基期。")


def _metric_p02(spec, form: int) -> str:
    tb, f = spec["table"], spec["field"]
    _, expr, dedup, _ = _metric_parts(tb, f)
    dims = _group_dims(tb)
    if f["name"] == "metric_ratio":
        extra = "分子分母分别汇总后再相除，禁止对行级比率取平均"
    elif f["name"] == "unit_price":
        extra = "按数量加权，不使用简单算术平均"
    else:
        extra = "剔除 is_deleted=1 的行，再按业务键去重"
    if form == 0:
        return _p("计算式：", expr, "，分组维度为 ", dims, "，时间字段用 date_key。去重键为 ",
                  dedup, "；", extra, "。结果保留 2 位小数。")
    return _p("取数写法：SELECT ", dims, "，", expr, " AS metric_value FROM ", tb["name"],
              " WHERE date_key BETWEEN :start AND :end GROUP BY ", dims, "。按 ", dedup,
              " 去重，", extra, "，保留 2 位小数。")


def _metric_p03(spec) -> str:
    tb, f = spec["table"], spec["field"]
    _, _, _, time_sem = _metric_parts(tb, f)
    boundary = FIELD_SPEC.get(f["name"], {}).get("boundary", "口径以字段卡为准")
    if tb["table_id"] in ("t12", "t13"):
        refund = "本表本身是退款或退货口径，计算净收入时应作为冲减项与正向事实表合并"
    elif tb["kind"] == "agg":
        refund = "退款是否冲减以该汇总行 version_tag 的口径为准，跨版本不可直接相减"
    else:
        refund = "退款不直接冲减本指标，净额需在退款表单独计算后合并"
    tail = ("空值不参与聚合，也不补 0" if f["name"] != "metric_ratio"
            else "比率不可跨行直接平均，需回到分子分母")
    if any(x["name"] == "currency_code" for x in tb["fields"]):
        currency = "跨币种先按 currency_code 折算"
    else:
        currency = "汇总表已折算为单一记账币种，跨表比较前先核对币种口径"
    name, _, _, _ = _metric_parts(tb, f)
    return _p(name, "的口径边界：", boundary, "；", refund, "。", time_sem, "。", tail,
              "；样本量不足 30 行时只标注不对外发布。", currency, "，再与 agg 表对账。")


# ---------------------------------------------------------------- 文案：工具卡
PERM_TEXT = {
    "public": ("公开域", "可返回业务明细与聚合结果，不含客户标识与成本字段", "analyst"),
    "staff": ("员工域", "仅返回脱敏后的客户键与金额，导出需登记用途", "staff"),
    "restricted": ("受限域", "只返回聚合结果，明细需审批工单并留存审计", "audit 或 finance_admin"),
}


def _tool_p01(spec, perm: str) -> str:
    rows = seeds.rng("knowledge", "param|" + spec["doc_id"]).choice((500, 1000, 2000, 5000))
    if spec["tool_kind"] == "table":
        tb = spec["table"]
        extra = {
            "dim": "code_prefix（编码前缀，可选）",
            "fact": "region_code、channel_code（可选）",
            "agg": "dimension_key（维度键，可选）",
            "log": "event_type、actor（可选）",
        }[tb["kind"]]
        return _p("工具 ", spec["doc_id"], "（query_", tb["name"], "）用于", SUBJECT[tb["table_id"]],
                  "的", {"dim": "维度取值与属性查询", "fact": "业务明细筛选",
                         "agg": "按周期取汇总值", "log": "审计事件检索"}[tb["kind"]],
                  "。入参：date_from、date_to（UTC 日期，必填）、单次返回上限 ", str(rows),
                  " 行、", extra, "。只读查询，不支持写入或 DDL。")
    a, b = spec["edge"]["from"], spec["edge"]["to"]
    return _p("工具 ", spec["doc_id"], "（join_", a, "_", b, "）用于把", SUBJECT[a], "与",
              SUBJECT[b], "按外键连接后取数。入参：date_from、date_to（必填）、",
              "on_key（连接键，默认 ", _edge_key(a, b),
              "）、单次返回上限 ", str(rows), " 行。只读查询，返回连接后的明细投影。")


def _tool_p02(spec) -> str:
    if spec["tool_kind"] == "table":
        tb = spec["table"]
        cols = _sample_fields(tb, 4)
        order = _pk(tb)
        return _p("返回字段：", cols, " 等 ", str(len(tb["fields"])), " 个字段的投影，按 ",
                  order, " 排序，分页用 offset。结果附带 query_id 与 snapshot_tag，",
                  "便于在 log_query_audit 中回溯本次读取。")
    a, b = spec["edge"]["from"], spec["edge"]["to"]
    return _p("返回：", _tb_name(a), " 与 ", _tb_name(b), " 的连接投影，默认只给主键、",
              "date_key 与 3 个度量字段，行数上限受 limit 约束。连接基数超过 1.05 倍时",
              "返回 warning，提示先聚合再连接。")


def _tool_p03(spec, perm: str) -> str:
    label, mask, scope = PERM_TEXT[perm]
    return _p("工具 ", spec["doc_id"], " 的权限域：", label, "。", mask, "。调用方需持有 ",
              scope, " 角色；越权访问返回 403，并写入 log_access 审计。")


# ---------------------------------------------------------------- 文案：计划卡
def _plan_p01(tb, form: int) -> str:
    tid = tb["table_id"]
    days = seeds.rng("knowledge", "param|plan|" + tid).choice((30, 60, 90, 120))
    goal = {
        "dim": "维度取值核对与属性补全",
        "fact": "明细取数与指标重算",
        "agg": "汇总值对账与趋势复核",
        "log": "变更追溯与异常定位",
    }[tb["kind"]]
    scene = {
        "dim": "新维表接入或码表调整后的回归",
        "fact": "月度经营分析或临时取数",
        "agg": "日报与周报的口径校验",
        "log": "故障复盘与权限审计",
    }[tb["kind"]]
    if form == 0:
        return _p("计划 ", spec_id(tb, "plan"), "：以", SUBJECT[tid], "（", tb["name"],
                  "）为主表完成", goal, "。计划覆盖 ", str(days), " 天，保持", _grain(tb),
                  "，输出按 date_key 与维度键排序。适用场景：", scene, "。")
    return _p("计划 ", spec_id(tb, "plan"), " 面向", scene, "，主表选", SUBJECT[tid], "（",
              tb["name"], "），目标是", goal, "。计划覆盖 ", str(days), " 天，",
              _grain(tb), "，结果按 date_key 升序输出并保留 query_id。")


def spec_id(tb, kind: str) -> str:
    idx = TABLES.index(tb) + 1
    if kind == "plan":
        return ids.plan_id(idx)
    return tb["table_id"]


def _plan_p02(tb) -> str:
    tid = tb["table_id"]
    ups = [e["from"] for e in _up(tid)]
    downs = [e["to"] for e in _down(tid)]
    up_txt = _list([f"{_tb_subject(x)}（{x}）" for x in ups]) if ups else "日期维"
    down_txt = _list([f"{_tb_subject(x)}（{x}）" for x in downs]) if downs else "即席报表"
    keys = "、".join(dict.fromkeys(_edge_key(e["from"], tid) for e in _up(tid))) \
        if _up(tid) else "date_key"
    step2 = (f"2）关联{up_txt}补齐维度属性，连接键为 {keys}；" if _up(tid)
             else "2）本表无血缘上游，直接校验主键与属性完整性；")
    return _p("步骤：1）在 ", tb["name"], " 上按 date_key 过滤并用 ", _pk(tb),
              " 去重，确认行数与主键基数；", step2,
              "3）按 date_key 与维度键聚合，与", down_txt, "对账。")


def _plan_p03(tb) -> str:
    check = {
        "fact": "金额恒等式（gross−discount+tax=net）与主键唯一性",
        "agg": "指标值与明细回算的一致性、is_partial 标记",
        "dim": "维表主键唯一性与 valid_from/valid_to 区间不重叠",
        "log": "事件时间覆盖、actor 与 trace_id 完整性",
    }[tb["kind"]]
    return _p(SUBJECT[tb["table_id"]], "计划的校验：核对", check, "。若关联后行数放大超过 1.05 倍，回查维表是否命中",
              "多条历史版本；若汇总差异超过 0.5%，先查 is_deleted 与回填批次，再复算。")


# ---------------------------------------------------------------- 文案：专题说明
def _note_codebook(tb, form: int) -> list[str]:
    tid = tb["table_id"]
    code_field = "status_code"
    for cand in ("status_code", "status", "event_type", "code", "category",
                 "refresh_mode", "version_tag", "unit_label", "error_code", "level"):
        if any(f["name"] == cand for f in tb["fields"]):
            code_field = cand
            break
    nvals = seeds.rng("knowledge", "param|note|" + tid).choice((8, 12, 16, 24))
    down = len(_down(tid))
    p01 = _p("码表说明：", SUBJECT[tid], "（", tb["name"], "）的 ", code_field,
             " 使用 ", str(nvals), " 个码值，码值一经发布不复用。码值到中文名称的映射以本卡为准，",
             "报表展示用名称、关联与过滤用码值。影响下游表数 ", str(max(1, down)), " 张。")
    p02 = _p("本卡对应", SUBJECT[tid], "的 ", code_field, "。新增码值需先更新码表再回刷事实表，禁止在 SQL 里硬编码中文；",
             "历史行保留旧码值，跨版本统计先映射到统一码表。码表变更需登记 log_schema_change，",
             "并同步检查引用该字段的下游任务。")
    return [p01, p02]


def _note_lineage(edge: dict) -> list[str]:
    a, b = edge["from"], edge["to"]
    keys = _edge_key(a, b)
    pos = ""
    if a in CHAIN and b in CHAIN:
        ia, ib = CHAIN.index(a), CHAIN.index(b)
        if ib == ia + 1:
            pos = f"该边是三跳链 {CHAIN[0]}→{CHAIN[1]}→{CHAIN[2]}→{CHAIN[3]} 的第 {ib} 段。"
    p01 = _p("血缘说明：", SUBJECT[a], "（", a, "）经 ", edge["kind"], " 关系供数给",
             SUBJECT[b], "（", b, "），传递粒度为", _grain(TB_BY_ID[b]), "，连接键为 ",
             keys, "。", pos, "影响下游表数 ", str(max(1, len(_down(b)))), " 张。")
    p02 = _p("断链风险：上游 ", a, " 若延迟或回填，", b, " 的 date_key 覆盖会先出现空洞。",
             "排查顺序为 log_etl_run → log_backfill → 上游主键基数；禁止直接改 ",
             b, " 的历史行，修复应重跑上游分区。")
    return [p01, p02]


def _note_change(tb) -> list[str]:
    tid = tb["table_id"]
    names = [x["name"] for x in tb["fields"]]
    down = len(_down(tid))
    if tb["kind"] in ("fact", "agg"):
        f = next(x for x in ("amount", "metric_value", "quantity") if x in names)
        if f in ("amount",):
            what = "原口径按含税金额统计，新口径改为不含税金额，并对最近 3 个分区重算"
        else:
            what = "原口径按明细行统计，新口径改为按业务键去重后统计，并对最近 3 个分区重算"
        scope = "引用该字段的字段卡、指标卡与下游汇总需同步复核"
    else:
        f = next(x for x in ("status", "code", "category", "event_type") if x in names)
        what = "码值映射由 v1 码表切换到 v2 码表，历史行保留旧码值，仅新增映射关系"
        scope = "引用该码值的字段卡、报表与下游任务需同步复核"
    tail = ("回查税率与折扣分摊" if tb["kind"] in ("fact", "agg")
            else "回查码表版本与映射关系")
    p01 = _p("口径变更记录：", SUBJECT[tid], "的 ", f, " 在 2024-05-15T06:00:00Z 版本中调整。",
             what, "。影响下游表数 ", str(max(1, down)), " 张。")
    p02 = _p(SUBJECT[tid], "的变更影响：", scope, "；比对 v1 与 v2 的 ", f, " 分布，差异超过 0.5% 时",
             tail, "。变更记录写入 log_metric_change，旧口径值保留只读。")
    return [p01, p02]


def _note_quality(tb) -> list[str]:
    tid = tb["table_id"]
    pk = _pk(tb)
    names = [x["name"] for x in tb["fields"]]
    f = next(x for x in ("amount", "metric_value", "quantity") if x in names)
    check = "金额恒等式" if f == "amount" else "指标值与明细回算"
    p01 = _p("质量规则：", SUBJECT[tid], "的主键 ", pk, " 必须唯一，date_key 覆盖率不低于 99%。",
             f, " 字段的非空率低于 95% 时触发告警。影响下游表数 ",
             str(max(1, len(_down(tid)))), " 张。")
    p02 = _p(SUBJECT[tid], "的处置流程：先查 log_etl_run 定位批次，再用 log_backfill 登记回填；回填后重跑唯一性",
             "校验与", check, "，结果写入质量台账。连续两个批次失败时冻结下游汇总并通知责任人。")
    return [p01, p02]


def _note_refresh(tb) -> list[str]:
    tid = tb["table_id"]
    p01 = _p("刷新与分区：", SUBJECT[tid], " 按 date_key 做日分区，保留 36 个月；全量刷新在",
             "每日 02:00 UTC 触发，增量刷新每 15 分钟一次。影响下游表数 ",
             str(max(1, len(_down(tid)))), " 张。")
    p02 = _p(SUBJECT[tid], "的回填约定：回填任务必须写 log_backfill 并标注影响分区；回填期间下游读取可能",
             "看到重复行，需按主键去重。超过 7 天的回填需数据负责人审批，回填完成后重跑质量规则。")
    return [p01, p02]


# ---------------------------------------------------------------- 版本补充块
def _add_p03(spec) -> str:
    if spec["doc_type"] == "field":
        tb = spec["table"]
        down_ids = [e["to"] for e in _down(tb["table_id"])]
        downs = _list([f"{_tb_subject(x)}（{x}）" for x in down_ids]) \
            if down_ids else "相关汇总表"
        return _p("版本联动：", spec["doc_id"], " 的口径调整会传导到", downs,
                  "与引用该字段的指标卡。变更后应重跑", SUBJECT[tb["table_id"]],
                  "的质量规则，并在 version_changes 中登记块级差异；检索侧按 chunk_id 保持引用稳定。")
    tid = spec.get("table_id")
    subject = SUBJECT.get(tid, "本说明")
    return _p("复核记录（", spec["doc_id"], "）：本说明归属", subject, "，最近一次复核覆盖 3 张相关表。若上游表结构",
              "或码表调整，应同步更新本段并在血缘台账登记受影响的下游任务，避免检索命中过期口径。")


# ---------------------------------------------------------------- 文档规格
def _sens_field(tb, f) -> int:
    s = {
        "customer_key": 9, "ip_hash": 10, "user_agent": 7, "actor": 8,
        "cost_amount": 8, "before_value": 6, "after_value": 6,
        "statement_hash": 6, "amount": 5, "net_amount": 5, "gross_amount": 5,
        "discount_amount": 4, "tax_amount": 4, "metric_value": 4,
        "metric_ratio": 4, "metric_delta": 4, "status_code": 3, "order_no": 4,
    }.get(f["name"], 3)
    if tb["kind"] == "log":
        s += 2
    if DOMAIN[tb["table_id"]] == "finance" and f["name"] in ("amount", "net_amount", "cost_amount"):
        s += 1
    return s


def build_specs() -> list[dict]:
    specs: list[dict] = []
    # 1,200 字段卡
    for tb in TABLES:
        for f in tb["fields"]:
            specs.append(dict(doc_id=f["field_id"], doc_type="field",
                              domain=DOMAIN[tb["table_id"]], table=tb, field=f,
                              sens=_sens_field(tb, f)))
    # 150 指标卡
    pairs = [(tb, f) for tb in TABLES if tb["kind"] in ("fact", "agg")
             for f in tb["fields"] if f["name"] in MEASURE_FIELDS]
    pairs = seeds.shuffle(pairs, "knowledge", "metric_pairs")[: KN_PARAMS["metrics"]]
    for i, (tb, f) in enumerate(pairs, 1):
        specs.append(dict(doc_id=ids.metric_id(i), doc_type="metric",
                          domain=DOMAIN[tb["table_id"]], table=tb, field=f,
                          sens=4 + (2 if DOMAIN[tb["table_id"]] == "finance" else 0)
                          + _sens_field(tb, f) // 3))
    # 180 表级白皮书 + 20 域级白皮书
    for i, tb in enumerate(TABLES, 1):
        for k, wkind in enumerate(("grain", "join", "pitfall")):
            specs.append(dict(doc_id=ids.whitepaper_id(3 * (i - 1) + k + 1),
                              doc_type="whitepaper", domain=DOMAIN[tb["table_id"]],
                              table=tb, wp_kind=wkind,
                              sens={"dim": 4, "fact": 5, "agg": 4, "log": 9}[tb["kind"]]
                              + (1 if wkind == "pitfall" else 0)))
    for di, dom in enumerate(DOMAINS):
        for ai, angle in enumerate(("overview", "metrics", "joins", "permission")):
            specs.append(dict(doc_id=ids.whitepaper_id(181 + di * 4 + ai),
                              doc_type="whitepaper", domain=dom, table=None,
                              wp_kind="domain", domain_angle=angle,
                              sens={"sales": 5, "supply": 5, "finance": 7,
                                    "ops": 4, "meta": 8}[dom]
                              + (1 if angle == "permission" else 0)))
    # 100 工具卡：60 表级 + 40 连接
    for i, tb in enumerate(TABLES, 1):
        specs.append(dict(doc_id=ids.tool_id(i), doc_type="tool",
                          domain=DOMAIN[tb["table_id"]], table=tb, tool_kind="table",
                          sens={"dim": 4, "fact": 5, "agg": 5, "log": 9}[tb["kind"]]))
    edges = seeds.shuffle(EDGES, "knowledge", "tool_edges")[:40]
    for j, e in enumerate(edges, 61):
        dom = DOMAIN[e["to"]] if DOMAIN[e["to"]] != "meta" else DOMAIN[e["from"]]
        specs.append(dict(doc_id=ids.tool_id(j), doc_type="tool", domain=dom,
                          table=None, tool_kind="join", edge=e,
                          sens=max({"dim": 4, "fact": 5, "agg": 5, "log": 9}[TB_BY_ID[e["from"]]["kind"]],
                                   {"dim": 4, "fact": 5, "agg": 5, "log": 9}[TB_BY_ID[e["to"]]["kind"]])))
    # 60 计划卡
    for i, tb in enumerate(TABLES, 1):
        specs.append(dict(doc_id=ids.plan_id(i), doc_type="plan",
                          domain=DOMAIN[tb["table_id"]], table=tb,
                          sens={"dim": 4, "fact": 5, "agg": 5, "log": 8}[tb["kind"]]))
    # 290 专题说明
    for i, tb in enumerate(TABLES, 1):
        specs.append(dict(doc_id=ids.note_id(i), doc_type="note",
                          domain=DOMAIN[tb["table_id"]], table=tb, note_kind="codebook",
                          sens={"dim": 3, "fact": 4, "agg": 4, "log": 8}[tb["kind"]]))
    for k, e in enumerate(EDGES, 61):
        dom = DOMAIN[e["to"]] if DOMAIN[e["to"]] != "meta" else DOMAIN[e["from"]]
        specs.append(dict(doc_id=ids.note_id(k), doc_type="note", domain=dom,
                          table=None, note_kind="lineage", edge=e, sens=4))
    for i, tb in enumerate(TABLES, 145):
        specs.append(dict(doc_id=ids.note_id(i), doc_type="note",
                          domain=DOMAIN[tb["table_id"]], table=tb, note_kind="change",
                          sens=5 + (2 if DOMAIN[tb["table_id"]] == "finance" else 0)))
    fact_agg = [t for t in TABLES if t["kind"] in ("fact", "agg")]
    for i, tb in enumerate(fact_agg, 205):
        specs.append(dict(doc_id=ids.note_id(i), doc_type="note",
                          domain=DOMAIN[tb["table_id"]], table=tb, note_kind="quality",
                          sens=4 + (1 if tb["kind"] == "fact" else 0)))
    for i, tb in enumerate(fact_agg[:40], 251):
        specs.append(dict(doc_id=ids.note_id(i), doc_type="note",
                          domain=DOMAIN[tb["table_id"]], table=tb, note_kind="refresh",
                          sens=3 + (1 if tb["kind"] == "fact" else 0)))
    specs.sort(key=lambda s: s["doc_id"])
    assert len(specs) == KN_PARAMS["docs_total"], len(specs)
    return specs


def assign_permissions(specs: list[dict]) -> dict[str, str]:
    """按文档类型固定 70/20/10 配额，同类内按敏感度降序、doc_id 升序排。

    规则是确定性的：配额由 params 规模算出（1200/200/150/100/60/290），
    敏感度只由表类型、业务域与字段名决定，不含随机数。
    """
    out: dict[str, str] = {}
    for dtype in ("field", "whitepaper", "metric", "tool", "plan", "note"):
        rows = [s for s in specs if s["doc_type"] == dtype]
        n = len(rows)
        n_restricted = n * 10 // 100
        n_staff = n * 20 // 100
        ranked = sorted(rows, key=lambda s: (-s["sens"], s["doc_id"]))
        for i, s in enumerate(ranked):
            out[s["doc_id"]] = ("restricted" if i < n_restricted
                                else "staff" if i < n_restricted + n_staff
                                else "public")
    return out


def render_base(spec: dict, perm: str) -> list[str]:
    t = spec["doc_type"]
    doc_id = spec["doc_id"]
    if t == "field":
        form = seeds.rng("knowledge", "form|" + doc_id).randrange(4)
        p2form = seeds.rng("knowledge", "form2|" + doc_id).randrange(3)
        return [_chk(doc_id, 1, _field_p01(spec, form, doc_id)),
                _chk(doc_id, 2, _field_p02(spec, p2form))]
    if t == "whitepaper":
        if spec["wp_kind"] == "domain":
            texts = _wp_domain(spec["domain"], spec["domain_angle"])
        else:
            tb = spec["table"]
            form = seeds.rng("knowledge", "form|" + doc_id).randrange(2)
            texts = [_wp_table_p01(tb, spec["wp_kind"], form),
                     _wp_table_p02(tb, spec["wp_kind"]),
                     _wp_table_p03(tb, spec["wp_kind"])]
        return [_chk(doc_id, i + 1, x) for i, x in enumerate(texts)]
    if t == "metric":
        form = seeds.rng("knowledge", "form|" + doc_id).randrange(2)
        p2 = _metric_p02(spec, form)
        if len(p2) > 220:  # SQL 写法在长表名或比率表达式下超长，退回计算式写法
            p2 = _metric_p02(spec, 0)
        return [_chk(doc_id, 1, _metric_p01(spec, form)),
                _chk(doc_id, 2, p2),
                _chk(doc_id, 3, _metric_p03(spec))]
    if t == "tool":
        return [_chk(doc_id, 1, _tool_p01(spec, perm)),
                _chk(doc_id, 2, _tool_p02(spec)),
                _chk(doc_id, 3, _tool_p03(spec, perm))]
    if t == "plan":
        form = seeds.rng("knowledge", "form|" + doc_id).randrange(2)
        return [_chk(doc_id, 1, _plan_p01(spec["table"], form)),
                _chk(doc_id, 2, _plan_p02(spec["table"])),
                _chk(doc_id, 3, _plan_p03(spec["table"]))]
    if t == "note":
        k = spec["note_kind"]
        if k == "codebook":
            texts = _note_codebook(spec["table"], 0)
        elif k == "lineage":
            texts = _note_lineage(spec["edge"])
        elif k == "change":
            texts = _note_change(spec["table"])
        elif k == "quality":
            texts = _note_quality(spec["table"])
        else:
            texts = _note_refresh(spec["table"])
        return [_chk(doc_id, i + 1, x) for i, x in enumerate(texts)]
    raise ValueError(t)


def _chunk(doc_id: str, p: int, text: str) -> dict:
    return {"chunk_id": ids.block_id(doc_id, p), "text": text,
            "hash": io.sha256_text(text)[:16]}


def _draws(doc_id: str) -> dict[str, float]:
    r = seeds.rng("knowledge", doc_id)
    return {k: r.random() for k in
            ("mod2", "kind2", "mod3", "kind3", "del3", "add3", "form2", "form3")}


def build_versions() -> tuple[list[dict], list[dict]]:
    specs = build_specs()
    perms = assign_permissions(specs)
    base = {s["doc_id"]: [_chunk(s["doc_id"], i + 1, t)
                          for i, t in enumerate(render_base(s, perms[s["doc_id"]]))]
            for s in specs}
    draws = {s["doc_id"]: _draws(s["doc_id"]) for s in specs}
    by_id = {s["doc_id"]: s for s in specs}
    doc_ids = [s["doc_id"] for s in specs]

    # 35% 在 v2 修改 p01（一半数字、一半表述）
    mod2 = sorted(doc_ids, key=lambda d: (draws[d]["mod2"], d))[:700]
    number2 = set(sorted(mod2, key=lambda d: (draws[d]["kind2"], d))[:350])
    # 15% 在 v2 已改的文档中于 v3 再改一次，数字与表述各半
    mod3 = sorted(mod2, key=lambda d: (draws[d]["mod3"], d))[:300]
    number3 = set(sorted(mod3, key=lambda d: (draws[d]["kind3"], d))[:150])
    # 8% 在 v3 删除 p02（避开 v3 改写，保证一对版本一行变更）
    del3 = sorted([d for d in doc_ids if d not in set(mod3)],
                  key=lambda d: (draws[d]["del3"], d))[:160]
    # 10% 的基础两段文档在 v2 新增 p03（避开 v2 改写）
    add3 = sorted([d for d in doc_ids
                   if len(base[d]) == 2 and d not in set(mod2)],
                  key=lambda d: (draws[d]["add3"], d))[:200]

    versions: dict[str, dict[int, list[dict]]] = {}
    kinds: dict[tuple[str, int, int], str] = {}
    for d in doc_ids:
        spec = by_id[d]
        v1 = [dict(c) for c in base[d]]
        v2 = [dict(c) for c in v1]
        v3: list[dict] = []
        if d in mod2:
            kind = "modify_number" if d in number2 else "modify_text"
            p1 = next(c for c in v2 if c["chunk_id"].endswith("#p01"))
            new = _bump_number(p1["text"]) if kind == "modify_number" else _rephrase(p1["text"], seeds.rng("knowledge", "form2|" + d), 2)
            p1["text"], p1["hash"] = new, io.sha256_text(new)[:16]
            kinds[(d, 1, 2)] = kind
        if d in add3:
            text = _chk(d, 3, _add_p03(spec))
            v2.append(_chunk(d, 3, text))
            kinds[(d, 1, 2)] = "add_chunk"
            v2.sort(key=lambda c: c["chunk_id"])
        # v3 从 v2 复制，避免修改串版
        v3 = [dict(c) for c in v2]
        if d in mod3:
            kind = "modify_number" if d in number3 else "modify_text"
            p1 = next(c for c in v3 if c["chunk_id"].endswith("#p01"))
            new = _bump_number(p1["text"]) if kind == "modify_number" else _rephrase(p1["text"], seeds.rng("knowledge", "form3|" + d), 3)
            p1["text"], p1["hash"] = new, io.sha256_text(new)[:16]
            kinds[(d, 2, 3)] = kind
        if d in del3:
            v3 = [c for c in v3 if not c["chunk_id"].endswith("#p02")]
            kinds[(d, 2, 3)] = "delete_chunk"
        versions[d] = {1: v1, 2: v2, 3: v3}

    rows: list[dict] = []
    for d in doc_ids:
        spec = by_id[d]
        for ver in (1, 2, 3):
            chunks = versions[d][ver]
            rows.append({
                "doc_id": d,
                "version": ver,
                "doc_type": ids.doc_type_of(d),
                "domain": spec["domain"],
                "permission": perms[d],
                "updated_at": VERSION_AT[ver],
                "chunks": chunks,
            })

    changes: list[dict] = []
    for d in doc_ids:
        for a, b in ((1, 2), (2, 3)):
            ma = {c["chunk_id"]: c["hash"] for c in versions[d][a]}
            mb = {c["chunk_id"]: c["hash"] for c in versions[d][b]}
            mods = sorted(cid for cid in ma if cid in mb and ma[cid] != mb[cid])
            adds = sorted(cid for cid in mb if cid not in ma)
            dels = sorted(cid for cid in ma if cid not in mb)
            if mods:
                changes.append({"doc_id": d, "from_ver": a, "to_ver": b,
                                "change_kind": kinds.get((d, a, b), "modify_text"),
                                "changed_chunk_ids": mods})
            if adds:
                changes.append({"doc_id": d, "from_ver": a, "to_ver": b,
                                "change_kind": "add_chunk",
                                "changed_chunk_ids": adds})
            if dels:
                changes.append({"doc_id": d, "from_ver": a, "to_ver": b,
                                "change_kind": "delete_chunk",
                                "changed_chunk_ids": dels})
    changes.sort(key=lambda c: (c["doc_id"], c["from_ver"],
                                ("modify_text", "modify_number", "add_chunk", "delete_chunk")
                                .index(c["change_kind"])))
    return rows, changes


# ---------------------------------------------------------------- 渲染与写盘
def dumps_row(row: dict) -> str:
    return io._dumps(row)


def render_docs_text() -> str:
    rows, _ = build_versions()
    return "".join(dumps_row(r) + "\n" for r in rows)


def render_changes_text() -> str:
    _, changes = build_versions()
    return "".join(dumps_row(c) + "\n" for c in changes)


def _manifest(rows: int, nchanges: int, doc_counts: dict[str, int]) -> dict:
    files = {}
    for name in ("docs.jsonl", "version_changes.jsonl"):
        p = KN / name
        files[name] = {"rows": rows if name == "docs.jsonl" else nchanges,
                       "sha256": io.sha256_file(p)}
    files["docs.jsonl"]["doc_counts"] = doc_counts
    for name in ("build.py", "selfcheck.py"):
        p = KN / name
        if p.is_file():
            files[name] = {"rows": len(p.read_text(encoding="utf-8").splitlines()),
                           "sha256": io.sha256_file(p)}
    return files


def main() -> int:
    docs_path = KN / "docs.jsonl"
    changes_path = KN / "version_changes.jsonl"
    rows, changes = build_versions()
    n1 = io.write_jsonl(docs_path, rows)
    n2 = io.write_jsonl(changes_path, changes)
    assert n1 == KN_PARAMS["docs_total"] * KN_PARAMS["versions"], n1
    counts: dict[str, int] = {}
    for r in rows:
        if r["version"] == 1:
            counts[r["doc_type"]] = counts.get(r["doc_type"], 0) + 1
    io.write_json(KN / "MANIFEST.json", _manifest(n1, n2, counts))
    print(f"docs.jsonl            {n1} 行  sha256={io.sha256_file(docs_path)}")
    print(f"version_changes.jsonl {n2} 行  sha256={io.sha256_file(changes_path)}")
    print(f"MANIFEST.json 已写入 {KN / 'MANIFEST.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
