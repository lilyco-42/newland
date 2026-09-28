-- 查询 nleedge 数据库中所有数据表和每个表的记录数
SELECT TABLE_NAME AS 表名,
       TABLE_ROWS AS 记录数
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'nleedge'
ORDER BY TABLE_NAME;