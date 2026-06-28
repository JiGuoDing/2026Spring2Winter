-- ============================================================
-- Hive SQL 面试题：窗口函数与排名
-- ============================================================

-- 建表：学生成绩表
DROP TABLE IF EXISTS student_score;
CREATE TABLE student_score (
    student_id   STRING COMMENT '学号',
    student_name STRING COMMENT '学生姓名',
    course       STRING COMMENT '课程',
    score        INT    COMMENT '成绩'
) COMMENT '学生成绩表';

-- 插入数据
INSERT INTO student_score VALUES
    ('S001', '张三', '语文', 85),
    ('S001', '张三', '数学', 92),
    ('S001', '张三', '英语', 78),
    ('S002', '李四', '语文', 90),
    ('S002', '李四', '数学', 88),
    ('S002', '李四', '英语', 95),
    ('S003', '王五', '语文', 76),
    ('S003', '王五', '数学', 85),
    ('S003', '王五', '英语', 82),
    ('S004', '赵六', '语文', 92),
    ('S004', '赵六', '数学', 91),
    ('S004', '赵六', '英语', 88),
    ('S005', '孙七', '语文', 68),
    ('S005', '孙七', '数学', 72),
    ('S005', '孙七', '英语', 65);

-- ============================================================
-- 题目 1：每门课程成绩排名（并列排名，不跳号）
-- 要求：查询每门课程中，每个学生的成绩排名（rank），
--       成绩相同时排名相同，不跳号（使用 DENSE_RANK）
-- 期望列：课程、学生姓名、成绩、排名
-- ============================================================
SELECT
    course,
    student_name,
    score,
    DENSE_RANK() OVER (PARTITION BY course ORDER BY score DESC) AS course_rank
FROM student_score;

-- [评价] ✅ 正确。
-- 1. 使用了 DENSE_RANK，满足"并列排名、不跳号"的要求。
-- 2. PARTITION BY course 按课程分组，ORDER BY score DESC 按成绩降序排列，逻辑正确。
-- 3. 输出列与期望列完全匹配。

-- ============================================================
-- 题目 2：每门课程成绩排名（并列排名，跳号）
-- 要求：查询每门课程中，每个学生的成绩排名（rank），
--       成绩相同时排名相同，跳号（使用 RANK）
-- 期望列：课程、学生姓名、成绩、排名
-- ============================================================
SELECT
    course,
    student_name,
    score,
    RANK() OVER (PARTITION BY course ORDER BY score DESC) AS course_rank
FROM student_score;

-- [评价] ✅ 正确（存在一个拼写小问题已修正）。
-- 1. 使用了 RANK，满足"并列排名、跳号"的要求。
-- 2. PARTITION BY course 和 ORDER BY score DESC 正确。
-- 3. 原题解中别名写成了 `corse_rank`（少了一个 u），应为 `course_rank`，已修正。
-- 4. 输出列与期望列完全匹配。

-- ============================================================
-- 题目 3：每个学生的总分及总分排名
-- 要求：计算每个学生的总分，并按总分降序排名（ROW_NUMBER）
-- 期望列：学号、学生姓名、总分、排名
-- ============================================================
SELECT
    student_id,
    student_name,
    SUM(score)                                                          AS total_score,
    ROW_NUMBER() OVER (ORDER BY SUM(score) DESC)                        AS total_score_rank
FROM student_score
GROUP BY student_id, student_name
ORDER BY SUM(score) DESC;

-- [评价] ✅ 正确。
-- 1. 使用 ROW_NUMBER 窗口函数，符合题目要求。
-- 2. GROUP BY 按学生聚合求总分，逻辑正确。
-- 3. 窗口函数 OVER (ORDER BY SUM(score) DESC) 按总分降序排名，正确。
-- 4. 末尾的 ORDER BY SUM(score) DESC 用于结果展示排序，合理。
-- 5. 注意：ROW_NUMBER 在总分相同时会随机分配不同排名（不并列），题目明确要求
--    ROW_NUMBER，所以这是符合预期的。若面试中希望相同总分并列排名，则需改用 RANK。
-- 6. 输出列与期望列完全匹配。

-- ============================================================
-- 题目 4：每门课程成绩的前一名和后一名成绩
-- 要求：使用 LAG/LEAD 窗口函数，查询每个学生在每门课程中，
--       成绩的上一行和下一行成绩（按成绩降序排列）
-- 期望列：课程、学生姓名、成绩、上一名成绩、下一名成绩
-- ============================================================
SELECT
    course,
    student_name,
    score,
    LAG(score, 1)  OVER (PARTITION BY course ORDER BY score DESC) AS preceding_score,
    LEAD(score, 1) OVER (PARTITION BY course ORDER BY score DESC) AS following_score
FROM student_score;

-- [评价] ✅ 正确。
-- 1. 正确使用了 LAG 和 LEAD 窗口函数。
-- 2. PARTITION BY course 按课程分组，ORDER BY score DESC 按成绩降序，逻辑正确。
-- 3. LAG(score, 1) 取上一行成绩，LEAD(score, 1) 取下一行成绩，正确。
-- 4. 原题解中第三个参数 NULL 是 LAG/LEAD 的默认值，可省略，已精简。
-- 5. 输出列与期望列完全匹配。

-- ============================================================
-- 题目 5：每门课程成绩与最高分的差值
-- 要求：查询每个学生在每门课程中，成绩与课程最高分的差值
-- 期望列：课程、学生姓名、成绩、最高分、差值
-- ============================================================
SELECT
    course,
    student_name,
    score,
    MAX(score) OVER (PARTITION BY course)           AS max_course_score,
    score - MAX(score) OVER (PARTITION BY course)   AS course_score_diff
FROM student_score;

-- [评价] ✅ 正确。
-- 1. 使用 MAX 窗口函数计算每门课程的最高分，正确。
-- 2. PARTITION BY course 按课程分组，逻辑正确。
-- 3. 差值 = score - max(score)，结果为负数或零（成绩不可能超过最高分），语义正确。
-- 4. 原题解中 `OVER( partition by course)` 有多余空格，已修正为统一格式。
-- 5. 输出列与期望列完全匹配。