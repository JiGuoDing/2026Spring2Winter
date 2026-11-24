"""executor.py 的单元测试：覆盖写语句拒绝、多语句拒绝、只读连接、超时、行数上限。"""
from __future__ import annotations

import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import executor  # noqa: E402


class ExecutorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.db = Path(cls._tmp.name) / "demo.sqlite"
        con = sqlite3.connect(str(cls.db))
        con.execute("CREATE TABLE demo (id INTEGER PRIMARY KEY, name TEXT, amount REAL)")
        con.executemany("INSERT INTO demo VALUES (?, ?, ?)",
                        [(1, "甲", 10.5), (2, "乙", None), (3, "丙", 3.25)])
        con.commit()
        con.close()

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    # ---- 正常路径 -----------------------------------------------------
    def test_查询成功(self):
        out = executor.execute(str(self.db), "SELECT id, name FROM demo ORDER BY id")
        self.assertIsNone(out["error"])
        self.assertEqual(out["columns"], ["id", "name"])
        self.assertEqual(out["rows"], [[1, "甲"], [2, "乙"], [3, "丙"]])
        self.assertIsInstance(out["elapsed_ms"], float)
        self.assertFalse(out["truncated"])

    def test_空结果不是错误(self):
        out = executor.execute(str(self.db), "SELECT id FROM demo WHERE id > 100")
        self.assertIsNone(out["error"])
        self.assertEqual(out["columns"], ["id"])
        self.assertEqual(out["rows"], [])

    def test_none值原样返回(self):
        out = executor.execute(str(self.db), "SELECT amount FROM demo WHERE id = 2")
        self.assertIsNone(out["error"])
        self.assertEqual(out["rows"], [[None]])

    def test_注释前缀可用(self):
        sql = "-- 统计总行数\n/* 块注释也不该影响判定 */\nSELECT COUNT(*) FROM demo"
        out = executor.execute(str(self.db), sql)
        self.assertIsNone(out["error"])
        self.assertEqual(out["rows"], [[3]])

    def test_短语句以with开头可用(self):
        sql = ("WITH t AS (SELECT amount FROM demo WHERE amount IS NOT NULL) "
               "SELECT COUNT(*) FROM t")
        out = executor.execute(str(self.db), sql)
        self.assertIsNone(out["error"])
        self.assertEqual(out["rows"], [[2]])

    def test_字符串里的写关键字不算写语句(self):
        out = executor.execute(str(self.db), "SELECT 'DELETE FROM demo' AS s")
        self.assertIsNone(out["error"])
        self.assertEqual(out["rows"], [["DELETE FROM demo"]])

    # ---- 语句层保护 ---------------------------------------------------
    def test_多语句被拒(self):
        for sql in ("SELECT 1; SELECT 2", "SELECT 1; DELETE FROM demo"):
            out = executor.execute(str(self.db), sql)
            self.assertIsNotNone(out["error"], sql)
            self.assertEqual(out["rows"], [])

    def test_写语句被拒(self):
        statements = (
            "DELETE FROM demo",
            "UPDATE demo SET name = 'x'",
            "INSERT INTO demo VALUES (9, 'x', 1.0)",
            "DROP TABLE demo",
            "CREATE TABLE t2 (a INTEGER)",
            "ALTER TABLE demo ADD COLUMN y TEXT",
            "PRAGMA table_info(demo)",
            "ATTACH DATABASE 'x.db' AS x",
            "VACUUM",
            "WITH t AS (SELECT 1) DELETE FROM demo",
            "REPLACE INTO demo VALUES (1, 'x', 0)",
        )
        for sql in statements:
            out = executor.execute(str(self.db), sql)
            self.assertIsNotNone(out["error"], sql)
            self.assertEqual(out["columns"], [], sql)

    def test_空语句被拒(self):
        for sql in ("", "   ", "-- 只有注释"):
            self.assertIsNotNone(executor.execute(str(self.db), sql)["error"])

    def test_表不存在返回错误(self):
        out = executor.execute(str(self.db), "SELECT * FROM 不存在的表")
        self.assertIsNotNone(out["error"])
        self.assertIn("SQL 执行失败", out["error"])

    # ---- 连接层保护 ---------------------------------------------------
    def test_只读连接写入抛错(self):
        con = executor.open_readonly(self.db)
        try:
            with self.assertRaises(sqlite3.OperationalError):
                con.execute("DELETE FROM demo")
        finally:
            con.close()
        # 数据没有被删
        out = executor.execute(str(self.db), "SELECT COUNT(*) FROM demo")
        self.assertEqual(out["rows"], [[3]])

    def test_快照不存在(self):
        out = executor.execute(str(Path(self._tmp.name) / "nope.sqlite"), "SELECT 1")
        self.assertIsNotNone(out["error"])
        self.assertIn("打开快照失败", out["error"])

    # ---- 资源层保护 ---------------------------------------------------
    def test_行数上限(self):
        sql = ("WITH RECURSIVE c(x) AS (SELECT 1 UNION ALL SELECT x + 1 FROM c WHERE x < 100) "
               "SELECT x FROM c")
        out = executor.execute(str(self.db), sql, row_limit=10)
        self.assertIsNone(out["error"])
        self.assertTrue(out["truncated"])
        self.assertEqual(len(out["rows"]), 10)
        self.assertEqual(out["rows"][0], [1])

    def test_超时(self):
        sql = ("WITH RECURSIVE c(x) AS (SELECT 1 UNION ALL SELECT x + 1 FROM c "
               "WHERE x < 200000000) SELECT COUNT(*) FROM c")
        out = executor.execute(str(self.db), sql, timeout_s=0.2)
        self.assertIsNotNone(out["error"])
        self.assertIn("超时", out["error"])

    # ---- 入口兼容 -----------------------------------------------------
    def test_单参形式(self):
        out = executor.execute("SELECT 1")
        for key in ("columns", "rows", "elapsed_ms", "error"):
            self.assertIn(key, out)

    def test_别名入口可用(self):
        for name in ("run", "query", "execute_sql"):
            self.assertTrue(callable(getattr(executor, name, None)), name)


if __name__ == "__main__":
    unittest.main()
