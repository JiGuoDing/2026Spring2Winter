# MySQL 完整教程 — 构建计划

## 项目定位

面向**大数据开发面试**的 MySQL 实战教程，从基础到专家级，深入浅出。以一个**电商系统数据库**为贯穿案例，覆盖面试中高频出现的 SQL 知识点。所有代码均为可直接运行的 `.sql` 文件，附带详细中文注释。

---

## 一、项目结构

```
mysql/
├── build.md                      # 本文档：构建计划
├── README.md                     # 项目说明、使用指南
├── setup.sql                     # 一键初始化脚本：建库 → 建表 → 造数据
├── teardown.sql                  # 一键清理脚本：删除数据库
│
├── 01_基础查询_CRUD.sql          # SELECT / INSERT / UPDATE / DELETE / WHERE
├── 02_高级过滤与排序.sql          # LIKE / IN / BETWEEN / IS NULL / ORDER BY / LIMIT / DISTINCT
├── 03_聚合函数与分组.sql          # COUNT / SUM / AVG / MAX / MIN / GROUP BY / HAVING
├── 04_内置函数大全.sql            # 字符串 / 日期 / 数学 / 条件 / 类型转换 函数
├── 05_JOIN连接.sql               # INNER / LEFT / RIGHT / CROSS / SELF JOIN / 多表连接
├── 06_子查询.sql                 # 标量 / 行 / 表子查询 / 关联子查询 / EXISTS / NOT EXISTS
├── 07_集合操作.sql               # UNION / INTERSECT / EXCEPT / UNION ALL
├── 08_窗口函数.sql               # ROW_NUMBER / RANK / DENSE_RANK / LAG / LEAD / 聚合窗口
├── 09_CTE公共表达式.sql           # 普通 CTE / 递归 CTE
├── 10_事务与隔离级别.sql          # COMMIT / ROLLBACK / SAVEPOINT / 隔离级别 / 死锁
├── 11_索引与性能优化.sql          # BTREE / HASH / 复合索引 / EXPLAIN / 慢查询 / 覆盖索引
├── 12_视图.sql                   # CREATE VIEW / 可更新视图 / MATERIALIZED 概念
├── 13_存储过程.sql               # PROCEDURE / IN / OUT / INOUT / 游标 / 异常处理
├── 14_自定义函数.sql              # FUNCTION / 确定性函数 / 聚合函数
├── 15_触发器与事件.sql            # TRIGGER / EVENT / 审计日志
├── 16_约束与外键.sql              # PK / FK / UNIQUE / CHECK / DEFAULT / 级联操作
├── 17_数据库设计范式.sql          # 1NF / 2NF / 3NF / BCNF / 反范式化 / 实际案例
├── 18_面试高频题50道.sql          # 由浅入深的 50 道面试真题 + 详解
│
└── answers/                      # 所有练习题的参考答案
    ├── answer_01.sql
    ├── answer_02.sql
    ├── ...
    └── answer_18.sql
```

> 共计 **18 个教学文件 + setup/teardown + answers**，按序号由浅入深。

---

## 二、学习路线图

```
[基础篇]           [进阶篇]              [高级篇]               [专家篇]
01 ─→ 02       03 ─→ 04              08 ─→ 09             12 ─→ 13
              └─→ 05 ─→ 06 ─→ 07   └─→ 10 ─→ 11          └─→ 14 ─→ 15
                                                           └─→ 16 ─→ 17
[实战篇]
18 (面试高频题50道) — 串联所有知识点
```

**各阶段说明：**

| 阶段 | 章节 | 目标 |
|------|------|------|
| 基础篇 | 01, 02 | 能独立写出正确的增删改查语句 |
| 进阶篇 | 03~07 | 能完成数据统计、多表关联、复杂筛选 |
| 高级篇 | 08~11 | 能写窗口函数分析、优化慢查询、理解事务 |
| 专家篇 | 12~17 | 能写存储过程/函数/触发器、设计规范数据库 |
| 实战篇 | 18 | 能应对大数据开发面试中的 SQL 题目 |

---

## 三、贯穿案例：电商数据库设计

所有课程共用同一套数据库 `mysql_tutorial`，包含以下 6 张表：

| 表名 | 说明 | 核心字段 |
|------|------|---------|
| `categories` | 商品分类 | id, name, parent_id（自引用，支持多级分类） |
| `products` | 商品信息 | id, name, category_id, price, stock, supplier_id, created_at |
| `customers` | 客户信息 | id, name, email, phone, city, register_date |
| `suppliers` | 供应商信息 | id, name, contact, city |
| `orders` | 订单主表 | id, customer_id, order_date, total_amount, status |
| `order_items` | 订单明细 | id, order_id, product_id, quantity, unit_price |

**表关系图：**

```
suppliers ──┐
             ├──→ products ──→ categories (自引用 parent_id)
             │       ↓
             │   order_items
             │       ↓
customers ───┘──→ orders
```

**设计要点：**
- `categories.parent_id` 指向自身 → 用于演示**自连接 (SELF JOIN)** 和**递归 CTE**
- `orders → order_items → products → categories` 形成**四表关联链** → 用于演示多表 JOIN
- 表间关系覆盖 1:1、1:N、M:N → 覆盖全部连接场景
- 数据量约 10 个分类、50 个商品、100 个客户、500 个订单、2000 条订单明细 → 足够体现索引优化效果

---

## 四、各章详细规划

### 01 — 基础查询与 CRUD

| 维度 | 内容 |
|------|------|
| **难度** | ★☆☆☆☆ |
| **学习时间** | 约 45 分钟 |
| **前置知识** | 无（执行 setup.sql 即可） |

**知识点：**
- `SELECT` 列选择与列别名 (`AS`)
- `SELECT DISTINCT` 去重
- `INSERT INTO` 单行插入 / 多行插入 / 从查询结果插入 (`INSERT ... SELECT`)
- `UPDATE` 条件更新（强调不带 WHERE 的危险）
- `DELETE` 与 `TRUNCATE` 的区别
- `WHERE` 基础条件筛选（`=` / `<>` / `>` / `<` / `>=` / `<=`）
- 三值逻辑：`NULL` 的判断 (`IS NULL` / `IS NOT NULL` / `<=>` 安全等于)

**练习：6 道题**

---

### 02 — 高级过滤与排序

| 维度 | 内容 |
|------|------|
| **难度** | ★★☆☆☆ |
| **学习时间** | 约 40 分钟 |
| **前置知识** | 01 |

**知识点：**
- 逻辑运算符：`AND` / `OR` / `NOT` 的优先级（括号的重要性）
- `LIKE` 模糊匹配与通配符 (`%` 任意长度 / `_` 单字符)
- `IN` / `NOT IN` 集合匹配
- `BETWEEN ... AND ...` 范围查询（含边界）
- `ORDER BY` 单列 / 多列 / 表达式排序、`ASC` / `DESC`
- `LIMIT` 与 `OFFSET` 分页

**练习：8 道题**（含分页、多条件组合筛选）

---

### 03 — 聚合函数与分组

| 维度 | 内容 |
|------|------|
| **难度** | ★★☆☆☆ |
| **学习时间** | 约 50 分钟 |
| **前置知识** | 01, 02 |

**知识点：**
- 聚合函数：`COUNT` / `SUM` / `AVG` / `MAX` / `MIN`
- `COUNT(*)` vs `COUNT(column)` vs `COUNT(DISTINCT column)` 的区别
- `GROUP BY` 单列分组 / 多列分组
- **`WHERE` vs `HAVING` 的本质区别**（SQL 执行顺序：FROM → WHERE → GROUP BY → HAVING → SELECT → ORDER BY → LIMIT）
- `WITH ROLLUP` 小计汇总（大数据报表场景常见）

**练习：8 道题**（销售分析场景：日/月销售额统计、客单价、复购率）

---

### 04 — 内置函数大全

| 维度 | 内容 |
|------|------|
| **难度** | ★★☆☆☆ |
| **学习时间** | 约 50 分钟 |
| **前置知识** | 01, 02, 03 |

**知识点：**
- **字符串函数**：`CONCAT`、`CONCAT_WS`、`SUBSTRING`、`REPLACE`、`LENGTH`/`CHAR_LENGTH`、`TRIM`/`LTRIM`/`RTRIM`、`UPPER`/`LOWER`、`LEFT`/`RIGHT`、`LPAD`/`RPAD`、`INSTR`、`LOCATE`
- **日期时间函数**：`NOW`、`CURDATE`、`DATE_FORMAT`、`STR_TO_DATE`、`DATEDIFF`、`TIMESTAMPDIFF`、`DATE_ADD`/`DATE_SUB`、`YEAR`/`MONTH`/`DAY`、`DAYOFWEEK`、`LAST_DAY`
- **数学函数**：`ROUND`、`CEIL`/`FLOOR`、`ABS`、`MOD`、`RAND`
- **条件函数**：`IF(expr, true_val, false_val)`、`IFNULL`、`COALESCE`、`NULLIF`、`CASE WHEN ... THEN ... ELSE ... END`
- **类型转换**：`CAST`、`CONVERT`

**练习：10 道题**（结合实际数据处理需求）

---

### 05 — JOIN 连接

| 维度 | 内容 |
|------|------|
| **难度** | ★★★☆☆ |
| **学习时间** | 约 60 分钟 |
| **前置知识** | 01, 02, 03 |

**知识点：**
- **`INNER JOIN`**：只返回匹配行（最常用，约 80% 场景）
- **`LEFT JOIN`**：保留左表全部行，右表无匹配填 NULL
- **`RIGHT JOIN`**：保留右表全部行（可用 LEFT JOIN 等价替换，但面试会问）
- **`CROSS JOIN`**：笛卡尔积（何时有意使用？生成测试数据、组合枚举）
- **`SELF JOIN`**：表自己连接自己（配合 `categories.parent_id` 查父子分类）
- **多表连接**：3 表、4 表连接，ON 条件的书写技巧
- **`USING` vs `ON`** 的语法差异
- 隐式连接（`FROM a, b WHERE a.id = b.id`）vs 显式 JOIN
- JOIN 的执行顺序与 ON 条件位置的影响

**练习：10 道题**（从 2 表到 4 表连接递进）

---

### 06 — 子查询

| 维度 | 内容 |
|------|------|
| **难度** | ★★★☆☆ |
| **学习时间** | 约 55 分钟 |
| **前置知识** | 05 |

**知识点：**
- 按返回值分类：**标量子查询**（单行单列）、**行子查询**（单行多列）、**列子查询**（多行单列）、**表子查询**（多行多列）
- 按位置分类：`SELECT` 中、`FROM` 中（派生表必须有别名）、`WHERE` 中、`HAVING` 中
- **关联子查询** vs **非关联子查询**：核心区别在于内查询是否引用外查询的列
- `EXISTS` 与 `NOT EXISTS`：相关子查询的最佳搭档，语义为"存在/不存在"
- **`IN` vs `EXISTS` 的性能差异**（面试高频题）
- **`NOT IN` 的 NULL 陷阱**（子查询结果含 NULL 时，NOT IN 返回空集）
- `ANY` / `ALL` / `SOME` 量化比较
- 子查询 vs JOIN 的互换与选择标准
- 派生表 (`FROM` 子查询)

**练习：10 道题**（含经典面试题如"查询从未下过单的用户"、"查询高于平均价格的商品"）

---

### 07 — 集合操作

| 维度 | 内容 |
|------|------|
| **难度** | ★★★☆☆ |
| **学习时间** | 约 30 分钟 |
| **前置知识** | 03, 05, 06 |

**知识点：**
- `UNION`（去重合并）vs `UNION ALL`（保留全部）
- `INTERSECT`（交集，MySQL 8.0.31+ 原生支持，旧版用 `IN` / `EXISTS` 模拟）
- `EXCEPT`（差集，MySQL 8.0.31+ 原生支持，旧版用 `NOT IN` / `NOT EXISTS` 模拟）
- 集合操作的前置条件：列数相同、数据类型兼容
- `ORDER BY` 只能出现在整个集合操作的末尾
- 用 `()` 给每个 SELECT 包裹可加独立 ORDER BY + LIMIT

**练习：6 道题**

---

### 08 — 窗口函数 ⭐（大数据岗位必考）

| 维度 | 内容 |
|------|------|
| **难度** | ★★★★☆ |
| **学习时间** | 约 75 分钟 |
| **前置知识** | 03, 05 |

**知识点：**
- **窗口函数 vs 聚合函数**的本质区别：聚合折叠行，窗口保留行
- `OVER()` 子句的构成：`PARTITION BY`（分组）+ `ORDER BY`（排序）+ Frame（范围）
- **排名函数**：
  - `ROW_NUMBER()` → 唯一行号，并列也递增
  - `RANK()` → 有间隔排名 (1, 1, 3)
  - `DENSE_RANK()` → 无间隔排名 (1, 1, 2)
  - `NTILE(n)` → 将数据分成 n 个桶
- **偏移函数**（同比/环比分析利器）：
  - `LAG(column, offset, default)` → 向前取值
  - `LEAD(column, offset, default)` → 向后取值
- **取值函数**：
  - `FIRST_VALUE()` / `LAST_VALUE()` / `NTH_VALUE(column, n)`
- **聚合窗口**：`SUM() OVER()`、`AVG() OVER()`、`COUNT() OVER()` → 累计求和、移动平均
- **Frame 子句**（窗口帧）：
  - `ROWS BETWEEN n PRECEDING AND CURRENT ROW` → 物理行范围
  - `RANGE BETWEEN n PRECEDING AND CURRENT ROW` → 逻辑值范围
  - `ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW` → 累计到当前行

**练习：12 道题**（TopN 每组前几名、累计销售额、移动平均、环比增长率、RFM 分析）

---

### 09 — CTE 公共表达式

| 维度 | 内容 |
|------|------|
| **难度** | ★★★☆☆ |
| **学习时间** | 约 40 分钟 |
| **前置知识** | 06, 08 |

**知识点：**
- 普通 CTE：`WITH name AS (SELECT ...) SELECT ... FROM name`
- 多个 CTE 链式定义：`WITH a AS (...), b AS (...) SELECT ...`
- CTE vs 子查询 vs 临时表 vs 视图：各自的适用场景
- **递归 CTE**（重要）：
  - 结构：`WITH RECURSIVE ... UNION ALL ...`
  - 递归终止条件（当子查询不再产生新行时自动终止）
  - 经典案例：遍历 `categories` 树形结构（查某个分类的所有子分类）
  - 经典案例：生成连续日期序列
  - `cte_max_recursion_depth` 系统变量

**练习：6 道题**（含递归查询父子分类、生成日期维度表）

---

### 10 — 事务与隔离级别

| 维度 | 内容 |
|------|------|
| **难度** | ★★★★☆ |
| **学习时间** | 约 55 分钟 |
| **前置知识** | 01（有基础概念即可） |

**知识点：**
- **ACID 四大特性**（概念必考）：
  - Atomicity 原子性 → Undo Log
  - Consistency 一致性 → 约束 + 应用逻辑
  - Isolation 隔离性 → 锁 + MVCC
  - Durability 持久性 → Redo Log
- 基本操作：`START TRANSACTION` / `BEGIN`、`COMMIT`、`ROLLBACK`
- `SAVEPOINT` 部分回滚
- **四种隔离级别**：
  - `READ UNCOMMITTED` → 脏读可能
  - `READ COMMITTED` → 不可重复读可能
  - `REPEATABLE READ`（InnoDB 默认）→ 幻读可能（但 InnoDB 用 Next-Key Lock 解决了）
  - `SERIALIZABLE` → 最高隔离，性能最差
- 并发问题对照表：
  | 隔离级别 | 脏读 | 不可重复读 | 幻读 |
  |---------|------|----------|------|
  | READ UNCOMMITTED | ✓ | ✓ | ✓ |
  | READ COMMITTED | ✗ | ✓ | ✓ |
  | REPEATABLE READ | ✗ | ✗ | ✓(InnoDB基本解决) |
  | SERIALIZABLE | ✗ | ✗ | ✗ |
- **MVCC** 概念：ReadView + Undo Log 实现快照读
- 锁分类：共享锁 (`SELECT ... LOCK IN SHARE MODE`/`FOR SHARE`) / 排他锁 (`SELECT ... FOR UPDATE`)
- 死锁的产生条件与排查 (`SHOW ENGINE INNODB STATUS`)

**练习：6 道题**（概念题 + 开两个终端实操验证隔离级别）

---

### 11 — 索引与性能优化 ⭐（面试必考重点）

| 维度 | 内容 |
|------|------|
| **难度** | ★★★★☆ |
| **学习时间** | 约 70 分钟 |
| **前置知识** | 01~09（需要数据基础做实验） |

**知识点：**
- **索引本质**：B+Tree 结构原理图解
- 索引类型：主键索引（聚簇索引）、二级索引（非聚簇索引）
- **回表查询**：二级索引找到主键 → 回聚簇索引查完整行
- **覆盖索引** (`Using index`)：查询列全在索引中，无需回表
- **复合索引**与**最左前缀原则**（面试必考！）：
  - 索引 `(a, b, c)` 能匹配 `a`、`a,b`、`a,b,c`，不能匹配 `b`、`b,c`
  - 范围查询 (`>` / `<` / `BETWEEN`) 会中断后续列的匹配
- **`EXPLAIN` 执行计划解读**（核心技能）：
  - `type`：ALL < index < range < ref < eq_ref < const < system
  - `key`：实际使用的索引
  - `rows`：预估扫描行数
  - `Extra`：Using index / Using temporary / Using filesort / Using where
- **索引失效的常见场景**（面试高频）：
  - 对索引列使用函数：`WHERE DATE(create_time) = '2024-01-01'`
  - 隐式类型转换：`WHERE phone = 13900000000`（phone 是 varchar）
  - LIKE 以 `%` 开头：`LIKE '%keyword'`
  - OR 连接非索引列
  - NOT IN / `<>` / `!=`
- **慢查询优化**：`slow_query_log`、`long_query_time`、`mysqldumpslow`
- `FORCE INDEX` / `USE INDEX` / `IGNORE INDEX` 手动控制
- 前缀索引 (`INDEX(col(10))`)、索引下推 (ICP)
- 索引设计的权衡：索引并非越多越好（写操作开销、存储空间）

**练习：10 道题**（给慢 SQL + EXPLAIN 结果 → 创建合适索引 → 验证优化效果）

---

### 12 — 视图

| 维度 | 内容 |
|------|------|
| **难度** | ★★☆☆☆ |
| **学习时间** | 约 30 分钟 |
| **前置知识** | 01~06 |

**知识点：**
- `CREATE VIEW` 基本语法，`OR REPLACE`
- `WITH CHECK OPTION`：防止通过视图插入/更新不可见数据
- 可更新视图的条件（不能含 `GROUP BY`、`DISTINCT`、聚合函数、`UNION` 等）
- 视图 vs 物化视图（概念对比，MySQL 不原生支持物化视图）
- 使用场景：权限控制（隐藏敏感列）、简化复杂查询、接口层抽象
- `SHOW CREATE VIEW` / `INFORMATION_SCHEMA.VIEWS`

**练习：5 道题**

---

### 13 — 存储过程

| 维度 | 内容 |
|------|------|
| **难度** | ★★★☆☆ |
| **学习时间** | 约 55 分钟 |
| **前置知识** | 01, 04 |

**知识点：**
- 基本语法：`DELIMITER //` → `CREATE PROCEDURE` → 主体 → `//` → `DELIMITER ;`
- 参数模式：`IN`（默认）、`OUT`（输出）、`INOUT`（输入输出）
- 变量声明 (`DECLARE`) 与赋值 (`SET` / `SELECT ... INTO`)
- 流程控制：
  - `IF ... THEN ... ELSEIF ... ELSE ... END IF`
  - `CASE ... WHEN ... THEN ... END CASE`
  - `WHILE ... DO ... END WHILE`
  - `REPEAT ... UNTIL ... END REPEAT`
  - `LOOP ... LEAVE ... END LOOP`
- 游标 (`CURSOR`) 遍历结果集（`DECLARE ... CURSOR FOR`、`OPEN`、`FETCH`、`CLOSE`）
- `DECLARE ... HANDLER FOR NOT FOUND` 处理游标结束
- 异常处理：`DECLARE ... HANDLER FOR SQLEXCEPTION`
- 存储过程的优缺点：减少网络开销 vs 难以调试、数据库耦合

**练习：5 道题**（含分页存储过程、批量更新、事务包裹）

---

### 14 — 自定义函数

| 维度 | 内容 |
|------|------|
| **难度** | ★★★☆☆ |
| **学习时间** | 约 30 分钟 |
| **前置知识** | 13 |

**知识点：**
- 标量函数：`CREATE FUNCTION ... RETURNS type`
- 必须声明 `DETERMINISTIC` 或 `NOT DETERMINISTIC`
- 函数中使用 `SELECT` 的限制（不能修改数据）
- 聚合函数（`CREATE AGGREGATE FUNCTION`，MySQL 8.0+）
- **函数 vs 存储过程的本质区别**：
  | | 函数 | 存储过程 |
  |---|------|---------|
  | 返回值 | 必须有 | 通过 OUT 参数 |
  | 调用方式 | `SELECT func()` | `CALL proc()` |
  | 事务控制 | 不能 | 可以 |
  | 使用场景 | 计算、转换 | 业务逻辑 |

**练习：4 道题**

---

### 15 — 触发器与事件

| 维度 | 内容 |
|------|------|
| **难度** | ★★★☆☆ |
| **学习时间** | 约 35 分钟 |
| **前置知识** | 01, 13 |

**知识点：**
- 触发器类型：`BEFORE INSERT` / `AFTER INSERT` / `BEFORE UPDATE` / `AFTER UPDATE` / `BEFORE DELETE` / `AFTER DELETE`
- `NEW` 和 `OLD` 伪行引用：
  - INSERT：只能引用 `NEW`（新插入的行）
  - DELETE：只能引用 `OLD`（被删除的行）
  - UPDATE：同时可用 `NEW`（更新后的值）和 `OLD`（更新前的值）
- 经典用例：**审计日志**（用触发器自动记录数据变更）
- 经典用例：自动更新 `updated_at` 时间戳
- 事件调度器：`CREATE EVENT ... ON SCHEDULE EVERY ... DO`
- `SHOW EVENTS` / 启用 `event_scheduler`
- 触发器的注意事项：性能影响、级联触发、调试困难、不建议放复杂业务逻辑

**练习：4 道题**

---

### 16 — 约束与外键

| 维度 | 内容 |
|------|------|
| **难度** | ★★★☆☆ |
| **学习时间** | 约 35 分钟 |
| **前置知识** | setup.sql 中的建表逻辑 |

**知识点：**
- `PRIMARY KEY`：主键（唯一 + 非空，每表只能有一个）
- `UNIQUE`：唯一约束（可为 NULL，允许多个 NULL）
- `NOT NULL`：非空约束
- `FOREIGN KEY`：外键约束
  - `ON DELETE CASCADE / SET NULL / RESTRICT / NO ACTION`
  - `ON UPDATE CASCADE / SET NULL / RESTRICT / NO ACTION`
- `CHECK` 约束（MySQL 8.0.16+）：`CHECK (price > 0)`、`CHECK (status IN ('pending', 'shipped', 'delivered'))`
- `DEFAULT` 默认值
- `AUTO_INCREMENT` 自增列
- 约束在数据库层 vs 应用层的取舍（为什么有些团队不建外键）

**练习：5 道题**

---

### 17 — 数据库设计范式

| 维度 | 内容 |
|------|------|
| **难度** | ★★★★☆ |
| **学习时间** | 约 45 分钟 |
| **前置知识** | 01~16 综合 |

**知识点：**
- **1NF**（第一范式）：列不可再分，属性原子性
- **2NF**（第二范式）：消除部分函数依赖（非主属性完全依赖于候选键）
- **3NF**（第三范式）：消除传递函数依赖（非主属性不依赖于其他非主属性）
- **BCNF**：消除主属性对候选键的部分和传递依赖
- **反范式化**：什么时候可以故意违反范式？
  - 冗余字段减少 JOIN → 提升查询性能
  - 汇总表/统计表 → 避免实时聚合
  - 典型案例：订单表冗余 `customer_name` 和 `product_name`
- E-R 模型实战：从业务需求 → 实体识别 → 属性定义 → 关系建立 → 表结构设计
- 一个完整的数据库设计演练

---

### 18 — 面试高频题 50 道

| 维度 | 内容 |
|------|------|
| **难度** | ★★ ~ ★★★★★ |
| **学习时间** | 综合练习，按需刷题 |
| **前置知识** | 全部前面章节 |

**题目分级：**
| 难度 | 题目数 | 示例题型 |
|------|--------|---------|
| 简单 | 1-15 | 基本 CRUD、简单 JOIN、聚合统计 |
| 中等 | 16-35 | 多表关联、复杂子查询、窗口函数排名、连续登录 |
| 困难 | 36-50 | 复杂业务场景、性能优化、留存分析、累加求和、行程问题 |

**每道题包含：**
- 题目描述（模拟面试场景）
- 建表 DDL + 测试数据
- 解题思路分析
- 参考答案（可能给出多种解法对比）
- 易错点 / 面试官追问方向

**部分题例预览：**
1. 查询每个商品销量排名（窗口函数）
2. 查询连续 3 天登录的用户（连续登录问题）
3. 查询累计销售额（累计求和）
4. 查询从未购买过某类商品的客户（NOT EXISTS）
5. 一条 SQL 删除重复数据保留最小 ID（面试高频）
6. 查询每个用户最近一次购买记录
7. 分组查询每组 Top 3
8. 行转列 / 列转行

---

## 五、文件编写规范

每个 `.sql` 教学文件遵循统一格式：

```sql
-- =====================================================
-- 文件名：01_基础查询_CRUD.sql
-- 难度：★☆☆☆☆
-- 前置知识：无（执行 setup.sql 即可）
-- 学习时间：约 45 分钟
-- 对应面试考点：SQL 基础语法、数据操作、NULL 处理
-- =====================================================

-- =====================================================
-- 第一部分：知识点讲解
-- 每个知识点包含：概念解释 + 可直接执行的代码示例
-- =====================================================

-- 1.1 SELECT 基本查询
-- 概念：SELECT 用于从表中查询数据...
SELECT * FROM customers LIMIT 5;

-- =====================================================
-- 第二部分：练习题
-- 每道题包含：题目描述（要实现什么）、提示（可选）
-- =====================================================

-- 题1：查询所有商品名称和价格，按价格从高到低排序
-- 你的代码：

-- =====================================================
-- 第三部分：面试技巧
-- 本章知识点在面试中的常见问法和注意事项
-- =====================================================
```

---

## 六、setup.sql 的设计规范

`setup.sql` 是整个教程的基石，必须遵循以下原则：

1. **幂等性**：可重复执行（`DROP DATABASE IF EXISTS mysql_tutorial;` 在开头）
2. **自包含**：一个文件完成建库 → 建表 → 约束 → 索引 → 造数据
3. **字符集统一**：`utf8mb4` + `utf8mb4_unicode_ci`
4. **注释清晰**：每个表用注释说明字段含义和业务含义
5. **数据真实感**：商品名、人名、城市名使用有意义的中文数据
6. **数据量合理**：约 500 订单 / 2000 行明细，足够体现索引效果又不至于执行过慢
7. **种子数据覆盖边界**：包含 NULL 值、边缘值、重复值 → 方便演示各种知识点

执行方式：
```bash
mysql -u root -padmin < setup.sql
```

---

## 七、构建顺序与依赖

| 步骤 | 文件 | 依赖 | 预计行数 |
|------|------|------|---------|
| 1 | `build.md` | 无 | ~300 行（本文档） |
| 2 | `setup.sql` | 无 | ~400 行 |
| 3 | `teardown.sql` | 无 | ~10 行 |
| 4 | `README.md` | setup.sql | ~80 行 |
| 5 | `01_基础查询_CRUD.sql` | setup.sql | ~250 行 |
| 6 | `02_高级过滤与排序.sql` | 01 | ~250 行 |
| 7 | `03_聚合函数与分组.sql` | 01, 02 | ~280 行 |
| 8 | `04_内置函数大全.sql` | 01, 02, 03 | ~350 行 |
| 9 | `05_JOIN连接.sql` | 01, 02, 03 | ~350 行 |
| 10 | `06_子查询.sql` | 05 | ~300 行 |
| 11 | `07_集合操作.sql` | 03, 05, 06 | ~200 行 |
| 12 | `08_窗口函数.sql` | 03, 05 | ~400 行 |
| 13 | `09_CTE公共表达式.sql` | 06, 08 | ~250 行 |
| 14 | `10_事务与隔离级别.sql` | 01 | ~300 行 |
| 15 | `11_索引与性能优化.sql` | 01~09 | ~400 行 |
| 16 | `12_视图.sql` | 01~06 | ~200 行 |
| 17 | `13_存储过程.sql` | 01, 04 | ~350 行 |
| 18 | `14_自定义函数.sql` | 13 | ~200 行 |
| 19 | `15_触发器与事件.sql` | 01, 13 | ~250 行 |
| 20 | `16_约束与外键.sql` | setup.sql 建表 | ~200 行 |
| 21 | `17_数据库设计范式.sql` | 01~16 综合 | ~250 行 |
| 22 | `18_面试高频题50道.sql` | 全部章节 | ~800 行 |
| 23 | `answers/*.sql`（18 个文件） | 对应章节 | 各 ~50~150 行 |

> 总计约 **5,500+ 行** 的 SQL 教学内容（含注释）。

---

## 八、关键设计决策

| 决策点 | 选择 | 理由 |
|--------|------|------|
| MySQL 版本 | **8.0+** | 窗口函数、CTE、递归 CTE、CHECK 约束都需 8.0 |
| 存储引擎 | **InnoDB** | 支持事务、行锁、外键、MVCC，生产环境默认 |
| 字符集 | **utf8mb4** | 支持 emoji 和完整 Unicode |
| 贯穿案例 | **电商系统** | 业务易懂、表关系丰富、覆盖全部 SQL 知识点 |
| 数据量级 | **~500 订单 / ~2000 明细** | 太小无法体现索引效果，太大执行慢影响学习体验 |
| 注释语言 | **中文** | 降低理解门槛，聚焦 SQL 语法本身 |
| 练习答案位置 | **独立 answers/ 目录** | 避免"不经意看到答案"，鼓励独立完成 |

---

## 九、自审清单（合理性验证）

### 逻辑完整性 ✅
- [x] 从建库建表到高级特性，学习路径逐层递进，无跳跃依赖
- [x] 每一章的前置知识都在前面的章节中覆盖
- [x] `setup.sql` 提供了贯穿全文的统一数据基础，所有章节共享同一套数据
- [x] 第 18 章的面试题串联了全部知识点，形成闭环

### 面试针对性 ✅
- [x] 窗口函数独立成章 ⭐ → 大数据岗位面试必考
- [x] 索引优化独立成章 ⭐ → SQL 调优必考
- [x] 事务与隔离级别 → 理论必考（ACID、隔离级别、MVCC）
- [x] JOIN / 子查询深度覆盖 → 手写 SQL 必考
- [x] 50 道面试题按难度分级，覆盖真实面试场景

### 可执行性 ✅
- [x] 所有 SQL 都是可直接运行的，不是伪代码
- [x] `setup.sql` 幂等设计，可反复执行，方便重来
- [x] 每道练习都有参考答案（在 `answers/` 目录），可自查
- [x] 本地 MySQL 安装，无需 Docker（符合用户要求）

### 学习体验 ✅
- [x] 每个文件标注难度、学习时间、前置知识、面试考点
- [x] 电商案例贴近实际业务，不枯燥
- [x] 面试技巧附在每个文件末尾，学完即能应对面试
- [x] 从简到难，40 分钟~75 分钟一章，适合碎片化学习

### 大数据岗位关联度 ✅
- [x] 窗口函数（第 08 章）→ 对应 Hive/Spark SQL 的窗口函数，语法几乎一致
- [x] CTE（第 09 章）→ 对应 Spark SQL / Flink SQL 的 WITH 子句
- [x] 索引优化（第 11 章）→ 数据仓库分层设计需要理解索引原理
- [x] 数据库设计（第 17 章）→ 数据仓库建模的基础（星型/雪花模型的前置知识）
