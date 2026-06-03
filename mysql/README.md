# MySQL 完整教程 — 面向大数据开发面试

## 简介

这是一个面向**大数据开发面试**的 MySQL 实战教程。以电商系统为贯穿案例，从基础的 CRUD 到高级的窗口函数、索引优化、存储过程，覆盖面试中 90% 以上的 SQL 考点。

## 环境准备

### 1. 安装 MySQL 8.0+
```bash
# Ubuntu/Debian
sudo apt install mysql-server-8.0

# macOS
brew install mysql@8.0

# 启动服务
sudo systemctl start mysql    # Linux
brew services start mysql@8.0  # macOS
```

### 2. 设置 root 密码
```bash
# 如果首次安装未设置密码
sudo mysql -u root
ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'admin';
FLUSH PRIVILEGES;
```

### 3. 初始化教程数据库
```bash
cd /home/jgd/workplace/2026Spring2Winter/mysql
mysql -u root -padmin < setup.sql
```

## 学习路线

```
[基础篇]           [进阶篇]              [高级篇]               [专家篇]
01 ─→ 02       03 ─→ 04              08 ─→ 09             12 ─→ 13
              └─→ 05 ─→ 06 ─→ 07   └─→ 10 ─→ 11          └─→ 14 ─→ 15
                                                           └─→ 16 ─→ 17
[实战篇]
18 (面试高频题50道) — 串联所有知识点
```

## 文件说明

| 文件 | 内容 | 难度 | 时间 |
|------|------|------|------|
| `setup.sql` | 一键初始化（建库+建表+数据） | — | 一次性 |
| `01_基础查询_CRUD.sql` | SELECT/INSERT/UPDATE/DELETE | ★ | 45min |
| `02_高级过滤与排序.sql` | LIKE/IN/BETWEEN/ORDER BY/LIMIT | ★★ | 40min |
| `03_聚合函数与分组.sql` | COUNT/SUM/AVG/GROUP BY/HAVING | ★★ | 50min |
| `04_内置函数大全.sql` | 字符串/日期/数学/条件函数 | ★★ | 50min |
| `05_JOIN连接.sql` | INNER/LEFT/RIGHT/CROSS/SELF JOIN | ★★★ | 60min |
| `06_子查询.sql` | 标量/行/表子查询/EXISTS | ★★★ | 55min |
| `07_集合操作.sql` | UNION/INTERSECT/EXCEPT | ★★★ | 30min |
| `08_窗口函数.sql` ⭐ | ROW_NUMBER/RANK/LAG/累计求和 | ★★★★ | 75min |
| `09_CTE公共表达式.sql` | WITH/递归CTE | ★★★ | 40min |
| `10_事务与隔离级别.sql` | ACID/隔离级别/MVCC/死锁 | ★★★★ | 55min |
| `11_索引与性能优化.sql` ⭐ | B+Tree/EXPLAIN/最左前缀/慢查询 | ★★★★ | 70min |
| `12_视图.sql` | CREATE VIEW/CHECK OPTION | ★★ | 30min |
| `13_存储过程.sql` | PROCEDURE/游标/异常处理 | ★★★ | 55min |
| `14_自定义函数.sql` | FUNCTION/确定性函数 | ★★★ | 30min |
| `15_触发器与事件.sql` | TRIGGER/EVENT/审计日志 | ★★★ | 35min |
| `16_约束与外键.sql` | PK/FK/UNIQUE/CHECK/级联 | ★★★ | 35min |
| `17_数据库设计范式.sql` | 1NF/2NF/3NF/反范式化 | ★★★★ | 45min |
| `18_面试高频题50道.sql` | 50道面试真题+详解 | ★★~★★★★★ | 按需 |

## 每章结构

每章 `.sql` 文件包含三部分：
1. **知识点讲解** — 概念 + 可运行的代码示例
2. **练习题** — 动手写 SQL
3. **面试技巧** — 本章在面试中的常见问法

练习答案在 `answers/` 目录。

## 清理
```bash
mysql -u root -padmin < teardown.sql
```

---

🛠️ 构建计划详见 [build.md](build.md)
