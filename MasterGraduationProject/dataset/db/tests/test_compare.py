"""compare.py 的单元测试：覆盖浮点容差、列序、行序、空结果与报错、NULL、多重集。"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import compare  # noqa: E402


def result(columns, rows, error=None, elapsed_ms=1.0):
    """构造一个与 executor.execute 同形的结果。"""
    return {"columns": list(columns),
            "rows": [list(row) for row in rows],
            "elapsed_ms": elapsed_ms,
            "error": error}


class NormalizeTest(unittest.TestCase):
    def test_数值舍入到六位(self):
        self.assertEqual(compare.normalize_value(1.0000004), 1.0)
        self.assertEqual(compare.normalize_value(1.0000006), 1.000001)
        self.assertEqual(compare.normalize_value(-0.0), 0.0)

    def test_none与空串不同(self):
        self.assertIsNone(compare.normalize_value(None))
        self.assertEqual(compare.normalize_value(""), "")
        self.assertNotEqual(compare.normalize_value(None), compare.normalize_value(""))

    def test_日期统一为iso(self):
        self.assertEqual(compare.normalize_value("2024/01/05"), "2024-01-05")
        self.assertEqual(compare.normalize_value("2024-05-15 06:00:00Z"),
                         "2024-05-15T06:00:00")
        self.assertEqual(compare.normalize_value("2024-05-15T06:00:00.5+08:00"),
                         "2024-05-15T06:00:00")
        # 非法日期保持原样，不做猜测性改写
        self.assertEqual(compare.normalize_value("2024-13-01"), "2024-13-01")

    def test_列按名排序且行随之重排(self):
        got = compare.normalize(result(["b", "a"], [[2, 1]]))
        self.assertEqual(got["columns"], ["a", "b"])
        self.assertEqual(got["rows"], [[1, 2]])

    def test_默认不保序(self):
        got = compare.normalize(result(["a"], [[3], [1], [2]]))
        self.assertEqual(got["rows"], [[1], [2], [3]])

    def test_显式保序(self):
        got = compare.normalize(result(["a"], [[3], [1]]), ordered=True)
        self.assertEqual(got["rows"], [[3], [1]])


class CompareTest(unittest.TestCase):
    def test_浮点容差(self):
        near = compare.compare(result(["v"], [[1.0000001]]), result(["v"], [[1.0]]))
        self.assertTrue(near["equal"], near["reason"])
        far = compare.compare(result(["v"], [[1.0001]]), result(["v"], [[1.0]]))
        self.assertFalse(far["equal"])

    def test_列序不同视为相同(self):
        a = result(["a", "b"], [[1, 2]])
        b = result(["b", "a"], [[2, 1]])
        self.assertTrue(compare.compare(a, b)["equal"])

    def test_行序不同视为相同(self):
        a = result(["a"], [[1], [2], [3]])
        b = result(["a"], [[3], [1], [2]])
        self.assertTrue(compare.compare(a, b)["equal"])

    def test_保序时行序不同判为不等(self):
        a = result(["a"], [[1], [2], [3]])
        b = result(["a"], [[3], [1], [2]])
        out = compare.compare(a, b, ordered=True)
        self.assertFalse(out["equal"])
        self.assertTrue(out["missing"] and out["extra"])

    def test_空结果与空结果相同(self):
        self.assertTrue(compare.compare(result([], []), result([], []))["equal"])

    def test_空结果与报错不同(self):
        out = compare.compare(result([], []), result([], [], error="no such table: x"))
        self.assertFalse(out["equal"])
        self.assertIn("报错", out["reason"])

    def test_两侧同样报错视为相同(self):
        a = result([], [], error="interrupted")
        b = result([], [], error="interrupted")
        self.assertTrue(compare.compare(a, b)["equal"])

    def test_null只等于null(self):
        self.assertTrue(compare.compare(result(["v"], [[None]]),
                                        result(["v"], [[None]]))["equal"])
        self.assertFalse(compare.compare(result(["v"], [[None]]),
                                         result(["v"], [[""]]))["equal"])
        self.assertFalse(compare.compare(result(["v"], [[None]]),
                                         result(["v"], [[0]]))["equal"])

    def test_多重集不去重(self):
        out = compare.compare(result(["a"], [[1], [1]]), result(["a"], [[1]]))
        self.assertFalse(out["equal"])
        self.assertEqual(len(out["missing"]), 1)
        self.assertEqual(out["missing"][0], {"a": 1.0})

    def test_多重集同构成相同(self):
        a = result(["a"], [[1], [1], [2]])
        b = result(["a"], [[2], [1], [1]])
        self.assertTrue(compare.compare(a, b)["equal"])

    def test_列集合不一致(self):
        out = compare.compare(result(["a", "b"], [[1, 2]]), result(["a", "c"], [[1, 3]]))
        self.assertFalse(out["equal"])
        self.assertEqual(out["missing"], ["b"])
        self.assertEqual(out["extra"], ["c"])

    def test_标量比较(self):
        self.assertTrue(compare.compare(3, 3.0)["equal"])
        self.assertTrue(compare.compare(None, None)["equal"])
        self.assertFalse(compare.compare(3, "3")["equal"])

    def test_忽略耗时字段(self):
        a = result(["a"], [[1]], elapsed_ms=1.0)
        b = result(["a"], [[1]], elapsed_ms=999.0)
        self.assertTrue(compare.compare(a, b)["equal"])

    def test_行数不同给出原因(self):
        out = compare.compare(result(["a"], [[1], [2]]), result(["a"], [[1]]))
        self.assertFalse(out["equal"])
        self.assertIn("缺失", out["reason"])
        self.assertEqual(out["extra"], [])


if __name__ == "__main__":
    unittest.main()
