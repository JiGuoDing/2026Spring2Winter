-- ============================================================
-- MySQL Tutorial — 一键清理脚本
-- 功能：删除 mysql_tutorial 数据库
-- 使用：mysql -u root -padmin < teardown.sql
-- ============================================================

DROP DATABASE IF EXISTS mysql_tutorial;

SELECT '🗑️  数据库 mysql_tutorial 已删除' AS 状态;
